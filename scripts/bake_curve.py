"""Precompute the risk-coverage and cost curves into a JSON the app can serve cold.

The public URL has to keep working when the GPU is down, because credits are per account and a
72-hour window does not fit in one. So the headline figures are baked here, from a real run, and
served as a static artifact. Live scoring is a separate request that can fail without taking the
page with it.

    python3 -I scripts/bake_curve.py data/ddxplus/release_validate_patients 1500
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from askfirst.ablation import argmax, entropy
from askfirst.ddxplus import NaiveBayes, load_patients

OUT = Path("src/askfirst/baked/curve.json")


def wilson(hits, n, z=1.96):
    if not n:
        return 0.0, 0.0
    p = hits / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return max(0.0, c - h), min(1.0, c + h)


def main(path, cases):
    patients = load_patients(path, limit=8000)
    scorer = NaiveBayes().fit(patients[:4000])
    held = [p for p in patients[4000:] if p["evidences"]][:cases]

    scored = []
    for patient in held:
        dist = scorer(patient["evidences"])
        scored.append({
            "right": argmax(dist) == patient["pathology"],
            "margin": max(dist.values()),
            "entropy": entropy(dist),
        })

    ranked = sorted(scored, key=lambda s: s["margin"], reverse=True)
    n = len(ranked)
    rows = []
    for step in range(1, 21):
        kept = max(1, int(n * step / 20))
        answered = ranked[:kept]
        right = sum(s["right"] for s in answered)
        lo, hi = wilson(right, kept)
        wrong = kept - right
        rows.append({
            "coverage": round(kept / n, 4),
            # the margin at the cut: answer when confidence is at or above this
            "threshold": round(answered[-1]["margin"], 6),
            "answered": kept,
            "accuracy": round(right / kept, 4),
            "ci": [round(lo, 4), round(hi, 4)],
            "wrong": wrong,
            "referred": n - kept,
            "cost_per_case": round((wrong * 100 + (n - kept) * 5) / n, 3),
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "dataset": "DDXPlus validation split (CC BY 4.0)",
        "scorer": "naive Bayes over 223 evidences, fitted on 4,000 patients",
        "cases": n,
        "outcomes": 49,
        "chance": round(1 / 49, 4),
        "signal": "margin (max posterior); measured to beat entropy at every coverage level",
        "prices": {"confident_wrong": 100, "referral": 5, "correct": 0},
        "rows": rows,
    }, indent=1) + "\n")
    print(f"wrote {OUT} — {n} cases, {len(rows)} coverage points")
    print(f"  full coverage {rows[-1]['accuracy']:.1%} at cost {rows[-1]['cost_per_case']}")
    best = min(rows, key=lambda r: r["cost_per_case"])
    print(f"  cheapest      {best['accuracy']:.1%} at coverage {best['coverage']:.0%}, "
          f"cost {best['cost_per_case']} (n={best['answered']}, CI lower {best['ci'][0]:.1%})")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 1500)
