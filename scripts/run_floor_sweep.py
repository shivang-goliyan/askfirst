"""Where should the completeness floor actually sit? Measured, instead of chosen.

    python3 scripts/run_floor_sweep.py data/ddxplus/release_validate_patients [patients]

`FLOOR = 0.35` was picked by hand on the reasoning that below about a third of a record nothing
reaches a useful precision anyway. On the scorer that shipped until 14 October that was true. On
the scorer that expects holes it is not: with no floor at all the calibrated rule answers a
*fifth* of a record at 98.5% [97.9%, 99.0%] and a tenth at 95.7% [93.5%, 97.1%], and the floor
refuses both — so it is throwing away cases the calibration had measured it could answer.

Two experiments that disagreed led here. `run_make_it_unnecessary.py` found the floor costing
fourteen points of coverage for no measurable precision. `run_portability.py` found it rescuing a
badly-shaped rule, from 13 of 21 scorer-fold cells to 15 of 21. Both are true, and neither says
where the floor belongs — which is this script's job.

The rule applied below, stated before the numbers. Take the **lowest** floor that satisfies all
three:

  1. the mixed-stream clustered lower bound clears the target;
  2. it keeps the promise in all seven leave-one-missingness-pattern-out folds;
  3. and it keeps the promise **at every completeness level it answers at all** — not just in
     aggregate.

The third condition is the one that matters and the first draft of this script did not have it.
Aggregated over a stream that is mostly fuller records, a floor of zero looks fine: 99.5% overall.
Per level it is not fine — at a tenth of a record the no-floor rule lands at 95.7% with a lower
bound of 93.5%, and a buyer whose queue is mostly thin records would be promised 95% and handed
that. A promise that only holds on average is not the promise this product makes.

Lowest rather than best-looking, because every point of floor is coverage given up and coverage is
the entire economic case.

**Three splits, because two were not enough.** The first version of this script applied all three
conditions to the test rows and picked the winner, which is choosing a hyperparameter on the
evaluation set — the thing this repo was already caught doing once today. The second version fitted
on one split and chose on it, which picked a floor of zero that then broke a completeness level on
held-out data. So: the calibration is **fitted** on one split, the floor is **chosen** on a second,
and everything is **reported** on a third. All three tables are printed, because whether the choice
transfers is the actual result."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from askfirst.calibrate import CEILING, FLOOR, Calibrator, Completeness  # noqa: E402
from askfirst.ddxplus import load_patients  # noqa: E402
from askfirst.metrics import clustered, precision_text  # noqa: E402
from askfirst.missing import mechanisms  # noqa: E402
from askfirst.schema import load_schema  # noqa: E402
from askfirst.softmax import SoftmaxScorer  # noqa: E402
from run_abstention import KEPT  # noqa: E402
from run_conformal import TARGET, stream  # noqa: E402

OUT = Path("docs/results/floor-sweep.json")
BAKE = Path("src/askfirst/baked")
WEIGHTS = BAKE / "ddxplus_softmax.npz"
FLOORS = (0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50)


def judge(rows, patients):
    if not rows:
        return None
    right = sum(1 for r in rows if r["right"])
    lo, hi = clustered(rows, patients)
    return {"precision": round(right / len(rows), 5), "answered": len(rows),
            "wrong": len(rows) - right,
            "ci": [round(lo, 4), round(hi, 4)] if lo is not None else None,
            "keeps_promise": bool(lo is not None and lo >= TARGET - 0.005)}


def main(path, cases=2000):
    schema = load_schema("ddxplus")
    rates = json.loads((BAKE / "ddxplus_priors.json").read_text())["rates"]
    model = SoftmaxScorer.load(WEIGHTS, schema)
    ways = mechanisms(schema, rates)
    patients = [p for p in load_patients(path, limit=46000 + cases) if p["evidences"]]
    fit_pool = patients[40000:40000 + cases]
    pick_pool = patients[42500:42500 + cases]
    test_pool = patients[46000:46000 + cases]

    fit = stream(model, fit_pool, ways, rates)
    pick = stream(model, pick_pool, ways, rates)
    test = stream(model, test_pool, ways, rates)
    print(f"{len(fit):,} rows to fit the calibration, {len(pick):,} to choose the floor, "
          f"{len(test):,} to report on — {cases:,} patients each, target {TARGET:.0%}")
    print(f"the floor in the shipped product is {FLOOR:.0%}, chosen by hand\n")

    # the calibration and the completeness estimate do not depend on the floor, so they are
    # fitted once per fold and every candidate floor is evaluated against the same fit
    def fitted(rows):
        cal = Calibrator(rates).fit(
            [(r["margin"], r["record"], r["right"]) for r in rows]).thin()
        seen = Completeness(model.encode).fit([(r["record"], r["true_n"]) for r in rows])
        return cal, seen

    cal, seen = fitted(fit)

    def sweep(rows, patients):
        out = {}
        for floor in FLOORS:
            taken = [r for r in rows
                     if seen(r["record"]) >= floor and len(r["record"]) <= CEILING
                     and cal(r["margin"], r["record"]) >= TARGET]
            out[str(floor)] = judge(taken, patients)
        return out

    def levels(rows, patients):
        out = {}
        for floor in FLOORS:
            cells = {}
            for frac in KEPT:
                taken = [r for r in rows
                         if abs(r["kept"] - frac) < 1e-9
                         and seen(r["record"]) >= floor and len(r["record"]) <= CEILING
                         and cal(r["margin"], r["record"]) >= TARGET]
                cells[str(frac)] = judge(taken, patients)
            judged = [c for c in cells.values() if c and c["answered"] >= 30]
            worst = min((c["precision"] for c in judged), default=None)
            out[str(floor)] = {
                "cells": cells,
                "all_levels_hold": all(c["keeps_promise"] for c in judged) if judged else False,
                "worst_level": round(worst, 5) if worst is not None else None,
            }
        return out

    on_pick, on_test = sweep(pick, len(pick_pool)), sweep(test, len(test_pool))
    pick_levels, by_level = levels(pick, len(pick_pool)), levels(test, len(test_pool))

    print(f"  {'floor':>6} | {'chosen on the second split':>31} | {'reported on the third':>31}")
    print(f"  {'':>6} | {'precision':>11} {'coverage':>8} {'levels':>10} | "
          f"{'precision':>11} {'coverage':>8} {'levels':>10}")
    for floor in FLOORS:
        cells = []
        for rows, lv, pool in ((on_pick, pick_levels, pick), (on_test, by_level, test)):
            row = rows[str(floor)]
            if row is None:
                cells.append(f"{'silent':>11} {'':>8} {'':>10}")
                continue
            ok = "hold" if lv[str(floor)]["all_levels_hold"] else "ONE BREAKS"
            cells.append(f"{precision_text(row['answered'] - row['wrong'], row['answered']):>11} "
                         f"{row['answered'] / len(pool):>8.1%} {ok:>10}")
        print(f"  {floor:>6.0%} | {cells[0]} | {cells[1]}")
    mixed = on_test

    print("\n  \"levels\" is whether every completeness level answering 30+ cases keeps the")
    print("  promise, not just the stream in aggregate. A floor of zero passes in aggregate and")
    print("  breaks at a tenth of a record, which is where a thin-record buyer actually sits.\n")

    print(f"\n  and under shift — folds kept, out of {len(ways)}:\n")
    folds = {}
    for held in ways:
        fold_cal, fold_seen = fitted([r for r in fit if r["way"] != held])
        rows = [r for r in pick if r["way"] == held]
        folds[held] = {}
        for floor in FLOORS:
            taken = [r for r in rows
                     if fold_seen(r["record"]) >= floor and len(r["record"]) <= CEILING
                     and fold_cal(r["margin"], r["record"]) >= TARGET]
            folds[held][str(floor)] = judge(taken, len(test_pool))

    print(f"  {'floor':>6} {'folds kept':>11} {'worst fold':>11} {'mean coverage':>14}")
    tally = {}
    for floor in FLOORS:
        live = [folds[h][str(floor)] for h in ways if folds[h][str(floor)]]
        if not live:
            tally[str(floor)] = None
            print(f"  {floor:>6.0%} {'all silent':>11}")
            continue
        n = sum(1 for r in live if r["keeps_promise"])
        worst = min(r["precision"] for r in live)
        cov = sum(r["answered"] for r in live) / max(1, sum(
            len([r for r in pick if r["way"] == h]) for h in ways))
        tally[str(floor)] = {"folds_kept": n, "folds": len(live),
                             "worst_precision": round(worst, 5),
                             "mean_coverage": round(cov, 4)}
        print(f"  {floor:>6.0%} {f'{n}/{len(live)}':>11} {worst:>11.2%} {cov:>14.1%}")

    # The rule, applied — plus one guard the first draft needed. As the floor rises, the thin
    # cells shrink and their intervals widen, so a cell can flip from holding to breaking on a
    # handful of cases. Requiring the chosen floor AND the next one up to both pass stops this
    # picking a value that only works at one point of a noisy sweep.
    def passes(floor):
        """On the CHOOSING split, plus the fold robustness. Never on the reporting rows."""
        row, fold = on_pick[str(floor)], tally[str(floor)]
        return bool(row and fold and row["keeps_promise"]
                    and fold["folds_kept"] == fold["folds"]
                    and pick_levels[str(floor)]["all_levels_hold"])

    picked = None
    for floor, nxt in zip(FLOORS, FLOORS[1:]):
        if passes(floor) and passes(nxt):
            picked = floor
            break

    print(f"\n{'=' * 80}")
    if picked is None:
        print("No floor in the sweep satisfies both conditions. The shipped one stays.")
    else:
        now, then = mixed[str(FLOOR)], mixed[str(picked)]
        print(f"The lowest floor that keeps the promise on the mixed stream AND in all "
              f"{len(ways)} folds: {picked:.0%}")
        if now and then and picked != FLOOR:
            gain = then["answered"] / len(test) - now["answered"] / len(test)
            print(f"Against the hand-picked {FLOOR:.0%}, that is {gain * 100:+.1f} points of "
                  f"coverage — {gain * 1000:+.0f} records per 1,000 that no longer need a person")
            print(f"and it costs {then['wrong'] - now['wrong']:+d} wrong answers across "
                  f"{len(test):,} rows.")
        elif picked == FLOOR:
            print(f"Which is the floor already shipping. It was picked by hand and the "
                  f"measurement agrees with it.")
    print(f"{'=' * 80}")

    OUT.write_text(json.dumps({
        "target": TARGET, "shipped_floor": FLOOR, "floors": list(FLOORS),
        "patients_each_split": cases, "test_rows": len(test),
        "ci_kind": "bootstrap over patients, 400 draws",
        "rule": "the lowest floor whose mixed-stream clustered lower bound clears the target "
                "and which keeps the promise in every leave-one-pattern-out fold",
        "on_pick": on_pick, "on_test": on_test,
        "levels_on_pick": pick_levels, "levels_on_test": by_level,
        "across_folds": tally, "picked": picked,
        "picked_on": "the second split; the third split is the report, not the choice",
    }, indent=1))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/ddxplus/release_validate_patients",
         int(sys.argv[2]) if len(sys.argv) > 2 else 2000)
