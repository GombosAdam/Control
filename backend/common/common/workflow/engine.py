"""Workflow engine: state machine for approval workflows."""

import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.events import event_bus
from common.models.workflow_definition import WorkflowDefinition
from common.models.workflow_step_definition import WorkflowStepDefinition, RoutingStrategy
from common.models.workflow_instance import WorkflowInstance, WorkflowStatus
from common.models.workflow_task import WorkflowTask, TaskStatus
from common.models.workflow_rule import WorkflowRule, RuleType
from common.models.delegation import Delegation
from common.models.user import User
from common.models.position import Position
from common.workflow.rules import RuleEvaluator

logger = logging.getLogger(__name__)


class WorkflowEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def start_workflow(
        self,
        workflow_code: str,
        entity_type: str,
        entity_id: str,
        context: dict,
        initiated_by: str,
    ) -> WorkflowInstance:
        """Start a new workflow instance."""
        # 1. Lookup active workflow definition
        result = await self.db.execute(
            select(WorkflowDefinition).where(
                WorkflowDefinition.code == workflow_code,
                WorkflowDefinition.is_active == True,
            )
        )
        wf_def = result.scalar_one_or_none()
        if not wf_def:
            raise ValueError(f"No active workflow definition found for code: {workflow_code}")

        # 2. Create workflow instance
        instance = WorkflowInstance(
            workflow_definition_id=wf_def.id,
            entity_type=entity_type,
            entity_id=entity_id,
            status=WorkflowStatus.active,
            current_step_order=1,
            context=context,
            initiated_by=initiated_by,
        )
        self.db.add(instance)
        await self.db.flush()

        # 3. Load rules for this workflow
        rules_result = await self.db.execute(
            select(WorkflowRule).where(
                WorkflowRule.workflow_id == wf_def.id,
                WorkflowRule.is_active == True,
            ).order_by(WorkflowRule.priority.desc())
        )
        rules = rules_result.scalars().all()

        # 4. Create tasks based on step definitions
        step_defs = sorted(wf_def.steps, key=lambda s: s.step_order)

        if not step_defs:
            raise ValueError(f"Workflow '{workflow_code}' has no step definitions")

        # For position_hierarchy routing: dynamically generate tasks by walking the tree
        hierarchy_steps = [s for s in step_defs if s.routing_strategy == RoutingStrategy.position_hierarchy]

        if hierarchy_steps:
            await self._create_hierarchy_tasks(instance, hierarchy_steps[0], context, initiated_by, rules)
        else:
            # Fixed steps
            for step_def in step_defs:
                await self._create_fixed_task(instance, step_def, context, rules)

        # 5. Activate first task(s)
        await self._activate_next_tasks(instance, start_order=1)

        # 6. Publish event
        asyncio.create_task(event_bus.publish("wf.started", {
            "instance_id": instance.id,
            "workflow_code": workflow_code,
            "entity_type": entity_type,
            "entity_id": entity_id,
        }))

        return instance

    async def _create_hierarchy_tasks(
        self,
        instance: WorkflowInstance,
        step_def: WorkflowStepDefinition,
        context: dict,
        initiated_by: str,
        rules: list[WorkflowRule],
    ) -> None:
        """Walk position hierarchy to create approval tasks."""
        creator = await self.db.get(User, initiated_by)
        if not creator or not creator.position_id:
            raise ValueError("User has no position assigned")

        position = await self.db.get(Position, creator.position_id)
        if not position or not position.reports_to_id:
            raise ValueError("Position has no reports_to set")

        step_num = 0
        current_pos = position
        visited = set()

        # Check for max hierarchy levels rule
        max_levels = None
        for rule in rules:
            if rule.rule_type == RuleType.skip_step and rule.step_code == step_def.step_code:
                if RuleEvaluator.evaluate(rule.condition, context):
                    action = rule.action or {}
                    if "max_levels" in action:
                        max_levels = action["max_levels"]

        while current_pos.reports_to_id and current_pos.reports_to_id not in visited:
            visited.add(current_pos.id)
            parent_pos = await self.db.get(Position, current_pos.reports_to_id)
            if not parent_pos:
                break

            # Find active user holding the parent position
            holder_result = await self.db.execute(
                select(User).where(
                    User.position_id == parent_pos.id,
                    User.is_active == True,
                ).limit(1)
            )
            holder = holder_result.scalar_one_or_none()

            step_num += 1

            # Check max_levels
            if max_levels is not None and step_num > max_levels:
                break

            task = WorkflowTask(
                instance_id=instance.id,
                step_definition_id=step_def.id,
                step_order=step_num,
                step_name=f"{parent_pos.name} jóváhagyás",
                status=TaskStatus.waiting,
                assigned_role=holder.role.value if holder else "department_head",
                assigned_to=holder.id if holder else None,
            )
            if step_def.timeout_hours:
                task.due_at = None  # Set when activated
            self.db.add(task)
            current_pos = parent_pos

        if step_num == 0:
            raise ValueError("No approval chain — position has no parent")

    async def _create_fixed_task(
        self,
        instance: WorkflowInstance,
        step_def: WorkflowStepDefinition,
        context: dict,
        rules: list[WorkflowRule],
    ) -> None:
        """Create a task for a fixed step definition."""
        # Check skip rules
        should_skip = False
        should_auto_approve = False

        for rule in rules:
            if rule.step_code and rule.step_code != step_def.step_code:
                continue
            if not RuleEvaluator.evaluate(rule.condition, context):
                continue

            if rule.rule_type == RuleType.skip_step:
                should_skip = True
            elif rule.rule_type == RuleType.auto_approve:
                should_auto_approve = True

        status = TaskStatus.waiting
        if should_skip:
            status = TaskStatus.skipped

        task = WorkflowTask(
            instance_id=instance.id,
            step_definition_id=step_def.id,
            step_order=step_def.step_order,
            step_name=step_def.step_name,
            status=status,
            assigned_role=step_def.assigned_role,
            parallel_group=step_def.parallel_group if step_def.is_parallel else None,
        )
        self.db.add(task)
        await self.db.flush()

        # Auto-approve if rule matched
        if should_auto_approve and not should_skip:
            task.status = TaskStatus.approved
            task.decided_at = datetime.utcnow()
            task.comment = "Auto-approved by rule"

    async def _activate_next_tasks(self, instance: WorkflowInstance, start_order: int) -> None:
        """Activate the next waiting task(s), skipping already decided ones."""
        result = await self.db.execute(
            select(WorkflowTask).where(
                WorkflowTask.instance_id == instance.id,
                WorkflowTask.status == TaskStatus.waiting,
                WorkflowTask.step_order >= start_order,
            ).order_by(WorkflowTask.step_order)
        )
        waiting_tasks = result.scalars().all()

        if not waiting_tasks:
            # Check if all tasks are done
            all_result = await self.db.execute(
                select(WorkflowTask).where(
                    WorkflowTask.instance_id == instance.id,
                    WorkflowTask.status.in_([TaskStatus.waiting, TaskStatus.pending]),
                )
            )
            if not all_result.scalars().all():
                await self._complete_instance(instance)
            return

        # Find the lowest step_order among waiting tasks
        next_order = waiting_tasks[0].step_order

        # Activate all tasks at this step_order (supports parallel)
        tasks_to_activate = [t for t in waiting_tasks if t.step_order == next_order]

        for task in tasks_to_activate:
            task.status = TaskStatus.pending
            # Resolve delegation
            await self._resolve_delegation(task, instance)
            # Set timeout
            if task.step_definition and task.step_definition.timeout_hours:
                task.due_at = datetime.utcnow() + timedelta(hours=task.step_definition.timeout_hours)

        instance.current_step_order = next_order

    async def _resolve_delegation(self, task: WorkflowTask, instance: WorkflowInstance) -> None:
        """Check if the assigned user has an active delegation."""
        if not task.assigned_to:
            return

        now = datetime.utcnow()
        wf_code = instance.workflow_definition.code if instance.workflow_definition else None

        result = await self.db.execute(
            select(Delegation).where(
                Delegation.delegator_id == task.assigned_to,
                Delegation.is_active == True,
                Delegation.valid_from <= now,
                Delegation.valid_until >= now,
            )
        )
        delegations = result.scalars().all()

        for d in delegations:
            if d.workflow_code is None or d.workflow_code == wf_code:
                task.delegated_to = d.delegate_id
                break

    async def process_decision(
        self,
        task_id: str,
        decision: str,
        comment: str | None,
        user_id: str,
        user_role: str,
    ) -> dict:
        """Process approve/reject decision on a task."""
        if decision not in ("approved", "rejected"):
            raise ValueError("Decision must be 'approved' or 'rejected'")

        task = await self.db.get(WorkflowTask, task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        if task.status != TaskStatus.pending:
            raise ValueError(f"Task is {task.status.value}, cannot decide")

        # Auth check: assigned_to → delegated_to → assigned_role → admin
        can_decide = False
        if task.assigned_to:
            can_decide = (
                user_id == task.assigned_to
                or user_id == task.delegated_to
                or user_role == "admin"
            )
        else:
            can_decide = user_role == task.assigned_role or user_role == "admin"

        if not can_decide:
            raise PermissionError("User is not authorized to decide on this task")

        # Record decision
        task.status = TaskStatus.approved if decision == "approved" else TaskStatus.rejected
        task.decided_by = user_id
        task.decided_at = datetime.utcnow()
        task.comment = comment

        instance = await self.db.get(WorkflowInstance, task.instance_id)

        if decision == "rejected":
            await self._cancel_remaining(instance)
            instance.status = WorkflowStatus.rejected
            instance.completed_at = datetime.utcnow()
        else:
            # Check parallel group completion
            if task.parallel_group:
                pending_in_group = await self.db.execute(
                    select(WorkflowTask).where(
                        WorkflowTask.instance_id == instance.id,
                        WorkflowTask.parallel_group == task.parallel_group,
                        WorkflowTask.status == TaskStatus.pending,
                    )
                )
                if pending_in_group.scalars().all():
                    # Still waiting for other tasks in the group
                    await self.db.flush()
                    asyncio.create_task(event_bus.publish("wf.task.decided", {
                        "task_id": task_id, "decision": decision, "instance_id": instance.id,
                    }))
                    return {"task_id": task_id, "decision": decision}

            # Advance to next step
            await self._activate_next_tasks(instance, task.step_order + 1)

        await self.db.flush()

        # Publish event
        event_type = "wf.completed" if instance.status in (WorkflowStatus.completed, WorkflowStatus.rejected) else "wf.task.decided"
        asyncio.create_task(event_bus.publish(event_type, {
            "task_id": task_id,
            "decision": decision,
            "instance_id": instance.id,
            "entity_type": instance.entity_type,
            "entity_id": instance.entity_id,
            "status": instance.status.value,
        }))

        return {"task_id": task_id, "decision": decision, "instance_status": instance.status.value}

    async def _complete_instance(self, instance: WorkflowInstance) -> None:
        """Mark instance as completed."""
        instance.status = WorkflowStatus.completed
        instance.completed_at = datetime.utcnow()

        asyncio.create_task(event_bus.publish("wf.completed", {
            "instance_id": instance.id,
            "entity_type": instance.entity_type,
            "entity_id": instance.entity_id,
        }))

    async def _cancel_remaining(self, instance: WorkflowInstance) -> None:
        """Cancel all waiting/pending tasks."""
        result = await self.db.execute(
            select(WorkflowTask).where(
                WorkflowTask.instance_id == instance.id,
                WorkflowTask.status.in_([TaskStatus.waiting, TaskStatus.pending]),
            )
        )
        for task in result.scalars().all():
            task.status = TaskStatus.cancelled

    async def cancel_instance(self, instance_id: str) -> None:
        """Cancel a workflow instance."""
        instance = await self.db.get(WorkflowInstance, instance_id)
        if not instance:
            raise ValueError(f"Instance not found: {instance_id}")
        if instance.status != WorkflowStatus.active:
            raise ValueError(f"Instance is {instance.status.value}, cannot cancel")

        await self._cancel_remaining(instance)
        instance.status = WorkflowStatus.cancelled
        instance.completed_at = datetime.utcnow()

    async def escalate_task(self, task_id: str) -> WorkflowTask | None:
        """Escalate a timed-out task."""
        task = await self.db.get(WorkflowTask, task_id)
        if not task or task.status != TaskStatus.pending:
            return None

        step_def = task.step_definition
        if not step_def or not step_def.escalation_role:
            # No escalation configured — just mark timed out
            task.status = TaskStatus.timed_out
            task.escalated_at = datetime.utcnow()
            return None

        # Mark original task
        task.status = TaskStatus.timed_out
        task.escalated_at = datetime.utcnow()

        # Create escalation task
        escalation_task = WorkflowTask(
            instance_id=task.instance_id,
            step_definition_id=task.step_definition_id,
            step_order=task.step_order,
            step_name=f"{task.step_name} (eszkaláció)",
            status=TaskStatus.pending,
            assigned_role=step_def.escalation_role,
        )
        if step_def.timeout_hours:
            escalation_task.due_at = datetime.utcnow() + timedelta(hours=step_def.timeout_hours)

        self.db.add(escalation_task)
        await self.db.flush()

        asyncio.create_task(event_bus.publish("wf.task.escalated", {
            "original_task_id": task_id,
            "escalation_task_id": escalation_task.id,
            "instance_id": task.instance_id,
        }))

        return escalation_task
