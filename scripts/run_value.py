"""What is this worth, with the prices taken from somewhere rather than invented?

    python3 scripts/run_value.py data/ddxplus/release_validate_patients

Every economics number in this repo so far used a confident wrong answer costing 100 and a
handover costing 5. Those were placeholders. They were never argued for, and a ratio is the only
thing the conclusion depends on, so this works out what the published literature implies the
ratio is and puts our assumption next to it.

What the handover costs. Three Canadian jurisdictions put the cost per triage call at C$10 to
C$27 (CCOHTA Technology Report 43, Nov 2003; INAHTA Brief 2004/53). That is the clearest
published per-call figure we could find; it is twenty years old and Canadian, and nothing here
leans on its precision.

What a confident wrong answer costs. Not a malpractice payout — most wrong answers harm nobody.
The expected cost is P(this error ends in serious harm) x what a serious harm costs.

  P(harm | error): Newman-Toker et al., BMJ Qual Saf 2024;33(2):109-120, report a weighted mean
  error rate of 11.1% and a serious harm rate of 4.4% per dangerous-disease case, which divides
  out to about 40% of errors on those presentations ending in serious harm. That is a ceiling,
  not an average: it is measured on vascular events, infections and cancers, the presentations
  selected for being dangerous. An unselected queue is far lower, and 1% is used as a floor.

  cost of a serious harm: CRICO's Comparative Benchmarking System gives an average payment of
  $422,000 on ambulatory diagnosis-related cases filed 2009-2013, with 35% of those cases closing
  with any payment at all. A paid claim is a poor proxy for a harm in both directions -- it misses
  every harm that never becomes a claim, and it counts the legal cost rather than the human one.

So the ratio a confident wrong answer bears to a handover is somewhere between about 200:1 and
8,000:1. Ours was 20:1. The interesting part is what that does to the answer."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from askfirst.ablation import argmax  # noqa: E402
from askfirst.calibrate import FLOOR, Calibrator, Completeness  # noqa: E402
from askfirst.ddxplus import load_patients  # noqa: E402
from askfirst.metrics import clustered, wilson  # noqa: E402
from askfirst.missing import cut, mechanisms  # noqa: E402
from askfirst.schema import load_schema  # noqa: E402
from askfirst.softmax import SoftmaxScorer  # noqa: E402
from run_abstention import KEPT, WEIGHTS  # noqa: E402

BAKE = Path("src/askfirst/baked")
OUT = Path("docs/results/value.json")
CASES = 6000
REFER = 20.0            # mid-point of the published C$10-27, in whole dollars
HARM = 422_000.0        # CRICO average payment, ambulatory diagnosis-related, filed 2009-2013
HARM_RATE = (0.01, 0.396)   # floor we assume; ceiling from 4.4 / 11.1 on dangerous presentations
# 0.0 answers everything, 1.01 refuses everything. Both ends belong in the policy set: leave
# the second one out and the sweep reports a "cheapest" policy that costs twice what refusing
# the lot would, which is how a price sweep flatters whatever it was built to evaluate.
TARGETS = (0.0, 0.5, 0.7, 0.8, 0.9, 0.95, 0.98, 0.99, 0.995, 1.01)


def stream(model, pool, ways):
    """A queue of records cut short for every reason and to every degree — what a deployment
    sees, rather than one tidy slice of it.

    Each row carries the patient it came from. 210,000 rows are 6,000 patients seen 35 ways, not
    210,000 patients, and an interval that forgets this is narrower than it has any right to be."""
    rows = []
    for key in ways.values():
        for frac in KEPT:
            for who, case in enumerate(cut(pool, frac, key)):
                dist = model(case["evidences"])
                rows.append({"record": case["evidences"], "margin": max(dist.values()),
                             "who": who, "right": argmax(dist) == case["pathology"]})
    return rows



def policy(rows, target):
    """Answer when the calibrated chance clears the target, hand over otherwise."""
    if target <= 0:
        return rows, []
    if target > 1.0:
        return [], rows
    answered = [r for r in rows if r["enough"] and r["chance"] >= target]
    kept = set(id(r) for r in answered)
    return answered, [r for r in rows if id(r) not in kept]


def main(path):
    schema = load_schema("ddxplus")
    model = SoftmaxScorer.load(WEIGHTS, schema)
    cal = Calibrator.load(BAKE / "calibrator.json")
    seen = Completeness.load(BAKE / "completeness.npz", model.encode)
    rates = json.loads((BAKE / "ddxplus_priors.json").read_text())["rates"]
    patients = [p for p in load_patients(path, limit=60000) if p["evidences"]]
    test = patients[46000:46000 + CASES]

    rows = stream(model, test, mechanisms(schema, rates))
    for r in rows:
        r["enough"] = seen(r["record"]) >= FLOOR
        r["chance"] = cal(r["margin"], r["record"])
    n = len(rows)
    print(f"{n} records — {CASES} patients, seven ways of going short, five levels each.\n")

    lo, hi = (rate * HARM for rate in HARM_RATE)
    print(f"A handover costs {REFER:,.0f}. A confident wrong answer costs between "
          f"{lo:,.0f} and {hi:,.0f},")
    print(f"so the ratio is between {lo / REFER:,.0f}:1 and {hi / REFER:,.0f}:1. "
          f"We had been assuming 20:1.\n")

    print("Where the cheapest policy sits, as the price of being wrong rises:\n")
    print(f"  {'wrong : handover':>18} {'cheapest policy answers':>25} {'cost per case':>15} "
          f"{'against answering all':>22}")
    sweep = []
    for ratio in (2, 5, 20, 50, 100, 211, 500, 1000, 4000, 8351):
        wrong_cost = ratio * REFER
        best = None
        for target in TARGETS:
            answered, referred = policy(rows, target)
            wrong = sum(1 for r in answered if not r["right"])
            cost = (wrong * wrong_cost + len(referred) * REFER) / n
            if best is None or cost < best["cost"]:
                best = {"target": target, "cost": cost,
                        "coverage": len(answered) / n, "wrong": wrong}
        every = sum(1 for r in rows if not r["right"]) * wrong_cost / n
        sweep.append({"ratio": ratio, **best, "answer_all": every,
                      "refuse_all": REFER})
        shape = "answers nothing" if best["coverage"] == 0 else f"{best['coverage']:.1%}"
        print(f"  {ratio:>14,}:1 {shape:>24} {best['cost']:>15,.2f} "
              f"{every / best['cost']:>21.0f}x")

    # where answering anything at all stops paying
    crossover = next((s["ratio"] for s in sweep if s["coverage"] == 0), None)
    if crossover:
        under = [s for s in sweep if s["coverage"] > 0][-1]
        print(f"\nAbove about {crossover:,}:1 the cheapest policy is to answer NOTHING — refusing "
              f"the lot costs {REFER:,.0f}")
        print(f"a case and nothing beats it. Below it, at {under['ratio']:,}:1, the best policy "
              f"still answers {under['coverage']:.1%}.")
    print("\nSo cost minimisation stops being a useful objective somewhere inside the band the")
    print("literature implies: it tells you to switch the product off. The question a buyer")
    print("actually has is the other one — how much can it take off the queue at a fixed bar:\n")

    print(f"  {'promise':>9} {'kept':>9} {'queue it takes':>16} {'wrong per 1,000':>17} "
          f"{'clustered on patients':>25}")
    held = []
    loose = sum(1 for r in rows if r["right"])
    print(f"  {'answer all':>9} {loose / n:>9.1%} {1.0:>16.1%} "
          f"{(n - loose) / n * 1000:>17.1f} {'':>25}")
    for target in (0.8, 0.9, 0.95, 0.98, 0.99):
        answered, referred = policy(rows, target)
        if not answered:
            continue
        right = sum(1 for r in answered if r["right"])
        prec = right / len(answered)
        wlo, whi = clustered(answered, len(test))
        held.append({"target": target, "precision": round(prec, 4),
                     "coverage": round(len(answered) / n, 4),
                     "wrong_per_1000": round((len(answered) - right) / n * 1000, 2),
                     "ci": [round(wlo, 4), round(whi, 4)],
                     "ci_kind": "bootstrap over patients"})
        print(f"  {target:>9.0%} {prec:>9.1%} {len(answered) / n:>16.1%} "
              f"{(len(answered) - right) / n * 1000:>17.1f} "
              f"{f'[{wlo:.1%}, {whi:.1%}]':>25}")

    best = max(held, key=lambda h: h["coverage"] if h["target"] == 0.95 else -1)
    per_k = best["coverage"] * 1000
    print(f"\nPer 1,000 records at a {best['target']:.0%} promise: {per_k:,.0f} never reach a "
          f"person,")
    print(f"and {best['wrong_per_1000']:.1f} of the 1,000 are answered wrongly. At C$10-C$27 a "
          f"call that is")
    print(f"C${per_k * 10:,.0f}-C${per_k * 27:,.0f} of review capacity returned per thousand — "
          f"and we are not")
    print("putting a number on the harm avoided, because this is synthetic data.")

    OUT.write_text(json.dumps({
        "refer": REFER, "harm": HARM, "harm_rate": list(HARM_RATE),
        "records": n, "ratio_band": [lo / REFER, hi / REFER],
        "sweep": sweep, "promises": held,
    }, indent=1))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/ddxplus/release_validate_patients")
