from fastapi.testclient import TestClient

from app.main import app


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
    assert payload["knowledge_base_dir"] == "knowledge_base"


def test_chat_returns_session_answer_and_sources():
    with TestClient(app) as client:
        response = client.post("/api/chat", json={"message": "Не работает DNS на Ubuntu", "session_id": None})
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload["session_id"], int)
    assert "answer" in payload and payload["answer"]
    assert "sources" in payload
    assert payload["sources"]
