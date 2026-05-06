---
type: index
domain: linux
tags: [linux, troubleshooting, runbooks, senior]
risk: low
requires_root: false
---

# Linux Troubleshooting — expanded senior pack

Эта папка — практическая база для диагностики Linux/Ubuntu/Astra/Debian-like систем. Формат специально сделан так, чтобы будущий агент мог:

1. быстро выбрать нужный runbook;
2. предложить безопасные команды;
3. принять вывод;
4. построить гипотезы;
5. предложить минимальное исправление;
6. оформить комментарий в заявку.

## Главное правило

```text
Не чинить вслепую.
Сначала факты -> слой проблемы -> гипотеза -> минимальное изменение -> проверка -> запись в KB.
```

## Базовая карта диагностики

```text
Симптом
  ├─ Не открывается сайт/API      -> port, DNS, curl, TLS, proxy, firewall, service
  ├─ Не резолвится имя            -> DNS, search domain, resolved, NetworkManager, AD SRV
  ├─ Не стартует сервис           -> systemd, config, env, permissions, port conflict, disk
  ├─ Медленно работает            -> CPU, load, RAM, IO, network, DB/dependency
  ├─ Нет места                    -> disk usage, inodes, logs, docker, temp
  ├─ SSH не подключается          -> route, port, auth, keys, sshd, fail2ban
  ├─ sudo/логин сломан            -> hostname, /etc/hosts, PAM, sudoers, AD/SSSD
  ├─ apt завис/не ставится        -> locks, dpkg interrupted, repo, DNS, proxy
  ├─ Время/Kerberos/AD проблемы   -> NTP, timezone, DNS SRV, krb5, sssd
  └─ Печать не работает           -> CUPS, queue, backend, PPD/filter, printer port
```

## Быстрый старт: первичный сбор фактов

```bash
hostnamectl
uptime
whoami
id
ip -br a
ip r
resolvectl status
ss -tulpn
df -h
df -i
free -h
systemctl --failed
journalctl -p warning..alert -n 100 --no-pager
```

## Когда нужны root-права

Многие диагностические команды безопасны без root. Root/sudo нужны для:
- чтения части логов;
- просмотра процессов с PID/именами;
- systemctl restart;
- правки конфигов;
- tcpdump;
- установки пакетов;
- firewall rules;
- CUPS admin actions.

## Рекомендуемый порядок для агента

```text
1. Уточнить симптом и сервис.
2. Спросить ОС/версию и способ доступа.
3. Дать read-only команды.
4. Попросить вывод без секретов.
5. Сформировать 2-4 гипотезы.
6. Предложить безопасную проверку гипотез.
7. Только потом предложить fix.
8. После fix дать verification checklist.
```

## Список файлов

```text
00-linux-troubleshooting-method.md
01-port-connectivity.md
02-curl-http-tls.md
03-dns-deep-dive.md
04-systemd-service-debug.md
05-logs-journalctl.md
06-network-routing-firewall.md
07-storage-disk-inodes-io.md
08-performance-cpu-ram-load.md
09-processes-files-descriptors.md
10-apt-dpkg-packages.md
11-users-permissions-sudo.md
12-ssh-troubleshooting.md
13-time-ntp-kerberos.md
14-sssd-realm-ad.md
15-cups-printers-linux.md
16-apparmor-selinux.md
17-common-symptoms-map.md
18-safe-fix-patterns.md
19-agent-runbook-format.md
20-linux-command-cheatsheet.md
scripts/
```
