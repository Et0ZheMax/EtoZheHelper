#!/usr/bin/env bash
set -Eeuo pipefail

NAME="${1:-}"
DNS_SERVER="${2:-}"

if [[ -z "$NAME" ]]; then
  echo "Usage: $0 <name> [dns_server]"
  exit 2
fi

echo "### resolv.conf"
cat /etc/resolv.conf || true

echo
echo "### resolvectl status"
resolvectl status || true

echo
echo "### getent"
getent hosts "$NAME" || true

echo
echo "### resolvectl query"
resolvectl query "$NAME" || true

echo
echo "### dig default"
dig "$NAME" || true

if [[ -n "$DNS_SERVER" ]]; then
  echo
  echo "### dig @$DNS_SERVER"
  dig @"$DNS_SERVER" "$NAME" || true
fi
