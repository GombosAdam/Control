from pydantic import BaseModel
from datetime import datetime


# ── Workflow Definition ──

class StepDefinitionCreate(BaseModel):
    step_order: int
    step_code: str
    step_name: str
    step_type: str = "approval"
    routing_strategy: str = "fixed_role"
    assigned_role: str | None = None
    is_parallel: bool = False
    parallel_group: str | None = None
    skip_rules: dict | None = None
    timeout_hours: int | None = None
    escalation_role: str | None = None
    config: dict | None = None


class WorkflowDefinitionCreate(BaseModel):
    code: str
    name: str
    entity_type: str
    trigger_event: str
    config: dict | None = None
    steps: list[StepDefinitionCreate] = []


class StepDefinitionOut(BaseModel):
    id: str
    step_order: int
    step_code: str
    step_name: str
    step_type: str
    routing_strategy: str
    assigned_role: str | None
    is_parallel: bool
    parallel_group: str | None
    timeout_hours: int | None
    escalation_role: str | None
    config: dict | None


class WorkflowDefinitionOut(BaseModel):
    id: str
    code: str
    name: str
    entity_type: str
    version: int
    is_active: bool
    trigger_event: str
    config: dict | None
    created_at: datetime
    steps: list[StepDefinitionOut] = []


# ── Workflow Rule ──

class WorkflowRuleCreate(BaseModel):
    workflow_id: str
    step_code: str | None = None
    rule_type: str
    name: str
    priority: int = 0
    condition: dict
    action: dict
    is_active: bool = True


class WorkflowRuleOut(BaseModel):
    id: str
    workflow_id: str
    step_code: str | None
    rule_type: str
    name: str
    priority: int
    condition: dict
    action: dict
    is_active: bool
    created_at: datetime


# ── Workflow Instance ──

class WorkflowInstanceOut(BaseModel):
    id: str
    workflow_definition_id: str
    workflow_code: str | None = None
    entity_type: str
    entity_id: str
    status: str
    current_step_order: int
    context: dict | None
    initiated_by: str | None
    initiator_name: str | None = None
    completed_at: datetime | None
    created_at: datetime


# ── Workflow Task ──

class WorkflowTaskOut(BaseModel):
    id: str
    instance_id: str
    step_order: int
    step_name: str
    status: str
    assigned_role: str | None
    assigned_to: str | None
    assignee_name: str | None = None
    delegated_to: str | None
    delegate_name: str | None = None
    parallel_group: str | None
    decided_by: str | None
    decider_name: str | None = None
    decided_at: datetime | None
    comment: str | None
    due_at: datetime | None
    escalated_at: datetime | None
    created_at: datetime


class TaskDecisionRequest(BaseModel):
    decision: str  # "approved" or "rejected"
    comment: str | None = None


# ── Delegation ──

class DelegationCreate(BaseModel):
    delegate_id: str
    workflow_code: str | None = None
    valid_from: datetime
    valid_until: datetime


class DelegationOut(BaseModel):
    id: str
    delegator_id: str
    delegator_name: str | None = None
    delegate_id: str
    delegate_name: str | None = None
    workflow_code: str | None
    valid_from: datetime
    valid_until: datetime
    is_active: bool
    created_at: datetime
