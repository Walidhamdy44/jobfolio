"""LangGraph orchestration for resumable AI CV preparation."""
import copy
import os
from contextlib import contextmanager
from typing import Any, TypedDict

os.environ.setdefault('LANGGRAPH_STRICT_MSGPACK', 'true')

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from . import profile as profiles, store


CHECKPOINT_DB = 'prepare-checkpoints.sqlite3'


class PreparationState(TypedDict, total=False):
    job_id: str
    run_id: str
    mode: str
    job_snapshot: dict[str, Any]
    profile_snapshot: dict[str, Any]
    profile_revision: int
    source_fingerprint: str
    raw_requirements: list[dict[str, Any]]
    requirements: list[dict[str, Any]]
    editable_entries: dict[str, str]
    rewrite_candidates: dict[str, str]
    profile: dict[str, Any]
    changes: list[dict[str, str]]
    coverage_rows: list[dict[str, Any]]
    score: float
    package_id: str


@contextmanager
def checkpoint_store():
    store.DATA.mkdir(parents=True, exist_ok=True)
    checkpoint_path = store.DATA / CHECKPOINT_DB
    with SqliteSaver.from_conn_string(str(checkpoint_path)) as saver:
        saver.setup()
        yield saver


def _source_fingerprint(job, profile):
    job_fields = ('id', 'title', 'company', 'location', 'url', 'description', 'verified', 'platform', 'source')
    return store.digest({
        'job': {key: job.get(key) for key in job_fields},
        'profile': profile,
    })


def _build_graph(progress=None):
    from . import tailoring

    def report(message):
        if progress:
            progress(message)

    def load_snapshot(state: PreparationState):
        report('Loading job posting and master profile...')
        job = store.get_job(state['job_id'])
        if job['state'] in ('submitted', 'submitting', 'uncertain'):
            raise ValueError('Resolve this application status before preparing another package.')
        master = store.setting('profile')
        if not master:
            raise ValueError('Import your master CV first.')
        master = copy.deepcopy(master)
        return {
            'mode': 'ai',
            'job_snapshot': copy.deepcopy(job),
            'profile_snapshot': master,
            'profile_revision': master.get('revision', 0),
            'profile': copy.deepcopy(master),
            'source_fingerprint': _source_fingerprint(job, master),
        }

    def extract_requirements(state: PreparationState):
        report('Extracting job requirements with AI...')
        return {'raw_requirements': tailoring.draft_ai_requirements(state['job_snapshot']['description'])}

    def verify_requirements(state: PreparationState):
        report('Checking requirement quotes and preserving omitted criteria...')
        rows = tailoring.verify_ai_requirements(
            state['job_snapshot']['description'], state['raw_requirements'])
        rows = tailoring.deduplicate_requirements(rows)
        if not rows:
            raise ValueError('No requirements could be identified. Add a complete description with requirements, or connect AI extraction.')
        return {'requirements': rows}

    def draft_rewrites(state: PreparationState):
        report('Drafting evidence-based CV wording...')
        editable, candidates = tailoring.draft_profile_rewrites(
            state['profile'], state['job_snapshot'], state['requirements'])
        return {'editable_entries': editable, 'rewrite_candidates': candidates}

    def audit_rewrites(state: PreparationState):
        report('Auditing proposed edits against original evidence...')
        profile, changes = tailoring.audit_profile_rewrites(
            state['profile'], state['editable_entries'], state['rewrite_candidates'], state['job_id'])
        return {'profile': profile, 'changes': changes}

    def assess_coverage(state: PreparationState):
        report('Assessing requirement coverage and evidence...')
        rows = tailoring.coverage(state['requirements'], state['profile'], ai=True)
        return {'coverage_rows': rows, 'score': tailoring.score(rows)}

    def publish_package(state: PreparationState):
        from .documents import generate, verify_files

        report('Generating CV files and publishing the review package...')
        job = state['job_snapshot']
        profile = copy.deepcopy(state['profile'])
        for section in profile['sections']:
            if section['title'] == 'Technical Skills':
                section['items'].sort(key=lambda item: -len(tailoring.tokens(item['text']) & tailoring.tokens(job['description'])))

        run_id = state['run_id']
        existing = store.get_package_by_id(run_id)
        if existing:
            if existing.get('job_id') != state['job_id']:
                raise ValueError('This preparation run is attached to a different job. Start a fresh preparation.')
            verify_files(existing)
            package_id = run_id
            newly_published = False
        else:
            package = {
                'job_id': state['job_id'],
                'job_snapshot': job,
                'profile_revision': state['profile_revision'],
                'profile': profile,
                'source_evidence': profiles.evidence(state['profile_snapshot']),
                'requirements': state['coverage_rows'],
                'score': state['score'],
                'changes': state['changes'],
                'mode': 'ai',
                'coverage_reviewed': False,
                'cv_reviewed': False,
                'form': None,
                'answers': {},
                'files': {},
                'note': 'AI-assessed coverage; review each requirement and CV statement.',
            }
            package['files'] = generate(profile, run_id)
            package_id = store.save_package(state['job_id'], package, package_id=run_id)
            newly_published = True

        published = store.get_package_by_id(package_id)
        if not published:
            raise ValueError('The prepared package could not be loaded. Start a fresh preparation.')
        verify_files(published)
        current = store.get_package(state['job_id'])
        if current and current['id'] == package_id:
            if not current.get('cv_reviewed') and not current.get('coverage_reviewed') and not current.get('approved'):
                store.update_job(state['job_id'], state='awaiting_review', score=current['score'])
        if newly_published:
            store.event(state['job_id'], 'AI CV package prepared. Review required before approval.')
        report(f"CV prepared ({published['score']}% coverage). Ready for your review.")
        return {'package_id': package_id}

    graph = StateGraph(PreparationState)
    graph.add_node('load_snapshot', load_snapshot)
    graph.add_node('extract_requirements', extract_requirements)
    graph.add_node('verify_requirements', verify_requirements)
    graph.add_node('draft_rewrites', draft_rewrites)
    graph.add_node('audit_rewrites', audit_rewrites)
    graph.add_node('assess_coverage', assess_coverage)
    graph.add_node('publish_package', publish_package)
    graph.add_edge(START, 'load_snapshot')
    graph.add_edge('load_snapshot', 'extract_requirements')
    graph.add_edge('extract_requirements', 'verify_requirements')
    graph.add_edge('verify_requirements', 'draft_rewrites')
    graph.add_edge('draft_rewrites', 'audit_rewrites')
    graph.add_edge('audit_rewrites', 'assess_coverage')
    graph.add_edge('assess_coverage', 'publish_package')
    graph.add_edge('publish_package', END)
    return graph


