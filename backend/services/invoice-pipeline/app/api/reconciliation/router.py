from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from common.dependencies import get_db, get_current_user
from common.models.user import User
from app.api.reconciliation.service import ReconciliationService
from app.api.reconciliation.schemas import ManualMatchRequest

router = APIRouter()


@router.get("/pending")
async def list_pending(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ReconciliationService.list_pending(db, page, limit)


@router.post("/{invoice_id}/match")
async def auto_match(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ReconciliationService.auto_match(db, invoice_id)


@router.post("/{invoice_id}/manual-match")
async def manual_match(
    invoice_id: str,
    data: ManualMatchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ReconciliationService.manual_match(db, invoice_id, data.purchase_order_id)


@router.post("/{invoice_id}/post")
async def post_to_accounting(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ReconciliationService.post_to_accounting(db, invoice_id, current_user.id)
