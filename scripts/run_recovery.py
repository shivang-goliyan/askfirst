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

    top1 = top3 = top10 = n = 0
    chance1 = chance3 = 0.0

    for patient in held[:cases]:
        full = dict(patient["evidences"])
        dropped = random.choice(list(full))
        reduced = {k: v for k, v in full.items() if k != dropped}

        candidates = [f for f in schema.fields if f not in reduced]
        ranked = [g.field for g in rank_gaps(reduced, scorer, schema, candidates=candidates)]
        if not ranked:
            continue

        n += 1
        top1 += ranked[0] == dropped
        top3 += dropped in ranked[:3]
        top10 += dropped in ranked[:10]
        chance1 += 1.0 / len(candidates)
        chance3 += 3.0 / len(candidates)

    print(f"cases                {n}")
    print(f"mean candidate pool  {len(schema.fields)} fields, "
          f"~{sum(1 for f in schema.fields):d} candidates per case")
    print()
    for label, hits, k, chance in (
        ("top-1 ", top1, 1, chance1), ("top-3 ", top3, 3, chance3),
        ("top-10", top10, 10, chance3 * 10 / 3),
    ):
        lo, hi = wilson(hits, n)
        rate = hits / n if n else 0.0
        base = chance / n if n else 0.0
        lift = rate / base if base else 0.0
        print(f"{label} recovery   {rate:6.1%}   95% CI [{lo:.1%}, {hi:.1%}]"
              f"   chance {base:.2%}   lift {lift:>5.1f}x")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 200)
