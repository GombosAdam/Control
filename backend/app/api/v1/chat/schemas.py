from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str
    sql: str | None = None
    error: str | None = None
    row_count: int | None = None
    response_time_ms: int | None = None
    sql_generation_ms: int | None = None
    retry_count: int = 0
    model_used: str | None = None
