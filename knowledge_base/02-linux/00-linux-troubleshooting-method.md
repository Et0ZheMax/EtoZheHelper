---
type: methodology
domain: linux
tags: [linux, troubleshooting, methodology]
risk: low
requires_root: false
---

# Linux troubleshooting method

## 1. Зафиксировать симптом

Плохой симптом:

```text
Не работает сервер.
```

Хороший симптом:

```text
На host app01 сервис nginx активен, но сайт https://app.example.local отдаёт 502.
Проблема началась после деплоя около 12:30.
Порт 443 слушает nginx, backend на 127.0.0.1:8080 не отвечает.
```

## 2. Определить слой

```text
DNS -> route -> port -> TLS -> proxy -> service -> app -> dependency -> storage -> auth
```

## 3. Сначала read-only

До исправлений собери факты:

```bash
date
hostnamectl
uptime
ip -br a
ip r
resolvectl status
ss -tulpn
systemctl status <service> --no-pager
journalctl -u <service> -n 100 --no-pager
```

## 4. Строить гипотезы

Пример:

```text
Факт: DNS резолвит app.example.local в 10.0.0.20.
Факт: ping проходит.
Факт: nc -vz 10.0.0.20 443 successful.
Факт: curl -vk https://app.example.local показывает 502.
Гипотеза: nginx доступен, проблема между reverse proxy и backend.
```

## 5. Минимальный fix

Не делай “перезагрузим сервер” первым действием. Лучше:

```text
reload config -> restart service -> rollback config -> restart dependency -> server reboot as last resort
```

## 6. Проверка результата

После fix обязательно:

```bash
systemctl is-active <service>
journalctl -u <service> -n 50 --no-pager
curl -I http://localhost:<port>
curl -vk https://service.example.local
```

## 7. Документировать

Минимальная запись:

```text
Симптом:
Причина:
Что проверено:
Что исправлено:
Как проверено:
Как предотвратить:
```

## Senior-подход

Senior отличается не количеством команд, а безопасной логикой:

- понимает blast radius;
- не делает необратимых действий без backup;
- сначала проверяет дешёвые гипотезы;
- отличает симптом от причины;
- оставляет после себя runbook/monitoring;
- умеет объяснить решение простым языком.
