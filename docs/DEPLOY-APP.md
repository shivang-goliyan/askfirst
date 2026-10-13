# Getting the app online, and keeping it there

**Live: https://askfirst.kgbnetwork.com** — deployed 12 Oct, valid certificate to 10 Jan 2027.

The submission needs a URL a stranger can open, with nothing to install and no key to paste, and
it has to survive judges poking it from 18 to 21 October. A GPU cannot be up for that window —
$1.99/GPU-hour against $100 per account means 72 hours on one card costs $143, more than any one
account holds. So the app and the model are deployed separately and on purpose.

## Two tiers, split deliberately

**The page and the headline run on CPU, free, permanently.** `/api/curve` reads a baked JSON
artifact measured once over 6,000 patients. It cannot fail and it does not depend on a droplet.

**The live case runs the real model, on CPU.** `/api/assess` on the `ddxplus` domain loads the
fitted softmax — 88 KB of weights that ship inside the image — so a visitor pokes the same scorer
every number on the page was measured with, at 99.6% top-1 on complete records. The cases it
scores are twelve real held-out patients from `/api/cases`, taken from past the end of both the
fitting set and the set the curve was measured on. The hand-written baseline is still there for
the `clinical` domain, which exists to exercise cost-aware ranking, and nothing measured comes
from it.

**The model attaches on demand.** Bring a droplet up, redeploy with one environment variable, and
the same endpoints score against the open model instead. Every response carries `scored_by`, so
nobody has to guess where a number came from:

    "scored_by": "open model on AMD MI300X"
    "scored_by": "softmax regression on CPU, 99.6% top-1 on complete records"
    "scored_by": "hand-written baseline, no GPU attached"

`threshold_calibrated` goes with it. The confidence cut-off was measured against the softmax, so
when a model on a GPU answers instead, the response says the cut-off was not calibrated for it.

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

## What it stands up to, measured

Judges poke a thing at the same time, so this was measured against the live URL rather than
assumed. An assessment is CPU-bound numpy, which the GIL serialises, so one worker was taking 11
seconds to clear 24 simultaneous requests. Two workers:

| at once | wall clock | slowest single request |
|---|---|---|
| 4 | 3.3s | 3.3s |
| 12 | 3.9s | 3.9s |
| 24 | 7.1s | 7.1s |

It degrades by queueing rather than by falling over: no failed requests, no restarts, no OOM kill
across any burst. Memory sits at **142 MB of the 400 MB cap** with both workers warm and all the
baked artifacts loaded, on a box that is running other people's things. The static endpoints —
the curve, the cases, the variant panel — are flat JSON and are not affected by any of this.

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
