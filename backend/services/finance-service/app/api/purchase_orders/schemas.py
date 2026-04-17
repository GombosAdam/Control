from pydantic import BaseModel, field_validator


class PurchaseOrderLineCreate(BaseModel):
    description: str
    quantity: float
    unit_price: float


class PurchaseOrderCreate(BaseModel):
    po_number: str | None = None
    department_id: str
    budget_line_id: str
    partner_id: str | None = None
    supplier_name: str
    supplier_tax_id: str | None = None
    lines: list[PurchaseOrderLineCreate]
    currency: str = "HUF"
    accounting_code: str
    description: str | None = None

    @field_validator("lines")
    @classmethod
    def at_least_one_line(cls, v):
        if not v:
            raise ValueError("At least one line item is required")
        return v


class PurchaseOrderUpdate(BaseModel):
    partner_id: str | None = None
    supplier_name: str | None = None
    supplier_tax_id: str | None = None
    amount: float | None = None
    accounting_code: str | None = None
    description: str | None = None


class POApprovalDecisionRequest(BaseModel):
    decision: str  # "approved" or "rejected"
    comment: str | None = None


class GoodsReceiptCreate(BaseModel):
    received_date: str
    notes: str | None = None
