"""The gate on a real emergency department queue.

    python3 scripts/run_nhamcs.py data/nhamcs-raw

Everything else in this repo is DDXPlus: synthetic patients, with evidence hidden according to
patterns we chose. This is 72,004 real visits from the CDC's ED survey, where a vital is missing
because nobody charted it. Fit on 2018-2019, tested on 2021-2022, which is a case-mix *and* a
charting shift we did not choose — fully-charted visits fall from 45.0% to 37.7% across it.

**The bar was set before this ran**, in `docs/results/2026-10-13-preregistered-real-queue.md`,
with four conditions for a win and four named losses, and the rule that none of them may excuse
another. Two results in this repo have already collapsed when they were made reproducible and
both times the tell was that the number agreed with us, so this time the conditions are quoted
back in the output and marked met or not met without editorial.

The decision is escalation, not diagnosis: from the triage form alone, does this visit need a
bed? Nothing from the visit itself is a feature — no labs, no imaging, no length of stay.

Intervals resample **hospitals**, not visits. Missingness here is site-driven and `HOSPCODE`
identifies the site, so resampling visits would understate the uncertainty badly."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from askfirst.ablation import argmax  # noqa: E402
from askfirst.calibrate import FLOOR, Calibrator, Completeness  # noqa: E402
from askfirst.metrics import clustered  # noqa: E402
from askfirst.nhamcs import (  # noqa: E402
    CORE, completeness, find, read_year, reason_vocabulary, vitals_charted,
)
from askfirst.nhamcs import schema_for  # noqa: E402
from askfirst.softmax import SoftmaxScorer  # noqa: E402

OUT = Path("docs/results/nhamcs.json")
TARGET = 0.95
FIT_YEARS = ("2018", "2019")
TEST_YEARS = ("2021", "2022")
SPARSE = 3          # three or fewer of six vitals charted
ESCALATED = "escalated"


def rows_for(scorer, records):
    out = []
    for r in records:
        dist = scorer(r["evidences"])
        out.append({
            "record": r["evidences"],
            "margin": max(dist.values()),
            "said": argmax(dist),
            "truth": r["pathology"],
            "right": argmax(dist) == r["pathology"],
            "who": r["hospital"],
            "vitals": vitals_charted(r["evidences"]),
            "complete": completeness(r["evidences"]),
            "year": r["year"],
        })
    return out


def escalation_side(rows, accepted):
    """Of the accepted cases we called an escalation, how many were — and of all the escalations
    there were, how many did we flag.

    Reported separately because discharge is the large majority class and a headline that works
    only because most people go home is not a headline."""
    flagged = [r for r in accepted if r["said"] == ESCALATED]
    truly = [r for r in rows if r["truth"] == ESCALATED]
    if not flagged:
        return {"flagged": 0, "precision": None, "coverage": 0.0, "ci": None,
                "escalations": len(truly)}
    hits = sum(1 for r in flagged if r["truth"] == ESCALATED)
    lo, hi = clustered(
        [{"who": r["who"], "right": r["truth"] == ESCALATED} for r in flagged],
        len({r["who"] for r in flagged}))
    return {"flagged": len(flagged), "precision": round(hits / len(flagged), 4),
            "coverage": round(hits / max(1, len(truly)), 4),
            "ci": [round(lo, 4), round(hi, 4)] if lo is not None else None,
            "escalations": len(truly)}


def auc_for(scored):
    """Rank-based AUC with ties averaged. Here to answer one question: when the escalation side
    fails, is it the gate or is it the data?"""
    order = sorted(range(len(scored)), key=lambda i: scored[i][0])
    ranks, i = {}, 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and scored[order[j + 1]][0] == scored[order[i]][0]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    pos = sum(1 for _, y in scored if y)
    neg = len(scored) - pos
    if not pos or not neg:
        return None
    hits = sum(ranks[i] for i, (_, y) in enumerate(scored) if y)
    return (hits - pos * (pos + 1) / 2) / (pos * neg)


def frontier(scored):
    """The best precision reachable on the escalation side at each level of recall, by ANY
    threshold on P(escalated). This is the ceiling the data imposes, and it is the thing that
    says whether a pre-registered bar was ambitious or impossible."""
    ranked = sorted(scored, key=lambda t: -t[0])
    pos = sum(1 for _, y in scored if y)
    out, hits = [], 0
    for n, (_, y) in enumerate(ranked, start=1):
        hits += bool(y)
        if n in (10, 25, 50, 100, 250, 500, 1000, 2000, 4000, 8000):
            out.append({"flagged": n, "precision": round(hits / n, 4),
                        "recall": round(hits / pos, 4)})
    return out


def side(rows, accepted, label):
    pick = [r for r in accepted if r["said"] == label]
    if not pick:
        return {"answered": 0, "precision": None, "ci": None}
    hits = sum(1 for r in pick if r["truth"] == label)
    lo, hi = clustered([{"who": r["who"], "right": r["truth"] == label} for r in pick],
                       len({r["who"] for r in pick}))
    return {"answered": len(pick), "precision": round(hits / len(pick), 4),
            "ci": [round(lo, 4), round(hi, 4)] if lo is not None else None}


def main(root="data/nhamcs-raw"):
    years = {y: (a, l) for y, a, l in find(root)}
    for y in FIT_YEARS + TEST_YEARS:
        if y not in years:
            raise SystemExit(f"No {y} in {root}. scripts/fetch_data.sh says where to get it.")

    # 300 rather than 60. The pre-registration said in advance that binning away resolution was
    # the likeliest reason the escalation side would fail, and it was: the first run kept 60
    # reason codes and five bands per vital. The bands are finer now and every reason code also
    # contributes its three-digit group, so a rare complaint no longer collapses into "other".
    vocab = reason_vocabulary([years[y][0] for y in FIT_YEARS],
                              [years[y][1] for y in FIT_YEARS], keep=300)
    print(f"reason-for-visit vocabulary: {len(vocab)} codes, counted on {', '.join(FIT_YEARS)} "
          f"only\n")

    fit = [r for y in FIT_YEARS for r in read_year(*years[y], reasons=vocab)]
    test = [r for y in TEST_YEARS for r in read_year(*years[y], reasons=vocab)]
    print(f"{len(fit):,} visits to fit on ({', '.join(FIT_YEARS)}), {len(test):,} to measure on "
          f"({', '.join(TEST_YEARS)})")
    print(f"{len({r['hospital'] for r in fit})} sites in the fit years, "
          f"{len({r['hospital'] for r in test})} in the test years, none shared")
    for name, pool in (("fit", fit), ("test", test)):
        esc = sum(1 for r in pool if r["pathology"] == ESCALATED)
        full = sum(1 for r in pool if completeness(r["evidences"]) == 1.0)
        thin = sum(1 for r in pool if vitals_charted(r["evidences"]) <= SPARSE)
        print(f"  {name:>4}: {esc / len(pool):>5.1%} escalated, {full / len(pool):>5.1%} fully "
              f"charted, {thin / len(pool):>5.1%} with {SPARSE} or fewer of six vitals")

    schema = schema_for(fit)
    scorer = SoftmaxScorer(schema).fit(fit, epochs=300, lr=0.05)
    print(f"\nscorer fitted on the triage form alone: {scorer.width} features, "
          f"{len(schema.fields)} fields")

    F, T = rows_for(scorer, fit), rows_for(scorer, test)
    loose = sum(1 for r in T if r["right"]) / len(T)
    base = sum(1 for r in T if r["truth"] != ESCALATED) / len(T)
    print(f"answering everything: {loose:.1%} right, against {base:.1%} for always saying "
          f"'went home'")

    rates = {name: schema.fields[name].asked_rate for name in schema.fields}
    cal = Calibrator(rates).fit(
        [(r["margin"], r["record"], r["right"]) for r in F]).thin()
    # observed, because the triage form is the same for everyone; and the ridge too, so the
    # pre-registered question about whether it adds anything here gets an answer either way
    ridge = Completeness(scorer.encode).fit(
        [(r["record"], len(CORE)) for r in F])

    def accept(rows, floor=True, use_cal=True, cut=None):
        out = []
        for r in rows:
            if floor and r["complete"] < FLOOR:
                continue
            score = cal(r["margin"], r["record"]) if use_cal else r["margin"]
            if score >= (TARGET if cut is None else cut):
                out.append(r)
        return out

    accepted = accept(T)
    esc = escalation_side(T, accepted)
    dis = side(T, accepted, "discharged")

    # How well the scorer separates at all, so a failure on the escalation side can be
    # attributed to the gate or to the task rather than guessed at.
    binary = [(scorer(r["evidences"])[ESCALATED], r["pathology"] == ESCALATED) for r in test]
    auc = auc_for(binary)
    ceiling = frontier(binary)

    # And the number that matters most to anyone who would deploy this: of the visits the gate
    # cleared to go home, how many actually needed a bed.
    cleared = [r for r in accepted if r["said"] == "discharged"]
    missed = [r for r in cleared if r["truth"] == ESCALATED]
    all_esc = sum(1 for r in T if r["truth"] == ESCALATED)
    print(f"\n{'=' * 84}\nThe gate on 2021-2022, fitted on 2018-2019\n{'=' * 84}")
    print(f"  accepted {len(accepted):,} of {len(T):,} visits ({len(accepted) / len(T):.1%})\n")
    print(f"  {'side':>12} {'answered':>9} {'precision':>11} {'clustered on sites':>21} "
          f"{'of all escalations':>19}")
    print(f"  {'escalation':>12} {esc['flagged']:>9,} "
          f"{(f'{esc['precision']:.1%}' if esc['precision'] is not None else '—'):>11} "
          f"{(f'[{esc['ci'][0]:.1%}, {esc['ci'][1]:.1%}]' if esc['ci'] else '—'):>21} "
          f"{esc['coverage']:>19.1%}")
    print(f"  {'discharge':>12} {dis['answered']:>9,} "
          f"{(f'{dis['precision']:.1%}' if dis['precision'] is not None else '—'):>11} "
          f"{(f'[{dis['ci'][0]:.1%}, {dis['ci'][1]:.1%}]' if dis['ci'] else '—'):>21}")

    print(f"\n  AUC for escalation from the triage form alone: {auc:.4f}")
    print(f"  the ceiling the data imposes, by ANY threshold on P(escalated):\n")
    print(f"  {'flagged':>9} {'precision':>10} {'recall':>8}")
    for row in ceiling[:7]:
        print(f"  {row['flagged']:>9,} {row['precision']:>10.1%} {row['recall']:>8.1%}")
    print(f"\n  AND THE COST: of the {len(cleared):,} visits this gate cleared to go home, "
          f"{len(missed):,} needed a bed.")
    print(f"  That is {len(missed) / max(1, len(cleared)):.1%} of the cleared visits and "
          f"{len(missed) / max(1, all_esc):.1%} of every escalation in the test years.")

    # pre-registered condition 2: ordering, isolated inside the same eligibility
    eligible = [r for r in T if r["complete"] >= FLOOR]
    thin_eligible = [r for r in eligible if r["vitals"] <= SPARSE]
    ordering = {}
    for name, pool in (("everything", eligible), ("sparse charts", thin_eligible)):
        want = len([r for r in accept(pool)])
        if not want:
            ordering[name] = None
            continue
        by_cal = sorted(pool, key=lambda r: -cal(r["margin"], r["record"]))[:want]
        by_raw = sorted(pool, key=lambda r: -r["margin"])[:want]
        rows = {}
        for how, picked in (("calibration", by_cal), ("raw margin", by_raw)):
            hits = sum(1 for r in picked if r["right"])
            lo, hi = clustered([{"who": r["who"], "right": r["right"]} for r in picked],
                               len({r["who"] for r in picked}))
            rows[how] = {"precision": round(hits / len(picked), 4), "n": len(picked),
                         "ci": [round(lo, 4), round(hi, 4)] if lo is not None else None}
        rows["ordering_gain"] = round(rows["calibration"]["precision"]
                                      - rows["raw margin"]["precision"], 4)
        ordering[name] = rows

    print(f"\n  ordering, isolated — same eligible pool, same size, only the sort key differs:\n")
    print(f"  {'pool':>14} {'n':>7} {'by calibration':>15} {'by raw margin':>14} {'gain':>8}")
    for name, rows in ordering.items():
        if not rows:
            print(f"  {name:>14} {'—':>7}")
            continue
        print(f"  {name:>14} {rows['calibration']['n']:>7,} "
              f"{rows['calibration']['precision']:>15.2%} "
              f"{rows['raw margin']['precision']:>14.2%} "
              f"{rows['ordering_gain'] * 100:>+7.2f}")

    # pre-registered conditions 3 and 4: does the gate refuse thin charts, and are they harder
    strata = {}
    for name, pick in (("3 or fewer of six vitals", lambda r: r["vitals"] <= SPARSE),
                       ("all six charted", lambda r: r["vitals"] == 6)):
        pool = [r for r in T if pick(r)]
        taken = [r for r in accepted if pick(r)]
        hits = sum(1 for r in pool if r["right"])
        strata[name] = {
            "visits": len(pool),
            "refused": round(1 - len(taken) / len(pool), 4) if pool else None,
            "answer_everything_precision": round(hits / len(pool), 4) if pool else None,
        }
    print(f"\n  {'stratum':>26} {'visits':>8} {'the gate refuses':>17} "
          f"{'answering everything':>21}")
    for name, row in strata.items():
        print(f"  {name:>26} {row['visits']:>8,} {row['refused']:>17.1%} "
              f"{row['answer_everything_precision']:>21.1%}")

    # and the question the pre-registration said to answer either way
    err = sum(abs(ridge(r["record"]) - r["complete"]) for r in T) / len(T)
    print(f"\n  the completeness ridge, which has nothing to estimate here because the form is "
          f"fixed:\n  mean absolute error {err:.4f} against the observed fraction. The floor uses "
          f"the observed one.")

    thin = strata["3 or fewer of six vitals"]
    full = strata["all six charted"]
    verdict = {
        "1. promise holds under real shift": bool(
            esc["precision"] is not None and esc["precision"] >= TARGET
            and esc["ci"] and esc["ci"][0] >= 0.93 and esc["coverage"] >= 0.10),
        "2. calibration buys >=1 point of ordering on sparse charts": bool(
            ordering.get("sparse charts")
            and ordering["sparse charts"]["ordering_gain"] >= 0.01),
        "3. refuses sparse charts at >=2x the rate": bool(
            thin["refused"] is not None and full["refused"] is not None
            and full["refused"] > 0 and thin["refused"] >= 2 * full["refused"]),
        "4. sparse charts are genuinely harder": bool(
            thin["answer_everything_precision"] < full["answer_everything_precision"]),
    }
    print(f"\n{'=' * 84}\nAgainst the bar set before this ran\n{'=' * 84}\n")
    for name, met in verdict.items():
        print(f"  {'MET    ' if met else 'NOT MET'}  {name}")
    print(f"\n  {sum(verdict.values())} of 4. A win needed all four.")

    OUT.write_text(json.dumps({
        "target": TARGET, "fit_years": list(FIT_YEARS), "test_years": list(TEST_YEARS),
        "fit_visits": len(fit), "test_visits": len(test),
        "fit_sites": len({r["hospital"] for r in fit}),
        "test_sites": len({r["hospital"] for r in test}),
        "reason_vocabulary": len(vocab), "features": scorer.width,
        "answer_everything": round(loose, 4), "always_discharge": round(base, 4),
        "accepted": len(accepted), "coverage": round(len(accepted) / len(T), 4),
        "escalation_side": esc, "discharge_side": dis,
        "auc": round(auc, 4) if auc is not None else None,
        "data_ceiling": ceiling,
        "cleared_to_go_home": len(cleared),
        "missed_escalations": len(missed),
        "missed_share_of_cleared": round(len(missed) / max(1, len(cleared)), 4),
        "missed_share_of_all_escalations": round(len(missed) / max(1, all_esc), 4),
        "ordering": ordering, "strata": strata,
        "ridge_error_against_observed": round(err, 4),
        "preregistered": verdict, "conditions_met": sum(verdict.values()),
        "ci_kind": "bootstrap over hospitals (HOSPCODE paired with year), 400 draws",
    }, indent=1))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/nhamcs-raw")
