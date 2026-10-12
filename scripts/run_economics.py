"""What is refusing actually worth?

"It declines to answer" is a weak thing to claim. "It costs less per thousand cases" is not.
Put a price on each outcome and the risk-coverage curve turns into a cost curve with an optimum
you can point at.

A confident wrong decision is expensive. A referral to a person is cheap but not free. A correct
answer is free. Sweep coverage, price the mix, and compare against a system that always answers.

    python3 -I scripts/run_economics.py data/ddxplus/release_validate_patients 1500
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from askfirst.ablation import argmax
from askfirst.ddxplus import NaiveBayes, load_patients


def sweep(scored, cost_wrong, cost_refer):
    ranked = sorted(scored, key=lambda s: s["margin"], reverse=True)
    n = len(ranked)
    rows = []
    for share in [i / 20 for i in range(1, 21)]:
        kept = max(1, int(n * share))
        answered = ranked[:kept]
        wrong = sum(1 for s in answered if not s["right"])
        referred = n - kept
        total = wrong * cost_wrong + referred * cost_refer
        rows.append({
            "coverage": kept / n,
            "accuracy": sum(s["right"] for s in answered) / kept,
            "wrong": wrong,
            "referred": referred,
            "cost": total / n,
        })
    return rows


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
        })
    n = len(scored)
    print(f"{n} cases, 49 pathologies\n")

    print("A confident wrong answer costs 100. A referral to a person costs 5.\n")
    rows = sweep(scored, 100, 5)
    always = rows[-1]
    best = min(rows, key=lambda r: r["cost"])
    print(f"{'coverage':>9} {'accuracy':>9} {'wrong':>7} {'referred':>9} {'cost/case':>10}")
    for r in rows:
        if r["coverage"] in {1.0} or abs(r["coverage"] - best["coverage"]) < 1e-9 \
           or round(r["coverage"], 2) in {0.75, 0.5, 0.25, 0.1}:
            mark = "  <- cheapest" if r is best else ""
            print(f"{r['coverage']:>8.0%} {r['accuracy']:>8.1%} {r['wrong']:>7} "
                  f"{r['referred']:>9} {r['cost']:>10.2f}{mark}")

    saved = always["cost"] - best["cost"]
    print(f"\nalways answer      {always['cost']:.2f} per case")
    print(f"refuse when unsure {best['cost']:.2f} per case at {best['coverage']:.0%} coverage")
    print(f"saving             {saved:.2f} per case = {saved / always['cost']:.0%} cheaper")
    print(f"                   {saved * 1000:,.0f} per thousand cases")

    print("\nHow sensitive is that to the prices? (optimum coverage, saving vs always answering)")
    print(f"{'wrong:refer':>12} {'best coverage':>14} {'saving':>9}")
    for cw, cr in ((100, 5), (100, 20), (100, 50), (50, 5), (20, 5), (10, 5), (100, 1)):
        rows = sweep(scored, cw, cr)
        b, a = min(rows, key=lambda r: r["cost"]), rows[-1]
        gain = (a["cost"] - b["cost"]) / a["cost"] if a["cost"] else 0.0
        print(f"{f'{cw}:{cr}':>12} {b['coverage']:>13.0%} {gain:>8.0%}")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 1500)
