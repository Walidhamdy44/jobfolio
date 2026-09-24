"""Persistent browser session launcher.
Allows user to log into LinkedIn, Google, and job portals once.
Sessions, cookies, and local storage persist in data/browser_profile.
"""
import sys
import os
from pathlib import Path
try:
    from . import store
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from backend import store
from playwright.sync_api import sync_playwright

def launch_session(url: str = 'https://www.linkedin.com'):
    profile_dir = store.DATA / 'browser_profile'
    profile_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=False,
            args=['--disable-blink-features=AutomationControlled'],
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(url)
        # Wait until user closes the browser window
        try:
            page.wait_for_event('close', timeout=0)
        except Exception:
            pass
        finally:
            try:
                ctx.close()
            except Exception:
                pass

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else 'https://www.linkedin.com'
    launch_session(target)
