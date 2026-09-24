import pytest
from playwright.sync_api import sync_playwright
from backend import browser,store

HTML='''<!doctype html><form><label for="name">Full name *</label><input id="name" required><label for="email">Email *</label><input id="email" type="email" required><label for="resume">Resume *</label><input id="resume" type="file" required><label for="sponsor">Require sponsorship? *</label><select id="sponsor" required><option value="">Choose</option><option value="yes">Yes</option><option value="no">No</option></select><button type="submit">Submit application</button></form><script>document.querySelector('form').onsubmit=e=>{e.preventDefault();document.body.innerHTML='<h1>Thank you for applying</h1>'}</script>'''

def test_form_inspection_and_submission_on_local_fixture(client,job,monkeypatch):
    from backend.tailoring import prepare
    prepare(job['id'])
    monkeypatch.setattr(browser,'application_url',lambda job:'https://jobs.lever.co/test/test')
    def fixture_page(b,url):
        ctx=b.new_context();page=ctx.new_page();page.set_content(HTML);return ctx,page
    monkeypatch.setattr(browser,'open_page',fixture_page)
    browser.inspect(job['id'])
    p=store.get_package(job['id'])
    assert len(p['form']['fields'])==4
    assert p['answers']['#email']=='walidhamdy314@gmail.com'
    assert browser.missing_answers(p)==['Require sponsorship? *']
    p['answers']['#sponsor']='no'
    result=browser.submit(job['id'],p)
    assert 'confirmed' in store.get_job(job['id'])['receipt']['text'].lower() or 'thank you' in store.get_job(job['id'])['receipt']['text'].lower()
    assert store.get_job(job['id'])['state']=='submitted'
    assert (store.DATA/store.get_job(job['id'])['receipt']['path']).exists()

def test_timeout_after_click_is_uncertain(client,job,monkeypatch):
    from backend.tailoring import prepare
    prepare(job['id'])
    monkeypatch.setattr(browser,'application_url',lambda job:'https://jobs.lever.co/test/test')
    def fixture_page(b,url):
        ctx=b.new_context();page=ctx.new_page();page.set_content(HTML.replace('Thank you for applying','Processing'));return ctx,page
    monkeypatch.setattr(browser,'open_page',fixture_page)
    browser.inspect(job['id']);p=store.get_package(job['id']);p['answers']['#sponsor']='no'
    browser.submit(job['id'],p)
    assert store.get_job(job['id'])['state']=='uncertain'

def test_changed_form_does_not_submit(client,job,monkeypatch):
    from backend.tailoring import prepare
    prepare(job['id'])
    monkeypatch.setattr(browser,'application_url',lambda job:'https://jobs.lever.co/test/test')
    def fixture_page(b,url):
        ctx=b.new_context();page=ctx.new_page();page.set_content(HTML);return ctx,page
    monkeypatch.setattr(browser,'open_page',fixture_page)
    browser.inspect(job['id']);p=store.get_package(job['id']);p['answers']['#sponsor']='no';p['form']['fingerprint']='outdated'
    with pytest.raises(ValueError,match='form changed'): browser.submit(job['id'],p)
    assert store.get_job(job['id'])['state']=='needs_input'

def test_conditional_question_blocks_submission(client,job,monkeypatch):
    from backend.tailoring import prepare
    prepare(job['id'])
    monkeypatch.setattr(browser,'application_url',lambda job:'https://jobs.lever.co/test/test')
    html=HTML.replace('<select id="sponsor" required>', '<select id="sponsor" required onchange="const e=document.createElement(\'input\'); e.id=\'extra\'; this.after(e)">')
    def fixture_page(b,url):
        ctx=b.new_context();page=ctx.new_page();page.set_content(html);return ctx,page
    monkeypatch.setattr(browser,'open_page',fixture_page)
    browser.inspect(job['id']);p=store.get_package(job['id']);p['answers']['#sponsor']='no'
    with pytest.raises(ValueError,match='new or changed questions'): browser.submit(job['id'],p)
    assert store.get_job(job['id'])['state']=='needs_input'
