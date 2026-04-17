from pydantic import BaseModel
from typing import List


class SubmitRequest(BaseModel):
    invoice_id: str
    config_id: str


class SubmitBatchRequest(BaseModel):
    invoice_ids: List[str]
    config_id: str
