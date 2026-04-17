import uuid
from datetime import datetime, date
from sqlalchemy import String, Float, Text, DateTime, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from common.database import Base


class GoodsReceipt(Base):
    __tablename__ = "goods_receipts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    gr_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    purchase_order_id: Mapped[str] = mapped_column(String(36), ForeignKey("purchase_orders.id"), unique=True, nullable=False)
    received_date: Mapped[date] = mapped_column(Date, nullable=False)
    received_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    purchase_order = relationship("PurchaseOrder", back_populates="goods_receipt")
    receiver = relationship("User", lazy="selectin")
    lines = relationship("GoodsReceiptLine", back_populates="goods_receipt", cascade="all, delete-orphan", lazy="selectin")


class GoodsReceiptLine(Base):
    __tablename__ = "goods_receipt_lines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    goods_receipt_id: Mapped[str] = mapped_column(String(36), ForeignKey("goods_receipts.id", ondelete="CASCADE"), nullable=False)
    purchase_order_line_id: Mapped[str] = mapped_column(String(36), ForeignKey("purchase_order_lines.id"), nullable=False)
    quantity_received: Mapped[float] = mapped_column(Float, nullable=False)

    goods_receipt = relationship("GoodsReceipt", back_populates="lines")
    purchase_order_line = relationship("PurchaseOrderLine", lazy="selectin")
