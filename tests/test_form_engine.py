from backend import browser, form_engine, providers
from playwright.sync_api import sync_playwright


def _profile():
    return {
        'name': 'Jane Doe',
        'headline': 'Frontend Engineer',
        'email': 'jane@example.com',
        'phone': '+20 100 123 4567',
        'location': 'Cairo, Egypt',
        'links': [],
        'sections': [{
            'title': 'Professional Experience',
            'items': [{
                'id': 'evidence-react',
                'text': 'Built responsive React interfaces for customer portals and integrated REST APIs.',
            }],
        }],
    }


def test_custom_question_uses_full_context_and_is_audited_before_filling(client, job, monkeypatch):
    profile = _profile()
    evidence = profile['sections'][0]['items'][0]['text']
    seen = {}

    def ask(schema, instruction, payload):
        if schema is form_engine.FieldAnswers:
            question = payload['questions'][0]
            seen['question'] = question
            evidence_id = next(iter(payload['cv_evidence']))
            return form_engine.FieldAnswers(answers=[form_engine.FieldAnswer(
                field_key=question['field_key'],
                answer=evidence,
                evidence_ids=[evidence_id],
                answerable=True,
            )])
        if schema is providers.Checks:
            entry = payload['entries'][0]
            seen['audit'] = entry
            return providers.Checks(checks=[providers.Check(
                evidence_id=entry['evidence_id'], supported=True, reason='Directly supported by CV evidence.',
            )])
        raise AssertionError(f'Unexpected provider schema: {schema.__name__}')

    monkeypatch.setattr(providers, 'ask', ask)
    html = '''<fieldset>
      <legend>Describe your React experience *</legend>
      <p>Use one relevant project example and keep your answer concise.</p>
      <textarea id="experience" name="experience" required></textarea>
    </fieldset>'''
    with sync_playwright() as playwright:
        chromium = playwright.chromium.launch(headless=True)
        try:
            page = chromium.new_page()
            page.set_content(html)
            package = {'answers': {}}
            unresolved = browser._fill_container_fields(page, page, profile, job, package, {})
            assert unresolved == []
            assert page.locator('#experience').input_value() == evidence
            assert seen['question']['question'] == 'Describe your React experience *'
            assert 'one relevant project example' in seen['question']['nearby_context']
            assert seen['audit']['cv_evidence']['evidence-react'] == evidence
            assert package['answers']['#experience'] == evidence
        finally:
            chromium.close()


def test_unsupported_ai_answer_stays_blank_and_triggers_user_handoff(client, job, monkeypatch):
    profile = _profile()
    evidence_id = 'evidence-react'

    def ask(schema, instruction, payload):
        if schema is form_engine.FieldAnswers:
            question = payload['questions'][0]
            return form_engine.FieldAnswers(answers=[form_engine.FieldAnswer(
                field_key=question['field_key'],
                answer='Led the architecture of the company platform.',
                evidence_ids=[evidence_id],
                answerable=True,
            )])
        if schema is providers.Checks:
            entry = payload['entries'][0]
            return providers.Checks(checks=[providers.Check(
                evidence_id=entry['evidence_id'], supported=False, reason='Leadership is not established by the source.',
            )])
        raise AssertionError(f'Unexpected provider schema: {schema.__name__}')

    monkeypatch.setattr(providers, 'ask', ask)
    html = '''<label for="experience">Describe your React experience *</label>
    <textarea id="experience" required></textarea>'''
    with sync_playwright() as playwright:
        chromium = playwright.chromium.launch(headless=True)
        try:
            page = chromium.new_page()
            page.set_content(html)
            unresolved = browser._fill_container_fields(page, page, profile, job, {'answers': {}}, {})
            assert page.locator('#experience').input_value() == ''
            assert unresolved == ['Describe your React experience *']
        finally:
            chromium.close()


def test_salary_and_jurisdiction_answers_are_never_inferred():
    assert form_engine.resolve_salary(
        'Expected annual salary', {'location': 'Cairo, Egypt'}, {'salary_note': 'Negotiable'}
    ) is None
    assert form_engine.resolve_salary(
        'Expected hourly rate', {'location': 'Remote'}, {'salary_note': ''}
    ) is None
    assert form_engine.resolve_work_auth(
        'Are you authorized to work in the United States?', {'work_authorization': 'Egyptian citizen'}
    ) is None
    assert form_engine.resolve_contact_field('Country of citizenship', _profile()) is None
