"""Workflow management service layer."""

import logging
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from common.models.workflow_definition import WorkflowDefinition
from common.models.workflow_step_definition import (
    WorkflowStepDefinition, StepType, RoutingStrategy,
)
from common.models.workflow_instance import WorkflowInstance, WorkflowStatus
from common.models.workflow_task import WorkflowTask, TaskStatus
from common.models.workflow_rule import WorkflowRule, RuleType
from common.models.delegation import Delegation
from common.workflow.engine import WorkflowEngine
from common.exceptions import NotFoundError, ValidationError

logger = logging.getLogger(__name__)


class WorkflowManagementService:
    """CRUD operations for workflow definitions, instances, tasks, delegations."""

    # ── Definitions ──

    @staticmethod
    async def list_definitions(db: AsyncSession) -> list[dict]:
        result = await db.execute(
            select(WorkflowDefinition).order_by(WorkflowDefinition.code)
        )
        defs = result.scalars().all()
        return [WorkflowManagementService._def_to_dict(d) for d in defs]

    @staticmethod
    async def create_definition(db: AsyncSession, data: dict, user_id: str) -> dict:
        steps_data = data.pop("steps", [])
        wf = WorkflowDefinition(**data, created_by=user_id)
        db.add(wf)
        await db.flush()

        for s in steps_data:
            step = WorkflowStepDefinition(
                workflow_id=wf.id,
                step_order=s["step_order"],
                step_code=s["step_code"],
                step_name=s["step_name"],
                step_type=StepType(s.get("step_type", "approval")),
                routing_strategy=RoutingStrategy(s.get("routing_strategy", "fixed_role")),
                assigned_role=s.get("assigned_role"),
                is_parallel=s.get("is_parallel", False),
                parallel_group=s.get("parallel_group"),
                skip_rules=s.get("skip_rules"),
                timeout_hours=s.get("timeout_hours"),
                escalation_role=s.get("escalation_role"),
                config=s.get("config"),
            )
            db.add(step)

        await db.commit()
        await db.refresh(wf)
        return WorkflowManagementService._def_to_dict(wf)

    @staticmethod
    async def get_definition(db: AsyncSession, def_id: str) -> dict:
        wf = await db.get(WorkflowDefinition, def_id)
        if not wf:
            raise NotFoundError("WorkflowDefinition", def_id)
        result = WorkflowManagementService._def_to_dict(wf)
        # Include rules
        rules_result = await db.execute(
            select(WorkflowRule).where(WorkflowRule.workflow_id == def_id)
            .order_by(WorkflowRule.priority.desc())
        )
        result["rules"] = [WorkflowManagementService._rule_to_dict(r) for r in rules_result.scalars().all()]
        return result

    # ── Rules ──

    @staticmethod
    async def create_rule(db: AsyncSession, data: dict) -> dict:
        rule = WorkflowRule(
            workflow_id=data["workflow_id"],
            step_code=data.get("step_code"),
            rule_type=RuleType(data["rule_type"]),
            name=data["name"],
            priority=data.get("priority", 0),
            condition=data["condition"],
            action=data["action"],
            is_active=data.get("is_active", True),
        )
        db.add(rule)
        await db.commit()
        await db.refresh(rule)
        return WorkflowManagementService._rule_to_dict(rule)

    # ── Instances ──

    @staticmethod
    async def list_instances(
        db: AsyncSession,
        entity_type: str | None = None,
        status: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> dict:
        import math
        query = select(WorkflowInstance)
        count_query = select(func.count(WorkflowInstance.id))

        if entity_type:
            query = query.where(WorkflowInstance.entity_type == entity_type)
            count_query = count_query.where(WorkflowInstance.entity_type == entity_type)
        if status:
            query = query.where(WorkflowInstance.status == WorkflowStatus(status))
            count_query = count_query.where(WorkflowInstance.status == WorkflowStatus(status))

        total = await db.scalar(count_query) or 0
        result = await db.execute(
            query.order_by(WorkflowInstance.created_at.desc())
            .offset((page - 1) * limit).limit(limit)
        )
        instances = result.scalars().all()

        return {
            "items": [WorkflowManagementService._instance_to_dict(i) for i in instances],
            "total": total,
            "page": page,
            "limit": limit,
            "pages": math.ceil(total / limit) if total > 0 else 1,
        }

    @staticmethod
    async def get_instance(db: AsyncSession, instance_id: str) -> dict:
        instance = await db.get(WorkflowInstance, instance_id)
        if not instance:
            raise NotFoundError("WorkflowInstance", instance_id)
        result = WorkflowManagementService._instance_to_dict(instance)
        result["tasks"] = [WorkflowManagementService._task_to_dict(t) for t in instance.tasks]
        return result

    @staticmethod
    async def cancel_instance(db: AsyncSession, instance_id: str) -> dict:
        engine = WorkflowEngine(db)
        await engine.cancel_instance(instance_id)
        await db.commit()
        instance = await db.get(WorkflowInstance, instance_id)
        return WorkflowManagementService._instance_to_dict(instance)

    # ── Tasks ──

    @staticmethod
    async def get_pending_tasks(db: AsyncSession, user_id: str, user_role: str) -> list[dict]:
        """Get pending tasks for the current user (by assignment or role)."""
        query = select(WorkflowTask).where(WorkflowTask.status == TaskStatus.pending)
        result = await db.execute(query.order_by(WorkflowTask.created_at))
        tasks = result.scalars().all()

        user_tasks = []
        for t in tasks:
            # Match by assignment, delegation, or role
            if (t.assigned_to == user_id
                    or t.delegated_to == user_id
                    or (not t.assigned_to and t.assigned_role == user_role)
                    or user_role == "admin"):
                user_tasks.append(WorkflowManagementService._task_to_dict(t))

        return user_tasks

    @staticmethod
    async def decide_task(
        db: AsyncSession, task_id: str, decision: str,
        comment: str | None, user_id: str, user_role: str,
    ) -> dict:
        engine = WorkflowEngine(db)
        result = await engine.process_decision(task_id, decision, comment, user_id, user_role)
        await db.commit()
        return result

    # ── Delegations ──

    @staticmethod
    async def create_delegation(db: AsyncSession, user_id: str, data: dict) -> dict:
        delegation = Delegation(
            delegator_id=user_id,
            delegate_id=data["delegate_id"],
            workflow_code=data.get("workflow_code"),
            valid_from=data["valid_from"],
            valid_until=data["valid_until"],
        )
        db.add(delegation)
        await db.commit()
        await db.refresh(delegation)
        return WorkflowManagementService._delegation_to_dict(delegation)

    @staticmethod
    async def list_delegations(db: AsyncSession, user_id: str | None = None) -> list[dict]:
        query = select(Delegation).where(Delegation.is_active == True)
        if user_id:
            query = query.where(Delegation.delegator_id == user_id)
        result = await db.execute(query.order_by(Delegation.created_at.desc()))
        return [WorkflowManagementService._delegation_to_dict(d) for d in result.scalars().all()]

    @staticmethod
    async def delete_delegation(db: AsyncSession, delegation_id: str) -> dict:
        delegation = await db.get(Delegation, delegation_id)
        if not delegation:
            raise NotFoundError("Delegation", delegation_id)
        delegation.is_active = False
        await db.commit()
        return {"message": "Delegation deactivated"}

    # ── Serializers ──

    @staticmethod
    def _def_to_dict(wf: WorkflowDefinition) -> dict:
        return {
            "id": wf.id,
            "code": wf.code,
            "name": wf.name,
            "entity_type": wf.entity_type,
            "version": wf.version,
            "is_active": wf.is_active,
            "trigger_event": wf.trigger_event,
            "config": wf.config,
            "created_at": wf.created_at.isoformat(),
            "steps": [{
                "id": s.id,
                "step_order": s.step_order,
                "step_code": s.step_code,
                "step_name": s.step_name,
                "step_type": s.step_type.value,
                "routing_strategy": s.routing_strategy.value,
                "assigned_role": s.assigned_role,
                "is_parallel": s.is_parallel,
                "parallel_group": s.parallel_group,
                "timeout_hours": s.timeout_hours,
                "escalation_role": s.escalation_role,
                "config": s.config,
            } for s in (wf.steps or [])],
        }

    @staticmethod
    def _rule_to_dict(r: WorkflowRule) -> dict:
        return {
            "id": r.id,
            "workflow_id": r.workflow_id,
            "step_code": r.step_code,
            "rule_type": r.rule_type.value,
            "name": r.name,
            "priority": r.priority,
            "condition": r.condition,
            "action": r.action,
            "is_active": r.is_active,
            "created_at": r.created_at.isoformat(),
        }

    @staticmethod
    def _instance_to_dict(i: WorkflowInstance) -> dict:
        return {
            "id": i.id,
            "workflow_definition_id": i.workflow_definition_id,
            "workflow_code": i.workflow_definition.code if i.workflow_definition else None,
            "entity_type": i.entity_type,
            "entity_id": i.entity_id,
            "status": i.status.value,
            "current_step_order": i.current_step_order,
            "context": i.context,
            "initiated_by": i.initiated_by,
            "initiator_name": i.initiator.full_name if i.initiator else None,
            "completed_at": i.completed_at.isoformat() if i.completed_at else None,
            "created_at": i.created_at.isoformat(),
        }

    @staticmethod
    def _task_to_dict(t: WorkflowTask) -> dict:
        return {
            "id": t.id,
            "instance_id": t.instance_id,
            "step_order": t.step_order,
            "step_name": t.step_name,
            "status": t.status.value,
            "assigned_role": t.assigned_role,
            "assigned_to": t.assigned_to,
            "assignee_name": t.assignee.full_name if t.assignee else None,
            "delegated_to": t.delegated_to,
            "delegate_name": t.delegate.full_name if t.delegate else None,
            "parallel_group": t.parallel_group,
            "decided_by": t.decided_by,
            "decider_name": t.decider.full_name if t.decider else None,
            "decided_at": t.decided_at.isoformat() if t.decided_at else None,
            "comment": t.comment,
            "due_at": t.due_at.isoformat() if t.due_at else None,
            "escalated_at": t.escalated_at.isoformat() if t.escalated_at else None,
            "created_at": t.created_at.isoformat(),
        }

    @staticmethod
    def _delegation_to_dict(d: Delegation) -> dict:
        return {
            "id": d.id,
            "delegator_id": d.delegator_id,
            "delegator_name": d.delegator.full_name if d.delegator else None,
            "delegate_id": d.delegate_id,
            "delegate_name": d.delegate.full_name if d.delegate else None,
            "workflow_code": d.workflow_code,
            "valid_from": d.valid_from.isoformat(),
            "valid_until": d.valid_until.isoformat(),
            "is_active": d.is_active,
            "created_at": d.created_at.isoformat(),
        }
