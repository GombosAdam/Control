from pydantic import BaseModel
from typing import Optional

class UserCreateRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: str = "reviewer"

class UserUpdateRequest(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class SettingUpdateRequest(BaseModel):
    value: str
