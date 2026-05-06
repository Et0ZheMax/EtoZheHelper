import re

from app.agent.findings import AnalysisResult, Finding

_OUTPUT_MARKERS = (
    "systemctl status",
    "journalctl",
    "resolvectl status",
    "getent hosts",
    "dig ",
    "curl -",
    "http/",
    "connection refused",
    "connection timed out",
    "df -h",
    "no space left on device",
    "loaded:",
    "active:",
    "failed",
    "listen",
    "docker ps",
    "exited",
    "permission denied",
    "unable to resolve host",
)

_ANALYZER_TOPIC_ORDER = (
    "dns",
    "systemd",
    "nginx_502",
    "http_tls",
    "disk_space",
    "performance",
    "ssh",
    "docker",
)


def looks_like_diagnostic_output(message: str) -> bool:
    """Return True when user text looks like pasted command output, not a fresh symptom."""
    text = message.strip()
    if not text:
        return False

    lower = text.lower()
    marker_hits = sum(1 for marker in _OUTPUT_MARKERS if marker in lower)
    line_count = len(text.splitlines())

    if line_count >= 2 and marker_hits >= 1:
        return True
    if line_count >= 4 and re.search(r"^(\S+\s+){0,3}(loaded:|active:|dns servers:|filesystem\s+|mem:|swap:)", lower, re.MULTILINE):
        return True
    if marker_hits >= 2:
        return True
    return False


def analyze_output(message: str, topic_key: str = "generic") -> AnalysisResult:
    """Analyze sanitized command output with deterministic domain analyzers."""
    findings: list[Finding] = []
    for analyzer in (
        _analyze_dns,
        _analyze_systemd,
        _analyze_http,
        _analyze_disk,
        _analyze_performance,
        _analyze_ssh,
        _analyze_docker,
    ):
        findings.extend(analyzer(message))

    topic = _choose_topic(topic_key, findings)
    hypotheses = _collect_unique(f.interpretation for f in findings)
    next_checks = _collect_unique(step for finding in findings for step in finding.next_steps)
    return AnalysisResult(topic=topic, findings=tuple(findings), hypotheses=hypotheses, next_checks=next_checks)


def _choose_topic(topic_key: str, findings: list[Finding]) -> str:
    if topic_key != "generic":
        return topic_key
    titles = "\n".join(f.title.lower() for f in findings)
    for key in _ANALYZER_TOPIC_ORDER:
        if key.split("_")[0] in titles or (key == "nginx_502" and "502" in titles):
            return key
    return topic_key


def _collect_unique(items: object) -> tuple[str, ...]:
    result: list[str] = []
    for item in items:
        if isinstance(item, str) and item and item not in result:
            result.append(item)
    return tuple(result)


def _snippet(message: str, patterns: tuple[str, ...], max_lines: int = 6) -> str:
    lines = [line.rstrip() for line in message.splitlines()]
    selected: list[str] = []
    lowered_patterns = tuple(pattern.lower() for pattern in patterns)
    for index, line in enumerate(lines):
        lower = line.lower()
        if any(pattern in lower for pattern in lowered_patterns):
            if index > 0 and lines[index - 1].strip() and lines[index - 1] not in selected:
                selected.append(lines[index - 1])
            selected.append(line)
        if len(selected) >= max_lines:
            break
    return "\n".join(selected[:max_lines]) or "Явный фрагмент не выделен; смотри присланный обезличенный вывод."


def _has_dig_a_record(text: str) -> bool:
    return bool(re.search(r"\bIN\s+A\s+(?:\d{1,3}\.){3}\d{1,3}\b", text, re.IGNORECASE))


def _has_getent_without_result(text: str) -> bool:
    lower = text.lower()
    if "getent hosts" not in lower:
        return False
    if "<empty>" in lower or "not found" in lower or "temporary failure in name resolution" in lower:
        return True
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if "getent hosts" in line.lower():
            following = [candidate.strip() for candidate in lines[index + 1 : index + 3] if candidate.strip()]
            if not following or (following and following[0].startswith(("dig ", "resolvectl ", "cat ", "$", "#"))):
                return True
    return False


