---
type: runbook
domain: linux
tags: [linux, disk, inodes, io, filesystem]
risk: medium
requires_root: sometimes
---

# Storage: disk, inodes, IO

## Быстрая диагностика

```bash
df -h
df -i
lsblk -f
mount | column -t
du -xh /var | sort -h | tail -30
```

## Disk full

```bash
df -h
sudo du -xh / | sort -h | tail -50
sudo du -xh /var | sort -h | tail -50
```

Частые места:

```text
/var/log
/var/cache/apt
/var/lib/docker
/tmp
/home/*/Downloads
/var/tmp
backup folders
```

## Inodes full

```bash
df -i
sudo find /var -xdev -type f | cut -d/ -f1-4 | sort | uniq -c | sort -n | tail -30
```

Симптом: место есть, но файлы не создаются.

## Journald size

```bash
journalctl --disk-usage
sudo journalctl --vacuum-time=14d
```

## Docker space

```bash
docker system df
docker image prune
docker container prune
docker volume ls
```

Осторожно с:

```bash
docker system prune -a --volumes
```

Это может удалить нужные volumes.

## Open deleted files

Иногда файл удалён, но процесс держит его открытым:

```bash
sudo lsof +L1
```

Решение: restart процесса, который держит файл.

## IO нагрузка

```bash
iostat -xz 1
iotop
pidstat -d 1
```

Если нет пакетов:

```bash
sudo apt install -y sysstat iotop
```

## Read-only filesystem

Проверить:

```bash
mount | grep ' ro,'
dmesg -T | grep -iE 'error|ext4|xfs|i/o'
```

Это может быть признак проблем диска/FS.

## Safe cleanup pattern

```text
1. df -h / df -i
2. найти крупные каталоги
3. понять владельца данных
4. backup/confirm
5. clean logs/cache/temp
6. restart processes with deleted files
7. проверить free space
8. добавить monitoring/rotation
```

## Комментарий в заявку

```text
Проверил файловые системы, свободное место и inode.
Причина была в заполнении <раздела/inode/logs/cache/docker>.
Выполнена безопасная очистка, свободное место восстановлено, сервисы проверены.
```
