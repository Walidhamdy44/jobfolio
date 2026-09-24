import copy
import json
import time
from pathlib import Path
import pytest
from backend import store, tailoring, profile, browser, network, providers, worker
from backend.documents import generate,verify_files
from pypdf import PdfReader
from docx import Document

def prepared(job):
    tailoring.prepare(job['id'],'local')
    return store.get_package(job['id'])

def review(client,job,p):
    return client.put(f"/api/jobs/{job['id']}/review",json={'package_hash':p['hash'],'cv_reviewed':True,'coverage_reviewed':True,'answers':p['answers'],'supports':[r['support'] for r in p['requirements']]})

def test_master_import(client):
    p=client.get('/api/workspace').json()['profile']
    assert p['name']=='Walid Hamdy'
    assert p['email']=='walidhamdy314@gmail.com'
    text=profile.cv_text(p)
    assert all(x in text for x in ('Boutiqaat','Skyloov','10/2025','Minya University','2.90'))
    assert len(profile.evidence(p))==sum(len(s['items']) for s in p['sections'])

def test_duplicate_jobs(client,job):
    r=client.post('/api/jobs',json={k:job[k] for k in ('title','company','location','description')})
    assert not r.json()['created']
    assert len(client.get('/api/workspace').json()['jobs'])==1

def test_coverage_math_and_local_conservatism(client,job):
    rows=[{'weight':3,'support':'full'},{'weight':1,'support':'missing'}]
    assert tailoring.score(rows)==75
    p=prepared(job)
    assert all(r['support']!='full' for r in p['requirements'])
    assert p['mode']=='local' and p['score']<=50
    assert p['changes']==[]
    assert next(r for r in p['requirements'] if 'Kubernetes' in r['text'])['support']=='missing'
    assert set(profile.evidence(p['profile']).values())==set(profile.evidence(store.setting('profile')).values())

def test_cv_exports_preserve_content(client,job):
    p=prepared(job)
    pdf_text=' '.join(x.extract_text() for x in PdfReader(store.DATA/p['files']['pdf']['path']).pages)
    docx_text=' '.join(x.text for x in Document(store.DATA/p['files']['docx']['path']).paragraphs)
    norm=lambda text:' '.join(text.split())
    for item in profile.evidence(p['profile']).values():
        assert norm(item) in norm(pdf_text)
        assert norm(item) in norm(docx_text)
    assert client.get(f"/api/jobs/{job['id']}/documents/pdf").status_code==200

def test_approval_required_and_stale_hash(client,job):
    p=prepared(job)
    assert client.post(f"/api/jobs/{job['id']}/submit",json={'package_hash':p['hash']}).status_code==400
    assert client.post(f"/api/jobs/{job['id']}/approve",json={'package_hash':p['hash']}).status_code==400
    assert review(client,job,p).status_code==200
    current=store.get_package(job['id'])
    assert client.post(f"/api/jobs/{job['id']}/approve",json={'package_hash':p['hash']}).status_code==409
    assert client.post(f"/api/jobs/{job['id']}/approve",json={'package_hash':current['hash']}).status_code==200
    assert store.get_package(job['id'])['approved']
    assert review(client,job,store.get_package(job['id'])).status_code==200
    assert not store.get_package(job['id'])['approved']

def test_changed_file_blocks_approval(client,job):
    p=prepared(job); review(client,job,p); p=store.get_package(job['id'])
    (store.DATA/p['files']['pdf']['path']).write_bytes(b'changed')
    r=client.post(f"/api/jobs/{job['id']}/approve",json={'package_hash':p['hash']})
    assert r.status_code==400 and 'changed' in r.json()['detail']

def test_changed_master_requires_new_package(client,job):
    p=prepared(job)
    master=store.setting('profile'); body={k:v for k,v in master.items() if k not in ('source_file','revision')}
    assert client.put('/api/profile',json=body).status_code==200
    assert review(client,job,p).status_code==400

