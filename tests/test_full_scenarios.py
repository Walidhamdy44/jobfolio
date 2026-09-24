import copy
import hashlib
import time
import pytest
from backend import store, profile, tailoring, browser, network, providers, worker
from backend.documents import verify_files
from pypdf import PdfReader
from docx import Document

def prepare_local(job_id):
    tailoring.prepare(job_id, 'local')
    return store.get_package(job_id)

def review_package(client, job_id, pkg):
    return client.put(
        f"/api/jobs/{job_id}/review",
        json={
            'package_hash': pkg['hash'],
            'cv_reviewed': True,
            'coverage_reviewed': True,
            'answers': pkg.get('answers', {}),
            'supports': [r['support'] for r in pkg['requirements']]
        }
    )

def test_scenario_1_profile_lifecycle(client):
    """Scenario 1: Profile import, validation, editing, and master CV export."""
    bootstrap = client.get('/api/bootstrap').json()
    prof = bootstrap['profile']
    assert prof['name'] == 'Walid Hamdy'
    assert prof['email'] == 'walidhamdy314@gmail.com'
    assert len(prof['sections']) >= 3

    # Duplicate evidence ID must be rejected
    prof_invalid = copy.deepcopy(prof)
    del prof_invalid['source_file']
    del prof_invalid['revision']
    prof_invalid['sections'][0]['items'].append(prof_invalid['sections'][0]['items'][0])
    res = client.put('/api/profile', json=prof_invalid)
    assert res.status_code == 400
    assert 'unique' in res.json()['detail'].lower()

    # Valid edit increments revision
    prof_valid = copy.deepcopy(prof)
    del prof_valid['source_file']
    del prof_valid['revision']
    prof_valid['headline'] = 'Senior Full Stack & AI Systems Engineer'
    res = client.put('/api/profile', json=prof_valid)
    assert res.status_code == 200
    updated = client.get('/api/bootstrap').json()['profile']
    assert updated['headline'] == 'Senior Full Stack & AI Systems Engineer'
    assert updated['revision'] > prof['revision']

    # Master CV export must be accessible
    res_cv = client.get('/api/master-cv')
    assert res_cv.status_code == 200

def test_scenario_2_preferences_and_exclusions(client):
    """Scenario 2: Preferences update, deal-breaker validation, and exclusion filtering."""
    # Target titles cannot be empty
    res = client.put('/api/preferences', json={
        'titles': ['   '],
        'location': 'Remote',
        'remote_only': True,
        'excluded_companies': [],
        'excluded_keywords': [],
        'salary_note': '',
        'work_authorization': '',
        'confirmed': True
    })
    assert res.status_code == 400

    # Valid preferences
    res = client.put('/api/preferences', json={
        'titles': ['Frontend Engineer', 'Full Stack Developer'],
        'location': 'Egypt',
        'remote_only': True,
        'excluded_companies': ['SpamInc'],
        'excluded_keywords': ['crypto', 'web3'],
        'salary_note': '$80k+/yr',
        'work_authorization': 'Citizen',
        'confirmed': True
    })
    assert res.status_code == 200
    prefs = client.get('/api/bootstrap').json()['preferences']
    assert prefs['confirmed'] is True
    assert 'Frontend Engineer' in prefs['titles']

    # Test exclusion notes calculation
    job_data = {
        'title': 'Frontend Engineer',
        'company': 'SpamInc',
        'location': 'Remote',
        'description': 'Working with crypto assets'
    }
    notes = tailoring.store.setting('preferences')
    from backend.search import filter_notes
    calc_notes = filter_notes(job_data)
    assert any('SpamInc' in n for n in calc_notes)
    assert any('crypto' in n for n in calc_notes)

def test_scenario_3_job_ingestion_and_deduplication(client, monkeypatch):
    """Scenario 3: Job addition, deduplication, and skip action."""
    monkeypatch.setattr(network, 'public_url', lambda u: u)
    job_payload = {
        'title': 'Senior TypeScript Architect',
        'company': 'TechForward',
        'location': 'Remote',
        'url': 'https://jobs.lever.co/techforward/job123?ref=linkedin',
        'description': 'Building scalable modern web applications with React and TypeScript.'
    }
    res = client.post('/api/jobs', json=job_payload)
    assert res.status_code == 200
    data = res.json()
    assert data['created'] is True
    job_id = data['job']['id']

    # Duplicate submission of same URL should not create duplicate
    res_dup = client.post('/api/jobs', json=job_payload)
    assert res_dup.status_code == 200
    assert res_dup.json()['created'] is False

    # Skip job
    res_skip = client.post(f"/api/jobs/{job_id}/skip")
    assert res_skip.status_code == 200
    assert client.get(f"/api/jobs/{job_id}").json()['job']['state'] == 'skipped'