def _analyze_dns(message: str) -> list[Finding]:
    findings: list[Finding] = []
    lower = message.lower()
    if "nameserver 127.0.0.53" in lower:
        findings.append(
            Finding(
                severity="info",
                title="DNS: используется systemd-resolved stub 127.0.0.53",
                evidence=_snippet(message, ("nameserver 127.0.0.53",)),
                interpretation="127.0.0.53 сам по себе не ошибка: это локальный stub systemd-resolved; важны upstream DNS Servers и routing domain.",
                next_steps=("resolvectl status", "resolvectl query example.local", "grep '^hosts:' /etc/nsswitch.conf"),
            )
        )
    if _has_dig_a_record(message) and _has_getent_without_result(message):
        findings.append(
            Finding(
                severity="warning",
                title="DNS: `dig` видит A-запись, но `getent`/shortname не дал результата",
                evidence=_snippet(message, ("getent hosts", "<empty>", " in a ", "temporary failure")),
                interpretation="Вероятна проблема не с самим DNS-сервером, а с NSS/search domain/systemd-resolved path.",
                next_steps=("grep '^hosts:' /etc/nsswitch.conf", "resolvectl query server01", "resolvectl query server01.example.local"),
            )
        )
    if "nxdomain" in lower:
        findings.append(Finding("warning", "DNS: NXDOMAIN", _snippet(message, ("nxdomain",)), "DNS-сервер ответил, но записи для имени нет или запрошена неверная зона/имя.", ("dig +trace example.local", "resolvectl query example.local")))
    if "servfail" in lower:
        findings.append(Finding("warning", "DNS: SERVFAIL", _snippet(message, ("servfail",)), "DNS-сервер не смог корректно завершить рекурсию или обработку зоны.", ("dig @dns-server example.local", "resolvectl status")))
    if "connection timed out; no servers could be reached" in lower or "communications error" in lower:
        findings.append(Finding("critical", "DNS: timeout до DNS-сервера", _snippet(message, ("connection timed out", "communications error")), "Похоже на недоступный DNS server, network path или firewall/drop до DNS.", ("ip route get DNS_SERVER", "nc -vz DNS_SERVER 53", "resolvectl status")))
    if "temporary failure in name resolution" in lower:
        findings.append(Finding("warning", "DNS: temporary failure in name resolution", _snippet(message, ("temporary failure",)), "Resolver временно не смог получить ответ; проверь upstream DNS, link state и resolved status.", ("resolvectl status", "resolvectl query example.local")))
    return findings


def _analyze_systemd(message: str) -> list[Finding]:
    findings: list[Finding] = []
    lower = message.lower()
    if "loaded:" in lower and "masked" in lower:
        findings.append(Finding("warning", "systemd: unit masked", _snippet(message, ("loaded:", "masked")), "Unit замаскирован; unmask — это remediation, сначала нужно понять, кто и зачем замаскировал unit.", ("systemctl cat service-name", "systemctl status service-name --no-pager")))
    if "active: failed" in lower or "failed to start" in lower:
        findings.append(Finding("warning", "systemd: service failed", _snippet(message, ("active:", "failed to start")), "Сервис завершился ошибкой; первопричина обычно выше в journal/status.", ("journalctl -u service-name -n 200 --no-pager", "systemctl cat service-name")))
    if "address already in use" in lower:
        findings.append(Finding("critical", "systemd: port conflict / Address already in use", _snippet(message, ("address already in use",)), "Сервис не смог занять порт; вероятен конфликт с уже слушающим процессом.", ("ss -lntp", "systemctl status service-name --no-pager")))
    if "no such file or directory" in lower:
        findings.append(Finding("warning", "systemd: missing file/path", _snippet(message, ("no such file",)), "Вероятен неверный ExecStart/path/env или отсутствующий файл.", ("systemctl cat service-name", "namei -l /path/from/error")))
    if "permission denied" in lower:
        findings.append(Finding("warning", "systemd: Permission denied", _snippet(message, ("permission denied",)), "Проверь пользователя unit, права, AppArmor/SELinux и capabilities.", ("systemctl cat service-name", "namei -l /path/from/error", "journalctl -u service-name -n 200 --no-pager")))
    if "start request repeated too quickly" in lower:
        findings.append(Finding("warning", "systemd: restart loop / StartLimit", _snippet(message, ("start request repeated",)), "Сервис быстро падает и упирается в StartLimit; нужна ошибка первой попытки выше в journal.", ("journalctl -u service-name -b --no-pager", "systemctl show service-name -p Restart -p StartLimitBurst -p StartLimitIntervalUSec")))
    return findings


