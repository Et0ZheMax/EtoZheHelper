from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    app: str


class KbStatsResponse(BaseModel):
    documents_count: int
    knowledge_base_dir: str
    domains: dict[str, int] = Field(default_factory=dict)
    types: dict[str, int] = Field(default_factory=dict)
    risks: dict[str, int] = Field(default_factory=dict)
    tags: dict[str, int] = Field(default_factory=dict)


class KbReloadResponse(BaseModel):
    status: str
    documents_count: int


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


class KbDocumentSummary(BaseModel):
    path: str
    title: str
    domain: str | None = None
    doc_type: str | None = None
    risk: str | None = None
    tags: list[str] = Field(default_factory=list)
    snippet: str


class KbDocumentListResponse(BaseModel):
    items: list[KbDocumentSummary]
    total: int
    limit: int
    offset: int


class KbDocumentDetailResponse(BaseModel):
    path: str
    title: str
    content: str
    metadata: dict[str, object] = Field(default_factory=dict)
    headings: list[str] = Field(default_factory=list)