def test_missing_api_keys_clear_error(client,job):
    assert client.post('/api/search').status_code==400
    r=client.post(f"/api/jobs/{job['id']}/prepare",json={'mode':'ai'})
    assert r.status_code==400 and 'Connect an API key' in r.json()['detail']
    assert client.get('/api/workspace').json()['search_results']['items']==[]

def test_csrf_and_dns_rebinding(client):
    r=client.post('/api/search',headers={'Origin':'https://evil.example'})
    assert r.status_code==403
    r=client.get('/api/workspace',headers={'Host':'evil.example'})
    assert r.status_code==400
    for url in ('http://localhost','https://127.0.0.1/','https://user:pass@example.com','https://[::1]/'):
        with pytest.raises(ValueError): network.public_url(url)

def test_identity_normalization():
    assert network.canonical('https://jobs.lever.co/acme/abc/apply?utm_source=test')==network.canonical('https://jobs.lever.co/acme/abc')

def test_uncertain_blocks_retry_and_can_only_reset_explicitly(client,job):
    p=prepared(job); store.update_job(job['id'],state='uncertain')
    for action,body in [('prepare',{'mode':'local'}),('approve',{'package_hash':p['hash']}),('submit',{'package_hash':p['hash']})]:
        assert client.post(f"/api/jobs/{job['id']}/{action}",json=body).status_code==400
    assert client.post(f"/api/jobs/{job['id']}/resolve",json={'status':'not_submitted','note':'Checked employer page; no application was received.'}).status_code==200
    assert store.get_job(job['id'])['state']=='awaiting_review'
    assert not store.get_package(job['id'])['approved']

def test_submitted_cannot_reset(client,job):
    store.update_job(job['id'],state='submitted')
    assert client.post(f"/api/jobs/{job['id']}/resolve",json={'status':'not_submitted','note':'Try to reset a completed application'}).status_code==400

def test_restart_marks_inflight_uncertain(client,job):
    store.update_job(job['id'],state='submitting')
    store.init()
    assert store.get_job(job['id'])['state']=='uncertain'

def test_unknown_evidence_cannot_be_marked_supported(client,job):
    p=prepared(job); data=store.package_data(p); data['requirements'][0]['evidence_ids']=[]
    store.revise_package(p['id'],data); p=store.get_package(job['id'])
    r=client.put(f"/api/jobs/{job['id']}/review",json={'package_hash':p['hash'],'cv_reviewed':True,'coverage_reviewed':True,'answers':{},'supports':['full']+[r['support'] for r in p['requirements'][1:]]})
    assert r.status_code==400

def test_numeric_claim_guard():
    assert not tailoring.guard_rewrite('Built four applications.', 'Built 10 applications.')
    assert not tailoring.guard_rewrite('4 years experience.', '10 years experience.')
    assert tailoring.guard_rewrite('Improved speed by 20%.','Speed increased by 20%.')

def test_required_upload_and_answers():
    package={'form':{'fields':[{'key':'#x','label':'Sponsorship','type':'text','required':True}, {'key':'#y','label':'Cover letter','type':'file','required':True}]},'answers':{}}
    assert len(browser.missing_answers(package))==2

def test_cover_letter_invalidates_review_and_is_downloadable(client,job):
    p=prepared(job); review(client,job,p); p=store.get_package(job['id'])
    client.post(f"/api/jobs/{job['id']}/approve",json={'package_hash':p['hash']})
    tailoring.cover_letter(job['id'],'local')
    current=store.get_package(job['id'])
    assert not current['approved'] and not current['cv_reviewed']
    assert job['title'] in current['cover_letter']
    assert client.get(f"/api/jobs/{job['id']}/documents/cover_letter_pdf").status_code==200
    assert current['hash']!=p['hash']

def test_worker_lifecycle(client):
    rid=worker.enqueue('test',None,lambda:'Completed the controlled local test successfully.')
    for _ in range(100):
        with store.db() as c: r=c.execute('SELECT * FROM runs WHERE id=?',(rid,)).fetchone()
        if r['state']=='completed': break
        time.sleep(.01)
    assert r['state']=='completed'

