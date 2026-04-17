from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, require_role
from app.api.taxpayer.schemas import TaxpayerValidateRequest, TaxpayerValidatePartnerRequest
from app.api.taxpayer.service import TaxpayerService
from app.models.user import User

router = APIRouter()


@router.post("/validate")
async def validate_tax_number(
    data: TaxpayerValidateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "accountant")),
):
    return await TaxpayerService.validate_tax_number(db, data.config_id, data.tax_number)


@router.post("/validate-partner/{partner_id}")
async def validate_partner(
    partner_id: str,
    data: TaxpayerValidatePartnerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "accountant")),
):
    return await TaxpayerService.validate_partner(db, data.config_id, partner_id)
