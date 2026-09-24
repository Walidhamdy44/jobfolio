import pytest
import httpx
import ssl
from datetime import datetime, timedelta, timezone
from backend import store, search, providers, worker


def test_all_providers_obey_location_date_and_title_criteria():
    now = datetime(2026, 9, 24, 12, tzinfo=timezone.utc)
    prefs = {'location': 'Cairo', 'country': 'Egypt', 'date_posted': 'past_week', 'workplace_type': 'any'}
    titles = ['Frontend Software Engineer', 'React Developer']
    item = {'job_title': 'Senior React Developer', 'location': 'Cairo, Egypt', 'posted_at': (now - timedelta(days=3)).isoformat()}

    assert search._matches_search_filters(item, prefs, titles, now)
    assert not search._matches_search_filters({**item, 'location': 'London'}, prefs, titles, now)
    assert not search._matches_search_filters({**item, 'location': 'Cairo'}, prefs, titles, now)
    assert not search._matches_search_filters({**item, 'posted_at': (now - timedelta(days=8)).isoformat()}, prefs, titles, now)
    assert not search._matches_search_filters({**item, 'posted_at': None}, prefs, titles, now)
    assert not search._matches_search_filters({**item, 'job_title': 'Office Manager'}, prefs, titles, now)
    assert not search._matches_search_filters({**item, 'location': 'Worldwide'}, prefs, titles, now)
    assert search._matches_search_filters({**item, 'location': 'Worldwide'}, {**prefs, 'remote_only': True}, titles, now)


def test_publisher_posting_dates_are_normalized():
    assert search._posting_date('Thu, 24 Sep 2026 10:00:00 +0000') == '2026-09-24T10:00:00+00:00'
    assert search._posting_date('2026-09-24T10:00:00+00:00') == '2026-09-24T10:00:00+00:00'
    assert search._posting_date('2026-09-24') == '2026-09-24T00:00:00+00:00'
    assert search._posting_date('invalid') is None


def test_feed_tls_context_keeps_certificate_and_hostname_validation():
    context = search._search_ssl_context()
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


def test_feed_connection_failures_do_not_erase_cached_jobs(client, monkeypatch):
    store.set_setting('preferences', {'confirmed': True, 'titles': ['Frontend Engineer']})
    store.set_setting('search_provider', 'free')
    old_results = {'at': 'previous-run', 'items': [{'url': 'https://example.com/job'}]}
    store.set_setting('search_results', old_results)

    def fail_get(self, url, *args, **kwargs):
        raise httpx.ConnectError('certificate validation failed')

    monkeypatch.setattr(httpx.Client, 'get', fail_get)
    with pytest.raises(ValueError, match='search sources failed'):
        search.search_jobs()
    assert store.setting('search_results') == old_results

def test_free_search_with_mocked_feeds(client, monkeypatch):
    # Set confirmed preferences
    prefs = store.setting('preferences', {})
    prefs['confirmed'] = True
    prefs['titles'] = ['Frontend Engineer', 'React Engineer']
    prefs['remote_only'] = True
    prefs['excluded_companies'] = ['BadCorp']
    prefs['excluded_keywords'] = ['intern']
    store.set_setting('preferences', prefs)
    store.set_setting('search_provider', 'free')

    class MockResponse:
        def __init__(self, json_data, status_code=200):
            self._json = json_data
            self.status_code = status_code
        def json(self):
            return self._json

    def mock_get(self, url, *args, **kwargs):
        url_str = str(url)
        if 'remotive.com' in url_str:
            return MockResponse({'jobs': [
                {'url': 'https://remotive.com/job/1', 'title': 'Frontend Engineer', 'company_name': 'GoodCorp', 'candidate_required_location': 'Worldwide', 'description': 'React remote job'},
                {'url': 'https://remotive.com/job/2', 'title': 'Frontend Intern', 'company_name': 'GoodCorp', 'candidate_required_location': 'Worldwide', 'description': 'internship'},
                {'url': 'https://remotive.com/job/3', 'title': 'Frontend Engineer', 'company_name': 'BadCorp', 'candidate_required_location': 'Worldwide', 'description': 'React remote job'}
            ]})
        elif 'jobicy.com' in url_str:
            return MockResponse({'jobs': [
                {'url': 'https://jobicy.com/job/4', 'jobTitle': 'Senior React Engineer', 'companyName': 'TechCo', 'jobGeo': 'Remote', 'jobDescription': 'Remote React and TypeScript'}
            ]})
        elif 'arbeitnow.com' in url_str:
            return MockResponse({'data': [
                {'url': 'https://arbeitnow.com/job/5', 'title': 'Frontend Developer', 'company_name': 'EuroTech', 'location': 'Berlin', 'tags': ['react', 'remote'], 'description': 'Remote frontend role'}
            ]})
        return MockResponse({}, 404)

    monkeypatch.setattr(httpx.Client, 'get', mock_get)

    msg = search.search_jobs()
    assert 'Found' in msg
    results = store.setting('search_results', {}).get('items', [])
    assert len(results) >= 2
    # Excluded company BadCorp and excluded keyword intern must be filtered out
    assert not any('badcorp' in r['title'].lower() or 'badcorp' in r['snippet'].lower() for r in results)
    assert not any('intern' in r['title'].lower() or 'intern' in r['snippet'].lower() for r in results)
    # Good matches should be present
    urls = [r['url'] for r in results]
    assert 'https://remotive.com/job/1' in urls
    assert 'https://jobicy.com/job/4' in urls

