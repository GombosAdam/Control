from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from common.dependencies import get_db, get_current_user, require_role
from app.api.accounting.service import AccountingService
from common.models.user import User, UserRole


class AccountingTemplateCreate(BaseModel):
    account_code_pattern: str
    name: str
    debit_account: str
    credit_account: str
    description: str | None = None


class AccountingTemplateUpdate(BaseModel):
    account_code_pattern: str | None = None
    name: str | None = None
    debit_account: str | None = None
    credit_account: str | None = None
    description: str | None = None

router = APIRouter()


@router.get("/invoices")
async def list_approved_invoices(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    search: str | None = None,
    currency: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await AccountingService.list_approved(db, page, limit, search, currency)


@router.get("/summary")
async def get_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await AccountingService.get_summary(db)


@router.get("/entries")
async def list_entries(
    period: str | None = None,
    department_id: str | None = None,
    account_code: str | None = None,
    invoice_id: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await AccountingService.list_entries(db, period, department_id, account_code, page, limit, invoice_id=invoice_id)


@router.get("/templates")
async def list_templates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await AccountingService.list_templates(db)


@router.post("/templates")
async def create_template(
    data: AccountingTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.accountant)),
):
    return await AccountingService.create_template(db, data.model_dump())


@router.put("/templates/{template_id}")
async def update_template(
    template_id: str,
    data: AccountingTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.accountant)),
):
    return await AccountingService.update_template(db, template_id, data.model_dump(exclude_unset=True))


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    return await AccountingService.delete_template(db, template_id)
