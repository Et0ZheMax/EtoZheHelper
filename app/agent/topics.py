from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Topic:
    """A deterministic troubleshooting topic detected from a user symptom."""

    key: str
    triggers: tuple[str, ...]
    search_hints: str


TOPICS: tuple[Topic, ...] = (
    Topic(
        key="nginx_502",
        triggers=("nginx 502", "502 nginx", "bad gateway", "upstream", "reverse proxy"),
        search_hints="nginx 502 bad gateway upstream backend curl",
    ),
    Topic(
        key="sssd_ad",
        triggers=("sssd", "realm", "realmd", "ad", "domain join", "kerberos", "kinit", "id user", "getent passwd"),
        search_hints="sssd realm realmd ad domain join kerberos kinit getent passwd dns srv ntp",
    ),
    Topic(
        key="cups_printers",
        triggers=("cups", "printer", "lpadmin", "lpstat", "lpq", "печать", "принтер", "rastertoufr2", "ppd"),
        search_hints="cups printer lpstat lpq ppd filter port 9100 journalctl",
    ),
    Topic(
        key="apt_dpkg",
        triggers=("apt", "dpkg", "lock", "пакет не ставится", "dependencies", "repository", "apt update"),
        search_hints="apt dpkg lock dependencies repository unattended dpkg audit",
    ),
    Topic(
        key="ssh",
        triggers=("ssh", "sshd", "ssh permission denied", "permission denied publickey", "publickey", "known_hosts", "host key verification", "ssh connection refused", "ssh connection timed out", "port 22", ":22"),
        search_hints="ssh sshd publickey known_hosts auth.log port 22 connection refused timeout",
    ),
    Topic(
        key="permissions_sudo",
        triggers=("sudo", "permission denied", "права", "chmod", "chown", "unable to resolve host", "sudoers"),
        search_hints="sudo permission denied sudoers chmod chown /etc/hosts hostname namei",
    ),
    Topic(
        key="docker",
        triggers=("docker", "compose", "container", "контейнер", "image", "volume", "docker logs", "docker ps"),
        search_hints="docker compose container logs ps volume network system df 500 502",
    ),
    Topic(
        key="systemd",
        triggers=("systemd", "systemctl", "сервис не стартует", "failed", "unit", "journalctl", "daemon-reload"),
        search_hints="systemd service journalctl failed unit",
    ),
    Topic(
        key="disk_space",
        triggers=("место", "диск", "disk full", "no space left", "inode", "df", "du", "логи забили"),
        search_hints="disk full no space left inode df du lsof journalctl disk usage",
    ),
    Topic(
        key="performance",
        triggers=("тормозит", "медленно", "load", "cpu", "ram", "memory", "oom", "iowait", "performance"),
        search_hints="performance load cpu ram memory oom iowait vmstat ps free uptime",
    ),
    Topic(
        key="dns",
        triggers=(
            "dns",
            "resolv",
            "resolved",
            "resolvectl",
            "nslookup",
            "dig",
            "не резолвится",
            "имя не находится",
            "shortname",
            "fqdn",
            "domain search",
        ),
        search_hints="dns resolvectl resolved getent dig",
    ),
    Topic(
        key="http_tls",
        triggers=("curl", "http", "https", "tls", "certificate", "сертификат", "ssl", "403", "404", "500", "502", "503", "504", "api"),
        search_hints="curl http https tls certificate ssl status code api 500 502 504",
    ),
    Topic(
        key="port_connectivity",
        triggers=("порт", "port", "connection refused", "timeout", "nc", "telnet", "не подключается", "443", "80", "8080", "22"),
        search_hints="port connectivity nc telnet connection refused timeout route ss listen",
    ),
)

GENERIC_TOPIC = Topic(
    key="generic",
    triggers=(),
    search_hints="linux troubleshooting hostnamectl uptime ip route resolvectl df free systemctl journalctl",
)


def _matches_trigger(normalized_message: str, tokens: set[str], trigger: str) -> bool:
    normalized_trigger = trigger.casefold()
    if len(normalized_trigger) <= 2 and normalized_trigger.isalnum():
        return normalized_trigger in tokens
    return normalized_trigger in normalized_message


def detect_topic(message: str) -> Topic:
    """Detect a topic via ordered keyword matching, falling back to generic."""

    normalized = message.casefold()
    tokens = set(re.findall(r"[\wа-яё]+", normalized, flags=re.UNICODE))
    for topic in TOPICS:
        if any(_matches_trigger(normalized, tokens, trigger) for trigger in topic.triggers):
            return topic
    return GENERIC_TOPIC
