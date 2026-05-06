#!/usr/bin/env bash
set -Eeuo pipefail

URL="${1:-}"

if [[ -z "$URL" ]]; then
  echo "Usage: $0 <url>"
  exit 2
fi

echo "### Probe: $URL"
curl -sS -o /dev/null \
  -w 'code=%{http_code} dns=%{time_namelookup} connect=%{time_connect} tls=%{time_appconnect} starttransfer=%{time_starttransfer} total=%{time_total} remote_ip=%{remote_ip}\n' \
  "$URL" || true

echo
echo "### Headers"
curl -kI --max-time 15 "$URL" || true

echo
echo "### Verbose TLS/HTTP"
curl -vk --max-time 20 "$URL" -o /dev/null || true
