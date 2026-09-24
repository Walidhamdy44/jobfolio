"""Conservative hosted-form adapter. Unknown controls stop instead of guessing."""
import re
from urllib.parse import urlparse
# pyrefly: ignore [missing-import]
from playwright.sync_api import sync_playwright
from . import store, network

FIELDS_JS = r'''() => {
 const els=[...document.querySelectorAll('input,textarea,select')];
 return els.filter(e => e.type !== 'hidden' && e.type !== 'submit' && e.type !== 'button' && (e.type==='file' || e.getClientRects().length)).map((e,index)=>{
   const label=[...(e.labels||[])].map(l=>l.innerText.trim()).join(' ') || e.getAttribute('aria-label') || e.getAttribute('placeholder') || e.name || e.id;
   const key=e.id ? '#'+CSS.escape(e.id) : e.name ? e.tagName.toLowerCase()+'[name='+JSON.stringify(e.name)+']'+(e.type==='radio'?'[value='+JSON.stringify(e.value)+']':'') : '';
   return {key,label:label.replace(/\s+/g,' ').slice(0,500),type:e.tagName==='SELECT'?'select':e.type||'textarea',required:e.required || e.getAttribute('aria-required')==='true' || /\*/.test(label),options:e.tagName==='SELECT'?[...e.options].map(o=>({label:o.text,value:o.value})):[],value:e.type==='radio'?e.value:'', index};
 });
}'''

def application_url(job):
    if network.platform(job['url'])=='manual': raise ValueError('This website requires a manual application. Download your package and open its link.')
    url=job['url']
    if network.platform(url)=='lever' and not urlparse(url).path.rstrip('/').endswith('/apply'): url=url.rstrip('/')+'/apply'
    return network.public_url(url)

def fingerprint(fields):
    return store.digest([{k:f[k] for k in ('key','label','type','required','options','value')} for f in fields])

def read_fields(page):
    fields=page.evaluate(FIELDS_JS)
    if not fields: raise ValueError('No supported application form was found. Open the job site to continue manually.')
    if any(not f['key'] for f in fields): raise ValueError('This form contains controls without stable identifiers. Continue manually.')
    if len({f['key'] for f in fields})!=len(fields): raise ValueError('This form contains ambiguous controls. Continue manually.')
    return fields

def blocked(page):
    return page.locator('iframe[src*="captcha"]:visible, .g-recaptcha:visible, .h-captcha:visible, [data-sitekey]:visible').count()>0 or bool(re.search(r'verify you are human|security verification|sign in to continue',page.locator('body').inner_text(),re.I))

def open_page(browser, url):
    context=browser.new_context()
    # No user browsing profile is used or stored; all requests must remain public.
    checked=set()
    def route(request_route):
        u=request_route.request.url
        if u.startswith('data:'): request_route.continue_(); return
        host=urlparse(u).netloc
        try:
            if host not in checked: network.public_url(u); checked.add(host)
            if urlparse(u).scheme!='https': raise ValueError('HTTPS required')
            request_route.continue_()
        except Exception: request_route.abort()
    context.route('**/*',route)
    page=context.new_page()
    page.goto(url,wait_until='domcontentloaded',timeout=45000)
    page.wait_for_timeout(1800)
    return context,page

