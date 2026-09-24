import pytest
from fastapi.testclient import TestClient
from backend import store, profile, providers
from backend.app import app

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DATA',tmp_path)
    monkeypatch.setattr(providers,'secret',lambda name:'')
    with TestClient(app,headers={'X-Job-Agent':'local'}) as c:
        yield c

@pytest.fixture
def job(client):
    r=client.post('/api/jobs',json={'title':'Frontend Engineer','company':'Local test employer','location':'Remote',
        'description':'Requirements:\nExperience building React applications and REST APIs.\nStrong TypeScript development skills required.\nKubernetes production experience is preferred.'})
    assert r.status_code==200,r.text
    return r.json()['job']
