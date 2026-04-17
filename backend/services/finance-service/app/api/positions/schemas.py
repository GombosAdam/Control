from pydantic import BaseModel
from typing import Optional


class PositionCreate(BaseModel):
    name: str
    department_id: str
    reports_to_id: str | None = None


class PositionUpdate(BaseModel):
    name: Optional[str] = None
    department_id: Optional[str] = None
    reports_to_id: Optional[str] = None
