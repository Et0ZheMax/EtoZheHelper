#!/usr/bin/env bash
set -Eeuo pipefail

TARGET="${1:-/}"

echo "### df -h"
df -h "$TARGET" || true

echo
echo "### df -i"
df -i "$TARGET" || true

echo
echo "### top dirs under $TARGET"
sudo du -xh "$TARGET" 2>/dev/null | sort -h | tail -50 || true

echo
echo "### journald usage"
journalctl --disk-usage || true

echo
echo "### open deleted files"
sudo lsof +L1 2>/dev/null | head -50 || true

if command -v docker >/dev/null 2>&1; then
  echo
  echo "### docker system df"
  docker system df || true
fi
