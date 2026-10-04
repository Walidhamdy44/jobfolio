import inspect
import json
from concurrent.futures import ThreadPoolExecutor
from pydantic import ValidationError
from . import store

pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='job-agent')


def error_message(exc):
    if isinstance(exc, ValidationError):
        return 'The AI provider returned an invalid structured response. Your previous CV is unchanged. Please try again or use local preparation.'
    if isinstance(exc, (json.JSONDecodeError, TypeError)) and 'json' in type(exc).__name__.lower():
        return 'The AI provider output could not be parsed as valid JSON. Your previous CV is unchanged.'
    if isinstance(exc, ValueError):
        msg = str(exc)
        if 'validation error' in msg.lower() or 'pydantic' in msg.lower():
            return 'The AI provider returned an invalid structured response. Your previous CV is unchanged. Please try again or use local preparation.'
        return msg
    # Avoid credentials, full URLs containing tokens, or applicant data in errors/logs.
    name = type(exc).__name__
    if 'Authentication' in name:
        return 'API authentication failed. Check your key in Settings.'
    if 'RateLimit' in name:
        return 'The provider rate limit or quota was reached. Check your account before retrying.'
    if 'Timeout' in name:
        return 'The operation timed out. Check the current application status before retrying.'
    if 'HTTPStatus' in name:
        return f'The remote service returned HTTP {exc.response.status_code}. Check access or try later.'
    if 'Error' in name:
        return 'The operation could not finish (' + name + '). Check your connection and browser setup, or continue manually.'
    return 'The operation could not finish. Review the current job state before retrying.'


def enqueue(kind, target, fn, run_id=None):
    run_id = run_id or store.uid()
    with store.db() as c:
        active = c.execute(
            "SELECT id FROM runs WHERE kind=? AND COALESCE(target,'')=COALESCE(?,'') AND state IN ('queued','running')",
            (kind, target),
        ).fetchone()
        if active:
            return active['id']
        c.execute(
            'INSERT INTO runs VALUES (?,?,?,?,?,?,?)',
            (run_id, kind, target, 'queued', 'Waiting to start.', store.now(), store.now()),
        )
    pool.submit(_execute, run_id, kind, target, fn)
    return run_id


def resume(run_id, fn):
    with store.db() as c:
        c.execute('BEGIN IMMEDIATE')
        run = c.execute('SELECT id,kind,target,state FROM runs WHERE id=?', (run_id,)).fetchone()
        if not run or run['kind'] != 'prepare' or not run['target']:
            raise ValueError('Preparation run was not found.')
        if run['state'] != 'interrupted':
            raise ValueError('Only an interrupted preparation can be resumed.')
        active = c.execute(
            "SELECT id FROM runs WHERE target=? AND state IN ('queued','running')",
            (run['target'],),
        ).fetchone()
        if active:
            raise ValueError('An operation for this job is still running. Wait for it to finish.')
        updated = c.execute(
            "UPDATE runs SET state='queued',message='Resuming saved preparation.',updated=? WHERE id=? AND state='interrupted'",
            (store.now(), run_id),
        )
        if updated.rowcount != 1:
            raise ValueError('Preparation run changed before it could be resumed.')
    pool.submit(_execute, run_id, run['kind'], run['target'], fn)
    return run_id


def _execute(run_id, kind, target, fn):
    with store.db() as c:
        c.execute(
            "UPDATE runs SET state='running',message='Starting operation...',updated=? WHERE id=?",
            (store.now(), run_id),
        )
    if kind == 'prepare' and target:
        from .prepare_graph import clear_interrupted_for_job
        try:
            clear_interrupted_for_job(target, except_run_id=run_id)
        except Exception:
            pass

    def progress(step_msg: str):
        with store.db() as c:
            c.execute('UPDATE runs SET message=?, updated=? WHERE id=?', (step_msg, store.now(), run_id))
        if target:
            store.event(target, step_msg)

    try:
        sig = inspect.signature(fn)
        result = fn(progress) if len(sig.parameters) > 0 else fn()
        message = result if isinstance(result, str) and len(result) > 40 else 'Finished. Your workspace is up to date.'
        state = 'completed'
        if target:
            try:
                store.update_job(target, last_error=None)
            except Exception:
                pass
    except Exception as exc:
        state = 'failed'
        message = error_message(exc)
        if target:
            try:
                store.update_job(target, last_error=message)
            except Exception:
                pass
        if kind in ('submit', 'auto_apply') and target and store.get_job(target)['state'] == 'submitting':
            # Includes failures before the browser opens or after click. Conservatively require a check.
            store.update_job(target, state='uncertain')
        if target:
            store.event(target, message)

    with store.db() as c:
        c.execute('UPDATE runs SET state=?,message=?,updated=? WHERE id=?', (state, message, store.now(), run_id))
    if kind == 'prepare' and state in ('completed', 'failed'):
        from .prepare_graph import clear_checkpoint
        clear_checkpoint(run_id)
