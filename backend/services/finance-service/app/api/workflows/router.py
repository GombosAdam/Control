"""Workflow management API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from common.dependencies import get_db, get_current_user, require_role
from common.models.user import User, UserRole
from app.api.workflows.service import WorkflowManagementService
from app.api.workflows.schemas import (
    WorkflowDefinitionCreate, WorkflowRuleCreate,
    TaskDecisionRequest, DelegationCreate,
)

router = APIRouter()


# ── Definitions ──

@router.get("/definitions")
async def list_definitions(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await WorkflowManagementService.list_definitions(db)


@router.post("/definitions")
async def create_definition(
    data: WorkflowDefinitionCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.admin)),
):
    return await WorkflowManagementService.create_definition(db, data.model_dump(), user.id)


@router.get("/definitions/{def_id}")
async def get_definition(
    def_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await WorkflowManagementService.get_definition(db, def_id)


# ── Rules ──

@router.post("/rules")
async def create_rule(
    data: WorkflowRuleCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    return await WorkflowManagementService.create_rule(db, data.model_dump())


# ── Instances ──

@router.get("/instances")
async def list_instances(
    entity_type: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await WorkflowManagementService.list_instances(db, entity_type, status, page, limit)


@router.get("/instances/{instance_id}")
async def get_instance(
    instance_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await WorkflowManagementService.get_instance(db, instance_id)


@router.post("/instances/{instance_id}/cancel")
async def cancel_instance(
    instance_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    return await WorkflowManagementService.cancel_instance(db, instance_id)


# ── Tasks ──

@router.get("/tasks/pending")
async def get_pending_tasks(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await WorkflowManagementService.get_pending_tasks(db, user.id, user.role.value)


@router.post("/tasks/{task_id}/decide")
async def decide_task(
    task_id: str,
    data: TaskDecisionRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await WorkflowManagementService.decide_task(
        db, task_id, data.decision, data.comment, user.id, user.role.value
    )


# ── Delegations ──

@router.post("/delegations")
async def create_delegation(
    data: DelegationCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await WorkflowManagementService.create_delegation(db, user.id, data.model_dump())


@router.get("/delegations")
async def list_delegations(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await WorkflowManagementService.list_delegations(db, user.id)


@router.delete("/delegations/{delegation_id}")
async def delete_delegation(
    delegation_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await WorkflowManagementService.delete_delegation(db, delegation_id)
