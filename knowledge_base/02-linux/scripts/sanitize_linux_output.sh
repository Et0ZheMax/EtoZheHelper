#!/usr/bin/env bash
set -Eeuo pipefail

FILE="${1:-}"

if [[ -z "$FILE" || ! -f "$FILE" ]]; then
  echo "Usage: $0 <file>"
  exit 2
fi

sed -E \
  -e 's/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/user@example.local/g' \
  -e 's/\b10\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\b/10.0.0.10/g' \
  -e 's/\b192\.168\.[0-9]{1,3}\.[0-9]{1,3}\b/192.168.0.10/g' \
  -e 's/(token|password|passwd|secret|api_key|apikey)=([^[:space:]]+)/\1=<REDACTED>/Ig' \
  -e 's/(Authorization: Bearer )[A-Za-z0-9._-]+/\1<TOKEN>/Ig' \
  "$FILE"
