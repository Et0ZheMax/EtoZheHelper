---
type: cheatsheet
domain: linux
tags: [linux, logs, journalctl, grep]
risk: low
requires_root: sometimes
---

# Logs and journalctl

## Главная идея

Логи должны отвечать на вопросы:

```text
Что произошло?
Когда?
На каком хосте?
Какой процесс?
Какая ошибка?
Это причина или следствие?
```

## journalctl basics

```bash
journalctl -n 100 --no-pager
journalctl -p err..alert -n 100 --no-pager
journalctl --since "1 hour ago" --no-pager
journalctl --since "2026-05-06 10:00" --until "2026-05-06 11:00"
```

## По сервису

```bash
journalctl -u nginx -n 100 --no-pager
journalctl -u nginx -f
journalctl -u nginx --since "today" --no-pager
```

## По PID

```bash
journalctl _PID=1234
```

## По boot

```bash
journalctl --list-boots
journalctl -b
journalctl -b -1
```

## Kernel logs

```bash
dmesg -T | tail -100
journalctl -k -n 100 --no-pager
```

## Grep по логам

```bash
grep -RniE "error|failed|timeout|denied|refused|oom|killed" /var/log/ 2>/dev/null
```

## Nginx

```bash
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
sudo grep -i "upstream" /var/log/nginx/error.log
```

## Auth logs

Ubuntu/Debian:

```bash
sudo tail -n 100 /var/log/auth.log
```

Некоторые системы:

```bash
sudo journalctl -u ssh -n 100 --no-pager
```

## Log rotation

```bash
ls -lh /var/log
du -sh /var/log/*
logrotate -d /etc/logrotate.conf
```

## Очистка journald

Посмотреть размер:

```bash
journalctl --disk-usage
```

Очистить старше 14 дней:

```bash
sudo journalctl --vacuum-time=14d
```

Ограничить размер:

```bash
sudo journalctl --vacuum-size=1G
```

## Senior-подход

```text
1. Сначала timeframe.
2. Потом service-specific logs.
3. Потом system/kernel logs.
4. Потом dependency logs.
5. Не вырывать одну ошибку без контекста.
6. Сравнивать "первую ошибку" и "последствия".
```