def test_scenario_4_truth_guarded_tailoring_and_cover_letter(client, job):
    """Scenario 4: Conservative tailoring, requirement weighting, and cover letter generation."""
    pkg = prepare_local(job['id'])
    assert pkg['mode'] == 'local'
    assert pkg['score'] <= 60
    assert pkg['cv_reviewed'] is False

    # Verify requirements have required weight=3, preferred weight=1
    for r in pkg['requirements']:
        if r['priority'] == 'required':
            assert r['weight'] == 3
        else:
            assert r['weight'] == 1

    # Numeric rewrite guard prevents fabricating figures
    assert not tailoring.guard_rewrite('Managed 2 servers.', 'Managed 20 servers.')
    assert tailoring.guard_rewrite('Reduced latency by 15%', 'Latency dropped by 15%')

    # Cover letter drafting
    tailoring.cover_letter(job['id'], 'local')
    pkg_updated = store.get_package(job['id'])
    assert 'cover_letter' in pkg_updated
    assert job['company'] in pkg_updated['cover_letter']
    assert 'cover_letter_pdf' in pkg_updated['files']
    assert 'cover_letter_docx' in pkg_updated['files']

    # Cover letter download
    res_pdf = client.get(f"/api/jobs/{job['id']}/documents/cover_letter_pdf")
    assert res_pdf.status_code == 200

def test_scenario_5_document_generation_and_tampering_check(client, job):
    """Scenario 5: Document generation, hashing, and anti-tampering verification."""
    pkg = prepare_local(job['id'])
    pdf_path = store.DATA / pkg['files']['pdf']['path']
    docx_path = store.DATA / pkg['files']['docx']['path']
    assert pdf_path.exists()
    assert docx_path.exists()

    # Tampering test: modify disk file -> verify_files fails
    original_bytes = pdf_path.read_bytes()
    pdf_path.write_bytes(original_bytes + b'\x00--tampered')
    try:
        with pytest.raises(ValueError, match='changed after preparation'):
            verify_files(pkg)
    finally:
        pdf_path.write_bytes(original_bytes)

    # Clean verification passes
    verify_files(pkg)

def test_scenario_6_review_and_approval_gates(client, job):
    """Scenario 6: Review, hash verification, approval gates, and revision conflicts."""
    pkg = prepare_local(job['id'])

    # Approve without review must fail
    res = client.post(f"/api/jobs/{job['id']}/approve", json={'package_hash': pkg['hash']})
    assert res.status_code == 400
    assert 'review' in res.json()['detail'].lower()

    # Reviewing with invalid hash must fail with 409
    res_wrong_hash = client.put(
        f"/api/jobs/{job['id']}/review",
        json={
            'package_hash': 'invalid-hash-value',
            'cv_reviewed': True,
            'coverage_reviewed': True,
            'answers': {},
            'supports': [r['support'] for r in pkg['requirements']]
        }
    )
    assert res_wrong_hash.status_code == 409

    # Valid review
    res_rev = review_package(client, job['id'], pkg)
    assert res_rev.status_code == 200
    current_pkg = store.get_package(job['id'])

    # Approve with current hash succeeds
    res_appr = client.post(f"/api/jobs/{job['id']}/approve", json={'package_hash': current_pkg['hash']})
    assert res_appr.status_code == 200
    assert store.get_package(job['id'])['approved'] is True
    assert store.get_job(job['id'])['state'] == 'approved'

def test_scenario_7_provider_configuration_and_switching(client):
    """Scenario 7: Multi-provider switching and error reporting."""
    providers_to_test = [
        ('openrouter', 'openrouter/free', 'https://openrouter.ai/api/v1/'),
        ('tokenrouter', 'z-ai/glm-5.3-free', 'https://api.tokenrouter.io/v1'),
        ('opencode', 'opencode/free', 'https://api.opencode.ai/v1'),
        ('custom', 'llama3.2', 'http://localhost:11434/v1')
    ]

    for p, m, u in providers_to_test:
        res = client.put('/api/settings', json={
            'provider': p,
            'model': m,
            'base_url': u,
            'search_provider': 'free'
        })
        assert res.status_code == 200
        cfg = providers.get_provider_config()
        assert cfg['provider'] == p
        assert cfg['model'] == m
        # Trailing slash must be cleanly normalized
        assert not cfg['base_url'].endswith('/')

