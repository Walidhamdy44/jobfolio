import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field, ConfigDict
from . import store, profile, providers, network, tailoring, search, browser, worker
from .documents import verify_files

load_dotenv(store.ROOT/'.env')

@asynccontextmanager
async def lifespan(app):
    store.init(); profile.import_master()
    yield

app=FastAPI(title='Jobfolio local agent',lifespan=lifespan,docs_url=None,redoc_url=None)
app.add_middleware(TrustedHostMiddleware,allowed_hosts=['127.0.0.1','localhost','testserver'])

@app.middleware('http')
async def local_only(request:Request, call_next):
    origin=request.headers.get('origin')
    expected=str(request.base_url).rstrip('/')
    is_loopback=False
    if origin:
        po=urlparse(origin)
        pe=urlparse(expected)
        is_loopback=(po.hostname in ('127.0.0.1','localhost') and pe.hostname in ('127.0.0.1','localhost') and po.scheme==pe.scheme)
    if origin and origin!=expected and not is_loopback:
        return JSONResponse({'detail':'Cross-origin access is disabled.'},status_code=403)
    if request.method not in ('GET','HEAD','OPTIONS') and request.headers.get('x-job-agent')!='local':
        return JSONResponse({'detail':'Use the local dashboard to make changes.'},status_code=403)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='no-referrer'
    response.headers['Cache-Control']='no-store'
    response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    return response

@app.exception_handler(ValueError)
async def value_error(request,exc): return JSONResponse({'detail':str(exc)},status_code=400)

@app.exception_handler(Exception)
async def generic_error(request,exc): return JSONResponse({'detail':worker.error_message(exc)},status_code=500)

def busy(job_id):
    with store.db() as c:
        active=c.execute("SELECT id FROM runs WHERE target=? AND state IN ('queued','running')",(job_id,)).fetchone()
    if active: raise ValueError('An operation for this job is still running. Wait for it to finish.')
    if store.get_job(job_id)['state'] in ('submitted','submitting','uncertain'):
        raise ValueError('This application is submitted or uncertain. Resolve its status before changing it.')

class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid')

class JobInput(Strict):
    title:str=Field(min_length=2,max_length=250)
    company:str=Field(min_length=2,max_length=200)
    location:str=Field(default='',max_length=200)
    url:str=Field(default='',max_length=2000)
    description:str=Field(min_length=50,max_length=60000)

class JobUpdateInput(Strict):
    title: str | None = Field(default=None, min_length=2, max_length=250)
    company: str | None = Field(default=None, min_length=2, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, min_length=20, max_length=60000)

class URLInput(Strict):
    url:str=Field(max_length=2000)

class PrepareInput(Strict):
    mode:Literal['ai','local']='local'

class Preferences(Strict):
    titles:list[str]=Field(min_length=1,max_length=10)
    location:str=Field(default='',max_length=200)
    country:str=Field(default='',max_length=100)
    date_posted:Literal['any','past_24h','past_week','past_month']='any'
    experience_level:Literal['any','entry','mid','senior']='any'
    job_type:Literal['any','full_time','contract','part_time']='any'
    remote_only:bool=False
    workplace_type:Literal['any','remote','hybrid','on_site']='any'
    excluded_companies:list[str]=Field(default_factory=list,max_length=100)
    excluded_keywords:list[str]=Field(default_factory=list,max_length=100)
    salary_note:str=Field(default='',max_length=500)
    work_authorization:str=Field(default='',max_length=1000)
    confirmed:bool=True

class Entry(Strict):
    id:str=Field(min_length=1,max_length=50)
    text:str=Field(min_length=1,max_length=8000)

class Section(Strict):
    title:str=Field(min_length=1,max_length=100)
    items:list[Entry]=Field(min_length=1,max_length=100)

class ProfileInput(Strict):
    name:str=Field(min_length=1,max_length=150)
    headline:str=Field(min_length=1,max_length=250)
    email:str=Field(max_length=250)
    phone:str=Field(max_length=100)
    location:str=Field(max_length=250)
    links:list[str]=Field(max_length=15)
    sections:list[Section]=Field(min_length=1,max_length=20)

class StructureProfileInput(Strict):
    mode: Literal['ai', 'local'] = 'ai'

