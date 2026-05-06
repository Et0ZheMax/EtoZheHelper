#!/usr/bin/env bash
set -Eeuo pipefail

HOST="${1:-}"
PORT="${2:-}"

if [[ -z "$HOST" || -z "$PORT" ]]; then
  echo "Usage: $0 <host> <port>"
  exit 2
fi

echo "### DNS"
getent hosts "$HOST" || true
resolvectl query "$HOST" || true

echo
echo "### Route"
IP="$(getent ahosts "$HOST" | awk '{print $1; exit}' || true)"
if [[ -n "${IP:-}" ]]; then
  ip route get "$IP" || true
fi

echo
echo "### TCP"
if nc -vz -w 5 "$HOST" "$PORT"; then
  echo "TCP_OK"
else
  echo "TCP_FAIL"
fi

echo
echo "### curl if HTTP/HTTPS-like"
if [[ "$PORT" == "80" ]]; then
  curl -I --max-time 10 "http://$HOST" || true
elif [[ "$PORT" == "443" ]]; then
  curl -vkI --max-time 10 "https://$HOST" || true
fi