def _analyze_http(message: str) -> list[Finding]:
    findings: list[Finding] = []
    lower = message.lower()
    status_map = {
        "401": ("warning", "HTTP: 401 Unauthorized", "Сервис отвечает, но запрос не аутентифицирован или credential не принят.", ("curl -vk https://host.example.local",)),
        "403": ("warning", "HTTP: 403 Forbidden", "Сервис отвечает, но доступ запрещён политикой/ACL/authz.", ("curl -vk https://host.example.local",)),
        "404": ("info", "HTTP: 404 Not Found", "Endpoint/route не найден; проверь URL, routing и location rules.", ("curl -I https://host.example.local/expected-path",)),
        "500": ("warning", "HTTP: 500 application error", "Backend/application вернул внутреннюю ошибку; нужны app logs.", ("journalctl -u backend-service -n 100 --no-pager", "docker compose logs --tail=100")),
        "502": ("critical", "HTTP: 502 Bad Gateway / upstream", "Прокси не получил корректный ответ от backend/upstream; вероятно backend недоступен, упал или слушает не там.", ("ss -lntp", "systemctl status backend-service --no-pager", "curl -v http://127.0.0.1:8080/health")),
        "503": ("warning", "HTTP: 503 Service Unavailable", "Сервис/балансировщик временно недоступен или backend pool пуст.", ("systemctl status backend-service --no-pager", "curl -v http://127.0.0.1:8080/health")),
        "504": ("critical", "HTTP: 504 Gateway Timeout", "Proxy дождался timeout от backend/upstream; проверь latency, hung requests и backend health.", ("ss -lntp", "journalctl -u backend-service -n 100 --no-pager")),
    }
    for code, data in status_map.items():
        if re.search(rf"http/\d(?:\.\d)?\s+{code}\b", lower):
            severity, title, interpretation, next_steps = data
            findings.append(Finding(severity, title, _snippet(message, (f"http/1.1 {code}", f"http/2 {code}", f"http/1.0 {code}")), interpretation, next_steps))
    if "ssl certificate problem" in lower or "certificate has expired" in lower:
        findings.append(Finding("warning", "HTTP/TLS: certificate problem", _snippet(message, ("ssl certificate problem", "certificate has expired")), "Проблема TLS trust chain, SAN/SNI или срока действия сертификата.", ("openssl s_client -connect host.example.local:443 -servername host.example.local </dev/null", "curl -vk https://host.example.local")))
    if "could not resolve host" in lower:
        findings.append(Finding("warning", "HTTP/curl: Could not resolve host", _snippet(message, ("could not resolve host",)), "curl не смог резолвить имя; сначала проверь DNS.", ("getent hosts host.example.local", "resolvectl query host.example.local")))
    if "connection refused" in lower:
        findings.append(Finding("critical", "HTTP/TCP: Connection refused", _snippet(message, ("connection refused",)), "TCP-доступ есть, но порт закрыт или сервис не слушает.", ("ss -lntp", "systemctl status service-name --no-pager")))
    if "operation timed out" in lower:
        findings.append(Finding("critical", "HTTP/TCP: Operation timed out", _snippet(message, ("operation timed out",)), "Похоже на network/firewall/drop или зависший backend path.", ("ip route get HOST", "nc -vz host.example.local 443")))
    return findings


