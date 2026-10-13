# The GPU day

One day, two numbers, about 50 GPU-hours per account at $1.99 an hour. The point of this file is
that nothing gets debugged at that price. Everything below was rehearsed first against
`scripts/fake_vllm.py`, a stand-in that answers in the shape the vLLM OpenAI-compatible server
documents — echo with `max_tokens=0`, one logprob per prompt token, `text_offset` as cumulative
character offsets, first token's logprob null.

## What the rehearsal already proved, and what it found

Proven working against a served endpoint, not a mock inside a test:

- `Endpoint` discovers the served model through `/v1/models`.
- `ModelScorer` scores every outcome in one batched request and returns a distribution summing
  to 1.0.
- `ModelProposer` returns 10 fields on both schemas, reports invented codes, reports an empty reply.
- `rank_gaps` runs end to end through the model — 11 gaps with non-zero information gain, plus the
  sensitivity map and the one-more-fact number.
- `/api/assess` serves the model path and names what answered.
- `scripts/run_proposer_recall.py` runs the whole comparison table, confidence intervals and the
  40% bar check.

Three bugs it found, which would otherwise have been found on the clock:

1. **`ModelProposer` returned an empty list on any schema whose fields are not named like
   DDXPlus codes.** The parser matched a hardcoded `\b[A-Za-z]+_\d+\b`, so `troponin` and
   `d_dimer` matched nothing at all and it failed silently. Now it matches against the names
   actually offered in the menu.
2. **The invented-code safeguard was dead code** — it appended a marker and then filtered the
   marker out one line later. Now the count is kept on the instance and reported.
3. **The scorer label was the hardcoded string "open model on AMD MI300X"**, printed whatever was
   really answering — a laptop, a stub, anything. On the one product whose whole subject is not
   being confidently wrong. It now reads the served model and host off the endpoint.

## Order of work, and why this order

1. **Serve the model.** `scripts/serve_vllm.sh`. Then `curl $URL/v1/models` and confirm the name.
2. **`run_proposer_recall.py` at n=200.** This is a go/no-go, it is cheap, and it decides whether
   the advice feature ships as a claim at all. **Bar: 40% recall at k=10.** Do it first so a
   failure costs twenty minutes instead of a day.
3. **Model confidence against the softmax margin, on the completeness grid.** This is the
   product and the reason the hardware matters. Budget most of the day here.
4. **ESM-2 650M** — `scripts/score_variants.py --model facebook/esm2_t33_650M_UR50D`. A second,
   genuinely different workload. The 34M CPU run already stands as the floor, so this either
   improves the 21% wrong-sign figure or it does not, and either is reportable.
5. **One profiler trace** with `rocprofv3`, for a measured number rather than a described one.

## Cost arithmetic, before anything is launched

MI300X is $1.99/GPU-hour and a single-GPU droplet is 20 vCPUs / 240 GB RAM / 720 GB NVMe.
$100 per account is **50.3 GPU-hours**. Three accounts do not pool — they are three separate
wallets, so no single run may assume more than 50 hours.

An exhaustive 223-field sweep with a language model is roughly **450 scoring requests per case**,
which the dead-end note puts at about 22 seconds of GPU per case. That is a latency wall, not a
budget one, and it does not move with more credits. The design already works around it: the model
proposes about ten fields in one generation, and the cheap scorer ablates exhaustively for free.

**A powered-off droplet still bills. Snapshot and destroy — never stop.** Credits expire 30 days
from deposit.

## Kill criteria, written down before the money is spent

- **Proposer under 40% at k=10:** the advice feature does not ship as a claim. It stays in the
  product as a visible aid. The refusal feature does not depend on it, so this is not a project
  failure and must not be treated as one on the day.
- **Model confidence no better than the naive Bayes margin:** report it. "A stronger scorer did
  not move the coverage frontier" is a real finding about this problem and it is more interesting
  than silence. Do not re-run it hoping for a better number.
- **Serving will not start within an hour:** fall back to a smaller open model and say which one.
  The curve is baked, so the live site never depends on this working.

## Attaching it to the live site

    ASKFIRST_VLLM_URL=http://<droplet>:8000/v1 \
      ASKFIRST_MODEL=<served name> ./scripts/deploy/vm.sh

Every response then names the model and host that answered. Re-run without those variables to
detach before the droplet dies, and the page carries on serving the baked curve.

## Rehearsing again, any time, for free

    python3 -I scripts/fake_vllm.py 8111 &
    ASKFIRST_VLLM_URL=http://127.0.0.1:8111/v1 python3 -I scripts/run_proposer_recall.py \
      data/ddxplus/release_validate_patients 20

**Nothing measured against the fake is a result.** Its logprobs are a hash of the prompt. It
exists to prove the plumbing, and the numbers it produces are deliberately meaningless.
