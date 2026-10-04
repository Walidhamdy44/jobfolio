import ssl
import sys

from backend import network


def test_network_tls_context_keeps_certificate_and_hostname_validation():
    context = network._network_ssl_context()

    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
    if sys.platform == 'win32':
        assert not context.verify_flags & ssl.VERIFY_X509_STRICT