def inspect(job_id, progress=None):
    job=store.get_job(job_id); package=store.get_package(job_id)
    if not package: raise ValueError('Prepare a CV before inspecting the application form.')
    if job['state'] in ('submitting','submitted','uncertain'): raise ValueError('Resolve application status before inspecting again.')
    if progress: progress('Launching browser to inspect application form…')
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        try:
            if progress: progress(f"Connecting to {network.platform(job['url'])} portal…")
            context,page=open_page(browser,application_url(job))
            if blocked(page): raise ValueError('The site requires human verification. Use the manual application link.')
            if progress: progress('Reading application controls and required questions…')
            fields=read_fields(page)
        finally: browser.close()
    profile=package['profile']; answers={}
    known={'first name':profile['name'].split()[0],'last name':profile['name'].split()[-1], 'full name':profile['name'],'name':profile['name'],
           'email':profile['email'],'email address':profile['email'],'phone':profile['phone'],'phone number':profile['phone']}
    for f in fields:
        label=f['label'].strip(' *').casefold()
        if f['type'] in ('text','email','tel','textarea') and label in known: answers[f['key']]=known[label]
        if f['type'] in ('text','textarea') and re.search(r'cover.?letter',label) and package.get('cover_letter'): answers[f['key']]=package['cover_letter']
    data=store.package_data(package)
    data['form']={'fields':fields,'fingerprint':fingerprint(fields),'inspected_at':store.now()}
    data['answers']=answers
    store.revise_package(package['id'],data)
    store.update_job(job_id,state='awaiting_review')
    store.event(job_id,'Application questions retrieved. Review answers before approval.')
    return 'Application questions are ready for review.'

def missing_answers(package):
    form=package.get('form')
    if not form: return ['Inspect the form before automated submission.']
    missing=[]
    groups={}
    for f in form['fields']:
        if f['type']=='radio': groups.setdefault(f['key'].split('[value=')[0],[]).append(f)
    for members in groups.values():
        if sum(package['answers'].get(f['key'])=='true' for f in members)>1:
            missing.append('Choose only one answer for: '+members[0]['label'])
    for f in form['fields']:
        if f['type']=='file':
            if re.search(r'cover.?letter',f['label'],re.I):
                if f['required'] and not package.get('files',{}).get('cover_letter_pdf'): missing.append('Draft a cover letter for: '+f['label'])
            elif not re.search(r'resume|cv\b',f['label'],re.I) and f['required']: missing.append('Unsupported required upload: '+f['label'])
        elif f['type']=='radio':
            group=f['key'].split('[value=')[0]
            members=[r for r in form['fields'] if r['type']=='radio' and r['key'].split('[value=')[0]==group]
            if f['required'] and not any(package['answers'].get(r['key'])=='true' for r in members): missing.append(f['label'])
        elif f['required'] and (not str(package['answers'].get(f['key'],'')).strip() or (f['type']=='checkbox' and package['answers'].get(f['key'])!='true')):
            missing.append(f['label'])
        elif f['type']=='select' and package['answers'].get(f['key']) and package['answers'][f['key']] not in {o['value'] for o in f['options']}:
            missing.append('Choose a valid option for: '+f['label'])
    return list(dict.fromkeys(missing))

