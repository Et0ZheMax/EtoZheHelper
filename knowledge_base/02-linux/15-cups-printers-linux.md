---
type: runbook
domain: linux
tags: [linux, cups, printers, lpadmin, printing]
risk: medium
requires_root: sometimes
---

# CUPS / Linux printing troubleshooting

## Базовая диагностика

```bash
systemctl status cups --no-pager
lpstat -t
lpstat -v
lpstat -o
```

## Проверить принтер по сети

```bash
ping -c 3 10.0.0.50
nc -vz 10.0.0.50 9100
nc -vz 10.0.0.50 515
nc -vz 10.0.0.50 631
```

## Очередь

```bash
lpq -P prn-001
cancel -a prn-001
```

## Тестовая печать

```bash
echo "test $(date)" | lp -d prn-001
```

## PPD/filter

```bash
ls -l /etc/cups/ppd/
grep -i filter /etc/cups/ppd/prn-001.ppd
ls -l /usr/lib/cups/filter/
```

## Ошибка filter not available

Симптом:

```text
File "/usr/lib/cups/filter/rastertoufr2" not available
```

Причина: PPD ссылается на фильтр, но пакет драйвера не установлен.

## Добавить socket-принтер

```bash
sudo lpadmin -p prn-001 -E -v socket://10.0.0.50:9100 -m everywhere
```

## Добавить с PPD

```bash
sudo lpadmin -p prn-001 -E -v socket://10.0.0.50:9100 -P /path/to/driver.ppd
```

## Логи

```bash
journalctl -u cups -n 200 --no-pager
sudo tail -f /var/log/cups/error_log
```

Включить debug:

```bash
sudo cupsctl --debug-logging
sudo systemctl restart cups
```

Выключить:

```bash
sudo cupsctl --no-debug-logging
```

## Senior flow

```text
1. CUPS running
2. queue exists
3. printer reachable by port
4. correct backend URI
5. PPD/filter installed
6. queue not paused
7. test print
8. logs
```