def _config(run_id):
    return {'configurable': {'thread_id': run_id}}


def run_ai_preparation(job_id, run_id, progress=None):
    with checkpoint_store() as saver:
        graph = _build_graph(progress).compile(checkpointer=saver)
        result = graph.invoke(
            {'job_id': job_id, 'run_id': run_id},
            config=_config(run_id),
            durability='sync',
        )
    return result['package_id']


def _snapshot_for(saver, run_id):
    graph = _build_graph().compile(checkpointer=saver)
    snapshot = graph.get_state(_config(run_id))
    if not snapshot or not snapshot.values or not snapshot.next:
        return None
    values = dict(snapshot.values)
    if values.get('run_id') != run_id or values.get('mode') != 'ai':
        return None
    return values


def _inputs_still_match(values, job_id):
    if values.get('job_id') != job_id:
        return False
    try:
        job = store.get_job(job_id)
        profile = store.setting('profile')
    except ValueError:
        return False
    if job['state'] in ('submitted', 'submitting', 'uncertain'):
        return False
    if not profile or profile.get('revision', 0) != values.get('profile_revision'):
        return False
    return values.get('source_fingerprint') == _source_fingerprint(job, profile)


def resumable_run(job_id):
    with store.db() as conn:
        row = conn.execute(
            "SELECT id,message,created,state FROM runs WHERE kind='prepare' AND target=? ORDER BY created DESC,id DESC LIMIT 1",
            (job_id,),
        ).fetchone()
    if not row or row['state'] != 'interrupted':
        return None
    try:
        with checkpoint_store() as saver:
            values = _snapshot_for(saver, row['id'])
            if not values or not _inputs_still_match(values, job_id):
                return None
    except Exception:
        return None
    return {'id': row['id'], 'message': row['message'], 'created': row['created']}


def resume_ai_preparation(run_id, progress=None):
    with checkpoint_store() as saver:
        graph = _build_graph(progress).compile(checkpointer=saver)
        values = _snapshot_for(saver, run_id)
        if not values:
            raise ValueError('No resumable preparation checkpoint was found. Start a fresh AI preparation.')
        if not _inputs_still_match(values, values['job_id']):
            raise ValueError('The job or master profile changed since this run stopped. Start a fresh AI preparation.')
        result = graph.invoke(None, config=_config(run_id), durability='sync')
    return result['package_id']


def clear_checkpoint(run_id):
    if not run_id:
        return
    if not (store.DATA / CHECKPOINT_DB).exists():
        return
    try:
        with checkpoint_store() as saver:
            saver.delete_thread(run_id)
    except Exception:
        # Checkpoint cleanup must not turn a completed package into a failed run.
        pass


def clear_interrupted_for_job(job_id, except_run_id=None):
    with store.db() as conn:
        rows = conn.execute(
            "SELECT id FROM runs WHERE kind='prepare' AND target=? AND state='interrupted'",
            (job_id,),
        ).fetchall()
    for row in rows:
        if row['id'] != except_run_id:
            clear_checkpoint(row['id'])
