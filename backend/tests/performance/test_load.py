"""Performance / load tests."""

import asyncio
import time

import httpx
import pytest

from tests.conftest import _login, auth_header

pytestmark = pytest.mark.performance


class TestPerformance:
    async def test_login_response_time(self, client: httpx.AsyncClient):
        start = time.monotonic()
        resp = await client.post("/auth/login", json={"email": "admin@invoice.local", "password": "admin123"})
        elapsed = time.monotonic() - start
        assert resp.status_code == 200
        assert elapsed < 0.5, f"Login took {elapsed:.2f}s (expected < 0.5s)"

    async def test_invoice_list_response_time(self, client: httpx.AsyncClient, admin_headers: dict):
        start = time.monotonic()
        resp = await client.get("/invoices?limit=100", headers=admin_headers)
        elapsed = time.monotonic() - start
        assert resp.status_code == 200
        assert elapsed < 1.0, f"Invoice list took {elapsed:.2f}s (expected < 1s)"

    async def test_dashboard_stats_response_time(self, client: httpx.AsyncClient, admin_headers: dict):
        start = time.monotonic()
        resp = await client.get("/dashboard/stats", headers=admin_headers)
        elapsed = time.monotonic() - start
        assert resp.status_code == 200
        assert elapsed < 2.0, f"Dashboard stats took {elapsed:.2f}s (expected < 2s)"

    @pytest.mark.ai
    async def test_ai_chat_response_time(self, client: httpx.AsyncClient, admin_headers: dict):
        start = time.monotonic()
        resp = await client.post(
            "/chat/ask",
            json={"question": "Hány számla van?"},
            headers=admin_headers,
            timeout=60.0,
        )
        elapsed = time.monotonic() - start
        assert resp.status_code == 200
        assert elapsed < 30.0, f"AI chat took {elapsed:.2f}s (expected < 30s)"

    async def test_concurrent_logins(self, api_url: str):
        """10 concurrent logins — all must succeed."""
        async def do_login():
            async with httpx.AsyncClient(base_url=api_url, timeout=10.0) as c:
                return await c.post("/auth/login", json={"email": "admin@invoice.local", "password": "admin123"})

        results = await asyncio.gather(*[do_login() for _ in range(10)])
        for r in results:
            assert r.status_code == 200

    async def test_pdf_upload_response_time(
        self, client: httpx.AsyncClient, admin_headers: dict, sample_pdf, cleanup,
    ):
        with open(sample_pdf, "rb") as f:
            content = f.read()
        # Pad to ~1MB to simulate realistic PDF
        padded = content + b"\x00" * (1024 * 1024 - len(content))
        start = time.monotonic()
        resp = await client.post(
            "/invoices/upload",
            files={"file": ("perf.pdf", padded, "application/pdf")},
            headers=admin_headers,
        )
        elapsed = time.monotonic() - start
        assert resp.status_code == 200
        assert elapsed < 3.0, f"PDF upload took {elapsed:.2f}s (expected < 3s)"
        if "id" in resp.json():
            cleanup.add(f"/invoices/{resp.json()['id']}")
