# Runbook: Linux service down

## Симптом

Сервис не отвечает или `systemctl status` показывает failed.

## Быстрые проверки

```bash
systemctl status <service>
journalctl -u <service> -n 200 --no-pager
ss -lntp
df -h
free -h
```

## Гипотезы

- конфиг сломан;
- порт занят;
- диск заполнен;
- нет прав;
- dependency недоступна;
- пакет/бинарь отсутствует;
- env-файл отсутствует.

## Исправление

```bash
sudo systemctl restart <service>
systemctl status <service>
journalctl -u <service> -n 100 --no-pager
```

Если конфиг менялся — сначала validation.

## Эскалация

- сервис падает повторно;
- данные повреждены;
- ошибка в приложении;
- нужна правка кода/БД.
