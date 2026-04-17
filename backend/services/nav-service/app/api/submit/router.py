from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, require_role
from app.api.submit.schemas import SubmitRequest, SubmitBatchRequest
from app.api.submit.service import SubmitService
from app.models.user import User

router = APIRouter()


@router.post("")
async def submit_invoice(
    data: SubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "accountant")),
):
    return await SubmitService.submit_invoice(db, data.invoice_id, data.config_id)


@router.post("/batch")
async def submit_batch(
    data: SubmitBatchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "accountant")),
):
    return await SubmitService.submit_batch(db, data.invoice_ids, data.config_id)
