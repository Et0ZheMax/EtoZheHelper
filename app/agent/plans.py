from dataclasses import dataclass


@dataclass(frozen=True)
class DiagnosticPlan:
    """Text-only diagnostic plan. Commands are suggestions, not executed by the app."""

    topic: str
    commands: tuple[str, ...]
    how_to_read: tuple[str, ...]
    what_not_to_do: tuple[str, ...]


PLANS: dict[str, DiagnosticPlan] = {
    "dns": DiagnosticPlan(
        topic="dns",
        commands=(
            "cat /etc/resolv.conf",
            "resolvectl status",
            "getent hosts example.local",
            "resolvectl query example.local",
            "dig example.local",
            "dig @10.0.0.10 example.local",
        ),
        how_to_read=(
            "FQDN работает, shortname нет → вероятна проблема с search domain/domain search.",
            "`dig` работает, а `getent` нет → проверь NSS, `/etc/nsswitch.conf` или systemd-resolved.",
            "`dig @server` даёт timeout → проверь DNS server, сеть, маршрут или firewall.",
            "Для AD/domain join дополнительно проверь SRV records.",
        ),
        what_not_to_do=(
            "Не менять `/etc/resolv.conf` вслепую: на Ubuntu он часто управляется systemd-resolved/NetworkManager.",
            "Не перезапускать сетевые службы до понимания, какой resolver реально используется.",
        ),
    ),
    "port_connectivity": DiagnosticPlan(
        topic="port_connectivity",
        commands=(
            "getent hosts host.example.local",
            "ip route get 10.0.0.10",
            "nc -vz host.example.local 443",
            "ss -lntp | grep ':443'",
        ),
        how_to_read=(
            "connection refused → host reachable, но service/port закрыт или не слушает.",
            "timeout → возможен route/firewall/drop по пути.",
            "no route → проблема routing/default gateway/VPN.",
            "Порт слушает только на 127.0.0.1 → снаружи он недоступен.",
        ),
        what_not_to_do=(
            "Не открывать firewall-правила без подтверждения, что сервис слушает нужный интерфейс.",
            "Не менять DNS, если `getent hosts` уже возвращает ожидаемый адрес.",
        ),
    ),
    "http_tls": DiagnosticPlan(
        topic="http_tls",
        commands=(
            "curl -I https://host.example.local",
            "curl -vk https://host.example.local",
            "curl -sS -o /dev/null -w 'code=%{http_code} dns=%{time_namelookup} connect=%{time_connect} tls=%{time_appconnect} total=%{time_total}\\n' https://host.example.local",
            "openssl s_client -connect host.example.local:443 -servername host.example.local </dev/null",
        ),
        how_to_read=(
            "401/403 → auth/rights/access policy.",
            "500 → ошибка приложения/backend.",
            "502 → proxy/backend/upstream недоступен или вернул некорректный ответ.",
            "504 → backend timeout.",
            "TLS error → certificate, SNI или trust chain.",
        ),
        what_not_to_do=(
            "Не отключать TLS verification как fix; `-k` использовать только для диагностики.",
            "Не перезапускать web stack до разделения DNS/connect/TLS/app-time.",
        ),
    ),
    "nginx_502": DiagnosticPlan(
        topic="nginx_502",
        commands=(
            "systemctl status nginx --no-pager",
            "sudo nginx -t",
            "sudo tail -n 100 /var/log/nginx/error.log",
            "ss -lntp",
            "curl -v http://127.0.0.1:8080/health",
        ),
        how_to_read=(
            "Сначала проверить backend/upstream health и порт, потом nginx как reverse proxy.",
            "`sudo nginx -t` покажет синтаксис и ошибки include/config; команда может требовать sudo.",
            "`/var/log/nginx/error.log` часто содержит `connect() failed`, `upstream timed out` или DNS ошибки; чтение может требовать sudo.",
            "Если backend не отвечает локально через curl, 502 почти наверняка не лечится правкой nginx.",
        ),
        what_not_to_do=(
            "Не делать restart/reload nginx вслепую до проверки backend/upstream и `nginx -t`.",
            "Не менять upstream URL/ports без сверки с реально слушающими процессами (`ss -lntp`).",
        ),
    ),
    "systemd": DiagnosticPlan(
        topic="systemd",
        commands=(
            "systemctl status service-name --no-pager",
            "systemctl cat service-name",
            "journalctl -u service-name -n 200 --no-pager",
            "systemctl --failed",
            "ss -lntp",
            "df -h",
        ),
        how_to_read=(
            "port conflict → ищи занятый порт через `ss`.",
            "env/config missing → смотри unit через `systemctl cat` и ошибки в journal.",
            "permission denied → права, владелец, AppArmor/SELinux или CapabilityBoundingSet.",
            "no space left → диск/inodes.",
            "restart loop → нужны journal + `systemctl show service-name` для Restart/StartLimit.",
        ),
        what_not_to_do=(
            "Не запускать `daemon-reload`/restart как первый шаг без чтения unit и journal.",
            "Не править unit-файл до понимания точной ошибки запуска.",
        ),
    ),
    "disk_space": DiagnosticPlan(
        topic="disk_space",
        commands=(
            "df -h",
            "df -i",
            "sudo du -xh /var | sort -h | tail -30",
            "journalctl --disk-usage",
            "sudo lsof +L1",
        ),
        how_to_read=(
            "`df -h` full → ищи большие каталоги/логи/артефакты.",
            "`df -i` full → слишком много мелких файлов, даже если GB ещё есть.",
            "`lsof +L1` → удалённые, но открытые файлы продолжают держать место.",
            "Для Docker сначала `docker system df`, но не prune без review.",
        ),
        what_not_to_do=(
            "Не удалять каталоги рекурсивно без понимания владельца данных.",
            "Не запускать `docker system prune --volumes` как первый шаг: volumes могут содержать данные.",
        ),
    ),
    "performance": DiagnosticPlan(
        topic="performance",
        commands=(
            "uptime",
            "nproc",
            "free -h",
            "vmstat 1 5",
            "ps aux --sort=-%cpu | head -20",
            "ps aux --sort=-%mem | head -20",
            "dmesg -T | grep -iE 'oom|killed process' | tail -50",
        ),
        how_to_read=(
            "Сравни load average с `nproc`: load сильно выше CPU может означать CPU или I/O очередь.",
            "Высокий iowait в `vmstat` → disk/storage bottleneck.",
            "OOM/killed process в `dmesg` → memory leak/limits/pressure.",
            "Один процесс в top CPU/MEM → app/process-level issue.",
        ),
        what_not_to_do=(
            "Не убивать процессы до понимания роли процесса и последствий.",
            "Не добавлять ресурсы вслепую без snapshot CPU/RAM/I/O.",
        ),
    ),
    "ssh": DiagnosticPlan(
        topic="ssh",
        commands=(
            "ssh -vvv user@host",
            "nc -vz host 22",
            "systemctl status ssh --no-pager",
            "ss -lntp | grep ':22'",
            "sudo tail -n 100 /var/log/auth.log",
        ),
        how_to_read=(
            "`ssh -vvv` может содержать usernames/hostnames — перед отправкой обезличь вывод.",
            "connection refused → host reachable, но sshd/port закрыт.",
            "connection timed out → route/firewall/drop.",
            "`/var/log/auth.log` покажет причину отказа на сервере и может требовать sudo.",
        ),
        what_not_to_do=(
            "Не вставлять private key, passphrase или полный known_hosts в чат.",
            "Не менять `sshd_config`/firewall без подтверждения server-side причины.",
        ),
    ),
    "apt_dpkg": DiagnosticPlan(
        topic="apt_dpkg",
        commands=(
            "ps aux | grep -E 'apt|dpkg|unattended'",
            "sudo lsof /var/lib/dpkg/lock-frontend",
            "sudo dpkg --audit",
            "apt policy package-name",
            "sudo apt update",
        ),
        how_to_read=(
            "Сначала проверь живой процесс apt/dpkg/unattended-upgrades.",
            "Lock занят живым PID → дождаться или разобраться, что делает процесс.",
            "`dpkg --audit` покажет partially installed/configured packages.",
            "`apt policy` помогает отделить repository/pinning от dependency issue.",
        ),
        what_not_to_do=(
            "Не удалять lock-файл вслепую.",
            "`dpkg --configure -a` и `apt -f install` — remediation, применять только после понимания состояния.",
        ),
    ),
    "permissions_sudo": DiagnosticPlan(
        topic="permissions_sudo",
        commands=(
            "whoami",
            "id",
            "groups",
            "sudo -l",
            "hostname",
            "cat /etc/hostname",
            "cat /etc/hosts",
            "namei -l /path/to/file",
        ),
        how_to_read=(
            "`sudo -l` показывает, что именно разрешено текущему пользователю.",
            "`unable to resolve host` часто означает mismatch между `/etc/hostname` и `/etc/hosts`.",
            "`namei -l` показывает права по всей цепочке каталогов к файлу.",
            "`id`/`groups` помогают понять, есть ли нужная group membership.",
        ),
        what_not_to_do=(
            "Не предлагать и не выполнять `chmod -R 777`.",
            "sudoers менять только через `visudo` и после review.",
        ),
    ),
    "sssd_ad": DiagnosticPlan(
        topic="sssd_ad",
        commands=(
            "realm list",
            "sssctl domain-list",
            "sssctl domain-status example.local",
            "id user@example.local",
            "getent passwd user@example.local",
            "kinit user@example.local",
            "dig _ldap._tcp.dc._msdcs.example.local SRV",
        ),
        how_to_read=(
            "Проверь DNS SRV records для AD discovery.",
            "Проверь время/NTP: Kerberos чувствителен к clock skew.",
            "`kinit` отделяет Kerberos/password проблему от NSS/SSSD.",
            "Проверь realm permit/access control, если auth работает, а login запрещён.",
        ),
        what_not_to_do=(
            "Не сбрасывать sssd cache первым шагом.",
            "Не делать re-join domain до проверки DNS, времени, Kerberos и access policy.",
        ),
    ),
    "cups_printers": DiagnosticPlan(
        topic="cups_printers",
        commands=(
            "systemctl status cups --no-pager",
            "lpstat -t",
            "lpstat -v",
            "lpq -P printer-name",
            "journalctl -u cups -n 100 --no-pager",
            "nc -vz printer.example.local 9100",
        ),
        how_to_read=(
            "Queue paused/stuck → смотри `lpstat -t` и `lpq`.",
            "Printer unreachable → DNS/network/port 9100/515/631.",
            "Missing PPD/filter/rastertoufr2 → ошибка появится в CUPS journal/log.",
            "Разделяй проблему очереди CUPS и доступность самого принтера.",
        ),
        what_not_to_do=(
            "Не удалять очередь/PPD до сохранения текущей конфигурации.",
            "Не переустанавливать драйвер без проверки CUPS logs и reachability принтера.",
        ),
    ),
    "docker": DiagnosticPlan(
        topic="docker",
        commands=(
            "docker ps",
            "docker ps -a",
            "docker compose ps",
            "docker compose logs --tail=100",
            "docker system df",
            "docker network ls",
        ),
        how_to_read=(
            "Exited/restarting container → смотри app logs и exit code.",
            "Для 500/502 смотри app logs + dependencies (DB/cache/backend network).",
            "`docker system df` показывает занятое место без удаления данных.",
            "Networks/ports в `compose ps` помогают отделить app issue от publish/network issue.",
        ),
        what_not_to_do=(
            "Не предлагать `docker system prune --volumes` как первый шаг: volume может содержать данные.",
            "Не пересоздавать контейнеры до сохранения logs/config и понимания stateful volumes.",
        ),
    ),
    "generic": DiagnosticPlan(
        topic="generic",
        commands=(
            "hostnamectl",
            "uptime",
            "ip -br a",
            "ip r",
            "resolvectl status",
            "df -h",
            "df -i",
            "free -h",
            "systemctl --failed",
            "journalctl -p warning..alert -n 100 --no-pager",
        ),
        how_to_read=(
            "Начни с фактов о хосте, uptime, сети, DNS, диске, памяти и failed units.",
            "Если обнаружится конкретный симптом (DNS/systemd/disk/http), сузь диагностику до соответствующей темы.",
            "Warnings/errors из journal используй как указатель на сервис или подсистему.",
        ),
        what_not_to_do=(
            "Не выполнять remediation до классификации симптома и сбора read-only фактов.",
            "Не отправлять секреты, токены, cookies, private keys и персональные данные.",
        ),
    ),
}


def get_plan(topic_key: str) -> DiagnosticPlan:
    return PLANS.get(topic_key, PLANS["generic"])
