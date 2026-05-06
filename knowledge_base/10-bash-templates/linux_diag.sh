#!/usr/bin/env bash
set -Eeuo pipefail

OUT_DIR="${1:-$HOME/diag-$(hostname)-$(date +%F-%H%M%S)}"
mkdir -p "$OUT_DIR"

run() {
  local name="$1"
  shift
  echo "### $name"
  "$@" > "$OUT_DIR/$name.txt" 2>&1 || true
}

run hostname hostnamectl
run uptime uptime
run ip_addr ip a
run routes ip r
run dns resolvectl status
run disk df -h
run inodes df -i
run memory free -h
run failed_units systemctl --failed
run journal_errors journalctl -p warning..alert -n 300 --no-pager

echo "Diagnostics saved to: $OUT_DIR"