def _analyze_disk(message: str) -> list[Finding]:
    findings: list[Finding] = []
    lower = message.lower()
    if "no space left on device" in lower:
        findings.append(Finding("critical", "disk: No space left on device", _snippet(message, ("no space left",)), "Файловая система или inodes исчерпаны; запись новых данных невозможна.", ("df -h", "df -i", "sudo du -xh /var | sort -h | tail -30")))
    if "100%" in message and ("use%" in lower or re.search(r"\s/\S*\s*$", message, re.MULTILINE)):
        findings.append(Finding("critical", "disk: filesystem 100% full", _snippet(message, ("use%", "100%")), "Файловая система заполнена; ищи большие каталоги, логи, артефакты или Docker layers.", ("sudo du -xh / | sort -h | tail -30", "journalctl --disk-usage", "sudo lsof +L1")))
    if "iuse%" in lower and "100%" in message:
        findings.append(Finding("critical", "disk: inode usage 100%", _snippet(message, ("iuse%", "100%")), "Закончились inodes: обычно слишком много мелких файлов.", ("df -i", "sudo find /var -xdev -type f | cut -d/ -f2-4 | sort | uniq -c | sort -n | tail")))
    if "deleted" in lower and ("lsof" in lower or "+l1" in lower):
        findings.append(Finding("warning", "disk: deleted open files", _snippet(message, ("deleted",)), "Удалённые файлы всё ещё удерживаются открытым процессом; место освободится после закрытия fd/restart конкретного процесса.", ("sudo lsof +L1",)))
    if "journalctl --disk-usage" in lower:
        findings.append(Finding("info", "disk: journal usage captured", _snippet(message, ("journalctl --disk-usage", "archived and active journals")), "Если journal занимает много места, проверь log retention/vacuum policy перед очисткой.", ("journalctl --disk-usage", "grep -R SystemMaxUse /etc/systemd/journald.conf /etc/systemd/journald.conf.d 2>/dev/null")))
    return findings


def _analyze_performance(message: str) -> list[Finding]:
    findings: list[Finding] = []
    lower = message.lower()
    if "load average:" in lower:
        findings.append(Finding("info", "performance: load average present", _snippet(message, ("load average:",)), "Сравни load average с количеством CPU; load сильно выше CPU указывает на CPU или I/O saturation.", ("nproc", "vmstat 1 5", "ps aux --sort=-%cpu | head -20")))
    if "oom" in lower or "killed process" in lower:
        findings.append(Finding("critical", "performance: OOM / killed process", _snippet(message, ("oom", "killed process")), "Есть признаки memory pressure, leak или слишком жёстких memory limits.", ("free -h", "dmesg -T | grep -iE 'oom|killed process' | tail -50", "ps aux --sort=-%mem | head -20")))
    if re.search(r"\bswap:\b", lower):
        findings.append(Finding("info", "performance: swap snapshot present", _snippet(message, ("swap:",)), "Если swap активно занят/растёт, вероятно давление на RAM.", ("free -h", "vmstat 1 5")))
    if re.search(r"\bwa\b", lower) and re.search(r"\b([5-9]\d|100)\b", lower):
        findings.append(Finding("warning", "performance: possible high iowait", _snippet(message, (" wa",)), "Высокий iowait указывает на storage bottleneck или блокировки на диске.", ("vmstat 1 5", "iostat -xz 1 5")))
    return findings


