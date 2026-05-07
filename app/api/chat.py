from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agent.assistant import DeterministicAssistant
from app.audit.logger import log_event
from app.config import Settings, get_settings
from app.db import get_db
from app.kb.search import search_documents
from app.kb.service import knowledge_base_service
from app.models import ChatMessage, ChatSession, Host, utcnow
from app.schemas import (
    ActionProposalResponse,
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
    ChatSessionCreateRequest,
    ChatSessionDeleteResponse,
    ChatSessionDetailResponse,
    ChatSessionHostUpdateRequest,
    ChatSessionListResponse,
    ChatSessionResponse,
    ChatSessionSummary,
    ChatSessionUpdateRequest,
    HealthResponse,
    KbDocumentDetailResponse,
    KbDocumentListResponse,
    KbDocumentSummary,
    KbReloadResponse,
    KbStatsResponse,
    Source,
)

router = APIRouter()


DEFAULT_SESSION_TITLE = "New investigation"
MAX_SESSION_TITLE_LENGTH = 120
SESSION_PREVIEW_LENGTH = 120


def _normalize_session_title(title: str | None, default: str = DEFAULT_SESSION_TITLE) -> str:
    normalized = (title or "").strip()
    if not normalized:
        normalized = default
    return normalized[:MAX_SESSION_TITLE_LENGTH]


def _preview_text(content: str | None, limit: int = SESSION_PREVIEW_LENGTH) -> str:
    normalized = " ".join((content or "").split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def _session_response(session: ChatSession) -> ChatSessionResponse:
    return ChatSessionResponse(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        host_id=session.host_id,
    )


def _session_or_404(db: Session, session_id: int) -> ChatSession:
    session = db.get(ChatSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return session


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


@router.get("/chat/sessions", response_model=ChatSessionListResponse)
def chat_sessions(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ChatSessionListResponse:
    total = db.scalar(select(func.count(ChatSession.id))) or 0
    sessions = (
        db.query(ChatSession)
        .order_by(ChatSession.updated_at.desc(), ChatSession.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    items: list[ChatSessionSummary] = []
    for session in sessions:
        messages_count = db.query(func.count(ChatMessage.id)).filter(ChatMessage.session_id == session.id).scalar() or 0
        latest_message = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session.id)
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .first()
        )
        items.append(
            ChatSessionSummary(
                id=session.id,
                title=session.title,
                created_at=session.created_at,
                updated_at=session.updated_at,
                host_id=session.host_id,
                messages_count=messages_count,
                preview=_preview_text(latest_message.content if latest_message else ""),
            )
        )
    return ChatSessionListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/chat/session/{session_id}", response_model=ChatSessionDetailResponse)
def chat_session_detail(session_id: int, db: Session = Depends(get_db)) -> ChatSessionDetailResponse:
    session = _session_or_404(db, session_id)
    log_event(db, "chat_session_opened", {"session_id": session.id})
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        .all()
    )
    return ChatSessionDetailResponse(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        host_id=session.host_id,
        messages=[
            ChatMessageResponse(id=item.id, role=item.role, content=item.content, created_at=item.created_at)
            for item in messages
        ],
    )


@router.post("/chat/session", response_model=ChatSessionResponse)
def create_chat_session(payload: ChatSessionCreateRequest, db: Session = Depends(get_db)) -> ChatSessionResponse:
    session = ChatSession(title=_normalize_session_title(payload.title))
    db.add(session)
    db.commit()
    db.refresh(session)
    log_event(db, "chat_session_created", {"session_id": session.id, "title": session.title})
    return _session_response(session)


@router.patch("/chat/session/{session_id}", response_model=ChatSessionResponse)
def update_chat_session(session_id: int, payload: ChatSessionUpdateRequest, db: Session = Depends(get_db)) -> ChatSessionResponse:
    session = _session_or_404(db, session_id)
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="Session title must not be empty")
    session.title = title[:MAX_SESSION_TITLE_LENGTH]
    session.updated_at = utcnow()
    db.add(session)
    db.commit()
    db.refresh(session)
    log_event(db, "chat_session_renamed", {"session_id": session.id, "title": session.title})
    return _session_response(session)


@router.patch("/chat/session/{session_id}/host", response_model=ChatSessionResponse)
def set_chat_session_host(session_id: int, payload: ChatSessionHostUpdateRequest, db: Session = Depends(get_db)) -> ChatSessionResponse:
    session = _session_or_404(db, session_id)
    if payload.host_id is not None and db.get(Host, payload.host_id) is None:
        raise HTTPException(status_code=404, detail="Host not found")
    session.host_id = payload.host_id
    session.updated_at = utcnow()
    db.add(session)
    db.commit()
    db.refresh(session)
    log_event(db, "chat_session_host_set", {"session_id": session.id, "host_id": session.host_id})
    return _session_response(session)


@router.delete("/chat/session/{session_id}", response_model=ChatSessionDeleteResponse)
def delete_chat_session(session_id: int, db: Session = Depends(get_db)) -> ChatSessionDeleteResponse:
    session = _session_or_404(db, session_id)
    db.query(ChatMessage).filter(ChatMessage.session_id == session.id).delete(synchronize_session=False)
    db.delete(session)
    db.commit()
    log_event(db, "chat_session_deleted", {"session_id": session_id})
    return ChatSessionDeleteResponse(status="deleted", id=session_id)


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> ChatResponse:
    session = db.get(ChatSession, payload.session_id) if payload.session_id else None
    if payload.session_id and session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    if session is None:
        title = _normalize_session_title(payload.message.strip().replace("\n", " "), default=DEFAULT_SESSION_TITLE)
        session = ChatSession(title=title)
        db.add(session)
        db.commit()
        db.refresh(session)
        log_event(db, "chat_session_created", {"session_id": session.id, "title": session.title})

    session.updated_at = utcnow()
    user_message = ChatMessage(session_id=session.id, role="user", content=payload.message)
    db.add(user_message)
    db.commit()
    log_event(db, "user_message_received", {"session_id": session.id, "message_length": len(payload.message)})

    snapshot = knowledge_base_service.get_knowledge_base(settings.knowledge_base_dir)
    assistant = DeterministicAssistant(documents=snapshot.documents, max_results=settings.max_search_results)
    answer, results = assistant.answer(payload.message)
    action_proposals = assistant.suggest_actions(payload.message)
    log_event(db, "kb_search_executed", {"session_id": session.id, "query_length": len(payload.message), "results_count": len(results)})

    session.updated_at = utcnow()
    assistant_message = ChatMessage(session_id=session.id, role="assistant", content=answer)
    db.add(assistant_message)
    db.commit()
    log_event(db, "assistant_answer_generated", {"session_id": session.id, "answer_length": len(answer), "actions_count": len(action_proposals)})

    return ChatResponse(
        session_id=session.id,
        answer=answer,
        sources=[Source(title=result.title, path=result.path, score=result.score, snippet=result.snippet, metadata=result.metadata) for result in results],
        actions=[
            ActionProposalResponse(
                action=proposal.action,
                label=proposal.label,
                category=proposal.category,
                risk=proposal.risk,
                read_only=proposal.read_only,
                requires_approval=proposal.requires_approval,
                needs_sudo=proposal.needs_sudo,
                execution_enabled=proposal.execution_enabled,
                command_preview=proposal.command_preview,
                params=proposal.params,
                warnings=proposal.warnings,
            )
            for proposal in action_proposals
        ],
    )
