import math
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.purchase_order import PurchaseOrder, POStatus
from app.models.purchase_order_approval import PurchaseOrderApproval
from app.models.budget_line import BudgetLine, BudgetStatus
from app.models.accounting_entry import AccountingEntry
from app.models.audit import AuditLog
from app.exceptions import NotFoundError, ValidationError, DuplicateError, AuthorizationError

PO_APPROVAL_THRESHOLD = 500_000  # HUF - above this, CFO approval required


class PurchaseOrderService:
    @staticmethod
    async def list_orders(db: AsyncSession, department_id: str | None, status: str | None,
                          page: int, limit: int) -> dict:
        query = select(PurchaseOrder)
        count_query = select(func.count(PurchaseOrder.id))

        if department_id:
            query = query.where(PurchaseOrder.department_id == department_id)
            count_query = count_query.where(PurchaseOrder.department_id == department_id)
        if status:
            query = query.where(PurchaseOrder.status == POStatus(status))
            count_query = count_query.where(PurchaseOrder.status == POStatus(status))

        total = await db.scalar(count_query) or 0
        result = await db.execute(
            query.order_by(PurchaseOrder.created_at.desc())
            .offset((page - 1) * limit).limit(limit)
        )
        orders = result.scalars().all()

        return {
            "items": [PurchaseOrderService._to_dict(o) for o in orders],
            "total": total,
            "page": page,
            "limit": limit,
            "pages": math.ceil(total / limit) if total > 0 else 1,
        }

    @staticmethod
    async def _generate_po_number(db: AsyncSession) -> str:
        """Generate next PO number: PO-YYYY-NNN"""
        from datetime import datetime
        year = datetime.utcnow().year
        prefix = f"PO-{year}-"
        result = await db.scalar(
            select(func.count(PurchaseOrder.id)).where(
                PurchaseOrder.po_number.like(f"{prefix}%")
            )
        )
        next_num = (result or 0) + 1
        return f"{prefix}{next_num:03d}"

    @staticmethod
    async def create(db: AsyncSession, data: dict, user_id: str) -> dict:
        # Auto-generate PO number if not provided
        if not data.get("po_number"):
            data["po_number"] = await PurchaseOrderService._generate_po_number(db)

        # Check PO number uniqueness
        existing = await db.execute(
            select(PurchaseOrder).where(PurchaseOrder.po_number == data["po_number"])
        )
        if existing.scalar_one_or_none():
            raise DuplicateError(f"PO number '{data['po_number']}' already exists")

        # Budget check
        budget_line = await db.get(BudgetLine, data["budget_line_id"])
        if not budget_line:
            raise NotFoundError("Budget line not found")
        if budget_line.status not in (BudgetStatus.approved, BudgetStatus.locked):
            raise ValidationError("PO can only be created against approved or locked budget lines")

        # Calculate available budget
        committed = await db.scalar(
            select(func.coalesce(func.sum(PurchaseOrder.amount), 0)).where(
                PurchaseOrder.budget_line_id == budget_line.id,
                PurchaseOrder.status.in_([POStatus.draft, POStatus.approved, POStatus.received, POStatus.closed]),
            )
        ) or 0
        from app.models.accounting_entry import EntryType
        actual = await db.scalar(
            select(func.coalesce(func.sum(AccountingEntry.amount), 0)).where(
                AccountingEntry.department_id == budget_line.department_id,
                AccountingEntry.account_code == budget_line.account_code,
                AccountingEntry.period == budget_line.period,
                AccountingEntry.entry_type == EntryType.debit,
            )
        ) or 0
        available = budget_line.planned_amount - float(committed) - float(actual)

        if data["amount"] > available:
            raise ValidationError(
                f"Insufficient budget. Available: {available:.0f} {budget_line.currency}, "
                f"Requested: {data['amount']:.0f} {data.get('currency', 'HUF')}"
            )

        po = PurchaseOrder(**data, created_by=user_id)
        db.add(po)
        await db.flush()

        # Auto-submit for approval
        await PurchaseOrderService._create_approval_chain(db, po, user_id)

        await db.commit()
        await db.refresh(po)
        return PurchaseOrderService._to_dict(po)

    @staticmethod
    async def _create_approval_chain(db: AsyncSession, po: PurchaseOrder, user_id: str) -> None:
        """Create 1 or 2-step approval chain based on PO amount."""
        # Check for existing chain
        existing = await db.execute(
            select(PurchaseOrderApproval).where(
                PurchaseOrderApproval.purchase_order_id == po.id
            ).limit(1)
        )
        if existing.scalar_one_or_none():
            return

        steps = [(1, "Területi jóváhagyás", "department_head")]
        if po.amount >= PO_APPROVAL_THRESHOLD:
            steps.append((2, "CFO jóváhagyás", "cfo"))

        for step_num, name, role in steps:
            approval = PurchaseOrderApproval(
                purchase_order_id=po.id,
                step=step_num,
                step_name=name,
                status="pending" if step_num == 1 else "waiting",
                assigned_role=role,
            )
            db.add(approval)

        log = AuditLog(
            user_id=user_id, action="po.submit_approval",
            entity_type="purchase_order", entity_id=po.id,
            details={"steps": len(steps), "amount": po.amount},
        )
        db.add(log)

    @staticmethod
    async def get_approval_status(db: AsyncSession, po_id: str) -> list[dict]:
        result = await db.execute(
            select(PurchaseOrderApproval).where(
                PurchaseOrderApproval.purchase_order_id == po_id
            ).order_by(PurchaseOrderApproval.step)
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
    async def decide_po_approval(db: AsyncSession, po_id: str, step: int,
                                  decision: str, comment: str | None,
                                  user_id: str, user_role: str) -> dict:
        if decision not in ("approved", "rejected"):
            raise ValidationError("Decision must be 'approved' or 'rejected'")

        result = await db.execute(
            select(PurchaseOrderApproval).where(
                PurchaseOrderApproval.purchase_order_id == po_id,
                PurchaseOrderApproval.step == step,
            )
        )
        approval = result.scalar_one_or_none()
        if not approval:
            raise NotFoundError("Approval step", f"{po_id}/step-{step}")
        if approval.status != "pending":
            raise ValidationError(f"Step {step} is {approval.status}, cannot decide")

        if user_role != approval.assigned_role and user_role != "admin":
            raise AuthorizationError(
                f"Role '{user_role}' cannot decide step assigned to '{approval.assigned_role}'"
            )

        approval.status = decision
        approval.decided_by = user_id
        approval.decided_at = datetime.utcnow()
        approval.comment = comment

        log = AuditLog(
            user_id=user_id, action=f"po.approval.{decision}",
            entity_type="purchase_order", entity_id=po_id,
            details={"step": step, "decision": decision, "comment": comment},
        )
        db.add(log)

        po = await db.get(PurchaseOrder, po_id)

        if decision == "rejected":
            po.status = POStatus.cancelled
            remaining = await db.execute(
                select(PurchaseOrderApproval).where(
                    PurchaseOrderApproval.purchase_order_id == po_id,
                    PurchaseOrderApproval.step > step,
                )
            )
            for rem in remaining.scalars().all():
                rem.status = "cancelled"
        else:
            next_result = await db.execute(
                select(PurchaseOrderApproval).where(
                    PurchaseOrderApproval.purchase_order_id == po_id,
                    PurchaseOrderApproval.step == step + 1,
                )
            )
            next_step = next_result.scalar_one_or_none()
            if next_step:
                next_step.status = "pending"
            else:
                po.status = POStatus.approved
                po.approved_by = user_id

        await db.commit()
        return {"purchase_order_id": po_id, "step": step, "decision": decision}

    @staticmethod
    async def update(db: AsyncSession, po_id: str, data: dict) -> dict:
        po = await db.get(PurchaseOrder, po_id)
        if not po:
            raise NotFoundError("Purchase order not found")
        if po.status not in (POStatus.draft,):
            raise ValidationError("Only draft POs can be edited")
        for key, value in data.items():
            if value is not None:
                setattr(po, key, value)
        await db.commit()
        await db.refresh(po)
        return PurchaseOrderService._to_dict(po)

    @staticmethod
    async def approve(db: AsyncSession, po_id: str, user_id: str) -> dict:
        """Legacy single-step approve — kept for backward compatibility."""
        po = await db.get(PurchaseOrder, po_id)
        if not po:
            raise NotFoundError("Purchase order not found")
        if po.status != POStatus.draft:
            raise ValidationError("Only draft POs can be approved")
        po.status = POStatus.approved
        po.approved_by = user_id
        await db.commit()
        await db.refresh(po)
        return PurchaseOrderService._to_dict(po)

    @staticmethod
    async def receive(db: AsyncSession, po_id: str) -> dict:
        po = await db.get(PurchaseOrder, po_id)
        if not po:
            raise NotFoundError("Purchase order not found")
        if po.status != POStatus.approved:
            raise ValidationError("Only approved POs can be received")
        po.status = POStatus.received
        await db.commit()
        await db.refresh(po)
        return PurchaseOrderService._to_dict(po)

    @staticmethod
    async def delete(db: AsyncSession, po_id: str) -> dict:
        po = await db.get(PurchaseOrder, po_id)
        if not po:
            raise NotFoundError("Purchase order not found")
        if po.status not in (POStatus.draft, POStatus.cancelled):
            raise ValidationError("Only draft or cancelled POs can be deleted")
        await db.delete(po)
        await db.commit()
        return {"message": "Purchase order deleted"}

    @staticmethod
    def _to_dict(po: PurchaseOrder) -> dict:
        return {
            "id": po.id,
            "po_number": po.po_number,
            "department_id": po.department_id,
            "department_name": po.department.name if po.department else None,
            "budget_line_id": po.budget_line_id,
            "budget_line_name": f"{po.budget_line.account_code} - {po.budget_line.account_name}" if po.budget_line else None,
            "supplier_name": po.supplier_name,
            "supplier_tax_id": po.supplier_tax_id,
            "amount": po.amount,
            "currency": po.currency,
            "accounting_code": po.accounting_code,
            "description": po.description,
            "status": po.status.value,
            "created_by": po.created_by,
            "approved_by": po.approved_by,
            "created_at": po.created_at.isoformat(),
            "updated_at": po.updated_at.isoformat(),
        }
