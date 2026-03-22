import json
import logging
import math
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from common.config import settings
from common.models.invoice import Invoice, InvoiceStatus
from common.models.extraction import ExtractionResult
from common.exceptions import NotFoundError

logger = logging.getLogger(__name__)

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

        # Check for extraction corrections before approving
        try:
            ext_result = await db.execute(
                select(ExtractionResult).where(ExtractionResult.invoice_id == invoice_id)
            )
            extraction = ext_result.scalar_one_or_none()
            if extraction and extraction.extracted_data:
                corrections = _detect_corrections(invoice, extraction.extracted_data)
                if corrections:
                    # Publish extraction.corrected event for template learning
                    import redis.asyncio as aioredis
                    r = aioredis.from_url(settings.REDIS_URL)
                    await r.publish(
                        "events:extraction.corrected",
                        json.dumps({
                            "event": "extraction.corrected",
                            "payload": {
                                "invoice_id": invoice_id,
                                "corrections": corrections,
                            },
                        }),
                    )
                    await r.close()
                    logger.info("Extraction corrections detected for %s: %s", invoice_id, list(corrections.keys()))
        except Exception as e:
            logger.warning("Correction detection failed for %s: %s", invoice_id, e)

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


def _detect_corrections(invoice: Invoice, extracted_data: dict) -> dict:
    """Compare current invoice fields with original OCR extraction to detect user corrections."""
    corrections = {}

    field_map = {
        "szamla_szam": invoice.invoice_number,
        "netto_osszeg": invoice.net_amount,
        "afa_osszeg": invoice.vat_amount,
        "brutto_osszeg": invoice.gross_amount,
        "szamla_kelte": str(invoice.invoice_date) if invoice.invoice_date else None,
        "fizetesi_hatarido": str(invoice.due_date) if invoice.due_date else None,
        "teljesites_datuma": str(invoice.fulfillment_date) if invoice.fulfillment_date else None,
    }

    for ocr_key, current_value in field_map.items():
        ocr_value = extracted_data.get(ocr_key)
        if ocr_value is None or current_value is None:
            continue

        # Normalize for comparison
        ocr_str = str(ocr_value).strip()
        current_str = str(current_value).strip()

        # For numeric fields, compare as floats
        if ocr_key in ("netto_osszeg", "afa_osszeg", "brutto_osszeg"):
            try:
                ocr_float = float(str(ocr_value).replace(",", "").replace(" ", ""))
                current_float = float(current_value)
                if abs(ocr_float - current_float) > 0.01:
                    corrections[ocr_key] = {"original": ocr_value, "corrected": current_value}
            except (ValueError, TypeError):
                pass
        elif ocr_str != current_str:
            corrections[ocr_key] = {"original": ocr_value, "corrected": current_value}

    return corrections