def _analyze_ssh(message: str) -> list[Finding]:
    findings: list[Finding] = []
    lower = message.lower()
    if "permission denied (publickey)" in lower:
        findings.append(Finding("warning", "SSH: public key auth denied", _snippet(message, ("permission denied (publickey)",)), "Ключ не принят сервером: проверь выбранный ключ, authorized_keys и права ~/.ssh на сервере.", ("ssh -vvv user@host", "sudo tail -n 100 /var/log/auth.log")))
    if "permission denied, please try again" in lower:
        findings.append(Finding("warning", "SSH: password auth denied", _snippet(message, ("permission denied, please try again",)), "Пароль/учётка не приняты или password auth запрещён политикой sshd/PAM.", ("sudo tail -n 100 /var/log/auth.log", "sshd -T | grep -i passwordauthentication")))
    if "host key verification failed" in lower:
        findings.append(Finding("warning", "SSH: host key verification failed", _snippet(message, ("host key verification failed",)), "known_hosts не совпал с ключом сервера; это может быть легитимная переустановка или риск MITM.", ("ssh-keygen -F host.example.local", "ssh-keyscan -H host.example.local")))
    if "too many authentication failures" in lower:
        findings.append(Finding("warning", "SSH: too many authentication failures", _snippet(message, ("too many authentication failures",)), "Клиент предлагает слишком много ключей до нужного; укажи конкретный IdentityFile/IdentitiesOnly для диагностики.", ("ssh -vvv -o IdentitiesOnly=yes -i /path/to/key user@host",)))
    if "authentication refused: bad ownership or modes" in lower:
        findings.append(Finding("warning", "SSH: bad ownership or modes", _snippet(message, ("bad ownership or modes",)), "sshd отказал из-за прав/владельца home или ~/.ssh/authorized_keys.", ("namei -l ~/.ssh/authorized_keys", "stat -c '%U %G %a %n' ~ ~/.ssh ~/.ssh/authorized_keys")))
    if "connection refused" in lower and "ssh" in lower:
        findings.append(Finding("critical", "SSH/TCP: Connection refused", _snippet(message, ("connection refused",)), "Host reachable, но sshd/порт закрыт или не слушает.", ("nc -vz host 22", "systemctl status ssh --no-pager", "ss -lntp | grep ':22'")))
    if "connection timed out" in lower and "ssh" in lower:
        findings.append(Finding("critical", "SSH/TCP: Connection timed out", _snippet(message, ("connection timed out",)), "Похоже на route/firewall/drop до SSH.", ("ip route get HOST", "nc -vz host 22")))
    return findings


def _analyze_docker(message: str) -> list[Finding]:
    findings: list[Finding] = []
    lower = message.lower()
    if "conflict. the container name" in lower:
        findings.append(Finding("warning", "Docker: container name conflict", _snippet(message, ("conflict. the container name",)), "Контейнер с таким именем уже существует; нужно понять, старый ли это контейнер и есть ли в нём нужные данные/logs.", ("docker ps -a", "docker inspect CONTAINER_NAME")))
    if "port is already allocated" in lower:
        findings.append(Finding("critical", "Docker: port is already allocated", _snippet(message, ("port is already allocated",)), "Порт уже занят другим контейнером или процессом на host.", ("docker ps --format 'table {{.Names}}\t{{.Ports}}'", "ss -lntp")))
    if "cannot connect to the docker daemon" in lower:
        findings.append(Finding("critical", "Docker: daemon unavailable", _snippet(message, ("cannot connect to the docker daemon",)), "Docker daemon/socket недоступен или у пользователя нет прав к socket.", ("systemctl status docker --no-pager", "docker context ls", "id")))
    if "oomkilled" in lower:
        findings.append(Finding("critical", "Docker: OOMKilled", _snippet(message, ("oomkilled",)), "Контейнер был убит из-за memory limit/pressure.", ("docker inspect CONTAINER --format '{{.State.OOMKilled}} {{.State.ExitCode}}'", "docker stats --no-stream")))
    if "restarting" in lower or "exited" in lower:
        findings.append(Finding("warning", "Docker: exited/restarting container", _snippet(message, ("restarting", "exited")), "Контейнер завершился или уходит в restart loop; первопричина обычно в logs и exit code.", ("docker ps -a", "docker logs --tail=100 CONTAINER")))
    if "no space left on device" in lower and "docker" in lower:
        findings.append(Finding("critical", "Docker: no space left on device", _snippet(message, ("no space left",)), "Docker storage или filesystem host заполнены; не запускай prune volumes без review.", ("docker system df", "df -h", "docker ps -a")))
    return findings
