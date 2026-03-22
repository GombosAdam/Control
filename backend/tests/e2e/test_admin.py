"""Admin E2E tests — 10 tests."""

import uuid

import httpx
import pytest

from tests.conftest import auth_header


class TestAdminUsers:
    async def test_list_users(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/admin/users", headers=admin_headers)
        assert resp.status_code == 200

    async def test_create_user(self, client: httpx.AsyncClient, admin_headers: dict):
        email = f"adm_new_{uuid.uuid4().hex[:8]}@test.local"
        resp = await client.post("/admin/users", json={
            "email": email, "password": "AdminNew1!", "full_name": "Admin Created", "role": "reviewer",
        }, headers=admin_headers)
        assert resp.status_code in (200, 201)

    async def test_update_user(self, client: httpx.AsyncClient, admin_headers: dict):
        email = f"adm_upd_{uuid.uuid4().hex[:8]}@test.local"
        create = await client.post("/admin/users", json={
            "email": email, "password": "AdminUpd1!", "full_name": "To Update", "role": "reviewer",
        }, headers=admin_headers)
        user_id = create.json()["id"]

        resp = await client.put(f"/admin/users/{user_id}", json={"full_name": "Updated Name"}, headers=admin_headers)
        assert resp.status_code == 200

    async def test_delete_user(self, client: httpx.AsyncClient, admin_headers: dict):
        email = f"adm_del_{uuid.uuid4().hex[:8]}@test.local"
        create = await client.post("/admin/users", json={
            "email": email, "password": "AdminDel1!", "full_name": "To Delete", "role": "reviewer",
        }, headers=admin_headers)
        user_id = create.json()["id"]

        resp = await client.delete(f"/admin/users/{user_id}", headers=admin_headers)
        assert resp.status_code == 200

    async def test_non_admin_forbidden(self, client: httpx.AsyncClient, role_tokens: dict):
        resp = await client.get("/admin/users", headers=auth_header(role_tokens["reviewer"]))
        assert resp.status_code == 403


class TestAdminSystem:
    async def test_settings(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/admin/settings", headers=admin_headers)
        assert resp.status_code == 200

    async def test_system_health(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/admin/system", headers=admin_headers)
        assert resp.status_code == 200

    async def test_audit_log(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/admin/audit", headers=admin_headers)
        assert resp.status_code == 200


class TestAdminGPU:
    async def test_gpu_status(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/admin/gpu/status", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "instance_id" in data or "state" in data or "status" in data

    # NOTE: We do NOT test gpu/start or gpu/stop as they incur real AWS costs


class TestAdminUpdateSetting:
    async def test_update_setting(self, client: httpx.AsyncClient, admin_headers: dict):
        # Get current settings first
        settings = await client.get("/admin/settings", headers=admin_headers)
        if settings.status_code != 200:
            pytest.skip("Settings not available")
        items = settings.json()
        if isinstance(items, list) and len(items) > 0:
            key = items[0].get("key", items[0].get("name", ""))
            if key:
                resp = await client.put(
                    f"/admin/settings/{key}",
                    json={"value": items[0].get("value", "")},
                    headers=admin_headers,
                )
                assert resp.status_code == 200
