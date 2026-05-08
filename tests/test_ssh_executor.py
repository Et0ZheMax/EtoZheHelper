from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.execution.executor import ActionExecutionBlockedError, execute_approved_action_run
from app.execution.ssh_client import SshCommandResult
from app.main import app
from app.models import ActionExecution, ActionRun, Host, SshProfile


class FakeSshClient:
    def __init__(self, result=None, error=None):
        self.result = result or SshCommandResult(exit_code=0, stdout=b"ok\n", stderr=b"")
        self.error = error
        self.calls = []

    def run_command(self, hostname, port, username, command, connect_timeout, command_timeout):
        self.calls.append(
            {
                "hostname": hostname,
                "port": port,
                "username": username,
                "command": command,
                "connect_timeout": connect_timeout,
                "command_timeout": command_timeout,
            }
        )
        if self.error:
            raise self.error
        return self.result


class AuthenticationException(Exception):
    pass


def _create_ready_run(status="approved", auth_type="agent", sudo_mode="none", action="systemd_status", command="systemctl status nginx --no-pager"):
    db = SessionLocal()
    try:
        profile = SshProfile(
            name=f"profile-{auth_type}-{sudo_mode}",
            username="support",
            auth_type=auth_type,
            key_ref="metadata/key" if auth_type == "key" else None,
            password_ref="vault/password" if auth_type == "password" else None,
            sudo_mode=sudo_mode,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        host = Host(
            name=f"host-{profile.id}",
            hostname="vm.example.local",
            port=2222,
            os_family="linux",
            enabled=True,
            ssh_profile_id=profile.id,
        )
        db.add(host)
        db.commit()
        db.refresh(host)
        run = ActionRun(
            session_id=None,
            host_id=host.id,
            action=action,
            category="systemd",
            risk="low",
            command_preview=command,
            params_json='{"service":"nginx"}',
            status=status,
            execution_enabled=False,
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return run.id, host.id, profile.id
    finally:
        db.close()


def _execute(run_id, fake):
    db = SessionLocal()
    try:
        execution = execute_approved_action_run(db, run_id, "max", ssh_client=fake)
        return execution.id
    finally:
        db.close()


def _get_execution(execution_id):
    db = SessionLocal()
    try:
        execution = db.get(ActionExecution, execution_id)
        assert execution is not None
        return {
            "status": execution.status,
            "exit_code": execution.exit_code,
            "stdout": execution.stdout,
            "stderr": execution.stderr,
            "stdout_truncated": execution.stdout_truncated,
            "stderr_truncated": execution.stderr_truncated,
            "error": execution.error,
            "host_id": execution.host_id,
            "ssh_profile_id": execution.ssh_profile_id,
            "command_preview": execution.command_preview,
            "duration_ms": execution.duration_ms,
            "error_category": execution.error_category,
            "analysis_status": execution.analysis_status,
            "analysis_summary": execution.analysis_summary,
            "analysis_json": execution.analysis_json,
        }
    finally:
        db.close()


def _blocked(run_id, fake):
    db = SessionLocal()
    try:
        try:
            execute_approved_action_run(db, run_id, "max", ssh_client=fake)
        except ActionExecutionBlockedError as exc:
            return exc
        raise AssertionError("expected blocked execution")
    finally:
        db.close()


def test_approved_ready_agent_run_executes_and_stores_completed_execution():
    run_id, host_id, profile_id = _create_ready_run()
    fake = FakeSshClient(SshCommandResult(exit_code=0, stdout=b"active\n", stderr=b""))

    execution_id = _execute(run_id, fake)
    payload = _get_execution(execution_id)

    assert payload["status"] == "completed"
    assert payload["exit_code"] == 0
    assert payload["stdout"] == "active\n"
    assert payload["host_id"] == host_id
    assert payload["ssh_profile_id"] == profile_id
    assert payload["duration_ms"] is not None


def test_executor_passes_host_port_username_and_stored_command_preview_to_fake_client():
    run_id, _, _ = _create_ready_run(command="systemctl status nginx --no-pager")
    fake = FakeSshClient()

    _execute(run_id, fake)

    assert fake.calls == [
        {
            "hostname": "vm.example.local",
            "port": 2222,
            "username": "support",
            "command": "systemctl status nginx --no-pager",
            "connect_timeout": 8,
            "command_timeout": 20,
        }
    ]


def test_prepared_run_is_blocked_and_fake_client_is_not_called():
    run_id, _, _ = _create_ready_run(status="prepared")
    fake = FakeSshClient()

    exc = _blocked(run_id, fake)

    assert "must be approved" in exc.blockers[0]
    assert fake.calls == []


def test_api_blocked_response_includes_execution_id_and_stores_blocked_row():
    run_id, _, _ = _create_ready_run(status="prepared")

    with TestClient(app) as client:
        response = client.post(f"/api/action-runs/{run_id}/execute", json={"operator": "max"})

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["status"] == "blocked"
    assert detail["execution_id"]
    assert detail["message"] == "Execution was blocked before SSH connection."
    assert "stdout" not in detail
    assert "stderr" not in detail

    payload = _get_execution(detail["execution_id"])
    assert payload["status"] == "blocked"


def test_rejected_run_is_blocked_and_fake_client_is_not_called():
    run_id, _, _ = _create_ready_run(status="rejected")
    fake = FakeSshClient()

    exc = _blocked(run_id, fake)

    assert "must be approved" in exc.blockers[0]
    assert fake.calls == []


def test_approved_run_without_readiness_is_blocked_and_fake_client_is_not_called():
    run_id, _, _ = _create_ready_run()
    db = SessionLocal()
    try:
        run = db.get(ActionRun, run_id)
        assert run is not None
        run.host_id = None
        db.commit()
    finally:
        db.close()
    fake = FakeSshClient()

    exc = _blocked(run_id, fake)

    assert "no host_id" in "; ".join(exc.blockers)
    assert fake.calls == []


def test_manual_auth_is_blocked():
    run_id, _, _ = _create_ready_run(auth_type="manual")
    fake = FakeSshClient()

    exc = _blocked(run_id, fake)

    assert "Manual auth is not executable in Stage 14" in exc.blockers[0]
    assert fake.calls == []


def test_key_auth_is_blocked():
    run_id, _, _ = _create_ready_run(auth_type="key")
    fake = FakeSshClient()

    exc = _blocked(run_id, fake)

    assert "Key auth execution is not implemented in Stage 14" in exc.blockers[0]
    assert fake.calls == []


def test_password_auth_is_blocked():
    run_id, _, _ = _create_ready_run(auth_type="password")
    fake = FakeSshClient()

    exc = _blocked(run_id, fake)

    assert "Password auth execution is not implemented in Stage 14" in exc.blockers[0]
    assert fake.calls == []


def test_sudo_prompt_is_blocked():
    run_id, _, _ = _create_ready_run(sudo_mode="prompt")
    fake = FakeSshClient()

    exc = _blocked(run_id, fake)

    assert "Interactive sudo prompt is not supported in Stage 14" in exc.blockers[0]
    assert fake.calls == []


def test_sudo_nopasswd_limited_is_blocked():
    run_id, _, _ = _create_ready_run(sudo_mode="nopasswd_limited")
    fake = FakeSshClient()

    exc = _blocked(run_id, fake)

    assert "NOPASSWD limited sudo execution is not implemented in Stage 14" in exc.blockers[0]
    assert fake.calls == []


def test_unknown_removed_action_is_blocked():
    run_id, _, _ = _create_ready_run(action="removed_action")
    fake = FakeSshClient()

    exc = _blocked(run_id, fake)

    assert "no longer present" in exc.blockers[0]
    assert fake.calls == []


def test_nonzero_exit_code_stores_failed_status():
    run_id, _, _ = _create_ready_run()
    fake = FakeSshClient(SshCommandResult(exit_code=3, stdout=b"", stderr=b"bad"))

    execution_id = _execute(run_id, fake)
    payload = _get_execution(execution_id)

    assert payload["status"] == "failed"
    assert payload["exit_code"] == 3
    assert payload["stderr"] == "bad"


def test_timeout_result_stores_timed_out_status():
    run_id, _, _ = _create_ready_run()
    fake = FakeSshClient(SshCommandResult(exit_code=None, stdout=b"partial", stderr=b"", timed_out=True))

    execution_id = _execute(run_id, fake)
    payload = _get_execution(execution_id)

    assert payload["status"] == "timed_out"
    assert payload["error"] == "SSH command timed out after 20 seconds."


def test_ssh_exception_stores_failed_with_safe_error_text():
    run_id, _, _ = _create_ready_run()
    fake = FakeSshClient(error=RuntimeError("connection refused"))

    execution_id = _execute(run_id, fake)
    payload = _get_execution(execution_id)

    assert payload["status"] == "failed"
    assert payload["error_category"] == "connection_failed"
    assert payload["error"] == "SSH connection failed. Check hostname, network path and port."


def test_auth_like_exception_sets_auth_failed_category():
    run_id, _, _ = _create_ready_run()
    fake = FakeSshClient(error=AuthenticationException("agent authentication failed"))

    execution_id = _execute(run_id, fake)
    payload = _get_execution(execution_id)

    assert payload["status"] == "failed"
    assert payload["error_category"] == "auth_failed"
    assert payload["error"] == "SSH authentication failed. Check ssh-agent key availability and username."


def test_timeout_like_exception_sets_timeout_category():
    run_id, _, _ = _create_ready_run()
    fake = FakeSshClient(error=TimeoutError("timed out while connecting"))

    execution_id = _execute(run_id, fake)
    payload = _get_execution(execution_id)

    assert payload["status"] == "failed"
    assert payload["error_category"] == "timeout"
    assert payload["error"] == "SSH connection or command timed out."


def test_safe_error_text_is_capped_and_sanitized():
    run_id, _, _ = _create_ready_run()
    fake = FakeSshClient(error=RuntimeError("token=" + "x" * 2000))

    execution_id = _execute(run_id, fake)
    payload = _get_execution(execution_id)

    assert payload["status"] == "failed"
    assert payload["error"] == "SSH execution failed with a redacted error message."
    assert "x" * 100 not in payload["error"]
    assert len(payload["error"]) <= 500


def test_large_stdout_and_stderr_are_truncated():
    run_id, _, _ = _create_ready_run()
    fake = FakeSshClient(SshCommandResult(exit_code=0, stdout=b"a" * (64 * 1024 + 10), stderr=b"b" * (32 * 1024 + 10)))

    execution_id = _execute(run_id, fake)
    payload = _get_execution(execution_id)

    assert payload["stdout_truncated"] is True
    assert payload["stderr_truncated"] is True
    assert len(payload["stdout"].encode()) == 64 * 1024
    assert len(payload["stderr"].encode()) == 32 * 1024


def test_api_rejects_extra_command_field_with_422():
    run_id, _, _ = _create_ready_run()
    with TestClient(app) as client:
        response = client.post(f"/api/action-runs/{run_id}/execute", json={"operator": "max", "command": "id"})

    assert response.status_code == 422


def test_api_does_not_accept_params_or_host_override():
    run_id, _, _ = _create_ready_run()
    with TestClient(app) as client:
        params_response = client.post(f"/api/action-runs/{run_id}/execute", json={"operator": "max", "params": {}})
        host_response = client.post(f"/api/action-runs/{run_id}/execute", json={"operator": "max", "host_id": 999})

    assert params_response.status_code == 422
    assert host_response.status_code == 422


def test_executions_list_returns_latest_first():
    run_id, _, _ = _create_ready_run()
    first = _execute(run_id, FakeSshClient(SshCommandResult(exit_code=0, stdout=b"first", stderr=b"")))
    second = _execute(run_id, FakeSshClient(SshCommandResult(exit_code=0, stdout=b"second", stderr=b"")))

    with TestClient(app) as client:
        response = client.get(f"/api/action-runs/{run_id}/executions?limit=5&offset=0")

    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["id"] for item in items[:2]] == [second, first]


def test_execution_detail_404_for_unknown_id():
    with TestClient(app) as client:
        response = client.get("/api/action-executions/999999")

    assert response.status_code == 404


def test_action_run_executions_list_404_for_unknown_run():
    with TestClient(app) as client:
        response = client.get("/api/action-runs/999999/executions")

    assert response.status_code == 404


def test_execution_response_contains_no_secrets():
    run_id, _, _ = _create_ready_run()
    fake = FakeSshClient()
    execution_id = _execute(run_id, fake)

    with TestClient(app) as client:
        response = client.get(f"/api/action-executions/{execution_id}")

    assert response.status_code == 200
    payload_text = response.text
    assert "key_ref" not in payload_text
    assert "password_ref" not in payload_text
    assert "vault" not in payload_text


def test_executor_modules_do_not_use_forbidden_execution_libraries():
    combined = "\n".join(
        Path(path).read_text(encoding="utf-8") for path in ["app/execution/executor.py", "app/execution/ssh_client.py"]
    )

    forbidden = ["os.system", "Fabric", "asyncssh", "subprocess", "shell=True"]
    for token in forbidden:
        assert token not in combined


def test_paramiko_is_only_used_in_ssh_client_adapter():
    allowed = Path("app/execution/ssh_client.py")
    offenders = []

    for path in Path("app").rglob("*.py"):
        text = path.read_text(encoding="utf-8").casefold()
        if "paramiko" in text and path != allowed:
            offenders.append(str(path))

    assert offenders == []


def test_action_run_dynamic_routes_do_not_shadow_readiness_or_executions():
    run_id, _, _ = _create_ready_run()
    fake = FakeSshClient()
    execution_id = _execute(run_id, fake)

    with TestClient(app) as client:
        readiness_response = client.get(f"/api/action-runs/{run_id}/readiness")
        executions_response = client.get(f"/api/action-runs/{run_id}/executions")
        detail_response = client.get(f"/api/action-runs/{run_id}")
        execution_detail_response = client.get(f"/api/action-executions/{execution_id}")

    assert readiness_response.status_code == 200
    assert executions_response.status_code == 200
    assert detail_response.status_code == 200
    assert execution_detail_response.status_code == 200


def test_completed_execution_stores_analysis_for_analyzable_stdout():
    run_id, _, _ = _create_ready_run()
    stdout = b"systemctl status nginx --no-pager\nLoaded: loaded\nActive: failed (Result: exit-code)\nFailed to start nginx\n"
    fake = FakeSshClient(SshCommandResult(exit_code=0, stdout=stdout, stderr=b""))

    execution_id = _execute(run_id, fake)
    payload = _get_execution(execution_id)

    assert payload["status"] == "completed"
    assert payload["analysis_status"] == "analyzed"
    assert payload["analysis_summary"] is not None
    parsed = json.loads(payload["analysis_json"])
    assert parsed["topic"] == "systemd"
    assert parsed["findings"]


def test_failed_execution_with_stderr_stores_analysis_when_analyzable():
    run_id, _, _ = _create_ready_run()
    stderr = b"write failed: No space left on device\n"
    fake = FakeSshClient(SshCommandResult(exit_code=1, stdout=b"", stderr=stderr))

    execution_id = _execute(run_id, fake)
    payload = _get_execution(execution_id)

    assert payload["status"] == "failed"
    assert payload["analysis_status"] == "analyzed"
    assert "disk" in payload["analysis_json"].lower()


def test_timed_out_execution_with_partial_output_can_be_analyzed():
    run_id, _, _ = _create_ready_run()
    stdout = b"systemctl status nginx --no-pager\nActive: failed (Result: timeout)\n"
    fake = FakeSshClient(SshCommandResult(exit_code=None, stdout=stdout, stderr=b"", timed_out=True))

    execution_id = _execute(run_id, fake)
    payload = _get_execution(execution_id)

    assert payload["status"] == "timed_out"
    assert payload["analysis_status"] == "analyzed"
    assert payload["analysis_json"] is not None


def test_blocked_execution_does_not_analyze():
    run_id, _, _ = _create_ready_run(status="prepared")
    fake = FakeSshClient()

    exc = _blocked(run_id, fake)
    payload = _get_execution(exc.execution.id)

    assert payload["status"] == "blocked"
    assert payload["analysis_status"] is None
    assert payload["analysis_json"] is None


def test_execution_detail_response_includes_parsed_analysis_fields():
    run_id, _, _ = _create_ready_run()
    stdout = b"systemctl status nginx --no-pager\nActive: failed (Result: exit-code)\n"
    execution_id = _execute(run_id, FakeSshClient(SshCommandResult(exit_code=0, stdout=stdout, stderr=b"")))

    with TestClient(app) as client:
        response = client.get(f"/api/action-executions/{execution_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis_status"] == "analyzed"
    assert payload["analysis_summary"]
    assert isinstance(payload["analysis"], dict)
    assert payload["analysis"]["findings"]


def test_execution_list_response_includes_analysis_summary_fields():
    run_id, _, _ = _create_ready_run()
    stdout = b"systemctl status nginx --no-pager\nActive: failed (Result: exit-code)\n"
    _execute(run_id, FakeSshClient(SshCommandResult(exit_code=0, stdout=stdout, stderr=b"")))

    with TestClient(app) as client:
        response = client.get(f"/api/action-runs/{run_id}/executions")

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["analysis_status"] == "analyzed"
    assert item["analysis_summary"]
    assert isinstance(item["analysis"], dict)


def test_execute_api_response_includes_analysis_fields(monkeypatch):
    run_id, _, _ = _create_ready_run()

    class ApiFakeSshClient(FakeSshClient):
        def __init__(self):
            super().__init__(SshCommandResult(exit_code=0, stdout=b"systemctl status nginx --no-pager\nActive: failed\n", stderr=b""))

    monkeypatch.setattr("app.execution.executor.DefaultSshClient", ApiFakeSshClient)

    with TestClient(app) as client:
        response = client.post(f"/api/action-runs/{run_id}/execute", json={"operator": "max"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis_status"] == "analyzed"
    assert payload["analysis_summary"]
    assert payload["analysis"]["findings"]


def test_paramiko_remains_only_in_ssh_client_adapter_after_analysis_stage():
    allowed = Path("app/execution/ssh_client.py")
    offenders = []

    for path in Path("app").rglob("*.py"):
        text = path.read_text(encoding="utf-8").casefold()
        if "paramiko" in text and path != allowed:
            offenders.append(str(path))

    assert offenders == []
