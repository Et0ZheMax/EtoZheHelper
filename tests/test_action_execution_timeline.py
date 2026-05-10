from pathlib import Path

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import ActionExecution, ActionRun, AuditEvent, ChatMessage, ChatSession, Host, utcnow


def _fixture(linked: bool = True, stdout: str | None = None) -> int:
    with SessionLocal() as db:
        session = ChatSession(title="Timeline investigation") if linked else None
        host = Host(name="app01", hostname="app01.example.test", os_family="linux", enabled=True)
        db.add(host)
        if session is not None:
            db.add(session)
        db.commit()
        if session is not None:
            db.refresh(session)
        db.refresh(host)
        run = ActionRun(
            session_id=session.id if session is not None else None,
            host_id=host.id,
            action="disk_usage",
            category="linux",
            risk="low",
            command_preview="df -h",
            params_json="{}",
            status="approved",
            execution_enabled=False,
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        execution = ActionExecution(
            run_id=run.id,
            host_id=host.id,
            ssh_profile_id=None,
            action="disk_usage",
            command_preview="df -h",
            status="completed",
            exit_code=0,
            stdout=stdout
            if stdout is not None
            else "Filesystem Size Used Avail Use% Mounted on\n/dev/sda2 20G 19G 1G 94% /\n",
            stderr="",
            stdout_truncated=False,
            stderr_truncated=False,
            started_at=utcnow(),
            finished_at=utcnow(),
            duration_ms=843,
            warnings_json="[]",
        )
        db.add(execution)
        db.commit()
        db.refresh(execution)
        return execution.id


def test_get_action_execution_detail_returns_timeline_fields():
    execution_id = _fixture()
    with TestClient(app) as client:
        response = client.get(f"/api/action-executions/{execution_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == execution_id
    assert payload["session_id"] is not None
    assert payload["host_name"] == "app01"
    assert payload["action"] == "disk_usage"
    assert payload["command_preview"] == "df -h"
    assert payload["chat_attached_at"] is None
    assert payload["analysis_attached_at"] is None


def test_attach_appends_chat_message_updates_timestamp_and_audit():
    execution_id = _fixture()
    with TestClient(app) as client:
        response = client.post(
            f"/api/action-executions/{execution_id}/attach",
            json={"operator": "max", "include_stdout": False, "note": "Checked disk usage"},
        )

    assert response.status_code == 200
    payload = response.json()
    with SessionLocal() as db:
        execution = db.get(ActionExecution, execution_id)
        message = db.get(ChatMessage, payload["message_id"])
        audit = db.query(AuditEvent).filter(AuditEvent.event_type == "action_execution_attached").order_by(AuditEvent.id.desc()).first()
        assert execution.chat_attached_at is not None
        assert message is not None
        assert message.session_id == payload["session_id"]
        assert message.role == "assistant"
        assert "Read-only SSH check attached" in message.content
        assert "Stdout is stored in execution detail" in message.content
        assert audit is not None


def test_analyze_appends_assistant_message_updates_summary_and_audit():
    execution_id = _fixture()
    with TestClient(app) as client:
        response = client.post(
            f"/api/action-executions/{execution_id}/analyze",
            json={"operator": "max", "note": "Analyze after df"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis_status"] == "analyzed"
    assert payload["analysis_summary"]
    with SessionLocal() as db:
        execution = db.get(ActionExecution, execution_id)
        message = db.get(ChatMessage, payload["message_id"])
        audit = db.query(AuditEvent).filter(AuditEvent.event_type == "action_execution_analyzed").order_by(AuditEvent.id.desc()).first()
        assert execution.analysis_attached_at is not None
        assert execution.analysis_summary
        assert message is not None
        assert message.role == "assistant"
        assert "Analysis of read-only SSH check" in message.content
        assert "Findings" in message.content
        assert audit is not None


def test_unknown_execution_id_returns_404():
    with TestClient(app) as client:
        response = client.get("/api/action-executions/999999999")

    assert response.status_code == 404


def test_execution_without_linked_session_returns_409_for_attach_and_analyze():
    execution_id = _fixture(linked=False)
    with TestClient(app) as client:
        attach = client.post(f"/api/action-executions/{execution_id}/attach", json={"operator": "max"})
        analyze = client.post(f"/api/action-executions/{execution_id}/analyze", json={"operator": "max"})

    assert attach.status_code == 409
    assert analyze.status_code == 409
    assert attach.json()["detail"] == "Execution is not linked to an investigation session"


def test_extra_and_secret_fields_are_rejected():
    execution_id = _fixture()
    with TestClient(app) as client:
        extra = client.post(f"/api/action-executions/{execution_id}/attach", json={"operator": "max", "command": "id"})
        secret = client.post(f"/api/action-executions/{execution_id}/analyze", json={"operator": "max", "token": "abc"})

    assert extra.status_code == 422
    assert secret.status_code == 422


def test_large_stdout_is_truncated_in_chat_and_bounded_for_analyzer():
    large = "df -h\n" + ("/dev/sda2 20G 19G 1G 94% /\n" * 1000)
    execution_id = _fixture(stdout=large)
    with TestClient(app) as client:
        attach = client.post(
            f"/api/action-executions/{execution_id}/attach",
            json={"operator": "max", "include_stdout": True},
        )
        analyze = client.post(f"/api/action-executions/{execution_id}/analyze", json={"operator": "max"})

    assert attach.status_code == 200
    assert analyze.status_code == 200
    with SessionLocal() as db:
        attach_msg = db.get(ChatMessage, attach.json()["message_id"])
        analysis_msg = db.get(ChatMessage, analyze.json()["message_id"])
        assert "output truncated for chat" in attach_msg.content
        assert len(attach_msg.content) < 7500
        assert "Analysis of read-only SSH check" in analysis_msg.content


def test_no_new_unsafe_execution_imports_or_calls_are_introduced():
    text = "\n".join(Path(path).read_text(encoding="utf-8") for path in ["app/api/action_executions.py", "app/static/app.js"])
    forbidden = ["subprocess", "os.system", "Popen", "shell=True"]
    for token in forbidden:
        assert token not in text


def test_ui_contains_timeline_execution_controls_without_secret_or_command_inputs():
    js = Path("app/static/app.js").read_text(encoding="utf-8")
    assert "Attach to chat" in js
    assert "Analyze output" in js
    assert "Copy stdout" in js
    assert "View raw" in js
    assert "private key" not in js.lower()
    assert "password" not in js.lower()
    assert "command input" not in js.lower()