def test_submission_claim_prevents_duplicate(client,job,monkeypatch):
    p=prepared(job)
    data=store.package_data(p); data.update(cv_reviewed=True,coverage_reviewed=True,form={'fields':[],'fingerprint':'test'})
    store.revise_package(p['id'],data); p=store.get_package(job['id'])
    assert client.post(f"/api/jobs/{job['id']}/approve",json={'package_hash':p['hash']}).status_code==200
    monkeypatch.setattr(browser,'application_url',lambda job:'https://jobs.lever.co/example/test')
    calls=[]
    monkeypatch.setattr(worker,'enqueue',lambda *args:calls.append(args) or 'queued-test')
    assert client.post(f"/api/jobs/{job['id']}/submit",json={'package_hash':p['hash']}).status_code==200
    assert client.post(f"/api/jobs/{job['id']}/submit",json={'package_hash':p['hash']}).status_code==400
    assert len(calls)==1

def test_model_cannot_inject_unfounded_rewrites(client,job,monkeypatch):
    original=store.setting('profile'); master=copy.deepcopy(original)
    editable=master['sections'][0]['items'][0]
    def fake(schema,instruction,payload):
        if schema==providers.Rewrites:
            return providers.Rewrites(changes=[providers.Rewrite(evidence_id=editable['id'],text='Expert Kubernetes architect.')])
        return providers.Checks(checks=[providers.Check(evidence_id=editable['id'],supported=False,reason='Not supported')])
    monkeypatch.setattr(providers,'ask',fake)
    assert tailoring.rewrite_profile(master,job,[])==[]
    assert profile.evidence(master)==profile.evidence(original)

def test_spa_fallback_routes(client):
    r_root = client.get('/')
    assert r_root.status_code == 200
    assert 'text/html' in r_root.headers.get('content-type', '')

    r_opps = client.get('/opportunities')
    assert r_opps.status_code == 200
    assert 'text/html' in r_opps.headers.get('content-type', '')

    r_nested = client.get('/jobs/76ee951a09544b7d9a91f9560ed5c24b/cv')
    assert r_nested.status_code == 200
    assert 'text/html' in r_nested.headers.get('content-type', '')

    r_missing_api = client.get('/api/unknown_route')
    assert r_missing_api.status_code == 404

    r_missing_asset = client.get('/assets/missing_file.js')
    assert r_missing_asset.status_code == 404

def test_qa_03_preferred_qualifications_extraction():
    fixture = """QA TEST DATA. This is a synthetic job for local testing only. Do not apply.
Responsibilities: Build accessible React interfaces and maintain TypeScript applications. Write unit tests and integrate REST APIs.
Required qualifications: Experience with React, TypeScript, JavaScript, HTML, CSS, Git, and REST APIs.
Preferred qualifications: Next.js, automated testing, and web accessibility.
Location: Remote, Egypt."""
    reqs = tailoring.extract_requirements(fixture, ai=False)
    assert len(reqs) == 3
    priorities = [r['priority'] for r in reqs]
    assert priorities.count('required') == 2
    assert priorities.count('preferred') == 1
    pref = [r for r in reqs if r['priority'] == 'preferred'][0]
    assert 'Next.js' in pref['text'] or 'automated testing' in pref['text']


def test_local_requirements_ignore_employer_marketing():
    description = """About the company
The employer has extensive experience developing global business services and invests in technical skills.
Responsibilities
Build and maintain React applications with the engineering team.
Required Skills
Experience with TypeScript, React, and REST APIs.
Preferred Skills
Experience with Storybook and component testing.
Our commitment to you
Develop your skills while experiencing excellent benefits and collaboration.
"""
    rows = tailoring.extract_requirements(description, ai=False)
    assert len(rows) == 3
    assert [row['priority'] for row in rows] == ['required', 'required', 'preferred']
    assert all('employer' not in row['text'].lower() and 'benefits' not in row['text'].lower() for row in rows)


