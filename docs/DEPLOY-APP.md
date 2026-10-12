# Getting the app online, and keeping it there

**Live: https://askfirst.kgbnetwork.com** — deployed 12 Oct, valid certificate to 10 Jan 2027.

The submission needs a URL a stranger can open, with nothing to install and no key to paste, and
it has to survive judges poking it from 18 to 21 October. A GPU cannot be up for that window —
$1.99/GPU-hour against $100 per account means 72 hours on one card costs $143, more than any one
account holds. So the app and the model are deployed separately and on purpose.

## Two tiers, split deliberately

**The page and the headline run on CPU, free, permanently.** `/api/curve` reads a baked JSON
artifact measured once over 1,500 patients. It cannot fail and it does not depend on a droplet.
`/api/assess` falls back to the hand-written baseline scorer when no model endpoint is set.

**The model attaches on demand.** Bring a droplet up, redeploy with one environment variable, and
the same endpoints score against the open model instead. Every response carries `scored_by`, so
nobody has to guess where a number came from:

    "scored_by": "open model on AMD MI300X"
    "scored_by": "hand-written baseline, no GPU attached"

## Where it runs

A small container on a box we already own, behind Caddy, which already held the hostname and
issues the certificate. No new account, no third-party token, and the model endpoint can be
attached or removed in one command without anyone clicking through a hosting UI.

    ./scripts/deploy/vm.sh                                   # redeploy, CPU only
    ASKFIRST_VLLM_URL=http://<droplet>:8000/v1 \
      ASKFIRST_MODEL=<name> ./scripts/deploy/vm.sh           # attach the model

The image is built on the box, because only ~200 KB of source needs to cross the wire that way and
the upstream link stalls on large uploads. The container is capped at 400 MB and actually uses
about 33 MB, which matters because that box runs other things that are not allowed to fall over.

**What the deploy touched, so it can be undone:** one container named `askfirst` bound to
`127.0.0.1:3330`, and one appended block in `/etc/caddy/Caddyfile`. The Caddyfile was backed up
first to `/etc/caddy/Caddyfile.bak-askfirst-20261012-193120`, validated before reloading, and
reloaded rather than restarted. Nothing else on the box was stopped, restarted or edited.

## Verified, not assumed

Checked against the public URL after the last deploy:

| check | result |
|---|---|
| `GET /` | 200, 10,618 bytes |
| `GET /deck.html` | 200, 15,138 bytes — the deck ships with the app |
| `GET /api/health` | `{"ok":true,"model_endpoint":false,"baked_curve":true,...}` |
| `GET /api/curve` | 200, 3,145 bytes |
| `POST /api/assess`, one symptom | **refuses** — asks for troponin first, 0.391 bits |
| certificate | Let's Encrypt, `CN=askfirst.kgbnetwork.com`, to 10 Jan 2027 |

## Running it anywhere else

The container is plain and takes `PORT` from the environment, so it runs unchanged on any host:

    docker build -t askfirst .
    docker run --rm -p 7860:7860 askfirst

`scripts/deploy/space.sh` pushes the same image definition to a free Hugging Face Space, which is
kept as a mirror in case the primary host is ever unavailable during judging. It needs a token with
the **write** role; a read-only token fails at the create step and the script says so rather than
passing on a bare 401.

## What is deliberately not here

No API key entry, no login, no upload of anything personal. The demo records are synthetic DDXPlus
cases and the variant examples come from CIViC, which is CC0. Nothing a visitor types is stored,
and the app sends `Cache-Control: no-store` so a proxy cannot serve one visitor's view to another.
