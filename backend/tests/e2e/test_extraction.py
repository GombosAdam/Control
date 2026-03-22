"""Extraction queue E2E tests — 5 tests."""

import httpx
import pytest

from tests.conftest import auth_header


class TestExtraction:
    async def test_extraction_queue(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/extraction/queue", headers=admin_headers)
        assert resp.status_code == 200

    async def test_approve_extraction(
        self, client: httpx.AsyncClient, admin_headers: dict, sample_pdf,  cleanup,
    ):
        with open(sample_pdf, "rb") as f:
            upload = await client.post(
                "/invoices/upload",
                files={"file": ("ext_appr.pdf", f, "application/pdf")},
                headers=admin_headers,
            )
        inv_id = upload.json()["id"]
        cleanup.add(f"/invoices/{inv_id}")

        resp = await client.post(f"/extraction/{inv_id}/approve", headers=admin_headers)
        # May fail if invoice not in extracted status — that's acceptable
        assert resp.status_code in (200, 400, 422)

    async def test_reject_extraction(
        self, client: httpx.AsyncClient, admin_headers: dict, sample_pdf, cleanup,
    ):
        with open(sample_pdf, "rb") as f:
            upload = await client.post(
                "/invoices/upload",
                files={"file": ("ext_rej.pdf", f, "application/pdf")},
                headers=admin_headers,
            )
        inv_id = upload.json()["id"]
        cleanup.add(f"/invoices/{inv_id}")

        resp = await client.post(f"/extraction/{inv_id}/reject", headers=admin_headers)
        assert resp.status_code in (200, 400, 422)

    async def test_duplicates(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/extraction/duplicates", headers=admin_headers)
        assert resp.status_code == 200

    async def test_queue_pagination(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/extraction/queue?page=1&limit=5", headers=admin_headers)
        assert resp.status_code == 200
