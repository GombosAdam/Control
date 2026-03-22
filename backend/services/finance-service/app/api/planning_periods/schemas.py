from pydantic import BaseModel


class PlanningPeriodCreate(BaseModel):
    name: str
    year: int
    start_month: int = 1
    end_month: int = 12
    plan_type: str = "budget"
    scenario_id: str | None = None
    source_period_id: str | None = None
    adjustment_pct: float = 0.0
    department_id: str | None = None
