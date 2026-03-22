"""Dashboard E2E tests — 8 tests."""

import httpx
import pytest

from tests.conftest import auth_header


class TestDashboard:
    async def test_stats(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/dashboard/stats", headers=admin_headers)
        assert resp.status_code == 200

    async def test_recent(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/dashboard/recent", headers=admin_headers)
        assert resp.status_code == 200

    async def test_processing_status(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/dashboard/processing-status", headers=admin_headers)
        assert resp.status_code == 200

    async def test_cfo_kpis(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/dashboard/cfo-kpis", headers=admin_headers)
        assert resp.status_code == 200

    async def test_cfo_trends(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/dashboard/cfo-trends", headers=admin_headers)
        assert resp.status_code == 200

    async def test_cfo_departments(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/dashboard/cfo-departments", headers=admin_headers)
        assert resp.status_code == 200

    async def test_cfo_alerts(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/dashboard/cfo-alerts", headers=admin_headers)
        assert resp.status_code == 200

    async def test_cfo_metrics(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/dashboard/cfo-metrics", headers=admin_headers)
        assert resp.status_code == 200
