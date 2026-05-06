from pathlib import Path
import re
from typing import Any

from app.kb.models import KnowledgeDocument

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
HEADING_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*$", re.MULTILINE)


def parse_scalar(value: str) -> Any:
    raw = value.strip().strip('"').strip("'")
    lowered = raw.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if not inner:
            return []
        return [item.strip().strip('"').strip("'") for item in inner.split(",") if item.strip()]
    return raw


def parse_frontmatter(text: str) -> tuple[dict[str, object], str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text

    metadata: dict[str, object] = {}
    for line in match.group(1).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip()
        if key:
            metadata[key] = parse_scalar(value)
    return metadata, text[match.end():]


def extract_headings(content: str) -> list[str]:
    return [match.group(2).strip() for match in HEADING_RE.finditer(content)]


def document_title(path: Path, headings: list[str]) -> str:
    return headings[0] if headings else path.stem.replace("-", " ").replace("_", " ").title()


def _is_hidden(path: Path) -> bool:
    return any(part.startswith(".") for part in path.parts)


def load_knowledge_base(base_dir: str | Path) -> list[KnowledgeDocument]:
    root = Path(base_dir)
    if not root.exists():
        return []

    documents: list[KnowledgeDocument] = []
    for md_path in sorted(root.rglob("*.md")):
        relative = md_path.relative_to(root)
        if _is_hidden(relative):
            continue
        try:
            raw = md_path.read_text(encoding="utf-8")
            metadata, content = parse_frontmatter(raw)
            headings = extract_headings(content)
            tags_value = metadata.get("tags", [])
            tags = [str(tag) for tag in tags_value] if isinstance(tags_value, list) else []
            doc = KnowledgeDocument(
                path=relative.as_posix(),
                title=document_title(md_path, headings),
                content=content.strip(),
                headings=headings,
                metadata=metadata,
                tags=tags,
                domain=str(metadata["domain"]) if metadata.get("domain") is not None else None,
                doc_type=str(metadata["type"]) if metadata.get("type") is not None else None,
                risk=str(metadata["risk"]) if metadata.get("risk") is not None else None,
                requires_root=bool(metadata.get("requires_root", False)),
            )
            documents.append(doc)
        except (OSError, UnicodeDecodeError):
            continue
    return documents
