import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class BudgetStatus(str, enum.Enum):
    draft = "draft"
    approved = "approved"
    locked = "locked"


class PnlCategory(str, enum.Enum):
    revenue = "revenue"
    cogs = "cogs"
    opex = "opex"
    depreciation = "depreciation"
    interest = "interest"
    tax = "tax"


class PlanType(str, enum.Enum):
    budget = "budget"
    forecast = "forecast"


class BudgetLine(Base):
    __tablename__ = "budget_lines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    department_id: Mapped[str] = mapped_column(String(36), ForeignKey("departments.id"), nullable=False)
    account_code: Mapped[str] = mapped_column(String(20), nullable=False)
    account_name: Mapped[str] = mapped_column(String(255), nullable=False)
    period: Mapped[str] = mapped_column(String(7), nullable=False)  # YYYY-MM
    planned_amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="HUF", nullable=False)
    status: Mapped[BudgetStatus] = mapped_column(SAEnum(BudgetStatus), default=BudgetStatus.draft, nullable=False)
    pnl_category: Mapped[str] = mapped_column(String(20), default="opex", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    plan_type: Mapped[str] = mapped_column(String(8), default="budget", nullable=False)
    scenario_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("scenarios.id"), nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    planning_period_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("planning_periods.id"), nullable=False
    )

    department = relationship("Department", back_populates="budget_lines", lazy="selectin")
    scenario = relationship("Scenario", lazy="selectin")
    planning_period = relationship("PlanningPeriod", lazy="selectin")
    creator = relationship("User", foreign_keys=[created_by], lazy="selectin")
    approver = relationship("User", foreign_keys=[approved_by], lazy="selectin")
