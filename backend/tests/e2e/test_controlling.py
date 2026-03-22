"""Controlling E2E tests — 4 tests."""

import httpx
import pytest


class TestControlling:
    async def test_plan_vs_actual(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/controlling/plan-vs-actual", headers=admin_headers)
        assert resp.status_code == 200

    async def test_budget_status(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/controlling/budget-status", headers=admin_headers)
        assert resp.status_code == 200

    async def test_ebitda(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/controlling/ebitda", headers=admin_headers)
        assert resp.status_code == 200

    async def test_pnl(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/controlling/pnl", headers=admin_headers)
        assert resp.status_code == 200
