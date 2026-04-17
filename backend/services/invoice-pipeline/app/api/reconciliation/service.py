import math
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from common.models.invoice import Invoice, InvoiceStatus
from common.models.purchase_order import PurchaseOrder, POStatus
from common.models.accounting_entry import AccountingEntry, EntryType
from common.models.accounting_template import AccountingTemplate
from common.exceptions import NotFoundError, ValidationError


class ReconciliationService:
    @staticmethod
    async def list_pending(db: AsyncSession, page: int, limit: int) -> dict:
        query = select(Invoice).where(
            Invoice.status == InvoiceStatus.awaiting_match,
        )
        count_query = select(func.count(Invoice.id)).where(
            Invoice.status == InvoiceStatus.awaiting_match,
        )

        total = await db.scalar(count_query) or 0
        result = await db.execute(
            query.order_by(Invoice.approved_at.desc().nullslast())
            .offset((page - 1) * limit).limit(limit)
        )
        invoices = result.scalars().all()

        items = []
        for inv in invoices:
            extracted = {}
            if inv.extraction_result:
                extracted = inv.extraction_result.extracted_data or {}
            items.append({
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "original_filename": inv.original_filename,
                "supplier_name": extracted.get("szallito_nev"),
                "supplier_tax_id": extracted.get("szallito_adoszam"),
                "gross_amount": inv.gross_amount,
                "net_amount": inv.net_amount,
                "currency": inv.currency,
                "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
                "match_status": inv.match_status,
                "status": inv.status.value,
                "approved_at": inv.approved_at.isoformat() if inv.approved_at else None,
            })

        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": math.ceil(total / limit) if total > 0 else 1,
        }

    @staticmethod
    async def auto_match(db: AsyncSession, invoice_id: str) -> dict:
        invoice = await db.get(Invoice, invoice_id)
        if not invoice:
            raise NotFoundError("Invoice", invoice_id)
        if invoice.status not in (InvoiceStatus.awaiting_match,):
            raise ValidationError("Only awaiting_match invoices can be matched")

        extracted = {}
        if invoice.extraction_result:
            extracted = invoice.extraction_result.extracted_data or {}

        supplier_tax_id = extracted.get("szallito_adoszam")
        invoice_amount = invoice.gross_amount

        if not supplier_tax_id or not invoice_amount:
            invoice.match_status = "mismatch"
            await db.commit()
            return {"status": "mismatch", "reason": "Missing supplier tax ID or amount"}

        # Exclude POs already matched to another invoice
        matched_po_ids = select(Invoice.purchase_order_id).where(
            Invoice.purchase_order_id.isnot(None),
            Invoice.status.in_([InvoiceStatus.matched, InvoiceStatus.posted]),
        )

        # Match by partner_id first (if invoice has partner), fallback to supplier_tax_id
        from sqlalchemy import or_
        po_filters = [
            PurchaseOrder.status == POStatus.received,
            PurchaseOrder.id.notin_(matched_po_ids),
        ]
        if invoice.partner_id:
            po_filters.append(or_(
                PurchaseOrder.partner_id == invoice.partner_id,
                PurchaseOrder.supplier_tax_id == supplier_tax_id,
            ))
        else:
            po_filters.append(PurchaseOrder.supplier_tax_id == supplier_tax_id)

        result = await db.execute(select(PurchaseOrder).where(*po_filters))
        pos = result.scalars().all()

        if not pos:
            invoice.match_status = "mismatch"
            await db.commit()
            return {"status": "mismatch", "reason": "No matching PO found for supplier"}

        for po in pos:
            tolerance = po.amount * 0.03
            if abs(invoice_amount - po.amount) <= tolerance:
                invoice.purchase_order_id = po.id
                invoice.match_status = "matched"
                invoice.status = InvoiceStatus.matched
                invoice.accounting_code = po.accounting_code
                await db.commit()
                return {
                    "status": "matched",
                    "purchase_order_id": po.id,
                    "po_number": po.po_number,
                    "accounting_code": po.accounting_code,
                }

        invoice.match_status = "mismatch"
        await db.commit()
        return {"status": "mismatch", "reason": "Amount mismatch exceeds 3% tolerance"}

    @staticmethod
    async def manual_match(db: AsyncSession, invoice_id: str, po_id: str) -> dict:
        invoice = await db.get(Invoice, invoice_id)
        if not invoice:
            raise NotFoundError("Invoice", invoice_id)
        if invoice.status != InvoiceStatus.awaiting_match:
            raise ValidationError(f"Invoice status is {invoice.status.value}, expected awaiting_match")

        po = await db.get(PurchaseOrder, po_id)
        if not po:
            raise NotFoundError("Purchase order", po_id)
        if po.status != POStatus.received:
            raise ValidationError("PO must have a goods receipt before matching")

        # Check PO not already matched to another invoice
        existing = await db.execute(
            select(Invoice).where(
                Invoice.purchase_order_id == po.id,
                Invoice.status.in_([InvoiceStatus.matched, InvoiceStatus.posted]),
            )
        )
        if existing.scalar_one_or_none():
            raise ValidationError("PO already matched to another invoice")

        # Currency check
        if invoice.currency and po.currency and invoice.currency != po.currency:
            raise ValidationError(f"Currency mismatch: invoice is {invoice.currency}, PO is {po.currency}")

        invoice.purchase_order_id = po.id
        invoice.match_status = "matched"
        invoice.status = InvoiceStatus.matched
        invoice.accounting_code = po.accounting_code
        await db.commit()
        return {
            "status": "matched",
            "purchase_order_id": po.id,
            "po_number": po.po_number,
            "accounting_code": po.accounting_code,
        }

    @staticmethod
    async def _find_template(db: AsyncSession, account_code: str) -> AccountingTemplate | None:
        """Find the best matching accounting template for an account code."""
        result = await db.execute(
            select(AccountingTemplate).order_by(
                func.length(AccountingTemplate.account_code_pattern).desc()
            )
        )
        templates = result.scalars().all()

        for t in templates:
            pattern = t.account_code_pattern
            if pattern == "*":
                continue
            if pattern.endswith("*"):
                if account_code.startswith(pattern[:-1]):
                    return t
            elif pattern == account_code:
                return t

        # Fallback to wildcard
        for t in templates:
            if t.account_code_pattern == "*":
                return t
        return None

    @staticmethod
    async def post_to_accounting(db: AsyncSession, invoice_id: str, user_id: str) -> dict:
        invoice = await db.get(Invoice, invoice_id)
        if not invoice:
            raise NotFoundError("Invoice", invoice_id)
        if invoice.status != InvoiceStatus.matched:
            raise ValidationError("Only matched invoices can be posted")
        if not invoice.purchase_order_id:
            raise ValidationError("Invoice must be linked to a PO before posting")

        # Idempotency check: prevent duplicate GL entries
        existing_entries = await db.execute(
            select(AccountingEntry).where(AccountingEntry.invoice_id == invoice_id).limit(1)
        )
        if existing_entries.scalar_one_or_none():
            raise ValidationError("Invoice already posted — entries exist")

        po = await db.get(PurchaseOrder, invoice.purchase_order_id)
        if not po:
            raise NotFoundError("Purchase order", invoice.purchase_order_id)

        period = invoice.invoice_date.strftime("%Y-%m") if invoice.invoice_date else datetime.utcnow().strftime("%Y-%m")

        # Find accounting template for debit/credit pair
        template = await ReconciliationService._find_template(db, po.accounting_code)
        debit_account = template.debit_account if template else po.accounting_code
        credit_account = template.credit_account if template else "454"

        net_amount = invoice.net_amount or invoice.gross_amount or 0
        vat_amount = invoice.vat_amount or 0

        # Debit: cost account (net amount)
        debit_entry = AccountingEntry(
            invoice_id=invoice.id,
            purchase_order_id=po.id,
            account_code=debit_account,
            department_id=po.department_id,
            amount=net_amount,
            currency=invoice.currency,
            period=period,
            entry_type=EntryType.debit,
            posted_at=datetime.utcnow(),
            posted_by=user_id,
        )
        db.add(debit_entry)

        # Debit: VAT account (if VAT exists)
        if vat_amount > 0:
            vat_entry = AccountingEntry(
                invoice_id=invoice.id,
                purchase_order_id=po.id,
                account_code="466",  # ÁFA levonható
                department_id=po.department_id,
                amount=vat_amount,
                currency=invoice.currency,
                period=period,
                entry_type=EntryType.debit,
                posted_at=datetime.utcnow(),
                posted_by=user_id,
            )
            db.add(vat_entry)

        # Credit: supplier account (gross amount)
        credit_entry = AccountingEntry(
            invoice_id=invoice.id,
            purchase_order_id=po.id,
            account_code=credit_account,
            department_id=po.department_id,
            amount=invoice.gross_amount or 0,
            currency=invoice.currency,
            period=period,
            entry_type=EntryType.credit,
            posted_at=datetime.utcnow(),
            posted_by=user_id,
        )
        db.add(credit_entry)

        # Update statuses
        invoice.match_status = "posted"
        invoice.status = InvoiceStatus.posted
        po.status = POStatus.closed

        await db.commit()

        # Publish event for metrics recalculation
        try:
            from common.events import event_bus
            import asyncio
            asyncio.create_task(event_bus.publish("invoice.posted", {"invoice_id": invoice_id}))
        except Exception:
            pass

        return {
            "status": "posted",
            "debit_account": debit_account,
            "credit_account": credit_account,
            "net_amount": net_amount,
            "vat_amount": vat_amount,
            "gross_amount": invoice.gross_amount or 0,
            "period": period,
            "template": template.name if template else "default",
        }
