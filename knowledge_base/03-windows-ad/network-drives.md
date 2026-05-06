# Сетевые диски Windows/Linux

## Windows проверить подключения

```cmd
net use
```

## Подключить диск

```cmd
net use U: \\fileserver.example.local\share /persistent:yes
```

## Удалить

```cmd
net use U: /delete
```

## Проверить доступ

```powershell
Test-Path \\fileserver.example.local\share
```

## Linux mount SMB

```bash
sudo apt install -y cifs-utils
mkdir -p ~/mnt/share
mount -t cifs //fileserver.example.local/share ~/mnt/share -o username=user1,domain=EXAMPLE
```

## Частые причины

- нет AD-группы;
- DNS не резолвит fileserver;
- SMB порт закрыт;
- пароль истёк;
- Kerberos/NTLM политика;
- share permission есть, NTFS permission нет или наоборот.
