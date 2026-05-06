#!/usr/bin/env bash
set -Eeuo pipefail

SERVICE="${1:-}"

if [[ -z "$SERVICE" ]]; then
  echo "Usage: $0 <service>"
  exit 2
fi

echo "### Status"
systemctl status "$SERVICE" --no-pager || true

echo
echo "### Is active/enabled"
systemctl is-active "$SERVICE" || true
systemctl is-enabled "$SERVICE" || true

echo
echo "### Unit"
systemctl cat "$SERVICE" || true

echo
echo "### Recent logs"
journalctl -u "$SERVICE" -n 200 --no-pager || true

echo
echo "### Failed units"
systemctl --failed || true

echo
echo "### Listening ports"
ss -lntp || true
