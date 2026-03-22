import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Float, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from common.database import Base


class AIEnrichment(Base):
    __tablename__ = "ai_enrichments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    invoice_id: Mapped[str] = mapped_column(String(36), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    enrichment_type: Mapped[str] = mapped_column(String(50), nullable=False)  # partner_detection, duplicate_check, budget_suggestion, po_suggestion, anomaly_detection
    result_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    accepted: Mapped[bool | None] = mapped_column(Boolean, nullable=True)  # None=pending, True=accepted, False=rejected
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
