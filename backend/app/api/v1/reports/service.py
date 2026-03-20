from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, extract
from app.models.invoice import Invoice, InvoiceStatus
from app.models.partner import Partner

class ReportService:
    @staticmethod
    async def monthly_report(db: AsyncSession, year: int | None, month: int | None) -> dict:
        now = datetime.utcnow()
        year = year or now.year
        month = month or now.month

        query = select(Invoice).where(
            Invoice.status == InvoiceStatus.approved,
            extract("year", Invoice.invoice_date) == year,
            extract("month", Invoice.invoice_date) == month,
        )
        result = await db.execute(query)
        invoices = result.scalars().all()

        total_net = sum(inv.net_amount or 0 for inv in invoices)
        total_vat = sum(inv.vat_amount or 0 for inv in invoices)
        total_gross = sum(inv.gross_amount or 0 for inv in invoices)

        return {
            "year": year, "month": month,
            "invoice_count": len(invoices),
            "total_net": total_net, "total_vat": total_vat, "total_gross": total_gross,
        }

    @staticmethod
    async def vat_report(db: AsyncSession, year: int | None) -> dict:
        year = year or datetime.utcnow().year
        query = select(Invoice).where(
            Invoice.status == InvoiceStatus.approved,
            extract("year", Invoice.invoice_date) == year,
        )
        result = await db.execute(query)
        invoices = result.scalars().all()

        by_rate: dict[float, dict] = {}
        for inv in invoices:
            rate = inv.vat_rate or 0
            if rate not in by_rate:
                by_rate[rate] = {"rate": rate, "count": 0, "net": 0, "vat": 0, "gross": 0}
            by_rate[rate]["count"] += 1
            by_rate[rate]["net"] += inv.net_amount or 0
            by_rate[rate]["vat"] += inv.vat_amount or 0
            by_rate[rate]["gross"] += inv.gross_amount or 0

        return {"year": year, "by_vat_rate": list(by_rate.values())}

    @staticmethod
    async def supplier_report(db: AsyncSession) -> list:
        result = await db.execute(
            select(Partner).where(Partner.invoice_count > 0).order_by(Partner.total_amount.desc()).limit(20)
        )
        return [
            {
                "id": p.id, "name": p.name, "tax_number": p.tax_number,
                "invoice_count": p.invoice_count, "total_amount": p.total_amount,
            }
            for p in result.scalars().all()
        ]
