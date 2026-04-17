import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum


class NavEnvironment(str, enum.Enum):
    test = "test"
    production = "production"


class NavConfig(Base):
    __tablename__ = "nav_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_tax_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    login: Mapped[str] = mapped_column(String(100), nullable=False)
    password_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    signature_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    replacement_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    environment: Mapped[NavEnvironment] = mapped_column(SAEnum(NavEnvironment), default=NavEnvironment.test, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    transactions = relationship("NavTransaction", back_populates="nav_config", lazy="selectin")
    sync_logs = relationship("NavSyncLog", back_populates="nav_config", lazy="selectin")