def submit(job_id, package, progress=None):
    from .documents import verify_files
    job=store.get_job(job_id)
    if progress: progress('Verifying application files and package integrity…')
    verify_files(package)
    if missing_answers(package): raise ValueError('Complete all required application answers before submitting.')
    clicked=False
    if progress: progress('Launching secure browser session…')
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        try:
            if progress: progress(f"Connecting to {network.platform(job['url'])} portal…")
            context,page=open_page(browser,application_url(job))
            if blocked(page): raise ValueError('Human verification is required. Continue manually.')
            if progress: progress('Verifying application form controls…')
            fields=read_fields(page)
            if fingerprint(fields)!=package['form']['fingerprint']: raise ValueError('The application form changed. Inspect it and approve the updated questions.')
            if progress: progress('Populating verified answers and attaching documents…')
            for f in fields:
                locator=page.locator(f['key'])
                value=str(package['answers'].get(f['key'],''))
                if f['type']=='file' and re.search(r'resume|cv\b',f['label'],re.I):
                    locator.set_input_files(str(store.DATA/package['files']['pdf']['path']))
                elif f['type']=='file' and re.search(r'cover.?letter',f['label'],re.I) and package['files'].get('cover_letter_pdf'):
                    locator.set_input_files(str(store.DATA/package['files']['cover_letter_pdf']['path']))
                elif f['type']=='select' and value: locator.select_option(value=value)
                elif f['type'] in ('checkbox','radio'):
                    if value=='true': locator.check()
                    elif f['type']=='checkbox': locator.uncheck()
                elif value and f['type'] in ('text','email','tel','url','number','textarea','date'): locator.fill(value)
                elif value: raise ValueError('Unsupported field type for '+f['label']+'. Continue manually.')
            if fingerprint(read_fields(page))!=package['form']['fingerprint']:
                raise ValueError('Answering exposed new or changed questions. Continue manually so you can review the complete form.')
            for f in fields:
                value=str(package['answers'].get(f['key'],''))
                if value and f['type'] in ('text','email','tel','url','number','textarea','date','select'):
                    if page.locator(f['key']).input_value()!=value:
                        raise ValueError('The website changed an answer while filling the form. Continue manually to review it.')
            if page.locator('input:invalid,select:invalid,textarea:invalid').count(): raise ValueError('The site rejected one or more answers. Review them before retrying.')
            if blocked(page): raise ValueError('Human verification is required before submission.')
            buttons=page.get_by_role('button',name=re.compile(r'^(submit application|submit|apply now|send application)$',re.I))
            if buttons.count()!=1: raise ValueError('Cannot identify a unique submit button. Continue manually.')
            success_pattern=re.compile(r'thank you for applying|application (has been |was )?(successfully )?(submitted|received)|thanks for applying',re.I)
            prior=page.get_by_text(success_pattern)
            prior_text={prior.nth(i).inner_text() for i in range(prior.count()) if prior.nth(i).is_visible()}
            # Once the click starts, failures are uncertain and cannot be auto-retried.
            clicked=True
            buttons.click(timeout=20000)
            page.wait_for_timeout(2500)
            receipts=page.get_by_text(success_pattern)
            candidates=[receipts.nth(i) for i in range(receipts.count()) if receipts.nth(i).is_visible() and receipts.nth(i).inner_text() not in prior_text]
            receipt=candidates[0] if candidates else None
            if receipt is None:
                store.update_job(job_id,state='uncertain')
                store.event(job_id,'Submission attempted; confirmation was not detected. Check the employer site before taking any further action.')
                return 'Submission status is uncertain. No automatic retry will occur.'
            folder=store.DATA/'receipts'; folder.mkdir(exist_ok=True)
            file=folder/(job_id+'.png')
            page.screenshot(path=str(file),full_page=True)
            store.update_job(job_id,state='submitted',receipt={'url':page.url,'text':receipt.inner_text()[:1000],'at':store.now(),'path':str(file.relative_to(store.DATA)),'package_id':package['id']})
            store.event(job_id,'Application submission confirmed by the employer page.')
            return 'Application submitted and confirmation saved.'
        except Exception:
            store.update_job(job_id,state='uncertain' if clicked else 'needs_input')
            raise
        finally: browser.close()

def open_user_browser_session(url: str = 'https://www.linkedin.com'):
    """Open visible browser session with user's persistent profile for login."""
    import subprocess
    import sys
    script = store.ROOT / 'backend' / 'browser_session.py'
    subprocess.Popen([sys.executable, str(script), url], cwd=str(store.ROOT))
    return 'Browser window opened. Log into your accounts, then close the window.'

def _extract_element_label(el, page) -> str:
    try:
        # Check aria-label or placeholder
        aria = el.get_attribute('aria-label') or el.get_attribute('placeholder') or ''
        if aria:
            return aria.strip()
        # Check associated label
        el_id = el.get_attribute('id')
        if el_id:
            lbl = page.locator(f'label[for="{el_id}"]').first
            if lbl.count():
                return lbl.inner_text().strip()
        # Check parent label or preceding text
        parent_lbl = el.locator('xpath=ancestor::label').first
        if parent_lbl.count():
            return parent_lbl.inner_text().strip()
        # Check fieldset legend or parent container text
        container = el.locator('xpath=ancestor::div[contains(@class, "fb-dash-form-element") or contains(@class, "jobs-easy-apply-form-section__grouping") or contains(@class, "form-group") or contains(@class, "field")]').first
        if container.count():
            txt = container.inner_text().split('\n')[0]
            if txt:
                return txt.strip()
        name = el.get_attribute('name') or ''
        return name
    except Exception:
        return ''

