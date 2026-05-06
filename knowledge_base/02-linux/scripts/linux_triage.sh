#!/usr/bin/env bash
set -Eeuo pipefail

OUT_DIR="${1:-$HOME/linux-triage-$(hostname)-$(date +%F-%H%M%S)}"
mkdir -p "$OUT_DIR"

run() {
  local name="$1"
  shift
  echo "### $name"
  {
    echo "### COMMAND: $*"
    echo "### DATE: $(date -Is)"
    "$@"
  } > "$OUT_DIR/$name.txt" 2>&1 || true
}

run hostnamectl hostnamectl
run uptime uptime
run date date
run timedatectl timedatectl
run ip_br ip -br a
run routes ip r
run resolvectl resolvectl status
run resolv_conf cat /etc/resolv.conf
run sockets ss -tulpn
run disk df -h
run inodes df -i
run lsblk lsblk -f
run memory free -h
run vmstat vmstat 1 5
run failed_units systemctl --failed
run journal_errors journalctl -p warning..alert -n 300 --no-pager
run dmesg_tail dmesg -T

echo "Linux triage saved to: $OUT_DIR"
echo "Before sharing externally, sanitize files for secrets/internal data."
