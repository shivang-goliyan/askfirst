#!/usr/bin/env bash
# Bring the GPU back from the most recent snapshot, or build fresh if there isn't one.
set -euo pipefail

NAME="${ASKFIRST_DROPLET:-askfirst-gpu}"
SIZE="${ASKFIRST_SIZE:-gpu-mi300x1-192gb}"
REGION="${ASKFIRST_REGION:-atl1}"
KEY="${ASKFIRST_SSH_KEY:?Set ASKFIRST_SSH_KEY to your key fingerprint or id}"

if doctl compute droplet list --format Name --no-header | grep -qx "$NAME"; then
  echo "$NAME is already up. Use status.sh to see what it is costing."
  exit 0
fi

SNAP="$(doctl compute snapshot list --format ID,Name,CreatedAt --no-header \
        | grep "$NAME" | sort -k3 | tail -1 | awk '{print $1}' || true)"

if [[ -n "$SNAP" ]]; then
  echo "rebuilding from snapshot $SNAP"
  IMAGE="$SNAP"
else
  echo "no snapshot found, building fresh — you will need to install ROCm and vLLM"
  IMAGE="${ASKFIRST_IMAGE:-ubuntu-24-04-x64}"
fi

doctl compute droplet create "$NAME" \
  --size "$SIZE" --region "$REGION" --image "$IMAGE" \
  --ssh-keys "$KEY" --wait

doctl compute droplet list --format Name,PublicIPv4,Status,Memory --no-header
echo
echo "remember: down.sh when you stop working. Powered-off still bills."
