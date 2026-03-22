"""Accounting E2E tests — 6 tests."""

import uuid

import httpx
import pytest


class TestAccounting:
    async def test_accounting_invoices(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/accounting/invoices", headers=admin_headers)
        assert resp.status_code == 200

    async def test_accounting_entries(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/accounting/entries", headers=admin_headers)
        assert resp.status_code == 200

    async def test_accounting_summary(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/accounting/summary", headers=admin_headers)
        assert resp.status_code == 200

    async def test_templates_list(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/accounting/templates", headers=admin_headers)
        assert resp.status_code == 200

    async def test_template_create(self, client: httpx.AsyncClient, admin_headers: dict, cleanup):
        resp = await client.post("/accounting/templates", json={
            "name": f"Test Template {uuid.uuid4().hex[:6]}",
            "debit_account": "5110",
            "credit_account": "4540",
            "description": "E2E test template",
        }, headers=admin_headers)
        assert resp.status_code in (200, 201)
        if resp.status_code in (200, 201) and "id" in resp.json():
            tmpl_id = resp.json()["id"]
            cleanup.add(f"/accounting/templates/{tmpl_id}")

    async def test_template_update(self, client: httpx.AsyncClient, admin_headers: dict, cleanup):
        create = await client.post("/accounting/templates", json={
            "name": f"Upd Template {uuid.uuid4().hex[:6]}",
            "debit_account": "5120",
            "credit_account": "4550",
            "description": "Update test",
        }, headers=admin_headers)
        if create.status_code not in (200, 201):
            pytest.skip("Template creation failed")
        tmpl_id = create.json()["id"]
        cleanup.add(f"/accounting/templates/{tmpl_id}")

        resp = await client.put(
            f"/accounting/templates/{tmpl_id}",
            json={"description": "Updated by E2E"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