class SettingsInput(Strict):
    provider: Literal['openrouter', 'tokenrouter', 'opencode', 'openai', 'custom'] = 'openrouter'
    api_key: str|None = Field(default=None, max_length=1000)
    openai_key: str|None = Field(default=None, max_length=1000)
    brave_key: str|None = Field(default=None, max_length=1000)
    serper_key: str|None = Field(default=None, max_length=1000)
    model: str = Field(min_length=1, max_length=100)
    base_url: str|None = Field(default=None, max_length=500)
    search_provider: Literal['free', 'brave', 'serper', 'google'] = 'free'

class SearchInput(Strict):
    preferences: Preferences | None = None
    search_provider: Literal['free', 'brave', 'serper', 'google'] | None = None

class ReviewInput(Strict):
    package_hash:str
    cv_reviewed:bool
    coverage_reviewed:bool
    answers:dict[str,str]
    supports:list[Literal['full','partial','missing']]

class HashInput(Strict):
    package_hash:str

class AutoApplyInput(Strict):
    package_hash: str | None = None
    auto_submit: bool = False
    headless: bool = False

class OpenSessionInput(Strict):
    url: str = 'https://www.linkedin.com'

class Resolution(Strict):
    status:Literal['submitted','not_submitted']
    note:str=Field(min_length=10,max_length=2000)

@app.get('/api/workspace')
def bootstrap():
    with store.db() as c:
        jobs=[store.get_job(r['id']) for r in c.execute('SELECT id FROM jobs ORDER BY created DESC').fetchall()]
        runs=[dict(r) for r in c.execute('SELECT * FROM runs ORDER BY created DESC LIMIT 15')]
        events=[dict(r) for r in c.execute('SELECT * FROM events ORDER BY id DESC LIMIT 20')]
    cfg = providers.get_provider_config()
    search_provider = store.setting('search_provider', 'free')
    return {
        'profile': store.setting('profile'),
        'preferences': store.setting('preferences'),
        'jobs': jobs,
        'runs': runs,
        'events': events,
        'search_results': store.setting('search_results', {'items': []}),
        'connections': {
            'provider': cfg['provider'],
            'connected': cfg['connected'],
            'model': cfg['model'],
            'base_url': cfg['base_url'],
            'search_provider': search_provider,
            'free_search_ready': True,
            'brave': bool(providers.secret('BRAVE_API_KEY')),
            'serper': bool(providers.secret('SERPER_API_KEY')),
            'openai': bool(providers.secret('OPENAI_API_KEY')),
            'openrouter': bool(providers.secret('OPENROUTER_API_KEY')),
            'tokenrouter': bool(providers.secret('TOKENROUTER_API_KEY')),
            'opencode': bool(providers.secret('OPENCODE_API_KEY')),
        }
    }

@app.get('/api/health')
def health(): return {'app':'jobfolio','status':'ok'}

@app.put('/api/profile')
def save_profile(body:ProfileInput):
    with store.db() as c:
        if c.execute("SELECT id FROM runs WHERE state IN ('queued','running')").fetchone(): raise ValueError('Wait for current operations before editing your master profile.')
    old=store.setting('profile',{})
    data=body.model_dump(); ids=[i['id'] for s in data['sections'] for i in s['items']]
    if len(ids)!=len(set(ids)): raise ValueError('Profile evidence identifiers must be unique.')
    data.update(revision=old.get('revision',0)+1,source_file=old.get('source_file',''))
    store.set_setting('profile',data)
    with store.db() as c:
        c.execute('UPDATE packages SET approved_hash=NULL')
        c.execute("UPDATE jobs SET state='awaiting_review' WHERE state='approved'")
    return {'ok':True}

@app.post('/api/profile/structure')
def structure_profile(body:StructureProfileInput=StructureProfileInput()):
    res=profile.structure_cv(mode=body.mode)
    return {'profile':res,'ok':True}

@app.get('/api/master-cv')
def master_cv():
    name=store.setting('profile',{}).get('source_file','')
    path=(store.ROOT/name).resolve()
    if not name or path.parent!=store.ROOT or not path.is_file(): raise HTTPException(404,'Master CV not found.')
    return FileResponse(path,media_type='application/pdf',filename=name)

