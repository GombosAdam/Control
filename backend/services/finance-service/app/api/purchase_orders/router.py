from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from common.dependencies import get_db, get_current_user
from common.models.user import User
from app.api.purchase_orders.service import PurchaseOrderService
from app.api.purchase_orders.schemas import PurchaseOrderCreate, PurchaseOrderUpdate, POApprovalDecisionRequest, GoodsReceiptCreate

router = APIRouter()


@router.get("/")
async def list_purchase_orders(
    department_id: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Role-based department scoping
    if current_user.role.value in ("admin", "cfo", "accountant"):
        # Full access
        effective_dept = department_id
    elif current_user.role.value == "department_head":
        # Own department (override if trying to see another)
        if department_id and department_id != current_user.department_id:
            effective_dept = current_user.department_id
        else:
            effective_dept = department_id or current_user.department_id
    else:
        # clerk, reviewer — own department only
        effective_dept = current_user.department_id
    return await PurchaseOrderService.list_orders(db, effective_dept, status, page, limit)


@router.post("/")
async def create_purchase_order(
    data: PurchaseOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await PurchaseOrderService.create(db, data.model_dump(), current_user.id)


@router.put("/{po_id}")
async def update_purchase_order(
    po_id: str,
    data: PurchaseOrderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await PurchaseOrderService.update(db, po_id, data.model_dump(exclude_unset=True))


@router.post("/{po_id}/approve")
async def approve_purchase_order(
    po_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await PurchaseOrderService.approve(db, po_id, current_user.id)


@router.post("/{po_id}/receive")
async def receive_purchase_order(
    po_id: str,
    body: GoodsReceiptCreate | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    received_date = body.received_date if body else None
    notes = body.notes if body else None
    return await PurchaseOrderService.receive(db, po_id, current_user.id, received_date, notes)


@router.get("/{po_id}/goods-receipt")
async def get_goods_receipt(
    po_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await PurchaseOrderService.get_goods_receipt(db, po_id)


@router.get("/{po_id}/approvals")
async def get_po_approvals(
    po_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await PurchaseOrderService.get_approval_status(db, po_id)


@router.post("/{po_id}/approvals/{step}/decide")
async def decide_po_approval(
    po_id: str,
    step: int,
    body: POApprovalDecisionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await PurchaseOrderService.decide_po_approval(
        db, po_id, step, body.decision, body.comment,
        current_user.id, user_role=current_user.role.value,
    )


@router.delete("/{po_id}")
async def delete_purchase_order(
    po_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await PurchaseOrderService.delete(db, po_id)
