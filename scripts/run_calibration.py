"""Does a confidence number mean the same thing on a thin record as on a full one?

    python3 scripts/run_calibration.py data/ddxplus/release_validate_patients

The page used to ask the visitor how complete the record was, and read the refusal threshold off
the curve for that level. Nobody deploying this knows their record is 40% complete — so either
one threshold works everywhere and the grid is a complication we invented, or it does not, and we
owe both an explanation and a way to pick the level without asking.

It does not. This script measures why, fits the two pieces that fix it, and bakes them.

Fresh patients throughout. The scorer was fitted on the first 30,000 and the published curve
measured on 30,000-36,000; nothing below touches either."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from askfirst.ablation import argmax  # noqa: E402
from askfirst.calibrate import FLOOR, Calibrator, Completeness  # noqa: E402
from askfirst.ddxplus import load_patients  # noqa: E402
from askfirst.metrics import ece, precision_text, reliability, wilson  # noqa: E402
from askfirst.missing import cut, mechanisms  # noqa: E402
from askfirst.schema import load_schema  # noqa: E402
from askfirst.softmax import SoftmaxScorer  # noqa: E402
from run_abstention import KEPT, WEIGHTS, thin  # noqa: E402

OUT = Path("docs/results/calibration.json")
BAKE = Path("src/askfirst/baked")
TARGET = 0.95
SPLIT = 6000


def gather(model, pool):
    """Every record at every level of thinning, with what the scorer made of it."""
    rows = {}
    for frac in KEPT:
        got = []
        for whole, short in zip(pool, thin(pool, frac)):
            dist = model(short["evidences"])
            got.append({
                "record": short["evidences"],
                "margin": max(dist.values()),
                "n": len(short["evidences"]),
                "true_n": len(whole["evidences"]),
                "right": argmax(dist) == whole["pathology"],
            })
        rows[frac] = got
    return rows


def every_way(model, pool, ways):
    """The same records cut short for every reason, not just the convenient one. Fitting only
    against uniform thinning leaves the calibration four points short on a record that kept the
    standard questions and lost the follow-ups, which is the likeliest shape of all."""
    out = []
    for key in ways.values():
        for frac in KEPT:
            for case in cut(pool, frac, key):
                dist = model(case["evidences"])
                out.append({
                    "record": case["evidences"],
                    "margin": max(dist.values()),
                    "n": len(case["evidences"]),
                    "true_n": case["true_n"],
                    "right": argmax(dist) == case["pathology"],
                })
    return out


def cut_for(rows, target):
    """Lowest margin that still delivers `target` precision, and what coverage it costs.
    None when nothing reaches it, which is an answer in itself."""
    ranked = sorted(rows, key=lambda r: -r["margin"])
    best, hits = None, 0
    for i, row in enumerate(ranked, start=1):
        hits += row["right"]
        if hits / i >= target:
            best = (row["margin"], i / len(ranked))
    return best


def table(name, rows_by_level, decide, target):
    print(f"\n{name}\n")
    print(f"  {'record':>8} {'precision':>11} {'coverage':>10} {'answered':>9}")
    out = {}
    for frac in KEPT:
        rows = rows_by_level[frac]
        answered = [r["right"] for r in rows if decide(r)]
        if not answered:
            print(f"  {frac:>8.0%} {'silent':>11} {0.0:>10.1%} {0:>9}")
            out[str(frac)] = None
            continue
        precision = sum(answered) / len(answered)
        lo, hi = wilson(sum(answered), len(answered))
        # only call it a miss when the interval says so. A handful of answered cases cannot
        # break a promise, and flagging them as though they could is its own kind of dishonesty.
        flag = "  <- misses the target" if hi < target and len(answered) >= 30 else ""
        print(f"  {frac:>8.0%} {precision_text(sum(answered), len(answered)):>11} "
              f"{len(answered) / len(rows):>10.1%} {len(answered):>9}{flag}")
        out[str(frac)] = {"precision": round(precision, 4),
                          "coverage": round(len(answered) / len(rows), 4),
                          "answered": len(answered),
                          "ci": [round(lo, 4), round(hi, 4)]}
    return out


def main(path):
    schema = load_schema("ddxplus")
    model = SoftmaxScorer.load(WEIGHTS, schema)
    patients = [p for p in load_patients(path, limit=60000) if p["evidences"]]
    fit = patients[40000:40000 + SPLIT]
    test = patients[46000:46000 + SPLIT]
    print(f"{len(fit)} patients to fit on, {len(test)} to test on, none of them seen by the "
          f"scorer or by the published curve")

    F, T = gather(model, fit), gather(model, test)

    print("\nIs the confidence honest about itself?\n")
    print(f"  {'record':>8} {'top-1':>8} {'mean margin':>13} {'ECE':>7}  verdict")
    honesty = {}
    for frac in KEPT:
        rows = T[frac]
        pairs = [(r["margin"], r["right"]) for r in rows]
        acc = sum(1 for r in rows if r["right"]) / len(rows)
        mean = sum(r["margin"] for r in rows) / len(rows)
        err = ece(pairs)
        gap = mean - acc
        verdict = ("honest" if abs(gap) < 0.02 else
                   f"overconfident by {gap:+.1%}" if gap > 0 else
                   f"underconfident by {-gap:.1%}")
        honesty[str(frac)] = {"accuracy": round(acc, 4), "mean_margin": round(mean, 4),
                              "ece": round(err, 4), "reliability": reliability(pairs)}
        print(f"  {frac:>8.0%} {acc:>8.1%} {mean:>13.1%} {err:>7.3f}  {verdict}")

    print(f"\nDoes one raw threshold hold {TARGET:.0%} everywhere? "
          f"(rows: the record it was chosen on)\n")
    chosen = {frac: cut_for(F[frac], TARGET) for frac in KEPT}
    print(f"  {'chosen on':>10} " + " ".join(f"{k:>9.0%}" for k in KEPT))
    transfer = {}
    for src in KEPT:
        if not chosen[src]:
            continue
        cut, row, cells = chosen[src][0], {}, []
        for frac in KEPT:
            answered = [r["right"] for r in T[frac] if r["margin"] >= cut]
            if not answered:
                row[str(frac)] = None
                cells.append(f"{'silent':>9}")
                continue
            precision = sum(answered) / len(answered)
            row[str(frac)] = round(precision, 4)
            cells.append(f"{precision:>8.1%}" + ("!" if precision < TARGET - 0.01 else " "))
        transfer[str(src)] = row
        print(f"  {src:>10.0%} " + " ".join(cells))
    print("\n  ! is a threshold that fails the target on a record it was not chosen on.")

    # The fix. What is in hand for the calibration, because that is observable; estimated
    # completeness for the floor, because below it nothing reaches a useful precision anyway.
    # Both are fitted against records cut short for every reason, not only the convenient one.
    rates = json.loads((BAKE / "ddxplus_priors.json").read_text())["rates"]
    ways = mechanisms(schema, rates)
    print(f"\nfitting against {len(ways)} ways a record goes short, not just uniform thinning")
    mixed_fit = every_way(model, fit, ways)
    calibrator = Calibrator(rates).fit(
        [(r["margin"], r["record"], r["right"]) for r in mixed_fit]).thin()
    completeness = Completeness(model.encode).fit(
        [(r["record"], r["true_n"]) for r in mixed_fit])

    errs = [abs(completeness(r["record"]) - min(1.0, r["n"] / r["true_n"]))
            for frac in KEPT for r in T[frac]]
    print(f"\nEstimating how much of the record is missing: mean error "
          f"{sum(errs) / len(errs):.3f} on a 0-1 scale")

    plain = table(f"Calibrated, answering whenever P(right) clears {TARGET:.0%}:",
                  T, lambda r: calibrator(r["margin"], r["record"]) >= TARGET, TARGET)
    floored = table(f"And refusing outright below {FLOOR:.0%} estimated completeness:",
                    T, lambda r: completeness(r["record"]) >= FLOOR
                    and calibrator(r["margin"], r["record"]) >= TARGET, TARGET)

    every = [r for frac in KEPT for r in T[frac]]
    answered = [r["right"] for r in every
                if completeness(r["record"]) >= FLOOR
                and calibrator(r["margin"], r["record"]) >= TARGET]
    loose = sum(1 for r in every if r["right"])
    lo, hi = wilson(sum(answered), len(answered))
    mixed = {
        "precision": round(sum(answered) / len(answered), 4),
        "coverage": round(len(answered) / len(every), 4),
        "wrong": len(answered) - sum(answered),
        "cases": len(every),
        "ci": [round(lo, 4), round(hi, 4)],
        "answer_everything": {"precision": round(loose / len(every), 4),
                              "wrong": len(every) - loose},
    }
    print(f"\nA mixed stream, nobody saying how complete anything is ({len(every)} records):\n")
    print(f"  answering everything        {precision_text(loose, len(every)):>9} right, "
          f"{len(every) - loose:>5} wrong")
    print(f"  under this rule             "
          f"{precision_text(len(answered) - mixed['wrong'], len(answered)):>9} right, "
          f"{mixed['wrong']:>5} wrong, on {mixed['coverage']:.1%} of cases")

    calibrator.save(BAKE / "calibrator.json")
    completeness.save(BAKE / "completeness.npz")
    OUT.write_text(json.dumps({
        "target": TARGET, "floor": FLOOR, "fit_cases": len(fit), "test_cases": len(test),
        "honesty": honesty, "transfer": transfer,
        "completeness_error": round(sum(errs) / len(errs), 4),
        "calibrated": plain, "calibrated_with_floor": floored, "mixed_stream": mixed,
    }, indent=1))
    print(f"\nwrote {OUT}, {BAKE / 'calibrator.json'}, {BAKE / 'completeness.npz'}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/ddxplus/release_validate_patients")
