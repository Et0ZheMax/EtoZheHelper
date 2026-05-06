# Remote command patterns

## Выполнить команду

```bash
ssh user@host 'hostname && uptime'
```

## Sudo

```bash
ssh -t user@host 'sudo systemctl status cups'
```

## Скопировать файл

```bash
scp file.txt user@host:/tmp/
scp user@host:/var/log/syslog ./syslog-host.log
```

## Запустить script safely

```bash
scp script.sh user@host:/tmp/script.sh
ssh -t user@host 'chmod +x /tmp/script.sh && sudo /tmp/script.sh'
```

## Список хостов

```bash
while read -r host; do
  echo "### $host"
  ssh -o ConnectTimeout=5 "$host" 'hostname && uptime'
done < hosts.txt
```
