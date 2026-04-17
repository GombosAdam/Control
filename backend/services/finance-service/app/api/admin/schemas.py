from pydantic import BaseModel
from typing import Optional

class UserCreateRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: str = "reviewer"
    department_id: str | None = None
    position_id: str | None = None

class UserUpdateRequest(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    department_id: Optional[str] = None
    reports_to: Optional[str] = None

class SettingUpdateRequest(BaseModel):
    value: str
