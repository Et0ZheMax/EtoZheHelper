from fastapi.testclient import TestClient

from app.main import app


def test_actions_catalog_returns_items():
    with TestClient(app) as client:
        response = client.get("/api/actions/catalog")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"]
    systemd = next(item for item in payload["items"] if item["key"] == "systemd_status")
    assert systemd["params_schema"]["service"]["type"] == "string"
    assert "command_template" not in systemd


def test_actions_propose_returns_command_preview():
    with TestClient(app) as client:
        response = client.post("/api/actions/propose", json={"action": "systemd_status", "params": {"service": "nginx"}})

    assert response.status_code == 200
    payload = response.json()
    assert payload["command_preview"] == "systemctl status nginx --no-pager"
    assert payload["execution_enabled"] is False
    assert payload["warnings"]


def test_actions_propose_bad_params_returns_422():
    with TestClient(app) as client:
        response = client.post("/api/actions/propose", json={"action": "systemd_status", "params": {"service": "nginx; rm -rf /"}})

    assert response.status_code == 422


def test_actions_propose_unknown_session_returns_404():
    with TestClient(app) as client:
        response = client.post(
            "/api/actions/propose",
            json={"action": "systemd_status", "params": {"service": "nginx"}, "session_id": 999999},
        )

    assert response.status_code == 404


def test_chat_dns_response_includes_actions():
    with TestClient(app) as client:
        response = client.post("/api/chat", json={"message": "Не работает DNS на Ubuntu", "session_id": None})

    assert response.status_code == 200
    payload = response.json()
    assert "actions" in payload
    assert payload["actions"]
    assert payload["actions"][0]["action"] == "resolved_status"
    assert payload["actions"][0]["command_preview"] == "resolvectl status"
    assert payload["actions"][0]["execution_enabled"] is False
