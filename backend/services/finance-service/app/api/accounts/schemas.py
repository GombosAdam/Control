from pydantic import BaseModel


class AccountCreate(BaseModel):
    code: str
    name: str
    name_en: str | None = None
    account_type: str
    pnl_category: str | None = None
    parent_code: str | None = None
    sort_order: int = 0
    is_active: bool = True
    is_header: bool = False
    normal_side: str | None = None


class AccountUpdate(BaseModel):
    name: str | None = None
    name_en: str | None = None
    account_type: str | None = None
    pnl_category: str | None = None
    parent_code: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None
    is_header: bool | None = None
    normal_side: str | None = None
