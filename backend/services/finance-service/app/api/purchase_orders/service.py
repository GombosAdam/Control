import asyncio
import logging
import math
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from common.models.purchase_order import PurchaseOrder, POStatus
from common.models.purchase_order_line import PurchaseOrderLine
from common.models.goods_receipt import GoodsReceipt, GoodsReceiptLine
from common.models.purchase_order_approval import PurchaseOrderApproval
from common.models.budget_line import BudgetLine, BudgetStatus
from common.models.accounting_entry import AccountingEntry
from common.models.audit import AuditLog
from common.models.user import User, UserRole
from common.models.position import Position
from common.exceptions import NotFoundError, ValidationError, DuplicateError, AuthorizationError
from common.events import event_bus

logger = logging.getLogger(__name__)


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
    async def _generate_gr_number(db: AsyncSession) -> str:
        """Generate next GR number: GR-YYYY-NNN"""
        year = datetime.utcnow().year
        prefix = f"GR-{year}-"
        result = await db.scalar(
            select(func.count(GoodsReceipt.id)).where(
                GoodsReceipt.gr_number.like(f"{prefix}%")
            )
        )
        next_num = (result or 0) + 1
        return f"{prefix}{next_num:03d}"

    @staticmethod
    async def create(db: AsyncSession, data: dict, user_id: str) -> dict:
        # Department validation: non-admin/cfo users can only order for their own department
        creator = await db.get(User, user_id)
        if creator and creator.role.value not in ("admin", "cfo"):
            if creator.department_id and data.get("department_id") != creator.department_id:
                raise AuthorizationError(
                    "Csak a saját osztályod nevében adhatsz fel megrendelést."
                )

        # Extract lines
        lines_data = data.pop("lines", [])

        # Calculate amount from lines
        amount = sum(line["quantity"] * line["unit_price"] for line in lines_data)
        data["amount"] = round(amount, 2)

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
        from common.models.accounting_entry import EntryType
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

        # Create PO lines
        for idx, line_data in enumerate(lines_data):
            net_amount = round(line_data["quantity"] * line_data["unit_price"], 2)
            po_line = PurchaseOrderLine(
                purchase_order_id=po.id,
                description=line_data["description"],
                quantity=line_data["quantity"],
                unit_price=line_data["unit_price"],
                net_amount=net_amount,
                sort_order=idx,
            )
            db.add(po_line)

        # Auto-submit for approval
        await PurchaseOrderService._create_approval_chain(db, po, user_id)

        await db.commit()
        await db.refresh(po)

        # Publish event: approval chain created
        asyncio.create_task(event_bus.publish("po.submitted", {
            "purchase_order_id": po.id,
            "created_by": user_id,
            "amount": po.amount,
        }))

        return PurchaseOrderService._to_dict(po)

    @staticmethod
    async def _create_approval_chain(db: AsyncSession, po: PurchaseOrder, user_id: str) -> None:
        """Create dynamic approval chain by walking up the position hierarchy."""
        # Check for existing chain
        existing = await db.execute(
            select(PurchaseOrderApproval).where(
                PurchaseOrderApproval.purchase_order_id == po.id
            ).limit(1)
        )
        if existing.scalar_one_or_none():
            return

        # Fetch creator's position
        creator = await db.get(User, user_id)
        if not creator or not creator.position_id:
            raise ValidationError("A felhasználóhoz nincs pozíció rendelve. Kérjük, forduljon az adminisztrátorhoz.")

        position = await db.get(Position, creator.position_id)
        if not position or not position.reports_to_id:
            raise ValidationError("A pozícióhoz nincs felettes pozíció beállítva. Kérjük, forduljon az adminisztrátorhoz.")

        # Walk up the position tree
        steps = []
        current_pos = position
        step_num = 0
        visited = set()  # infinite loop protection

        while current_pos.reports_to_id and current_pos.reports_to_id not in visited:
            visited.add(current_pos.id)
            parent_pos = await db.get(Position, current_pos.reports_to_id)
            if not parent_pos:
                break

            # Find active user holding the parent position
            holder_result = await db.execute(
                select(User).where(
                    User.position_id == parent_pos.id,
                    User.is_active == True,
                ).limit(1)
            )
            holder = holder_result.scalar_one_or_none()

            step_num += 1
            steps.append((
                step_num,
                f"{parent_pos.name} jóváhagyás",
                holder.role.value if holder else "department_head",
                holder.id if holder else None,
            ))

            current_pos = parent_pos

        if not steps:
            raise ValidationError("Nincs jóváhagyási lánc — a pozíciónak nincs felettese.")

        # Create approval records
        for sn, name, role, assignee_id in steps:
            approval = PurchaseOrderApproval(
                purchase_order_id=po.id,
                step=sn,
                step_name=name,
                status="pending" if sn == 1 else "waiting",
                assigned_role=role,
                assigned_to=assignee_id,
            )
            db.add(approval)

        log = AuditLog(
            user_id=user_id, action="po.submit_approval",
            entity_type="purchase_order", entity_id=po.id,
            details={
                "steps": len(steps),
                "amount": po.amount,
                "chain": [{"step": sn, "name": name, "assignee_id": aid}
                          for sn, name, _, aid in steps],
            },
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
            "assigned_to": a.assigned_to,
            "assignee_name": a.assignee.full_name if a.assignee else None,
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

        # Authorization: concrete user assignment takes priority, then role-based
        can_decide = False
        if approval.assigned_to:
            can_decide = (user_id == approval.assigned_to) or (user_role == "admin")
        else:
            can_decide = (user_role == approval.assigned_role) or (user_role == "admin")

        if not can_decide:
            if approval.assigned_to:
                assignee = await db.get(User, approval.assigned_to)
                assignee_name = assignee.full_name if assignee else approval.assigned_to
                raise AuthorizationError(
                    f"Ez a lépés {assignee_name} feladata"
                )
            raise AuthorizationError(
                f"'{user_role}' szerepkör nem dönthet '{approval.assigned_role}' lépésről"
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

        # Publish step decision event
        event_payload = {
            "purchase_order_id": po_id,
            "step": step,
            "decision": decision,
            "decided_by": user_id,
        }
        if decision == "rejected":
            asyncio.create_task(event_bus.publish("po.step_rejected", event_payload))
        else:
            if po.status == POStatus.approved:
                asyncio.create_task(event_bus.publish("po.approved", event_payload))
            else:
                asyncio.create_task(event_bus.publish("po.step_approved", event_payload))

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
        """Legacy single-step approve -- kept for backward compatibility."""
        po = await db.get(PurchaseOrder, po_id)
        if not po:
            raise NotFoundError("Purchase order not found")
        if po.status != POStatus.draft:
            raise ValidationError("Only draft POs can be approved")
        po.status = POStatus.approved
        po.approved_by = user_id
        await db.commit()
        await db.refresh(po)

        # Publish event
        asyncio.create_task(event_bus.publish("po.approved", {"purchase_order_id": po.id}))

        return PurchaseOrderService._to_dict(po)

    @staticmethod
    async def receive(db: AsyncSession, po_id: str, user_id: str,
                      received_date: str | None = None, notes: str | None = None) -> dict:
        po = await db.get(PurchaseOrder, po_id)
        if not po:
            raise NotFoundError("Purchase order not found")
        if po.status != POStatus.approved:
            raise ValidationError("Only approved POs can be received")

        # Check no existing GR
        if po.goods_receipt:
            raise ValidationError("PO already has a goods receipt")

        # Generate GR number
        gr_number = await PurchaseOrderService._generate_gr_number(db)

        # Parse received date
        if received_date:
            rd = date.fromisoformat(received_date)
        else:
            rd = date.today()

        # Create GoodsReceipt
        gr = GoodsReceipt(
            gr_number=gr_number,
            purchase_order_id=po.id,
            received_date=rd,
            received_by=user_id,
            notes=notes,
        )
        db.add(gr)
        await db.flush()

        # Create GR lines for each PO line
        for po_line in po.lines:
            gr_line = GoodsReceiptLine(
                goods_receipt_id=gr.id,
                purchase_order_line_id=po_line.id,
                quantity_received=po_line.quantity,
            )
            db.add(gr_line)

        po.status = POStatus.received

        # Audit log
        log = AuditLog(
            user_id=user_id, action="po.goods_receipt",
            entity_type="purchase_order", entity_id=po.id,
            details={"gr_number": gr_number, "received_date": rd.isoformat()},
        )
        db.add(log)

        await db.commit()
        await db.refresh(po)
        return PurchaseOrderService._to_dict(po)

    @staticmethod
    async def get_goods_receipt(db: AsyncSession, po_id: str) -> dict:
        po = await db.get(PurchaseOrder, po_id)
        if not po:
            raise NotFoundError("Purchase order not found")
        gr = po.goods_receipt
        if not gr:
            raise NotFoundError("Goods receipt", po_id)
        return {
            "id": gr.id,
            "gr_number": gr.gr_number,
            "purchase_order_id": gr.purchase_order_id,
            "received_date": gr.received_date.isoformat(),
            "received_by": gr.received_by,
            "receiver_name": gr.receiver.full_name if gr.receiver else None,
            "notes": gr.notes,
            "created_at": gr.created_at.isoformat(),
            "lines": [{
                "id": line.id,
                "purchase_order_line_id": line.purchase_order_line_id,
                "description": line.purchase_order_line.description if line.purchase_order_line else None,
                "quantity_received": line.quantity_received,
            } for line in gr.lines],
        }

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
        result = {
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
            "lines": [{
                "id": line.id,
                "description": line.description,
                "quantity": line.quantity,
                "unit_price": line.unit_price,
                "net_amount": line.net_amount,
                "sort_order": line.sort_order,
            } for line in po.lines] if po.lines else [],
            "goods_receipt": None,
        }
        if po.goods_receipt:
            gr = po.goods_receipt
            result["goods_receipt"] = {
                "id": gr.id,
                "gr_number": gr.gr_number,
                "received_date": gr.received_date.isoformat(),
                "receiver_name": gr.receiver.full_name if gr.receiver else None,
                "notes": gr.notes,
            }
        return result
