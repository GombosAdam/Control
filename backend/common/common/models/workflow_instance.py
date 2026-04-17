import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, JSON, Index
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from common.database import Base


class WorkflowStatus(str, enum.Enum):
    active = "active"
    completed = "completed"
    rejected = "rejected"
    cancelled = "cancelled"
    error = "error"


class WorkflowInstance(Base):
    __tablename__ = "workflow_instances"
    __table_args__ = (
        Index("ix_wf_instance_entity", "entity_type", "entity_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_definition_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workflow_definitions.id"), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    status: Mapped[WorkflowStatus] = mapped_column(SAEnum(WorkflowStatus), default=WorkflowStatus.active, nullable=False)
    current_step_order: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    context: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    initiated_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    workflow_definition = relationship("WorkflowDefinition", lazy="selectin")
    initiator = relationship("User", lazy="selectin")
    tasks = relationship("WorkflowTask", back_populates="instance", lazy="selectin",
                         order_by="WorkflowTask.step_order")
