"""Does a frontier model stop answering when the record runs out?

    ANTHROPIC_API_KEY=... python3 scripts/rehearsal/claude_abstention.py --cases 100

This is NOT an accuracy contest, and a judge who reads it as one should be corrected. Our scorer
is fitted on 30,000 labelled patients from this exact generator; Claude is zero-shot. Comparing
top-1 between them is a rigged race and nothing here claims otherwise.

The question is the one the product exists for: **as the record thins, does the model notice?**
Every call offers an explicit way out — "INSUFFICIENT" — exactly as arXiv 2608.09080 did on
MedMCQA, where GPT-5 took it 19.2% of the time. If abstention stays flat while accuracy falls,
a model cannot gate itself and something has to gate it. If abstention climbs as the evidence
disappears, frontier models have solved part of this and our contribution is narrower than we
have been saying. Both are worth knowing; only one is comfortable.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from askfirst.ddxplus import load_patients  # noqa: E402
from askfirst.model import describe  # noqa: E402
from askfirst.schema import load_schema  # noqa: E402
from run_abstention import thin  # noqa: E402

HERE = Path(__file__).resolve().parent.parent.parent
OUT = HERE / "docs/results/rehearsal-claude-abstention.json"
MODEL = "claude-opus-5-5"
EFFORT = "low"
OUT_OF = "INSUFFICIENT"

ASK = """You are triaging a patient from an intake record. Choose the single most likely \
condition from the list, or answer {out} if the record does not contain enough to tell.

{out} is a real answer and the right one when the evidence is too thin. Do not guess.

CONDITIONS
{conditions}

RECORD
{record}

Reply with the condition name exactly as written above, or {out}. Nothing else."""


def main(cases, levels, model, effort="low"):
    global EFFORT
    EFFORT = effort
    import anthropic

    schema = load_schema("ddxplus")
    conditions = "\n".join(f"- {o}" for o in schema.outcomes)
    patients = [p for p in load_patients(
        str(HERE / "data/ddxplus/release_validate_patients"), limit=60000) if p["evidences"]]
    held = patients[46000:46000 + cases]

    import concurrent.futures as cf

    client = anthropic.Anthropic(max_retries=5)
    rows, spend = [], {"in": 0, "out": 0, "cached": 0}
    started = time.time()

    def ask(job):
        frac, whole, short = job
        prompt = ASK.format(out=OUT_OF, conditions=conditions,
                            record=describe(short["evidences"], schema))
        r = client.messages.create(
            model=model, max_tokens=64,
            output_config={"effort": EFFORT},
            system=[{"type": "text", "text": "You are a careful clinical triage assistant.",
                     "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": prompt}],
        )
        said = " ".join(b.text for b in r.content if b.type == "text").strip()
        abstained = OUT_OF.lower() in said.lower()
        match = next((o for o in schema.outcomes if o.lower() in said.lower()), None)
        return r.usage, {"kept": frac, "n": len(short["evidences"]), "said": said[:120],
                         "abstained": abstained, "picked": match,
                         "right": (match == whole["pathology"]) and not abstained,
                         "truth": whole["pathology"]}

    for frac in levels:
        jobs = [(frac, w, s) for w, s in zip(held, thin(held, frac))]
        with cf.ThreadPoolExecutor(8) as ex:
            for usage, row in ex.map(ask, jobs):
                spend["in"] += usage.input_tokens
                spend["out"] += usage.output_tokens
                spend["cached"] += getattr(usage, "cache_read_input_tokens", 0) or 0
                rows.append(row)
        done = [r for r in rows if r["kept"] == frac]
        print(f"  {frac:>5.0%} of the record: abstained {sum(r['abstained'] for r in done) / len(done):>6.1%}"
              f"   right {sum(r['right'] for r in done) / len(done):>6.1%}   ({len(done)} cases)",
              flush=True)

    cost = spend["in"] / 1e6 * 4.0 + spend["out"] / 1e6 * 20.0
    out = {"model": model, "effort": effort, "cases": len(held), "levels": list(levels),
           "seconds": round(time.time() - started, 1), "usage": spend,
           "approx_usd": round(cost, 2), "rows": rows}
    Path(OUT).write_text(json.dumps(out, indent=1))
    print(f"\n{len(rows)} calls, {spend['in']:,} in / {spend['out']:,} out "
          f"({spend['cached']:,} cached) — about ${cost:.2f}")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", type=int, default=100)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--levels", default="1.0,0.4,0.2")
    ap.add_argument("--effort", default="low")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if a.out:
        OUT = HERE / a.out
    main(a.cases, [float(x) for x in a.levels.split(",")], a.model, a.effort)
