---
type: runbook
domain: linux
tags: [linux, performance, cpu, ram, load, oom]
risk: low
requires_root: sometimes
---

# Performance: CPU, RAM, load

## Быстрая диагностика

```bash
uptime
top
free -h
vmstat 1 5
ps aux --sort=-%cpu | head -20
ps aux --sort=-%mem | head -20
```

## Load average

```bash
uptime
nproc
```

Интерпретация:
- load 4 на 8 CPU — нормально;
- load 40 на 4 CPU — проблема;
- высокий load может быть CPU или IO wait.

## CPU

```bash
top
mpstat -P ALL 1 5
pidstat 1 5
```

Пакет:

```bash
sudo apt install -y sysstat
```

## IO wait

В `top` смотри `%wa`.  
В `vmstat` смотри `wa`.

```bash
vmstat 1 10
iostat -xz 1
```

Высокий IO wait значит процессы ждут диск.

## RAM

```bash
free -h
cat /proc/meminfo | head
ps aux --sort=-%mem | head -20
```

Важно: `buff/cache` — не обязательно проблема.

## Swap

```bash
swapon --show
free -h
vmstat 1 5
```

Постоянный swap in/out — признак нехватки RAM.

## OOM killer

```bash
dmesg -T | grep -i 'killed process'
journalctl -k | grep -i oom
```

## Process tree

```bash
pstree -ap
```

## Senior flow

```text
1. load vs CPU count
2. CPU user/system/io wait
3. top processes
4. RAM/swap/OOM
5. IO latency
6. recent changes
7. service-specific metrics/logs
```

## Быстрые гипотезы

| Симптом | Вероятная причина |
|---|---|
| high CPU user | приложение/цикл/нагрузка |
| high CPU system | kernel/network/io/syscalls |
| high iowait | диск/FS/backup/logs |
| high load + low CPU | IO wait/blocked tasks |
| OOM killed | memory leak/лимиты/слишком мало RAM |
| swap thrashing | RAM pressure |

## Комментарий в заявку

```text
Проверил нагрузку CPU/RAM/load average и процессы.
Основная нагрузка приходилась на <процесс/IO/RAM>. 
После <действия> показатели нормализовались/передано на дальнейший анализ.
```
