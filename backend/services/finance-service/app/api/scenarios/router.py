from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from common.dependencies import get_db, get_current_user, require_role
from common.models.user import User, UserRole
from app.api.scenarios.service import ScenarioService
from app.api.scenarios.schemas import ScenarioCreate, ScenarioCopy

router = APIRouter()


@router.get("")
async def list_scenarios(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ScenarioService.list_scenarios(db)


@router.post("")
async def create_scenario(
    data: ScenarioCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.cfo)),
):
    return await ScenarioService.create_scenario(db, data.name, data.description, current_user.id)


@router.post("/copy")
async def copy_scenario(
    data: ScenarioCopy,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.cfo)),
):
    return await ScenarioService.copy_scenario(
        db, data.source_scenario_id, data.name, data.description,
        data.adjustment_pct, data.period, data.department_id, current_user.id,
    )


@router.delete("/{scenario_id}")
async def delete_scenario(
    scenario_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    return await ScenarioService.delete_scenario(db, scenario_id)
