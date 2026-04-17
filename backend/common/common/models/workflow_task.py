import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Index
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from common.database import Base


class TaskStatus(str, enum.Enum):
    waiting = "waiting"
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    skipped = "skipped"
    escalated = "escalated"
    cancelled = "cancelled"
    timed_out = "timed_out"


class WorkflowTask(Base):
    __tablename__ = "workflow_tasks"
    __table_args__ = (
        Index("ix_wf_task_timeout", "status", "due_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    instance_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workflow_instances.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_definition_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("workflow_step_definitions.id"), nullable=True
    )
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    step_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(SAEnum(TaskStatus), default=TaskStatus.waiting, nullable=False)
    assigned_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    assigned_to: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    delegated_to: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    parallel_group: Mapped[str | None] = mapped_column(String(50), nullable=True)
    decided_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    instance = relationship("WorkflowInstance", back_populates="tasks")
    step_definition = relationship("WorkflowStepDefinition", lazy="selectin")
    assignee = relationship("User", foreign_keys=[assigned_to], lazy="selectin")
    delegate = relationship("User", foreign_keys=[delegated_to], lazy="selectin")
    decider = relationship("User", foreign_keys=[decided_by], lazy="selectin")
