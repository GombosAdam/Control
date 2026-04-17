import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from common.database import Base


class Delegation(Base):
    __tablename__ = "delegations"
    __table_args__ = (
        Index("ix_delegation_active", "delegator_id", "is_active", "valid_from", "valid_until"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    delegator_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    delegate_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    workflow_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    valid_from: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    delegator = relationship("User", foreign_keys=[delegator_id], lazy="selectin")
    delegate = relationship("User", foreign_keys=[delegate_id], lazy="selectin")
