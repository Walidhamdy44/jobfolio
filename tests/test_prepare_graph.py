import time
from collections import Counter

import pytest

from backend import prepare_graph, providers, store, tailoring
from backend.documents import verify_files


def fake_ai_provider(monkeypatch, job, calls=None):
    calls = calls if calls is not None else Counter()
    profile = store.setting('profile')
    editable = tailoring.editable_profile_entries(profile)
    evidence_id, original = next(iter(editable.items()))
    quote = 'Experience building React applications and REST APIs.'

    def ask(schema, instruction, payload):
        calls[schema.__name__] += 1
        if schema is providers.Requirements:
            return providers.Requirements(requirements=[providers.Requirement(
                text=quote, priority='required', source_quote=quote,
            )])
        if schema is providers.Rewrites:
            return providers.Rewrites(changes=[providers.Rewrite(
                evidence_id=evidence_id,
                text=original + ' Work was delivered collaboratively.',
            )])
        if schema is providers.Checks:
            return providers.Checks(checks=[providers.Check(
                evidence_id=row['evidence_id'], supported=True, reason='Supported by the original entry.',
            ) for row in payload['entries']])
        if schema is providers.Coverages:
            first_evidence = next(iter(payload['cv_entries']))
            return providers.Coverages(coverage=[providers.Coverage(
                requirement_index=row['index'], support='full', evidence_ids=[first_evidence],
                explanation='Evidence was found in the CV.',
            ) for row in payload['requirements']])
        raise AssertionError(f'Unexpected provider schema: {schema.__name__}')

    monkeypatch.setattr(providers, 'ask', ask)
    return calls


def insert_interrupted_run(job_id, run_id):
    with store.db() as conn:
        conn.execute(
            'INSERT INTO runs VALUES (?,?,?,?,?,?,?)',
            (run_id, 'prepare', job_id, 'running', 'Running AI preparation.', store.now(), store.now()),
        )
    store.init()


def interrupt_after_draft(job, run_id):
    with prepare_graph.checkpoint_store() as saver:
        graph = prepare_graph._build_graph().compile(
            checkpointer=saver,
            interrupt_after=['draft_rewrites'],
        )
        graph.invoke(
            {'job_id': job['id'], 'run_id': run_id},
            config=prepare_graph._config(run_id),
            durability='sync',
        )
    insert_interrupted_run(job['id'], run_id)


def test_ai_graph_runs_guarded_stages_and_publishes_verified_exports(client, job, monkeypatch):
    fake_ai_provider(monkeypatch, job)
    progress = []
    run_id = store.uid()

    package_id = tailoring.prepare(job['id'], 'ai', progress=progress.append, run_id=run_id)

    assert package_id == run_id
    assert [message.split('...')[0] for message in progress] == [
        'Loading job posting and master profile',
        'Extracting job requirements with AI',
        'Checking requirement quotes and preserving omitted criteria',
        'Drafting evidence-based CV wording',
        'Auditing proposed edits against original evidence',
        'Assessing requirement coverage and evidence',
        'Generating CV files and publishing the review package',
        'CV prepared (100.0% coverage). Ready for your review.',
    ]
    package = store.get_package(job['id'])
    assert package['id'] == run_id
    assert package['mode'] == 'ai'
    assert len(package['requirements']) == 3
    assert package['changes']
    verify_files(package)

    with store.db() as conn:
        assert conn.execute('SELECT count(*) FROM packages WHERE job_id=?', (job['id'],)).fetchone()[0] == 1
    prepare_graph.clear_checkpoint(run_id)


def test_ai_requirement_verification_rejects_unquoted_text_and_merges_omitted_items(job):
    quote = 'Experience building React applications and REST APIs.'
    rows = [dict(text=quote, priority='required', source_quote=quote)]
    merged = tailoring.deduplicate_requirements(tailoring.verify_ai_requirements(job['description'], rows))

    assert len(merged) == 3
    assert any('TypeScript' in row['text'] for row in merged)
    assert any('Kubernetes' in row['text'] and row['priority'] == 'preferred' for row in merged)
    with pytest.raises(ValueError, match='source quotes'):
        tailoring.verify_ai_requirements(job['description'], [
            dict(text='Unrelated requirement', priority='required', source_quote='Not in this posting.'),
        ])


