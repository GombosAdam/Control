from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, get_current_user
from app.api.v1.partners.service import PartnerService
from app.api.v1.partners.schemas import PartnerCreateRequest, PartnerUpdateRequest
from app.models.user import User

router = APIRouter()

@router.get("")
async def list_partners(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    partner_type: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await PartnerService.list_partners(db, page, limit, partner_type, search)

@router.get("/{partner_id}")
async def get_partner(
    partner_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await PartnerService.get_partner(db, partner_id)

@router.post("")
async def create_partner(
    data: PartnerCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await PartnerService.create_partner(db, data)

@router.put("/{partner_id}")
async def update_partner(
    partner_id: str,
    data: PartnerUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await PartnerService.update_partner(db, partner_id, data)

@router.delete("/{partner_id}")
async def delete_partner(
    partner_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await PartnerService.delete_partner(db, partner_id)
    return {"message": "Partner deleted"}

@router.get("/{partner_id}/invoices")
async def get_partner_invoices(
    partner_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await PartnerService.get_partner_invoices(db, partner_id)
