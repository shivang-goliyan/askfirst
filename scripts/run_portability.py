"""Is this a layer, or is it just our model?

    python3 scripts/run_portability.py data/ddxplus/release_validate_patients [patients]

The hostile question this repo has to answer is one sentence long: *any team can add a confidence
threshold in an afternoon.* And the second one is worse: *your gate is fitted to your own scorer,
so it is a model, not a layer.* The second is a fair reading of the code — `rule_for()` in
`api.py` returns nothing for a scorer it cannot encode for, and the API then says so. This script
is the measurement that decides whether that is a limitation of the idea or of the plumbing.

Three scorers, chosen because their confidence is wrong in three different directions:

  logistic regression   the shipped one. Underconfident as the record thins: a linear model's
                        logits shrink as features drop out.
  naive Bayes           overconfident. It multiplies dependent findings as though they were
                        independent, so agreement compounds.
  nearest-neighbour     saturated. On a thin record a handful of neighbours agree unanimously and
                        it returns 1.00 with nothing behind it.

All three see identical features — the neighbour scorer borrows the softmax's encoder on purpose
— so only the inductive bias differs. Every rule is refitted per scorer and per fold against
whatever that fold's fit split contains; nothing is loaded off disk.

The rules, the folds and the intervals are `run_conformal.py`'s, imported rather than
reimplemented, so the two experiments cannot drift apart. That matters here: the first version of
the conformal comparison was rigged by refitting the baselines and not ourselves, and sharing one
implementation is how that stops being possible to do twice."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from askfirst.ddxplus import NaiveBayes, load_patients  # noqa: E402
from askfirst.missing import mechanisms  # noqa: E402
from askfirst.neighbours import NeighbourScorer  # noqa: E402
from askfirst.schema import load_schema  # noqa: E402
from askfirst.softmax import SoftmaxScorer  # noqa: E402
from run_conformal import TARGET, rules_on, show, stream  # noqa: E402

OUT = Path("docs/results/portability.json")
BAKE = Path("src/askfirst/baked")
WEIGHTS = BAKE / "ddxplus_softmax.npz"
TRAIN = 30000           # what the shipped scorer was fitted on, so the others get the same
FIT_AT = 40000
TEST_AT = 46000
NEIGHBOURS = 12000      # strided index; a full one triples the query cost and moves nothing
SATURATED = 0.999
OURS = "ours: isotonic in-group + the floor"
RIVALS = ("one global threshold", "a threshold per group (Mondrian partition)",
          "a threshold per group + the same floor")


def saturation(rows):
    """Inside the pile where confidence is pinned at 1.00, does the record still carry
    information the number has thrown away? If it does, a threshold cannot reach it: to a
    threshold every row in that pile is identical, and they are not."""
    pile = [r for r in rows if r["margin"] >= SATURATED]
    out = {"share": round(len(pile) / len(rows), 4), "thin": None, "full": None, "gap": None}
    thin = [r for r in pile if len(r["record"]) <= 4]
    full = [r for r in pile if len(r["record"]) >= 12]
    if len(thin) >= 30:
        out["thin"] = {"rows": len(thin),
                       "accuracy": round(sum(r["right"] for r in thin) / len(thin), 4)}
    if len(full) >= 30:
        out["full"] = {"rows": len(full),
                       "accuracy": round(sum(r["right"] for r in full) / len(full), 4)}
    if out["thin"] and out["full"]:
        out["gap"] = round(out["full"]["accuracy"] - out["thin"]["accuracy"], 4)
    return out


def assess(label, note, scorer, fit_pool, test_pool, ways, rates, encode):
    print(f"\n{'=' * 92}\n{label} — {note}\n{'=' * 92}")
    fit = stream(scorer, fit_pool, ways, rates)
    test = stream(scorer, test_pool, ways, rates)
    loose = sum(1 for r in test if r["right"])
    print(f"  {len(fit):,} fit rows, {len(test):,} test rows. Answering everything: "
          f"{loose / len(test):.1%} right, {len(test) - loose:,} wrong\n")

    plain, matched = rules_on(fit, test, len(test_pool), rates, encode)
    show(plain)
    if matched:
        print()
        show(matched)

    print(f"\n  under shift, {len(ways)} leave-one-pattern-out folds:\n")
    folds = {}
    for held in ways:
        rows, extra = rules_on([r for r in fit if r["way"] != held],
                               [r for r in test if r["way"] == held],
                               len(test_pool), rates, encode)
        folds[held] = {"rules": rows, "at_matched_coverage": extra}
        kept = {r["rule"]: r for r in rows}
        marks = []
        for name in RIVALS + (OURS,):
            r = kept.get(name)
            marks.append("—" if not r or r["precision"] is None
                         else ("kept" if r["keeps_promise"] else "BROKE"))
        print(f"    {held:<42} " + "  ".join(f"{m:>5}" for m in marks))
    print(f"    {'':<42} " + "  ".join(f"{n.split()[0][:5]:>5}" for n in RIVALS + (OURS,)))

    sat = saturation(test)
    if sat["gap"] is not None:
        print(f"\n  confidence pinned at 1.00 on {sat['share']:.1%} of rows. Inside that pile: "
              f"{sat['thin']['accuracy']:.1%} right on <=4 findings ({sat['thin']['rows']:,} "
              f"rows)\n  against {sat['full']['accuracy']:.1%} on >=12 ({sat['full']['rows']:,}) "
              f"— a {sat['gap'] * 100:.1f} point gap one number cannot see.")
    elif sat["share"] >= 0.01:
        print(f"\n  confidence pinned at 1.00 on {sat['share']:.1%} of rows")

    out = {"scorer": label, "note": note, "test_rows": len(test),
           "answer_everything": round(loose / len(test), 4),
           "in_distribution": plain, "at_matched_coverage": matched,
           "leave_one_pattern_out": folds, "saturation": sat}
    del fit, test
    return out


def main(path, cases=1200):
    schema = load_schema("ddxplus")
    rates = json.loads((BAKE / "ddxplus_priors.json").read_text())["rates"]
    ways = mechanisms(schema, rates)
    patients = [p for p in load_patients(path, limit=TEST_AT + cases) if p["evidences"]]
    train, fit_pool = patients[:TRAIN], patients[FIT_AT:FIT_AT + cases]
    test_pool = patients[TEST_AT:TEST_AT + cases]
    print(f"{len(train):,} patients to fit the scorers on, {len(fit_pool):,} for the rules, "
          f"{len(test_pool):,} to measure on — three disjoint slices, target {TARGET:.0%}")

    softmax = SoftmaxScorer.load(WEIGHTS, schema)
    step = max(1, len(train) // NEIGHBOURS)
    index = train[::step][:NEIGHBOURS]
    scorers = [
        ("logistic regression", "the shipped scorer, underconfident as the record thins",
         softmax),
        ("naive Bayes", "overconfident, because it multiplies dependent findings",
         NaiveBayes().fit(train)),
        ("nearest-neighbour vote", f"saturated; {len(index):,}-patient index",
         NeighbourScorer(softmax.encode, softmax.outcomes).fit(index)),
    ]

    report = [assess(name, note, s, fit_pool, test_pool, ways, rates, softmax.encode)
              for name, note, s in scorers]

    print(f"\n{'=' * 92}\nDoes the layer transfer? Fold-cells kept, out of "
          f"{len(report)} scorers x {len(ways)} folds\n{'=' * 92}\n")
    print(f"  {'rule':44} {'cells kept':>11} {'worst cell':>11} {'mean coverage':>14}")
    tally = {}
    for name in RIVALS + (OURS,):
        cells = [next((r for r in report[i]["leave_one_pattern_out"][h]["rules"]
                       if r["rule"] == name), None)
                 for i in range(len(report)) for h in ways]
        live = [c for c in cells if c and c["precision"] is not None]
        if not live:
            continue
        kept = sum(1 for c in live if c["keeps_promise"])
        worst = min(c["precision"] for c in live)
        cov = sum(c["coverage"] for c in live) / len(live)
        tally[name] = {"cells_kept": kept, "cells": len(live),
                       "worst_precision": round(worst, 4), "mean_coverage": round(cov, 4)}
        print(f"  {name:44} {f'{kept}/{len(live)}':>11} {worst:>11.1%} {cov:>14.1%}")

    print("\n  Every rule above is refitted per scorer and per fold. The question is not which is")
    print("  more accurate — it is which one can be handed a scorer it has never seen and still")
    print("  keep the promise it made.\n")

    OUT.write_text(json.dumps({
        "target": TARGET, "patients_each_split": cases, "scorer_train_patients": len(train),
        "ways": len(ways), "neighbour_index": len(index),
        "ci_kind": "bootstrap over patients, 400 draws",
        "scorers": report, "across_scorers_and_folds": tally,
    }, indent=1))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/ddxplus/release_validate_patients",
         int(sys.argv[2]) if len(sys.argv) > 2 else 1200)
