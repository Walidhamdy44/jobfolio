"""Only fetch public HTTPS URLs, including after redirects."""
import html
import ipaddress
import re
import socket
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
import httpx
from bs4 import BeautifulSoup

def clean_title(text):
    if not text:
        return ''
    unescaped = html.unescape(text)
    if '<' in unescaped and '>' in unescaped:
        soup = BeautifulSoup(unescaped, 'html.parser')
        unescaped = soup.get_text(' ', strip=True)
    unescaped = html.unescape(unescaped)
    unescaped = unescaped.replace('\xa0', ' ')
    return ' '.join(unescaped.split())

def public_url(url):
    p = urlparse(url)
    if p.scheme != 'https' or not p.hostname or p.username or p.password or p.port not in (None, 443):
        raise ValueError('Use a public HTTPS job URL without embedded credentials.')
    try:
        addresses = socket.getaddrinfo(p.hostname, 443)
    except socket.gaierror:
        raise ValueError('The job site could not be resolved. Check its URL.')
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError('Private and local network URLs are not supported.')
    return url

def canonical(url):
    p = urlparse(url)
    path = p.path.rstrip('/')
    if platform(url) == 'lever' and path.endswith('/apply'): path = path[:-6]
    query = [(k,v) for k,v in parse_qsl(p.query) if not k.lower().startswith(('utm_', 'source', 'ref'))]
    return urlunparse((p.scheme.lower(), p.netloc.lower(), path, '', urlencode(sorted(query)), ''))

