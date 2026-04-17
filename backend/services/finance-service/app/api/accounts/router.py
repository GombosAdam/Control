from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from common.dependencies import get_db, get_current_user, require_role
from common.models.user import User, UserRole
from app.api.accounts.service import AccountService
from app.api.accounts.schemas import AccountCreate, AccountUpdate

router = APIRouter()


@router.get("/")
async def list_accounts(
    type: str | None = Query(None),
    active: bool | None = Query(None),
    pnl_category: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await AccountService.list_all(db, account_type=type, active=active, pnl_category=pnl_category)


@router.get("/tree")
async def get_account_tree(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await AccountService.get_tree(db)


@router.get("/{code}")
async def get_account(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await AccountService.get(db, code)


@router.post("/")
async def create_account(
    data: AccountCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.cfo)),
):
    return await AccountService.create(db, data.model_dump())


@router.patch("/{code}")
async def update_account(
    code: str,
    data: AccountUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.cfo)),
):
    return await AccountService.update(db, code, data.model_dump(exclude_unset=True))
