from pydantic import BaseModel


class PurchaseOrderCreate(BaseModel):
    po_number: str | None = None
    department_id: str
    budget_line_id: str
    supplier_name: str
    supplier_tax_id: str | None = None
    amount: float
    currency: str = "HUF"
    accounting_code: str
    description: str | None = None


class PurchaseOrderUpdate(BaseModel):
    supplier_name: str | None = None
    supplier_tax_id: str | None = None
    amount: float | None = None
    description: str | None = None


class POApprovalDecisionRequest(BaseModel):
    decision: str  # "approved" or "rejected"
    comment: str | None = None
