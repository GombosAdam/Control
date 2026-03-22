import math
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.invoice import Invoice, InvoiceStatus
from app.exceptions import NotFoundError

class ExtractionService:
    @staticmethod
    async def get_queue(db: AsyncSession, page: int, limit: int) -> dict:
        query = select(Invoice).where(Invoice.status == InvoiceStatus.pending_review)
        count_query = select(func.count(Invoice.id)).where(Invoice.status == InvoiceStatus.pending_review)

        total = await db.scalar(count_query) or 0
        result = await db.execute(
            query.order_by(Invoice.created_at.desc()).offset((page - 1) * limit).limit(limit)
        )
        invoices = result.scalars().all()

        return {
            "items": [
                {
                    "id": inv.id,
                    "invoice_number": inv.invoice_number,
                    "status": inv.status.value,
                    "original_filename": inv.original_filename,
                    "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
                    "due_date": inv.due_date.isoformat() if inv.due_date else None,
                    "payment_method": inv.payment_method,
                    "net_amount": inv.net_amount,
                    "vat_rate": inv.vat_rate,
                    "vat_amount": inv.vat_amount,
                    "gross_amount": inv.gross_amount,
                    "currency": inv.currency,
                    "ocr_text": inv.ocr_text,
                    "is_duplicate": inv.is_duplicate,
                    "created_at": inv.created_at.isoformat(),
                }
                for inv in invoices
            ],
            "total": total,
            "page": page,
            "limit": limit,
            "pages": math.ceil(total / limit) if total > 0 else 1,
        }

    @staticmethod
    async def approve(db: AsyncSession, invoice_id: str, user_id: str) -> dict:
        from datetime import datetime
        result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
        invoice = result.scalar_one_or_none()
        if not invoice:
            raise NotFoundError("Invoice", invoice_id)
        invoice.status = InvoiceStatus.pending_review
        invoice.reviewed_by_id = user_id
        await db.commit()
        return {"id": invoice.id, "status": "pending_review"}

    @staticmethod
    async def reject(db: AsyncSession, invoice_id: str, user_id: str) -> dict:
        result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
        invoice = result.scalar_one_or_none()
        if not invoice:
            raise NotFoundError("Invoice", invoice_id)
        invoice.status = InvoiceStatus.rejected
        invoice.reviewed_by_id = user_id
        await db.commit()
        return {"id": invoice.id, "status": "rejected"}

    @staticmethod
    async def get_duplicates(db: AsyncSession) -> list:
        result = await db.execute(
            select(Invoice).where(Invoice.is_duplicate == True).order_by(Invoice.created_at.desc())
        )
        invoices = result.scalars().all()
        return [
            {
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "original_filename": inv.original_filename,
                "duplicate_of_id": inv.duplicate_of_id,
                "similarity_score": inv.similarity_score,
                "created_at": inv.created_at.isoformat(),
            }
            for inv in invoices
        ]
