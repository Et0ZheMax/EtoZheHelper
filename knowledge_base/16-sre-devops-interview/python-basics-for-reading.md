# Python basics for reading code

## Типичная структура

```python
import os
from pathlib import Path

CONFIG = "config.json"

def load_config():
    ...

def main():
    config = load_config()
    ...

if __name__ == "__main__":
    main()
```

## Что смотреть первым

1. imports — какие библиотеки используются;
2. constants — пути, URL, настройки;
3. main — точка входа;
4. functions — что делают куски логики;
5. side effects — где меняются файлы/система/API;
6. error handling — что будет при ошибке.

## def

`def` создаёт функцию. Функция не выполняется, пока её не вызвали.

## class

`class` описывает объект с данными и методами. В админских скриптах часто можно жить без классов.

## try/except

Используется для обработки ошибок.

```python
try:
    risky()
except Exception as exc:
    print(exc)
```

## list/dict

```python
items = [1, 2, 3]
user = {"name": "Max", "role": "admin"}
```
