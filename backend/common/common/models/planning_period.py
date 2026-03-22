import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from common.database import Base


class PlanningPeriod(Base):
    __tablename__ = "planning_periods"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    start_month: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    end_month: Mapped[int] = mapped_column(Integer, nullable=False, default=12)
    plan_type: Mapped[str] = mapped_column(String(8), nullable=False, default="budget")
    scenario_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("scenarios.id"), nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    scenario = relationship("Scenario", lazy="selectin")
    creator = relationship("User", lazy="selectin")