@app.put('/api/preferences')
def save_preferences(body:Preferences):
    data=body.model_dump()
    data['titles']=[s.strip() for s in data['titles'] if s.strip()]
    if not data['titles']: raise ValueError('Enter at least one target title.')
    if data.get('workplace_type') == 'remote':
        data['remote_only'] = True
    elif data.get('remote_only') and data.get('workplace_type') == 'any':
        data['workplace_type'] = 'remote'
    store.set_setting('preferences',data)
    return {'ok':True}

@app.put('/api/settings')
def save_settings(body:SettingsInput):
    store.set_setting('provider', body.provider)
    store.set_setting('model', body.model.strip())
    if body.base_url is not None:
        store.set_setting('base_url', body.base_url.strip())
    store.set_setting('search_provider', body.search_provider)

    if body.api_key is not None:
        secret_name = providers.PROVIDER_SECRET_NAMES.get(body.provider, 'OPENROUTER_API_KEY')
        providers.save_secret(secret_name, body.api_key.strip())
    if body.openai_key is not None:
        providers.save_secret('OPENAI_API_KEY', body.openai_key.strip())
    if body.brave_key is not None:
        providers.save_secret('BRAVE_API_KEY', body.brave_key.strip())
    if body.serper_key is not None:
        providers.save_secret('SERPER_API_KEY', body.serper_key.strip())
    return {'ok':True}

@app.post('/api/jobs')
def add_job(body:JobInput):
    data=body.model_dump()
    data['title'] = network.clean_title(data['title'])
    data['company'] = network.clean_title(data['company'])
    data['location'] = network.clean_title(data.get('location', ''))
    if data['url']:
        network.public_url(data['url'])
        plat = network.platform(data['url'])
        data.update(
            canonical_url=network.canonical(data['url']),
            platform=plat,
            source=network.get_source_label(data['url'], plat),
            verified=False,
            verification_note='Description supplied by you. Verify the posting before applying.'
        )
    else:
        data.update(
            canonical_url='',
            platform='manual',
            source='Pasted description',
            verified=False,
            verification_note='Description supplied by you.'
        )
    data['filter_notes']=search.filter_notes(data)
    job,created=store.add_job(data)
    return {'job':job,'created':created}

@app.post('/api/jobs/import')
def import_job(body:URLInput):
    network.public_url(body.url)
    try:
        data = network.import_url(body.url)
        data['title'] = network.clean_title(data.get('title', 'Untitled job'))
        data['company'] = network.clean_title(data.get('company', 'Employer'))
        if not data.get('source'):
            data['source'] = network.get_source_label(body.url, data.get('platform'))
        data['filter_notes'] = search.filter_notes(data)
        job, created = store.add_job(data)
        if any(n.startswith('Excluded preference') for n in data['filter_notes']):
            store.update_job(job['id'], state='skipped')
        store.event(job['id'], f"Imported job: {job['title']} at {job['company']}")
        run_id = store.uid()
        with store.db() as c:
            if not created:
                msg = 'This job is already in your workspace; no duplicate was created.'
            elif not data.get('verified') or len(data.get('description', '')) < 250:
                msg = 'Job saved with a brief description. Fetch the full posting before preparing a CV.'
            else:
                msg = 'Job imported and ready for review.'
            c.execute('INSERT INTO runs VALUES (?,?,?,?,?,?,?)',
                      (run_id, 'import', job['id'], 'completed', msg, store.now(), store.now()))
        return {'job': job, 'created': created, 'run_id': run_id, 'ok': True}
    except Exception as exc:
        run_id = store.uid()
        err_msg = worker.error_message(exc)
        with store.db() as c:
            c.execute('INSERT INTO runs VALUES (?,?,?,?,?,?,?)',
                      (run_id, 'import', None, 'failed', err_msg, store.now(), store.now()))
        raise ValueError(err_msg)

@app.post('/api/search')
def run_search(body: SearchInput = SearchInput()):
    if body.preferences is not None:
        pdata = body.preferences.model_dump()
        pdata['titles'] = [s.strip() for s in pdata['titles'] if s.strip()]
        if not pdata['titles']:
            raise ValueError('Enter at least one target title.')
        pdata['confirmed'] = True
        store.set_setting('preferences', pdata)
    if body.search_provider is not None:
        store.set_setting('search_provider', body.search_provider)

    search_provider = store.setting('search_provider', 'free')
    if search_provider == 'brave' and not providers.secret('BRAVE_API_KEY'):
        raise ValueError('Connect a Brave Search API key in Settings, or switch to Free Search Feeds.')
    if not store.setting('preferences',{}).get('confirmed'):
        raise ValueError('Review and save your search preferences first.')
    return {'run_id':worker.enqueue('search',None,lambda progress=None:search.search_jobs(progress=progress))}

