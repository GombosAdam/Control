"""RBAC matrix E2E tests — 25 tests.

Tests every role × critical endpoint combination.
"""

import uuid
from pathlib import Path

import httpx
import pytest

from tests.conftest import auth_header


def _h(role_tokens: dict, role: str) -> dict:
    return auth_header(role_tokens[role])


# ---- Reviewer ----

class TestReviewerRBAC:
    async def test_reviewer_upload_ok(
        self, client: httpx.AsyncClient, role_tokens: dict, sample_pdf: Path, admin_headers: dict, cleanup,
    ):
        with open(sample_pdf, "rb") as f:
            resp = await client.post(
                "/invoices/upload",
                files={"file": ("rv.pdf", f, "application/pdf")},
                headers=_h(role_tokens, "reviewer"),
            )
        assert resp.status_code == 200
        cleanup.add(f"/invoices/{resp.json()['id']}")

    async def test_reviewer_delete_forbidden(
        self, client: httpx.AsyncClient, role_tokens: dict, admin_headers: dict, sample_pdf: Path, cleanup,
    ):
        with open(sample_pdf, "rb") as f:
            upload = await client.post(
                "/invoices/upload",
                files={"file": ("rvdel.pdf", f, "application/pdf")},
                headers=admin_headers,
            )
        inv_id = upload.json()["id"]
        cleanup.add(f"/invoices/{inv_id}")
        resp = await client.delete(f"/invoices/{inv_id}", headers=_h(role_tokens, "reviewer"))
        assert resp.status_code == 403

    async def test_reviewer_user_mgmt_forbidden(self, client: httpx.AsyncClient, role_tokens: dict):
        resp = await client.get("/admin/users", headers=_h(role_tokens, "reviewer"))
        assert resp.status_code == 403

    async def test_reviewer_create_user_forbidden(self, client: httpx.AsyncClient, role_tokens: dict):
        resp = await client.post("/admin/users", json={
            "email": "hack@test.local", "password": "x", "full_name": "x", "role": "admin",
        }, headers=_h(role_tokens, "reviewer"))
        assert resp.status_code == 403

    async def test_reviewer_budget_create_forbidden(self, client: httpx.AsyncClient, role_tokens: dict):
        resp = await client.post("/budget/lines", json={
            "name": "Hack", "department_id": 1, "period": "2025-01", "amount": 1, "category": "operational",
        }, headers=_h(role_tokens, "reviewer"))
        assert resp.status_code == 403


# ---- Accountant ----

class TestAccountantRBAC:
    async def test_accountant_upload_ok(
        self, client: httpx.AsyncClient, role_tokens: dict, sample_pdf: Path, cleanup,
    ):
        with open(sample_pdf, "rb") as f:
            resp = await client.post(
                "/invoices/upload",
                files={"file": ("acc.pdf", f, "application/pdf")},
                headers=_h(role_tokens, "accountant"),
            )
        assert resp.status_code == 200
        cleanup.add(f"/invoices/{resp.json()['id']}")

    async def test_accountant_update_ok(
        self, client: httpx.AsyncClient, role_tokens: dict, admin_headers: dict, sample_pdf: Path, cleanup,
    ):
        with open(sample_pdf, "rb") as f:
            upload = await client.post(
                "/invoices/upload",
                files={"file": ("accupd.pdf", f, "application/pdf")},
                headers=admin_headers,
            )
        inv_id = upload.json()["id"]
        cleanup.add(f"/invoices/{inv_id}")
        resp = await client.put(
            f"/invoices/{inv_id}",
            json={"invoice_number": f"ACC-{uuid.uuid4().hex[:6]}"},
            headers=_h(role_tokens, "accountant"),
        )
        assert resp.status_code == 200

    async def test_accountant_user_mgmt_forbidden(self, client: httpx.AsyncClient, role_tokens: dict):
        resp = await client.get("/admin/users", headers=_h(role_tokens, "accountant"))
        assert resp.status_code == 403

    async def test_accountant_budget_create_ok(
        self, client: httpx.AsyncClient, role_tokens: dict, test_department: dict, cleanup,
    ):
        resp = await client.post("/budget/lines", json={
            "name": f"Acc Budget {uuid.uuid4().hex[:6]}",
            "department_id": test_department["id"],
            "period": "2025-10",
            "amount": 5000.0,
            "category": "operational",
        }, headers=_h(role_tokens, "accountant"))
        assert resp.status_code in (200, 201)
        cleanup.add(f"/budget/lines/{resp.json()['id']}")

    async def test_accountant_delete_invoice_forbidden(
        self, client: httpx.AsyncClient, role_tokens: dict, admin_headers: dict, sample_pdf: Path, cleanup,
    ):
        with open(sample_pdf, "rb") as f:
            upload = await client.post(
                "/invoices/upload",
                files={"file": ("accdel.pdf", f, "application/pdf")},
                headers=admin_headers,
            )
        inv_id = upload.json()["id"]
        cleanup.add(f"/invoices/{inv_id}")
        resp = await client.delete(f"/invoices/{inv_id}", headers=_h(role_tokens, "accountant"))
        assert resp.status_code == 403


