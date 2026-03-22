"""Partners E2E tests — 6 tests."""

import uuid

import httpx
import pytest


class TestPartners:
    async def test_list_partners(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/partners", headers=admin_headers)
        assert resp.status_code == 200

    async def test_create_partner(self, client: httpx.AsyncClient, admin_headers: dict, cleanup):
        resp = await client.post("/partners", json={
            "name": f"Partner {uuid.uuid4().hex[:6]}",
            "tax_number": f"88{uuid.uuid4().hex[:6]}-2-42",
            "partner_type": "supplier",
        }, headers=admin_headers)
        assert resp.status_code in (200, 201)
        cleanup.add(f"/partners/{resp.json()['id']}")

    async def test_get_partner(self, client: httpx.AsyncClient, admin_headers: dict, test_partner: dict):
        resp = await client.get(f"/partners/{test_partner['id']}", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == test_partner["id"]

    async def test_update_partner(self, client: httpx.AsyncClient, admin_headers: dict, cleanup):
        create = await client.post("/partners", json={
            "name": f"Upd Partner {uuid.uuid4().hex[:6]}",
            "tax_number": f"77{uuid.uuid4().hex[:6]}-2-42",
            "partner_type": "supplier",
        }, headers=admin_headers)
        pid = create.json()["id"]
        cleanup.add(f"/partners/{pid}")

        resp = await client.put(f"/partners/{pid}", json={"name": "Updated Partner"}, headers=admin_headers)
        assert resp.status_code == 200

    async def test_delete_partner(self, client: httpx.AsyncClient, admin_headers: dict):
        create = await client.post("/partners", json={
            "name": f"Del Partner {uuid.uuid4().hex[:6]}",
            "tax_number": f"66{uuid.uuid4().hex[:6]}-2-42",
            "partner_type": "supplier",
        }, headers=admin_headers)
        pid = create.json()["id"]
        resp = await client.delete(f"/partners/{pid}", headers=admin_headers)
        assert resp.status_code == 200

    async def test_partner_invoices(self, client: httpx.AsyncClient, admin_headers: dict, test_partner: dict):
        resp = await client.get(f"/partners/{test_partner['id']}/invoices", headers=admin_headers)
        assert resp.status_code == 200