@app.get('/api/jobs/{job_id}')
def job_detail(job_id:str):
    job=store.get_job(job_id)
    with store.db() as c: events=[dict(r) for r in c.execute('SELECT * FROM events WHERE job_id=? ORDER BY id DESC',(job_id,))]
    return {'job':job,'package':store.get_package(job_id),'events':events}

@app.patch('/api/jobs/{job_id}')
def update_job_details(job_id:str, body:JobUpdateInput):
    busy(job_id)
    job=store.get_job(job_id)
    changes={}
    if body.title is not None:
        changes['title'] = network.clean_title(body.title)
    if body.company is not None:
        changes['company'] = network.clean_title(body.company)
    if body.location is not None:
        changes['location'] = network.clean_title(body.location)
    if body.description is not None:
        changes['description'] = body.description.strip()
        changes['last_error'] = None

    temp_job = {**job, **changes}
    changes['filter_notes'] = search.filter_notes(temp_job)
    store.update_job(job_id, **changes)
    store.event(job_id, 'Job details updated by you.')
    return {'job': store.get_job(job_id), 'ok': True}

@app.post('/api/jobs/{job_id}/refetch')
def refetch_job(job_id:str):
    busy(job_id)
    job=store.get_job(job_id)
    if not job.get('url'):
        raise ValueError('This job does not have a posting URL to fetch.')
    data=network.import_url(job['url'])
    changes={
        'description': data['description'],
        'verified': data.get('verified', False),
        'verification_note': data.get('verification_note', ''),
        'last_error': None
    }
    if data.get('source'):
        changes['source'] = data['source']
    if data.get('title') and job.get('title') in ('Untitled job', 'Software Engineer'):
        changes['title'] = network.clean_title(data['title'])
    if data.get('company') and job.get('company') == 'Employer':
        changes['company'] = network.clean_title(data['company'])
    temp_job = {**job, **changes}
    changes['filter_notes'] = search.filter_notes(temp_job)
    store.update_job(job_id, **changes)
    store.event(job_id, 'Job posting re-fetched from source.')
    return {'job': store.get_job(job_id), 'ok': True}

@app.post('/api/jobs/{job_id}/prepare')
def prepare_job(job_id:str,body:PrepareInput):
    busy(job_id)
    job = store.get_job(job_id)
    if job.get('url') and not job.get('verified'):
        refreshed = network.import_url(job['url'])
        if not refreshed.get('verified') or len(refreshed.get('description', '')) < 50:
            raise ValueError('The full job description could not be fetched. Use "Retry fetching description" or paste the complete posting before preparing a CV.')
        store.update_job(
            job_id,
            description=refreshed['description'],
            verified=True,
            verified_at=refreshed.get('verified_at'),
            verification_note='',
            last_error=None,
        )
        store.event(job_id, 'Fetched the complete job description before CV preparation.')
    if body.mode=='ai':
        cfg = providers.get_provider_config()
        if not cfg['connected']:
            p_name = providers.PROVIDER_DISPLAY_NAMES.get(cfg['provider'], cfg['provider'].capitalize())
            raise ValueError(f'Connect an API key for {p_name} in Settings first, or use local preparation.')
    return {'run_id':worker.enqueue('prepare',job_id,lambda progress=None:tailoring.prepare(job_id,body.mode,progress=progress))}

@app.post('/api/jobs/{job_id}/inspect')
def inspect_form(job_id:str):
    busy(job_id)
    return {'run_id':worker.enqueue('inspect',job_id,lambda progress=None:browser.inspect(job_id))}

@app.post('/api/jobs/{job_id}/cover-letter')
def draft_cover_letter(job_id:str,body:PrepareInput):
    busy(job_id)
    return {'run_id':worker.enqueue('cover-letter',job_id,lambda progress=None:tailoring.cover_letter(job_id,body.mode,progress=progress))}