def test_search_provider_brave_requires_key(client, monkeypatch):
    prefs = store.setting('preferences', {})
    prefs['confirmed'] = True
    store.set_setting('preferences', prefs)
    store.set_setting('search_provider', 'brave')
    monkeypatch.setattr(providers, 'secret', lambda name: '')

    with pytest.raises(ValueError, match='Connect a Brave Search API key'):
        search.search_jobs()

def test_settings_provider_update(client):
    r = client.put('/api/settings', json={
        'provider': 'openrouter',
        'model': 'meta-llama/llama-3.3-70b-instruct:free',
        'search_provider': 'free',
        'api_key': 'test-openrouter-key'
    })
    assert r.status_code == 200
    bootstrap = client.get('/api/workspace').json()
    assert bootstrap['connections']['provider'] == 'openrouter'
    assert bootstrap['connections']['model'] == 'meta-llama/llama-3.3-70b-instruct:free'
    assert bootstrap['connections']['search_provider'] == 'free'
    assert bootstrap['connections']['free_search_ready'] is True

def test_providers_rate_limit_formatting(monkeypatch):
    import openai
    from pydantic import BaseModel

    class Dummy(BaseModel):
        text: str

    def mock_create(*args, **kwargs):
        raise openai.RateLimitError("Rate limit exceeded", response=httpx.Response(429, request=httpx.Request("POST", "https://api.test")), body=None)

    monkeypatch.setattr(providers, 'get_provider_config', lambda: {
        'provider': 'openrouter',
        'key': 'test-key',
        'base_url': 'https://openrouter.ai/api/v1',
        'model': 'meta-llama/llama-3.3-70b-instruct:free',
        'connected': True,
        'secret_name': 'OPENROUTER_API_KEY'
    })
    client_instance = openai.OpenAI(api_key="test-key")
    monkeypatch.setattr(client_instance.chat.completions, 'create', mock_create)
    monkeypatch.setattr(openai, 'OpenAI', lambda **kwargs: client_instance)

    with pytest.raises(ValueError, match='Free model quota or rate limit reached'):
        providers.ask(Dummy, "instruction", {})


def test_invalid_ai_key_has_actionable_error(monkeypatch):
    import openai
    from unittest.mock import MagicMock
    from pydantic import BaseModel

    class Dummy(BaseModel):
        answer: str

    monkeypatch.setattr(providers, 'get_provider_config', lambda: {
        'provider': 'openrouter', 'key': 'invalid-test-key',
        'base_url': 'https://openrouter.ai/api/v1', 'model': 'openrouter/free',
    })
    client = MagicMock()
    response = httpx.Response(401, request=httpx.Request('POST', 'https://openrouter.ai/api/v1/chat/completions'))
    client.chat.completions.create.side_effect = openai.AuthenticationError('User not found.', response=response, body=None)
    monkeypatch.setattr(openai, 'OpenAI', lambda **kwargs: client)

    with pytest.raises(ValueError, match='Replace it in Connections, or use local CV preparation'):
        providers.ask(Dummy, 'Return JSON.', {'test': 'synthetic'})

