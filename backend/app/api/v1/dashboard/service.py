from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.invoice import Invoice, InvoiceStatus

class DashboardService:
    @staticmethod
    async def get_stats(db: AsyncSession) -> dict:
        total = await db.scalar(select(func.count(Invoice.id)))
        approved = await db.scalar(select(func.count(Invoice.id)).where(Invoice.status == InvoiceStatus.approved))
        pending = await db.scalar(select(func.count(Invoice.id)).where(Invoice.status == InvoiceStatus.pending_review))
        error = await db.scalar(select(func.count(Invoice.id)).where(Invoice.status == InvoiceStatus.error))
        total_amount = await db.scalar(select(func.coalesce(func.sum(Invoice.gross_amount), 0)).where(Invoice.status == InvoiceStatus.approved))

        return {
            "total_invoices": total or 0,
            "approved": approved or 0,
            "pending_review": pending or 0,
            "errors": error or 0,
            "total_amount": float(total_amount or 0),
        }

    @staticmethod
    async def get_recent_invoices(db: AsyncSession, limit: int = 10) -> list:
        result = await db.execute(
            select(Invoice).order_by(Invoice.created_at.desc()).limit(limit)
        )
        invoices = result.scalars().all()
        return [
            {
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "status": inv.status.value,
                "gross_amount": inv.gross_amount,
                "currency": inv.currency,
                "original_filename": inv.original_filename,
                "created_at": inv.created_at.isoformat(),
            }
            for inv in invoices
        ]

    @staticmethod
    async def get_processing_status(db: AsyncSession) -> dict:
        statuses = {}
        for status in InvoiceStatus:
            count = await db.scalar(select(func.count(Invoice.id)).where(Invoice.status == status))
            statuses[status.value] = count or 0
        return statuses
