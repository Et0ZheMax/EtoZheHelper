from app.agent.analyzer import analyze_output, looks_like_diagnostic_output


def titles(result):
    return "\n".join(finding.title for finding in result.findings).lower()


def interpretations(result):
    return "\n".join(finding.interpretation for finding in result.findings).lower()


def test_looks_like_diagnostic_output_detects_multiline_command_output():
    message = """resolvectl status
DNS Servers: 10.0.0.10
DNS Domain: ~.
"""

    assert looks_like_diagnostic_output(message)


def test_dns_dig_a_record_but_getent_empty_finds_nss_shortname_issue():
    message = """cat /etc/resolv.conf
nameserver 127.0.0.53

resolvectl status
DNS Servers: 10.0.0.10
DNS Domain: ~.

getent hosts server01
<empty>

dig server01.example.local
server01.example.local. 300 IN A 10.0.0.20
"""

    result = analyze_output(message, "dns")

    assert "dig" in titles(result)
    assert "getent" in titles(result)
    assert "nss" in interpretations(result)
    assert "grep '^hosts:' /etc/nsswitch.conf" in result.next_checks


def test_systemd_failed_address_in_use_finds_port_conflict():
    message = """systemctl status demo.service
Loaded: loaded (/etc/systemd/system/demo.service; enabled)
Active: failed (Result: exit-code)
Main PID: 123 (code=exited, status=1/FAILURE)
Failed to start demo.service
listen tcp :8080: bind: Address already in use
"""

    result = analyze_output(message, "systemd")

    assert "address already in use" in titles(result)
    assert "порт" in interpretations(result) or "port" in interpretations(result)
    assert "ss -lntp" in result.next_checks


def test_http_502_finds_proxy_backend_upstream_issue():
    message = """curl -I https://app.example.local
HTTP/1.1 502 Bad Gateway

connect() failed (111: Connection refused) while connecting to upstream
"""

    result = analyze_output(message, "nginx_502")

    assert "502" in titles(result)
    assert "upstream" in interpretations(result)
    assert "systemctl status backend-service --no-pager" in result.next_checks


def test_disk_df_100_percent_finds_filesystem_full():
    message = """df -h
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1        20G   20G     0 100% /
"""

    result = analyze_output(message, "disk_space")

    assert "filesystem 100% full" in titles(result)
    assert "заполнена" in interpretations(result)


def test_ssh_permission_denied_publickey_finds_public_key_auth_issue():
    message = """ssh user@host
Permission denied (publickey).
"""

    result = analyze_output(message, "ssh")

    assert "public key" in titles(result)
    assert "authorized_keys" in interpretations(result)


def test_docker_container_name_conflict_finds_name_conflict():
    message = """docker run --name app nginx
Conflict. The container name "/app" is already in use by container "abc123".
"""

    result = analyze_output(message, "docker")

    assert "container name conflict" in titles(result)
    assert "docker ps -a" in result.next_checks


def test_generic_http_502_output_chooses_nginx_502_topic():
    result = analyze_output("curl -I https://app.example.local\nHTTP/1.1 502 Bad Gateway\n", "generic")

    assert result.topic == "nginx_502"
