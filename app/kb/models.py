from dataclasses import dataclass, field


@dataclass(frozen=True)
class KnowledgeDocument:
    path: str
    title: str
    content: str
    headings: list[str] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    domain: str | None = None
    doc_type: str | None = None
    risk: str | None = None
    requires_root: bool = False


@dataclass(frozen=True)
class SearchResult:
    path: str
    title: str
    score: float
    snippet: str
    metadata: dict[str, object] = field(default_factory=dict)
