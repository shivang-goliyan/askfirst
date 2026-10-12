"""Proposer recall — the number that caps the whole pipeline.

The engine ablates a shortlist. Whatever the model does afterwards, it can only re-rank what the
proposer handed it, so if the field we need is not on the list it is unreachable. Measured:
a marginal naive Bayes recalls 31.8% at k=20, which caps a finished system near a third.

Run it on whatever proposers are available. With ASKFIRST_VLLM_URL set, the model joins in and
this becomes the first thing worth spending GPU time on.

    python3 -I scripts/run_proposer_recall.py data/ddxplus/release_validate_patients 200
    ASKFIRST_VLLM_URL=http://127.0.0.1:8000/v1 python3 -I scripts/run_proposer_recall.py ... 200
"""
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from askfirst.ddxplus import NaiveBayes, load_patients
from askfirst.model import Endpoint, ModelProposer
from askfirst.propose import MarginalProposer, PathologyProposer
from askfirst.schema import fit_priors, load_schema

KS = (1, 3, 5, 10, 20)


def wilson(hits, n, z=1.96):
    if not n:
        return 0.0, 0.0
    p = hits / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return max(0.0, c - h), min(1.0, c + h)


def measure(name, proposer, cases, budget=None):
    hits = {k: 0 for k in KS}
    n, failed, started = 0, 0, time.time()

    for full, dropped in cases:
        if budget and time.time() - started > budget:
            break
        reduced = {k: v for k, v in full.items() if k != dropped}
        try:
            ranked = proposer(reduced, k=max(KS))
        except NotImplementedError:
            return None
        except Exception:
            failed += 1
            continue
        n += 1
        for k in KS:
            hits[k] += dropped in ranked[:k]

    if not n:
        return None
    took = time.time() - started
    return {
        "name": name, "n": n, "failed": failed,
        "per_case": took / n,
        "recall": {k: hits[k] / n for k in KS},
        "ci": {k: wilson(hits[k], n) for k in KS},
    }


def main(path, count):
    random.seed(13)
    patients = load_patients(path, limit=6000)
    schema = load_schema("ddxplus")
    scorer = NaiveBayes().fit(patients[:4000])
    schema = schema.with_priors(fit_priors([p["evidences"] for p in patients[:4000]], schema))

    cases = []
    for patient in patients[4000:]:
        if len(patient["evidences"]) >= 4 and len(cases) < count:
            full = dict(patient["evidences"])
            cases.append((full, random.choice(list(full))))

    pool = len(schema.fields)
    print(f"{len(cases)} cases, {pool} candidate fields, seed 13\n")

    endpoint = Endpoint()
    runs = [
        ("pathology (cpu)", PathologyProposer(scorer, scorer), None),
        ("marginal  (cpu)", MarginalProposer(scorer, schema), 180),
    ]
    if endpoint.available():
        runs.insert(0, (endpoint.describe()[:21], ModelProposer(schema, endpoint), None))
    else:
        print("No ASKFIRST_VLLM_URL set, so the model proposer is skipped. It is the one that\n"
              "matters: the CPU proposers know co-occurrence, not medicine.\n")

    results = [r for r in (measure(name, prop, cases, budget)
                           for name, prop, budget in runs) if r]

    head = "  ".join(f"@{k}".rjust(7) for k in KS)
    print(f"{'proposer':<20}{head}{'per case':>11}{'n':>6}")
    for r in results:
        row = "  ".join(f"{r['recall'][k]:6.1%}".rjust(7) for k in KS)
        print(f"{r['name']:<20}{row}{r['per_case']:>10.2f}s{r['n']:>6}")
        if r["failed"]:
            print(f"{'':<20}({r['failed']} cases errored and were skipped)")

    chance = {k: min(1.0, k / pool) for k in KS}
    row = "  ".join(f"{chance[k]:6.1%}".rjust(7) for k in KS)
    print(f"{'chance':<20}{row}")

    print()
    for r in results:
        lo, hi = r["ci"][10]
        verdict = "clears the 40% bar" if lo >= 0.40 else "below the 40% bar"
        print(f"{r['name']}: recall@10 {r['recall'][10]:.1%} "
              f"[{lo:.1%}, {hi:.1%}] — {verdict}")
    print("\n40% at k=10 is the kill criterion for the advice feature. The refusal feature does\n"
          "not depend on it; see docs/results/2026-10-13-the-refusal-works.md")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 200)
