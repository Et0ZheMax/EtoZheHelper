---
type: runbook
domain: linux
tags: [linux, process, fd, lsof, limits]
risk: low
requires_root: sometimes
---

# Processes, files, descriptors

## Процессы

```bash
ps aux
ps aux --sort=-%cpu | head
ps aux --sort=-%mem | head
pstree -ap
pgrep -a <name>
```

## Кто держит порт

```bash
ss -lntp | grep ':8080'
sudo lsof -i :8080
```

## Кто держит файл

```bash
sudo lsof /path/to/file
```

## Deleted open files

```bash
sudo lsof +L1
```

Если большой удалённый лог всё ещё держит процесс, место не освободится до restart.

## File descriptors

```bash
ulimit -n
cat /proc/<PID>/limits
ls /proc/<PID>/fd | wc -l
```

## Too many open files

Симптомы:

```text
Too many open files
EMFILE
cannot accept connection
```

Проверить:

```bash
cat /proc/<PID>/limits
ls /proc/<PID>/fd | wc -l
```

Systemd override:

```bash
sudo systemctl edit <service>
```

```ini
[Service]
LimitNOFILE=65535
```

Применить:

```bash
sudo systemctl daemon-reload
sudo systemctl restart <service>
```

## Zombie processes

```bash
ps aux | awk '$8 ~ /Z/ { print }'
```

Zombie обычно нужно чинить через parent process, не kill самого zombie.

## Safe kill

Сначала мягко:

```bash
kill <PID>
```

Потом, если не завершился:

```bash
kill -TERM <PID>
```

В крайнем случае:

```bash
kill -KILL <PID>
```

`kill -9` не даёт процессу корректно закрыть файлы/соединения.
