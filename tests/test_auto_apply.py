import pytest
from unittest.mock import MagicMock
from playwright.sync_api import sync_playwright
from backend import store, form_engine, browser

def test_form_engine_contact_resolution():
    mock_profile = {
        'name': 'Jane Doe',
        'email': 'jane@example.com',
        'phone': '+1234567890',
        'location': 'Cairo, Egypt',
        'links': ['https://linkedin.com/in/janedoe', 'https://github.com/janedoe']
    }
    assert form_engine.resolve_contact_field('First Name', mock_profile) == 'Jane'
    assert form_engine.resolve_contact_field('Last Name', mock_profile) == 'Doe'
    assert form_engine.resolve_contact_field('Full Name', mock_profile) == 'Jane Doe'
    assert form_engine.resolve_contact_field('Email Address', mock_profile) == 'jane@example.com'
    assert form_engine.resolve_contact_field('Mobile Phone', mock_profile) == '+1234567890'
    assert form_engine.resolve_contact_field('LinkedIn Profile', mock_profile) == 'https://linkedin.com/in/janedoe'
    assert form_engine.resolve_contact_field('GitHub URL', mock_profile) == 'https://github.com/janedoe'

def test_form_engine_salary_resolution():
    # 1. With user salary note
    prefs = {'salary_note': '$95,000'}
    assert form_engine.resolve_salary('Expected Annual Salary', {}, prefs) == '95000'
    assert form_engine.resolve_salary('Monthly salary expectation', {}, prefs) == '7916'

    # 2. Without a user salary preference, leave the answer unresolved.
    cairo_job = {'location': 'Cairo, Egypt'}
    cairo_sal = form_engine.resolve_salary('Annual Compensation Requirement', cairo_job, {})
    assert cairo_sal is None

    remote_job = {'location': 'Remote / Worldwide'}
    remote_sal = form_engine.resolve_salary('Expected Salary (USD)', remote_job, {})
    assert remote_sal is None

def test_form_engine_experience_years():
    mock_profile = {
        'sections': [
            {'title': 'Experience', 'items': [{'text': '5+ years building React and TypeScript apps.'}]}
        ]
    }
    assert form_engine.resolve_experience_years('How many years of work experience do you have with React?', mock_profile) == '5'
    assert form_engine.resolve_experience_years('Years of TypeScript experience:', mock_profile) == '5'
    assert form_engine.resolve_experience_years('Years of Python experience:', mock_profile) is None


def test_unknown_screening_answers_are_not_invented(monkeypatch):
    monkeypatch.setattr(form_engine.providers, 'get_provider_config', lambda: {'connected': True})
    monkeypatch.setattr(form_engine.providers, 'ask', lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('AI must not answer sensitive questions')))
    assert form_engine.answer_single_field({'label': 'Expected annual salary', 'type': 'text'}, {}, {'location': 'Cairo'}, {}, {}) == ''
    assert form_engine.answer_single_field({'label': 'Are you authorized to work in the US?', 'type': 'text'}, {}, {}, {}, {}) == ''
    assert form_engine.answer_single_field({'label': 'I agree to the terms', 'type': 'text'}, {}, {}, {}, {}) == ''

def test_form_engine_dropdown_option_matching():
    options = [
        {'label': '0-1 year', 'value': 'junior'},
        {'label': '2-4 years', 'value': 'mid'},
        {'label': '5+ years', 'value': 'senior'},
    ]
    # Exact or keyword matching
    assert form_engine.match_dropdown_option(options, '5') == 'senior'
    assert form_engine.match_dropdown_option(options, 'mid') == 'mid'

    yes_no_opts = [
        {'label': 'Yes, I am authorized', 'value': 'yes_auth'},
        {'label': 'No', 'value': 'no_auth'}
    ]
    assert form_engine.match_dropdown_option(yes_no_opts, 'Yes') == 'yes_auth'
    assert form_engine.match_dropdown_option(yes_no_opts, 'No') == 'no_auth'

def test_browser_session_status_endpoint(client):
    res = client.get('/api/browser/session-status')
    assert res.status_code == 200
    data = res.json()
    assert 'profile_exists' in data

def test_auto_apply_endpoint_validation(client):
    # Job without package should fail
    job, _ = store.add_job({
        'title': 'Frontend Engineer',
        'company': 'Tech Corp',
        'location': 'Remote',
        'url': 'https://example.com/jobs/1',
        'description': 'React role'
    })
    res = client.post(f'/api/jobs/{job["id"]}/auto-apply', json={'auto_submit': False})
    assert res.status_code == 400
    assert 'Prepare and review a tailored CV' in res.json()['detail']


def test_unattended_auto_apply_stops_before_browser_launch(client):
    job, _ = store.add_job({
        'title': 'Frontend Engineer', 'company': 'Synthetic employer',
        'location': 'Remote', 'url': 'https://example.com/jobs/synthetic',
        'description': 'Responsibilities: Build accessible React applications and test frontend components.'
    })
    response = client.post(f'/api/jobs/{job["id"]}/auto-apply', json={'auto_submit': True})
    assert response.status_code == 400
    assert 'Unattended Auto-Apply is unavailable' in response.json()['detail']

