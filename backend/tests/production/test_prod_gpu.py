"""Production GPU instance tests."""

import os

import httpx
import pytest

from tests.conftest import _login, auth_header

pytestmark = pytest.mark.production

PROD_URL = os.environ.get("TEST_BASE_URL", "https://invoice.rhcdemoaccount2.com")


class TestProductionGPU:
    async def _admin_token(self) -> str:
        async with httpx.AsyncClient(timeout=15.0) as c:
            return await _login(
                httpx.AsyncClient(base_url=f"{PROD_URL}/api/v1", timeout=15.0),
                "admin@invoice.local",
                "admin123",
            )

    async def test_gpu_status_endpoint(self):
        async with httpx.AsyncClient(base_url=f"{PROD_URL}/api/v1", timeout=15.0) as c:
            token = await _login(c, "admin@invoice.local", "admin123")
            resp = await c.get("/admin/gpu/status", headers=auth_header(token))
        assert resp.status_code == 200
        data = resp.json()
        assert "state" in data or "instance_id" in data or "status" in data

    async def test_gpu_instance_state(self):
        async with httpx.AsyncClient(base_url=f"{PROD_URL}/api/v1", timeout=15.0) as c:
            token = await _login(c, "admin@invoice.local", "admin123")
            resp = await c.get("/admin/gpu/status", headers=auth_header(token))
        data = resp.json()
        state = data.get("state", data.get("status", ""))
        assert state in ("running", "stopped", "stopping", "pending", "unknown", "")

    async def test_ollama_ready_if_running(self):
        async with httpx.AsyncClient(base_url=f"{PROD_URL}/api/v1", timeout=15.0) as c:
            token = await _login(c, "admin@invoice.local", "admin123")
            resp = await c.get("/admin/gpu/status", headers=auth_header(token))
        data = resp.json()
        state = data.get("state", data.get("status", ""))
        if state == "running":
            ollama_status = data.get("ollama_status", data.get("ollama_ready", ""))
            assert ollama_status in (True, "ready", "ok", "healthy")
        else:
            pytest.skip("GPU instance not running — skipping Ollama check")

    async def test_model_available_if_running(self):
        async with httpx.AsyncClient(base_url=f"{PROD_URL}/api/v1", timeout=15.0) as c:
            token = await _login(c, "admin@invoice.local", "admin123")
            resp = await c.get("/admin/gpu/status", headers=auth_header(token))
        data = resp.json()
        state = data.get("state", data.get("status", ""))
        if state == "running":
            models = data.get("models", [])
            model_names = [m.get("name", m) if isinstance(m, dict) else m for m in models]
            assert any("qwen" in str(m).lower() for m in model_names), f"qwen model not found: {model_names}"
        else:
            pytest.skip("GPU instance not running")
