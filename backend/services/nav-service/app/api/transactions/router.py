from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, require_role
from app.api.transactions.service import TransactionService
from app.models.user import User

router = APIRouter()


@router.get("")
async def list_transactions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "accountant")),
):
    return await TransactionService.list_transactions(db, page, limit, status)


@router.get("/{transaction_id}")
async def get_transaction(
    transaction_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "accountant")),
):
    return await TransactionService.get_transaction(db, transaction_id)


@router.post("/{transaction_id}/refresh")
async def refresh_status(
    transaction_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "accountant")),
):
    return await TransactionService.refresh_status(db, transaction_id)
