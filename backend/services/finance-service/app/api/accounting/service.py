import math
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from common.models.invoice import Invoice, InvoiceStatus
from common.models.extraction import ExtractionResult
from common.models.accounting_entry import AccountingEntry
from common.models.accounting_template import AccountingTemplate
from common.exceptions import NotFoundError


class AccountingService:
    @staticmethod
    async def list_approved(db: AsyncSession, page: int, limit: int, search: str | None, currency: str | None) -> dict:
        from common.models.purchase_order import PurchaseOrder
        reconciled_statuses = [InvoiceStatus.matched, InvoiceStatus.posted]
        query = select(Invoice).where(Invoice.status.in_(reconciled_statuses))
        count_query = select(func.count(Invoice.id)).where(Invoice.status.in_(reconciled_statuses))

        if currency:
            query = query.where(Invoice.currency == currency)
            count_query = count_query.where(Invoice.currency == currency)

        if search:
            sf = or_(
                Invoice.original_filename.ilike(f"%{search}%"),
                Invoice.invoice_number.ilike(f"%{search}%"),
            )
            query = query.where(sf)
            count_query = count_query.where(sf)

        total = await db.scalar(count_query) or 0
        result = await db.execute(
            query.order_by(Invoice.approved_at.desc().nullslast(), Invoice.created_at.desc())
            .offset((page - 1) * limit).limit(limit)
        )
        invoices = result.scalars().all()

        items = []
        for inv in invoices:
            # Get extracted data from extraction_result
            extracted = {}
            if inv.extraction_result:
                extracted = inv.extraction_result.extracted_data or {}

            # Get PO number
            po_number = None
            if inv.purchase_order_id:
                po = await db.get(PurchaseOrder, inv.purchase_order_id)
                po_number = po.po_number if po else None

            items.append({
                "id": inv.id,
                "original_filename": inv.original_filename,
                "invoice_number": inv.invoice_number,
                "po_number": po_number,
                "status": inv.status.value,
                "match_status": inv.match_status,
                "szallito_nev": extracted.get("szallito_nev"),
                "szallito_adoszam": extracted.get("szallito_adoszam"),
                "szallito_bankszamlaszam": extracted.get("szallito_bankszamlaszam"),
                "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else extracted.get("szamla_kelte"),
                "fulfillment_date": inv.fulfillment_date.isoformat() if inv.fulfillment_date else extracted.get("teljesites_datuma"),
                "due_date": inv.due_date.isoformat() if inv.due_date else extracted.get("fizetesi_hatarido"),
                "payment_method": inv.payment_method or extracted.get("fizetesi_mod"),
                "net_amount": inv.net_amount,
                "vat_rate": inv.vat_rate,
                "vat_amount": inv.vat_amount,
                "gross_amount": inv.gross_amount,
                "currency": inv.currency,
                "approved_at": inv.approved_at.isoformat() if inv.approved_at else None,
                "created_at": inv.created_at.isoformat(),
            })

        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": math.ceil(total / limit) if total > 0 else 1,
        }

    @staticmethod
    async def get_summary(db: AsyncSession) -> dict:
        approved_count = await db.scalar(
            select(func.count(Invoice.id)).where(Invoice.status.in_([InvoiceStatus.matched, InvoiceStatus.posted]))
        ) or 0
        total_net = await db.scalar(
            select(func.coalesce(func.sum(Invoice.net_amount), 0)).where(Invoice.status.in_([InvoiceStatus.matched, InvoiceStatus.posted]))
        )
        total_vat = await db.scalar(
            select(func.coalesce(func.sum(Invoice.vat_amount), 0)).where(Invoice.status.in_([InvoiceStatus.matched, InvoiceStatus.posted]))
        )
        total_gross = await db.scalar(
            select(func.coalesce(func.sum(Invoice.gross_amount), 0)).where(Invoice.status.in_([InvoiceStatus.matched, InvoiceStatus.posted]))
        )

        # By currency
        result = await db.execute(
            select(Invoice.currency, func.count(Invoice.id), func.coalesce(func.sum(Invoice.gross_amount), 0))
            .where(Invoice.status.in_([InvoiceStatus.matched, InvoiceStatus.posted]))
            .group_by(Invoice.currency)
        )
        by_currency = [
            {"currency": row[0], "count": row[1], "total_gross": float(row[2])}
            for row in result.all()
        ]

        return {
            "approved_count": approved_count,
            "total_net": float(total_net or 0),
            "total_vat": float(total_vat or 0),
            "total_gross": float(total_gross or 0),
            "by_currency": by_currency,
        }

    @staticmethod
    async def list_entries(db: AsyncSession, period: str | None, department_id: str | None,
                           account_code: str | None, page: int, limit: int,
                           invoice_id: str | None = None) -> dict:
        query = select(AccountingEntry)
        count_query = select(func.count(AccountingEntry.id))

        if invoice_id:
            query = query.where(AccountingEntry.invoice_id == invoice_id)
            count_query = count_query.where(AccountingEntry.invoice_id == invoice_id)
        if period:
            query = query.where(AccountingEntry.period == period)
            count_query = count_query.where(AccountingEntry.period == period)
        if department_id:
            query = query.where(AccountingEntry.department_id == department_id)
            count_query = count_query.where(AccountingEntry.department_id == department_id)
        if account_code:
            query = query.where(AccountingEntry.account_code == account_code)
            count_query = count_query.where(AccountingEntry.account_code == account_code)

        total = await db.scalar(count_query) or 0
        result = await db.execute(
            query.order_by(AccountingEntry.posted_at.desc())
            .offset((page - 1) * limit).limit(limit)
        )
        entries = result.scalars().all()

        items = []
        for e in entries:
            items.append({
                "id": e.id,
                "invoice_id": e.invoice_id,
                "purchase_order_id": e.purchase_order_id,
                "po_number": e.purchase_order.po_number if e.purchase_order else None,
                "account_code": e.account_code,
                "department_id": e.department_id,
                "department_name": e.department.name if e.department else None,
                "amount": e.amount,
                "currency": e.currency,
                "period": e.period,
                "entry_type": e.entry_type.value,
                "posted_at": e.posted_at.isoformat(),
                "posted_by": e.poster.full_name if e.poster else None,
            })

        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": math.ceil(total / limit) if total > 0 else 1,
        }

    # --- Accounting Templates (könyvelési tükör) ---

    @staticmethod
    async def list_templates(db: AsyncSession) -> list[dict]:
        result = await db.execute(
            select(AccountingTemplate).order_by(AccountingTemplate.account_code_pattern)
        )
        return [{
            "id": t.id,
            "account_code_pattern": t.account_code_pattern,
            "name": t.name,
            "debit_account": t.debit_account,
            "credit_account": t.credit_account,
            "description": t.description,
            "created_at": t.created_at.isoformat(),
        } for t in result.scalars().all()]

    @staticmethod
    async def create_template(db: AsyncSession, data: dict) -> dict:
        template = AccountingTemplate(**data)
        db.add(template)
        await db.commit()
        await db.refresh(template)
        return {
            "id": template.id,
            "account_code_pattern": template.account_code_pattern,
            "name": template.name,
            "debit_account": template.debit_account,
            "credit_account": template.credit_account,
            "description": template.description,
            "created_at": template.created_at.isoformat(),
        }

    @staticmethod
    async def update_template(db: AsyncSession, template_id: str, data: dict) -> dict:
        template = await db.get(AccountingTemplate, template_id)
        if not template:
            raise NotFoundError("Accounting template", template_id)
        for key, value in data.items():
            if value is not None:
                setattr(template, key, value)
        await db.commit()
        await db.refresh(template)
        return {
            "id": template.id,
            "account_code_pattern": template.account_code_pattern,
            "name": template.name,
            "debit_account": template.debit_account,
            "credit_account": template.credit_account,
            "description": template.description,
            "created_at": template.created_at.isoformat(),
        }

    @staticmethod
    async def delete_template(db: AsyncSession, template_id: str) -> dict:
        template = await db.get(AccountingTemplate, template_id)
        if not template:
            raise NotFoundError("Accounting template", template_id)
        await db.delete(template)
        await db.commit()
        return {"message": "Template deleted"}
