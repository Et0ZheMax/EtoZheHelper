# PowerShell templates

## Общие правила

- Используй `-WhatIf` для опасных операций.
- Используй `Try/Catch`.
- Логи пиши в файл.
- Не храни пароли в скриптах.
- Для AD импортируй модуль `ActiveDirectory`.

## Запуск

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\script.ps1
```