@app.put('/api/jobs/{job_id}/review')
def review_job(job_id:str,body:ReviewInput):
    busy(job_id)
    package=store.get_package(job_id)
    if not package or package['hash']!=body.package_hash: raise HTTPException(409,'Package changed. Reload before reviewing.')
    if package['profile_revision']!=store.setting('profile')['revision']: raise ValueError('Your master profile changed. Prepare a fresh CV.')
    data=store.package_data(package)
    if len(body.supports)!=len(data['requirements']): raise ValueError('Review every extracted requirement.')
    allowed={f['key'] for f in (data.get('form') or {}).get('fields',[])}
    if set(body.answers)-allowed: raise ValueError('Answers include fields not in the inspected form.')
    if any(len(v)>20000 for v in body.answers.values()): raise ValueError('An application answer is too long.')
    for row,support in zip(data['requirements'],body.supports):
        if support!='missing' and not row['evidence_ids']: raise ValueError('A supported requirement needs source evidence. Add the missing facts to your profile and prepare again.')
        row['support']=support
    data.update(score=tailoring.score(data['requirements']),cv_reviewed=body.cv_reviewed,coverage_reviewed=body.coverage_reviewed,answers=body.answers)
    store.revise_package(package['id'],data); store.update_job(job_id,state='awaiting_review',score=data['score'])
    return {'ok':True}

@app.post('/api/jobs/{job_id}/approve')
def approve(job_id:str,body:HashInput):
    busy(job_id)
    package=store.get_package(job_id)
    if not package or package['hash']!=body.package_hash: raise HTTPException(409,'Package changed. Reload before approving.')
    if not package['cv_reviewed'] or not package['coverage_reviewed']: raise ValueError('Review the CV and requirement coverage before approving.')
    if package['profile_revision']!=store.setting('profile')['revision']: raise ValueError('Your master profile changed. Prepare a new CV.')
    if package.get('form') and browser.missing_answers(package): raise ValueError('Complete required answers: '+'; '.join(browser.missing_answers(package)))
    verify_files(package)
    with store.db() as c: c.execute('UPDATE packages SET approved_hash=hash WHERE id=? AND hash=?',(package['id'],body.package_hash))
    store.update_job(job_id,state='approved'); store.event(job_id,'You approved this exact CV and answer package.')
    return {'ok':True}

@app.post('/api/jobs/{job_id}/submit')
def submit(job_id:str,body:HashInput):
    busy(job_id)
    package=store.get_package(job_id)
    if not package or not package['approved'] or package['hash']!=body.package_hash: raise ValueError('Approve the current package before submitting.')
    if package['profile_revision']!=store.setting('profile')['revision']: raise ValueError('Profile changed. Prepare and approve again.')
    browser.application_url(store.get_job(job_id)); verify_files(package)
    missing=browser.missing_answers(package)
    if missing: raise ValueError('Complete application review: '+'; '.join(missing))
    # Transactional claim makes double-clicks and concurrent requests harmless.
    with store.db() as c:
        result=c.execute("UPDATE jobs SET state='submitting',updated=? WHERE id=? AND state='approved'",(store.now(),job_id))
        if result.rowcount!=1: raise HTTPException(409,'This application is already processing or needs review.')
    store.event(job_id,'Submission started using your approved package.')
    return {'run_id':worker.enqueue('submit',job_id,lambda progress=None:browser.submit(job_id,package,progress=progress))}

@app.post('/api/jobs/{job_id}/auto-apply')
def auto_apply(job_id: str, body: AutoApplyInput = AutoApplyInput()):
    busy(job_id)
    if body.auto_submit:
        raise ValueError('Unattended Auto-Apply is unavailable until employer screening answers can be reviewed. Use Co-Pilot and submit only after checking the employer form.')
    package = store.get_package(job_id)
    if not package:
        raise ValueError('Prepare and review a tailored CV before starting AI Auto-Apply.')
    if not package.get('approved'):
        raise ValueError('Tailored package must be reviewed and approved before starting AI Auto-Apply.')
    if not package.get('cv_reviewed') or not package.get('coverage_reviewed'):
        raise ValueError('CV and coverage must be reviewed before starting AI Auto-Apply.')
    if not body.package_hash or package.get('hash') != body.package_hash:
        raise HTTPException(409, 'Application package has changed. Please review and approve the updated package.')
    return {
        'run_id': worker.enqueue(
            'auto_apply',
            job_id,
            lambda progress=None: browser.auto_apply_job(
                job_id,
                auto_submit=body.auto_submit,
                headless=body.headless,
                progress=progress
            )
        )
    }

