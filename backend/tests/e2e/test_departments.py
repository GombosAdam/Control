"""Departments E2E tests — 4 tests."""

import uuid

import httpx
import pytest


class TestDepartments:
    async def test_list_departments(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/departments/", headers=admin_headers)
        assert resp.status_code == 200

    async def test_create_department(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.post("/departments/", json={
            "name": f"Dept {uuid.uuid4().hex[:6]}",
            "code": f"D{uuid.uuid4().hex[:5]}",
        }, headers=admin_headers)
        assert resp.status_code in (200, 201)

    async def test_get_department(self, client: httpx.AsyncClient, admin_headers: dict, test_department: dict):
        resp = await client.get(f"/departments/{test_department['id']}", headers=admin_headers)
        assert resp.status_code == 200

    async def test_update_department(self, client: httpx.AsyncClient, admin_headers: dict, test_department: dict):
        resp = await client.put(
            f"/departments/{test_department['id']}",
            json={"name": f"Updated Dept {uuid.uuid4().hex[:6]}"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
