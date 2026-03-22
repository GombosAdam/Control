"""Error handling E2E tests — 8 tests."""

import httpx
import pytest

from tests.conftest import auth_header


class TestErrorHandling:
    async def test_404_nonexistent_invoice(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/invoices/99999999", headers=admin_headers)
        assert resp.status_code == 404

    async def test_404_nonexistent_endpoint(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/nonexistent-endpoint", headers=admin_headers)
        assert resp.status_code == 404

    async def test_422_malformed_json(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.post(
            "/auth/login",
            content="not valid json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422

    async def test_422_missing_required_fields(self, client: httpx.AsyncClient):
        resp = await client.post("/auth/login", json={})
        assert resp.status_code == 422

    async def test_422_empty_required_field(self, client: httpx.AsyncClient):
        resp = await client.post("/auth/login", json={"email": "", "password": ""})
        # May return 422 for validation or 401 for auth failure
        assert resp.status_code in (401, 422)

    async def test_409_duplicate_entity(self, client: httpx.AsyncClient, admin_headers: dict):
        """Create a department twice with the same code."""
        import uuid
        code = f"ERR{uuid.uuid4().hex[:4]}"
        payload = {"name": "Error Test Dept", "code": code}
        resp1 = await client.post("/departments/", json=payload, headers=admin_headers)
        if resp1.status_code not in (200, 201):
            pytest.skip("Department creation not available")
        resp2 = await client.post("/departments/", json=payload, headers=admin_headers)
        assert resp2.status_code == 409

    async def test_oversized_file_upload(self, client: httpx.AsyncClient, admin_headers: dict):
        """Upload a very large fake file — should be rejected or handled gracefully."""
        # 20MB of zeros — larger than reasonable invoice PDF
        large_content = b"\x00" * (20 * 1024 * 1024)
        files = {"file": ("huge.pdf", large_content, "application/pdf")}
        resp = await client.post("/invoices/upload", files=files, headers=admin_headers)
        # Accept either 413 (too large) or 400/422 (validation) or 200 (if no size limit)
        assert resp.status_code in (200, 400, 413, 422)

    async def test_method_not_allowed(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.patch("/auth/login", json={}, headers=admin_headers)
        assert resp.status_code == 405
