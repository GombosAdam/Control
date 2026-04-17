import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, JSON, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from common.database import Base


class StepType(str, enum.Enum):
    approval = "approval"
    notification = "notification"
    auto_action = "auto_action"


class RoutingStrategy(str, enum.Enum):
    fixed_role = "fixed_role"
    position_hierarchy = "position_hierarchy"
    department_manager = "department_manager"


class WorkflowStepDefinition(Base):
    __tablename__ = "workflow_step_definitions"
    __table_args__ = (
        UniqueConstraint("workflow_id", "step_order", name="uq_wf_step_order"),
        UniqueConstraint("workflow_id", "step_code", name="uq_wf_step_code"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id: Mapped[str] = mapped_column(String(36), ForeignKey("workflow_definitions.id", ondelete="CASCADE"),
                                             nullable=False, index=True)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    step_code: Mapped[str] = mapped_column(String(50), nullable=False)
    step_name: Mapped[str] = mapped_column(String(255), nullable=False)
    step_type: Mapped[StepType] = mapped_column(SAEnum(StepType), nullable=False, default=StepType.approval)
    routing_strategy: Mapped[RoutingStrategy] = mapped_column(SAEnum(RoutingStrategy), nullable=False,
                                                               default=RoutingStrategy.fixed_role)
    assigned_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_parallel: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    parallel_group: Mapped[str | None] = mapped_column(String(50), nullable=True)
    skip_rules: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    timeout_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    escalation_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    workflow = relationship("WorkflowDefinition", back_populates="steps")
