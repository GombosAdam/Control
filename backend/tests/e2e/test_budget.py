"""Budget workflow E2E tests — 15 tests."""

import uuid

import httpx
import pytest

from tests.conftest import auth_header


class TestBudgetLines:
    async def test_list_budget_lines(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/budget/lines", headers=admin_headers)
        assert resp.status_code == 200

    async def test_create_budget_line(
        self, client: httpx.AsyncClient, admin_headers: dict, test_department: dict, cleanup,
    ):
        resp = await client.post("/budget/lines", json={
            "name": f"Test Budget {uuid.uuid4().hex[:6]}",
            "department_id": test_department["id"],
            "period": "2025-01",
            "amount": 100000.0,
            "category": "operational",
        }, headers=admin_headers)
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert "id" in data
        cleanup.add(f"/budget/lines/{data['id']}")

    async def test_update_budget_line(
        self, client: httpx.AsyncClient, admin_headers: dict, test_department: dict, cleanup,
    ):
        create = await client.post("/budget/lines", json={
            "name": f"Upd Budget {uuid.uuid4().hex[:6]}",
            "department_id": test_department["id"],
            "period": "2025-02",
            "amount": 50000.0,
            "category": "operational",
        }, headers=admin_headers)
        line_id = create.json()["id"]
        cleanup.add(f"/budget/lines/{line_id}")

        resp = await client.put(f"/budget/lines/{line_id}", json={"amount": 75000.0}, headers=admin_headers)
        assert resp.status_code == 200


class TestBudgetApproval:
    async def test_approve_budget_line(
        self, client: httpx.AsyncClient, admin_headers: dict, test_department: dict, cleanup,
    ):
        create = await client.post("/budget/lines", json={
            "name": f"Appr Budget {uuid.uuid4().hex[:6]}",
            "department_id": test_department["id"],
            "period": "2025-03",
            "amount": 60000.0,
            "category": "operational",
        }, headers=admin_headers)
        line_id = create.json()["id"]
        cleanup.add(f"/budget/lines/{line_id}")

        resp = await client.post(f"/budget/lines/{line_id}/approve", headers=admin_headers)
        assert resp.status_code == 200

    async def test_lock_budget_line(
        self, client: httpx.AsyncClient, admin_headers: dict, test_department: dict, cleanup,
    ):
        create = await client.post("/budget/lines", json={
            "name": f"Lock Budget {uuid.uuid4().hex[:6]}",
            "department_id": test_department["id"],
            "period": "2025-04",
            "amount": 80000.0,
            "category": "operational",
        }, headers=admin_headers)
        line_id = create.json()["id"]
        cleanup.add(f"/budget/lines/{line_id}")

        await client.post(f"/budget/lines/{line_id}/approve", headers=admin_headers)
        resp = await client.post(f"/budget/lines/{line_id}/lock", headers=admin_headers)
        assert resp.status_code == 200

    async def test_bulk_approve(
        self, client: httpx.AsyncClient, admin_headers: dict, test_department: dict, cleanup,
    ):
        ids = []
        for i in range(2):
            r = await client.post("/budget/lines", json={
                "name": f"Bulk Appr {i} {uuid.uuid4().hex[:6]}",
                "department_id": test_department["id"],
                "period": "2025-05",
                "amount": 10000.0,
                "category": "operational",
            }, headers=admin_headers)
            lid = r.json()["id"]
            ids.append(lid)
            cleanup.add(f"/budget/lines/{lid}")

        resp = await client.post("/budget/lines/bulk-approve", json={"line_ids": ids}, headers=admin_headers)
        assert resp.status_code == 200

    async def test_bulk_lock(
        self, client: httpx.AsyncClient, admin_headers: dict, test_department: dict, cleanup,
    ):
        ids = []
        for i in range(2):
            r = await client.post("/budget/lines", json={
                "name": f"Bulk Lock {i} {uuid.uuid4().hex[:6]}",
                "department_id": test_department["id"],
                "period": "2025-06",
                "amount": 10000.0,
                "category": "operational",
            }, headers=admin_headers)
            lid = r.json()["id"]
            ids.append(lid)
            cleanup.add(f"/budget/lines/{lid}")
            await client.post(f"/budget/lines/{lid}/approve", headers=admin_headers)

        resp = await client.post("/budget/lines/bulk-lock", json={"line_ids": ids}, headers=admin_headers)
        assert resp.status_code == 200


class TestBudgetAudit:
    async def test_audit_log(
        self, client: httpx.AsyncClient, admin_headers: dict, test_department: dict, cleanup,
    ):
        create = await client.post("/budget/lines", json={
            "name": f"Audit Budget {uuid.uuid4().hex[:6]}",
            "department_id": test_department["id"],
            "period": "2025-07",
            "amount": 20000.0,
            "category": "operational",
        }, headers=admin_headers)
        line_id = create.json()["id"]
        cleanup.add(f"/budget/lines/{line_id}")

        resp = await client.get(f"/budget/lines/{line_id}/audit", headers=admin_headers)
        assert resp.status_code == 200

    async def test_comments(
        self, client: httpx.AsyncClient, admin_headers: dict, test_department: dict, cleanup,
    ):
        create = await client.post("/budget/lines", json={
            "name": f"Comment Budget {uuid.uuid4().hex[:6]}",
            "department_id": test_department["id"],
            "period": "2025-08",
            "amount": 30000.0,
            "category": "operational",
        }, headers=admin_headers)
        line_id = create.json()["id"]
        cleanup.add(f"/budget/lines/{line_id}")

        await client.post(f"/budget/lines/{line_id}/comments", json={"text": "E2E comment"}, headers=admin_headers)
        resp = await client.get(f"/budget/lines/{line_id}/comments", headers=admin_headers)
        assert resp.status_code == 200


class TestBudgetAdvanced:
    async def test_copy_period(self, client: httpx.AsyncClient, admin_headers: dict, test_department: dict):
        resp = await client.post("/budget/lines/copy-period", json={
            "source_period": "2025-01",
            "target_period": "2025-12",
            "department_id": test_department["id"],
        }, headers=admin_headers)
        assert resp.status_code == 200

    async def test_bulk_adjust(
        self, client: httpx.AsyncClient, admin_headers: dict, test_department: dict, cleanup,
    ):
        create = await client.post("/budget/lines", json={
            "name": f"Adjust Budget {uuid.uuid4().hex[:6]}",
            "department_id": test_department["id"],
            "period": "2025-09",
            "amount": 100000.0,
            "category": "operational",
        }, headers=admin_headers)
        line_id = create.json()["id"]
        cleanup.add(f"/budget/lines/{line_id}")

        resp = await client.post(
            "/budget/lines/bulk-adjust",
            json={"line_ids": [line_id], "percentage": 10.0},
            headers=admin_headers,
        )
        assert resp.status_code == 200

    async def test_create_forecast(self, client: httpx.AsyncClient, admin_headers: dict, test_department: dict):
        resp = await client.post("/budget/lines/create-forecast", json={
            "source_period": "2025-01",
            "department_id": test_department["id"],
            "adjustment_pct": 5.0,
        }, headers=admin_headers)
        assert resp.status_code == 200

    async def test_create_year_plan(self, client: httpx.AsyncClient, admin_headers: dict, test_department: dict):
        resp = await client.post("/budget/create-year-plan", json={
            "year": 2026,
            "source_year": 2025,
            "adjustment_pct": 3.0,
            "department_id": test_department["id"],
        }, headers=admin_headers)
        assert resp.status_code == 200

    async def test_periods(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/budget/periods", headers=admin_headers)
        assert resp.status_code == 200

    async def test_availability(self, client: httpx.AsyncClient, admin_headers: dict, test_department: dict):
        resp = await client.get(f"/budget/availability/{test_department['id']}", headers=admin_headers)
        assert resp.status_code == 200
