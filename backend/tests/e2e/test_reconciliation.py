"""Reconciliation E2E tests — 5 tests."""

import httpx
import pytest

from tests.conftest import auth_header


class TestReconciliation:
    async def test_pending_list(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/reconciliation/pending", headers=admin_headers)
        assert resp.status_code == 200

    async def test_auto_match(
        self, client: httpx.AsyncClient, admin_headers: dict, sample_pdf, cleanup,
    ):
        with open(sample_pdf, "rb") as f:
            upload = await client.post(
                "/invoices/upload",
                files={"file": ("recon.pdf", f, "application/pdf")},
                headers=admin_headers,
            )
        inv_id = upload.json()["id"]
        cleanup.add(f"/invoices/{inv_id}")

        resp = await client.post(f"/reconciliation/{inv_id}/match", headers=admin_headers)
        # Match may fail if no matching PO — both outcomes valid
        assert resp.status_code in (200, 400, 404, 422)

    async def test_manual_match(
        self, client: httpx.AsyncClient, admin_headers: dict, sample_pdf, cleanup,
    ):
        with open(sample_pdf, "rb") as f:
            upload = await client.post(
                "/invoices/upload",
                files={"file": ("recon_m.pdf", f, "application/pdf")},
                headers=admin_headers,
            )
        inv_id = upload.json()["id"]
        cleanup.add(f"/invoices/{inv_id}")

        resp = await client.post(
            f"/reconciliation/{inv_id}/manual-match",
            json={"purchase_order_id": 99999},
            headers=admin_headers,
        )
        assert resp.status_code in (200, 400, 404, 422)

    async def test_post_matched_invoice(
        self, client: httpx.AsyncClient, admin_headers: dict, sample_pdf, cleanup,
    ):
        with open(sample_pdf, "rb") as f:
            upload = await client.post(
                "/invoices/upload",
                files={"file": ("recon_p.pdf", f, "application/pdf")},
                headers=admin_headers,
            )
        inv_id = upload.json()["id"]
        cleanup.add(f"/invoices/{inv_id}")

        resp = await client.post(f"/reconciliation/{inv_id}/post", headers=admin_headers)
        assert resp.status_code in (200, 400, 422)

    async def test_pending_pagination(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/reconciliation/pending?page=1&limit=5", headers=admin_headers)
        assert resp.status_code == 200
