"""Scenarios E2E tests — 4 tests."""

import uuid

import httpx
import pytest


class TestScenarios:
    async def test_list_scenarios(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/scenarios", headers=admin_headers)
        assert resp.status_code == 200

    async def test_create_scenario(self, client: httpx.AsyncClient, admin_headers: dict, cleanup):
        resp = await client.post("/scenarios", json={
            "name": f"Scenario {uuid.uuid4().hex[:6]}",
            "description": "E2E test scenario",
        }, headers=admin_headers)
        assert resp.status_code in (200, 201)
        if "id" in resp.json():
            cleanup.add(f"/scenarios/{resp.json()['id']}")

    async def test_copy_scenario(self, client: httpx.AsyncClient, admin_headers: dict, cleanup):
        create = await client.post("/scenarios", json={
            "name": f"Copy Src {uuid.uuid4().hex[:6]}",
            "description": "Source scenario",
        }, headers=admin_headers)
        if create.status_code not in (200, 201):
            pytest.skip("Scenario creation failed")
        src_id = create.json()["id"]
        cleanup.add(f"/scenarios/{src_id}")

        resp = await client.post("/scenarios/copy", json={
            "source_scenario_id": src_id,
            "name": f"Copy Dst {uuid.uuid4().hex[:6]}",
            "description": "Copied scenario",
            "adjustment_pct": 5.0,
        }, headers=admin_headers)
        assert resp.status_code in (200, 201)
        if resp.status_code in (200, 201) and "id" in resp.json():
            cleanup.add(f"/scenarios/{resp.json()['id']}")

    async def test_delete_scenario(self, client: httpx.AsyncClient, admin_headers: dict):
        create = await client.post("/scenarios", json={
            "name": f"Del Scen {uuid.uuid4().hex[:6]}",
            "description": "To be deleted",
        }, headers=admin_headers)
        if create.status_code not in (200, 201):
            pytest.skip("Scenario creation failed")
        scen_id = create.json()["id"]
        resp = await client.delete(f"/scenarios/{scen_id}", headers=admin_headers)
        assert resp.status_code == 200
