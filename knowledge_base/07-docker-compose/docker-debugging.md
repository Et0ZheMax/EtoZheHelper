# Docker debugging

## Container exits

```bash
docker ps -a
docker logs <container>
docker inspect <container>
```

## Port conflict

```bash
ss -lntp | grep :8080
docker ps --format 'table {{.Names}}\t{{.Ports}}'
```

## Container name conflict

Симптом:

```text
Conflict. The container name "/app" is already in use
```

Решения:

```bash
docker rm -f app
# или
docker compose down
docker compose up -d
```

## Volume issues

```bash
docker volume ls
docker volume inspect <volume>
docker system df
```

## Войти внутрь

```bash
docker exec -it <container> sh
docker exec -it <container> bash
```

## Проверить сеть

```bash
docker network ls
docker network inspect <network>
docker exec -it <container> ping db
docker exec -it <container> nc -vz db 5432
```
