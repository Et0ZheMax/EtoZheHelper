# Быстрые ответы

## Что такое inode

Inode — это запись файловой системы с метаданными файла: права, владелец, размер, указатели на блоки данных. Имя файла хранится отдельно в directory entry. Если inode закончились, новые файлы не создаются даже при наличии свободного места.

## Что происходит при открытии google.com

```text
1. Браузер проверяет cache.
2. ОС проверяет hosts/cache.
3. DNS резолвит домен в IP.
4. Строится маршрут.
5. TCP handshake.
6. TLS handshake для HTTPS.
7. HTTP request.
8. Сервер/reverse proxy/app отвечает.
9. Браузер парсит HTML/CSS/JS и догружает ресурсы.
```

## CI/CD

CI:
```text
commit -> build -> tests -> lint/security -> artifact/image
```

CD:
```text
deploy to env -> migrations/config -> health checks -> rollout/rollback -> monitoring
```

## Docker volume

Volume — persistent storage, который живёт отдельно от container lifecycle. Если контейнер удалить, volume может остаться. Но данные можно потерять при удалении volume, ошибке приложения, повреждении FS, неправильном backup/restore, ручном `docker volume rm`.
