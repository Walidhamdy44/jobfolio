"""Bounded, cached proxy for company logos supplied by trusted job feeds."""
from functools import lru_cache
from urllib.parse import urljoin, urlparse

import httpx

from . import network

_LOGO_HOSTS = (
    'licdn.com',
    'linkedin.com',
    'remotive.com',
    'jobicy.com',
    'arbeitnow.com',
    'weworkremotely.com',
)
_IMAGE_TYPES = {'image/png', 'image/jpeg', 'image/webp', 'image/gif'}
_MAX_LOGO_BYTES = 512_000


def _validated_logo_url(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or '').casefold().removeprefix('www.')
    if (
        parsed.scheme != 'https'
        or not host
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
        or not any(host == domain or host.endswith('.' + domain) for domain in _LOGO_HOSTS)
    ):
        raise ValueError('Logo host is not allowed.')
    return network.public_url(url)


@lru_cache(maxsize=128)
def fetch_company_logo(url: str) -> tuple[str, bytes] | None:
    """Fetch a small raster logo from a job-feed CDN, rejecting private hosts and SVG."""
    try:
        current_url = _validated_logo_url(url)
        with httpx.Client(
            timeout=6,
            follow_redirects=False,
            trust_env=False,
            verify=network._network_ssl_context(),
        ) as client:
            for _ in range(4):
                current_url = _validated_logo_url(current_url)
                with client.stream(
                    'GET',
                    current_url,
                    headers={
                        'User-Agent': 'Jobfolio/1.0',
                        'Accept': 'image/png,image/jpeg,image/webp,image/gif',
                    },
                ) as response:
                    if response.is_redirect:
                        location = response.headers.get('location')
                        if not location:
                            return None
                        current_url = urljoin(current_url, location)
                        continue
                    if response.status_code != 200:
                        return None

                    content_type = response.headers.get('content-type', '').split(';', 1)[0].strip().casefold()
                    if content_type not in _IMAGE_TYPES:
                        return None
                    try:
                        if int(response.headers.get('content-length', '0')) > _MAX_LOGO_BYTES:
                            return None
                    except ValueError:
                        return None

                    chunks: list[bytes] = []
                    size = 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > _MAX_LOGO_BYTES:
                            return None
                        chunks.append(chunk)
                    return content_type, b''.join(chunks)
    except (httpx.HTTPError, OSError, ValueError):
        return None
    return None
