import re

from app.kb.models import KnowledgeDocument, SearchResult

TOKEN_RE = re.compile(r"[\wа-яА-ЯёЁ.-]+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text) if len(token.strip()) >= 2]


def _snippet(content: str, tokens: list[str], size: int = 320) -> str:
    if not content:
        return ""
    lower = content.lower()
    positions = [lower.find(token) for token in tokens if lower.find(token) >= 0]
    pos = min(positions) if positions else 0
    start = max(pos - size // 3, 0)
    end = min(start + size, len(content))
    snippet = content[start:end].strip()
    if start > 0:
        snippet = "…" + snippet
    if end < len(content):
        snippet += "…"
    return snippet


def search_documents(query: str, documents: list[KnowledgeDocument], limit: int = 5) -> list[SearchResult]:
    tokens = tokenize(query)
    if not tokens:
        return []

    results: list[SearchResult] = []
    for doc in documents:
        score = 0.0
        title = doc.title.lower()
        path = doc.path.lower()
        headings = " ".join(doc.headings).lower()
        tags_domain = " ".join([*doc.tags, doc.domain or ""]).lower()
        content = doc.content.lower()

        for token in tokens:
            if token in title:
                score += 5
            if token in headings:
                score += 3
            if token in tags_domain:
                score += 3
            if token in path:
                score += 2
            if token in content:
                score += 1

        if score > 0:
            results.append(
                SearchResult(
                    path=doc.path,
                    title=doc.title,
                    score=score,
                    snippet=_snippet(doc.content, tokens),
                    metadata=doc.metadata,
                )
            )

    return sorted(results, key=lambda item: (-item.score, item.title))[:limit]
