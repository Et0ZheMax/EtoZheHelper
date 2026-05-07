from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import ChatMessage, ChatSession


def _create_session(client: TestClient, title: str = "Test investigation") -> dict:
    response = client.post("/api/chat/session", json={"title": title})
    assert response.status_code == 200
    return response.json()


def test_create_session_and_list_returns_created_session():
    with TestClient(app) as client:
        created = _create_session(client, "API list investigation")
        response = client.get("/api/chat/sessions")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 1
    assert payload["limit"] == 50
    assert payload["offset"] == 0
    matching = [item for item in payload["items"] if item["id"] == created["id"]]
    assert matching
    assert matching[0]["title"] == "API list investigation"
    assert matching[0]["messages_count"] == 0
    assert matching[0]["preview"] == ""


def test_session_detail_returns_messages():
    with TestClient(app) as client:
        created = _create_session(client, "Detail messages investigation")
        chat_response = client.post("/api/chat", json={"message": "Не работает DNS на Ubuntu", "session_id": created["id"]})
        response = client.get(f"/api/chat/session/{created['id']}")

    assert chat_response.status_code == 200
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == created["id"]
    assert payload["title"] == "Detail messages investigation"
    assert [message["role"] for message in payload["messages"]] == ["user", "assistant"]
    assert payload["messages"][0]["content"] == "Не работает DNS на Ubuntu"


def test_patch_session_renames_and_trims_title():
    with TestClient(app) as client:
        created = _create_session(client, "Old title")
        response = client.patch(f"/api/chat/session/{created['id']}", json={"title": "  DNS Ubuntu shortname issue  "})

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == created["id"]
    assert payload["title"] == "DNS Ubuntu shortname issue"


def test_delete_session_deletes_session_and_messages():
    with TestClient(app) as client:
        created = _create_session(client, "Delete investigation")
        chat_response = client.post("/api/chat", json={"message": "Docker container conflict", "session_id": created["id"]})
        response = client.delete(f"/api/chat/session/{created['id']}")
        detail_response = client.get(f"/api/chat/session/{created['id']}")

    assert chat_response.status_code == 200
    assert response.status_code == 200
    assert response.json() == {"status": "deleted", "id": created["id"]}
    assert detail_response.status_code == 404

    db = SessionLocal()
    try:
        assert db.get(ChatSession, created["id"]) is None
        assert db.query(ChatMessage).filter(ChatMessage.session_id == created["id"]).count() == 0
    finally:
        db.close()


def test_chat_null_session_creates_session_and_appears_in_list():
    with TestClient(app) as client:
        chat_response = client.post("/api/chat", json={"message": "Не работает DNS на Ubuntu", "session_id": None})
        session_id = chat_response.json()["session_id"]
        list_response = client.get("/api/chat/sessions")

    assert chat_response.status_code == 200
    assert list_response.status_code == 200
    items = list_response.json()["items"]
    matching = [item for item in items if item["id"] == session_id]
    assert matching
    assert matching[0]["messages_count"] == 2
    assert matching[0]["preview"]


def test_chat_existing_session_appends_messages():
    with TestClient(app) as client:
        created = _create_session(client, "Append investigation")
        first = client.post("/api/chat", json={"message": "Не работает DNS на Ubuntu", "session_id": created["id"]})
        second = client.post("/api/chat", json={"message": "Проверил resolvectl status", "session_id": created["id"]})
        detail = client.get(f"/api/chat/session/{created['id']}")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["session_id"] == created["id"]
    assert second.json()["session_id"] == created["id"]
    assert detail.status_code == 200
    assert [message["role"] for message in detail.json()["messages"]] == ["user", "assistant", "user", "assistant"]


def test_unknown_session_returns_404_for_get_patch_delete():
    unknown_id = 99999999
    with TestClient(app) as client:
        get_response = client.get(f"/api/chat/session/{unknown_id}")
        patch_response = client.patch(f"/api/chat/session/{unknown_id}", json={"title": "Missing"})
        delete_response = client.delete(f"/api/chat/session/{unknown_id}")

    assert get_response.status_code == 404
    assert patch_response.status_code == 404
    assert delete_response.status_code == 404


def test_create_session_uses_default_title_for_empty_title():
    with TestClient(app) as client:
        response = client.post("/api/chat/session", json={"title": "   "})

    assert response.status_code == 200
    assert response.json()["title"] == "New investigation"


def test_set_clear_session_host_context_and_unknown_host_rejected():
    with TestClient(app) as client:
        host_response = client.post("/api/hosts", json={"name": "session-host", "hostname": "session-host.example.local"})
        session_response = client.post("/api/chat/session", json={"title": "Host context investigation"})

        assert host_response.status_code == 200
        assert session_response.status_code == 200
        host_id = host_response.json()["id"]
        session_id = session_response.json()["id"]

        set_response = client.patch(f"/api/chat/session/{session_id}/host", json={"host_id": host_id})
        detail_response = client.get(f"/api/chat/session/{session_id}")
        clear_response = client.patch(f"/api/chat/session/{session_id}/host", json={"host_id": None})
        cleared_detail_response = client.get(f"/api/chat/session/{session_id}")
        unknown_response = client.patch(f"/api/chat/session/{session_id}/host", json={"host_id": 99999999})

    assert set_response.status_code == 200
    assert set_response.json()["host_id"] == host_id
    assert detail_response.status_code == 200
    assert detail_response.json()["host_id"] == host_id
    assert clear_response.status_code == 200
    assert clear_response.json()["host_id"] is None
    assert cleared_detail_response.status_code == 200
    assert cleared_detail_response.json()["host_id"] is None
    assert unknown_response.status_code == 404