def _safe_count(locator) -> int:
    try:
        c = locator.count()
        return int(c)
    except Exception:
        return 0

def auto_apply_job(job_id: str, auto_submit: bool = False, headless: bool = False, progress=None) -> str:
    """AI Auto-Apply agent using persistent user-logged-in browser session."""
    from . import form_engine
    job = store.get_job(job_id)
    package = store.get_package(job_id)
    if not package:
        raise ValueError('Prepare a tailored CV before starting auto-apply.')

    pdf_info = package.get('files', {}).get('pdf')
    if not pdf_info or not (store.DATA / pdf_info.get('path', '')).exists():
        raise ValueError('Tailored CV PDF not found. Open the Tailored CV tab to review and export it.')

    pdf_path = store.DATA / pdf_info['path']
    prefs = store.setting('preferences', {})
    profile = package['profile']

    user_dir = store.DATA / 'browser_profile'
    user_dir.mkdir(parents=True, exist_ok=True)

    if progress:
        progress('Launching browser session with your saved logins…')

    store.update_job(job_id, state='submitting')
    store.event(job_id, 'AI Auto-Apply started. Connecting to job portal…')

    clicked = False
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(user_dir),
            headless=headless,
            args=['--disable-blink-features=AutomationControlled'],
            viewport={'width': 1280, 'height': 800} if headless else None,
            no_viewport=not headless
        )
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            target_url = job.get('url', '').strip()
            if not target_url.startswith('http'):
                raise ValueError('Invalid job application URL.')

            if progress:
                progress(f'Navigating to job posting: {job.get("title", "Job")}…')

            page.goto(target_url, wait_until='domcontentloaded', timeout=45000)
            page.wait_for_timeout(2500)

            # Check if LinkedIn
            is_linkedin = 'linkedin.com' in page.url or 'linkedin.com' in target_url

            if is_linkedin:
                # 1. Check if user is logged in
                login_form = page.locator('input#session_key, input#username, form.login__form').first
                if _safe_count(login_form) and login_form.is_visible():
                    if headless:
                        raise ValueError('You are not logged into LinkedIn. Use "Open Logged-in Browser" to log in once, then retry.')
                    else:
                        if progress:
                            progress('Please log into LinkedIn in the browser window to continue…')
                        page.wait_for_selector('nav.global-nav, a[href*="/feed"], button.jobs-apply-button, .jobs-details', timeout=90000)

                # 2. Find Easy Apply button with condition-based waiting (AA-01)
                if progress:
                    progress('Searching for application button…')

                easy_apply_selectors = [
                    'button.jobs-apply-button',
                    'button:has-text("Easy Apply")',
                    'button[aria-label*="Easy Apply"]',
                    '.jobs-s-apply button',
                    'div[data-job-id] button.jobs-apply-button'
                ]
                apply_btn = None
                for selector in easy_apply_selectors:
                    loc = page.locator(selector).first
                    try:
                        loc.wait_for(state='visible', timeout=3000)
                        apply_btn = loc
                        break
                    except Exception:
                        continue

                if not apply_btn:
                    # Check for generic Apply button that redirects to external site
                    ext_apply_selectors = [
                        'button:has-text("Apply")',
                        'a:has-text("Apply")',
                        'a.jobs-apply-button',
                        'button[aria-label*="Apply"]'
                    ]
                    ext_apply = None
                    for selector in ext_apply_selectors:
                        loc = page.locator(selector).first
                        try:
                            loc.wait_for(state='visible', timeout=2000)
                            ext_apply = loc
                            break
                        except Exception:
                            continue

                    if ext_apply:
                        if progress:
                            progress('Opening external employer application portal…')
                        with page.expect_popup(timeout=15000) as popup_info:
                            ext_apply.click()
                        page = popup_info.value
                        page.wait_for_timeout(3000)
                        return _handle_generic_form(page, job, package, prefs, profile, pdf_path, auto_submit, progress)
                    else:
                        # Capture diagnostics on failure (AA-01)
                        diag_folder = store.DATA / 'diagnostics'
                        diag_folder.mkdir(exist_ok=True)
                        diag_file = diag_folder / f"apply_btn_missing_{job_id}.png"
                        try:
                            page.screenshot(path=str(diag_file))
                        except Exception:
                            pass
                        store.update_job(job_id, state='needs_input')
                        raise ValueError(f"No active application button was found on this posting (URL: {page.url}). Verify the job is still open or apply manually.")

                if progress:
                    progress('Opening LinkedIn Easy Apply modal…')
                apply_btn.click()
                page.wait_for_timeout(2000)

                # 3. Handle Easy Apply modal traversal
                max_steps = 12
                step = 0
                while step < max_steps:
                    step += 1
                    modal = page.locator('div[role="dialog"], .jobs-easy-apply-modal').first
                    if not _safe_count(modal) or not modal.is_visible():
                        break

                    if blocked(page):
                        store.update_job(job_id, state='needs_input')
                        raise ValueError('Human verification or security challenge detected on LinkedIn. Complete it in the browser.')

                    if progress:
                        progress(f'Answering questions on application step {step}…')

                    # Attach tailored CV if file input is present on this step
                    file_input = modal.locator('input[type="file"]').first
                    if _safe_count(file_input):
                        try:
                            if progress:
                                progress('Attaching tailored CV PDF…')
                            file_input.set_input_files(str(pdf_path))
                            page.wait_for_timeout(1000)
                        except Exception:
                            pass

                    # Read and fill form controls on this modal step
                    _fill_container_fields(page, modal, profile, job, package, prefs)

                    # Check navigation buttons
                    submit_btn = modal.locator('button:has-text("Submit application"), button[aria-label="Submit application"]').first
                    review_btn = modal.locator('button:has-text("Review"), button[aria-label="Review your application"]').first
                    next_btn = modal.locator('button:has-text("Next"), button[aria-label="Continue to next step"]').first

                    has_submit = _safe_count(submit_btn) and submit_btn.is_visible()
                    has_review = _safe_count(review_btn) and review_btn.is_visible()
                    has_next = _safe_count(next_btn) and next_btn.is_visible()

                    if has_submit:
                        if auto_submit:
                            if progress:
                                progress('Submitting application on LinkedIn…')
                            success_pattern = re.compile(r'application (was|has been) (sent|submitted)|thank you for applying|your application was sent|applied', re.I)
                            prior = page.get_by_text(success_pattern)
                            prior_text = set()
                            try:
                                for i in range(_safe_count(prior)):
                                    el = prior.nth(i)
                                    if el.is_visible():
                                        prior_text.add(el.inner_text())
                            except Exception:
                                pass

                            clicked = True
                            submit_btn.click(timeout=20000)
                            page.wait_for_timeout(3500)

                            folder = store.DATA / 'receipts'
                            folder.mkdir(exist_ok=True)
                            file = folder / (job_id + '.png')
                            try:
                                page.screenshot(path=str(file))
                            except Exception:
                                pass

                            receipts = page.get_by_text(success_pattern)
                            candidates = []
                            try:
                                for i in range(_safe_count(receipts)):
                                    el = receipts.nth(i)
                                    if el.is_visible() and el.inner_text() not in prior_text:
                                        candidates.append(el)
                            except Exception:
                                pass

                            receipt = candidates[0] if candidates else None
                            if receipt is None:
                                store.update_job(job_id, state='uncertain')
                                store.event(job_id, 'AI Auto-Apply clicked Submit on LinkedIn, but employer confirmation was not detected. Check LinkedIn before retrying.')
                                return 'Submission status is uncertain. Confirmation was not detected.'

                            store.update_job(job_id, state='submitted', receipt={
                                'url': page.url,
                                'text': receipt.inner_text()[:1000] if hasattr(receipt, 'inner_text') else 'Submitted automatically via AI Auto-Apply on LinkedIn',
                                'at': store.now(),
                                'path': str(file.relative_to(store.DATA)),
                                'package_id': package['id']
                            })
                            store.event(job_id, 'AI Auto-Apply successfully submitted the application on LinkedIn.')
                            return 'Application submitted successfully to LinkedIn with confirmation screenshot saved.'
                        else:
                            if progress:
                                progress('Form completed and CV attached! Paused at final Review step.')
                            store.event(job_id, 'AI Auto-Apply pre-filled all questions and attached your CV. Ready for your final review in the browser.')
                            store.update_job(job_id, state='awaiting_review')
                            # Durable Co-Pilot review handoff (AA-09)
                            if not headless:
                                try:
                                    page.wait_for_event('close', timeout=0)
                                except Exception:
                                    pass
                            return 'All questions answered and tailored CV attached. Review and submit in your browser window.'

                    elif has_review:
                        review_btn.click()
                        page.wait_for_timeout(1500)
                    elif has_next:
                        next_btn.click()
                        page.wait_for_timeout(1500)
                    else:
                        break

                store.update_job(job_id, state='awaiting_review')
                return 'Application form processed. Complete any remaining questions and submit.'
            else:
                return _handle_generic_form(page, job, package, prefs, profile, pdf_path, auto_submit, progress)

        except Exception:
            store.update_job(job_id, state='uncertain' if clicked else 'needs_input')
            raise

