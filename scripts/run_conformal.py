"""Why not just use conformal prediction? Measured, rather than argued — and measured fairly,
which took two attempts.

    python3 scripts/run_conformal.py data/ddxplus/release_validate_patients [patients]

Selective prediction with a precision target is not a new idea and conformal prediction is the
framework for it. The honest thing is to name it, implement the standard version, and show where
ours differs and why — not to invent vocabulary and hope nobody asks.

WHAT THE FIRST VERSION GOT WRONG. It reported that under missingness shift the per-group
threshold fell to 92.7% while ours held at 98.9%. That comparison was rigged, and not subtly:
the baselines were refitted on six patterns and tested on the seventh, while *ours* was the
shipped calibrator — loaded off disk, fitted on all seven, including the one being held out. It
had seen the test condition and they had not. The result said nothing about robustness.

This version fixes four things, all of which make the comparison harder for us:

  - every component is refitted per fold, ours included, on the six patterns only;
  - all seven leave-one-pattern-out folds are run, not the one that flattered us;
  - the baselines are offered the same completeness floor, so the floor is isolated from the
    calibration rather than being ours alone;
  - at matched coverage the baselines are allowed to pick their operating point ON THE TEST
    ranking, which we are not. That flatters them on purpose: if we still come out ahead against
    a baseline reading its own answers, the margin is real.

A NOTE ON THE NAME. `threshold()` below is a quantile of the calibration scores chosen so the
accepted set hits a target accuracy. That is selective prediction with a Mondrian-style
partition — it is the standard practical construction, and it is NOT a conformal prediction set
and carries no conformal coverage guarantee. Conformal guarantees marginal coverage of a
prediction SET; what a buyer here asks for is precision conditional on having answered, which is
a different quantity (Angelopoulos & Bates, arXiv:2107.07511; Vovk, Gammerman & Shafer 2005 for
the Mondrian partition). The baselines are named for what they are and the write-up says so."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from askfirst.ablation import argmax  # noqa: E402
from askfirst.calibrate import CEILING, FLOOR, Calibrator, Completeness, band_of, bucket_of  # noqa: E402
from askfirst.ddxplus import load_patients  # noqa: E402
from askfirst.metrics import clustered  # noqa: E402
from askfirst.missing import cut, mechanisms  # noqa: E402
from askfirst.schema import load_schema  # noqa: E402
from askfirst.softmax import SoftmaxScorer  # noqa: E402
from run_abstention import KEPT, WEIGHTS  # noqa: E402

BAKE = Path("src/askfirst/baked")
OUT = Path("docs/results/conformal.json")
TARGET = 0.95
CASES = 2000


def stream(model, pool, ways, rates):
    """Every record, every way of going short, every level — tagged with which way, so a fold
    can be sliced out of one pass instead of rebuilding the stream seven times."""
    rows = []
    for name, key in ways.items():
        for frac in KEPT:
            for i, case in enumerate(cut(pool, frac, key)):
                record = case["evidences"]
                dist = model(record)
                rows.append({
                    "record": record, "margin": max(dist.values()),
                    "true_n": case["true_n"], "who": i, "way": name,
                    "right": argmax(dist) == case["pathology"],
                    "group": f"{bucket_of(len(record))}|"
                             f"{band_of(sum(1 - rates.get(n, 0.0) for n in record) / max(len(record), 1))}",
                })
    return rows


def threshold(rows, target):
    """Lowest margin whose accepted set still hits the target on the calibration split.

    A quantile of the calibration scores. Standard practice for selective prediction; see the
    note at the top of this file about why calling it conformal would be an overclaim."""
    ranked = sorted(rows, key=lambda r: -r["margin"])
    best, hits = None, 0
    for i, r in enumerate(ranked, start=1):
        hits += r["right"]
        if hits / i >= target:
            best = r["margin"]
    return best


def score(name, accepted, total, patients):
    if not accepted:
        return {"rule": name, "precision": None, "coverage": 0.0, "answered": 0, "ci": None,
                "keeps_promise": None}
    right = sum(1 for r in accepted if r["right"])
    lo, hi = clustered(accepted, patients)
    return {"rule": name, "precision": round(right / len(accepted), 4),
            "coverage": round(len(accepted) / total, 4), "answered": len(accepted),
            "ci": [round(lo, 4), round(hi, 4)] if lo is not None else None,
            "keeps_promise": None if lo is None else bool(lo >= TARGET - 0.005)}


def show(rows):
    print(f"  {'rule':44} {'precision':>10} {'coverage':>10}   {'clustered':>18}  promise")
    for r in rows:
        if r["precision"] is None:
            print(f"  {r['rule']:44} {'silent':>10} {0.0:>10.1%}   {'—':>18}")
            continue
        band = f"[{r['ci'][0]:.1%}, {r['ci'][1]:.1%}]" if r["ci"] else "—"
        mark = "kept" if r["keeps_promise"] else "BROKEN"
        print(f"  {r['rule']:44} {r['precision']:>10.1%} {r['coverage']:>10.1%}   "
              f"{band:>18}  {mark}")


def rules_on(fit, test, patients, rates, encode):
    """Fit every rule on `fit` and score every rule on `test`. Nothing is loaded off disk, so
    whatever `fit` has not seen, no rule has seen."""
    out = []

    cut_one = threshold(fit, TARGET)
    out.append(score("one global threshold",
                     [r for r in test if cut_one is not None and r["margin"] >= cut_one],
                     len(test), patients))

    groups = {}
    for r in fit:
        groups.setdefault(r["group"], []).append(r)
    per = {g: threshold(rows, TARGET) for g, rows in groups.items()}
    mondrian = [r for r in test
                if per.get(r["group"]) is not None and r["margin"] >= per[r["group"]]]
    out.append(score("a threshold per group (Mondrian partition)", mondrian, len(test), patients))

    seen = Completeness(encode).fit([(r["record"], r["true_n"]) for r in fit])
    out.append(score("a threshold per group + the same floor",
                     [r for r in mondrian if seen(r["record"]) >= FLOOR],
                     len(test), patients))

    cal = Calibrator(rates).fit(
        [(r["margin"], r["record"], r["right"]) for r in fit]).thin()
    ours = [r for r in test
            if seen(r["record"]) >= FLOOR and len(r["record"]) <= CEILING
            and cal(r["margin"], r["record"]) >= TARGET]
    out.append(score("ours: isotonic in-group + the floor", ours, len(test), patients))

    out.append(score("the floor alone, no calibration",
                     [r for r in test if seen(r["record"]) >= FLOOR], len(test), patients))

    # And the fair-to-them reading. Every threshold rule accepts a prefix of the margin ranking,
    # so "the Mondrian rule at our coverage" and "the global rule at our coverage" are the same
    # set of rows — there is one comparison here, not two, and the first version of this printed
    # it twice at identical values before anyone noticed what that meant.
    #
    # It is the honest test of the CALIBRATION as distinct from the floor: stop the raw margin
    # ranking exactly where we stopped and see whether reading P(correct) bought any accuracy.
    # The ranking gets to choose its cut-off on the TEST set, which we never do.
    matched = []
    if ours:
        best = sorted(test, key=lambda r: -r["margin"])[:len(ours)]
        row = score("the raw margin ranking, stopped at our coverage", best, len(test), patients)
        row["note"] = ("cut-off read off the test ranking, which no deployable rule can do — "
                       "this flatters the baseline on purpose")
        matched.append(row)

        # The row above compares a POLICY against a policy, and our accepted set is not a prefix
        # of the margin ranking — the floor throws out rows the margin would have taken. So any
        # gap it shows could be the floor's work rather than the calibration's, and reading it as
        # "the calibration buys ordering" was a mistake a reviewer caught.
        #
        # This isolates ordering properly: give BOTH arms the same eligibility (ceiling and
        # floor), then take the same number of rows from each, one ranked by the calibrated
        # probability and one by the raw margin. Same pool, same size, only the sort key differs.
        eligible = [r for r in test
                    if seen(r["record"]) >= FLOOR and len(r["record"]) <= CEILING]
        if eligible:
            want = min(len(ours), len(eligible))
            by_cal = sorted(eligible, key=lambda r: -cal(r["margin"], r["record"]))[:want]
            by_raw = sorted(eligible, key=lambda r: -r["margin"])[:want]
            for label, rows in (("inside the floor, ranked by the calibration", by_cal),
                                ("inside the floor, ranked by the raw margin", by_raw)):
                row = score(label, rows, len(test), patients)
                row["note"] = ("same eligible pool, same size, only the sort key differs — this "
                               "is the row that isolates ordering from the floor")
                matched.append(row)
    return out, matched


def main(path, cases=CASES):
    schema = load_schema("ddxplus")
    rates = json.loads((BAKE / "ddxplus_priors.json").read_text())["rates"]
    model = SoftmaxScorer.load(WEIGHTS, schema)
    ways = mechanisms(schema, rates)

    patients = [p for p in load_patients(path, limit=46000 + cases) if p["evidences"]]
    fit_pool = patients[40000:40000 + cases]
    test_pool = patients[46000:46000 + cases]
    fit = stream(model, fit_pool, ways, rates)
    test = stream(model, test_pool, ways, rates)
    print(f"{len(fit):,} calibration rows and {len(test):,} test rows, from {cases:,} and "
          f"{cases:,} patients, target {TARGET:.0%}")
    print(f"intervals are bootstrapped over patients, because {len(KEPT)} levels x "
          f"{len(ways)} patterns is 35 views of each person\n")

    print("In distribution — every rule fitted on all seven patterns, tested on all seven:\n")
    plain, matched = rules_on(fit, test, len(test_pool), rates, model.encode)
    show(plain)
    if matched:
        print()
        show(matched)

    print(f"\n\nUnder shift — fit on six patterns, test on the seventh. Every component "
          f"refitted,\nours included. All {len(ways)} folds:\n")
    folds = {}
    for held in ways:
        fold_fit = [r for r in fit if r["way"] != held]
        fold_test = [r for r in test if r["way"] == held]
        print(f"  held out: {held!r}  ({len(fold_fit):,} fit rows, {len(fold_test):,} test)")
        rows, extra = rules_on(fold_fit, fold_test, len(test_pool), rates, model.encode)
        show(rows)
        if extra:
            show(extra)
        print()
        folds[held] = {"rules": rows, "at_matched_coverage": extra}

    print("Across the seven folds:\n")
    print(f"  {'rule':44} {'worst precision':>16} {'folds kept':>11} {'mean coverage':>14}")
    tally = {}
    names = [r["rule"] for r in folds[next(iter(folds))]["rules"]]
    for name in names:
        rows = [next(r for r in folds[h]["rules"] if r["rule"] == name) for h in folds]
        live = [r for r in rows if r["precision"] is not None]
        if not live:
            continue
        worst = min(live, key=lambda r: r["precision"])
        kept = sum(1 for r in live if r["keeps_promise"])
        cov = sum(r["coverage"] for r in live) / len(live)
        tally[name] = {"worst_precision": worst["precision"], "worst_fold": None,
                       "folds_kept": kept, "folds": len(live), "mean_coverage": round(cov, 4)}
        for h in folds:
            if next(r for r in folds[h]["rules"] if r["rule"] == name) is worst:
                tally[name]["worst_fold"] = h
        print(f"  {name:44} {worst['precision']:>15.1%}  {f'{kept}/{len(live)}':>11} "
              f"{cov:>14.1%}")

    OUT.write_text(json.dumps({
        "target": TARGET, "floor": FLOOR, "patients_each_split": cases,
        "calibration_rows": len(fit), "test_rows": len(test),
        "ci_kind": "bootstrap over patients, 400 draws",
        "in_distribution": plain, "in_distribution_at_matched_coverage": matched,
        "leave_one_pattern_out": folds, "across_folds": tally,
        "retracted": "An earlier version of this experiment refitted only the baselines on six "
                     "patterns and reused the shipped calibrator, which had been fitted on all "
                     "seven. It reported 98.9% for us against 92.7% for Mondrian under shift. "
                     "That comparison was invalid and those two numbers should not be quoted.",
    }, indent=1))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/ddxplus/release_validate_patients",
         int(sys.argv[2]) if len(sys.argv) > 2 else CASES)
