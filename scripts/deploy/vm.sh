#!/usr/bin/env bash
# Redeploy the app to the box that already serves it. One command, from the repo root:
#
#   ./scripts/deploy/vm.sh
#
# The image is built ON the box — the home uplink stalls on large uploads, and only ~200 KB of
# source goes over the wire this way. Caddy already has the hostname and the certificate, so
# nothing here touches /etc/caddy or any other service.
#
# To attach the model once a droplet is serving:
#   ASKFIRST_VLLM_URL=http://<droplet>:8000/v1 ASKFIRST_MODEL=<name> ./scripts/deploy/vm.sh
# Leave them unset and the app falls back to the CPU baseline and says so in every response.

set -euo pipefail

host="${ASKFIRST_HOST:-ggtwo@34.133.42.59}"
key="${ASKFIRST_KEY:-$HOME/.ssh/gcp_kgb}"
port="${ASKFIRST_PORT:-3330}"
url="${ASKFIRST_URL:-https://askfirst.kgbnetwork.com}"
ssh_opts=(-i "$key" -o IdentitiesOnly=yes -o BatchMode=yes)

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root"

echo "→ syncing source"
rsync -az --delete --exclude '__pycache__' --exclude '*.pyc' \
  -e "ssh ${ssh_opts[*]}" \
  src ui Dockerfile .dockerignore LICENSE pyproject.toml README.md \
  "$host:~/askfirst/"

echo "→ building and restarting on the box"
ssh "${ssh_opts[@]}" "$host" \
  ASKFIRST_VLLM_URL="${ASKFIRST_VLLM_URL:-}" \
  ASKFIRST_MODEL="${ASKFIRST_MODEL:-}" \
  PORT_BIND="$port" bash -s <<'REMOTE'
set -e
cd ~/askfirst
docker build -q -t askfirst:live . >/dev/null

env_args=()
[ -n "${ASKFIRST_VLLM_URL:-}" ] && env_args+=(-e "ASKFIRST_VLLM_URL=$ASKFIRST_VLLM_URL")
[ -n "${ASKFIRST_MODEL:-}" ]    && env_args+=(-e "ASKFIRST_MODEL=$ASKFIRST_MODEL")

docker rm -f askfirst >/dev/null 2>&1 || true
docker run -d --name askfirst --restart unless-stopped \
  -p "127.0.0.1:${PORT_BIND}:7860" -m 400m --memory-swap 400m \
  "${env_args[@]}" askfirst:live >/dev/null

for i in $(seq 1 30); do
  curl -fsS "http://127.0.0.1:${PORT_BIND}/api/health" >/dev/null 2>&1 && break
  sleep 1
done
curl -s "http://127.0.0.1:${PORT_BIND}/api/health"; echo
REMOTE

echo "→ checking the public URL"
code=$(curl -sS -o /dev/null -w '%{http_code}' "$url/")
scorer=$(curl -sS -X POST "$url/api/assess" -H 'content-type: application/json' \
  -d '{"domain":"clinical","record":{"chest_pain":"yes"},"coverage":0.25}' \
  | sed -n 's/.*"scored_by":"\([^"]*\)".*/\1/p')

echo
echo "$url → HTTP $code"
echo "scoring with: ${scorer:-unknown}"
[ "$code" = "200" ] || { echo "that is not a 200 — check 'docker logs askfirst' on the box" >&2; exit 1; }