@app.post('/api/browser/open-session')
def open_session(body: OpenSessionInput = OpenSessionInput()):
    msg = browser.open_user_browser_session(body.url)
    return {'ok': True, 'message': msg}

@app.get('/api/browser/session-status')
def session_status():
    p_dir = store.DATA / 'browser_profile'
    exists = p_dir.exists() and any(p_dir.iterdir()) if p_dir.exists() else False
    return {'profile_exists': exists}

@app.post('/api/jobs/{job_id}/skip')
def skip(job_id:str):
    busy(job_id); store.update_job(job_id,state='skipped'); store.event(job_id,'Job skipped by you.')
    return {'ok':True}

@app.post('/api/jobs/{job_id}/resolve')
def resolve(job_id:str,body:Resolution):
    job=store.get_job(job_id)
    with store.db() as c:
        if c.execute("SELECT id FROM runs WHERE target=? AND state IN ('queued','running')",(job_id,)).fetchone(): raise ValueError('Wait for the current operation to finish.')
    if body.status=='submitted':
        store.update_job(job_id,state='submitted',receipt={'text':body.note,'at':store.now(),'url':job.get('url',''),'manual':True})
    else:
        if job['state']=='submitted': raise ValueError('A confirmed submitted application cannot be reset for resubmission.')
        store.update_job(job_id,state='awaiting_review' if store.get_package(job_id) else 'shortlisted')
        with store.db() as c: c.execute('UPDATE packages SET approved_hash=NULL WHERE job_id=?',(job_id,))
    store.event(job_id,'You recorded '+body.status.replace('_',' ')+': '+body.note)
    return {'ok':True}

@app.get('/api/jobs/{job_id}/documents/{fmt}')
def download(job_id:str,fmt:Literal['pdf','docx','cover_letter_pdf','cover_letter_docx']):
    package=store.get_package(job_id)
    if not package: raise HTTPException(404,'Prepare a CV first.')
    verify_files(package)
    if fmt not in package['files']: raise HTTPException(404,'Draft a cover letter first.')
    path=store.DATA/package['files'][fmt]['path']
    name='Walid_Hamdy_'+('Cover_Letter_' if fmt.startswith('cover_letter') else 'CV_')+store.get_job(job_id)['id'][:8]+'.'+fmt.split('_')[-1]
    return FileResponse(path,filename=name)

@app.get('/api/jobs/{job_id}/receipt')
def receipt(job_id:str):
    r=store.get_job(job_id).get('receipt',{})
    if not r.get('path'): raise HTTPException(404,'No screenshot receipt was saved.')
    path=(store.DATA/r['path']).resolve()
    if not path.is_relative_to(store.DATA.resolve()): raise HTTPException(404)
    return FileResponse(path,media_type='image/png')

dist=store.ROOT/'frontend'/'dist'
if dist.exists():
    assets_dir = dist / 'assets'
    if assets_dir.is_dir():
        app.mount('/assets', StaticFiles(directory=assets_dir), name='dashboard_assets')

    @app.get('/')
    def serve_index():
        index_file = dist / 'index.html'
        if index_file.is_file():
            return FileResponse(index_file, media_type='text/html')
        raise HTTPException(404, 'Frontend index not found.')

    @app.get('/{full_path:path}')
    def serve_frontend_spa(full_path: str, request: Request):
        if full_path.startswith('api/') or full_path == 'api':
            raise HTTPException(404, 'API endpoint not found.')
        target = (dist / full_path).resolve()
        if target.is_file() and target.is_relative_to(dist.resolve()):
            return FileResponse(target)
        if full_path.startswith('assets/') or ('.' in full_path.split('/')[-1] and not full_path.endswith('.html')):
            raise HTTPException(404, 'Asset not found.')
        index_file = dist / 'index.html'
        if index_file.is_file():
            return FileResponse(index_file, media_type='text/html')
        raise HTTPException(404, 'Frontend build not found.')
