from backend import providers, store, tailoring
from backend.documents import verify_files


def package_with_missing_requirement(job, evidence_id=None):
    tailoring.prepare(job['id'], 'local')
    package = store.get_package(job['id'])
    data = store.package_data(package)
    row = data['requirements'][0]
    row['support'] = 'missing'
    if evidence_id:
        evidence = store.get_package(job['id'])['profile']
        text = next(item['text'] for section in evidence['sections'] for item in section['items'] if item['id'] == evidence_id)
        row['evidence_ids'] = [evidence_id]
        row['evidence'] = [{'id': evidence_id, 'text': text}]
    else:
        row['evidence_ids'] = []
        row['evidence'] = []
    store.revise_package(package['id'], data)
    return store.get_package(job['id'])


def connect_custom_provider(monkeypatch):
    monkeypatch.setattr(providers, 'get_provider_config', lambda: {
        'provider': 'custom', 'connected': True, 'key': '', 'base_url': 'http://localhost:11434/v1',
    })


def test_draft_and_apply_rewrite_creates_a_new_verified_package(client, job, monkeypatch):
    tailoring.prepare(job['id'], 'local')
    package = store.get_package(job['id'])
    evidence_id = next(iter(tailoring.editable_profile_entries(package['profile'])))
    package = package_with_missing_requirement(job, evidence_id)
    original = package['source_evidence'][evidence_id]
    current = next(
        item['text'] for section in package['profile']['sections'] for item in section['items']
        if item['id'] == evidence_id
    )
    connect_custom_provider(monkeypatch)

    def ask(schema, instruction, payload):
        if schema is providers.CVImprovements:
            return providers.CVImprovements(changes=[providers.CVImprovement(
                requirement_indices=[0], action='rewrite', evidence_id=evidence_id,
                text=original + ' Delivered the work with cross-functional partners.',
            )])
        if schema is providers.Checks:
            return providers.Checks(checks=[providers.Check(
                evidence_id=row['evidence_id'], supported=True, reason='Supported by the source entry.',
            ) for row in payload['entries']])
        if schema is providers.Coverages:
            evidence = next(iter(payload['cv_entries']))
            return providers.Coverages(coverage=[providers.Coverage(
                requirement_index=row['index'], support='full', evidence_ids=[evidence],
                explanation='The updated CV statement supports this requirement.',
            ) for row in payload['requirements']])
        raise AssertionError(f'Unexpected provider schema: {schema.__name__}')

    monkeypatch.setattr(providers, 'ask', ask)
    old_id, old_hash = package['id'], package['hash']
    response = client.post(f"/api/jobs/{job['id']}/coverage/improvements/draft", json={
        'package_hash': package['hash'],
        'selections': [{'requirement_index': 0, 'evidence_text': '', 'evidence_confirmed': False}],
    })
    assert response.status_code == 200, response.text
    draft = response.json()
    assert len(draft['suggestions']) == 1
    assert draft['suggestions'][0]['before'] == current
    assert draft['suggestions'][0]['source_evidence'] == original
    assert store.get_package(job['id'])['id'] == old_id

    applied = client.post(f"/api/jobs/{job['id']}/coverage/improvements/apply", json={
        'package_hash': package['hash'],
        'draft_id': draft['draft_id'],
        'suggestion_ids': [draft['suggestions'][0]['id']],
    })
    assert applied.status_code == 200, applied.text
    updated = store.get_package(job['id'])
    assert updated['id'] != old_id
    assert updated['cv_reviewed'] is False
    assert updated['coverage_reviewed'] is False
    assert store.get_package_by_id(old_id)['hash'] == old_hash
    assert store.get_package_by_id(old_id)['profile']['sections'] == package['profile']['sections']
    changed = next(item for section in updated['profile']['sections'] for item in section['items'] if item['id'] == evidence_id)
    assert changed['text'].endswith('Delivered the work with cross-functional partners.')
    assert updated['changes'][-1]['evidence'] == original
    verify_files(updated)