def test_work_auth_no_guessing_and_negation():
    # AA-03: Never guess authorization or sponsorship when unstated
    assert form_engine.resolve_work_auth('Are you legally authorized to work in the US?', {}) is None
    assert form_engine.resolve_work_auth('Will you require visa sponsorship?', {}) is None
    # Negation must return 'No'
    assert form_engine.resolve_work_auth('Are you authorized to work in the US?', {'work_authorization': 'Not authorized to work in the US'}) == 'No'

def test_experience_and_notice_period_no_guessing():
    # AA-04: Empty profile returns None, not fabricated years
    assert form_engine.resolve_experience_years('How many years of React experience?', {}) is None
    assert form_engine.resolve_notice_period('When can you start?') is None
    assert form_engine.resolve_notice_period('When can you start?', {'notice_period': '2 weeks'}) == '2 weeks'

def test_salary_resolution_safeguards():
    # AA-05: An unspecified salary remains unresolved even when the location is known.
    assert form_engine.resolve_salary('Expected annual salary', {'location': 'Cairo'}, {}) is None
    # Unknown location without preferences returns None (unresolved)
    assert form_engine.resolve_salary('Expected annual salary', {'location': 'Berlin'}, {}) is None
    # Explicit monthly note preserves monthly amount
    assert form_engine.resolve_salary('Monthly salary expectation', {'location': 'Egypt'}, {'salary_note': 'EGP 65000 per month'}) == '65000'
    # Start date not misclassified as salary
    assert form_engine.resolve_salary('Expected start date', {'location': 'Remote'}, {}) is None

def test_dropdown_matching_boundary():
    # AA-06: Word boundary matching prevents 'Unknown' from matching 'no'
    assert form_engine.match_dropdown_option([{'label': 'Yes', 'value': 'yes'}, {'label': 'No', 'value': 'no'}], 'Unknown') is None

def test_contact_field_country_code_disambiguation():
    # AA-14: Disambiguate phone country code vs phone number
    profile = {'phone': '+20 100 123 4567', 'location': 'Cairo, Egypt'}
    assert form_engine.resolve_contact_field('Phone Country Code', profile) == '+20'
    assert form_engine.resolve_contact_field('Mobile Phone', profile) == '+20 100 123 4567'
    assert form_engine.answer_single_field(
        {
            'label': 'Phone Country Code', 'type': 'select',
            'options': [
                {'label': 'Egypt (+20)', 'value': 'eg'},
                {'label': 'United States (+1)', 'value': 'us'},
            ],
        },
        profile, {}, {}, {},
    ) == 'eg'


def test_copilot_keeps_browser_open_for_missing_input(client, job):
    page = MagicMock()
    page.is_closed.return_value = False
    progress = []
    message = 'Complete expected salary in the employer form.'

    result = browser._handoff_to_user(page, job['id'], message, progress.append)

    assert result == message
    assert store.get_job(job['id'])['state'] == 'needs_input'
    assert store.get_job(job['id'])['input_request'] == message
    assert progress == [f'Input needed: {message}']
    page.wait_for_event.assert_called_once_with('close', timeout=0)


def test_copilot_fills_known_contact_and_flags_unknown_required_field(client, job):
    html = '''<label for="phone">Mobile phone *</label><input id="phone" type="tel" required>
    <label for="salary">Expected salary *</label><input id="salary" required>'''
    with sync_playwright() as playwright:
        chromium = playwright.chromium.launch(headless=True)
        try:
            page = chromium.new_page()
            page.set_content(html)
            profile = {'phone': '+20 100 123 4567', 'name': 'Jane Doe'}
            unresolved = browser._fill_container_fields(page, page, profile, job, {'answers': {}}, {})
            assert page.locator('#phone').input_value() == profile['phone']
            assert 'Expected salary *' in unresolved
            assert browser._unresolved_required_fields(page, page) == ['Expected salary *']
        finally:
            chromium.close()


def test_linkedin_native_dialog_is_recognized():
    with sync_playwright() as playwright:
        chromium = playwright.chromium.launch(headless=True)
        try:
            page = chromium.new_page()
            page.set_content('<dialog open><h2>Apply to SAQAYA</h2><input required></dialog>')
            modal = page.locator(browser.EASY_APPLY_MODAL_SELECTOR).first
            assert modal.is_visible()
            assert modal.locator('h2').inner_text() == 'Apply to SAQAYA'
        finally:
            chromium.close()

def test_auto_apply_unapproved_package_rejected(client):
    # AA-02: Endpoint must reject unapproved or unreviewed packages
    job, _ = store.add_job({
        'title': 'Frontend Engineer',
        'company': 'Tech Corp',
        'location': 'Remote',
        'url': 'https://example.com/jobs/2',
        'description': 'React role with 5+ years experience needed.'
    })
    # Save unapproved package
    store.save_package(job['id'], {
        'approved': False,
        'cv_reviewed': False,
        'coverage_reviewed': False,
        'answers': {},
        'files': {}
    })
    res = client.post(f'/api/jobs/{job["id"]}/auto-apply', json={'auto_submit': False})
    assert res.status_code == 400
    assert 'must be reviewed and approved' in res.json()['detail']
