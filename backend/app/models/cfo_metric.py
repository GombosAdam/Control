import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Float, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class CfoMetric(Base):
    __tablename__ = "cfo_metrics"
    __table_args__ = (
        UniqueConstraint("metric_key", "period", name="uq_cfo_metric_key_period"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    metric_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    period: Mapped[str] = mapped_column(String(7), nullable=False, index=True)  # YYYY-MM
    value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="HUF")
    calculated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
