import copy
import re
from . import profile as profiles, providers, store

STOP = set('a an the and or to of in on for with using experience knowledge understanding ability strong excellent required preferred must have years year working work build develop skills proficiency'.split())
ALIASES = {'react.js':'react','reactjs':'react','next.js':'nextjs','next js':'nextjs','typescript':'typescript','javascript':'javascript','node.js':'nodejs','restful':'rest','rest apis':'rest api'}
TECH_TERMS=set('kubernetes docker aws azure gcp react nextjs angular vue typescript javascript python java golang rust c++ c# sql postgresql mysql mongodb redis graphql rest terraform jenkins figma pytorch tensorflow spark hadoop'.split())

def tokens(text):
    text = text.casefold()
    for a,b in ALIASES.items(): text = text.replace(a,b)
    return set(re.findall(r'[a-z][a-z0-9+#.-]*', text)) - STOP

def normalized(text):
    return re.sub(r'[\s\u2010-\u2015\u2018\u2019\u201c\u201d]+', ' ', text).strip().casefold()

def extract_requirements(description, ai):
    if ai:
        rows = providers.ask(providers.Requirements,
            'Extract ALL distinct substantive candidate requirements, including responsibilities, education, years, language and mandatory qualifications. Split compound criteria into atomic requirements, but retain conditions and negation. Do not extract company benefits. Required by default; preferred only if explicit. source_quote must be an exact excerpt from the description. No more than 60 requirements.',
            {'description':description}).model_dump()['requirements']
        desc_norm = normalized(description)
        for r in rows:
            quote = r.get('source_quote', '').strip()
            if not quote:
                raise ValueError('Requirement extraction returned empty quote. Please try again or use local preparation.')
            q_norm = normalized(quote)
            if q_norm not in desc_norm:
                words = [w for w in q_norm.split() if len(w) > 2]
                matched = any(' '.join(words[i:i+4]) in desc_norm for i in range(max(1, len(words)-3))) if len(words) >= 4 else False
                if not matched:
                    raise ValueError('Requirement extraction did not preserve source quotes. Please try again or use local preparation.')
    else:
        rows = []
        current_priority = None
        for raw_line in re.split(r'[\r\n;]+', description):
            line = raw_line.strip(' •\t-*#')
            if not line:
                continue

            preferred_heading = re.match(
                r'^(?:preferred(?: skills| qualifications)?|nice[\s\-_]to[\s\-_]have|bonus|desirable|optional|what we would like you to have)\s*:?(.*)$',
                line, re.I,
            )
            required_heading = re.match(
                r'^(?:required(?: skills| qualifications)?|requirements?|qualifications?|responsibilit(?:y|ies)|duties|what you must have|what you[\'’]ll do|skills and (?:experience|qualifications))\s*:?(.*)$',
                line, re.I,
            )
            if preferred_heading:
                current_priority = 'preferred'
                line = preferred_heading.group(1).strip(' :')
            elif required_heading:
                current_priority = 'required'
                line = required_heading.group(1).strip(' :')
            elif re.match(r'^as .{10,100} you will:?$', line, re.I):
                current_priority = 'required'
                continue
            elif re.match(
                r'^(?:about (?:the |this )?(?:role|company)|connect (?:to|with)|our (?:commitment|culture|benefits)|'
                r'qualities we are looking for|location\s*:|how we work|benefits|equal opportunity)',
                line, re.I,
            ):
                current_priority = None
                continue

            if current_priority is None or not 20 <= len(line) <= 450:
                continue
            rows.append({'text': line, 'priority': current_priority, 'source_quote': line})
        rows = rows[:60]
    seen = {}
    result = []
    for r in rows:
        key = normalized(r['text'])
        if key not in seen:
            seen[key] = len(result)
            result.append(r)
        elif r['priority'] == 'required':
            result[seen[key]]['priority'] = 'required'
    if not result:
        raise ValueError('No requirements could be identified. Add a complete description with requirements, or connect AI extraction.')
    return result

def guard_rewrite(old, new):
    """Numeric changes are never silently introduced by prose editing."""
    return set(re.findall(r'\d+(?:[./]\d+)*%?', new)).issubset(set(re.findall(r'\d+(?:[./]\d+)*%?', old)))

