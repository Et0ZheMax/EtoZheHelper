# systemd

## Посмотреть статус

```bash
systemctl status <service>
systemctl is-enabled <service>
systemctl is-active <service>
```

## Логи

```bash
journalctl -u <service> -n 100 --no-pager
journalctl -u <service> -f
journalctl -p err..alert -n 100 --no-pager
journalctl --since "1 hour ago" -u <service>
```

## Перезапуск

```bash
sudo systemctl daemon-reload
sudo systemctl restart <service>
sudo systemctl status <service>
```

## Маскированный сервис

Симптом:

```text
Loaded: masked
```

Проверка:

```bash
systemctl status <service>
systemctl cat <service>
ls -l /etc/systemd/system/<service>
```

Размаскировать:

```bash
sudo systemctl unmask <service>
sudo systemctl enable --now <service>
```

## Unit override

```bash
sudo systemctl edit <service>
sudo systemctl daemon-reload
sudo systemctl restart <service>
```

## Типовые причины падения сервиса

- неверный путь в ExecStart;
- нет прав на файл;
- занят порт;
- отсутствует env-файл;
- зависимость не стартовала;
- синтаксическая ошибка в конфиге;
- AppArmor/SELinux блокирует доступ.
