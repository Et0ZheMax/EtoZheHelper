# Web service basic hardening

## Перед публикацией наружу

```text
[ ] HTTPS
[ ] reverse proxy
[ ] auth где нужно
[ ] rate limiting
[ ] security headers
[ ] no directory listing
[ ] no debug mode
[ ] no .env exposure
[ ] logs without secrets
[ ] backups
[ ] monitoring
[ ] update process
```

## Nginx headers example

```nginx
add_header X-Content-Type-Options nosniff;
add_header X-Frame-Options SAMEORIGIN;
add_header Referrer-Policy no-referrer-when-downgrade;
```

## Что часто сканируют

```text
/.env
/.git
/wp-admin
/phpmyadmin
/server-status
/config.php
/backup.zip
```

404 на такие запросы не всегда авария, но это сигнал, что сайт видят сканеры.
