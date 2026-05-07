from pathlib import Path

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import ActionRun


def _create_session(client: TestClient, title: str = "Action run test") -> dict:
    response = client.post("/api/chat/session", json={"title": title})
    assert response.status_code == 200
    return response.json()


def _create_host(client: TestClient, name: str = "run-host", enabled: bool = True) -> dict:
    response = client.post(
        "/api/hosts",
        json={"name": name, "hostname": f"{name}.example.local", "enabled": enabled, "tags": ["test"]},
    )
    assert response.status_code == 200
    return response.json()


def _create_historical_run(action: str, params_json: str, command_preview: str) -> ActionRun:
    db = SessionLocal()
    try:
        run = ActionRun(
            session_id=None,
            host_id=None,
            action=action,
            category="legacy",
            risk="low",
            command_preview=command_preview,
            params_json=params_json,
            status="prepared",
            execution_enabled=False,
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        db.expunge(run)
        return run
    finally:
        db.close()


def _prepare(client: TestClient, **overrides) -> dict:
    payload = {"action": "systemd_status", "params": {"service": "nginx"}}
    payload.update(overrides)
    response = client.post("/api/action-runs/prepare", json=payload)
    assert response.status_code == 200
    return response.json()



def _approve(client: TestClient, run_id: int, **overrides) -> dict:
    payload = {"operator": "max", "note": "Checked host and action preview.", "expires_in_minutes": 60}
    payload.update(overrides)
    response = client.post(f"/api/action-runs/{run_id}/approve", json=payload)
    assert response.status_code == 200
    return response.json()


def _reject(client: TestClient, run_id: int, **overrides) -> dict:
    payload = {"operator": "max", "note": "Wrong host selected."}
    payload.update(overrides)
    response = client.post(f"/api/action-runs/{run_id}/reject", json=payload)
    assert response.status_code == 200
    return response.json()


def _expire(client: TestClient, run_id: int, **overrides) -> dict:
    payload = {"operator": "system", "note": "Manual expiration."}
    payload.update(overrides)
    response = client.post(f"/api/action-runs/{run_id}/expire", json=payload)
    assert response.status_code == 200
    return response.json()


def test_prepare_valid_action_run_with_host_and_session():
    with TestClient(app) as client:
        session = _create_session(client, "run-with-session")
        host = _create_host(client, "run-with-host")
        payload = _prepare(client, session_id=session["id"], host_id=host["id"])

    assert payload["session_id"] == session["id"]
    assert payload["host_id"] == host["id"]
    assert payload["action"] == "systemd_status"
    assert payload["category"] == "systemd"
    assert payload["risk"] == "low"
    assert payload["read_only"] is True
    assert payload["requires_approval"] is True
    assert payload["execution_enabled"] is False
    assert payload["status"] == "prepared"
    assert payload["command_preview"] == "systemctl status nginx --no-pager"
    assert payload["params"] == {"service": "nginx"}
    assert payload["warnings"]


def test_prepare_valid_action_run_without_session():
    with TestClient(app) as client:
        host = _create_host(client, "run-no-session")
        payload = _prepare(client, session_id=None, host_id=host["id"])

    assert payload["session_id"] is None
    assert payload["host_id"] == host["id"]
    assert payload["execution_enabled"] is False
    assert payload["status"] == "prepared"


def test_prepare_unknown_action_returns_404():
    with TestClient(app) as client:
        host = _create_host(client, "run-unknown-action")
        response = client.post("/api/action-runs/prepare", json={"host_id": host["id"], "action": "nope", "params": {}})

    assert response.status_code == 404


def test_prepare_invalid_params_returns_422():
    with TestClient(app) as client:
        host = _create_host(client, "run-invalid-params")
        response = client.post(
            "/api/action-runs/prepare",
            json={"host_id": host["id"], "action": "systemd_status", "params": {"service": "nginx; rm -rf /"}},
        )

    assert response.status_code == 422


def test_prepare_unknown_host_returns_404():
    with TestClient(app) as client:
        response = client.post(
            "/api/action-runs/prepare",
            json={"host_id": 999999, "action": "systemd_status", "params": {"service": "nginx"}},
        )

    assert response.status_code == 404


def test_prepare_disabled_host_returns_422():
    with TestClient(app) as client:
        host = _create_host(client, "run-disabled-host", enabled=False)
        response = client.post(
            "/api/action-runs/prepare",
            json={"host_id": host["id"], "action": "systemd_status", "params": {"service": "nginx"}},
        )

    assert response.status_code == 422


def test_prepare_unknown_session_returns_404():
    with TestClient(app) as client:
        host = _create_host(client, "run-unknown-session")
        response = client.post(
            "/api/action-runs/prepare",
            json={"session_id": 999999, "host_id": host["id"], "action": "systemd_status", "params": {"service": "nginx"}},
        )

    assert response.status_code == 404


def test_list_action_runs():
    with TestClient(app) as client:
        host = _create_host(client, "run-list-host")
        prepared = _prepare(client, host_id=host["id"])
        response = client.get(f"/api/action-runs?host_id={host['id']}&limit=10&offset=0")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 1
    assert any(item["id"] == prepared["id"] for item in payload["items"])


def test_get_action_run_detail():
    with TestClient(app) as client:
        host = _create_host(client, "run-detail-host")
        prepared = _prepare(client, host_id=host["id"])
        response = client.get(f"/api/action-runs/{prepared['id']}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == prepared["id"]
    assert payload["execution_enabled"] is False
    assert payload["status"] == "prepared"



def test_approve_prepared_action_run_sets_metadata_only():
    with TestClient(app) as client:
        host = _create_host(client, "run-approve-host")
        prepared = _prepare(client, host_id=host["id"])
        payload = _approve(client, prepared["id"], operator="max", note="Approved for future read-only execution")

    assert payload["status"] == "approved"
    assert payload["approved_at"] is not None
    assert payload["approved_by"] == "max"
    assert payload["approval_note"] == "Approved for future read-only execution"
    assert payload["expires_at"] is not None
    assert payload["execution_enabled"] is False
    assert any("metadata only" in warning for warning in payload["warnings"])


def test_approve_already_approved_run_returns_409():
    with TestClient(app) as client:
        prepared = _prepare(client)
        _approve(client, prepared["id"])
        response = client.post(f"/api/action-runs/{prepared['id']}/approve", json={"operator": "max"})

    assert response.status_code == 409


def test_approve_rejected_run_returns_409():
    with TestClient(app) as client:
        prepared = _prepare(client)
        _reject(client, prepared["id"])
        response = client.post(f"/api/action-runs/{prepared['id']}/approve", json={"operator": "max"})

    assert response.status_code == 409


def test_approve_expired_run_returns_409():
    with TestClient(app) as client:
        prepared = _prepare(client)
        _expire(client, prepared["id"])
        response = client.post(f"/api/action-runs/{prepared['id']}/approve", json={"operator": "max"})

    assert response.status_code == 409


def test_reject_prepared_action_run_sets_metadata_only():
    with TestClient(app) as client:
        prepared = _prepare(client)
        payload = _reject(client, prepared["id"], operator="max", note="Wrong host selected.")

    assert payload["status"] == "rejected"
    assert payload["rejected_at"] is not None
    assert payload["rejected_by"] == "max"
    assert payload["rejection_note"] == "Wrong host selected."
    assert payload["approval_note"] is None
    assert payload["execution_enabled"] is False


def test_reject_approved_run_preserves_approval_metadata():
    with TestClient(app) as client:
        prepared = _prepare(client)
        _approve(client, prepared["id"], operator="max", note="approved note")
        payload = _reject(client, prepared["id"], operator="max2", note="rejected note")
        detail_response = client.get(f"/api/action-runs/{prepared['id']}")

    assert payload["status"] == "rejected"
    assert payload["approved_by"] == "max"
    assert payload["approval_note"] == "approved note"
    assert payload["rejected_at"] is not None
    assert payload["rejected_by"] == "max2"
    assert payload["rejection_note"] == "rejected note"
    assert payload["execution_enabled"] is False
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["approved_by"] == "max"
    assert detail["approval_note"] == "approved note"
    assert detail["rejection_note"] == "rejected note"


def test_reject_expired_run_returns_409():
    with TestClient(app) as client:
        prepared = _prepare(client)
        _expire(client, prepared["id"])
        response = client.post(f"/api/action-runs/{prepared['id']}/reject", json={"operator": "max"})

    assert response.status_code == 409


def test_expire_prepared_action_run_sets_metadata_only():
    with TestClient(app) as client:
        prepared = _prepare(client)
        payload = _expire(client, prepared["id"], operator="system", note="Manual expiration.")

    assert payload["status"] == "expired"
    assert payload["expired_at"] is not None
    assert payload["expiration_note"] == "Manual expiration."
    assert payload["expired_by"] == "system"
    assert payload["approval_note"] is None
    assert payload["execution_enabled"] is False


def test_expire_approved_run_preserves_approval_metadata():
    with TestClient(app) as client:
        prepared = _prepare(client)
        _approve(client, prepared["id"], operator="max", note="approved note")
        payload = _expire(client, prepared["id"], operator="system", note="expired note")

    assert payload["status"] == "expired"
    assert payload["approval_note"] == "approved note"
    assert payload["approved_by"] == "max"
    assert payload["expired_at"] is not None
    assert payload["expired_by"] == "system"
    assert payload["expiration_note"] == "expired note"
    assert payload["execution_enabled"] is False


def test_expire_rejected_run_returns_409():
    with TestClient(app) as client:
        prepared = _prepare(client)
        _reject(client, prepared["id"])
        response = client.post(f"/api/action-runs/{prepared['id']}/expire", json={"operator": "system"})

    assert response.status_code == 409


def test_list_action_runs_filters_by_approved_status_and_detail_has_fields():
    with TestClient(app) as client:
        prepared = _prepare(client)
        approved = _approve(client, prepared["id"], operator="max", note="list detail note")
        list_response = client.get("/api/action-runs?status=approved&limit=20&offset=0")
        detail_response = client.get(f"/api/action-runs/{prepared['id']}")

    assert list_response.status_code == 200
    matching = [item for item in list_response.json()["items"] if item["id"] == approved["id"]]
    assert matching
    assert all(item["status"] == "approved" for item in list_response.json()["items"])
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["approved_at"] is not None
    assert detail["approved_by"] == "max"
    assert detail["approval_note"] == "list detail note"


def test_approval_request_with_extra_command_field_returns_422():
    with TestClient(app) as client:
        prepared = _prepare(client)
        response = client.post(
            f"/api/action-runs/{prepared['id']}/approve",
            json={"operator": "max", "command": "whoami"},
        )

    assert response.status_code == 422


def test_approval_request_with_extra_password_field_returns_422():
    with TestClient(app) as client:
        prepared = _prepare(client)
        response = client.post(
            f"/api/action-runs/{prepared['id']}/approve",
            json={"operator": "max", "password": "secret"},
        )

    assert response.status_code == 422


def test_historical_unknown_action_run_remains_readable():
    with TestClient(app) as client:
        run = _create_historical_run(
            action="old_removed_action",
            params_json='{"service":"nginx"}',
            command_preview="old preview",
        )
        response = client.get(f"/api/action-runs/{run.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["command_preview"] == "old preview"
    assert payload["execution_enabled"] is False
    assert payload["status"] == "prepared"
    assert payload["params"] == {"service": "nginx"}
    assert any("no longer validate" in warning for warning in payload["warnings"])


def test_historical_invalid_params_run_remains_readable():
    with TestClient(app) as client:
        run = _create_historical_run(
            action="systemd_status",
            params_json='{"service":"nginx;rm"}',
            command_preview="old stored preview",
        )
        response = client.get(f"/api/action-runs/{run.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "systemd_status"
    assert payload["command_preview"] == "old stored preview"
    assert payload["execution_enabled"] is False
    assert payload["params"] == {"service": "nginx;rm"}
    assert any("no longer validate" in warning for warning in payload["warnings"])


def test_list_action_runs_handles_historical_invalid_run():
    with TestClient(app) as client:
        run = _create_historical_run(
            action="old_removed_action",
            params_json='{"service":"nginx"}',
            command_preview="old list preview",
        )
        response = client.get("/api/action-runs?limit=20&offset=0")

    assert response.status_code == 200
    matching = [item for item in response.json()["items"] if item["id"] == run.id]
    assert matching
    assert matching[0]["command_preview"] == "old list preview"
    assert any("no longer validate" in warning for warning in matching[0]["warnings"])


def test_prepare_rejects_arbitrary_command_field():
    with TestClient(app) as client:
        host = _create_host(client, "run-command-field")
        response = client.post(
            "/api/action-runs/prepare",
            json={
                "host_id": host["id"],
                "action": "systemd_status",
                "params": {"service": "nginx"},
                "command": "whoami",
            },
        )

    assert response.status_code == 422


def test_prepare_unsafe_params_rejected_by_policy():
    with TestClient(app) as client:
        host = _create_host(client, "run-unsafe-url")
        response = client.post(
            "/api/action-runs/prepare",
            json={"host_id": host["id"], "action": "curl_head", "params": {"url": "https://example.com;whoami"}},
        )

    assert response.status_code == 422


def test_no_ssh_subprocess_execution_code_is_introduced():
    forbidden = ["subprocess", "paramiko", "asyncssh", "os.system", "Popen"]
    app_files = Path("app").rglob("*.py")
    matches = []
    for path in app_files:
        text = path.read_text(encoding="utf-8")
        lowered = text.casefold()
        matches.extend(f"{path}:{term}" for term in forbidden if term.casefold() in lowered)

    assert matches == []
