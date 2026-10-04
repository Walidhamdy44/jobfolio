import ssl
from types import SimpleNamespace

import openai
import truststore

from backend import providers


def test_codecraft_client_uses_system_certificate_store(monkeypatch):
    system_context = object()
    captured = {}

    def make_context(protocol):
        captured['protocol'] = protocol
        return system_context

    monkeypatch.setattr(truststore, 'SSLContext', make_context)

    def make_client(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(providers.httpx, 'Client', make_client)

    providers._provider_http_client('codecraft')

    assert captured['protocol'] == ssl.PROTOCOL_TLS_CLIENT
    assert captured['verify'] is system_context
    assert captured['timeout'] == 90


def test_other_providers_keep_the_default_http_transport(monkeypatch):
    def unexpected_client(**kwargs):
        raise AssertionError('The default provider transport should remain unchanged.')

    monkeypatch.setattr(providers.httpx, 'Client', unexpected_client)

    assert providers._provider_http_client('openai') is None


def test_codecraft_request_uses_and_closes_the_system_trust_transport(monkeypatch):
    closed = []

    class FakeHTTPClient:
        def close(self):
            closed.append(True)

    http_client = FakeHTTPClient()
    monkeypatch.setattr(providers, '_provider_http_client', lambda provider: http_client)
    monkeypatch.setattr(providers, 'get_provider_config', lambda: {
        'provider': 'codecraft', 'key': 'cc-test', 'base_url': 'https://codecraftapi.com/v1',
        'model': 'gpt-5.6-luna', 'connected': True,
    })

    class FakeOpenAI:
        def __init__(self, **kwargs):
            assert kwargs['http_client'] is http_client
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=lambda **args: SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content='{"requirements":[]}'))],
            )))

    monkeypatch.setattr(openai, 'OpenAI', FakeOpenAI)

    result = providers.ask(providers.Requirements, 'Extract requirements.', {'description': 'A job description.'})

    assert result.requirements == []
    assert closed == [True]
