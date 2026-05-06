import re

from app.kb.models import KnowledgeDocument, SearchResult

TOKEN_RE = re.compile(r"[\wа-яА-ЯёЁ]+", re.UNICODE)
WHITESPACE_RE = re.compile(r"\s+")

SYNONYMS = {
    "dns": ["resolvectl", "resolved", "dig", "getent", "nsswitch", "резолвится", "резолвить", "резолв"],
    "порт": ["port", "nc", "ss", "listen", "connection refused", "timeout"],
    "nginx": ["502", "bad gateway", "upstream", "reverse proxy"],
    "место": ["disk", "df", "du", "inode", "no space left"],
    "docker": ["compose", "container", "volume", "logs"],
}


def tokenize(text: str) -> list[str]:
    seen: set[str] = set()
    tokens: list[str] = []
    for token in TOKEN_RE.findall(text.casefold()):
        cleaned = token.strip("_-")
        if len(cleaned) < 2 or cleaned in seen:
            continue
        seen.add(cleaned)
        tokens.append(cleaned)
    return tokens


def expand_query_terms(query: str) -> list[str]:
    tokens = tokenize(query)
    terms = list(tokens)
    seen = set(terms)
    for key, hints in SYNONYMS.items():
        key_tokens = tokenize(key)
        hint_tokens = tokenize(" ".join(hints))
        all_group_tokens = set(key_tokens + hint_tokens)
        if all_group_tokens.intersection(tokens):
            for term in key_tokens + hint_tokens:
                if term not in seen:
                    seen.add(term)
                    terms.append(term)
    return terms


def _normalize_whitespace(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text).strip()


def _matching_section(content: str, terms: list[str]) -> str | None:
    heading_matches = list(re.finditer(r"^#{1,6}\s+.+$", content, re.MULTILINE))
    if not heading_matches:
        return None

    lowered_terms = [term.casefold() for term in terms]
    for index, match in enumerate(heading_matches):
        next_start = heading_matches[index + 1].start() if index + 1 < len(heading_matches) else len(content)
        section = content[match.start():next_start]
        section_lower = section.casefold()
        heading_lower = match.group(0).casefold()
        if any(term in heading_lower for term in lowered_terms) or any(term in section_lower for term in lowered_terms):
            return section
    return None


def _snippet(content: str, terms: list[str], size: int = 400) -> str:
    if not content:
        return ""
    source = _matching_section(content, terms) or content
    lowered = source.casefold()
    positions = [lowered.find(term) for term in terms if lowered.find(term) >= 0]
    pos = min(positions) if positions else 0
    start = max(pos - size // 3, 0)
    end = min(start + size, len(source))
    snippet = _normalize_whitespace(source[start:end])
    if start > 0:
        snippet = "…" + snippet
    if end < len(source):
        snippet += "…"
    return snippet[: size + 2]


def _matched_terms(doc: KnowledgeDocument, terms: list[str]) -> list[str]:
    searchable = " ".join(
        [
            doc.title,
            doc.path,
            " ".join(doc.headings),
            " ".join(doc.tags),
            doc.domain or "",
            doc.doc_type or "",
            doc.risk or "",
            doc.content,
        ]
    ).casefold()
    return [term for term in terms if term in searchable]


def search_documents(query: str, documents: list[KnowledgeDocument], limit: int = 5) -> list[SearchResult]:
    base_tokens = tokenize(query)
    terms = expand_query_terms(query)
    if not terms:
        return []

    results: list[SearchResult] = []
    for doc in documents:
        score = 0.0
        title = doc.title.casefold()
        path = doc.path.casefold()
        headings = " ".join(doc.headings).casefold()
        tags_domain = " ".join([*doc.tags, doc.domain or "", doc.doc_type or "", doc.risk or ""]).casefold()
        content = doc.content.casefold()
        matched_terms = _matched_terms(doc, terms)

        for term in terms:
            weight = 1.0 if term in base_tokens else 0.35
            if term in title:
                score += 5 * weight
            if term in headings:
                score += 3 * weight
            if term in tags_domain:
                score += 3 * weight
            if term in path:
                score += 2 * weight
            if term in content:
                score += 1 * weight

        if score > 0:
            metadata = dict(doc.metadata)
            metadata["matched_terms"] = matched_terms
            results.append(
                SearchResult(
                    path=doc.path,
                    title=doc.title,
                    score=round(score, 3),
                    snippet=_snippet(doc.content, terms),
                    metadata=metadata,
                )
            )

    return sorted(results, key=lambda item: (-item.score, item.title))[:limit]