def _fill_container_fields(page, container, profile, job, package, prefs):
    """Detect and fill form controls within a container element using form_engine."""
    from . import form_engine
    if 'answers' not in package or not isinstance(package.get('answers'), dict):
        package['answers'] = {}
    answers = package['answers']

    # 1. Text, number, email, tel, textarea inputs
    inputs = container.locator('input[type="text"]:visible, input[type="email"]:visible, input[type="tel"]:visible, input[type="number"]:visible, input:not([type]):visible, textarea:visible')
    for i in range(_safe_count(inputs)):
        el = inputs.nth(i)
        try:
            curr = el.input_value()
            if curr and len(curr) > 1:
                continue
            label = _extract_element_label(el, page)
            if not label:
                continue
            field_dict = {'label': label, 'type': el.get_attribute('type') or 'text', 'options': []}
            ans = form_engine.answer_single_field(field_dict, profile, job, package, prefs)
            if ans:
                el.fill(str(ans))
                answers[label] = str(ans)
                page.wait_for_timeout(200)
        except Exception:
            continue

    # 2. Select dropdowns
    selects = container.locator('select:visible')
    for i in range(_safe_count(selects)):
        el = selects.nth(i)
        try:
            label = _extract_element_label(el, page)
            opts = el.locator('option')
            opt_list = []
            for o in range(_safe_count(opts)):
                opt_el = opts.nth(o)
                opt_list.append({'value': opt_el.get_attribute('value') or '', 'label': opt_el.inner_text().strip()})
            field_dict = {'label': label, 'type': 'select', 'options': opt_list}
            ans = form_engine.answer_single_field(field_dict, profile, job, package, prefs)
            if ans:
                try:
                    el.select_option(value=str(ans))
                except Exception:
                    el.select_option(label=str(ans))
                answers[label] = str(ans)
                page.wait_for_timeout(200)
        except Exception:
            continue

    # 3. Radio groups
    radios = container.locator('input[type="radio"]:visible, div[role="radio"]:visible')
    for i in range(_safe_count(radios)):
        el = radios.nth(i)
        try:
            label = _extract_element_label(el, page)
            field_dict = {'label': label, 'type': 'radio', 'options': []}
            ans = form_engine.answer_single_field(field_dict, profile, job, package, prefs)
            if ans and ans.casefold() in ('yes', 'true', '1'):
                if not any(k in label.casefold() for k in ('not authorized', 'disagree', 'no')):
                    el.check()
                    answers[label] = 'true'
                    page.wait_for_timeout(200)
        except Exception:
            continue

    try:
        if package.get('id'):
            store.revise_package(package['id'], store.package_data(package))
    except Exception:
        pass

