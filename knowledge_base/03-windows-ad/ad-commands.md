# AD команды и PowerShell

## RSAT модуль

```powershell
Import-Module ActiveDirectory
```

## Пользователь

```powershell
Get-ADUser user1 -Properties *
Get-ADUser user1 -Properties MemberOf | Select-Object -ExpandProperty MemberOf
```

## Группы пользователя

```powershell
Get-ADPrincipalGroupMembership user1 | Select-Object Name
```

## Добавить в группу

```powershell
Add-ADGroupMember -Identity "GroupName" -Members user1
```

## Проверить группу

```powershell
Get-ADGroupMember "GroupName" | Select-Object Name, SamAccountName
```

## Компьютер

```powershell
Get-ADComputer workstation-01 -Properties *
```

## Поиск отключенных пользователей

```powershell
Search-ADAccount -UsersOnly -AccountDisabled
```

## Поиск заблокированных

```powershell
Search-ADAccount -LockedOut
```

## Разблокировать

```powershell
Unlock-ADAccount user1
```

## Password expired / last set

```powershell
Get-ADUser user1 -Properties PasswordLastSet, PasswordExpired, LockedOut, Enabled
```
