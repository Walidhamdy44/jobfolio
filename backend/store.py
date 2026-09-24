"""Local persistence. Documents and personal data stay outside source control."""
import hashlib
import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.getenv('JOB_AGENT_DATA', ROOT / 'data'))

def now():
    return datetime.now(timezone.utc).isoformat()

def uid():
    return uuid.uuid4().hex

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

@contextmanager
def db():
    DATA.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATA / 'agent.sqlite3', timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init():
    with db() as c:
        c.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, identity TEXT UNIQUE NOT NULL, data TEXT NOT NULL,
            state TEXT NOT NULL, created TEXT NOT NULL, updated TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS packages (
            id TEXT PRIMARY KEY, job_id TEXT NOT NULL, data TEXT NOT NULL,
            hash TEXT NOT NULL, approved_hash TEXT, created TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS runs (
            id TEXT PRIMARY KEY, kind TEXT NOT NULL, target TEXT, state TEXT NOT NULL,
            message TEXT NOT NULL, created TEXT NOT NULL, updated TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT, text TEXT NOT NULL, created TEXT NOT NULL);
        ''')
        c.execute("UPDATE runs SET state='interrupted',message='App restarted. Review the job before retrying.',updated=? WHERE state IN ('queued','running')", (now(),))
        c.execute("UPDATE jobs SET state='uncertain',updated=? WHERE state='submitting'", (now(),))

        # Legacy data repair for HTML entity encoding (QA-09)
        import html
        from bs4 import BeautifulSoup
        def clean_legacy(text):
            if not text or not isinstance(text, str) or ('&' not in text and '<' not in text):
                return text
            un = html.unescape(text)
            if '<' in un and '>' in un:
                soup = BeautifulSoup(un, 'html.parser')
                un = soup.get_text(' ', strip=True)
            un = html.unescape(un).replace('\xa0', ' ')
            return ' '.join(un.split())

        sr_row = c.execute("SELECT value FROM settings WHERE key='search_results'").fetchone()
        if sr_row:
            try:
                sr = json.loads(sr_row[0])
                modified = False
                for it in sr.get('items', []):
                    for k in ('title', 'job_title', 'company', 'snippet'):
                        if k in it and isinstance(it[k], str):
                            cl = clean_legacy(it[k])
                            if cl != it[k]:
                                it[k] = cl
                                modified = True
                if modified:
                    c.execute("UPDATE settings SET value=? WHERE key='search_results'", (json.dumps(sr),))
            except Exception:
                pass

        for j_row in c.execute("SELECT id, data FROM jobs").fetchall():
            try:
                j_data = json.loads(j_row['data'])
                modified = False
                for k in ('title', 'company', 'location'):
                    if k in j_data and isinstance(j_data[k], str):
                        cl = clean_legacy(j_data[k])
                        if cl != j_data[k]:
                            j_data[k] = cl
                            modified = True
                if modified:
                    c.execute("UPDATE jobs SET data=? WHERE id=?", (json.dumps(j_data), j_row['id']))
            except Exception:
                pass

def setting(key, default=None):
    with db() as c:
        r = c.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
    return json.loads(r[0]) if r else default

def set_setting(key, value):
    with db() as c:
        c.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', (key, json.dumps(value)))

def event(job_id, text):
    with db() as c:
        c.execute('INSERT INTO events(job_id,text,created) VALUES (?,?,?)', (job_id, text, now()))

def get_job(job_id):
    with db() as c:
        r = c.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
    if not r:
        raise ValueError('Job not found.')
    return {**json.loads(r['data']), 'id': r['id'], 'state': r['state'], 'created': r['created'], 'updated': r['updated']}

def update_job(job_id, **changes):
    job = get_job(job_id)
    job.update(changes)
    with db() as c:
        c.execute('UPDATE jobs SET data=?,state=?,updated=? WHERE id=?', (json.dumps(job), job['state'], now(), job_id))

def add_job(job):
    identity = job.get('canonical_url') or digest([job['company'].casefold(), job['title'].casefold(), job.get('location','').casefold()])
    with db() as c:
        r = c.execute('SELECT id FROM jobs WHERE identity=?', (identity,)).fetchone()
        if r:
            return get_job(r['id']), False
        job_id = uid()
        c.execute('INSERT INTO jobs VALUES (?,?,?,?,?,?)', (job_id, identity, json.dumps(job), 'shortlisted', now(), now()))
    event(job_id, 'Job saved. No application has been sent.')
    return get_job(job_id), True

def get_package(job_id):
    with db() as c:
        r = c.execute('SELECT * FROM packages WHERE job_id=? ORDER BY created DESC LIMIT 1', (job_id,)).fetchone()
    if not r:
        return None
    return {**json.loads(r['data']), 'id': r['id'], 'hash': r['hash'], 'approved': r['approved_hash'] == r['hash'], 'created': r['created']}

def save_package(job_id, data):
    package_id = uid()
    with db() as c:
        c.execute('INSERT INTO packages VALUES (?,?,?,?,?,?)', (package_id, job_id, json.dumps(data), digest(data), None, now()))
    return package_id

def revise_package(package_id, data):
    with db() as c:
        c.execute('UPDATE packages SET data=?,hash=?,approved_hash=NULL WHERE id=?', (json.dumps(data), digest(data), package_id))

def package_data(package):
    return {k:v for k,v in package.items() if k not in ('id','hash','approved','created')}