def test_search_preferences_sync_and_ranking(client, monkeypatch):
    """Test instant sync of preferences on search request and score ranking."""
    class MockResponse:
        def __init__(self, json_data, status_code=200):
            self._json = json_data
            self.status_code = status_code
        def json(self):
            return self._json

    def mock_get(self, url, *args, **kwargs):
        url_str = str(url)
        if 'remotive.com' in url_str:
            return MockResponse({'jobs': [
                {'url': 'https://remotive.com/job/10', 'title': 'Lead Frontend Engineer', 'company_name': 'ScaleCo', 'candidate_required_location': 'Worldwide', 'description': 'React TypeScript Senior role'},
                {'url': 'https://remotive.com/job/11', 'title': 'Junior Content Writer', 'company_name': 'WriteCo', 'candidate_required_location': 'Worldwide', 'description': 'Writing tasks'}
            ]})
        elif 'jobicy.com' in url_str:
            return MockResponse({'jobs': [
                {'url': 'https://jobicy.com/job/20', 'jobTitle': 'Senior Frontend Developer', 'companyName': 'DevCorp', 'jobGeo': 'Remote', 'jobDescription': 'React Redux Next.js frontend'}
            ]})
        elif 'arbeitnow.com' in url_str:
            return MockResponse({'data': []})
        return MockResponse({}, 404)

    monkeypatch.setattr(httpx.Client, 'get', mock_get)
    monkeypatch.setattr(worker, 'enqueue', lambda kind, target, fn: 'mock-search-run')

    new_prefs = {
        'titles': ['Senior Frontend Developer'],
        'location': 'Egypt',
        'remote_only': True,
        'excluded_companies': [],
        'excluded_keywords': [],
        'salary_note': '',
        'work_authorization': '',
        'confirmed': True
    }

    res = client.post('/api/search', json={'preferences': new_prefs})
    assert res.status_code == 200

    # Verify preferences were immediately synced to DB
    saved = store.setting('preferences')
    assert saved['titles'] == ['Senior Frontend Developer']
    assert saved['confirmed'] is True

    # Run search synchronously to verify scoring and ranking
    search.search_jobs()
    results = store.setting('search_results', {}).get('items', [])
    assert len(results) >= 2
    # Ensure items have score and are sorted descending
    for r in results:
        assert 'score' in r
    scores = [r['score'] for r in results]
    assert scores == sorted(scores, reverse=True)

def test_linkedin_guest_search_and_import(monkeypatch):
    """Test that LinkedIn guest search parses cards and import_url extracts LinkedIn jobs."""
    from backend import network

    html_search_sample = """
    <ul>
      <li>
        <a class="base-card__full-link" href="https://eg.linkedin.com/jobs/view/senior-react-dev-12345678"></a>
        <h3 class="base-search-card__title">Senior React Developer</h3>
        <h4 class="base-search-card__subtitle">Acme Egypt</h4>
        <span class="job-search-card__location">Cairo, Egypt</span>
      </li>
    </ul>
    """
    html_job_sample = """
    <div>
      <h1 class="top-card-layout__title">Senior React Developer</h1>
      <a class="topcard__org-name-link">Acme Egypt</a>
      <span class="topcard__flavor--bullet">Cairo, Egypt</span>
      <div class="show-more-less-html__markup">
        <p>We are seeking a Senior React Developer with 5+ years experience in TypeScript and Next.js.</p>
      </div>
    </div>
    """

    class MockResponse:
        def __init__(self, text, status_code=200):
            self.text = text
            self.status_code = status_code

    def mock_get(self, url, *args, **kwargs):
        url_str = str(url)
        if 'seeMoreJobPostings' in url_str:
            return MockResponse(html_search_sample)
        elif 'jobPosting' in url_str:
            return MockResponse(html_job_sample)
        return MockResponse('', 404)

    import socket
    monkeypatch.setattr(socket, 'getaddrinfo', lambda host, port, *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 443))])
    monkeypatch.setattr(httpx.Client, 'get', mock_get)

    with httpx.Client() as client:
        results = search._search_linkedin(client, ['Senior React Developer'], {'location': 'Cairo, Egypt', 'remote_only': False})
        assert len(results) == 1
        assert results[0]['job_title'] == 'Senior React Developer'
        assert results[0]['company'] == 'Acme Egypt'
        assert results[0]['location'] == 'Cairo, Egypt'
        assert results[0]['platform'] == 'linkedin'
        assert results[0]['source'] == 'LinkedIn Jobs'

    # Test import_url on a LinkedIn URL
    imported = network.import_url('https://eg.linkedin.com/jobs/view/senior-react-dev-12345678')
    assert imported['title'] == 'Senior React Developer'
    assert imported['company'] == 'Acme Egypt'
    assert imported['location'] == 'Cairo, Egypt'
    assert imported['platform'] == 'linkedin'
    assert 'TypeScript and Next.js' in imported['description']

def test_serper_google_jobs_search(monkeypatch):
    """Test Serper Google Jobs API parsing."""
    sample_serper_response = {
        'jobs': [
            {
                'title': 'Staff Frontend Engineer',
                'companyName': 'GlobalTech',
                'location': 'Cairo, Egypt',
                'description': 'Building next-gen web platforms in React and TypeScript.',
                'via': 'via LinkedIn',
                'link': 'https://example.com/apply/1'
            }
        ]
    }

    class MockResponse:
        def __init__(self, json_data, status_code=200):
            self._json = json_data
            self.status_code = status_code
        def json(self):
            return self._json

    def mock_post(self, url, *args, **kwargs):
        return MockResponse(sample_serper_response)

    monkeypatch.setattr(httpx.Client, 'post', mock_post)

    results = search._search_serper_google_jobs('mock-serper-key', ['Staff Frontend Engineer'], {'location': 'Cairo, Egypt'})
    assert len(results) == 1
    assert results[0]['title'] == 'Staff Frontend Engineer at GlobalTech'
    assert results[0]['company'] == 'GlobalTech'
    assert results[0]['platform'] == 'google'
    assert 'Google Jobs (via LinkedIn)' in results[0]['source']
    assert 'React and TypeScript' in results[0]['description']

