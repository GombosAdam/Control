"""Production SSL/TLS certificate tests."""

import os
import ssl
import socket
from datetime import datetime, timezone, timedelta

import pytest

pytestmark = pytest.mark.production

PROD_HOST = os.environ.get("PROD_HOST", "invoice.rhcdemoaccount2.com")


class TestProductionSSL:
    def _get_cert(self):
        ctx = ssl.create_default_context()
        with socket.create_connection((PROD_HOST, 443), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=PROD_HOST) as ssock:
                return ssock.getpeercert()

    def test_certificate_valid(self):
        cert = self._get_cert()
        assert cert is not None

    def test_domain_match(self):
        cert = self._get_cert()
        # Subject or SAN should contain our domain
        san = dict(x[0] for x in cert.get("subjectAltName", []))  # type: ignore
        subjects = [entry[0][1] for entry in cert.get("subject", []) if entry[0][0] == "commonName"]
        all_names = list(san.values()) + subjects if san else subjects
        # Check that at least one name matches (possibly wildcard)
        assert any(
            PROD_HOST == name or (name.startswith("*.") and PROD_HOST.endswith(name[1:]))
            for name in all_names
        ), f"Domain {PROD_HOST} not in cert names: {all_names}"

    def test_tls_version(self):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
        ctx.load_default_certs()
        # Disable old protocols
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        with socket.create_connection((PROD_HOST, 443), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=PROD_HOST) as ssock:
                ver = ssock.version()
        assert ver in ("TLSv1.2", "TLSv1.3")

    def test_certificate_not_expiring_soon(self):
        cert = self._get_cert()
        not_after = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
        remaining = not_after - datetime.now(timezone.utc)
        assert remaining > timedelta(days=30), f"Certificate expires in {remaining.days} days"
