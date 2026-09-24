"""Browser smoke test against an isolated database. Never contacts an employer."""
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tmp'/'qa'
OUT.mkdir(parents=True,exist_ok=True)
env={**os.environ,'JOB_AGENT_DATA':str(OUT/('data-'+uuid.uuid4().hex[:8]))}
kwargs={'cwd':str(ROOT),'env':env,'stdout':subprocess.DEVNULL,'stderr':subprocess.DEVNULL}
if os.name=='nt': kwargs['creationflags']=subprocess.CREATE_NO_WINDOW
server=subprocess.Popen([sys.executable,'-m','uvicorn','backend.app:app','--host','127.0.0.1','--port','8766','--no-access-log'],**kwargs)
try:
    for _ in range(60):
        try:
            if httpx.get('http://127.0.0.1:8766/api/health',timeout=1).status_code==200: break
        except httpx.HTTPError: pass
        time.sleep(.25)
    with sync_playwright() as p:
        b=p.chromium.launch()
        page=b.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1)
        def capture(name):
            page.evaluate('() => { document.activeElement?.blur(); window.scrollTo(0,0); }')
            page.wait_for_timeout(200)
            page.screenshot(path=str(OUT/name),full_page=True)
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto('http://127.0.0.1:8766');page.get_by_role('heading',name='Your next chapter.').wait_for()
        page.evaluate('document.fonts.ready')
        capture('desktop.png')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Desktop overflow'
        page.set_viewport_size({'width':390,'height':844})
        capture('mobile.png')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Mobile overflow'
        page.set_viewport_size({'width':1440,'height':1000})
        page.get_by_role('button',name='Add a job',exact=True).click()
        page.get_by_role('button',name='Paste a description').click()
        page.get_by_label('Job title',exact=True).fill('Frontend Engineer — local QA fixture')
        page.get_by_label('Company',exact=True).fill('Test employer (not a real application)')
        page.get_by_label('Location',exact=True).fill('Remote')
        page.get_by_label('Full job description').fill('Requirements:\nExperience developing React applications.\nStrong TypeScript skills required.\nExperience integrating REST APIs required.\nKubernetes production experience preferred.')
        page.get_by_role('button',name='Save opportunity').click()
        page.get_by_role('heading',name='Frontend Engineer — local QA fixture').wait_for()
        page.get_by_role('button',name='Prepare local CV',exact=True).click()
        page.locator('a:has-text("Tailored CV")').click()
        page.get_by_role('heading',name='A CV with this role in mind').wait_for(timeout=60000)
        page.locator('.run-banner').wait_for(state='detached',timeout=60000)
        page.locator('.cv-paper').wait_for()
        capture('review-desktop.png')
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Review mobile overflow'
        capture('review-mobile.png')
        page.get_by_label('I reviewed the complete CV and confirm its statements are accurate.').check()
        page.get_by_role('button',name='Save CV review').click()
        page.get_by_text('Review saved. Approval applies only to this exact package version.').wait_for()

        # Test route refresh
        page.reload()
        page.get_by_role('heading',name='A CV with this role in mind').wait_for(timeout=30000)

        page.locator('a:has-text("Requirement coverage")').click()
        page.get_by_text('I reviewed every requirement, its evidence, and any missing qualifications.').click()
        page.get_by_role('button',name='Save coverage review').click()
        page.wait_for_timeout(800)
        page.get_by_role('link', name='Application', exact=True).click()
        page.get_by_role('button',name='Approve this package').click()
        page.get_by_text('Package approved. No application has been sent yet.').wait_for()
        assert page.get_by_role('button',name='Submit application',exact=True).count()==0,'Manual job must not offer automation'
        page.set_viewport_size({'width':1440,'height':1000})
        capture('application-desktop.png')
        page.get_by_role('link', name='Connections', exact=True).click()
        page.get_by_role('heading', name='Give your agent its tools.').wait_for()
        assert page.locator('input[type=password]').count()>=1
        page.get_by_role('link', name='My profile', exact=True).click()
        page.get_by_role('heading', name='The experience behind every application.').wait_for()
        assert page.get_by_label('Name', exact=True).input_value()=='Walid Hamdy'
        assert not errors,errors
        b.close()
    print(json.dumps({'result':'passed','browser_errors':errors,'screenshots':str(OUT),'database':'isolated QA data, no real job submitted'}))
finally:
    server.terminate();server.wait(timeout=15)