def test_settings_serper_provider(client, monkeypatch):
    """Test configuring serper provider in Settings."""
    secrets_store = {}
    monkeypatch.setattr(providers, 'save_secret', lambda name, val: secrets_store.update({name: val}))
    monkeypatch.setattr(providers, 'secret', lambda name: secrets_store.get(name, ''))

    r = client.put('/api/settings', json={
        'provider': 'openrouter',
        'model': 'meta-llama/llama-3.3-70b-instruct:free',
        'search_provider': 'serper',
        'serper_key': 'test-serper-key-123'
    })
    assert r.status_code == 200
    bootstrap = client.get('/api/workspace').json()
    assert bootstrap['connections']['search_provider'] == 'serper'
    assert bootstrap['connections']['serper'] is True

def test_linkedin_search_filters_mapping(monkeypatch):
    """Test that LinkedIn search maps date_posted, experience_level, job_type, workplace_type, and country."""
    captured_requests = []

    class MockResponse:
        def __init__(self, text="", status_code=200):
            self.text = text
            self.status_code = status_code

    def mock_get(self, url, *args, **kwargs):
        captured_requests.append({
            'url': str(url),
            'params': kwargs.get('params', {})
        })
        return MockResponse("<ul></ul>")

    monkeypatch.setattr(httpx.Client, 'get', mock_get)

    prefs = {
        'location': 'Cairo',
        'country': 'Egypt',
        'date_posted': 'past_week',
        'experience_level': 'senior',
        'job_type': 'full_time',
        'workplace_type': 'remote',
        'remote_only': True
    }

    with httpx.Client() as client:
        search._search_linkedin(client, ['Senior Frontend Developer'], prefs)

    assert len(captured_requests) > 0
    req_params = captured_requests[0]['params']
    assert req_params['keywords'] == 'Senior Frontend Developer'
    assert 'Cairo, Egypt' in req_params['location']
    assert req_params['f_TPR'] == 'r604800'
    assert req_params['f_E'] == '4,5'
    assert req_params['f_JT'] == 'F'
    assert req_params['f_WT'] == '2'

def test_score_candidate_experience_adjustments():
    """Test that candidate scoring properly adjusts based on experience_level preferences."""
    senior_item = {
        'job_title': 'Senior Frontend Developer',
        'raw_text': 'senior frontend developer react typescript'
    }
    junior_item = {
        'job_title': 'Junior Frontend Developer',
        'raw_text': 'junior intern frontend developer react'
    }

    senior_prefs = {'experience_level': 'senior'}
    entry_prefs = {'experience_level': 'entry'}

    # With senior preference:
    senior_score = search.score_candidate(senior_item, ['Frontend Developer'], '', False, prefs=senior_prefs)
    junior_score_with_senior_pref = search.score_candidate(junior_item, ['Frontend Developer'], '', False, prefs=senior_prefs)
    assert senior_score > junior_score_with_senior_pref

    # With entry level preference:
    junior_score_with_entry_pref = search.score_candidate(junior_item, ['Frontend Developer'], '', False, prefs=entry_prefs)
    senior_score_with_entry_pref = search.score_candidate(senior_item, ['Frontend Developer'], '', False, prefs=entry_prefs)
    assert junior_score_with_entry_pref > senior_score_with_entry_pref

def test_search_preferences_advanced_filters_persistence(client):
    """Test saving and loading advanced search filters via the API."""
    advanced_prefs = {
        'titles': ['Senior React Developer'],
        'location': 'Cairo',
        'country': 'Egypt',
        'date_posted': 'past_week',
        'experience_level': 'senior',
        'job_type': 'full_time',
        'workplace_type': 'remote',
        'remote_only': True,
        'excluded_companies': ['BadOrg'],
        'excluded_keywords': ['crypto'],
        'salary_note': '$80k+',
        'work_authorization': 'Citizen',
        'confirmed': True
    }

    res = client.put('/api/preferences', json=advanced_prefs)
    assert res.status_code == 200

    bootstrap = client.get('/api/workspace').json()
    saved = bootstrap['preferences']
    assert saved['country'] == 'Egypt'
    assert saved['location'] == 'Cairo'
    assert saved['date_posted'] == 'past_week'
    assert saved['experience_level'] == 'senior'
    assert saved['job_type'] == 'full_time'
    assert saved['workplace_type'] == 'remote'
    assert saved['remote_only'] is True
