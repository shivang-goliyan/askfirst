#!/usr/bin/env bash
# Snapshot, then destroy. There is no "stop" that stops the billing.
set -euo pipefail

NAME="${ASKFIRST_DROPLET:-askfirst-gpu}"
ID="$(doctl compute droplet list --format ID,Name --no-header | awk -v n="$NAME" '$2==n {print $1}')"

if [[ -z "$ID" ]]; then
  echo "Nothing called $NAME is running. Nothing to do."
  exit 0
fi

STAMP="$NAME-$(date -u +%Y%m%d-%H%M)"
echo "snapshotting $ID as $STAMP — this takes a few minutes, do not interrupt it"
doctl compute droplet-action snapshot "$ID" --snapshot-name "$STAMP" --wait

echo "snapshot done. destroying $ID so it stops billing"
doctl compute droplet delete "$ID" --force
echo "gone. rebuild with up.sh when you need it"
