# Printers / CUPS

## Базовые команды

```bash
lpstat -t
lpstat -v
lpoptions -p <printer> -l
lpq -P <printer>
cancel -a <printer>
```

## CUPS service

```bash
systemctl status cups
journalctl -u cups -n 200 --no-pager
```

## Добавить принтер socket

```bash
sudo lpadmin -p prn-001 -E -v socket://10.0.0.50:9100 -m everywhere
sudo lpoptions -d prn-001
```

## Тест

```bash
echo "test page" | lp -d prn-001
lpq -P prn-001
```
