import html
import re
import ssl
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from bs4 import BeautifulSoup
import httpx
from . import store, providers, network

COMMON_TECH_SKILLS = [
    'react', 'next.js', 'nextjs', 'typescript', 'javascript', 'vue', 'angular',
    'tailwind', 'css', 'html', 'node', 'nodejs', 'frontend', 'front-end',
    'redux', 'graphql', 'rest', 'webpack', 'vite', 'ui', 'ux', 'web'
]


def _search_ssl_context() -> ssl.SSLContext:
    """Use the OS trust store for feed HTTPS requests on Windows.

    Python 3.14 enables OpenSSL's strict X.509 checks by default. Some CAs
    trusted by the Windows store have non-critical Basic Constraints; those
    chains fail strict validation even though trust and hostname checks pass.
    Keep certificate verification and hostname matching enabled.
    """
    context = ssl.create_default_context()
    if sys.platform == 'win32':
        context.verify_flags &= ~ssl.VERIFY_X509_STRICT
    return context


def _feed_issue(issues: list[str] | None, source: str, reason: str) -> None:
    if issues is not None:
        issues.append(f'{source}: {reason}')


def _posting_date(value: object) -> str | None:
    """Normalize a publisher's posting timestamp to UTC, or leave it unknown."""
    if value is None or value == '':
        return None
    try:
        if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
            posted = datetime.fromtimestamp(int(value), timezone.utc)
        elif isinstance(value, str):
            try:
                posted = datetime.fromisoformat(value.strip().replace('Z', '+00:00'))
            except ValueError:
                posted = parsedate_to_datetime(value)
        else:
            return None
        if posted.tzinfo is None:
            posted = posted.replace(tzinfo=timezone.utc)
        return posted.astimezone(timezone.utc).isoformat()
    except (ValueError, TypeError, OverflowError):
        return None


def _title_matches(title: str, targets: list[str]) -> bool:
    """Require a target specialty in the job title, not just its description."""
    def tokens(value: str) -> set[str]:
        value = re.sub(r'full[\s-]?stack', 'fullstack', value.casefold())
        value = re.sub(r'front[\s-]?end', 'frontend', value)
        value = re.sub(r'next[\s.]?js', 'nextjs', value)
        return set(re.findall(r'[a-z0-9]+', value))

    title_words = tokens(title)
    occupation = {'engineer', 'engineering', 'developer', 'development', 'programmer', 'scientist', 'analyst', 'architect', 'designer', 'manager'}
    if not title_words & occupation:
        return False
    generic = occupation | {'software', 'senior', 'junior', 'lead', 'staff', 'full', 'time', 'web'}
    specialties = set().union(*(tokens(target) - generic for target in targets)) if targets else set()
    if specialties and title_words & specialties:
        return True
    return 'web' in title_words and any('web' in tokens(target) for target in targets)


def _matches_search_filters(item: dict, prefs: dict, targets: list[str], now: datetime) -> bool:
    if not _title_matches(item.get('job_title') or item.get('title', ''), targets):
        return False

    city = prefs.get('location', '').strip().casefold()
    country = prefs.get('country', '').strip().casefold()
    location = ' '.join((item.get('location') or '').casefold().split())
    remote_search = prefs.get('remote_only') or prefs.get('workplace_type') == 'remote'
    worldwide = location in {'remote', 'worldwide', 'anywhere', 'anywhere in the world', 'global'}
    if not (remote_search and worldwide):
        if city and city not in location:
            return False
        if country and country not in location:
            return False

    max_age = {'past_24h': timedelta(days=1), 'past_week': timedelta(days=7), 'past_month': timedelta(days=30)}.get(prefs.get('date_posted'))
    if max_age:
        posted_at = item.get('posted_at')
        if not posted_at:
            return False
        try:
            posted = datetime.fromisoformat(posted_at)
        except (ValueError, TypeError):
            return False
        if not now - max_age <= posted <= now:
            return False
    return True

def clean_html_text(html_or_text: str) -> str:
    if not html_or_text:
        return ''
    unescaped = html.unescape(html_or_text)
    if '<' in unescaped and '>' in unescaped:
        soup = BeautifulSoup(unescaped, 'html.parser')
        for tag in soup(['script', 'style', 'nav', 'footer', 'noscript']):
            tag.decompose()
        text = soup.get_text(' ', strip=True)
    else:
        text = unescaped
    text = html.unescape(text)
    text = text.replace('\xa0', ' ')
    return ' '.join(text.split())

