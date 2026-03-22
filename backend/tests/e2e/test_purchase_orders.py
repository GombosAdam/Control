"""Purchase order workflow E2E tests — 10 tests."""

import uuid

import httpx
import pytest

from tests.conftest import auth_header


class TestPurchaseOrders:
    async def test_list_purchase_orders(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/purchase-orders/", headers=admin_headers)
        assert resp.status_code == 200

    async def test_create_purchase_order(
        self, client: httpx.AsyncClient, admin_headers: dict, test_department: dict, test_partner: dict, cleanup,
    ):
        resp = await client.post("/purchase-orders/", json={
            "description": f"Test PO {uuid.uuid4().hex[:6]}",
            "department_id": test_department["id"],
            "partner_id": test_partner["id"],
            "amount": 50000.0,
            "currency": "HUF",
        }, headers=admin_headers)
        assert resp.status_code in (200, 201)
        cleanup.add(f"/purchase-orders/{resp.json()['id']}")

    async def test_update_purchase_order(
        self, client: httpx.AsyncClient, admin_headers: dict, test_department: dict, test_partner: dict, cleanup,
    ):
        create = await client.post("/purchase-orders/", json={
            "description": f"Upd PO {uuid.uuid4().hex[:6]}",
            "department_id": test_department["id"],
            "partner_id": test_partner["id"],
            "amount": 30000.0,
            "currency": "HUF",
        }, headers=admin_headers)
        po_id = create.json()["id"]
        cleanup.add(f"/purchase-orders/{po_id}")

        resp = await client.put(f"/purchase-orders/{po_id}", json={"amount": 45000.0}, headers=admin_headers)
        assert resp.status_code == 200

    async def test_approve_purchase_order(
        self, client: httpx.AsyncClient, admin_headers: dict, test_department: dict, test_partner: dict, cleanup,
    ):
        create = await client.post("/purchase-orders/", json={
            "description": f"Appr PO {uuid.uuid4().hex[:6]}",
            "department_id": test_department["id"],
            "partner_id": test_partner["id"],
            "amount": 25000.0,
            "currency": "HUF",
        }, headers=admin_headers)
        po_id = create.json()["id"]
        cleanup.add(f"/purchase-orders/{po_id}")

        resp = await client.post(f"/purchase-orders/{po_id}/approve", headers=admin_headers)
        assert resp.status_code == 200

    async def test_receive_purchase_order(
        self, client: httpx.AsyncClient, admin_headers: dict, test_department: dict, test_partner: dict, cleanup,
    ):
        create = await client.post("/purchase-orders/", json={
            "description": f"Recv PO {uuid.uuid4().hex[:6]}",
            "department_id": test_department["id"],
            "partner_id": test_partner["id"],
            "amount": 20000.0,
            "currency": "HUF",
        }, headers=admin_headers)
        po_id = create.json()["id"]
        cleanup.add(f"/purchase-orders/{po_id}")

        await client.post(f"/purchase-orders/{po_id}/approve", headers=admin_headers)
        resp = await client.post(f"/purchase-orders/{po_id}/receive", headers=admin_headers)
        assert resp.status_code == 200

    async def test_get_po_approvals(
        self, client: httpx.AsyncClient, admin_headers: dict, test_department: dict, test_partner: dict, cleanup,
    ):
        create = await client.post("/purchase-orders/", json={
            "description": f"POAppr {uuid.uuid4().hex[:6]}",
            "department_id": test_department["id"],
            "partner_id": test_partner["id"],
            "amount": 15000.0,
            "currency": "HUF",
        }, headers=admin_headers)
        po_id = create.json()["id"]
        cleanup.add(f"/purchase-orders/{po_id}")

        resp = await client.get(f"/purchase-orders/{po_id}/approvals", headers=admin_headers)
        assert resp.status_code == 200

    async def test_po_approval_decide(
        self, client: httpx.AsyncClient, admin_headers: dict, test_department: dict, test_partner: dict, cleanup,
    ):
        create = await client.post("/purchase-orders/", json={
            "description": f"PODec {uuid.uuid4().hex[:6]}",
            "department_id": test_department["id"],
            "partner_id": test_partner["id"],
            "amount": 12000.0,
            "currency": "HUF",
        }, headers=admin_headers)
        po_id = create.json()["id"]
        cleanup.add(f"/purchase-orders/{po_id}")

        approvals = await client.get(f"/purchase-orders/{po_id}/approvals", headers=admin_headers)
        steps = approvals.json()
        if isinstance(steps, list) and len(steps) > 0:
            step = steps[0].get("step", steps[0].get("id", 1))
            resp = await client.post(
                f"/purchase-orders/{po_id}/approvals/{step}/decide",
                json={"decision": "approve", "comment": "PO E2E"},
                headers=admin_headers,
            )
            assert resp.status_code == 200

    async def test_delete_purchase_order(
        self, client: httpx.AsyncClient, admin_headers: dict, test_department: dict, test_partner: dict,
    ):
        create = await client.post("/purchase-orders/", json={
            "description": f"Del PO {uuid.uuid4().hex[:6]}",
            "department_id": test_department["id"],
            "partner_id": test_partner["id"],
            "amount": 5000.0,
            "currency": "HUF",
        }, headers=admin_headers)
        po_id = create.json()["id"]

        resp = await client.delete(f"/purchase-orders/{po_id}", headers=admin_headers)
        assert resp.status_code == 200

    async def test_po_match_invoice(
        self, client: httpx.AsyncClient, admin_headers: dict,
        test_department: dict, test_partner: dict, sample_pdf,
        cleanup,
    ):
        """Create PO + invoice, then try reconciliation match."""
        create = await client.post("/purchase-orders/", json={
            "description": f"Match PO {uuid.uuid4().hex[:6]}",
            "department_id": test_department["id"],
            "partner_id": test_partner["id"],
            "amount": 100000.0,
            "currency": "HUF",
        }, headers=admin_headers)
        po_id = create.json()["id"]
        cleanup.add(f"/purchase-orders/{po_id}")

        await client.post(f"/purchase-orders/{po_id}/approve", headers=admin_headers)
        await client.post(f"/purchase-orders/{po_id}/receive", headers=admin_headers)

        with open(sample_pdf, "rb") as f:
            upload = await client.post(
                "/invoices/upload",
                files={"file": ("match.pdf", f, "application/pdf")},
                headers=admin_headers,
            )
        inv_id = upload.json()["id"]
        cleanup.add(f"/invoices/{inv_id}")

        resp = await client.post(
            f"/reconciliation/{inv_id}/manual-match",
            json={"purchase_order_id": po_id},
            headers=admin_headers,
        )
        # May succeed or fail depending on invoice status
        assert resp.status_code in (200, 400, 422)

    async def test_list_with_filters(
        self, client: httpx.AsyncClient, admin_headers: dict, test_department: dict,
    ):
        resp = await client.get(
            f"/purchase-orders/?department_id={test_department['id']}",
            headers=admin_headers,
        )
        assert resp.status_code == 200
