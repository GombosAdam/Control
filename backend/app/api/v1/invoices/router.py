import os
import uuid
import aiofiles
from fastapi import APIRouter, Depends, UploadFile, File, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, get_current_user, require_role
from app.api.v1.invoices.service import InvoiceService
from app.api.v1.invoices.schemas import InvoiceUpdateRequest, InvoiceListResponse, ApprovalDecisionRequest
from app.models.user import User, UserRole
from app.config import settings
from app.exceptions import NotFoundError
from app.workers.tasks.process_invoice import process_invoice_task

router = APIRouter()


@router.get("", response_model=InvoiceListResponse)
async def list_invoices(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await InvoiceService.list_invoices(db, page, limit, status, search)


@router.get("/approval-queue")
async def get_approval_queue(
    role: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await InvoiceService.get_pending_approvals(db, role)


@router.get("/{invoice_id}")
async def get_invoice(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await InvoiceService.get_invoice(db, invoice_id)

@router.put("/{invoice_id}")
async def update_invoice(
    invoice_id: str,
    data: InvoiceUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.accountant)),
):
    return await InvoiceService.update_invoice(db, invoice_id, data)

@router.delete("/{invoice_id}")
async def delete_invoice(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    await InvoiceService.delete_invoice(db, invoice_id)
    return {"message": "Invoice deleted"}

@router.post("/upload")
async def upload_invoice(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.accountant, UserRole.reviewer)),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise Exception("Only PDF files are allowed")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    file_id = str(uuid.uuid4())
    stored_filename = f"{file_id}.pdf"
    stored_path = os.path.join(settings.UPLOAD_DIR, stored_filename)

    async with aiofiles.open(stored_path, "wb") as f:
        content = await file.read()
        await f.write(content)

    invoice = await InvoiceService.create_invoice(
        db, file.filename, stored_path, current_user.id
    )

    # Queue for processing via Celery
    process_invoice_task.delay(invoice["id"])

    return invoice

@router.post("/bulk-upload")
async def bulk_upload(
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.accountant, UserRole.reviewer)),
):
    results = []
    for file in files:
        if file.filename and file.filename.lower().endswith(".pdf"):
            os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
            file_id = str(uuid.uuid4())
            stored_path = os.path.join(settings.UPLOAD_DIR, f"{file_id}.pdf")
            async with aiofiles.open(stored_path, "wb") as f:
                content = await file.read()
                await f.write(content)
            invoice = await InvoiceService.create_invoice(db, file.filename, stored_path, current_user.id)
            results.append(invoice)
    # Process all in background
    for inv in results:
        process_invoice_task.delay(inv["id"])
    return {"uploaded": len(results), "invoices": results}

@router.get("/{invoice_id}/pdf")
async def get_invoice_pdf(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoice = await InvoiceService.get_invoice_model(db, invoice_id)
    if not os.path.exists(invoice.stored_filepath):
        raise NotFoundError("PDF file", invoice_id)
    return FileResponse(
        invoice.stored_filepath,
        media_type="application/pdf",
        filename=invoice.original_filename,
    )

@router.post("/batch-import")
async def batch_import_from_inbox(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.accountant)),
):
    """Import all PDFs from data/inbox/ into the system as 'uploaded' invoices."""
    inbox_dir = os.path.join(os.path.dirname(settings.UPLOAD_DIR), "inbox")
    if not os.path.exists(inbox_dir):
        return {"imported": 0, "message": "Inbox directory does not exist"}

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    imported = []

    for filename in sorted(os.listdir(inbox_dir)):
        if not filename.lower().endswith(".pdf"):
            continue
        src = os.path.join(inbox_dir, filename)
        file_id = str(uuid.uuid4())
        dst = os.path.join(settings.UPLOAD_DIR, f"{file_id}.pdf")
        import shutil
        shutil.move(src, dst)
        invoice = await InvoiceService.create_invoice(db, filename, dst, current_user.id)
        imported.append(invoice)

    return {"imported": len(imported), "invoices": imported}

@router.post("/process-all")
async def process_all_uploaded(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.accountant)),
):
    """Start processing all 'uploaded' invoices."""
    from sqlalchemy import select
    from app.models.invoice import Invoice, InvoiceStatus

    result = await db.execute(
        select(Invoice).where(Invoice.status == InvoiceStatus.uploaded)
    )
    invoices = result.scalars().all()

    count = 0
    for inv in invoices:
        process_invoice_task.delay(inv.id)
        count += 1

    return {"queued": count, "message": f"{count} invoices queued for processing"}

@router.post("/{invoice_id}/reprocess")
async def reprocess_invoice(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.accountant)),
):
    result = await InvoiceService.reprocess(db, invoice_id)
    process_invoice_task.delay(invoice_id)
    return result


@router.post("/{invoice_id}/submit-approval")
async def submit_for_approval(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await InvoiceService.submit_for_approval(db, invoice_id, current_user.id)


@router.get("/{invoice_id}/approvals")
async def get_approval_status(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await InvoiceService.get_approval_status(db, invoice_id)


@router.post("/{invoice_id}/approvals/{step}/decide")
async def decide_approval(
    invoice_id: str,
    step: int,
    body: ApprovalDecisionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await InvoiceService.decide_approval(
        db, invoice_id, step, body.decision, body.comment,
        current_user.id, user_role=current_user.role.value,
    )
