# CPU/RAM/Disk/Inodes

## CPU/load

```bash
uptime
top
htop
ps aux --sort=-%cpu | head
pidstat 1 5
```

Load average оценивай относительно количества CPU.

## RAM

```bash
free -h
vmstat 1 5
ps aux --sort=-%mem | head
```

Важно: Linux активно использует cache/buffers, это не всегда проблема.

## Disk usage

```bash
df -h
sudo du -xh / | sort -h | tail -50
sudo du -xh /var | sort -h | tail -50
```

## Inodes

```bash
df -i
sudo find /var -xdev -type f | cut -d/ -f2-4 | sort | uniq -c | sort -n | tail
```

Если место есть, но inode закончились — новые файлы не создаются.

## Частые пожиратели места

```text
/var/log
/var/cache/apt
/var/lib/docker
/tmp
/home/*/Downloads
backup directories
core dumps
```

## Очистка аккуратно

```bash
sudo journalctl --vacuum-time=14d
sudo apt clean
docker system df
docker system prune
```

Не удаляй `/var/lib/docker` руками без понимания последствий.
