from pydantic import BaseModel
from typing import Optional, List
from datetime import date

class InvoiceResponse(BaseModel):
    id: str
    invoice_number: Optional[str] = None
    partner_id: Optional[str] = None
    partner_name: Optional[str] = None
    status: str
    invoice_date: Optional[str] = None
    fulfillment_date: Optional[str] = None
    due_date: Optional[str] = None
    payment_method: Optional[str] = None
    net_amount: Optional[float] = None
    vat_rate: Optional[float] = None
    vat_amount: Optional[float] = None
    gross_amount: Optional[float] = None
    currency: str = "HUF"
    original_filename: str
    ocr_confidence: Optional[float] = None
    is_duplicate: bool = False
    similarity_score: Optional[float] = None
    created_at: str
    updated_at: str

class InvoiceUpdateRequest(BaseModel):
    invoice_number: Optional[str] = None
    partner_id: Optional[str] = None
    invoice_date: Optional[date] = None
    fulfillment_date: Optional[date] = None
    due_date: Optional[date] = None
    payment_method: Optional[str] = None
    net_amount: Optional[float] = None
    vat_rate: Optional[float] = None
    vat_amount: Optional[float] = None
    gross_amount: Optional[float] = None
    currency: Optional[str] = None

class InvoiceListResponse(BaseModel):
    items: List[InvoiceResponse]
    total: int
    page: int
    limit: int
    pages: int