def _extract_text_content(html_or_text: str) -> str:
    return clean_html_text(html_or_text)

def _search_weworkremotely(client: httpx.Client, titles: list[str], prefs: dict, issues: list[str] | None = None) -> list[dict]:
    results = []
    feeds = [
        'https://weworkremotely.com/categories/remote-front-end-programming-jobs.rss',
        'https://weworkremotely.com/categories/remote-programming-jobs.rss'
    ]
    for feed_url in feeds:
        try:
            r = client.get(feed_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            if r.status_code != 200:
                _feed_issue(issues, 'WeWorkRemotely', f'HTTP {r.status_code}')
                continue
            root = ET.fromstring(r.content)
            for it in root.findall('.//item'):
                link = it.find('link').text if it.find('link') is not None else ''
                if not link or not link.startswith('https://'):
                    continue
                raw_title = it.find('title').text if it.find('title') is not None else ''
                cleaned_title = clean_html_text(raw_title)
                company = clean_html_text(cleaned_title.split(':', 1)[0].strip()) if ':' in cleaned_title else 'Remote Tech'
                job_title = clean_html_text(cleaned_title.split(':', 1)[1].strip()) if ':' in cleaned_title else cleaned_title
                region = clean_html_text(it.findtext('region') or 'Remote')
                posted_at = _posting_date(it.findtext('pubDate'))
                desc_elem = it.find('description')
                raw_desc = desc_elem.text if desc_elem is not None else ''
                plain_desc = clean_html_text(raw_desc)
                snippet = f"{company} · Remote · {plain_desc[:220]}"
                results.append({
                    'url': link.strip(),
                    'title': f"{job_title} at {company}",
                    'job_title': job_title,
                    'company': company,
                    'location': region,
                    'posted_at': posted_at,
                    'snippet': snippet,
                    'description': plain_desc,
                    'platform': 'weworkremotely',
                    'source': 'WeWorkRemotely feed',
                    'raw_text': f"{job_title} {company} remote worldwide {plain_desc}".casefold()
                })
        except Exception as exc:
            _feed_issue(issues, 'WeWorkRemotely', type(exc).__name__)
    return results

def _search_remotive(client: httpx.Client, query: str, prefs: dict, issues: list[str] | None = None) -> list[dict]:
    results = []
    try:
        search_kw = 'frontend' if any(w in query.lower() for w in ['front', 'react', 'ui', 'web']) else query.split()[-1]
        r = client.get('https://remotive.com/api/remote-jobs', params={'category': 'software-dev', 'search': search_kw, 'limit': 25}, headers={'User-Agent': 'Jobfolio/1.0'})
        if r.status_code == 200:
            data = r.json()
            for item in data.get('jobs', []):
                url = item.get('url', '')
                if not url.startswith('https://'):
                    continue
                title = clean_html_text(item.get('title', ''))
                company = clean_html_text(item.get('company_name', ''))
                location = clean_html_text(item.get('candidate_required_location', 'Worldwide'))
                posted_at = _posting_date(item.get('publication_date'))
                desc = clean_html_text(item.get('description', ''))
                snippet = f"{company} · {location} · {desc[:220]}"
                results.append({
                    'url': url,
                    'title': f"{title} at {company}",
                    'job_title': title,
                    'company': company,
                    'location': location,
                    'posted_at': posted_at,
                    'description': desc,
                    'snippet': snippet,
                    'platform': 'remotive',
                    'source': 'Remotive feed',
                    'raw_text': f"{title} {company} {location} {desc}".casefold()
                })
        else:
            _feed_issue(issues, 'Remotive', f'HTTP {r.status_code}')
    except Exception as exc:
        _feed_issue(issues, 'Remotive', type(exc).__name__)
    return results

def _search_jobicy(client: httpx.Client, query: str, prefs: dict, issues: list[str] | None = None) -> list[dict]:
    results = []
    q_lower = query.lower()
    if 'front' in q_lower or 'react' in q_lower or 'ui' in q_lower:
        tag = 'frontend'
    elif 'full' in q_lower or 'node' in q_lower or 'back' in q_lower:
        tag = 'fullstack'
    elif 'dev' in q_lower or 'engineer' in q_lower or 'software' in q_lower:
        tag = 'dev'
    else:
        tag = 'dev'

    try:
        r = client.get('https://jobicy.com/api/v2/remote-jobs', params={'count': 25, 'tag': tag}, headers={'User-Agent': 'Jobfolio/1.0'})
        if r.status_code == 200:
            data = r.json()
            for item in data.get('jobs', []):
                url = item.get('url', '')
                if not url.startswith('https://'):
                    continue
                title = clean_html_text(item.get('jobTitle', ''))
                company = clean_html_text(item.get('companyName', ''))
                location = clean_html_text(item.get('jobGeo', 'Remote'))
                posted_at = _posting_date(item.get('pubDate'))
                desc = clean_html_text(item.get('jobDescription', ''))
                snippet = f"{company} · {location} · {desc[:220]}"
                results.append({
                    'url': url,
                    'title': f"{title} at {company}",
                    'job_title': title,
                    'company': company,
                    'location': location,
                    'posted_at': posted_at,
                    'description': desc,
                    'snippet': snippet,
                    'platform': 'jobicy',
                    'source': 'Jobicy feed',
                    'raw_text': f"{title} {company} {location} {desc}".casefold()
                })
        else:
            _feed_issue(issues, 'Jobicy', f'HTTP {r.status_code}')
    except Exception as exc:
        _feed_issue(issues, 'Jobicy', type(exc).__name__)
    return results

def _search_arbeitnow(client: httpx.Client, query: str, prefs: dict, issues: list[str] | None = None) -> list[dict]:
    results = []
    try:
        r = client.get('https://www.arbeitnow.com/api/job-board-api', headers={'User-Agent': 'Jobfolio/1.0'})
        if r.status_code == 200:
            data = r.json()
            terms = [q.casefold() for q in query.split() if len(q) > 2]
            for item in data.get('data', []):
                url = item.get('url', '')
                if not url.startswith('https://'):
                    continue
                title = clean_html_text(item.get('title', ''))
                company = clean_html_text(item.get('company_name', ''))
                location = clean_html_text(item.get('location', ''))
                posted_at = _posting_date(item.get('created_at'))
                tags = ' '.join(item.get('tags', []))
                desc = clean_html_text(item.get('description', ''))
                combined = f"{title} {company} {location} {tags} {desc}".casefold()
                if terms and not any(t in combined for t in terms):
                    continue
                snippet = f"{company} · {location or 'Remote'} · {desc[:220]}"
                results.append({
                    'url': url,
                    'title': f"{title} at {company}",
                    'job_title': title,
                    'company': company,
                    'location': location or 'Remote',
                    'posted_at': posted_at,
                    'description': desc,
                    'snippet': snippet,
                    'platform': 'arbeitnow',
                    'source': 'Arbeitnow feed',
                    'raw_text': combined
                })
        else:
            _feed_issue(issues, 'Arbeitnow', f'HTTP {r.status_code}')
    except Exception as exc:
        _feed_issue(issues, 'Arbeitnow', type(exc).__name__)
    return results

def _search_linkedin(client: httpx.Client, titles: list[str], prefs: dict, issues: list[str] | None = None) -> list[dict]:
    results = []
    city = prefs.get('location', '').strip()
    country = prefs.get('country', '').strip()
    remote_only = prefs.get('remote_only', False)
    workplace_type = prefs.get('workplace_type', 'any')

    loc_parts = [p for p in (city, country) if p]
    target_loc = ', '.join(loc_parts)

    search_locations = []
    if target_loc:
        search_locations.append(target_loc)
    elif country:
        search_locations.append(country)
    elif city:
        search_locations.append(city)

    if (remote_only or workplace_type == 'remote' or not search_locations) and 'Worldwide' not in search_locations:
        search_locations.append('Worldwide')

    # LinkedIn filter parameter mappings
    date_posted = prefs.get('date_posted', 'any')
    tpr_map = {
        'past_24h': 'r86400',
        'past_week': 'r604800',
        'past_month': 'r2592000'
    }

    exp_level = prefs.get('experience_level', 'any')
    exp_map = {
        'entry': '2',
        'mid': '3,4',
        'senior': '4,5'
    }

    job_type = prefs.get('job_type', 'any')
    jt_map = {
        'full_time': 'F',
        'contract': 'C',
        'part_time': 'P'
    }

    wt_map = {
        'on_site': '1',
        'remote': '2',
        'hybrid': '3'
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }

    seen_urls = set()
    for title in titles:
        for loc in search_locations[:2]:
            try:
                params = {
                    'keywords': title,
                    'location': loc,
                    'start': 0
                }
                if date_posted in tpr_map:
                    params['f_TPR'] = tpr_map[date_posted]
                if exp_level in exp_map:
                    params['f_E'] = exp_map[exp_level]
                if job_type in jt_map:
                    params['f_JT'] = jt_map[job_type]
                if workplace_type in wt_map:
                    params['f_WT'] = wt_map[workplace_type]
                elif remote_only:
                    params['f_WT'] = '2'

                r = client.get(
                    'https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search',
                    params=params,
                    headers=headers
                )
                if r.status_code != 200:
                    _feed_issue(issues, 'LinkedIn', f'HTTP {r.status_code}')
                    continue
                soup = BeautifulSoup(r.text, 'html.parser')
                cards = soup.select('li')
                for c in cards:
                    a = c.select_one('a.base-card__full-link')
                    if not a or not a.get('href'):
                        continue
                    job_url = a['href'].split('?')[0]
                    if job_url in seen_urls:
                        continue
                    seen_urls.add(job_url)

                    title_el = c.select_one('.base-search-card__title')
                    job_title = clean_html_text(title_el.get_text(strip=True)) if title_el else title
                    company_el = c.select_one('.base-search-card__subtitle')
                    company = clean_html_text(company_el.get_text(strip=True)) if company_el else 'Employer'
                    loc_el = c.select_one('.job-search-card__location')
                    job_loc = clean_html_text(loc_el.get_text(strip=True)) if loc_el else loc
                    time_el = c.select_one('time[datetime]')
                    posted_at = _posting_date(time_el.get('datetime')) if time_el else None

                    snippet = f"{company} · {job_loc} · LinkedIn job posting"
                    results.append({
                        'url': job_url,
                        'title': f"{job_title} at {company}",
                        'job_title': job_title,
                        'company': company,
                        'location': job_loc,
                        'posted_at': posted_at,
                        'description': '',
                        'snippet': snippet,
                        'platform': 'linkedin',
                        'source': 'LinkedIn Jobs',
                        'raw_text': f"{job_title} {company} {job_loc} linkedin".casefold()
                    })
            except Exception as exc:
                _feed_issue(issues, 'LinkedIn', type(exc).__name__)
                continue
    return results

def _search_serper_google_jobs(api_key: str, titles: list[str], prefs: dict) -> list[dict]:
    results = []
    city = prefs.get('location', '').strip()
    country = prefs.get('country', '').strip()
    loc_parts = [p for p in (city, country) if p]
    location = ', '.join(loc_parts)

    remote_only = prefs.get('remote_only', False)
    workplace_type = prefs.get('workplace_type', 'any')
    experience_level = prefs.get('experience_level', 'any')
    job_type = prefs.get('job_type', 'any')
    date_posted = prefs.get('date_posted', 'any')

    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }

    seen_urls = set()
    with httpx.Client(timeout=25, trust_env=False) as client:
        for title in titles:
            query_parts = [title]
            if experience_level == 'senior':
                query_parts.append('senior')
            elif experience_level == 'entry':
                query_parts.append('entry level')
            elif experience_level == 'mid':
                query_parts.append('mid level')

            if job_type == 'full_time':
                query_parts.append('full time')
            elif job_type == 'contract':
                query_parts.append('contract')
            elif job_type == 'part_time':
                query_parts.append('part time')

            if workplace_type == 'remote' or remote_only:
                query_parts.append('remote')
            elif workplace_type == 'hybrid':
                query_parts.append('hybrid')
            elif workplace_type == 'on_site':
                query_parts.append('on-site')

            if location:
                query_parts.append(location)

            payload = {
                'q': ' '.join(query_parts),
                'location': location if location else 'United States'
            }
            if date_posted == 'past_24h':
                payload['tbs'] = 'qdr:d'
            elif date_posted == 'past_week':
                payload['tbs'] = 'qdr:w'
            elif date_posted == 'past_month':
                payload['tbs'] = 'qdr:m'

            try:
                r = client.post('https://google.serper.dev/jobs', json=payload, headers=headers)
                if r.status_code != 200:
                    continue
                data = r.json()
                for job in data.get('jobs', []):
                    link = job.get('link') or job.get('applyLink') or ''
                    if not link or link in seen_urls:
                        continue
                    seen_urls.add(link)

                    job_title = clean_html_text(job.get('title', ''))
                    company = clean_html_text(job.get('companyName', 'Employer'))
                    job_loc = clean_html_text(job.get('location', location or 'Remote'))
                    desc = clean_html_text(job.get('description', ''))
                    via = clean_html_text(job.get('via', ''))

                    snippet = f"{company} · {job_loc}{f' ({via})' if via else ''} · {desc[:220]}"
                    results.append({
                        'url': link,
                        'title': f"{job_title} at {company}",
                        'job_title': job_title,
                        'company': company,
                        'location': job_loc,
                        'posted_at': _posting_date(job.get('date')),
                        'description': desc,
                        'snippet': snippet,
                        'platform': 'google',
                        'source': f"Google Jobs ({via})" if via else 'Google Jobs',
                        'raw_text': f"{job_title} {company} {job_loc} {via} {desc}".casefold()
                    })
            except Exception:
                continue
    return results

