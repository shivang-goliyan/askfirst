"""What is refusing worth, once the scorer is real?

    python3 scripts/run_economics.py data/ddxplus/release_validate_patients

A confident wrong decision costs CW, a referral to a person costs CR, a correct answer is free.
Sweep coverage at each level of record completeness and price the mix.

The previous version of this file reported 94% cheaper. That number came from a naive Bayes at
22.6% top-1 on complete records — with 1,185 wrong answers per 1,500 cases to avoid, refusing was
bound to look like a bargain. With a scorer that gets 99.6% on complete records there is
almost nothing to avoid, so the saving shrinks to 38% and the best policy answers 98% of cases
rather than 5%. What the completeness axis changes is how much to refuse, not whether to."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from askfirst.ablation import argmax  # noqa: E402
from askfirst.ddxplus import load_patients  # noqa: E402
from askfirst.schema import load_schema  # noqa: E402
from askfirst.softmax import SoftmaxScorer  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from run_abstention import KEPT, WEIGHTS, thin  # noqa: E402

COVERAGE = [i / 40 for i in range(1, 41)]
OUT = Path("docs/results/economics.json")


def priced(scorer, cases, cost_wrong=100.0, cost_refer=5.0):
    scored = []
    for case in cases:
        dist = scorer(case["evidences"])
        scored.append((max(dist.values()), argmax(dist) == case["pathology"]))
    scored.sort(key=lambda s: -s[0])
    n = len(scored)

    rows = []
    for share in COVERAGE:
        keep = max(1, int(n * share))
        wrong = sum(1 for _, right in scored[:keep] if not right)
        referred = n - keep
        rows.append({
            "coverage": keep / n,
            "accuracy": (keep - wrong) / keep,
            "wrong": wrong,
            "referred": referred,
            "cost": (wrong * cost_wrong + referred * cost_refer) / n,
        })
    return rows


def main(path, cases=6000):
    schema = load_schema("ddxplus")
    patients = [p for p in load_patients(path, limit=40000) if p["evidences"]]
    held = patients[30000:30000 + cases]
    model = SoftmaxScorer.load(WEIGHTS, schema)

    print(f"{len(held)} held-out patients. A confident wrong decision costs 100, "
          f"a referral costs 5.\n")
    print(f"{'evidence kept':>14} {'always answer':>14} {'best':>8} {'at coverage':>12} "
          f"{'saving':>9}")

    out = {}
    for frac in KEPT:
        rows = priced(model, thin(held, frac))
        always = rows[-1]
        best = min(rows, key=lambda r: r["cost"])
        saving = (always["cost"] - best["cost"]) / always["cost"] if always["cost"] else 0.0
        out[str(frac)] = {"always": always, "best": best, "saving": saving, "rows": rows}
        verdict = f"{saving:>8.0%}" if saving > 0.005 else "   none  "
        print(f"{frac:>13.0%} {always['cost']:>14.2f} {best['cost']:>8.2f} "
              f"{best['coverage']:>11.0%} {verdict}")

    print("\nThe top row is the finding people will not expect: with a complete record and a")
    print("scorer this good there is nothing to refuse, and refusing anything is pure cost.")
    print("This product is for thin records, and now we can say where the line is.\n")

    print("Sensitivity at 20% evidence — does the answer depend on flattering prices?")
    print(f"{'wrong : referral':>18} {'best coverage':>14} {'saving':>9}")
    for cw, cr in ((100, 5), (100, 20), (100, 50), (50, 5), (20, 5), (10, 5), (100, 1)):
        rows = priced(model, thin(held, 0.2), cw, cr)
        best, always = min(rows, key=lambda r: r["cost"]), rows[-1]
        gain = (always["cost"] - best["cost"]) / always["cost"]
        print(f"{f'{cw} : {cr}':>18} {best['coverage']:>13.0%} {gain:>8.0%}")

    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/ddxplus/release_validate_patients",
         int(sys.argv[2]) if len(sys.argv) > 2 else 6000)
