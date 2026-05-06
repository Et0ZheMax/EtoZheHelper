# Dockerfile best practices

## Принципы

- Используй конкретные версии образов.
- Минимизируй слои, но не в ущерб читаемости.
- Не клади secrets в image.
- Используй `.dockerignore`.
- Запускай приложение не от root, если возможно.
- Разделяй build/runtime stage.
- HEALTHCHECK, если сервис долгоживущий.

## Пример

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd -r appuser
USER appuser

EXPOSE 8080

CMD ["python", "app.py"]
```

## .dockerignore

```text
.git
.env
__pycache__
*.pyc
node_modules
dist
build
```
