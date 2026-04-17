import uuid
import enum
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, DateTime, ForeignKey, Numeric, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from common.database import Base


class EntryType(str, enum.Enum):
    debit = "debit"
    credit = "credit"


class AccountingEntry(Base):
    __tablename__ = "accounting_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    invoice_id: Mapped[str] = mapped_column(String(36), ForeignKey("invoices.id"), nullable=False)
    purchase_order_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("purchase_orders.id"), nullable=True)
    account_code: Mapped[str] = mapped_column(String(20), nullable=False)
    department_id: Mapped[str] = mapped_column(String(36), ForeignKey("departments.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="HUF", nullable=False)
    period: Mapped[str] = mapped_column(String(7), nullable=False)  # YYYY-MM
    entry_type: Mapped[EntryType] = mapped_column(SAEnum(EntryType), nullable=False)
    posted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    posted_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    invoice = relationship("Invoice", lazy="selectin")
    purchase_order = relationship("PurchaseOrder", lazy="selectin")
    department = relationship("Department", lazy="selectin")
    poster = relationship("User", lazy="selectin")
