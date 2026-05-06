from app.agent.assistant import DeterministicAssistant
from app.agent.topics import detect_topic
from app.kb.models import KnowledgeDocument


def make_assistant() -> DeterministicAssistant:
    documents = [
        KnowledgeDocument(
            path="knowledge_base/02-linux/03-dns-deep-dive.md",
            title="DNS deep dive",
            content="resolvectl getent dig DNS troubleshooting",
            tags=["dns", "linux"],
            domain="linux",
        ),
        KnowledgeDocument(
            path="knowledge_base/02-linux/04-systemd-service-debug.md",
            title="Systemd service debug",
            content="systemctl journalctl failed unit service troubleshooting",
            tags=["systemd"],
            domain="linux",
        ),
        KnowledgeDocument(
            path="knowledge_base/02-linux/07-storage-disk-inodes-io.md",
            title="Disk and inodes",
            content="df du inode no space left disk troubleshooting",
            tags=["disk"],
            domain="linux",
        ),
        KnowledgeDocument(
            path="knowledge_base/02-linux/02-curl-http-tls.md",
            title="HTTP and nginx backend",
            content="nginx 502 bad gateway upstream backend curl troubleshooting",
            tags=["nginx", "http"],
            domain="linux",
        ),
    ]
    return DeterministicAssistant(documents=documents, max_results=3)


def answer_for(message: str) -> str:
    answer, _sources = make_assistant().answer(message)
    return answer


def test_dns_query_returns_dns_plan_commands():
    answer = answer_for("Не работает DNS на Ubuntu")

    assert "Похоже, это тема: `dns`" in answer
    assert "resolvectl status" in answer
    assert "getent hosts" in answer


def test_systemd_query_returns_systemd_plan_commands():
    answer = answer_for("Сервис не стартует в systemd failed unit")

    assert "Похоже, это тема: `systemd`" in answer
    assert "systemctl status" in answer
    assert "journalctl -u" in answer


def test_disk_query_returns_disk_plan_commands():
    answer = answer_for("На сервере no space left и логи забили диск")

    assert "Похоже, это тема: `disk_space`" in answer
    assert "df -h" in answer
    assert "df -i" in answer


def test_nginx_502_query_returns_nginx_backend_plan():
    answer = answer_for("nginx отдаёт 502 bad gateway")

    assert "Похоже, это тема: `nginx_502`" in answer
    assert "nginx -t" in answer
    assert "curl" in answer
    assert "backend" in answer
    assert "upstream" in answer


def test_unknown_query_returns_generic_plan():
    answer = answer_for("Странное поведение без понятных симптомов")

    assert "Похоже, это тема: `generic`" in answer
    assert "hostnamectl" in answer
    assert "systemctl --failed" in answer


def test_detect_topic_prefers_specific_nginx_over_http_502():
    assert detect_topic("nginx 502 bad gateway").key == "nginx_502"


def test_detect_topic_handles_nginx_502_without_broad_nginx_trigger():
    assert detect_topic("nginx отдаёт 502").key == "nginx_502"


def test_detect_topic_nginx_failed_routes_to_systemd_not_nginx_502():
    assert detect_topic("nginx не стартует systemd failed").key == "systemd"


def test_detect_topic_nginx_certificate_expired_routes_to_http_tls():
    assert detect_topic("nginx certificate expired").key == "http_tls"


def test_detect_topic_prefers_specific_ssh_over_generic_permission_denied():
    assert detect_topic("ssh permission denied publickey").key == "ssh"


def test_detect_topic_handles_502_nginx_reverse_order():
    assert detect_topic("Сайт отдаёт 502 nginx").key == "nginx_502"


def test_detect_topic_routes_file_permission_denied_to_permissions_sudo():
    assert detect_topic("permission denied при доступе к файлу").key == "permissions_sudo"


def test_detect_topic_routes_chmod_chown_permission_denied_to_permissions_sudo():
    assert detect_topic("permission denied chmod chown права").key == "permissions_sudo"


def test_detect_topic_matches_ad_as_word_only():
    assert detect_topic("AD domain join не проходит").key == "sssd_ad"


def test_detect_topic_matches_bad_gateway_as_nginx_502():
    assert detect_topic("bad gateway без nginx").key == "nginx_502"


def test_detect_topic_routes_generic_connection_refused_to_port_connectivity():
    assert detect_topic("connection refused на postgres 5432").key == "port_connectivity"


def test_detect_topic_routes_generic_timeout_to_port_connectivity():
    assert detect_topic("connection timed out до 10.0.0.10:443").key == "port_connectivity"


def test_detect_topic_routes_ssh_connection_refused_to_ssh():
    assert detect_topic("ssh connection refused").key == "ssh"


def test_detect_topic_routes_ssh_timeout_to_ssh():
    assert detect_topic("ssh connection timed out").key == "ssh"


def test_detect_topic_routes_port_22_to_ssh_or_port_consistently():
    # If message explicitly says SSH, it must be ssh.
    assert detect_topic("ssh порт 22 не отвечает").key == "ssh"


def test_assistant_analyzes_diagnostic_output_instead_of_repeating_plan():
    answer = answer_for(
        """curl -I https://app.example.local
HTTP/1.1 502 Bad Gateway

sudo tail -n 100 /var/log/nginx/error.log
connect() failed (111: Connection refused) while connecting to upstream
"""
    )

    assert "Похоже, ты прислал диагностический вывод" in answer
    assert "Findings" in answer
    assert "Гипотезы" in answer
    assert "upstream" in answer


def test_assistant_regular_symptom_still_returns_topic_plan():
    answer = answer_for("nginx отдаёт 502")

    assert "Похоже, это тема: `nginx_502`" in answer
    assert "Безопасный старт диагностики" in answer
    assert "Похоже, ты прислал диагностический вывод" not in answer
