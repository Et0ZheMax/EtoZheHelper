# Windows services and logs

## Службы

```powershell
Get-Service
Get-Service -Name Spooler
Restart-Service Spooler
Set-Service Spooler -StartupType Automatic
```

## События

```powershell
Get-EventLog -LogName System -Newest 50
Get-WinEvent -LogName System -MaxEvents 100
Get-WinEvent -FilterHashtable @{LogName='System'; Level=2; StartTime=(Get-Date).AddHours(-2)}
```

## Диск

```powershell
Get-PSDrive
Get-Volume
```

## Процессы

```powershell
Get-Process | Sort-Object CPU -Descending | Select-Object -First 10
Get-Process | Sort-Object WorkingSet -Descending | Select-Object -First 10
```