def test_new_summary_statement_requires_confirmed_user_evidence_and_is_audited(client, job, monkeypatch):
    tailoring.prepare(job['id'], 'local')
    package = package_with_missing_requirement(job)
    connect_custom_provider(monkeypatch)
    response = client.post(f"/api/jobs/{job['id']}/coverage/improvements/draft", json={
        'package_hash': package['hash'],
        'selections': [{'requirement_index': 0, 'evidence_text': '', 'evidence_confirmed': False}],
    })
    assert response.status_code == 400
    assert 'evidence' in response.json()['detail'].lower()

    user_evidence = 'Built React applications and integrated REST APIs for customer-facing products.'

    def ask(schema, instruction, payload):
        if schema is providers.CVImprovements:
            return providers.CVImprovements(changes=[providers.CVImprovement(
                requirement_indices=[0], action='add', evidence_id='user:0',
                text='Built React applications and integrated REST APIs for customer-facing products.',
            )])
        if schema is providers.Checks:
            return providers.Checks(checks=[providers.Check(
                evidence_id=row['evidence_id'], supported=True, reason='Directly supported by applicant evidence.',
            ) for row in payload['entries']])
        if schema is providers.Coverages:
            evidence = next(iter(payload['cv_entries']))
            return providers.Coverages(coverage=[providers.Coverage(
                requirement_index=row['index'], support='full', evidence_ids=[evidence], explanation='Supported by the added statement.',
            ) for row in payload['requirements']])
        raise AssertionError(f'Unexpected provider schema: {schema.__name__}')

    monkeypatch.setattr(providers, 'ask', ask)
    response = client.post(f"/api/jobs/{job['id']}/coverage/improvements/draft", json={
        'package_hash': package['hash'],
        'selections': [{
            'requirement_index': 0,
            'evidence_text': user_evidence,
            'evidence_confirmed': True,
        }],
    })
    assert response.status_code == 200, response.text
    draft = response.json()
    assert draft['suggestions'][0]['action'] == 'add'
    assert draft['suggestions'][0]['section'] == 'Summary'

    applied = client.post(f"/api/jobs/{job['id']}/coverage/improvements/apply", json={
        'package_hash': package['hash'], 'draft_id': draft['draft_id'],
        'suggestion_ids': [draft['suggestions'][0]['id']],
    })
    assert applied.status_code == 200, applied.text
    updated = store.get_package(job['id'])
    added = next(item for section in updated['profile']['sections'] for item in section['items'] if item['id'] == updated['changes'][-1]['id'])
    assert added['text'] == user_evidence
    assert updated['source_evidence'][added['id']] == user_evidence
    assert updated['requirements'][0]['evidence_ids']
    verify_files(updated)


def test_unsupported_edits_are_not_offered_and_stale_drafts_cannot_apply(client, job, monkeypatch):
    tailoring.prepare(job['id'], 'local')
    package = store.get_package(job['id'])
    evidence_id = next(iter(tailoring.editable_profile_entries(package['profile'])))
    package = package_with_missing_requirement(job, evidence_id)
    connect_custom_provider(monkeypatch)

    def ask(schema, instruction, payload):
        if schema is providers.CVImprovements:
            return providers.CVImprovements(changes=[providers.CVImprovement(
                requirement_indices=[0], action='rewrite', evidence_id=evidence_id,
                text='Led a 25-person team and delivered 400% growth.',
            )])
        if schema is providers.Checks:
            return providers.Checks(checks=[])
        raise AssertionError(f'Unexpected provider schema: {schema.__name__}')

    monkeypatch.setattr(providers, 'ask', ask)
    response = client.post(f"/api/jobs/{job['id']}/coverage/improvements/draft", json={
        'package_hash': package['hash'],
        'selections': [{'requirement_index': 0, 'evidence_text': '', 'evidence_confirmed': False}],
    })
    assert response.status_code == 200, response.text
    draft = response.json()
    assert draft['suggestions'] == []
    assert len(draft['unresolved']) == 1

    changed = store.get_job(job['id'])
    store.update_job(job['id'], title=changed['title'] + ' Updated')
    stale = client.post(f"/api/jobs/{job['id']}/coverage/improvements/apply", json={
        'package_hash': package['hash'], 'draft_id': draft['draft_id'], 'suggestion_ids': ['not-a-real-suggestion'],
    })
    assert stale.status_code == 400
    assert store.get_package(job['id'])['id'] == package['id']
