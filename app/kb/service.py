from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock

from app.kb.loader import load_knowledge_base
from app.kb.models import KnowledgeDocument


@dataclass(frozen=True)
class KnowledgeBaseStats:
    documents_count: int
    knowledge_base_dir: str
    domains: dict[str, int] = field(default_factory=dict)
    types: dict[str, int] = field(default_factory=dict)
    risks: dict[str, int] = field(default_factory=dict)
    tags: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class KnowledgeBaseSnapshot:
    documents: list[KnowledgeDocument]
    stats: KnowledgeBaseStats


@dataclass(frozen=True)
class _CacheEntry:
    fingerprint: tuple[int, int]
    snapshot: KnowledgeBaseSnapshot


class KnowledgeBaseService:
    """Small in-memory cache for local Markdown knowledge base documents."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._cache: dict[str, _CacheEntry] = {}

    def get_knowledge_base(self, base_dir: str | Path, *, force_reload: bool = False) -> KnowledgeBaseSnapshot:
        root = Path(base_dir).expanduser().resolve()
        cache_key = str(root)
        fingerprint = self._fingerprint(root)

        with self._lock:
            cached = self._cache.get(cache_key)
            if not force_reload and cached and cached.fingerprint == fingerprint:
                return cached.snapshot

            documents = load_knowledge_base(root)
            # Re-read the fingerprint after loading so edits during the read do not leave
            # an obviously stale latest mtime/count in the cache metadata.
            refreshed_fingerprint = self._fingerprint(root)
            snapshot = KnowledgeBaseSnapshot(
                documents=documents,
                stats=self._build_stats(root, documents),
            )
            self._cache[cache_key] = _CacheEntry(fingerprint=refreshed_fingerprint, snapshot=snapshot)
            return snapshot

    def reload(self, base_dir: str | Path) -> KnowledgeBaseSnapshot:
        return self.get_knowledge_base(base_dir, force_reload=True)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    @staticmethod
    def _fingerprint(root: Path) -> tuple[int, int]:
        if not root.exists():
            return (0, 0)

        count = 0
        latest_mtime_ns = 0
        for md_path in root.rglob("*.md"):
            try:
                relative = md_path.relative_to(root)
                if any(part.startswith(".") for part in relative.parts):
                    continue
                stat = md_path.stat()
            except OSError:
                continue
            count += 1
            latest_mtime_ns = max(latest_mtime_ns, stat.st_mtime_ns)
        return (count, latest_mtime_ns)

    @staticmethod
    def _build_stats(root: Path, documents: list[KnowledgeDocument]) -> KnowledgeBaseStats:
        domains = Counter(doc.domain for doc in documents if doc.domain)
        types = Counter(doc.doc_type for doc in documents if doc.doc_type)
        risks = Counter(doc.risk for doc in documents if doc.risk)
        tags = Counter(tag for doc in documents for tag in doc.tags if tag)
        return KnowledgeBaseStats(
            documents_count=len(documents),
            knowledge_base_dir=str(root),
            domains=dict(sorted(domains.items())),
            types=dict(sorted(types.items())),
            risks=dict(sorted(risks.items())),
            tags=dict(sorted(tags.items())),
        )


knowledge_base_service = KnowledgeBaseService()
