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
