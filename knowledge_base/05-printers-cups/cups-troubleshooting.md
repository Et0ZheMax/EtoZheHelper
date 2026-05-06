# CUPS troubleshooting

## Проверить доступность принтера

```bash
ping -c 3 10.0.0.50
nc -vz 10.0.0.50 9100
nc -vz 10.0.0.50 515
nc -vz 10.0.0.50 631
```

## Очередь

```bash
lpstat -o
lpq -P prn-001
cancel -a prn-001
```

## PPD и фильтры

```bash
lpstat -v
lpoptions -p prn-001 -l
grep -i filter /etc/cups/ppd/prn-001.ppd
ls -l /usr/lib/cups/filter/
```

## Ошибка filter not available

Симптом:

```text
File "/usr/lib/cups/filter/rastertoufr2" not available
```

Причина: установлен PPD, но не установлен пакет драйвера/фильтра.

Что делать:

```text
1. Проверить PPD.
2. Проверить наличие нужного фильтра.
3. Установить официальный драйвер.
4. Перезапустить cups.
5. Повторить тестовую печать.
```

## Логи CUPS debug

```bash
sudo cupsctl --debug-logging
sudo systemctl restart cups
journalctl -u cups -f
```

Выключить:

```bash
sudo cupsctl --no-debug-logging
```
