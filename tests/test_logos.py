from backend import logos


def test_logo_proxy_ignores_untrusted_hosts():
    logos.fetch_company_logo.cache_clear()

    assert logos.fetch_company_logo('https://example.com/company.png') is None


def test_logo_proxy_serves_small_raster_from_linkedin_cdn(monkeypatch):
    image_bytes = b'\x89PNG\r\n\x1a\n'

    class MockResponse:
        status_code = 200
        is_redirect = False
        headers = {'content-type': 'image/png', 'content-length': str(len(image_bytes))}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def iter_bytes(self):
            yield image_bytes

    class MockClient:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def stream(self, *_args, **_kwargs):
            return MockResponse()

    monkeypatch.setattr(logos.network, 'public_url', lambda url: url)
    monkeypatch.setattr(logos.httpx, 'Client', lambda **_kwargs: MockClient())
    logos.fetch_company_logo.cache_clear()

    assert logos.fetch_company_logo('https://media.licdn.com/company.png') == ('image/png', image_bytes)


def test_logo_proxy_rejects_svg(monkeypatch):
    class SvgResponse:
        status_code = 200
        is_redirect = False
        headers = {'content-type': 'image/svg+xml'}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def iter_bytes(self):
            yield b'<svg></svg>'

    class MockClient:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def stream(self, *_args, **_kwargs):
            return SvgResponse()

    monkeypatch.setattr(logos.network, 'public_url', lambda url: url)
    monkeypatch.setattr(logos.httpx, 'Client', lambda **_kwargs: MockClient())
    logos.fetch_company_logo.cache_clear()

    assert logos.fetch_company_logo('https://media.licdn.com/company.svg') is None
