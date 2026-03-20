import os
import uuid
import threading
import aiofiles
from fastapi import APIRouter, Depends, UploadFile, File, Query, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, get_current_user
from app.api.v1.invoices.service import InvoiceService
from app.api.v1.invoices.schemas import InvoiceUpdateRequest, InvoiceListResponse
from app.models.user import User
from app.config import settings
from app.exceptions import NotFoundError

router = APIRouter()


def _run_processing(invoice_id: str):
    """Run invoice processing in a background thread."""
    from app.workers.tasks.process_invoice import process_invoice_sync
    process_invoice_sync(invoice_id, settings.DATABASE_URL_SYNC)


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
    current_user: User = Depends(get_current_user),
):
    return await InvoiceService.update_invoice(db, invoice_id, data)

@router.delete("/{invoice_id}")
async def delete_invoice(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await InvoiceService.delete_invoice(db, invoice_id)
    return {"message": "Invoice deleted"}

@router.post("/upload")
async def upload_invoice(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
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

    # Queue for processing in background thread
    threading.Thread(target=_run_processing, args=(invoice["id"],), daemon=True).start()

    return invoice

@router.post("/bulk-upload")
async def bulk_upload(
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
        threading.Thread(target=_run_processing, args=(inv["id"],), daemon=True).start()
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
        threading.Thread(target=_run_processing, args=(inv.id,), daemon=True).start()
        count += 1

    return {"queued": count, "message": f"{count} invoices queued for processing"}

@router.post("/{invoice_id}/reprocess")
async def reprocess_invoice(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await InvoiceService.reprocess(db, invoice_id)
    threading.Thread(target=_run_processing, args=(invoice_id,), daemon=True).start()
    return result
