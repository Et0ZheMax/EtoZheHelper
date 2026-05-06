# GPO troubleshooting

## Клиент

```cmd
gpupdate /force
gpresult /r
gpresult /h C:\Temp\gpresult.html
```

## PowerShell

```powershell
Get-GPResultantSetOfPolicy -ReportType Html -Path C:\Temp\rsop.html
```

## Частые причины неприменения GPO

- объект не в нужной OU;
- security filtering;
- WMI filter;
- deny apply group policy;
- slow link;
- DNS/DC проблемы;
- replication delay;
- конфликтующие политики;
- loopback processing.

## Проверки

```cmd
echo %LOGONSERVER%
nltest /dsgetdc:example.local
whoami /groups
```

## Логи

Event Viewer:

```text
Applications and Services Logs
 -> Microsoft
   -> Windows
     -> GroupPolicy
       -> Operational
```