def rewrite_profile(profile, job, requirements):
    original = profiles.evidence(profile)
    # Only prose; role headings, dates, education, skills and contact remain exact.
    editable = {}
    for section in profile['sections']:
        if section['title'] == 'Summary':
            editable.update({i['id']:i['text'] for i in section['items']})
        if section['title'] in ('Professional Experience','Selected Projects'):
            for i in section['items']:
                if not re.search(r'\d{2}/\d{4}| - |\.com\b|\.app\b',i['text']): editable[i['id']]=i['text']
    try:
        proposed = providers.ask(providers.Rewrites,
            'Tailor the provided editable CV prose to the requirements using ONLY the facts in EACH original entry. Preserve all qualifications, scope, tense, seniority and quantities. Do not move experience between employers. Do not add any technology not already in that entry. Prefer clearer wording to keyword stuffing. Return only changed entries; keep each evidence_id.',
            {'editable_entries':editable,'requirements':requirements,'job_title':job['title']}).changes
    except Exception as exc:
        store.event(job.get('id'), f'AI prose adaptation notice: {exc}. Retaining original verified wording.')
        return []

    candidates={r.evidence_id:r.text.strip() for r in proposed if r.evidence_id in editable and r.text.strip() and guard_rewrite(editable[r.evidence_id],r.text)}
    changes=[]
    if candidates:
        try:
            checks=providers.ask(providers.Checks,
                'Audit every proposed CV rewrite against its original entry. supported=true ONLY if every factual claim is entailed by that original entry, with no added technologies, inflated ownership, qualifications, metrics or years. Treat merely related skills as unsupported. Be conservative.',
                {'entries':[{'evidence_id':k,'original':editable[k],'rewrite':v} for k,v in candidates.items()]}).checks
            allowed={c.evidence_id for c in checks if c.supported}
        except Exception:
            allowed=set()

        for section in profile['sections']:
            for item in section['items']:
                if item['id'] in allowed:
                    changes.append({'id':item['id'],'before':item['text'],'after':candidates[item['id']]})
                    item['text']=candidates[item['id']]
    return changes

def coverage(requirements, profile, ai):
    ev=profiles.evidence(profile)
    rows=[]
    mapped={}
    if ai:
        try:
            result=providers.ask(providers.Coverages,
                'Assess EVERY indexed requirement against the finished CV entries. Full only if the ENTIRE criterion is supported; partial if some but not all is supported; missing otherwise. Technology mention alone does not prove years, mastery, certification or production use. Return valid evidence_ids and a concise explanation. Do not give an overall score.',
                {'requirements':[{'index':i,**r} for i,r in enumerate(requirements)],'cv_entries':ev}).coverage
            mapped={c.requirement_index:c for c in result}
        except Exception:
            ai = False
    for i,r in enumerate(requirements):
        if ai:
            item=mapped.get(i)
            ids=[k for k in (item.evidence_ids if item else []) if k in ev]
            support=item.support if item and ids else 'missing'
            explanation=item.explanation if item else 'No assessment returned; counted as missing.'
        else:
            wanted=tokens(r['text'])
            ranked=sorted(((len(wanted & tokens(text))/max(1,len(wanted)),k) for k,text in ev.items()),reverse=True)
            best, eid=ranked[0] if ranked else (0,'')
            missing_tech=(wanted & TECH_TERMS)-tokens(' '.join(ev.values()))
            ids=[eid] if best>=0.3 and not missing_tech else []
            # Local matching never asserts full semantic support.
            support='partial' if ids else 'missing'
            explanation='Related wording found; confirm the complete requirement yourself.' if ids else 'No clear wording match in the CV.'
        rows.append({**r,'support':support,'weight':3 if r['priority']=='required' else 1,'evidence_ids':ids,
                     'evidence':[{'id':k,'text':ev[k]} for k in ids], 'explanation':explanation})
    return rows

def score(rows):
    total=sum(r['weight'] for r in rows)
    return round(100*sum(r['weight']*{'full':1,'partial':0.5,'missing':0}[r['support']] for r in rows)/total,1) if total else 0

