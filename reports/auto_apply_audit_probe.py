"""Isolated behavior probes. No real browser, network, employer, or workspace writes.

These checks document current behavior; PASS means reproduced, not safe/correct.
Run from the repository root with its virtualenv Python.
"""
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend import browser, form_engine
from backend.app import app
from fastapi.testclient import TestClient

results = []

def probe(name, fn):
    try:
        results.append({'case': name, 'observed': fn()})
    except Exception as exc:
        results.append({'case': name, 'exception': type(exc).__name__, 'message': str(exc)})

probe('missing work authorization', lambda: form_engine.resolve_work_auth('Are you legally authorized to work in the US?', {}))
probe('missing sponsorship preference', lambda: form_engine.resolve_work_auth('Will you require visa sponsorship?', {}))
probe('negated authorization', lambda: form_engine.resolve_work_auth('Are you authorized to work in the US?', {'work_authorization': 'Not authorized to work in the US'}))
probe('empty profile React experience', lambda: form_engine.resolve_experience_years('How many years of React experience?', {}))
probe('missing notice period', lambda: form_engine.resolve_notice_period('When can you start?'))
probe('salary Cairo without country', lambda: form_engine.resolve_salary('Expected annual salary', {'location': 'Cairo'}, {}))
probe('salary unrelated Berlin location', lambda: form_engine.resolve_salary('Expected annual salary', {'location': 'Berlin'}, {}))
probe('salary monthly EGP explicitly 65000', lambda: form_engine.resolve_salary('Monthly salary expectation', {'location': 'Egypt'}, {'salary_note': 'EGP 65000 per month'}))
probe('expected start date misclassified as salary', lambda: form_engine.resolve_salary('Expected start date', {'location': 'Remote'}, {}))
probe('unmatched dropdown', lambda: form_engine.match_dropdown_option([{'label':'Yes','value':'yes'}, {'label':'No','value':'no'}], 'Unknown'))
with patch('backend.providers.get_provider_config', return_value={'connected':False}):
    probe('agreement fallback with no provider', lambda: form_engine.answer_single_field({'label':'I agree to the terms','type':'text'}, {}, {}, {}, {}))

def endpoint_unapproved():
    package = {'id':'synthetic-package','approved':False,'cv_reviewed':False,'coverage_reviewed':False}
    # Mock all storage/queue boundaries; do not execute the queued browser callback.
    with patch('backend.app.busy'), patch('backend.store.get_package', return_value=package), patch('backend.worker.enqueue', return_value='synthetic-run') as enqueue:
        with TestClient(app, headers={'X-Job-Agent':'local'}) as client:
            # Lifespan is overridden below to avoid initialization of real storage.
            response = client.post('/api/jobs/synthetic/auto-apply', json={'auto_submit':True})
        return {'status':response.status_code,'body':response.json(),'enqueued':enqueue.called}

from contextlib import asynccontextmanager
@asynccontextmanager
async def isolated_lifespan(app):
    yield
with patch.object(app.router, 'lifespan_context', isolated_lifespan):
    probe('full auto endpoint accepts unreviewed unapproved package', endpoint_unapproved)

def generic(auto_submit, button_exists=True, screenshot_fails=False):
    page = MagicMock()
    files = MagicMock()
    files.count.return_value = 0
    button = MagicMock()
    button.count.return_value = int(button_exists)
    button.is_visible.return_value = button_exists
    button.first = button
    def locator(selector):
        return files if selector == 'input[type="file"]' else button
    page.locator.side_effect = locator
    page.url = 'https://example.invalid/test-only'
    if screenshot_fails:
        page.screenshot.side_effect = RuntimeError('synthetic screenshot failure after click')
    with tempfile.TemporaryDirectory() as folder, patch.object(browser.store,'DATA',Path(folder)), patch.object(browser.store,'update_job') as update, patch.object(browser.store,'event'), patch.object(browser,'_fill_container_fields'):
        try:
            message = browser._handle_generic_form(page, {'id':'synthetic'}, {'id':'synthetic-package'}, {}, {}, Path(folder)/'not-uploaded.pdf', auto_submit, None)
            error = None
        except Exception as exc:
            message = None
            error = type(exc).__name__
        return {'message':message,'error':error,'submit_clicks':button.click.call_count,'state_updates':[c.kwargs for c in update.call_args_list], 'browser_confirmation_checks':page.get_by_text.call_count}

probe('generic submit without confirmation', lambda: generic(True))
probe('generic no form/no submit button', lambda: generic(False, False))
probe('generic copilot no file input', lambda: generic(False))
probe('generic screenshot failure after submit click', lambda: generic(True, True, True))
print(json.dumps(results, indent=2))
