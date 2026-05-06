#!/usr/bin/env bash
set -Eeuo pipefail

FILE="${1:-}"
if [[ -z "$FILE" || ! -f "$FILE" ]]; then
  echo "Usage: $0 /path/to/config"
  exit 2
fi

BACKUP="${FILE}.bak.$(date +%F-%H%M%S)"
sudo cp -a "$FILE" "$BACKUP"
echo "Backup created: $BACKUP"
