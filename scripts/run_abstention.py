"""Does refusing help? Measured against a scorer nobody can call weak.

    python3 scripts/run_abstention.py data/ddxplus/release_validate_patients

The first version of this script answered yes, loudly, and for the wrong reason: it used a naive
Bayes at 22.6% top-1 and scored COMPLETE records. Filtering the confident tenth took that from
21.0% to 85.3%, which is a statement about the baseline and not about the problem. A softmax
regression on the same features gets 99.6% on complete records, where the curve is flat and there
is nothing to refuse.

The product's premise was never complete records. It is "is there enough here?" — so completeness
is the axis that belongs on this grid, and the honest claim is about how the value of refusing
depends on how thin the record is. Trained on complete records, tested on incomplete ones, which
is also how it would be deployed.
"""

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from askfirst.ablation import argmax, entropy  # noqa: E402
from askfirst.ddxplus import NaiveBayes, load_patients  # noqa: E402
from askfirst.metrics import wilson  # noqa: E402
from askfirst.schema import load_schema  # noqa: E402
from askfirst.softmax import SoftmaxScorer  # noqa: E402

WEIGHTS = Path("src/askfirst/baked/ddxplus_softmax.npz")
KEPT = (1.0, 0.6, 0.4, 0.2, 0.1)
COVERAGE = (1.0, 0.75, 0.5, 0.25, 0.1)
OUT = Path("docs/results/abstention.json")


def thin(patients, frac, seed=13):
    """Hide evidence at random. Random rather than adversarial on purpose — an adversarial choice
    would measure our own ablation engine's taste instead of the scorer's behaviour."""
    rng = random.Random(seed)
    out = []
    for p in patients:
        items = list(p["evidences"].items())
        keep = max(1, int(len(items) * frac))
        out.append({"evidences": dict(rng.sample(items, keep)),
                    "pathology": p["pathology"], "n_fields": keep})
    return out


def curve(scorer, cases, signal="margin"):
    scored = []
    for case in cases:
        dist = scorer(case["evidences"])
        scored.append({
            "right": argmax(dist) == case["pathology"],
            "margin": max(dist.values()),
            "entropy": -entropy(dist),
        })
    scored.sort(key=lambda s: -s[signal])

    rows = []
    for share in COVERAGE:
        keep = scored[: max(1, int(len(scored) * share))]
        hits = sum(s["right"] for s in keep)
        lo, hi = wilson(hits, len(keep))
        rows.append({"coverage": share, "n": len(keep), "accuracy": hits / len(keep),
                     "wrong": len(keep) - hits, "ci": [lo, hi]})
    return rows


def main(path, cases=6000):
    schema = load_schema("ddxplus")
    patients = [p for p in load_patients(path, limit=40000) if p["evidences"]]
    train, held = patients[:30000], patients[30000:30000 + cases]

    if not WEIGHTS.exists():
        raise SystemExit("No scorer. Run scripts/train_scorer.py first.")
    model = SoftmaxScorer.load(WEIGHTS, schema)

    print(f"{len(held)} held-out patients, {len(schema.outcomes)} conditions, chance 2.0%")
    print("scorer: softmax regression, 99.6% top-1 on complete records\n")

    header = f"{'evidence kept':>14} {'fields':>7}" + "".join(f"{int(c * 100):>7}%" for c in COVERAGE)
    print(header)
    print(f"{'':>14} {'':>7}" + "".join(f"{'cov':>8}" for _ in COVERAGE))

    grid = {}
    for frac in KEPT:
        cases_at = thin(held, frac)
        rows = curve(model, cases_at)
        grid[frac] = rows
        avg = sum(c["n_fields"] for c in cases_at) / len(cases_at)
        print(f"{frac:>13.0%} {avg:>7.1f}" + "".join(f"{r['accuracy']:>7.1%} " for r in rows))

    print("\nSame grid, as a 95% interval on the answered cases:")
    for frac in KEPT:
        cells = " ".join(f"[{r['ci'][0]:.0%},{r['ci'][1]:.0%}]" for r in grid[frac])
        print(f"{frac:>13.0%}  {cells}")

    print("\nmargin against entropy as the confidence signal, at 40% of the evidence:")
    thin40 = thin(held, 0.4)
    for signal in ("margin", "entropy"):
        rows = curve(model, thin40, signal)
        print(f"  {signal:<8}" + "".join(f"{r['accuracy']:>8.1%}" for r in rows))

    print("\nand the scorer this replaced, at the same 40%, to show why everything was re-measured:")
    nb = NaiveBayes().fit(train)
    rows = curve(nb, thin40)
    print(f"  {'naive bayes':<8}" + "".join(f"{r['accuracy']:>8.1%}" for r in rows))

    OUT.write_text(json.dumps({"coverage_points": COVERAGE, "kept": KEPT,
                               "grid": {str(k): v for k, v in grid.items()}}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/ddxplus/release_validate_patients",
         int(sys.argv[2]) if len(sys.argv) > 2 else 6000)
