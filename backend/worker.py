import inspect
import json
from concurrent.futures import ThreadPoolExecutor
from pydantic import ValidationError
from . import store

pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='job-agent')

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
    name=type(exc).__name__
    if 'Authentication' in name: return 'API authentication failed. Check your key in Settings.'
    if 'RateLimit' in name: return 'The provider rate limit or quota was reached. Check your account before retrying.'
    if 'Timeout' in name: return 'The operation timed out. Check the current application status before retrying.'
    if 'HTTPStatus' in name:
        return f'The remote service returned HTTP {exc.response.status_code}. Check access or try later.'
    if 'Error' in name: return 'The operation could not finish ('+name+'). Check your connection and browser setup, or continue manually.'
    return 'The operation could not finish. Review the current job state before retrying.'

def enqueue(kind, target, fn):
    run_id=store.uid()
    with store.db() as c:
        active=c.execute("SELECT id FROM runs WHERE kind=? AND COALESCE(target,'')=COALESCE(?,'') AND state IN ('queued','running')",(kind,target)).fetchone()
        if active: return active['id']
        c.execute('INSERT INTO runs VALUES (?,?,?,?,?,?,?)',(run_id,kind,target,'queued','Waiting to start.',store.now(),store.now()))
    def work():
        with store.db() as c: c.execute("UPDATE runs SET state='running',message='Starting operation…',updated=? WHERE id=?",(store.now(),run_id))
        def progress(step_msg: str):
            with store.db() as c:
                c.execute("UPDATE runs SET message=?, updated=? WHERE id=?", (step_msg, store.now(), run_id))
            if target:
                store.event(target, step_msg)
        try:
            sig = inspect.signature(fn)
            if len(sig.parameters) > 0:
                result = fn(progress)
            else:
                result = fn()
            message=result if isinstance(result,str) and len(result)>40 else 'Finished. Your workspace is up to date.'
            state='completed'
            if target:
                try:
                    store.update_job(target, last_error=None)
                except Exception:
                    pass
        except Exception as exc:
            state='failed'; message=error_message(exc)
            if target:
                try:
                    store.update_job(target, last_error=message)
                except Exception:
                    pass
            if kind in ('submit', 'auto_apply') and target and store.get_job(target)['state']=='submitting':
                # Includes failures before the browser opens or after click. Conservatively require a check.
                store.update_job(target,state='uncertain')
            if target: store.event(target,message)
        with store.db() as c: c.execute('UPDATE runs SET state=?,message=?,updated=? WHERE id=?',(state,message,store.now(),run_id))
    pool.submit(work)
    return run_id
