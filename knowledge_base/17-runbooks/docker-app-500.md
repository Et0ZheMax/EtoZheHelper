# Runbook: Docker app returns 500

## Проверки

```bash
docker compose ps
docker compose logs --tail=200 app
docker compose logs --tail=200 db
docker inspect <container>
docker exec -it <container> env
```

## Типовые причины

- DB недоступна;
- env переменная неверная;
- миграции не применены;
- volume permission;
- внешний API недоступен;
- приложение стартовало раньше БД.

## Проверка сети

```bash
docker exec -it app nc -vz db 5432
docker exec -it app getent hosts db
```

## Rollback

```bash
docker compose pull
docker compose up -d
# или вернуть предыдущий tag image
```
