#!/usr/bin/env bash
# What exists, and what it is costing.
set -euo pipefail

echo "droplets"
doctl compute droplet list --format ID,Name,Status,Size,PublicIPv4 --no-header || true
echo
echo "snapshots"
doctl compute snapshot list --format ID,Name,CreatedAt,MinDiskSize --no-header || true
echo
RUNNING="$(doctl compute droplet list --format Status --no-header 2>/dev/null | grep -c active || true)"
printf 'active droplets: %s   at $1.99/GPU-hour that is $%.2f per hour, $%.2f per day\n' \
  "$RUNNING" "$(echo "$RUNNING * 1.99" | bc -l)" "$(echo "$RUNNING * 1.99 * 24" | bc -l)"
