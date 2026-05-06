# Runbook: Printer not printing

## Быстрые проверки

```bash
ping -c 3 10.0.0.50
nc -vz 10.0.0.50 9100
lpstat -t
lpq -P prn-001
journalctl -u cups -n 100 --no-pager
```

## Очистить очередь

```bash
cancel -a prn-001
```

## Тест

```bash
echo "test" | lp -d prn-001
```

## Частые причины

- принтер offline;
- IP изменился;
- очередь stuck;
- драйвер/PPD/фильтр отсутствует;
- firewall;
- неправильный протокол socket/lpd/ipp.
