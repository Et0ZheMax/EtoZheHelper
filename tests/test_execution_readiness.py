from pathlib import Path

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import ActionRun, Host, SshProfile


def _create_profile(client: TestClient, name: str, **overrides) -> dict:
    payload = {"name": name, "username": "support", "auth_type": "agent", "sudo_mode": "none"}
    payload.update(overrides)
    response = client.post("/api/ssh-profiles", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def _create_host(client: TestClient, name: str, profile_id: int | None = None, **overrides) -> dict:
    payload = {"name": name, "hostname": f"{name}.example.local", "tags": ["nginx", "prod"]}
    if profile_id is not None:
        payload["ssh_profile_id"] = profile_id
    payload.update(overrides)
    response = client.post("/api/hosts", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def _prepare(client: TestClient, host_id: int | None = None) -> dict:
    payload = {"action": "systemd_status", "params": {"service": "nginx"}}
    if host_id is not None:
        payload["host_id"] = host_id
    response = client.post("/api/action-runs/prepare", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def _approve(client: TestClient, run_id: int) -> dict:
    response = client.post(f"/api/action-runs/{run_id}/approve", json={"operator": "max", "note": "ready check"})
    assert response.status_code == 200, response.text
    return response.json()


def _approved_run(client: TestClient, name: str, profile_overrides: dict | None = None, host_overrides: dict | None = None) -> dict:
    profile = _create_profile(client, f"{name}-profile", **(profile_overrides or {}))
    host = _create_host(client, f"{name}-host", profile["id"], **(host_overrides or {}))
    run = _prepare(client, host["id"])
    _approve(client, run["id"])
    return {"profile": profile, "host": host, "run": run}


def _set_host_enabled(host_id: int, enabled: bool) -> None:
    db = SessionLocal()
    try:
        host = db.get(Host, host_id)
        assert host is not None
        host.enabled = enabled
        db.commit()
    finally:
        db.close()


def _set_host_profile(host_id: int, profile_id: int | None) -> None:
    db = SessionLocal()
    try:
        host = db.get(Host, host_id)
        assert host is not None
        host.ssh_profile_id = profile_id
        db.commit()
    finally:
        db.close()


def _create_direct_approved_run(command_preview: str = "systemctl status nginx --no-pager", host_id: int | None = None) -> int:
    db = SessionLocal()
    try:
        run = ActionRun(
            session_id=None,
            host_id=host_id,
            action="systemd_status",
            category="systemd",
            risk="low",
            command_preview=command_preview,
            params_json='{"service":"nginx"}',
            status="approved",
            execution_enabled=True,
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return run.id
    finally:
        db.close()


def test_approved_run_with_enabled_linux_host_and_agent_profile_is_ready():
    with TestClient(app) as client:
        data = _approved_run(client, "ready-agent")
        response = client.get(f"/api/action-runs/{data['run']['id']}/readiness")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ready"] is True
    assert payload["execution_enabled"] is False
    assert payload["blockers"] == []
    assert payload["host"]["name"] == data["host"]["name"]
    assert payload["ssh_profile"]["auth_type"] == "agent"
    assert "Stage 13 does not connect over SSH and does not execute commands." in payload["warnings"]


def test_prepared_but_not_approved_run_is_not_ready():
    with TestClient(app) as client:
        data = _approved_run(client, "not-approved-source")
        run = _prepare(client, data["host"]["id"])
        response = client.get(f"/api/action-runs/{run['id']}/readiness")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ready"] is False
    assert payload["host"] is None
    assert "Action run must be approved before executor readiness can be checked." in payload["blockers"]


def test_approved_run_without_host_id_is_not_ready():
    with TestClient(app) as client:
        run = _prepare(client)
        _approve(client, run["id"])
        response = client.get(f"/api/action-runs/{run['id']}/readiness")

    assert response.status_code == 200
    assert "Approved run has no host_id. Select a host and prepare a host-targeted run." in response.json()["blockers"]


def test_approved_run_with_disabled_host_is_not_ready():
    with TestClient(app) as client:
        data = _approved_run(client, "disabled-host")
        _set_host_enabled(data["host"]["id"], False)
        response = client.get(f"/api/action-runs/{data['run']['id']}/readiness")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ready"] is False
    assert "Referenced host is disabled." in payload["blockers"]


def test_approved_run_with_host_missing_ssh_profile_is_not_ready():
    with TestClient(app) as client:
        data = _approved_run(client, "no-profile")
        _set_host_profile(data["host"]["id"], None)
        response = client.get(f"/api/action-runs/{data['run']['id']}/readiness")

    assert response.status_code == 200
    assert "Host has no SSH profile assigned." in response.json()["blockers"]


def test_approved_run_with_missing_referenced_ssh_profile_is_not_ready():
    with TestClient(app) as client:
        data = _approved_run(client, "missing-profile")
        _set_host_profile(data["host"]["id"], 999999)
        response = client.get(f"/api/action-runs/{data['run']['id']}/readiness")

    assert response.status_code == 200
    assert "Referenced SSH profile was not found." in response.json()["blockers"]


def test_key_auth_without_key_ref_is_not_ready():
    with TestClient(app) as client:
        data = _approved_run(client, "key-no-ref", profile_overrides={"auth_type": "key"})
        response = client.get(f"/api/action-runs/{data['run']['id']}/readiness")

    assert response.status_code == 200
    assert "SSH profile key auth requires key_ref metadata." in response.json()["blockers"]


def test_password_auth_without_password_ref_is_not_ready():
    with TestClient(app) as client:
        data = _approved_run(client, "password-no-ref", profile_overrides={"auth_type": "password"})
        response = client.get(f"/api/action-runs/{data['run']['id']}/readiness")

    assert response.status_code == 200
    assert "SSH profile password auth requires password_ref metadata." in response.json()["blockers"]


def test_manual_auth_can_be_ready():
    with TestClient(app) as client:
        data = _approved_run(client, "manual-ready", profile_overrides={"auth_type": "manual"})
        response = client.get(f"/api/action-runs/{data['run']['id']}/readiness")

    assert response.status_code == 200
    assert response.json()["ready"] is True


def test_sudo_mode_prompt_returns_warning():
    with TestClient(app) as client:
        data = _approved_run(client, "sudo-prompt", profile_overrides={"sudo_mode": "prompt"})
        response = client.get(f"/api/action-runs/{data['run']['id']}/readiness")

    assert response.status_code == 200
    assert "Future executor may require an interactive sudo prompt." in response.json()["warnings"]


def test_sudo_mode_nopasswd_limited_returns_warning():
    with TestClient(app) as client:
        data = _approved_run(client, "sudo-limited", profile_overrides={"sudo_mode": "nopasswd_limited"})
        response = client.get(f"/api/action-runs/{data['run']['id']}/readiness")

    assert response.status_code == 200
    assert "Future executor must enforce a limited sudo allowlist." in response.json()["warnings"]


def test_empty_command_preview_is_not_ready():
    with TestClient(app) as client:
        data = _approved_run(client, "empty-preview")
        run_id = _create_direct_approved_run(command_preview="", host_id=data["host"]["id"])
        response = client.get(f"/api/action-runs/{run_id}/readiness")

    assert response.status_code == 200
    assert "Prepared run has no command preview." in response.json()["blockers"]


def test_readiness_response_always_has_execution_enabled_false():
    with TestClient(app) as client:
        data = _approved_run(client, "exec-disabled")
        response = client.get(f"/api/action-runs/{data['run']['id']}/readiness")

    assert response.status_code == 200
    assert response.json()["execution_enabled"] is False


def test_unknown_run_returns_404():
    with TestClient(app) as client:
        response = client.get("/api/action-runs/999999/readiness")

    assert response.status_code == 404


def test_no_ssh_or_process_execution_code_is_introduced():
    forbidden = ("paramiko", "asyncssh", "fabric", "subprocess", "os.system", "socket", "ping")
    for path in Path("app/execution").glob("*.py"):
        text = path.read_text(encoding="utf-8").casefold()
        assert not any(term in text for term in forbidden), path
