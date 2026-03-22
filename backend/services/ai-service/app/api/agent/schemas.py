from pydantic import BaseModel


class AgentRequest(BaseModel):
    question: str


class ToolCallLog(BaseModel):
    tool: str
    params: dict
    latency_ms: int


class AgentResponse(BaseModel):
    answer: str
    tool_calls: list[ToolCallLog] = []
    response_time_ms: int | None = None
    model_used: str | None = None
    error: str | None = None
    chart_data: dict | None = None