def prepare(job_id, mode='local', progress=None):
    if progress: progress('Reading job details and master profile…')
    job=store.get_job(job_id)
    if job['state'] in ('submitted','submitting','uncertain'):
        raise ValueError('Resolve this application status before preparing another package.')
    master=store.setting('profile')
    if not master: raise ValueError('Import your master CV first.')
    profile=copy.deepcopy(master)
    ai=mode=='ai'
    if progress: progress(f"Extracting requirements ({'AI analysis' if ai else 'local criteria analysis'})…")
    reqs=extract_requirements(job['description'],ai)
    if progress: progress(f"Extracted {len(reqs)} requirements. Tailoring profile experience…")
    changes=rewrite_profile(profile,job,reqs) if ai else []
    # Reorder individual skill rows by job relevance; retain all source facts.
    for s in profile['sections']:
        if s['title']=='Technical Skills': s['items'].sort(key=lambda i:-len(tokens(i['text']) & tokens(job['description'])))
    if progress: progress('Auditing requirement coverage against source evidence…')
    rows=coverage(reqs,profile,ai)
    calc_score = score(rows)
    if progress: progress(f'Calculated {calc_score}% requirement coverage. Compiling executive PDF & Word…')
    package={'job_id':job_id,'job_snapshot':job,'profile_revision':master['revision'],'profile':profile,
        'source_evidence':profiles.evidence(master),'requirements':rows,'score':calc_score,'changes':changes,
        'mode':mode,'coverage_reviewed':False,'cv_reviewed':False,'form':None,'answers':{},'files':{},
        'note':'AI-assessed coverage; review each requirement and CV statement.' if ai else 'Local preparation preserves your wording. Coverage is provisional, not a complete semantic assessment.'}
    from .documents import generate
    package['files']=generate(profile,store.uid())
    # Publish only complete exports. A half-built package must never replace a review.
    package_id=store.save_package(job_id,package)
    store.update_job(job_id,state='awaiting_review',score=package['score'])
    store.event(job_id,'CV package prepared. Review required before approval.')
    if progress: progress(f'CV prepared ({calc_score}% coverage). Ready for your review.')
    return package_id

def cover_letter(job_id, mode='local', progress=None):
    if progress: progress('Loading job posting and master profile…')
    package=store.get_package(job_id)
    if not package: raise ValueError('Prepare a CV first.')
    job=store.get_job(job_id)
    if job['state'] in ('submitted','submitting','uncertain'): raise ValueError('Resolve submission status before changing this package.')
    data=store.package_data(package)
    cv=data['profile']; ev=profiles.evidence(cv)
    summary=next((s['items'][0]['text'] for s in cv['sections'] if s['title']=='Summary'),'')
    if mode=='ai':
        if progress: progress('Drafting personalized cover letter with AI…')
        text=providers.ask(providers.Letter,
            'Write a concise English cover letter, 180-250 words, signed with the provided name. Use ONLY supplied CV evidence. Explain relevance to the target role without claiming missing skills. No invented company praise, achievements, metrics, availability, authorization or promises. Plain text paragraphs only.',
            {'name':cv['name'],'job_title':job['title'],'company':job['company'],'requirements':job['description'],'cv_evidence':ev}).text
        if progress: progress('Auditing factual claims against master profile…')
        audit=providers.ask(providers.Checks,
            'Audit this cover letter. Return one check with evidence_id cover_letter. Every personal factual claim must be supported by the CV. Target company and job title are application context, not past employment. Reject invented metrics, skills, ownership or eligibility.',
            {'letter':text,'cv_evidence':ev,'target_title':job['title'],'target_company':job['company']}).checks
        if not any(c.evidence_id=='cover_letter' and c.supported for c in audit) or not guard_rewrite(' '.join(ev.values())+job['title']+job['company'],text):
            raise ValueError('The cover-letter draft did not pass its factual check. Try again or use a local draft.')
    else:
        if progress: progress('Drafting local cover letter based on CV summary…')
        text=f"Dear Hiring Team,\n\nI am applying for the {job['title']} position at {job['company']}.\n\nMy background, as described in my CV:\n\n{summary}\n\nI would welcome the opportunity to discuss how this experience relates to your team’s needs. Thank you for considering my application.\n\nKind regards,\n{cv['name']}"
    data['cover_letter']=text
    letter_profile={**cv,'headline':f"Application for {job['title']}",'sections':[{'title':'Cover letter','items':[{'id':f'l{i}','text':s} for i,s in enumerate(text.split('\n\n')) if s.strip()]}]}
    if progress: progress('Generating PDF and Word cover letter downloads…')
    from .documents import generate
    files=generate(letter_profile,store.uid())
    for fmt in ('pdf','docx'): data['files']['cover_letter_'+fmt]=files[fmt]
    for f in (data.get('form') or {}).get('fields',[]):
        if re.search(r'cover.?letter',f['label'],re.I) and f['type'] in ('textarea','text'):
            data['answers'][f['key']]=text
    data['cv_reviewed']=False
    store.revise_package(package['id'],data)
    store.update_job(job_id,state='awaiting_review')
    store.event(job_id,'Cover letter drafted. Review the complete package again before approval.')
    if progress: progress('Cover letter drafted and verified. Ready for review.')
    return 'Cover letter and downloads are ready. Review the new draft before approving.'
