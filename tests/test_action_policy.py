import pytest

from app.actions.policy import InvalidActionParamsError, UnknownActionError, propose_action


def test_systemd_status_preview():
    proposal = propose_action("systemd_status", {"service": "nginx"})

    assert proposal.command_preview == "systemctl status nginx --no-pager"
    assert proposal.execution_enabled is False
    assert proposal.read_only is True
    assert proposal.requires_approval is True


def test_unknown_action_rejected():
    with pytest.raises(UnknownActionError):
        propose_action("rm_rf", {})


@pytest.mark.parametrize("service", ["nginx; rm -rf /", "nginx && whoami"])
def test_unsafe_service_rejected(service):
    with pytest.raises(InvalidActionParamsError):
        propose_action("systemd_status", {"service": service})


@pytest.mark.parametrize("url", ["file:///etc/passwd", "https://example.com;whoami"])
def test_unsafe_url_rejected(url):
    with pytest.raises(InvalidActionParamsError):
        propose_action("curl_head", {"url": url})


@pytest.mark.parametrize("port", [0, 65536])
def test_port_out_of_range_rejected(port):
    with pytest.raises(InvalidActionParamsError):
        propose_action("tcp_probe", {"host": "example.com", "port": port})


@pytest.mark.parametrize("lines", [19, 501])
def test_lines_out_of_range_rejected(lines):
    with pytest.raises(InvalidActionParamsError):
        propose_action("journal_tail", {"service": "nginx", "lines": lines})


def test_docker_container_unsafe_rejected():
    with pytest.raises(InvalidActionParamsError):
        propose_action("docker_logs_tail", {"container": "web;whoami", "lines": 100})


def test_no_param_action_works():
    proposal = propose_action("disk_usage", {})

    assert proposal.command_preview == "df -h"
    assert proposal.params == {}
