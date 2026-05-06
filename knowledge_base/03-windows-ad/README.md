# Windows / Active Directory

Раздел для Windows-администрирования: пользователи, группы, домен, GPO, DNS, сетевые диски, службы.

## Быстрые проверки на клиенте

```powershell
hostname
whoami
whoami /groups
ipconfig /all
nltest /dsgetdc:example.local
gpresult /r
klist
net use
```

## Частые проблемы

- нет доступа к сетевому диску;
- пользователь не в группе;
- GPO не применились;
- DNS смотрит не на DC;
- время отличается;
- пароль истёк;
- компьютер потерял trust relationship;
- Kerberos ticket старый.