def fetch(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    with httpx.Client(timeout=25, follow_redirects=False, trust_env=False) as client:
        for _ in range(5):
            public_url(url)
            with client.stream('GET', url, headers=headers) as r:
                if r.is_redirect:
                    from urllib.parse import urljoin
                    url = urljoin(url, r.headers['location'])
                    continue
                r.raise_for_status()
                chunks, size = [], 0
                for chunk in r.iter_bytes():
                    size += len(chunk)
                    if size > 3_000_000:
                        raise ValueError('The job page is too large to import.')
                    chunks.append(chunk)
                return b''.join(chunks).decode('utf-8', errors='replace'), url
    raise ValueError('The job link redirects too many times.')

def plain(html_content):
    if not html_content:
        return ''
    unescaped = html.unescape(html_content)
    soup = BeautifulSoup(unescaped, 'html.parser')
    for tag in soup(['script','style','nav','footer','noscript']):
        tag.decompose()
    text = soup.get_text('\n', strip=True)
    text = html.unescape(text)
    text = text.replace('\xa0', ' ')
    return re.sub(r'\n{3,}', '\n\n', text).strip()

def platform(url):
    if not url:
        return 'manual'
    host = (urlparse(url).hostname or '').lower()
    if host in ('boards.greenhouse.io','job-boards.greenhouse.io'):
        return 'greenhouse'
    if host in ('jobs.lever.co','jobs.eu.lever.co'):
        return 'lever'
    if host == 'linkedin.com' or host.endswith('.linkedin.com'):
        return 'linkedin'
    return 'manual'

def get_source_label(url, plat=None):
    if not url:
        return 'Pasted description'
    if plat in ('jobicy', 'remotive', 'arbeitnow', 'weworkremotely'):
        feed_names = {'jobicy': 'Jobicy feed', 'remotive': 'Remotive feed', 'arbeitnow': 'Arbeitnow feed', 'weworkremotely': 'WeWorkRemotely feed'}
        return feed_names.get(plat, f'{plat.capitalize()} feed')
    if plat == 'greenhouse':
        return 'Greenhouse board'
    if plat == 'lever':
        return 'Lever board'
    if plat == 'linkedin':
        return 'LinkedIn'
    if plat == 'google':
        return 'Google Jobs'
    host = (urlparse(url).hostname or '').lower().replace('www.', '')
    return host if host else 'Employer website'

def _fetch_linkedin_job(url):
    from datetime import datetime, timezone
    m = re.search(r'(\d{7,})', url)
    if not m:
        return None
    job_id = m.group(1)
    api_url = f'https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    with httpx.Client(timeout=20, follow_redirects=True, trust_env=False) as client:
        try:
            r = client.get(api_url, headers=headers)
            if r.status_code != 200:
                return None
            soup = BeautifulSoup(r.text, 'html.parser')
            title_el = soup.select_one('.top-card-layout__title') or soup.select_one('h2') or soup.select_one('h1')
            title = clean_title(title_el.get_text(strip=True)) if title_el else 'Software Engineer'

            company_el = soup.select_one('.topcard__org-name-link') or soup.select_one('.topcard__flavor')
            company = clean_title(company_el.get_text(strip=True)) if company_el else 'Employer'

            loc_el = soup.select_one('.topcard__flavor--bullet') or soup.select_one('.sub-nav-cta__sub-title')
            location = clean_title(loc_el.get_text(strip=True)) if loc_el else 'Remote / Unspecified'

            desc_el = soup.select_one('.show-more-less-html__markup') or soup.select_one('.description__text') or soup.select_one('section')
            desc = plain(str(desc_el)) if desc_el else plain(r.text)

            if len(desc) >= 50:
                return {
                    'title': title,
                    'company': company,
                    'location': location,
                    'description': desc,
                    'url': url,
                    'canonical_url': canonical(url),
                    'platform': 'linkedin',
                    'source': 'LinkedIn',
                    'verified': True,
                    'verified_at': datetime.now(timezone.utc).isoformat()
                }
        except Exception:
            return None
    return None

def _fetch_weworkremotely_job(url):
    import xml.etree.ElementTree as ET
    from datetime import datetime, timezone
    feeds = [
        'https://weworkremotely.com/categories/remote-front-end-programming-jobs.rss',
        'https://weworkremotely.com/categories/remote-programming-jobs.rss',
        'https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss',
        'https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss',
    ]
    target_clean = canonical(url).split('?')[0].rstrip('/')
    with httpx.Client(timeout=15, follow_redirects=True, trust_env=False) as client:
        for f in feeds:
            try:
                r = client.get(f, headers={'User-Agent': 'Mozilla/5.0'})
                if r.status_code != 200:
                    continue
                root = ET.fromstring(r.content)
                for it in root.findall('.//item'):
                    link = it.find('link').text if it.find('link') is not None else ''
                    guid = it.find('guid').text if it.find('guid') is not None else ''
                    if (link and canonical(link).split('?')[0].rstrip('/') == target_clean) or (guid and canonical(guid).split('?')[0].rstrip('/') == target_clean):
                        raw_title = it.find('title').text if it.find('title') is not None else 'Software Engineer'
                        company = raw_title.split(':', 1)[0].strip() if ':' in raw_title else 'Remote Tech'
                        job_title = raw_title.split(':', 1)[1].strip() if ':' in raw_title else raw_title
                        region = it.find('region').text if it.find('region') is not None else 'Remote'
                        desc_elem = it.find('description')
                        raw_desc = desc_elem.text if desc_elem is not None else ''
                        desc = plain(raw_desc)
                        return {
                            'title': f"{job_title} at {company}" if ' at ' not in job_title else job_title,
                            'company': company,
                            'location': region,
                            'description': desc,
                            'url': link or url,
                            'canonical_url': target_clean,
                            'platform': 'manual',
                            'verified': True,
                            'verified_at': datetime.now(timezone.utc).isoformat()
                        }
            except Exception:
                continue
    return None

def import_url(url):
    import json
    from datetime import datetime, timezone
    from . import store

    target_can = canonical(public_url(url))

    # 1. Check search_cache if it has a substantive full description
    cache = store.setting('search_cache', {})
    if target_can in cache and len(cache[target_can].get('description', '')) >= 250:
        c_item = cache[target_can]
        plat = c_item.get('platform', platform(url))
        return {
            'title': clean_title(c_item.get('title', 'Untitled job')),
            'company': clean_title(c_item.get('company') or 'Employer'),
            'location': c_item.get('location', 'Remote'),
            'description': c_item.get('description', ''),
            'url': c_item.get('url', url),
            'canonical_url': target_can,
            'platform': plat,
            'source': c_item.get('source') or get_source_label(url, plat),
            'verified': True,
            'verified_at': datetime.now(timezone.utc).isoformat()
        }

    # 2. Check search_results if it already has a substantive description
    sr = store.setting('search_results', {})
    search_fallback = None
    for item in sr.get('items', []):
        if canonical(item.get('url', '')) == target_can or item.get('url') == url:
            desc = item.get('description', '')
            company = clean_title(item.get('company', ''))
            title = clean_title(item.get('job_title') or item.get('title', 'Untitled job'))
            if not company and ' at ' in title:
                company = title.split(' at ')[-1].strip()
            plat = item.get('platform', platform(url))
            if len(desc) >= 250:
                return {
                    'title': title,
                    'company': company or 'Employer',
                    'location': item.get('location', 'Remote'),
                    'description': desc,
                    'url': item.get('url', url),
                    'canonical_url': target_can,
                    'platform': plat,
                    'source': item.get('source') or get_source_label(url, plat),
                    'verified': True,
                    'verified_at': datetime.now(timezone.utc).isoformat()
                }
            # Keep shorter item as fallback in case web fetch is blocked
            snippet = item.get('snippet', '')
            best_desc = desc if len(desc) >= len(snippet) else snippet
            if len(best_desc) >= 50:
                search_fallback = {
                    'title': title,
                    'company': company or 'Employer',
                    'location': item.get('location', 'Remote'),
                    'description': best_desc,
                    'url': item.get('url', url),
                    'canonical_url': target_can,
                    'platform': plat,
                    'source': item.get('source') or get_source_label(url, plat),
                    'verified': False,
                    'verification_note': 'Description imported from search feed summary. Check the posting for complete requirements.'
                }

    p = urlparse(public_url(url))
    host = (p.hostname or '').lower()
    bits = [x for x in p.path.split('/') if x]
    kind = platform(url)

    # 3. Greenhouse API
    if kind == 'greenhouse' and len(bits) >= 3 and bits[1] == 'jobs' and bits[2].isdigit():
        try:
            raw, _ = fetch(f'https://boards-api.greenhouse.io/v1/boards/{bits[0]}/jobs/{bits[2]}')
            data = json.loads(raw)
            return {
                'title': clean_title(data['title']),
                'company': clean_title(data.get('company_name') or bits[0]),
                'location': data.get('location', {}).get('name', ''),
                'description': plain(data['content']),
                'url': data.get('absolute_url', url),
                'canonical_url': canonical(data.get('absolute_url', url)),
                'platform': kind,
                'source': 'Greenhouse board',
                'verified': True,
                'verified_at': datetime.now(timezone.utc).isoformat()
            }
        except Exception:
            pass

    # 4. Lever API
    if kind == 'lever' and len(bits) >= 2:
        try:
            region = 'api.eu.lever.co' if p.hostname == 'jobs.eu.lever.co' else 'api.lever.co'
            raw, _ = fetch(f'https://{region}/v0/postings/{bits[0]}/{bits[1]}?mode=json')
            data = json.loads(raw)
            html_content = data.get('description', '') + '\n' + '\n'.join(x.get('text', '') + '\n' + x.get('content', '') for x in data.get('lists', [])) + '\n' + data.get('additional', '')
            return {
                'title': clean_title(data['text']),
                'company': clean_title(bits[0]),
                'location': data.get('categories', {}).get('location', ''),
                'description': plain(html_content),
                'url': data['hostedUrl'],
                'canonical_url': canonical(data['hostedUrl']),
                'platform': kind,
                'source': 'Lever board',
                'verified': True,
                'verified_at': datetime.now(timezone.utc).isoformat()
            }
        except Exception:
            pass

    # 5. WeWorkRemotely RSS feed matcher
    if 'weworkremotely.com' in host:
        wwr_job = _fetch_weworkremotely_job(url)
        if wwr_job:
            wwr_job['source'] = 'WeWorkRemotely feed'
            return wwr_job

    # 6. LinkedIn Guest Job fetcher
    if 'linkedin.com' in host:
        # Guest pages occasionally return an auth wall on the first request.
        # Retry once before keeping only the discovery summary.
        li_job = _fetch_linkedin_job(url) or _fetch_linkedin_job(url)
        if li_job:
            return li_job

    # 7. Fetch webpage
    try:
        raw, final = fetch(url)
        soup = BeautifulSoup(raw, 'html.parser')

        # Try JSON-LD schema.org JobPosting
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string or script.get_text())
            except (ValueError, TypeError):
                continue
            def walk(x):
                if isinstance(x, list):
                    for a in x: yield from walk(a)
                if isinstance(x, dict):
                    if x.get('@type') == 'JobPosting' or 'JobPosting' in (x.get('@type') or []): yield x
                    yield from walk(x.get('@graph', []))
            for j in walk(data):
                desc = plain(j.get('description', ''))
                if len(desc) >= 50:
                    return {
                        'title': clean_title(j.get('title', 'Untitled job')),
                        'company': clean_title((j.get('hiringOrganization') or {}).get('name', 'Unknown employer')),
                        'location': str(j.get('jobLocationType', 'Remote')),
                        'description': desc,
                        'url': final,
                        'canonical_url': canonical(final),
                        'platform': 'manual',
                        'source': get_source_label(final, 'manual'),
                        'verified': False,
                        'verification_note': 'Imported structured posting. Verify availability and location on the employer site.'
                    }

        # HTML Heuristic Fallback
        page_title = ''
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            page_title = clean_title(og_title.get('content'))
        if not page_title and soup.find('h1'):
            page_title = clean_title(soup.find('h1').get_text(strip=True))
        if not page_title and soup.title:
            page_title = clean_title(soup.title.get_text(strip=True))

        company_name = ''
        og_site = soup.find('meta', property='og:site_name')
        if og_site and og_site.get('content'):
            company_name = clean_title(og_site.get('content'))
        if not company_name and ' at ' in page_title:
            company_name = page_title.split(' at ')[-1].split(' - ')[0].strip()
        if not company_name and host:
            company_name = host.replace('www.', '').split('.')[0].capitalize()

        content_box = soup.find('main') or soup.find('article') or soup.find(class_=re.compile(r'job[-_]?desc|posting[-_]?desc|content[-_]?body', re.I))
        body_text = plain(str(content_box)) if content_box else plain(raw)

        if len(body_text) >= 50:
            return {
                'title': page_title[:200] if page_title else 'Software Engineer',
                'company': company_name[:150] if company_name else 'Employer',
                'location': 'Remote / Unspecified',
                'description': body_text[:30000],
                'url': final,
                'canonical_url': canonical(final),
                'platform': 'manual',
                'source': get_source_label(final, 'manual'),
                'verified': False,
                'verification_note': 'Imported from webpage text. Verify full requirements on the employer site.'
            }
    except Exception:
        pass

    if search_fallback:
        return search_fallback

    raise ValueError('Could not identify a complete job posting. Paste the job description using Add job instead.')
