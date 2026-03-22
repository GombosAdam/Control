import uuid
from datetime import datetime, date
from sqlalchemy import String, Boolean, DateTime, Date, Float, Integer, Text, ForeignKey, JSON, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from common.database import Base
import enum

class InvoiceStatus(str, enum.Enum):
    uploaded = "uploaded"
    ocr_processing = "ocr_processing"
    ocr_done = "ocr_done"
    extracting = "extracting"
    pending_review = "pending_review"
    in_approval = "in_approval"
    approved = "approved"
    awaiting_match = "awaiting_match"
    matched = "matched"
    posted = "posted"
    rejected = "rejected"
    error = "error"


class MatchStatus(str, enum.Enum):
    unmatched = "unmatched"
    matched = "matched"
    mismatch = "mismatch"
    posted = "posted"

class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    invoice_number: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    partner_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("partners.id"), nullable=True)
    status: Mapped[InvoiceStatus] = mapped_column(SAEnum(InvoiceStatus), default=InvoiceStatus.uploaded, nullable=False, index=True)

    # Dates
    invoice_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    fulfillment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Payment
    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Amounts
    net_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    vat_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    vat_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    gross_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="HUF", nullable=False)

    # File
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    stored_filepath: Mapped[str] = mapped_column(String(500), nullable=False)

    # OCR
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Duplicate detection
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    duplicate_of_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("invoices.id"), nullable=True)
    similarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    vector_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Controlling fields
    purchase_order_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("purchase_orders.id"), nullable=True)
    match_status: Mapped[str] = mapped_column(String(20), default="unmatched", nullable=False)
    accounting_code: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # AI enrichment fields
    suggested_accounting_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    anomaly_flags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relations
    reviewed_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    uploaded_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    partner = relationship("Partner", back_populates="invoices", lazy="selectin")
    lines = relationship("InvoiceLine", back_populates="invoice", cascade="all, delete-orphan", lazy="selectin")
    extraction_result = relationship("ExtractionResult", back_populates="invoice", uselist=False, lazy="selectin")
    purchase_order = relationship("PurchaseOrder", lazy="selectin")

class InvoiceLine(Base):
    __tablename__ = "invoice_lines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    invoice_id: Mapped[str] = mapped_column(String(36), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    net_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    vat_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    vat_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    gross_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    invoice = relationship("Invoice", back_populates="lines")
