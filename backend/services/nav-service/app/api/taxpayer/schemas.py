from pydantic import BaseModel


class TaxpayerValidateRequest(BaseModel):
    config_id: str
    tax_number: str


class TaxpayerValidatePartnerRequest(BaseModel):
    config_id: str
