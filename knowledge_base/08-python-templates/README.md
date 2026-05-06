# Python templates for sysadmin

## Базовая структура

```python
import argparse
import logging
from pathlib import Path

def parse_args():
    ...

def main():
    ...

if __name__ == "__main__":
    main()
```

## Что важно

- argparse для параметров;
- logging вместо print для рабочих скриптов;
- pathlib для путей;
- try/except только там, где есть понятная обработка;
- dry-run для опасных действий;
- exit code для CI/автоматизации.
