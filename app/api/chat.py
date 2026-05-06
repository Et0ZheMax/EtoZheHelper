from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.agent.assistant import DeterministicAssistant
from app.audit.logger import log_event
from app.config import Settings, get_settings
from app.db import get_db
from app.kb.search import search_documents
from app.kb.service import knowledge_base_service
from app.models import ChatMessage, ChatSession, utcnow
from app.schemas import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    KbDocumentDetailResponse,
    KbDocumentListResponse,
    KbDocumentSummary,
    KbReloadResponse,
    KbStatsResponse,
    Source,
)

router = APIRouter()


def _short_snippet(content: str, limit: int = 400) -> str:
    normalized = " ".join(content.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def _matches_filter(value: str | None, expected: str | None) -> bool:
    if expected is None or expected == "":
        return True
    return (value or "").casefold() == expected.casefold()


def _document_summaries(documents, q: str | None) -> list[KbDocumentSummary]:
    if q:
        results = search_documents(q, documents, limit=len(documents) or 1)
        snippets = {result.path: result.snippet for result in results}
        docs_by_path = {doc.path: doc for doc in documents}
        seen_paths: set[str] = set()
        ordered_docs = []
        for result in results:
            if result.path in seen_paths or result.path not in docs_by_path:
                continue
            seen_paths.add(result.path)
            ordered_docs.append(docs_by_path[result.path])
    else:
        snippets = {}
        seen_paths: set[str] = set()
        ordered_docs = []
        for doc in sorted(documents, key=lambda item: item.path):
            if doc.path in seen_paths:
                continue
            seen_paths.add(doc.path)
            ordered_docs.append(doc)

    return [
        KbDocumentSummary(
            path=doc.path,
            title=doc.title,
            domain=doc.domain,
            doc_type=doc.doc_type,
            risk=doc.risk,
            tags=doc.tags,
            snippet=snippets.get(doc.path) or _short_snippet(doc.content),
        )
        for doc in ordered_docs
    ]


@router.get("/health", response_model=HealthResponse)
def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(status="ok", app=settings.app_name)


@router.get("/kb/stats", response_model=KbStatsResponse)
def kb_stats(settings: Settings = Depends(get_settings)) -> KbStatsResponse:
    snapshot = knowledge_base_service.get_knowledge_base(settings.knowledge_base_dir)
    return KbStatsResponse(
        documents_count=snapshot.stats.documents_count,
        knowledge_base_dir=snapshot.stats.knowledge_base_dir,
        domains=snapshot.stats.domains,
        types=snapshot.stats.types,
        risks=snapshot.stats.risks,
        tags=snapshot.stats.tags,
    )


@router.post("/kb/reload", response_model=KbReloadResponse)
def kb_reload(settings: Settings = Depends(get_settings)) -> KbReloadResponse:
    try:
        snapshot = knowledge_base_service.reload(settings.knowledge_base_dir)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Knowledge base reload failed: {exc}") from exc
    return KbReloadResponse(status="reloaded", documents_count=snapshot.stats.documents_count)


@router.get("/kb/documents", response_model=KbDocumentListResponse)
def kb_documents(
    q: str | None = Query(default=None, max_length=500),
    domain: str | None = Query(default=None, max_length=100),
    doc_type: str | None = Query(default=None, max_length=100),
    risk: str | None = Query(default=None, max_length=100),
    tag: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    settings: Settings = Depends(get_settings),
) -> KbDocumentListResponse:
    snapshot = knowledge_base_service.get_knowledge_base(settings.knowledge_base_dir)
    filtered = [
        doc
        for doc in snapshot.documents
        if _matches_filter(doc.domain, domain)
        and _matches_filter(doc.doc_type, doc_type)
        and _matches_filter(doc.risk, risk)
        and (not tag or tag.casefold() in {item.casefold() for item in doc.tags})
    ]
    summaries = _document_summaries(filtered, q)
    total = len(summaries)
    return KbDocumentListResponse(items=summaries[offset : offset + limit], total=total, limit=limit, offset=offset)


@router.get("/kb/document", response_model=KbDocumentDetailResponse)
def kb_document(path: str = Query(min_length=1, max_length=1000), settings: Settings = Depends(get_settings)) -> KbDocumentDetailResponse:
    normalized = path.replace("\\", "/")
    parts = [part for part in normalized.split("/") if part]
    if normalized.startswith("/") or ".." in parts or any(part.startswith(".") for part in parts):
        raise HTTPException(status_code=404, detail="Knowledge base document not found")

    snapshot = knowledge_base_service.get_knowledge_base(settings.knowledge_base_dir)
    for doc in snapshot.documents:
        if doc.path == normalized:
            return KbDocumentDetailResponse(
                path=doc.path,
                title=doc.title,
                content=doc.content,
                metadata=doc.metadata,
                headings=doc.headings,
            )
    raise HTTPException(status_code=404, detail="Knowledge base document not found")


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> ChatResponse:
    session = db.get(ChatSession, payload.session_id) if payload.session_id else None
    if payload.session_id and session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    if session is None:
        title = payload.message.strip().replace("\n", " ")[:80] or "New chat"
        session = ChatSession(title=title)
        db.add(session)
        db.commit()
        db.refresh(session)

    session.updated_at = utcnow()
    user_message = ChatMessage(session_id=session.id, role="user", content=payload.message)
    db.add(user_message)
    db.commit()
    log_event(db, "user_message_received", {"session_id": session.id, "message_length": len(payload.message)})

    snapshot = knowledge_base_service.get_knowledge_base(settings.knowledge_base_dir)
    assistant = DeterministicAssistant(documents=snapshot.documents, max_results=settings.max_search_results)
    answer, results = assistant.answer(payload.message)
    log_event(db, "kb_search_executed", {"session_id": session.id, "query_length": len(payload.message), "results_count": len(results)})

    session.updated_at = utcnow()
    assistant_message = ChatMessage(session_id=session.id, role="assistant", content=answer)
    db.add(assistant_message)
    db.commit()
    log_event(db, "assistant_answer_generated", {"session_id": session.id, "answer_length": len(answer)})

    return ChatResponse(
        session_id=session.id,
        answer=answer,
        sources=[Source(title=result.title, path=result.path, score=result.score, snippet=result.snippet, metadata=result.metadata) for result in results],
    )
