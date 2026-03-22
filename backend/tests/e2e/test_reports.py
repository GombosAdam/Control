"""Reports E2E tests — 3 tests."""

import httpx
import pytest


class TestReports:
    async def test_monthly_report(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/reports/monthly?year=2025&month=1", headers=admin_headers)
        assert resp.status_code == 200

    async def test_vat_report(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/reports/vat?year=2025", headers=admin_headers)
        assert resp.status_code == 200

    async def test_suppliers_report(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/reports/suppliers", headers=admin_headers)
        assert resp.status_code == 200
