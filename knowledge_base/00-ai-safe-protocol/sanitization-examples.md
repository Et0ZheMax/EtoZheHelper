# Примеры обезличивания

## Лог systemd

Было:

```text
May 06 12:01:22 l-ivanov-01 realmd[1234]: Joined domain pak-cspmz.ru as L-IVANOV-01
```

Стало:

```text
May 06 12:01:22 workstation-01 realmd[1234]: Joined domain example.local as WORKSTATION-01
```

## API config

Было:

```json
{
  "url": "https://inv.real-company.local/apirest.php",
  "app_token": "abcdef",
  "user_token": "123456"
}
```

Стало:

```json
{
  "url": "https://glpi.example.local/apirest.php",
  "app_token": "<APP_TOKEN>",
  "user_token": "<USER_TOKEN>"
}
```

## Ошибка Python

Было:

```text
requests.exceptions.ConnectionError: HTTPSConnectionPool(host='secret-service.real-company.local', port=443)
```

Стало:

```text
requests.exceptions.ConnectionError: HTTPSConnectionPool(host='service.example.local', port=443)
```
