import re
from pathlib import Path


def _ui_text() -> str:
    return Path("app/templates/index.html").read_text(encoding="utf-8") + "\n" + Path("app/static/app.js").read_text(encoding="utf-8")


def test_ssh_profile_ui_exposes_agent_profile_and_host_assignment_flow():
    text = _ui_text()

    assert "SSH Profiles" in text
    assert "+ Add agent profile" in text
    assert "auth_type: \"agent\"" in text
    assert "sudo_mode: \"none\"" in text
    assert "Assign SSH profile" in text
    assert "ssh profile:" in text
    assert "No SSH connection was performed" in text


def test_readiness_blockers_include_actionable_profile_helpers():
    text = _ui_text()

    assert "Assign an SSH profile to this host in the Hosts panel" in text
    assert "agent auth with sudo_mode=none" in text


def test_profile_create_ui_does_not_add_secret_bearing_inputs():
    template = Path("app/templates/index.html").read_text(encoding="utf-8")
    app_js = Path("app/static/app.js").read_text(encoding="utf-8")

    assert not re.search(r"<(input|textarea)[^>]+(password|private_key|token|secret)", template, flags=re.I)
    assert "prompt(\"Password" not in app_js
    assert "prompt(\"Private key" not in app_js
    assert "password_ref" not in app_js
    assert "key_ref" not in app_js


def test_ui_does_not_add_arbitrary_command_controls():
    text = _ui_text().casefold()

    forbidden_phrases = [
        "arbitrary command",
        "command textbox",
        "web terminal",
        "interactive shell",
        "ssh terminal",
    ]
    assert [phrase for phrase in forbidden_phrases if phrase in text] == []
