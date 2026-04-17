from pydantic import BaseModel
from typing import Optional


class NavConfigCreateRequest(BaseModel):
    company_tax_number: str
    company_name: str
    login: str
    password: str
    signature_key: str
    replacement_key: str
    environment: str = "test"


class NavConfigUpdateRequest(BaseModel):
    company_name: Optional[str] = None
    login: Optional[str] = None
    password: Optional[str] = None
    signature_key: Optional[str] = None
    replacement_key: Optional[str] = None
    environment: Optional[str] = None
    is_active: Optional[bool] = None
