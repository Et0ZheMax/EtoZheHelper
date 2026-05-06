from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    app: str


class KbStatsResponse(BaseModel):
    documents_count: int
    knowledge_base_dir: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10_000)
    session_id: int | None = None


class Source(BaseModel):
    title: str
    path: str
    score: float
    snippet: str
    metadata: dict[str, object] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    session_id: int
    answer: str
    sources: list[Source]
