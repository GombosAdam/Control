from pydantic import BaseModel


class DepartmentCreate(BaseModel):
    name: str
    code: str
    parent_id: str | None = None
    manager_id: str | None = None


class DepartmentUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    parent_id: str | None = None
    manager_id: str | None = None


class BudgetMasterEntry(BaseModel):
    account_code: str
    account_name: str = ""
    is_active: bool = True


class BudgetMasterSet(BaseModel):
    entries: list[BudgetMasterEntry]
