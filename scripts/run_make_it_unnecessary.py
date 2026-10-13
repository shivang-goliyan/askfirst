"""Try to make the gate unnecessary, and report it if we succeed.

    python3 scripts/run_make_it_unnecessary.py data/ddxplus/release_validate_patients [patients]

A reviewer asked two questions we had no answer to, and both of them are attempts to delete the
product rather than improve it:

  1. The completeness estimator is a ridge regression predicting how many findings this patient
     would have had. Does `findings in hand / average record size` do the same job? If it does,
     the learned estimator is decoration and the write-ups should say so.
  2. The scorer is fitted on complete records and then handed records with holes in them, where a
     deleted finding is represented exactly like one that was asked about and denied. Train it on
     records with holes instead and the confidence may come out honest by itself — in which case
     the calibration is fixing a problem we created.

Both are the right questions. Five arms, all at the same 95% promise, all on the same mixed
stream, all scored across seven leave-one-pattern-out folds so nothing is being graded on a
distribution it was fitted against:

  no floor at all           the calibration alone. The control.
  a bare count              refuse under n findings, n chosen on the fit split.
  constant denominator      findings in hand / mean record size, against the same floor.
  the learned ridge         what ships.
  trained for holes         the scorer refitted on thinned records, with one global threshold.
  trained for holes + gate  and with the gate on top, to see whether it is still earning its keep.

The arms share `run_conformal.py`'s scoring, folds and patient-clustered intervals, because the
first version of that comparison was rigged by refitting one side and not the other, and sharing
one implementation is how that stops being possible to do by accident."""

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from askfirst.calibrate import CEILING, FLOOR, Calibrator, Completeness  # noqa: E402
from askfirst.ddxplus import load_patients  # noqa: E402
from askfirst.missing import cut, mechanisms  # noqa: E402
from askfirst.schema import load_schema  # noqa: E402
from askfirst.softmax import SoftmaxScorer  # noqa: E402
from run_conformal import TARGET, score, show, stream, threshold  # noqa: E402

OUT = Path("docs/results/make-it-unnecessary.json")
BAKE = Path("src/askfirst/baked")
WEIGHTS = BAKE / "ddxplus_softmax.npz"
KEPT = (1.0, 0.6, 0.4, 0.2, 0.1)
TRAIN = 30000
FIT_AT = 40000
TEST_AT = 46000


def calibrated(fit, rates):
    return Calibrator(rates).fit(
        [(r["margin"], r["record"], r["right"]) for r in fit]).thin()


def smallest_count_that_holds(fit, cal, target):
    """The count floor an engineer would pick: the smallest n that still delivers the target on
    the fit split, which is also the one that keeps the most rows.

    On this stream it picks n=0, because the calibration alone already clears the target — so
    the arm says nothing on its own and `count_matching` below is the one that does the work."""
    for n in range(0, 40):
        kept = [r for r in fit
                if len(r["record"]) >= n and cal(r["margin"], r["record"]) >= target]
        if len(kept) < 30:
            continue
        if sum(1 for r in kept if r["right"]) / len(kept) >= target:
            return n
    return None


def count_matching(fit, cal, ridge, target):
    """The count floor that gives up the SAME coverage the learned ridge does.

    This is the arm that can embarrass the ridge. If throwing away the same number of records
    by counting them is as precise as throwing them away by estimating how complete they are,
    the regression is decoration and the write-up has to say so."""
    want = sum(1 for r in fit
               if cal(r["margin"], r["record"]) >= target and ridge(r["record"]) >= FLOOR)
    best, gap = None, None
    for n in range(0, 40):
        kept = sum(1 for r in fit
                   if cal(r["margin"], r["record"]) >= target and len(r["record"]) >= n)
        if gap is None or abs(kept - want) < gap:
            best, gap = n, abs(kept - want)
    return best


