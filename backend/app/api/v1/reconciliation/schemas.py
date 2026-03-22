from pydantic import BaseModel


class ManualMatchRequest(BaseModel):
    purchase_order_id: str
