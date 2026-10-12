#!/usr/bin/env bash
# Push the app to a Hugging Face Space. Free CPU tier, no card, public URL.
#
#   HF_TOKEN=hf_xxx ./scripts/deploy/space.sh <user>/<space-name>
#
# Create the Space first in the browser, SDK "Docker", blank template. This script replaces its
# contents with the app and the Space README, then pushes. It never touches the GitHub remote.
#
# Once a droplet is serving the model, add ASKFIRST_VLLM_URL (and ASKFIRST_MODEL) as Space
# secrets and restart. The page is identical either way; the API says which scorer answered.

set -euo pipefail

space="${1:-}"
if [[ -z "$space" || -z "${HF_TOKEN:-}" ]]; then
  echo "Need a space id and HF_TOKEN. See the header of this file." >&2
  exit 1
fi

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

git clone "https://user:${HF_TOKEN}@huggingface.co/spaces/${space}" "$work/space" --quiet

cd "$work/space"
find . -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +

cp -r "$root/src" "$root/ui" .
cp "$root/Dockerfile" "$root/.dockerignore" "$root/LICENSE" "$root/pyproject.toml" .
cp "$root/scripts/deploy/space-README.md" README.md

echo "pushing:"
find . -mindepth 1 -maxdepth 1 ! -name .git | sort | sed 's/^/  /'

git add -A
git -c user.name="$(git -C "$root" config user.name)" \
    -c user.email="$(git -C "$root" config user.email)" \
    commit -m "deploy askfirst" --quiet
git push --quiet

echo
echo "live at https://huggingface.co/spaces/${space}"
echo "first build takes a couple of minutes — watch the Logs tab"