def arms_on(fit, test, patients, rates, encode):
    """Fit every arm on `fit`, score every arm on `test`. Nothing is loaded off disk."""
    cal = calibrated(fit, rates)
    ridge = Completeness(encode).fit([(r["record"], r["true_n"]) for r in fit])
    mean_size = sum(r["true_n"] for r in fit) / len(fit)
    count = smallest_count_that_holds(fit, cal, TARGET)
    matched_count = count_matching(fit, cal, ridge, TARGET)

    def passes(r):
        return cal(r["margin"], r["record"]) >= TARGET and len(r["record"]) <= CEILING

    rows = [
        score("no floor at all", [r for r in test if passes(r)], len(test), patients),
        score(f"a bare count, n={count}" if count is not None else "a bare count, none holds",
              [] if count is None else
              [r for r in test if passes(r) and len(r["record"]) >= count],
              len(test), patients),
        score("constant denominator",
              [r for r in test if passes(r)
               and min(1.0, len(r["record"]) / mean_size) >= FLOOR],
              len(test), patients),
        score(f"a count giving up the same coverage, n={matched_count}",
              [r for r in test if passes(r) and len(r["record"]) >= matched_count],
              len(test), patients),
        score("the learned ridge",
              [r for r in test if passes(r) and ridge(r["record"]) >= FLOOR],
              len(test), patients),
    ]
    return rows, {"count": count, "matched_count": matched_count,
                  "mean_record_size": round(mean_size, 2)}


def thin_randomly(patients, ways, seed=5):
    """One masked copy of each patient, at a random level and for a random reason.

    One copy rather than all thirty-five, so the augmented training set is twice the size of the
    original instead of thirty-six times it — which matters on a box with three spare gigabytes,
    and is the usual shape of masking augmentation anyway."""
    rng = random.Random(seed)
    keys = list(ways.values())
    out = []
    for i, patient in enumerate(patients):
        frac = rng.choice([f for f in KEPT if f < 1.0])
        key = keys[rng.randrange(len(keys))]
        out.append(cut([patient], frac, key, seed=seed + i)[0])
    return [{"evidences": r["evidences"], "pathology": r["pathology"]} for r in out]


