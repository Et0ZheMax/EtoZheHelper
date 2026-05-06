from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.kb.service import knowledge_base_service


def test_health():
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "app": "EtoZheHelper"}


def test_kb_stats():
    with TestClient(app) as client:
        response = client.get("/api/kb/stats")
    assert response.status_code == 200
    payload = response.json()
    assert payload["documents_count"] >= 1
    assert payload["knowledge_base_dir"] == str(get_settings().knowledge_base_dir.resolve())
    assert payload["domains"]["linux"] >= 1
    assert payload["types"]["runbook"] >= 1


def test_chat_returns_session_answer_sources_and_topic_plan():
    with TestClient(app) as client:
        response = client.post("/api/chat", json={"message": "Не работает DNS на Ubuntu", "session_id": None})
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload["session_id"], int)
    assert "answer" in payload and payload["answer"]
    assert "Похоже, это тема: `dns`" in payload["answer"]
    assert "resolvectl status" in payload["answer"]
    assert "getent hosts" in payload["answer"]
    assert "sources" in payload
    assert payload["sources"]


def test_kb_reload_picks_up_new_document():
    kb_dir = get_settings().knowledge_base_dir
    extra_doc = kb_dir / "windows.md"
    try:
        extra_doc.write_text("---\ntype: cheatsheet\ndomain: windows\n---\n\n# Windows DNS\n\nipconfig /displaydns", encoding="utf-8")
        with TestClient(app) as client:
            response = client.post("/api/kb/reload")
            stats_response = client.get("/api/kb/stats")
        assert response.status_code == 200
        assert response.json()["status"] == "reloaded"
        assert stats_response.status_code == 200
        assert stats_response.json()["domains"]["windows"] == 1
    finally:
        extra_doc.unlink(missing_ok=True)
        knowledge_base_service.clear()


def test_chat_unknown_session_returns_404():
    with TestClient(app) as client:
        response = client.post("/api/chat", json={"message": "hello", "session_id": 999999})
    assert response.status_code == 404


def test_chat_handles_empty_knowledge_base(tmp_path, monkeypatch):
    empty_kb = tmp_path / "empty_kb"
    empty_kb.mkdir()
    db_path = tmp_path / "test.db"

    monkeypatch.setenv("KNOWLEDGE_BASE_DIR", str(empty_kb))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    get_settings.cache_clear()
    knowledge_base_service.clear()

    try:
        with TestClient(app) as client:
            response = client.post("/api/chat", json={"message": "anything", "session_id": None})
        assert response.status_code == 200
        assert response.json()["sources"] == []
        assert "не нашлось" in response.json()["answer"]
    finally:
        get_settings.cache_clear()
        knowledge_base_service.clear()
