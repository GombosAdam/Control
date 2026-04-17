"""Feature flag bridge: routes approval calls to legacy code or new workflow engine."""

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.config import settings
from common.models.workflow_instance import WorkflowInstance, WorkflowStatus
from common.models.workflow_task import WorkflowTask, TaskStatus
from common.models.purchase_order import PurchaseOrder, POStatus
from common.models.invoice import Invoice, InvoiceStatus
from common.workflow.engine import WorkflowEngine

logger = logging.getLogger(__name__)


class WorkflowBridge:
    """Routes approval operations to legacy or workflow engine based on feature flag."""

    @staticmethod
    def _is_engine_enabled() -> bool:
        return settings.WORKFLOW_ENGINE_ENABLED

    # ── Purchase Order ──

    @staticmethod
    async def start_po_approval(db: AsyncSession, po: PurchaseOrder, user_id: str) -> None:
        """Start PO approval: engine or legacy."""
        if not WorkflowBridge._is_engine_enabled():
            from app.api.purchase_orders.service import PurchaseOrderService
            await PurchaseOrderService._legacy_create_approval_chain(db, po, user_id)
            return

        engine = WorkflowEngine(db)
        context = {
            "purchase_order_id": po.id,
            "amount": float(po.amount),
            "department_id": po.department_id,
            "created_by": user_id,
            "currency": po.currency,
        }
        await engine.start_workflow(
            workflow_code="po_approval",
            entity_type="purchase_order",
            entity_id=po.id,
            context=context,
            initiated_by=user_id,
        )

    @staticmethod
    async def decide_po_step(
        db: AsyncSession,
        po_id: str,
        step: int,
        decision: str,
        comment: str | None,
        user_id: str,
        user_role: str,
    ) -> dict:
        """Decide a PO approval step: engine or legacy."""
        if not WorkflowBridge._is_engine_enabled():
            from app.api.purchase_orders.service import PurchaseOrderService
            return await PurchaseOrderService._legacy_decide_po_approval(
                db, po_id, step, decision, comment, user_id, user_role
            )

        # Find the matching workflow task
        instance = await WorkflowBridge._get_instance(db, "purchase_order", po_id)
        if not instance:
            raise ValueError(f"No active workflow instance for PO {po_id}")

        task = await WorkflowBridge._get_task_by_step(db, instance.id, step)
        if not task:
            raise ValueError(f"No task found for step {step} in workflow instance {instance.id}")

        engine = WorkflowEngine(db)
        result = await engine.process_decision(task.id, decision, comment, user_id, user_role)

        # Sync entity status
        po = await db.get(PurchaseOrder, po_id)
        await db.refresh(instance)
        if instance.status == WorkflowStatus.completed:
            po.status = POStatus.approved
            po.approved_by = user_id
        elif instance.status == WorkflowStatus.rejected:
            po.status = POStatus.cancelled

        return {"purchase_order_id": po_id, "step": step, "decision": decision}

    # ── Invoice ──

    @staticmethod
    async def start_invoice_approval(db: AsyncSession, invoice: Invoice, user_id: str) -> dict:
        """Start invoice approval: engine or legacy."""
        if not WorkflowBridge._is_engine_enabled():
            from app.api.invoices.service import InvoiceService
            return await InvoiceService._legacy_submit_for_approval(db, invoice.id, user_id)

        engine = WorkflowEngine(db)
        context = {
            "invoice_id": invoice.id,
            "gross_amount": float(invoice.gross_amount) if invoice.gross_amount else 0,
            "net_amount": float(invoice.net_amount) if invoice.net_amount else 0,
            "nav_verified": getattr(invoice, "nav_verified", False),
            "created_by": user_id,
            "currency": invoice.currency or "HUF",
        }
        instance = await engine.start_workflow(
            workflow_code="invoice_approval",
            entity_type="invoice",
            entity_id=invoice.id,
            context=context,
            initiated_by=user_id,
        )

        # Update invoice status
        invoice.status = InvoiceStatus.in_approval

        return {"invoice_id": invoice.id, "instance_id": instance.id}

    @staticmethod
    async def decide_invoice_step(
        db: AsyncSession,
        invoice_id: str,
        step: int,
        decision: str,
        comment: str | None,
        user_id: str,
        user_role: str,
    ) -> dict:
        """Decide an invoice approval step: engine or legacy."""
        if not WorkflowBridge._is_engine_enabled():
            from app.api.invoices.service import InvoiceService
            return await InvoiceService._legacy_decide_approval(
                db, invoice_id, step, decision, comment, user_id, user_role
            )

        instance = await WorkflowBridge._get_instance(db, "invoice", invoice_id)
        if not instance:
            raise ValueError(f"No active workflow instance for invoice {invoice_id}")

        task = await WorkflowBridge._get_task_by_step(db, instance.id, step)
        if not task:
            raise ValueError(f"No task found for step {step}")

        engine = WorkflowEngine(db)
        result = await engine.process_decision(task.id, decision, comment, user_id, user_role)

        # Sync entity status
        invoice = await db.get(Invoice, invoice_id)
        await db.refresh(instance)
        if instance.status == WorkflowStatus.completed:
            invoice.status = InvoiceStatus.awaiting_match
            invoice.reviewed_by_id = user_id
            invoice.approved_at = datetime.utcnow()

            # Auto-match: try to find a matching PO immediately
            await WorkflowBridge._try_auto_match(db, invoice)

        elif instance.status == WorkflowStatus.rejected:
            invoice.status = InvoiceStatus.rejected
            invoice.purchase_order_id = None
            invoice.match_status = "unmatched"
            invoice.accounting_code = None

        return {"invoice_id": invoice_id, "step": step, "decision": decision}

    # ── Helpers ──

    @staticmethod
    async def _get_instance(db: AsyncSession, entity_type: str, entity_id: str) -> WorkflowInstance | None:
        result = await db.execute(
            select(WorkflowInstance).where(
                WorkflowInstance.entity_type == entity_type,
                WorkflowInstance.entity_id == entity_id,
                WorkflowInstance.status == WorkflowStatus.active,
            ).order_by(WorkflowInstance.created_at.desc())
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def _get_task_by_step(db: AsyncSession, instance_id: str, step: int) -> WorkflowTask | None:
        result = await db.execute(
            select(WorkflowTask).where(
                WorkflowTask.instance_id == instance_id,
                WorkflowTask.step_order == step,
                WorkflowTask.status == TaskStatus.pending,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def _try_auto_match(db: AsyncSession, invoice: Invoice) -> None:
        """Try to auto-match an invoice to a PO after approval completes."""
        from common.models.purchase_order import PurchaseOrder, POStatus
        from sqlalchemy import or_

        extracted = {}
        if invoice.extraction_result:
            extracted = invoice.extraction_result.extracted_data or {}

        supplier_tax_id = extracted.get("szallito_adoszam")
        invoice_amount = invoice.gross_amount

        if not supplier_tax_id or not invoice_amount:
            invoice.match_status = "unmatched"
            return

        # Exclude POs already matched
        matched_po_ids = select(Invoice.id).where(
            Invoice.purchase_order_id.isnot(None),
            Invoice.status.in_([InvoiceStatus.matched, InvoiceStatus.posted]),
        )

        po_filters = [
            PurchaseOrder.status.in_([POStatus.sent, POStatus.received]),
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

        for po in pos:
            tolerance = float(po.amount) * 0.03
            if abs(float(invoice_amount) - float(po.amount)) <= tolerance:
                invoice.purchase_order_id = po.id
                invoice.match_status = "matched"
                invoice.status = InvoiceStatus.matched
                invoice.accounting_code = po.accounting_code
                logger.info("Auto-matched invoice %s to PO %s", invoice.id, po.po_number)
                return

        invoice.match_status = "unmatched"
        logger.info("No auto-match found for invoice %s (tax_id=%s, amount=%s)", invoice.id, supplier_tax_id, invoice_amount)