def test_ai_extraction_keeps_explicit_requirements_it_omits(monkeypatch):
    description = """Responsibilities
Build React web applications and maintain frontend components.
Required Skills
Strong experience with React, TypeScript, AWS Lambda and CloudWatch monitoring systems.
Preferred Skills
Experience with Storybook and component testing.
"""
    quoted = 'Build React web applications and maintain frontend components.'
    result = providers.Requirements(requirements=[providers.Requirement(
        text=quoted, priority='required', source_quote=quoted,
    )])
    monkeypatch.setattr(providers, 'ask', lambda *args, **kwargs: result)
    rows = tailoring.extract_requirements(description, ai=True)
    texts = [row['text'] for row in rows]
    assert len(rows) == 3
    assert any('AWS Lambda' in text for text in texts)
    assert any('Storybook' in text and row['priority'] == 'preferred' for text, row in zip(texts, rows))


def test_prepare_fetches_full_description_before_queueing(client, monkeypatch):
    brief = 'LinkedIn search summary for a frontend position in Cairo.'
    job, _ = store.add_job({
        'title': 'Frontend Engineer', 'company': 'Example', 'location': 'Cairo, Egypt',
        'url': 'https://www.linkedin.com/jobs/view/frontend-engineer-1234567890',
        'description': brief, 'verified': False,
    })
    full = 'Responsibilities\nBuild accessible React applications and maintain tests.\nRequired Skills\nExperience with TypeScript, React, REST APIs and frontend architecture.'
    monkeypatch.setattr(network, 'import_url', lambda url: {'description': full, 'verified': True})
    monkeypatch.setattr(worker, 'enqueue', lambda *args, **kwargs: 'test-run')
    response = client.post(f"/api/jobs/{job['id']}/prepare", json={'mode': 'local'})
    assert response.status_code == 200
    assert store.get_job(job['id'])['description'] == full
    assert store.get_job(job['id'])['verified'] is True


def test_prepare_rejects_unverified_summary(client, monkeypatch):
    job, _ = store.add_job({
        'title': 'Frontend Engineer', 'company': 'Example', 'location': 'Cairo, Egypt',
        'url': 'https://www.linkedin.com/jobs/view/frontend-engineer-1234567891',
        'description': 'A brief search summary for an engineering role.', 'verified': False,
    })
    monkeypatch.setattr(network, 'import_url', lambda url: {'description': 'Still only a snippet.', 'verified': False})
    response = client.post(f"/api/jobs/{job['id']}/prepare", json={'mode': 'local'})
    assert response.status_code == 400
    assert 'full job description' in response.json()['detail']
    assert store.get_package(job['id']) is None

def test_qa_01_update_job_details(client, job):
    store.update_job(job['id'], last_error='Some previous error')
    res = client.patch(f"/api/jobs/{job['id']}", json={'description': 'Brand new complete description with responsibilities and requirements for frontend engineer.'})
    assert res.status_code == 200
    updated = store.get_job(job['id'])
    assert 'Brand new complete description' in updated['description']
    assert updated.get('last_error') is None

def test_qa_09_clean_html_text():
    from backend.search import clean_html_text
    raw = '&lt;div class=&quot;content-intro&quot;&gt;&lt;p&gt;Software Engineer &amp;#8211; Contract&lt;/p&gt;&lt;/div&gt;&nbsp;'
    cleaned = clean_html_text(raw)
    assert cleaned == 'Software Engineer – Contract'

def test_qa_13_worker_validation_error_mapping():
    from pydantic import BaseModel, Field
    from backend import worker
    class DummyModel(BaseModel):
        count: int = Field(gt=10)
    try:
        DummyModel(count=2)
    except Exception as exc:
        msg = worker.error_message(exc)
        assert 'The AI provider returned an invalid structured response' in msg
        assert 'https://errors.pydantic.dev' not in msg
