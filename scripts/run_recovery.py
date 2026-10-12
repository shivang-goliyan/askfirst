"""The experiment from docs/METRIC.md: take a patient, delete one evidence they actually had,
and see whether the engine names it. Run from the repo root:

    python3 -I scripts/run_recovery.py data/ddxplus/release_validate_patients 400
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from askfirst.ablation import rank_gaps
from askfirst.ddxplus import NaiveBayes, load_patients
from askfirst.schema import fit_priors, load_schema


def wilson(hits, n, z=1.96):
    if not n:
        return 0.0, 0.0
    p = hits / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return max(0.0, centre - half), min(1.0, centre + half)


def main(path, cases):
    random.seed(7)
    patients = load_patients(path, limit=6000)
    schema = load_schema("ddxplus")
    scorer = NaiveBayes().fit(patients[:4000])

    held = [p for p in patients[4000:] if len(p["evidences"]) >= 4]
    schema = schema.with_priors(fit_priors([p["evidences"] for p in patients[:4000]], schema))

    KS = (1, 3, 5, 10, 20, 50)
    hits = {k: 0 for k in KS}
    pool = n = 0

    for patient in held[:cases]:
        full = dict(patient["evidences"])
        dropped = random.choice(list(full))
        reduced = {k: v for k, v in full.items() if k != dropped}

        candidates = [f for f in schema.fields if f not in reduced]
        ranked = [g.field for g in rank_gaps(reduced, scorer, schema, candidates=candidates)]
        if not ranked:
            continue

        n += 1
        pool += len(candidates)
        for k in KS:
            hits[k] += dropped in ranked[:k]

    avg_pool = pool / n if n else 0.0
    print(f"cases {n}   mean candidate pool {avg_pool:.0f} of {len(schema.fields)} fields\n")
    print(f"{'k':>4}  {'recall':>7}  {'95% CI':>18}  {'chance':>7}  {'lift':>6}")
    for k in KS:
        lo, hi = wilson(hits[k], n)
        rate = hits[k] / n if n else 0.0
        base = min(1.0, k / avg_pool) if avg_pool else 0.0
        lift = rate / base if base else 0.0
        print(f"{k:>4}  {rate:>6.1%}   [{lo:>5.1%}, {hi:>5.1%}]  {base:>6.2%}  {lift:>5.1f}x")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 200)
