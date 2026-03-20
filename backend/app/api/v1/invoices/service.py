import math
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.invoice import Invoice, InvoiceStatus
from app.exceptions import NotFoundError

class InvoiceService:
    @staticmethod
    async def list_invoices(db: AsyncSession, page: int, limit: int, status: str | None, search: str | None) -> dict:
        query = select(Invoice)
        count_query = select(func.count(Invoice.id))

        if status:
            try:
                status_enum = InvoiceStatus(status)
                query = query.where(Invoice.status == status_enum)
                count_query = count_query.where(Invoice.status == status_enum)
            except ValueError:
                pass

        if search:
            search_filter = Invoice.original_filename.ilike(f"%{search}%")
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        total = await db.scalar(count_query) or 0

        result = await db.execute(
            query.order_by(Invoice.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        invoices = result.scalars().all()

        return {
            "items": [
                {
                    "id": inv.id,
                    "invoice_number": inv.invoice_number,
                    "partner_id": inv.partner_id,
                    "partner_name": inv.partner.name if inv.partner else None,
                    "status": inv.status.value,
                    "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
                    "fulfillment_date": inv.fulfillment_date.isoformat() if inv.fulfillment_date else None,
                    "due_date": inv.due_date.isoformat() if inv.due_date else None,
                    "payment_method": inv.payment_method,
                    "net_amount": inv.net_amount,
                    "vat_rate": inv.vat_rate,
                    "vat_amount": inv.vat_amount,
                    "gross_amount": inv.gross_amount,
                    "currency": inv.currency,
                    "original_filename": inv.original_filename,
                    "ocr_confidence": inv.ocr_confidence,
                    "is_duplicate": inv.is_duplicate,
                    "similarity_score": inv.similarity_score,
                    "created_at": inv.created_at.isoformat(),
                    "updated_at": inv.updated_at.isoformat(),
                }
                for inv in invoices
            ],
            "total": total,
            "page": page,
            "limit": limit,
            "pages": math.ceil(total / limit) if total > 0 else 1,
        }

    @staticmethod
    async def get_invoice(db: AsyncSession, invoice_id: str) -> dict:
        inv = await InvoiceService.get_invoice_model(db, invoice_id)
        return {
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "partner_id": inv.partner_id,
            "partner_name": inv.partner.name if inv.partner else None,
            "status": inv.status.value,
            "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
            "fulfillment_date": inv.fulfillment_date.isoformat() if inv.fulfillment_date else None,
            "due_date": inv.due_date.isoformat() if inv.due_date else None,
            "payment_method": inv.payment_method,
            "net_amount": inv.net_amount,
            "vat_rate": inv.vat_rate,
            "vat_amount": inv.vat_amount,
            "gross_amount": inv.gross_amount,
            "currency": inv.currency,
            "original_filename": inv.original_filename,
            "stored_filepath": inv.stored_filepath,
            "ocr_text": inv.ocr_text,
            "ocr_confidence": inv.ocr_confidence,
            "is_duplicate": inv.is_duplicate,
            "duplicate_of_id": inv.duplicate_of_id,
            "similarity_score": inv.similarity_score,
            "reviewed_by_id": inv.reviewed_by_id,
            "uploaded_by_id": inv.uploaded_by_id,
            "created_at": inv.created_at.isoformat(),
            "updated_at": inv.updated_at.isoformat(),
            "lines": [
                {
                    "id": line.id,
                    "description": line.description,
                    "quantity": line.quantity,
                    "unit_price": line.unit_price,
                    "net_amount": line.net_amount,
                    "vat_rate": line.vat_rate,
                    "vat_amount": line.vat_amount,
                    "gross_amount": line.gross_amount,
                    "sort_order": line.sort_order,
                }
                for line in (inv.lines or [])
            ],
            "extraction_result": {
                "id": inv.extraction_result.id,
                "extracted_data": inv.extraction_result.extracted_data,
                "confidence_scores": inv.extraction_result.confidence_scores,
                "model_used": inv.extraction_result.model_used,
                "extraction_time_ms": inv.extraction_result.extraction_time_ms,
            } if inv.extraction_result else None,
        }

    @staticmethod
    async def get_invoice_model(db: AsyncSession, invoice_id: str) -> Invoice:
        result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
        invoice = result.scalar_one_or_none()
        if not invoice:
            raise NotFoundError("Invoice", invoice_id)
        return invoice

    @staticmethod
    async def create_invoice(db: AsyncSession, filename: str, stored_path: str, user_id: str) -> dict:
        invoice = Invoice(
            original_filename=filename,
            stored_filepath=stored_path,
            uploaded_by_id=user_id,
            status=InvoiceStatus.uploaded,
        )
        db.add(invoice)
        await db.commit()
        await db.refresh(invoice)
        return {
            "id": invoice.id,
            "status": invoice.status.value,
            "original_filename": invoice.original_filename,
            "created_at": invoice.created_at.isoformat(),
        }

    @staticmethod
    async def update_invoice(db: AsyncSession, invoice_id: str, data) -> dict:
        invoice = await InvoiceService.get_invoice_model(db, invoice_id)
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(invoice, key, value)
        await db.commit()
        await db.refresh(invoice)
        return await InvoiceService.get_invoice(db, invoice_id)

    @staticmethod
    async def delete_invoice(db: AsyncSession, invoice_id: str) -> None:
        invoice = await InvoiceService.get_invoice_model(db, invoice_id)
        await db.delete(invoice)
        await db.commit()

    @staticmethod
    async def reprocess(db: AsyncSession, invoice_id: str) -> dict:
        invoice = await InvoiceService.get_invoice_model(db, invoice_id)
        invoice.status = InvoiceStatus.uploaded
        invoice.ocr_text = None
        invoice.ocr_confidence = None
        await db.commit()
        return {"id": invoice.id, "status": "uploaded", "message": "Invoice queued for reprocessing"}
