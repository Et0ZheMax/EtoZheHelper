# Docker / Compose

## Базовые команды

```bash
docker ps
docker ps -a
docker images
docker logs <container>
docker logs -f --tail=100 <container>
docker exec -it <container> sh
docker compose ps
docker compose logs -f --tail=100
docker compose up -d
docker compose down
```

## Разница run/start/up

- `docker run` создаёт новый контейнер из образа.
- `docker start` запускает уже созданный контейнер.
- `docker compose up` создаёт/обновляет и запускает сервисы из compose-файла.
