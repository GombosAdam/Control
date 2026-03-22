"""Production health checks — service availability."""

import os

import httpx
import pytest

pytestmark = pytest.mark.production

PROD_URL = os.environ.get("TEST_BASE_URL", "https://invoice.rhcdemoaccount2.com")


class TestProductionHealth:
    async def test_http_to_https_redirect(self):
        http_url = PROD_URL.replace("https://", "http://")
        async with httpx.AsyncClient(follow_redirects=False, timeout=10.0) as c:
            resp = await c.get(http_url)
        assert resp.status_code in (301, 302, 307, 308)
        assert "https" in resp.headers.get("location", "").lower()

    async def test_frontend_loads(self):
        async with httpx.AsyncClient(timeout=10.0) as c:
            resp = await c.get(PROD_URL)
        assert resp.status_code == 200
        assert "html" in resp.headers.get("content-type", "").lower()

    async def test_api_responds(self):
        async with httpx.AsyncClient(timeout=10.0) as c:
            resp = await c.get(f"{PROD_URL}/api/v1/auth/me")
        # No token → 401, but NOT 502/503
        assert resp.status_code == 401

    async def test_finance_service_reachable(self):
        """Auth endpoint proves finance-service is up."""
        async with httpx.AsyncClient(timeout=10.0) as c:
            resp = await c.post(
                f"{PROD_URL}/api/v1/auth/login",
                json={"email": "probe@test", "password": "probe"},
            )
        assert resp.status_code in (401, 422)

    async def test_invoice_pipeline_reachable(self):
        """Invoices endpoint proves invoice-pipeline service is up."""
        async with httpx.AsyncClient(timeout=10.0) as c:
            resp = await c.get(f"{PROD_URL}/api/v1/invoices")
        assert resp.status_code in (401, 403)

    async def test_ai_service_reachable(self):
        """Chat endpoint proves ai-service is up."""
        async with httpx.AsyncClient(timeout=10.0) as c:
            resp = await c.post(
                f"{PROD_URL}/api/v1/chat/ask",
                json={"question": "test"},
            )
        assert resp.status_code in (401, 403)
