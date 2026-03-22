"""Invoice lifecycle E2E tests — 18 tests."""

import uuid
from pathlib import Path

import httpx
import pytest

from tests.conftest import auth_header, role_header


class TestInvoiceList:
    async def test_list_invoices(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/invoices", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        # Response is either a list or paginated object
        assert isinstance(data, (list, dict))


class TestInvoiceUpload:
    async def test_upload_pdf(self, client: httpx.AsyncClient, admin_headers: dict, sample_pdf: Path, cleanup):
        with open(sample_pdf, "rb") as f:
            resp = await client.post(
                "/invoices/upload",
                files={"file": ("invoice.pdf", f, "application/pdf")},
                headers=admin_headers,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        cleanup.add(f"/invoices/{data['id']}")

    async def test_upload_non_pdf_rejected(self, client: httpx.AsyncClient, admin_headers: dict, invalid_file: Path):
        with open(invalid_file, "rb") as f:
            resp = await client.post(
                "/invoices/upload",
                files={"file": ("invalid.txt", f, "text/plain")},
                headers=admin_headers,
            )
        assert resp.status_code in (400, 422)

    async def test_list_after_upload(self, client: httpx.AsyncClient, admin_headers: dict, sample_pdf: Path, cleanup):
        with open(sample_pdf, "rb") as f:
            upload = await client.post(
                "/invoices/upload",
                files={"file": ("test.pdf", f, "application/pdf")},
                headers=admin_headers,
            )
        inv_id = upload.json()["id"]
        cleanup.add(f"/invoices/{inv_id}")

        resp = await client.get("/invoices", headers=admin_headers)
        assert resp.status_code == 200


class TestInvoiceDetail:
    async def test_get_invoice(self, client: httpx.AsyncClient, admin_headers: dict, sample_pdf: Path, cleanup):
        with open(sample_pdf, "rb") as f:
            upload = await client.post(
                "/invoices/upload",
                files={"file": ("detail.pdf", f, "application/pdf")},
                headers=admin_headers,
            )
        inv_id = upload.json()["id"]
        cleanup.add(f"/invoices/{inv_id}")

        resp = await client.get(f"/invoices/{inv_id}", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == inv_id

    async def test_update_invoice(self, client: httpx.AsyncClient, admin_headers: dict, sample_pdf: Path, cleanup):
        with open(sample_pdf, "rb") as f:
            upload = await client.post(
                "/invoices/upload",
                files={"file": ("upd.pdf", f, "application/pdf")},
                headers=admin_headers,
            )
        inv_id = upload.json()["id"]
        cleanup.add(f"/invoices/{inv_id}")

        resp = await client.put(
            f"/invoices/{inv_id}",
            json={"invoice_number": f"UPD-{uuid.uuid4().hex[:6]}"},
            headers=admin_headers,
        )
        assert resp.status_code == 200


class TestBulkOperations:
    async def test_bulk_upload(self, client: httpx.AsyncClient, admin_headers: dict, sample_pdf: Path):
        with open(sample_pdf, "rb") as f:
            content = f.read()
        files = [
            ("files", ("bulk1.pdf", content, "application/pdf")),
            ("files", ("bulk2.pdf", content, "application/pdf")),
        ]
        resp = await client.post("/invoices/bulk-upload", files=files, headers=admin_headers)
        assert resp.status_code == 200

    async def test_batch_import(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.post("/invoices/batch-import", headers=admin_headers)
        # May return 200 even if inbox is empty
        assert resp.status_code == 200

    async def test_process_all(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.post("/invoices/process-all", headers=admin_headers)
        assert resp.status_code == 200


class TestInvoiceReprocess:
    async def test_reprocess(self, client: httpx.AsyncClient, admin_headers: dict, sample_pdf: Path, cleanup):
        with open(sample_pdf, "rb") as f:
            upload = await client.post(
                "/invoices/upload",
                files={"file": ("reproc.pdf", f, "application/pdf")},
                headers=admin_headers,
            )
        inv_id = upload.json()["id"]
        cleanup.add(f"/invoices/{inv_id}")

        resp = await client.post(f"/invoices/{inv_id}/reprocess", headers=admin_headers)
        assert resp.status_code == 200


class TestInvoicePdf:
    async def test_download_pdf(self, client: httpx.AsyncClient, admin_headers: dict, sample_pdf: Path, cleanup):
        with open(sample_pdf, "rb") as f:
            upload = await client.post(
                "/invoices/upload",
                files={"file": ("dl.pdf", f, "application/pdf")},
                headers=admin_headers,
            )
        inv_id = upload.json()["id"]
        cleanup.add(f"/invoices/{inv_id}")

        resp = await client.get(f"/invoices/{inv_id}/pdf", headers=admin_headers)
        assert resp.status_code == 200
        assert "pdf" in resp.headers.get("content-type", "").lower()


class TestApprovalFlow:
    async def test_submit_approval(self, client: httpx.AsyncClient, admin_headers: dict, sample_pdf: Path, cleanup):
        with open(sample_pdf, "rb") as f:
            upload = await client.post(
                "/invoices/upload",
                files={"file": ("appr.pdf", f, "application/pdf")},
                headers=admin_headers,
            )
        inv_id = upload.json()["id"]
        cleanup.add(f"/invoices/{inv_id}")

        resp = await client.post(f"/invoices/{inv_id}/submit-approval", headers=admin_headers)
        assert resp.status_code == 200

    async def test_get_approvals(self, client: httpx.AsyncClient, admin_headers: dict, sample_pdf: Path, cleanup):
        with open(sample_pdf, "rb") as f:
            upload = await client.post(
                "/invoices/upload",
                files={"file": ("apprs.pdf", f, "application/pdf")},
                headers=admin_headers,
            )
        inv_id = upload.json()["id"]
        cleanup.add(f"/invoices/{inv_id}")

        await client.post(f"/invoices/{inv_id}/submit-approval", headers=admin_headers)
        resp = await client.get(f"/invoices/{inv_id}/approvals", headers=admin_headers)
        assert resp.status_code == 200

    async def test_approve_invoice(self, client: httpx.AsyncClient, admin_headers: dict, sample_pdf: Path, cleanup):
        with open(sample_pdf, "rb") as f:
            upload = await client.post(
                "/invoices/upload",
                files={"file": ("apv.pdf", f, "application/pdf")},
                headers=admin_headers,
            )
        inv_id = upload.json()["id"]
        cleanup.add(f"/invoices/{inv_id}")

        await client.post(f"/invoices/{inv_id}/submit-approval", headers=admin_headers)
        approvals = await client.get(f"/invoices/{inv_id}/approvals", headers=admin_headers)
        steps = approvals.json()
        if isinstance(steps, list) and len(steps) > 0:
            step = steps[0].get("step", steps[0].get("id", 1))
            resp = await client.post(
                f"/invoices/{inv_id}/approvals/{step}/decide",
                json={"decision": "approve", "comment": "E2E test"},
                headers=admin_headers,
            )
            assert resp.status_code == 200
        elif isinstance(steps, dict) and steps.get("steps"):
            step = steps["steps"][0].get("step", 1)
            resp = await client.post(
                f"/invoices/{inv_id}/approvals/{step}/decide",
                json={"decision": "approve", "comment": "E2E test"},
                headers=admin_headers,
            )
            assert resp.status_code == 200

    async def test_reject_invoice(self, client: httpx.AsyncClient, admin_headers: dict, sample_pdf: Path, cleanup):
        with open(sample_pdf, "rb") as f:
            upload = await client.post(
                "/invoices/upload",
                files={"file": ("rej.pdf", f, "application/pdf")},
                headers=admin_headers,
            )
        inv_id = upload.json()["id"]
        cleanup.add(f"/invoices/{inv_id}")

        await client.post(f"/invoices/{inv_id}/submit-approval", headers=admin_headers)
        approvals = await client.get(f"/invoices/{inv_id}/approvals", headers=admin_headers)
        steps = approvals.json()
        if isinstance(steps, list) and len(steps) > 0:
            step = steps[0].get("step", steps[0].get("id", 1))
            resp = await client.post(
                f"/invoices/{inv_id}/approvals/{step}/decide",
                json={"decision": "reject", "comment": "E2E reject test"},
                headers=admin_headers,
            )
            assert resp.status_code == 200


class TestInvoiceDelete:
    async def test_admin_delete(self, client: httpx.AsyncClient, admin_headers: dict, sample_pdf: Path):
        with open(sample_pdf, "rb") as f:
            upload = await client.post(
                "/invoices/upload",
                files={"file": ("del.pdf", f, "application/pdf")},
                headers=admin_headers,
            )
        inv_id = upload.json()["id"]
        resp = await client.delete(f"/invoices/{inv_id}", headers=admin_headers)
        assert resp.status_code == 200

    async def test_reviewer_delete_forbidden(
        self, client: httpx.AsyncClient, admin_headers: dict, role_tokens: dict, sample_pdf: Path, cleanup,
    ):
        with open(sample_pdf, "rb") as f:
            upload = await client.post(
                "/invoices/upload",
                files={"file": ("nodelrev.pdf", f, "application/pdf")},
                headers=admin_headers,
            )
        inv_id = upload.json()["id"]
        cleanup.add(f"/invoices/{inv_id}")

        resp = await client.delete(
            f"/invoices/{inv_id}",
            headers=auth_header(role_tokens["reviewer"]),
        )
        assert resp.status_code == 403


class TestApprovalQueue:
    async def test_approval_queue(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/invoices/approval-queue", headers=admin_headers)
        assert resp.status_code == 200
