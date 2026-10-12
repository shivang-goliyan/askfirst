# Getting the app online, and keeping it there

The submission needs a URL a stranger can open, with nothing to install and no key to paste, and
it has to survive judges poking it from 18 to 21 October. A GPU cannot be up for that window —
$1.99/GPU-hour against $100 per account means 72 hours on one card costs $143, more than any one
account holds. So the app and the model are deployed separately and on purpose.

## Two tiers, split deliberately

**The page and the headline run on CPU, free, permanently.** `/api/curve` reads a baked JSON
artifact measured once over 1,500 patients. It cannot fail and it does not depend on a droplet.
`/api/assess` falls back to the hand-written baseline scorer when no model endpoint is set.

**The model attaches on demand.** Bring a droplet up, point the app at it, and the same endpoints
start scoring against the open model instead. Every response carries `scored_by`, so nobody has
to guess where a number came from:

    "scored_by": "open model on AMD MI300X"
    "scored_by": "hand-written baseline, no GPU attached"

## Host: Hugging Face Space, Docker SDK, CPU basic

Free, no payment method, public URL, and it does not cold-start behind a 50-second wall the way
free Render does. Create the Space in the browser (SDK **Docker**, blank template), then:

    HF_TOKEN=hf_xxx ./scripts/deploy/space.sh <user>/askfirst

That pushes `src/`, `ui/`, the Dockerfile and `scripts/deploy/space-README.md` as the Space
README. Front matter in that file sets `app_port: 7860`, which is what the Dockerfile listens on.

When a droplet is live, add **ASKFIRST_VLLM_URL** and **ASKFIRST_MODEL** as Space secrets and
restart. Remove them when the droplet dies and the page keeps working.

## Verified locally, not assumed

    docker build -t askfirst:local .
    docker run --rm -p 7860:7860 askfirst:local

Checked on 13 Oct against the image above:

| check | result |
|---|---|
| `GET /api/health` | `{"ok":true,"model_endpoint":false,"baked_curve":true,"schemas":["clinical","ddxplus","variant"]}` |
| `GET /` | 200, 9450 bytes |
| `GET /api/curve` | 20 rows, first at 5% coverage |
| `POST /api/assess` thin record | refuses — confidence 0.25 under threshold 0.3719, asks for troponin at 0.391 bits |

The image installs fastapi, uvicorn, pyyaml and openai at pinned versions. It does **not**
install vLLM; the client speaks to the server over HTTP and nothing heavy belongs in a CPU image.

## Fallback, if the Space jams

Render free web service from the same Dockerfile — `PORT` is read from the environment, so it
needs no change. It sleeps after 15 minutes idle and wakes in roughly 50 seconds, which is
survivable as a mirror and poor as a primary.

## What is deliberately not here

No API key entry, no login, no upload of anything personal. The demo records are synthetic
DDXPlus cases and the variant examples come from CIViC, which is CC0. Nothing a visitor types is
stored.
