import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Float, Integer, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum

class PartnerType(str, enum.Enum):
    supplier = "supplier"
    customer = "customer"
    both = "both"

class Partner(Base):
    __tablename__ = "partners"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    tax_number: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True, index=True)
    bank_account: Mapped[str | None] = mapped_column(String(50), nullable=True)
    partner_type: Mapped[PartnerType] = mapped_column(SAEnum(PartnerType), default=PartnerType.supplier, nullable=False)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    auto_detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    invoice_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    invoices = relationship("Invoice", back_populates="partner", lazy="selectin")
