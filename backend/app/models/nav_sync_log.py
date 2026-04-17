import uuid
from datetime import datetime, date
from sqlalchemy import String, Integer, DateTime, Date, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum


class NavSyncDirection(str, enum.Enum):
    inbound = "inbound"
    outbound = "outbound"


class NavSyncStatus(str, enum.Enum):
    running = "running"
    completed = "completed"
    error = "error"


class NavSyncLog(Base):
    __tablename__ = "nav_sync_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nav_config_id: Mapped[str] = mapped_column(String(36), ForeignKey("nav_configs.id"), nullable=False)
    direction: Mapped[NavSyncDirection] = mapped_column(SAEnum(NavSyncDirection), nullable=False)
    date_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    invoices_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    invoices_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    invoices_skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[NavSyncStatus] = mapped_column(SAEnum(NavSyncStatus), default=NavSyncStatus.running, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    nav_config = relationship("NavConfig", back_populates="sync_logs")
