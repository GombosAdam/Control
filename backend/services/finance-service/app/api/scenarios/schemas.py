from pydantic import BaseModel


class ScenarioCreate(BaseModel):
    name: str
    description: str | None = None


class ScenarioCopy(BaseModel):
    source_scenario_id: str
    name: str
    description: str | None = None
    adjustment_pct: float = 0.0
    period: str | None = None
    department_id: str | None = None