def main(path, cases=1200):
    schema = load_schema("ddxplus")
    rates = json.loads((BAKE / "ddxplus_priors.json").read_text())["rates"]
    ways = mechanisms(schema, rates)
    patients = [p for p in load_patients(path, limit=TEST_AT + cases) if p["evidences"]]
    train = patients[:TRAIN]
    fit_pool = patients[FIT_AT:FIT_AT + cases]
    test_pool = patients[TEST_AT:TEST_AT + cases]
    shipped = SoftmaxScorer.load(WEIGHTS, schema)

    print(f"{len(train):,} training patients, {cases:,} to fit the rules on, {cases:,} to "
          f"measure on, target {TARGET:.0%}\n")

    label = "the shipped scorer, trained on complete records only"
    fit = stream(shipped, fit_pool, ways, rates)
    test = stream(shipped, test_pool, ways, rates)
    print(f"{'=' * 88}\n{label}\n{'=' * 88}")
    plain, knobs = arms_on(fit, test, len(test_pool), rates, shipped.encode)
    shipped_loose = sum(1 for r in test if r["right"]) / len(test)
    print(f"  answering everything with it: {shipped_loose:.1%} right")
    print(f"  the count floor it picked: {knobs['count']}; mean record size "
          f"{knobs['mean_record_size']}\n")
    show(plain)

    print(f"\n  across {len(ways)} leave-one-pattern-out folds:\n")
    folds = {}
    for held in ways:
        rows, _ = arms_on([r for r in fit if r["way"] != held],
                          [r for r in test if r["way"] == held],
                          len(test_pool), rates, shipped.encode)
        folds[held] = rows
    report = {label: {"answer_everything": round(shipped_loose, 4),
                      "in_distribution": plain, "knobs": knobs, "folds": folds}}
    summarise(folds, ways)
    del fit, test

    # And the arm that tries to delete the whole thing: a scorer that has seen holes.
    #
    # Two of them, because the obvious version is confounded. Training on the complete records
    # PLUS a cut copy of each doubles the rows, so a gain could be the extra data rather than the
    # holes. The control uses half of each and lands on exactly the row count the shipped scorer
    # saw, which is the comparison that attributes the gain to one thing or the other.
    cut_copies = thin_randomly(train, ways)
    sets = (
        ("trained for holes", train + cut_copies),
        ("trained for holes, same row count as shipped",
         train[:len(train) // 2] + cut_copies[len(train) // 2:]),
    )
    for label, rows_in in sets:
        print(f"\n{'=' * 88}\n{label} — {len(rows_in):,} rows\n{'=' * 88}")
        print(f"  refitting. This takes a few minutes.")
        augmented = SoftmaxScorer(schema, seed=29).fit(rows_in, epochs=400, lr=0.05)

        fit = stream(augmented, fit_pool, ways, rates)
        test = stream(augmented, test_pool, ways, rates)
        loose = sum(1 for r in test if r["right"])
        print(f"\n  answering everything with it: {loose / len(test):.1%} right, against "
              f"{shipped_loose:.1%} for the shipped scorer on the same stream\n")

        cal = calibrated(fit, rates)
        ridge = Completeness(augmented.encode).fit([(r["record"], r["true_n"]) for r in fit])
        one = threshold(fit, TARGET)
        trained = [
            score("one global threshold on it",
                  [r for r in test if one is not None and r["margin"] >= one],
                  len(test), len(test_pool)),
            score("plus the gate",
                  [r for r in test
                   if cal(r["margin"], r["record"]) >= TARGET and len(r["record"]) <= CEILING
                   and ridge(r["record"]) >= FLOOR],
                  len(test), len(test_pool)),
        ]
        show(trained)

        print(f"\n  across {len(ways)} folds:\n")
        folds = {}
        for held in ways:
            f2 = [r for r in fit if r["way"] != held]
            t2 = [r for r in test if r["way"] == held]
            c2 = calibrated(f2, rates)
            r2 = Completeness(augmented.encode).fit([(r["record"], r["true_n"]) for r in f2])
            o2 = threshold(f2, TARGET)
            folds[held] = [
                score("one global threshold on it",
                      [r for r in t2 if o2 is not None and r["margin"] >= o2],
                      len(t2), len(test_pool)),
                score("plus the gate",
                      [r for r in t2 if c2(r["margin"], r["record"]) >= TARGET
                       and len(r["record"]) <= CEILING and r2(r["record"]) >= FLOOR],
                      len(t2), len(test_pool)),
            ]
        summarise(folds, ways)
        report[label] = {"training_rows": len(rows_in),
                         "answer_everything": round(loose / len(test), 4),
                         "in_distribution": trained, "folds": folds}
        del fit, test, augmented

    OUT.write_text(json.dumps({
        "target": TARGET, "floor": FLOOR, "patients_each_split": cases,
        "train_patients": len(train),
        "ci_kind": "bootstrap over patients, 400 draws", "arms": report,
    }, indent=1))
    print(f"\nwrote {OUT}")


def summarise(folds, ways):
    names = [r["rule"] for r in folds[next(iter(folds))]]
    print(f"  {'arm':44} {'folds kept':>11} {'worst':>8} {'mean coverage':>14}")
    for i, name in enumerate(names):
        live = [folds[h][i] for h in ways if folds[h][i]["precision"] is not None]
        if not live:
            print(f"  {name:44} {'silent':>11}")
            continue
        kept = sum(1 for r in live if r["keeps_promise"])
        worst = min(r["precision"] for r in live)
        cov = sum(r["coverage"] for r in live) / len(live)
        print(f"  {name:44} {f'{kept}/{len(live)}':>11} {worst:>8.1%} {cov:>14.1%}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/ddxplus/release_validate_patients",
         int(sys.argv[2]) if len(sys.argv) > 2 else 1200)
