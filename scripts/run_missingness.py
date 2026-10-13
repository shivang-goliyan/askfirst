"""Everything so far hid evidence uniformly at random. Records do not go missing that way.

    python3 scripts/run_missingness.py data/ddxplus/release_validate_patients

An intake that runs out of time does not lose a random scattering of findings. It gets through
the standard questions and not the follow-ups; it has what the patient said and nothing about
their history; it knows there is pain and not where it is. Each of those removes a different
*kind* of evidence.

Same patients, same scorer, same number of findings taken away. Only which ones go changes."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from askfirst.ablation import argmax  # noqa: E402
from askfirst.calibrate import FLOOR, Calibrator, Completeness  # noqa: E402
from askfirst.ddxplus import load_patients  # noqa: E402
from askfirst.metrics import wilson  # noqa: E402
from askfirst.missing import cut, mechanisms  # noqa: E402
from askfirst.schema import load_schema  # noqa: E402
from askfirst.softmax import SoftmaxScorer  # noqa: E402
from run_abstention import KEPT, WEIGHTS  # noqa: E402

BAKE = Path("src/askfirst/baked")
OUT = Path("docs/results/missingness.json")
TARGET = 0.95
CASES = 6000
# the one left out of the fit for the transfer test, chosen because it is the likeliest shape a
# real intake takes and because it is the one that broke when nothing was done about it
HELD_OUT = "standard questions, no follow-ups"


def look(model, pool, ways, names):
    rows = []
    for name in names:
        for frac in KEPT:
            for case in cut(pool, frac, ways[name]):
                dist = model(case["evidences"])
                rows.append({
                    "record": case["evidences"], "margin": max(dist.values()),
                    "true_n": case["true_n"], "right": argmax(dist) == case["pathology"],
                    "way": name, "frac": frac,
                })
    return rows


def judge(rows, cal, done, names, title, marked=()):
    print(f"\n{title}\n")
    print(f"  {'how the record got cut short':36} " + " ".join(f"{k:>8.0%}" for k in KEPT))
    out = {}
    for name in names:
        row, cells = {}, []
        for frac in KEPT:
            here = [r for r in rows if r["way"] == name and r["frac"] == frac]
            answered = [r["right"] for r in here
                        if done(r["record"]) >= FLOOR
                        and cal(r["margin"], r["record"]) >= TARGET]
            if not answered:
                row[str(frac)] = {"answered": 0}
                cells.append(f"{'silent':>8}")
                continue
            precision = sum(answered) / len(answered)
            lo, hi = wilson(sum(answered), len(answered))
            broken = hi < TARGET and len(answered) >= 30
            row[str(frac)] = {"precision": round(precision, 4), "answered": len(answered),
                              "coverage": round(len(answered) / len(here), 4),
                              "ci": [round(lo, 4), round(hi, 4)], "broken": broken}
            cells.append(f"{precision:>7.1%}" + ("!" if broken else " "))
        out[name] = row
        print(f"  {'*' if name in marked else ' '}{name:35} " + " ".join(cells))

    tiny = [(name, frac, row[str(frac)]["answered"])
            for name, row in out.items() for frac in KEPT
            if 0 < row[str(frac)]["answered"] < 30]
    for name, frac, n in tiny:
        print(f"    (at {frac:.0%}, {name!r} answered {n} case{'s' if n != 1 else ''} — "
              f"read nothing into that cell)")
    return out


def main(path):
    schema = load_schema("ddxplus")
    model = SoftmaxScorer.load(WEIGHTS, schema)
    rates = json.loads((BAKE / "ddxplus_priors.json").read_text())["rates"]
    ways = mechanisms(schema, rates)
    names = list(ways)
    patients = [p for p in load_patients(path, limit=60000) if p["evidences"]]
    fit, test = patients[40000:40000 + CASES], patients[46000:46000 + CASES]

    print(f"{len(test)} held-out patients, {len(ways)} ways a record can be cut short, "
          f"{len(KEPT)} levels.")
    rows = look(model, test, ways, names)

    print(f"\nTop-1 answering everything, which is where 'how complete is it' stops being one "
          f"question:\n")
    print(f"  {'how the record got cut short':36} " + " ".join(f"{k:>8.0%}" for k in KEPT))
    top = {}
    for name in names:
        row, cells = {}, []
        for frac in KEPT:
            here = [r for r in rows if r["way"] == name and r["frac"] == frac]
            acc = sum(r["right"] for r in here) / len(here)
            row[str(frac)] = round(acc, 4)
            cells.append(f"{acc:>8.1%}")
        top[name] = row
        print(f"   {name:35} " + " ".join(cells))

    shipped = Calibrator.load(BAKE / "calibrator.json")
    seen = Completeness.load(BAKE / "completeness.npz", model.encode)
    kept = judge(rows, shipped, seen, names,
                 f"Does the shipped rule keep its {TARGET:.0%} promise? "
                 f"(fitted against all of these)")

    # The transfer test: refit with one pattern removed entirely and see whether the fit carries.
    partial = [n for n in names if n != HELD_OUT]
    train = look(model, fit, ways, partial)
    blind = Calibrator(rates).fit(
        [(r["margin"], r["record"], r["right"]) for r in train]).thin()
    blind_seen = Completeness(model.encode).fit([(r["record"], r["true_n"]) for r in train])
    missed = judge(rows, blind, blind_seen, names,
                   f"And if {HELD_OUT!r} had never been in the fit:", marked=(HELD_OUT,))

    print("\n  ! is a promise broken with an interval to back it. 'silent' is the floor working.")
    print(f"  * is the pattern held out of the second fit.")

    OUT.write_text(json.dumps({
        "target": TARGET, "floor": FLOOR, "cases": len(test), "held_out": HELD_OUT,
        "top1": top, "shipped": kept, "held_out_of_fit": missed,
    }, indent=1))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/ddxplus/release_validate_patients")