def _handle_generic_form(page, job, package, prefs, profile, pdf_path, auto_submit, progress):
    """Handle generic hosted ATS portals (Greenhouse, Lever, Workable, etc.)."""
    job_id = job['id']
    if progress:
        progress('Inspecting page for application form controls…')
    page.wait_for_timeout(2000)

    # Attach CV to any file upload element
    cv_attached = False
    try:
        file_inputs = page.locator('input[type="file"]')
        if _safe_count(file_inputs) > 0:
            if progress:
                progress('Attaching tailored CV PDF…')
            file_inputs.first.set_input_files(str(pdf_path))
            page.wait_for_timeout(1000)
            cv_attached = True
    except Exception:
        pass

    # Fill all visible fields on the page
    if progress:
        progress('Auto-filling candidate details, screening questions, and salary…')
    _fill_container_fields(page, page, profile, job, package, prefs)

    submit_btn = page.locator('button:has-text("Submit application"), button:has-text("Apply now"), button:has-text("Submit"), input[type="submit"]').first
    has_submit = False
    try:
        has_submit = _safe_count(submit_btn) > 0 and submit_btn.is_visible()
    except Exception:
        pass

    clicked = False
    if has_submit:
        if auto_submit:
            if progress:
                progress('Submitting application…')
            success_pattern = re.compile(r'thank you for applying|application (has been |was )?(successfully )?(submitted|received)|thanks for applying|application received', re.I)
            prior = page.get_by_text(success_pattern)
            prior_text = set()
            try:
                for i in range(_safe_count(prior)):
                    el = prior.nth(i)
                    if el.is_visible():
                        prior_text.add(el.inner_text())
            except Exception:
                pass

            try:
                clicked = True
                submit_btn.click(timeout=20000)
                page.wait_for_timeout(3500)

                folder = store.DATA / 'receipts'
                folder.mkdir(exist_ok=True)
                file = folder / (job_id + '.png')
                page.screenshot(path=str(file))

                receipts = page.get_by_text(success_pattern)
                candidates = []
                try:
                    for i in range(_safe_count(receipts)):
                        el = receipts.nth(i)
                        if el.is_visible() and el.inner_text() not in prior_text:
                            candidates.append(el)
                except Exception:
                    pass

                receipt = candidates[0] if candidates else None
                if receipt is None:
                    store.update_job(job_id, state='uncertain')
                    store.event(job_id, 'AI Auto-Apply clicked submit, but employer confirmation was not detected. Check the site before retrying.')
                    return 'Submission status is uncertain. Confirmation was not detected on employer portal.'

                store.update_job(job_id, state='submitted', receipt={
                    'url': page.url,
                    'text': receipt.inner_text()[:1000] if hasattr(receipt, 'inner_text') else 'Submitted automatically via AI Auto-Apply',
                    'at': store.now(),
                    'path': str(file.relative_to(store.DATA)),
                    'package_id': package['id']
                })
                store.event(job_id, 'AI Auto-Apply submitted the application.')
                return 'Application submitted successfully with screenshot receipt saved.'
            except Exception:
                if clicked:
                    store.update_job(job_id, state='uncertain')
                raise
        else:
            if progress:
                progress('All questions answered. Ready for final review!')
            store.update_job(job_id, state='awaiting_review')
            upload_msg = ' and CV uploaded' if cv_attached else ''
            store.event(job_id, f'AI Auto-Apply pre-filled the application{upload_msg}. Ready for your review in the browser.')
            return f'Application pre-filled{upload_msg}. Review and submit in your browser.'

    store.update_job(job_id, state='awaiting_review')
    upload_msg = ' and CV uploaded' if cv_attached else ''
    return f'Application pre-filled{upload_msg}. Complete any remaining custom questions and submit.'
