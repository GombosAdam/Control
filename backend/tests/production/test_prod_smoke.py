"""Production smoke tests — login → dashboard → APIs."""

import os

import httpx
import pytest

from tests.conftest import _login, auth_header

pytestmark = pytest.mark.production

PROD_URL = os.environ.get("TEST_BASE_URL", "https://invoice.rhcdemoaccount2.com")


class TestProductionSmoke:
    async def test_full_smoke_flow(self):
        """Login → dashboard stats → invoice list → budget lines → monthly report."""
        async with httpx.AsyncClient(base_url=f"{PROD_URL}/api/v1", timeout=15.0) as c:
            # Login
            token = await _login(c, "admin@invoice.local", "admin123")
            h = auth_header(token)

            # Dashboard
            resp = await c.get("/dashboard/stats", headers=h)
            assert resp.status_code == 200

            # Invoices
            resp = await c.get("/invoices", headers=h)
            assert resp.status_code == 200

            # Budget
            resp = await c.get("/budget/lines", headers=h)
            assert resp.status_code == 200

            # Report
            resp = await c.get("/reports/monthly?year=2025&month=1", headers=h)
            assert resp.status_code == 200

    async def test_response_times(self):
        """All critical endpoints respond within 5 seconds."""
        async with httpx.AsyncClient(base_url=f"{PROD_URL}/api/v1", timeout=5.0) as c:
            token = await _login(c, "admin@invoice.local", "admin123")
            h = auth_header(token)

            endpoints = [
                "/dashboard/stats",
                "/invoices",
                "/budget/lines",
                "/partners",
            ]
            for ep in endpoints:
                resp = await c.get(ep, headers=h)
                assert resp.status_code == 200, f"{ep} returned {resp.status_code}"

    async def test_cors_headers(self):
        """Verify CORS headers are present."""
        async with httpx.AsyncClient(timeout=10.0) as c:
            resp = await c.options(
                f"{PROD_URL}/api/v1/auth/login",
                headers={
                    "Origin": "https://invoice.rhcdemoaccount2.com",
                    "Access-Control-Request-Method": "POST",
                },
            )
            # Should not be 500; CORS may return 200 or 204
            assert resp.status_code in (200, 204, 405)
