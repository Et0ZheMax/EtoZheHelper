from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agent.assistant import DeterministicAssistant
from app.audit.logger import log_event
from app.config import Settings, get_settings
from app.db import get_db
from app.kb.loader import load_knowledge_base
from app.models import ChatMessage, ChatSession
from app.schemas import ChatRequest, ChatResponse, HealthResponse, KbStatsResponse, Source

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(status="ok", app=settings.app_name)


@router.get("/kb/stats", response_model=KbStatsResponse)
def kb_stats(settings: Settings = Depends(get_settings)) -> KbStatsResponse:
    documents = load_knowledge_base(settings.knowledge_base_dir)
    return KbStatsResponse(documents_count=len(documents), knowledge_base_dir=str(settings.knowledge_base_dir))


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

    user_message = ChatMessage(session_id=session.id, role="user", content=payload.message)
    db.add(user_message)
    db.commit()
    log_event(db, "user_message_received", {"session_id": session.id, "message_length": len(payload.message)})

    documents = load_knowledge_base(settings.knowledge_base_dir)
    assistant = DeterministicAssistant(documents=documents, max_results=settings.max_search_results)
    answer, results = assistant.answer(payload.message)
    log_event(db, "kb_search_executed", {"session_id": session.id, "query_length": len(payload.message), "results_count": len(results)})

    assistant_message = ChatMessage(session_id=session.id, role="assistant", content=answer)
    db.add(assistant_message)
    db.commit()
    log_event(db, "assistant_answer_generated", {"session_id": session.id, "answer_length": len(answer)})

    return ChatResponse(
        session_id=session.id,
        answer=answer,
        sources=[Source(title=result.title, path=result.path, score=result.score, snippet=result.snippet, metadata=result.metadata) for result in results],
    )
