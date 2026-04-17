import enum
from datetime import datetime
from sqlalchemy import String, Boolean, Integer, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from common.database import Base


class AccountType(str, enum.Enum):
    asset = "asset"
    liability = "liability"
    revenue = "revenue"
    expense = "expense"
    tax = "tax"


class AccountMaster(Base):
    __tablename__ = "account_master"

    code: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(255), nullable=True)
    account_type: Mapped[AccountType] = mapped_column(SAEnum(AccountType), nullable=False)
    pnl_category: Mapped[str | None] = mapped_column(String(20), nullable=True)
    parent_code: Mapped[str | None] = mapped_column(String(20), ForeignKey("account_master.code"), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_header: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    normal_side: Mapped[str | None] = mapped_column(String(6), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    parent = relationship("AccountMaster", remote_side="AccountMaster.code", lazy="selectin")
    children = relationship("AccountMaster", back_populates="parent", lazy="selectin")