def score_candidate(item: dict, target_titles: list[str], pref_location: str, remote_only: bool, prefs: dict | None = None) -> int:
    score = 60
    raw = item.get('raw_text', '')
    title = item.get('job_title', '').casefold()

    for target in target_titles:
        t_clean = target.casefold().strip()
        if not t_clean:
            continue
        if t_clean in title:
            score += 25
            break
        target_words = [w for w in t_clean.split() if len(w) > 2 and w not in ('and', 'for', 'the', 'with')]
        matching_words = sum(1 for w in target_words if w in title)
        if matching_words > 0:
            score += min(20, matching_words * 8)
            break

    # Skill match bonus in body
    matched_skills = sum(1 for s in COMMON_TECH_SKILLS if s in raw)
    score += min(15, matched_skills * 2)

    # Remote preference match
    if remote_only and ('remote' in raw or 'worldwide' in raw or 'anywhere' in raw):
        score += 8
    elif not remote_only and pref_location and pref_location.casefold() in raw:
        score += 8

    # Advanced filter scoring adjustments
    if prefs:
        exp_level = prefs.get('experience_level', 'any')
        if exp_level == 'senior':
            if any(k in title for k in ('senior', 'lead', 'principal', 'staff', 'head', 'architect')):
                score += 10
            elif any(k in title for k in ('junior', 'intern', 'entry', 'trainee', 'graduate')):
                score -= 20
        elif exp_level == 'entry':
            if any(k in title for k in ('junior', 'intern', 'entry', 'associate', 'graduate')):
                score += 10
            elif any(k in title for k in ('senior', 'lead', 'principal', 'staff', 'head', 'architect')):
                score -= 20
        elif exp_level == 'mid':
            if any(k in title for k in ('mid', 'intermediate', 'engineer', 'developer')) and not any(k in title for k in ('intern', 'principal', 'head')):
                score += 5

        target_country = prefs.get('country', '').strip().casefold()
        if target_country and target_country in raw:
            score += 6

        workplace = prefs.get('workplace_type', 'any')
        if workplace == 'hybrid' and 'hybrid' in raw:
            score += 6
        elif workplace == 'on_site' and ('on-site' in raw or 'onsite' in raw or 'office' in raw):
            score += 6

    return min(99, max(55, score))

