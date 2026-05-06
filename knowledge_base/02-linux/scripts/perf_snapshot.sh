#!/usr/bin/env bash
set -Eeuo pipefail

echo "### uptime/load"
uptime
echo "CPU count: $(nproc)"

echo
echo "### memory"
free -h

echo
echo "### vmstat"
vmstat 1 5

echo
echo "### top CPU processes"
ps aux --sort=-%cpu | head -20

echo
echo "### top MEM processes"
ps aux --sort=-%mem | head -20

echo
echo "### OOM signs"
dmesg -T | grep -iE 'oom|killed process' | tail -50 || true

if command -v iostat >/dev/null 2>&1; then
  echo
  echo "### iostat"
  iostat -xz 1 3
else
  echo
  echo "iostat not installed. Package: sysstat"
fi
