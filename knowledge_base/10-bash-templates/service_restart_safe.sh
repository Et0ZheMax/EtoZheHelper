#!/usr/bin/env bash
set -Eeuo pipefail

SERVICE="${1:-}"
if [[ -z "$SERVICE" ]]; then
  echo "Usage: $0 <service>"
  exit 2
fi

echo "### Before"
systemctl status "$SERVICE" --no-pager || true

echo "### Config check if available"
if command -v nginx >/dev/null && [[ "$SERVICE" == "nginx" ]]; then
  sudo nginx -t
fi

echo "### Restart"
sudo systemctl restart "$SERVICE"

echo "### After"
systemctl status "$SERVICE" --no-pager
journalctl -u "$SERVICE" -n 50 --no-pager