# ---- Department Head ----

class TestDepartmentHeadRBAC:
    async def test_dept_head_budget_approve_ok(
        self, client: httpx.AsyncClient, role_tokens: dict, admin_headers: dict, test_department: dict, cleanup,
    ):
        create = await client.post("/budget/lines", json={
            "name": f"DH Appr {uuid.uuid4().hex[:6]}",
            "department_id": test_department["id"],
            "period": "2025-11",
            "amount": 10000.0,
            "category": "operational",
        }, headers=admin_headers)
        line_id = create.json()["id"]
        cleanup.add(f"/budget/lines/{line_id}")

        resp = await client.post(f"/budget/lines/{line_id}/approve", headers=_h(role_tokens, "department_head"))
        assert resp.status_code == 200

    async def test_dept_head_budget_lock_forbidden(
        self, client: httpx.AsyncClient, role_tokens: dict, admin_headers: dict, test_department: dict, cleanup,
    ):
        create = await client.post("/budget/lines", json={
            "name": f"DH Lock {uuid.uuid4().hex[:6]}",
            "department_id": test_department["id"],
            "period": "2025-11",
            "amount": 10000.0,
            "category": "operational",
        }, headers=admin_headers)
        line_id = create.json()["id"]
        cleanup.add(f"/budget/lines/{line_id}")

        await client.post(f"/budget/lines/{line_id}/approve", headers=admin_headers)
        resp = await client.post(f"/budget/lines/{line_id}/lock", headers=_h(role_tokens, "department_head"))
        assert resp.status_code == 403

    async def test_dept_head_user_mgmt_forbidden(self, client: httpx.AsyncClient, role_tokens: dict):
        resp = await client.get("/admin/users", headers=_h(role_tokens, "department_head"))
        assert resp.status_code == 403


# ---- CFO ----

class TestCFORBAC:
    async def test_cfo_budget_approve_ok(
        self, client: httpx.AsyncClient, role_tokens: dict, admin_headers: dict, test_department: dict, cleanup,
    ):
        create = await client.post("/budget/lines", json={
            "name": f"CFO Appr {uuid.uuid4().hex[:6]}",
            "department_id": test_department["id"],
            "period": "2025-12",
            "amount": 200000.0,
            "category": "operational",
        }, headers=admin_headers)
        line_id = create.json()["id"]
        cleanup.add(f"/budget/lines/{line_id}")

        resp = await client.post(f"/budget/lines/{line_id}/approve", headers=_h(role_tokens, "cfo"))
        assert resp.status_code == 200

    async def test_cfo_budget_lock_ok(
        self, client: httpx.AsyncClient, role_tokens: dict, admin_headers: dict, test_department: dict, cleanup,
    ):
        create = await client.post("/budget/lines", json={
            "name": f"CFO Lock {uuid.uuid4().hex[:6]}",
            "department_id": test_department["id"],
            "period": "2025-12",
            "amount": 150000.0,
            "category": "operational",
        }, headers=admin_headers)
        line_id = create.json()["id"]
        cleanup.add(f"/budget/lines/{line_id}")

        await client.post(f"/budget/lines/{line_id}/approve", headers=admin_headers)
        resp = await client.post(f"/budget/lines/{line_id}/lock", headers=_h(role_tokens, "cfo"))
        assert resp.status_code == 200

    async def test_cfo_dashboard_ok(self, client: httpx.AsyncClient, role_tokens: dict):
        resp = await client.get("/dashboard/cfo-kpis", headers=_h(role_tokens, "cfo"))
        assert resp.status_code == 200

    async def test_cfo_user_mgmt_forbidden(self, client: httpx.AsyncClient, role_tokens: dict):
        resp = await client.get("/admin/users", headers=_h(role_tokens, "cfo"))
        assert resp.status_code == 403


# ---- Admin ----

class TestAdminRBAC:
    async def test_admin_user_list(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/admin/users", headers=admin_headers)
        assert resp.status_code == 200

    async def test_admin_create_user(self, client: httpx.AsyncClient, admin_headers: dict):
        email = f"rbac_admin_{uuid.uuid4().hex[:8]}@test.local"
        resp = await client.post("/admin/users", json={
            "email": email, "password": "AdminRBAC1!", "full_name": "RBAC Admin Test", "role": "reviewer",
        }, headers=admin_headers)
        assert resp.status_code in (200, 201)

    async def test_admin_settings(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/admin/settings", headers=admin_headers)
        assert resp.status_code == 200

    async def test_admin_system_health(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/admin/system", headers=admin_headers)
        assert resp.status_code == 200

    async def test_admin_audit_log(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/admin/audit", headers=admin_headers)
        assert resp.status_code == 200

    async def test_admin_gpu_status(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/admin/gpu/status", headers=admin_headers)
        assert resp.status_code == 200
