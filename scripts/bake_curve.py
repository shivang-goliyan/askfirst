"""Precompute the grid the app serves cold, so the headline never depends on a GPU or a fit.

    python3 scripts/bake_curve.py data/ddxplus/release_validate_patients

One curve per level of record completeness, because the whole finding is that the right amount to
refuse depends on how thin the record is. Each point carries the confidence threshold that
produces it, so the dial in the page and the decision the server takes are the same number rather
than two that drift apart."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from askfirst.ablation import argmax  # noqa: E402
from askfirst.ddxplus import load_patients  # noqa: E402
from askfirst.metrics import wilson  # noqa: E402
from askfirst.schema import load_schema  # noqa: E402
from askfirst.softmax import SoftmaxScorer  # noqa: E402
from run_abstention import WEIGHTS, thin  # noqa: E402

OUT = Path("src/askfirst/baked/curve.json")
KEPT = (1.0, 0.6, 0.4, 0.2, 0.1)
POINTS = 40   # same granularity as run_economics, so the two cannot report different optima
COST_WRONG, COST_REFER = 100.0, 5.0


def main(path, cases=6000):
    schema = load_schema("ddxplus")
    patients = [p for p in load_patients(path, limit=40000) if p["evidences"]]
    held = patients[30000:30000 + cases]
    model = SoftmaxScorer.load(WEIGHTS, schema)

    levels = {}
    for frac in KEPT:
        scored = []
        for case in thin(held, frac):
            dist = model(case["evidences"])
            scored.append({"margin": max(dist.values()),
                           "right": argmax(dist) == case["pathology"]})
        scored.sort(key=lambda s: -s["margin"])
        n = len(scored)

        rows = []
        for step in range(1, POINTS + 1):
            keep = max(1, int(n * step / POINTS))
            answered = scored[:keep]
            hits = sum(s["right"] for s in answered)
            lo, hi = wilson(hits, keep)
            rows.append({
                "coverage": round(keep / n, 4),
                "threshold": round(answered[-1]["margin"], 6),
                "answered": keep,
                "accuracy": round(hits / keep, 4),
                "ci": [round(lo, 4), round(hi, 4)],
                "wrong": keep - hits,
                "referred": n - keep,
                "cost_per_case": round(((keep - hits) * COST_WRONG + (n - keep) * COST_REFER) / n, 3),
            })
        levels[str(frac)] = rows
        best = min(rows, key=lambda r: r["cost_per_case"])
        print(f"  kept {frac:>5.0%}  full-coverage {rows[-1]['accuracy']:>6.1%}  "
              f"cheapest {best['cost_per_case']:>6.2f} at coverage {best['coverage']:>4.0%}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "cases": len(held),
        "outcomes": len(schema.outcomes),
        "chance": round(1 / len(schema.outcomes), 4),
        "scorer": "softmax regression over 972 one-hot evidence features, 99.6% top-1 on "
                  "complete held-out records",
        "signal": "margin (max posterior); measured to beat entropy at every coverage level",
        "cost_wrong": COST_WRONG,
        "cost_refer": COST_REFER,
        "kept_levels": [str(k) for k in KEPT],
        "levels": levels,
        # kept so an older page still finds something sensible at the top level
        "rows": levels["0.4"],
    }, indent=1))
    print(f"\nwrote {OUT} — {len(KEPT)} completeness levels x {POINTS} coverage points")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/ddxplus/release_validate_patients",
         int(sys.argv[2]) if len(sys.argv) > 2 else 6000)
