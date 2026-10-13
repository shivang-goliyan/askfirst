"""Why not just use conformal prediction? Measured, rather than argued.

    python3 scripts/run_conformal.py data/ddxplus/release_validate_patients

Selective prediction with a precision target is not a new idea and conformal prediction is the
framework for it. The honest thing is to name it, implement the standard version, and show where
ours differs and why — not to invent vocabulary and hope nobody asks.

Three rules, same scorer, same test stream, same target:

  marginal       one global threshold on the margin, chosen on a calibration split. This is
                 split-conformal selective prediction in its plainest form.
  Mondrian       a separate threshold per group, the group being how many findings are in hand
                 and how unusual they are. Vovk's Mondrian/class-conditional predictors are the
                 same idea with the partition chosen differently.
  what we ship   the Mondrian partition, but an isotonic fit of P(correct) inside each group
                 rather than a quantile, plus a refusal below an estimated-completeness floor
                 that no conformal variant has an equivalent of.

The last one is the only one that can refuse a record for being too thin REGARDLESS of what the
score says, which matters because the exchangeability that conformal guarantees rest on is
exactly what `2026-10-13-missing-not-at-random.md` measured failing."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from askfirst.ablation import argmax  # noqa: E402
from askfirst.calibrate import CEILING, FLOOR, Calibrator, Completeness, bucket_of, band_of  # noqa: E402
from askfirst.ddxplus import load_patients  # noqa: E402
from askfirst.metrics import wilson  # noqa: E402
from askfirst.missing import cut, mechanisms  # noqa: E402
from askfirst.schema import load_schema  # noqa: E402
from askfirst.softmax import SoftmaxScorer  # noqa: E402
from run_abstention import KEPT, WEIGHTS  # noqa: E402

BAKE = Path("src/askfirst/baked")
OUT = Path("docs/results/conformal.json")
TARGET = 0.95
CASES = 3000


def stream(model, pool, ways, rates):
    rows = []
    for key in ways.values():
        for frac in KEPT:
            for case in cut(pool, frac, key):
                record = case["evidences"]
                dist = model(record)
                rows.append({
                    "record": record, "margin": max(dist.values()),
                    "right": argmax(dist) == case["pathology"],
                    "group": f"{bucket_of(len(record))}|"
                             f"{band_of(sum(1 - rates.get(n, 0.0) for n in record) / max(len(record), 1))}",
                })
    return rows


def threshold(rows, target):
    """Lowest margin whose accepted set still hits the target. The conformal construction, in
    the form selective prediction needs: a quantile of the calibration scores."""
    ranked = sorted(rows, key=lambda r: -r["margin"])
    best, hits = None, 0
    for i, r in enumerate(ranked, start=1):
        hits += r["right"]
        if hits / i >= target:
            best = r["margin"]
    return best


def report(name, accepted, total, out):
    if not accepted:
        print(f"  {name:38} {'silent':>10} {0.0:>11.1%}")
        out[name] = None
        return
    right = sum(accepted)
    lo, hi = wilson(right, len(accepted))
    print(f"  {name:38} {right / len(accepted):>10.1%} {len(accepted) / total:>11.1%} "
          f"  [{lo:.1%}, {hi:.1%}]")
    out[name] = {"precision": round(right / len(accepted), 4),
                 "coverage": round(len(accepted) / total, 4),
                 "answered": len(accepted), "ci": [round(lo, 4), round(hi, 4)]}


def main(path):
    schema = load_schema("ddxplus")
    rates = json.loads((BAKE / "ddxplus_priors.json").read_text())["rates"]
    model = SoftmaxScorer.load(WEIGHTS, schema)
    cal = Calibrator.load(BAKE / "calibrator.json")
    seen = Completeness.load(BAKE / "completeness.npz", model.encode)
    ways = mechanisms(schema, rates)

    patients = [p for p in load_patients(path, limit=60000) if p["evidences"]]
    fit = stream(model, patients[40000:40000 + CASES], ways, rates)
    test = stream(model, patients[46000:46000 + CASES], ways, rates)
    print(f"{len(fit):,} calibration rows, {len(test):,} test rows, target {TARGET:.0%}\n")
    print(f"  {'rule':38} {'precision':>10} {'coverage':>11}   95% interval")

    out = {}
    # 1. split-conformal, marginal
    cut_marginal = threshold(fit, TARGET)
    report("split-conformal, one threshold",
           [r["right"] for r in test if cut_marginal and r["margin"] >= cut_marginal],
           len(test), out)

    # 2. Mondrian: a threshold per group
    groups = {}
    for r in fit:
        groups.setdefault(r["group"], []).append(r)
    per = {g: threshold(rows, TARGET) for g, rows in groups.items()}
    report("Mondrian, a threshold per group",
           [r["right"] for r in test
            if per.get(r["group"]) is not None and r["margin"] >= per[r["group"]]],
           len(test), out)

    # 3. what ships
    report("ours: isotonic in-group + the floor",
           [r["right"] for r in test
            if seen(r["record"]) >= FLOOR and len(r["record"]) <= CEILING
            and cal(r["margin"], r["record"]) >= TARGET],
           len(test), out)

    # 4. and the floor's own contribution, with the calibration removed
    report("the floor alone, no calibration",
           [r["right"] for r in test if seen(r["record"]) >= FLOOR],
           len(test), out)

    # The comparison above fits every rule on the same mixture the test comes from, which is the
    # friendly case. The one that matters is shift: fit on six ways a record goes short and test
    # on the seventh, which is the situation any deployment is actually in.
    held = "standard questions, no follow-ups"
    some = {k: v for k, v in ways.items() if k != held}
    fit_part = stream(model, patients[40000:40000 + CASES], some, rates)
    test_held = stream(model, patients[46000:46000 + CASES],
                       {held: ways[held]}, rates)
    print(f"\nAnd under shift — fitted on six patterns, tested on the seventh "
          f"({held!r}):\n")
    print(f"  {'rule':38} {'precision':>10} {'coverage':>11}   95% interval")

    shifted = {}
    cut_m = threshold(fit_part, TARGET)
    report("split-conformal, one threshold",
           [r["right"] for r in test_held if cut_m and r["margin"] >= cut_m],
           len(test_held), shifted)
    g2 = {}
    for r in fit_part:
        g2.setdefault(r["group"], []).append(r)
    per2 = {g: threshold(rows, TARGET) for g, rows in g2.items()}
    report("Mondrian, a threshold per group",
           [r["right"] for r in test_held
            if per2.get(r["group"]) is not None and r["margin"] >= per2[r["group"]]],
           len(test_held), shifted)
    report("ours: isotonic in-group + the floor",
           [r["right"] for r in test_held
            if seen(r["record"]) >= FLOOR and len(r["record"]) <= CEILING
            and cal(r["margin"], r["record"]) >= TARGET],
           len(test_held), shifted)

    OUT.write_text(json.dumps({"target": TARGET, "calibration_rows": len(fit),
                               "test_rows": len(test), "rules": out,
                               "held_out_pattern": held, "under_shift": shifted}, indent=1))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/ddxplus/release_validate_patients")