def test_scenario_8_browser_form_inspection_and_safety(client, job, monkeypatch):
    """Scenario 8: Form inspection, answer mapping, and safe execution."""
    prepare_local(job['id'])
    monkeypatch.setattr(browser, 'application_url', lambda j: 'https://jobs.lever.co/test/role')

    html_fixture = '''<!doctype html>
    <form>
      <label for="name">Full name *</label><input id="name" required>
      <label for="email">Email *</label><input id="email" type="email" required>
      <label for="resume">Resume *</label><input id="resume" type="file" required>
      <button type="submit">Submit application</button>
    </form>
    '''

    def mock_open_page(b, url):
        ctx = b.new_context()
        page = ctx.new_page()
        page.set_content(html_fixture)
        return ctx, page

    monkeypatch.setattr(browser, 'open_page', mock_open_page)
    browser.inspect(job['id'])

    pkg = store.get_package(job['id'])
    assert pkg['form'] is not None
    assert len(pkg['form']['fields']) == 3
    # Known profile values auto-filled
    assert pkg['answers']['#name'] == 'Walid Hamdy'
    assert pkg['answers']['#email'] == 'walidhamdy314@gmail.com'

def test_scenario_9_security_sandbox_and_isolation(client):
    """Scenario 9: Loopback security, CSRF headers, and URL validation."""
    # Private / internal URLs must be blocked
    for bad_url in ['http://169.254.169.254/latest/meta-data', 'http://127.0.0.1:8080', 'http://localhost:3000']:
        with pytest.raises(ValueError):
            network.public_url(bad_url)

    # Disallowed origin on mutating requests must be rejected (403)
    res_csrf = client.post('/api/search', headers={'Origin': 'https://malicious-site.com'})
    assert res_csrf.status_code == 403

    # Missing x-job-agent header on mutating requests must be rejected
    res_no_agent = client.post('/api/search', headers={'x-job-agent': 'unauthorized'})
    assert res_no_agent.status_code == 403

def test_scenario_10_profile_cv_structuring(client):
    """Scenario 10: AI and local CV review & structuring before profile confirmation."""
    # Test local structuring
    res_local = client.post('/api/profile/structure', json={'mode': 'local'})
    assert res_local.status_code == 200
    data_local = res_local.json()
    assert data_local['ok'] is True
    prof_local = data_local['profile']
    assert prof_local['name'] == 'Walid Hamdy'
    assert len(prof_local['sections']) >= 3
    for s in prof_local['sections']:
        assert 'title' in s
        assert len(s['items']) > 0
        for itm in s['items']:
            assert itm['text'].strip() != ''

    # Test AI structuring with mock provider response
    mock_struct = providers.StructuredProfile(
        name='Walid Hamdy',
        headline='Senior Frontend Engineer | React & AI',
        email='walidhamdy314@gmail.com',
        phone='+20 100 000 0000',
        location='Cairo, Egypt',
        links=['https://github.com/walidhamdy'],
        sections=[
            providers.StructuredSection(
                title='Summary',
                items=['Senior Frontend Engineer with 5+ years building scalable React & Next.js applications.']
            ),
            providers.StructuredSection(
                title='Technical Skills',
                items=['Languages: JavaScript, TypeScript', 'Frameworks: React, Next.js, Redux']
            ),
            providers.StructuredSection(
                title='Professional Experience',
                items=['Front-End Developer at Tech Corp (2022 - Present): Led migration to Next.js reducing bundle size by 35%.']
            )
        ]
    )

    import unittest.mock as mock
    with mock.patch.object(providers, 'ask', return_value=mock_struct):
        with mock.patch.object(providers, 'get_provider_config', return_value={'connected': True, 'provider': 'openrouter', 'model': 'openrouter/free', 'base_url': 'https://openrouter.ai/api/v1'}):
            res_ai = client.post('/api/profile/structure', json={'mode': 'ai'})
            assert res_ai.status_code == 200
            data_ai = res_ai.json()
            assert data_ai['ok'] is True
            prof_ai = data_ai['profile']
            assert prof_ai['name'] == 'Walid Hamdy'
            assert len(prof_ai['sections']) == 3
            assert prof_ai['sections'][0]['title'] == 'Summary'
            assert 'bundle size' in prof_ai['sections'][2]['items'][0]['text']

            # Verify this structured profile can be confirmed and saved
            save_payload = {
                'name': prof_ai['name'],
                'headline': prof_ai['headline'],
                'email': prof_ai['email'],
                'phone': prof_ai['phone'],
                'location': prof_ai['location'],
                'links': prof_ai['links'],
                'sections': prof_ai['sections']
            }
            res_save = client.put('/api/profile', json=save_payload)
            assert res_save.status_code == 200
            updated = client.get('/api/bootstrap').json()['profile']
            assert updated['headline'] == 'Senior Frontend Engineer | React & AI'