def search_jobs(progress=None):
    if progress:
        progress('Reading target titles and active search preferences…')

    prefs = store.setting('preferences', {})
    if not prefs.get('confirmed'):
        raise ValueError('Review and save your search preferences before searching.')

    search_provider = store.setting('search_provider', 'free')
    candidates = []
    feed_issues: list[str] = []
    seen = set()
    city = prefs.get('location', '').strip()
    country = prefs.get('country', '').strip()
    loc_parts = [p for p in (city, country) if p]
    location = ', '.join(loc_parts)

    titles = [t.strip() for t in prefs.get('titles', []) if t.strip()][:4]
    excluded = [x.casefold() for x in prefs.get('excluded_companies', []) + prefs.get('excluded_keywords', []) if x.strip()]
    remote_only = prefs.get('remote_only', False)

    if search_provider in ('serper', 'google'):
        key = providers.secret('SERPER_API_KEY')
        if not key:
            raise ValueError('Connect a Serper Google Jobs API key in Settings, or switch to Free Search Feeds.')
        if progress:
            progress(f'Querying Google Jobs (via Serper) across {len(titles)} target roles…')
        all_found = _search_serper_google_jobs(key, titles, prefs)
        for item in all_found:
            can = network.canonical(item['url'])
            if can in seen:
                continue
            seen.add(can)
            text = item['raw_text']
            if any(x in text for x in excluded):
                continue
            match_score = score_candidate(item, titles, location, remote_only, prefs=prefs)
            item['score'] = match_score
            candidates.append(item)
    elif search_provider == 'brave':
        key = providers.secret('BRAVE_API_KEY')
        if not key:
            raise ValueError('Connect a Brave Search API key in Settings, or switch to Free Search Feeds.')
        if progress:
            progress(f'Querying Brave Search across {len(titles)} target roles…')
        for title in titles:
            query_parts = [f'"{title}"']
            if prefs.get('experience_level') == 'senior':
                query_parts.append('senior')
            elif prefs.get('experience_level') == 'entry':
                query_parts.append('entry level')

            if prefs.get('job_type') == 'full_time':
                query_parts.append('full time')
            elif prefs.get('job_type') == 'contract':
                query_parts.append('contract')

            if prefs.get('workplace_type') == 'remote' or remote_only:
                query_parts.append('remote')
            elif prefs.get('workplace_type') == 'hybrid':
                query_parts.append('hybrid')
            elif prefs.get('workplace_type') == 'on_site':
                query_parts.append('on-site')

            if location:
                query_parts.append(location)
            query_parts.append('jobs careers apply')
            query = ' '.join(query_parts)

            with httpx.Client(timeout=30, trust_env=False) as client:
                response = client.get(
                    'https://api.search.brave.com/res/v1/web/search',
                    params={'q': query, 'count': 12},
                    headers={'X-Subscription-Token': key, 'Accept': 'application/json'}
                )
                response.raise_for_status()
            for hit in response.json().get('web', {}).get('results', []):
                url = hit.get('url', '')
                if not url.startswith('https://'):
                    continue
                can = network.canonical(url)
                if can in seen:
                    continue
                seen.add(can)
                text = (hit.get('title', '') + ' ' + hit.get('description', '')).casefold()
                if any(x in text for x in excluded):
                    continue
                clean_title = clean_html_text(hit.get('title', ''))
                clean_snippet = clean_html_text(hit.get('description', ''))
                plat = network.platform(url)
                item_obj = {
                    'url': url,
                    'title': clean_title,
                    'job_title': clean_title,
                    'company': 'Employer',
                    'location': 'Remote / Web',
                    'posted_at': _posting_date(hit.get('age')),
                    'description': clean_snippet,
                    'snippet': clean_snippet,
                    'platform': plat if plat != 'manual' else 'web',
                    'source': 'Brave web search',
                    'raw_text': text
                }
                item_obj['score'] = score_candidate(item_obj, titles, location, remote_only, prefs=prefs)
                candidates.append(item_obj)
    else:
        # 100% Free: LinkedIn Jobs (Direct Guest Search) + WeWorkRemotely, Jobicy, Remotive, Arbeitnow
        with httpx.Client(timeout=25, follow_redirects=True, trust_env=False, verify=_search_ssl_context()) as client:
            all_found = []

            if progress:
                progress('Querying LinkedIn public jobs and WeWorkRemotely feeds…')
            all_found.extend(_search_linkedin(client, titles, prefs, feed_issues))
            all_found.extend(_search_weworkremotely(client, titles, prefs, feed_issues))

            for title in titles:
                if progress:
                    progress(f'Querying Jobicy, Remotive & Arbeitnow for "{title}"…')
                all_found.extend(_search_jobicy(client, title, prefs, feed_issues))
                all_found.extend(_search_remotive(client, title, prefs, feed_issues))
                all_found.extend(_search_arbeitnow(client, title, prefs, feed_issues))

            if progress:
                progress(f'Filtering {len(all_found)} candidates against preferences and deal-breakers…')

            for item in all_found:
                can = network.canonical(item['url'])
                if can in seen:
                    continue
                seen.add(can)
                text = item['raw_text']
                if any(x in text for x in excluded):
                    continue
                if remote_only and 'remote' not in text and 'worldwide' not in text and 'anywhere' not in text:
                    continue
                match_score = score_candidate(item, titles, location, remote_only, prefs=prefs)
                candidates.append({
                    'url': item['url'],
                    'title': item['title'],
                    'job_title': item.get('job_title', ''),
                    'company': item.get('company', ''),
                    'location': item.get('location', 'Remote'),
                    'posted_at': item.get('posted_at'),
                    'description': item.get('description', ''),
                    'snippet': item['snippet'],
                    'platform': item['platform'],
                    'source': item.get('source', 'Feed search'),
                    'score': match_score
                })

    # Enforce saved criteria on every provider. Provider query parameters alone
    # are insufficient: several feeds do not implement location or date filters.
    before_filters = len(candidates)
    now = datetime.now(timezone.utc)
    candidates = [item for item in candidates if _matches_search_filters(item, prefs, titles, now)]
    if progress:
        progress(f'{len(candidates)} of {before_filters} opportunities match the saved title, location and date criteria.')

    # Sort candidates by relevance score descending so the best matches are first
    candidates.sort(key=lambda c: c.get('score', 0), reverse=True)

    if not candidates and feed_issues:
        failures = ', '.join(dict.fromkeys(feed_issues))
        raise ValueError(f'No jobs were returned because search sources failed: {failures}. Check the network or certificate configuration and retry.')

    if progress:
        progress(f'Found and ranked {len(candidates)} high-match opportunities.')

    # Save full descriptions in search_cache for instant 0ms import without network bloat
    cache = store.setting('search_cache', {})
    for item in candidates:
        can = network.canonical(item['url'])
        cache[can] = {
            'title': item.get('job_title') or item.get('title'),
            'company': item.get('company'),
            'location': item.get('location'),
            'posted_at': item.get('posted_at'),
            'description': item.get('description', ''),
            'url': item.get('url'),
            'platform': item.get('platform'),
            'source': item.get('source', 'Feed search')
        }
    store.set_setting('search_cache', cache)

    # Strip description from search_results to keep /api/bootstrap lightweight
    light_items = [
        {
            'url': c['url'],
            'title': c['title'],
            'job_title': c.get('job_title', ''),
            'company': c.get('company', ''),
            'location': c.get('location', 'Remote'),
            'posted_at': c.get('posted_at'),
            'snippet': c['snippet'],
            'platform': c['platform'],
            'source': c.get('source', 'Feed search'),
            'score': c['score']
        }
        for c in candidates
    ]
    store.set_setting('search_results', {'at': store.now(), 'items': light_items})
    if search_provider in ('serper', 'google'):
        source_name = 'Google Jobs (via Serper)'
    elif search_provider == 'brave':
        source_name = 'Brave Search'
    else:
        source_name = 'LinkedIn Jobs & curated tech feeds'
    return f'Found {len(candidates)} opportunities from {source_name}. Import a posting to tailor your application.'

def filter_notes(job):
    p = store.setting('preferences', {})
    notes = []
    text = (job['title'] + ' ' + job['company'] + ' ' + job.get('description', '')).casefold()
    job_loc = job.get('location', '').casefold()
    for term in p.get('excluded_companies', []) + p.get('excluded_keywords', []):
        if term.strip() and term.casefold() in text:
            notes.append('Excluded preference matched: ' + term)
    if p.get('remote_only') and 'remote' not in text:
        notes.append('Remote eligibility needs confirmation.')
    if p.get('location') and p['location'].casefold() not in job_loc:
        notes.append('Check city location against preference: ' + p['location'])
    if p.get('country') and p['country'].casefold() not in text and p['country'].casefold() not in job_loc:
        notes.append('Check country location against preference: ' + p['country'])
    if p.get('salary_note'):
        notes.append('Check salary: ' + p['salary_note'])
    if not p.get('work_authorization'):
        notes.append('Work authorization is not set; answer any related questions yourself.')
    return notes
