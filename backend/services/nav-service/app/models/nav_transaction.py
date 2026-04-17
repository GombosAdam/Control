import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum


class NavOperation(str, enum.Enum):
    CREATE = "CREATE"
    MODIFY = "MODIFY"
    STORNO = "STORNO"
    ANNULMENT = "ANNULMENT"


class NavTransactionStatus(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    processing = "processing"
    done = "done"
    aborted = "aborted"
    error = "error"


class NavTransaction(Base):
    __tablename__ = "nav_transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nav_config_id: Mapped[str] = mapped_column(String(36), ForeignKey("nav_configs.id"), nullable=False)
    invoice_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("invoices.id"), nullable=True)
    transaction_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    operation: Mapped[NavOperation] = mapped_column(SAEnum(NavOperation), nullable=False)
    status: Mapped[NavTransactionStatus] = mapped_column(SAEnum(NavTransactionStatus), default=NavTransactionStatus.pending, nullable=False)
    request_xml: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_xml: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    invoice_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    nav_config = relationship("NavConfig", back_populates="transactions")
    invoice = relationship("Invoice", lazy="selectin")