def test_coverage_failure_uses_conservative_local_assessment(job, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError('provider unavailable')

    monkeypatch.setattr(providers, 'ask', fail)
    requirements = [{'text': 'Production Kubernetes experience', 'priority': 'required', 'source_quote': 'Production Kubernetes experience'}]

    rows = tailoring.coverage(requirements, store.setting('profile'), ai=True)

    assert rows[0]['support'] in ('partial', 'missing')
    assert rows[0]['support'] != 'full'
    assert rows[0]['weight'] == 3


def test_failed_ai_extraction_does_not_replace_previous_package(client, job, monkeypatch):
    tailoring.prepare(job['id'], 'local')
    previous = store.get_package(job['id'])

    monkeypatch.setattr(providers, 'ask', lambda *args, **kwargs: providers.Requirements(requirements=[
        providers.Requirement(text='Invented requirement', priority='required', source_quote='Not in the posting.'),
    ]))
    run_id = store.uid()
    with pytest.raises(ValueError, match='source quotes'):
        tailoring.prepare(job['id'], 'ai', run_id=run_id)

    current = store.get_package(job['id'])
    assert current['id'] == previous['id']
    assert current['hash'] == previous['hash']
    prepare_graph.clear_checkpoint(run_id)


def test_resume_continues_after_checkpoint_without_repeating_completed_nodes(client, job, monkeypatch):
    calls = fake_ai_provider(monkeypatch, job)
    run_id = store.uid()
    interrupt_after_draft(job, run_id)
    assert calls['Requirements'] == 1
    assert calls['Rewrites'] == 1
    assert prepare_graph.resumable_run(job['id'])['id'] == run_id

    monkeypatch.setattr(providers, 'get_provider_config', lambda: {
        'provider': 'custom', 'connected': True, 'key': '', 'base_url': 'http://localhost:11434/v1',
    })
    response = client.post(f"/api/jobs/{job['id']}/prepare/{run_id}/resume")
    assert response.status_code == 200
    assert response.json() == {'run_id': run_id}

    for _ in range(300):
        with store.db() as conn:
            run = conn.execute('SELECT state FROM runs WHERE id=?', (run_id,)).fetchone()
        if run['state'] in ('completed', 'failed'):
            break
        time.sleep(0.02)

    assert run['state'] == 'completed'
    assert calls['Requirements'] == 1
    assert calls['Rewrites'] == 1
    assert calls['Checks'] == 1
    assert calls['Coverages'] == 1
    package = store.get_package(job['id'])
    assert package['id'] == run_id
    verify_files(package)
    with store.db() as conn:
        assert conn.execute('SELECT count(*) FROM packages WHERE job_id=?', (job['id'],)).fetchone()[0] == 1


def test_resume_is_hidden_when_inputs_change_or_a_newer_prepare_supersedes_it(client, job, monkeypatch):
    fake_ai_provider(monkeypatch, job)
    run_id = store.uid()
    interrupt_after_draft(job, run_id)
    changed = store.get_job(job['id'])
    store.update_job(job['id'], description=changed['description'] + '\nAnother required qualification.')
    assert prepare_graph.resumable_run(job['id']) is None
    store.update_job(job['id'], description=job['description'])
    assert prepare_graph.resumable_run(job['id'])['id'] == run_id

    with store.db() as conn:
        conn.execute(
            'INSERT INTO runs VALUES (?,?,?,?,?,?,?)',
            (store.uid(), 'prepare', job['id'], 'failed', 'Newer local preparation.', store.now(), store.now()),
        )
    assert prepare_graph.resumable_run(job['id']) is None
    prepare_graph.clear_checkpoint(run_id)


def test_resume_rejects_missing_checkpoint_and_concurrent_job_work(client, job, monkeypatch):
    missing_id = store.uid()
    insert_interrupted_run(job['id'], missing_id)
    assert prepare_graph.resumable_run(job['id']) is None
    missing_response = client.post(f"/api/jobs/{job['id']}/prepare/{missing_id}/resume")
    assert missing_response.status_code == 409

    fake_ai_provider(monkeypatch, job)
    run_id = store.uid()
    interrupt_after_draft(job, run_id)
    with store.db() as conn:
        conn.execute(
            'INSERT INTO runs VALUES (?,?,?,?,?,?,?)',
            (store.uid(), 'inspect', job['id'], 'running', 'Concurrent operation.', store.now(), store.now()),
        )
    response = client.post(f"/api/jobs/{job['id']}/prepare/{run_id}/resume")
    assert response.status_code == 400
    assert 'still running' in response.json()['detail']
    prepare_graph.clear_checkpoint(run_id)
