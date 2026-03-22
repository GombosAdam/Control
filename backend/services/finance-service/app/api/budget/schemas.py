from pydantic import BaseModel


class BudgetLineCreate(BaseModel):
    department_id: str
    account_code: str
    account_name: str
    period: str  # YYYY-MM
    planned_amount: float
    currency: str = "HUF"
    pnl_category: str = "opex"
    sort_order: int = 0
    plan_type: str = "budget"
    scenario_id: str | None = None


class BudgetLineUpdate(BaseModel):
    account_code: str | None = None
    account_name: str | None = None
    planned_amount: float | None = None
    pnl_category: str | None = None
    sort_order: int | None = None


class BulkLineIds(BaseModel):
    line_ids: list[str]


class BulkAdjust(BaseModel):
    line_ids: list[str]
    percentage: float


class CopyPeriod(BaseModel):
    source_period: str  # YYYY-MM
    target_period: str  # YYYY-MM
    department_id: str | None = None


class CreateYearPlan(BaseModel):
    year: int
    source_year: int | None = None
    adjustment_pct: float = 0.0
    department_id: str | None = None
    plan_type: str = "budget"
    scenario_id: str | None = None


class CopyToForecast(BaseModel):
    source_period: str | None = None
    department_id: str | None = None
    adjustment_pct: float = 0.0
    scenario_id: str | None = None


class AddComment(BaseModel):
    text: str
