from pydantic import BaseModel
from typing import Optional

class PartnerCreateRequest(BaseModel):
    name: str
    tax_number: Optional[str] = None
    bank_account: Optional[str] = None
    partner_type: str = "supplier"
    address: Optional[str] = None
    contact_email: Optional[str] = None

class PartnerUpdateRequest(BaseModel):
    name: Optional[str] = None
    tax_number: Optional[str] = None
    bank_account: Optional[str] = None
    partner_type: Optional[str] = None
    address: Optional[str] = None
    contact_email: Optional[str] = None
