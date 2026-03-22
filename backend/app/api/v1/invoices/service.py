import math
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.invoice import Invoice, InvoiceStatus
from app.models.invoice_approval import InvoiceApproval
from app.models.audit import AuditLog
from app.exceptions import NotFoundError, ValidationError, AuthorizationError

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

    @staticmethod
    async def submit_for_approval(db: AsyncSession, invoice_id: str, user_id: str) -> dict:
        """Move invoice from pending_review to approval workflow."""
        invoice = await InvoiceService.get_invoice_model(db, invoice_id)
        if invoice.status != InvoiceStatus.pending_review:
            raise ValidationError(f"Cannot submit: status is {invoice.status.value}, expected pending_review")

        # Check for duplicate approval chain
        existing = await db.execute(
            select(InvoiceApproval).where(InvoiceApproval.invoice_id == invoice_id).limit(1)
        )
        if existing.scalar_one_or_none():
            raise ValidationError("Approval chain already exists for this invoice")

        # Create 3-step approval chain
        steps = [
            (1, "Ellenőrzés", "reviewer"),
            (2, "Jóváhagyás", "department_head"),
            (3, "Pénzügyi jóváhagyás", "cfo"),
        ]
        for step_num, name, role in steps:
            approval = InvoiceApproval(
                invoice_id=invoice_id,
                step=step_num,
                step_name=name,
                status="pending" if step_num == 1 else "waiting",
                assigned_role=role,
            )
            db.add(approval)

        # Update invoice status to in_approval
        invoice.status = InvoiceStatus.in_approval

        # Audit
        log = AuditLog(user_id=user_id, action="invoice.submit_approval", entity_type="invoice", entity_id=invoice_id, details={"steps": 3})
        db.add(log)
        await db.commit()
        return {"invoice_id": invoice_id, "steps_created": 3}

    @staticmethod
    async def get_approval_status(db: AsyncSession, invoice_id: str) -> list[dict]:
        result = await db.execute(
            select(InvoiceApproval).where(
                InvoiceApproval.invoice_id == invoice_id
            ).order_by(InvoiceApproval.step)
        )
        approvals = result.scalars().all()
        return [{
            "id": a.id,
            "step": a.step,
            "step_name": a.step_name,
            "status": a.status,
            "assigned_role": a.assigned_role,
            "decided_by": a.decided_by,
            "decider_name": a.decider.full_name if a.decider else None,
            "decided_at": a.decided_at.isoformat() if a.decided_at else None,
            "comment": a.comment,
            "created_at": a.created_at.isoformat(),
        } for a in approvals]

    @staticmethod
    async def decide_approval(db: AsyncSession, invoice_id: str, step: int,
                              decision: str, comment: str | None, user_id: str,
                              user_role: str = "") -> dict:
        """Approve or reject a specific step."""
        if decision not in ("approved", "rejected"):
            raise ValidationError("Decision must be 'approved' or 'rejected'")

        result = await db.execute(
            select(InvoiceApproval).where(
                InvoiceApproval.invoice_id == invoice_id,
                InvoiceApproval.step == step,
            )
        )
        approval = result.scalar_one_or_none()
        if not approval:
            raise NotFoundError("Approval step", f"{invoice_id}/step-{step}")
        if approval.status not in ("pending",):
            raise ValidationError(f"Step {step} is {approval.status}, cannot decide")

        # Role authorization check
        if user_role != approval.assigned_role and user_role != "admin":
            raise AuthorizationError(f"Role '{user_role}' cannot decide step assigned to '{approval.assigned_role}'")

        approval.status = decision
        approval.decided_by = user_id
        approval.decided_at = datetime.utcnow()
        approval.comment = comment

        # Audit
        log = AuditLog(user_id=user_id, action=f"invoice.approval.{decision}", entity_type="invoice",
                       entity_id=invoice_id, details={"step": step, "decision": decision, "comment": comment})
        db.add(log)

        if decision == "rejected":
            # Reject: set invoice to rejected, clear PO link, mark remaining steps as cancelled
            invoice = await InvoiceService.get_invoice_model(db, invoice_id)
            invoice.status = InvoiceStatus.rejected
            # Clear PO link to free up budget commitment
            invoice.purchase_order_id = None
            invoice.match_status = "unmatched"
            invoice.accounting_code = None
            remaining = await db.execute(
                select(InvoiceApproval).where(
                    InvoiceApproval.invoice_id == invoice_id,
                    InvoiceApproval.step > step,
                )
            )
            for rem in remaining.scalars().all():
                rem.status = "cancelled"
        else:
            # Approved: activate next step or finalize
            next_result = await db.execute(
                select(InvoiceApproval).where(
                    InvoiceApproval.invoice_id == invoice_id,
                    InvoiceApproval.step == step + 1,
                )
            )
            next_step = next_result.scalar_one_or_none()
            if next_step:
                next_step.status = "pending"
            else:
                # All steps done - move to awaiting_match (requires PO reconciliation)
                invoice = await InvoiceService.get_invoice_model(db, invoice_id)
                invoice.status = InvoiceStatus.awaiting_match
                invoice.reviewed_by_id = user_id
                invoice.approved_at = datetime.utcnow()

        await db.commit()
        return {"invoice_id": invoice_id, "step": step, "decision": decision}

    @staticmethod
    async def get_pending_approvals(db: AsyncSession, role: str | None = None) -> list[dict]:
        """Get all invoices with pending approval steps, optionally filtered by role."""
        query = select(InvoiceApproval).where(InvoiceApproval.status == "pending")
        if role:
            query = query.where(InvoiceApproval.assigned_role == role)
        query = query.order_by(InvoiceApproval.created_at)

        result = await db.execute(query)
        approvals = result.scalars().all()

        items = []
        seen_invoices = set()
        for a in approvals:
            if a.invoice_id in seen_invoices:
                continue
            seen_invoices.add(a.invoice_id)
            invoice = await db.get(Invoice, a.invoice_id)
            items.append({
                "invoice_id": a.invoice_id,
                "invoice_number": invoice.invoice_number if invoice else None,
                "original_filename": invoice.original_filename if invoice else None,
                "gross_amount": invoice.gross_amount if invoice else None,
                "currency": invoice.currency if invoice else "HUF",
                "step": a.step,
                "step_name": a.step_name,
                "assigned_role": a.assigned_role,
                "created_at": a.created_at.isoformat(),
            })
        return items
