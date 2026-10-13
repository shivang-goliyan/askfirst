"""Fit the gate to a scorer that is not ours.

    python3 scripts/fit_gate.py history.jsonl --scorer their-xgboost

This is the part of the product a customer runs once, on their own records, against their own
model. It exists because the precision promise does not transfer: measured, an 80% cut-off
borrowed from our softmax delivers 54.7% on an open model's own confidence
(`docs/results/2026-10-13-the-open-model-is-not-the-scorer.md`). The record-level half of the
gate — the ceiling and the completeness floor — needs none of this and works on the first call.

What it wants is one JSON object per line:

    {"record": {"E_55": true, ...}, "confidence": 0.84, "right": true, "true_findings": 14,
     "patient": "p-104"}

`confidence` is whatever your model's top probability was. `right` is whether its top answer was
the correct one. `true_findings` is how many findings that patient really had, if you know — it
is what the completeness estimator learns from, and without it that half is skipped and the
shipped estimate is kept. `patient` is optional and only affects the held-out interval: with it
the check clusters on people, which is correct whenever one person contributed several rows. A few thousand rows is enough; the measurement behind this product
fitted on 42,000 rows from 1,200 patients.

It writes `src/askfirst/baked/calibrator-<scorer>.json`, which `POST /api/gate` then picks up by
name. Nothing else changes, and your records never leave the machine this runs on.

Whether a calibration fitted this way holds is a question the fit cannot answer, so this prints
a held-out check and refuses to look pleased about it if the promise is not kept."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from askfirst.calibrate import Calibrator, Completeness  # noqa: E402
from askfirst.metrics import clustered  # noqa: E402
from askfirst.schema import load_schema  # noqa: E402
from askfirst.softmax import SoftmaxScorer  # noqa: E402

BAKE = Path("src/askfirst/baked")


def read(path):
    rows = []
    for n, line in enumerate(Path(path).read_text().splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as e:
            raise SystemExit(f"line {n} of {path} is not JSON: {e}")
        for need in ("record", "confidence", "right"):
            if need not in row:
                raise SystemExit(f"line {n} has no {need!r}. See the top of this file for the "
                                 f"shape it wants.")
        rows.append(row)
    if len(rows) < 500:
        print(f"  only {len(rows)} rows. This will fit, but a calibration off that little data "
              f"is a guess with a decimal point on it.")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("history")
    ap.add_argument("--scorer", required=True, help="the name POST /api/gate will look up")
    ap.add_argument("--domain", default="ddxplus")
    ap.add_argument("--target", type=float, default=0.95)
    ap.add_argument("--hold-out", type=float, default=0.3)
    args = ap.parse_args()

    schema = load_schema(args.domain)
    rows = read(args.history)
    rates = json.loads((BAKE / "ddxplus_priors.json").read_text())["rates"]

    # One sanitised name for both artifacts. They used to disagree: the calibration was saved
    # under the tidied name and the completeness estimator under the raw one, so a scorer called
    # "Their XGBoost" got its own calibration and silently fell back to OUR completeness.
    name = "".join(c if c.isalnum() or c in "-_" else "-" for c in args.scorer.lower())[:48]
    if name in ("", "unnamed", "unknown", "none", "null", "-"):
        raise SystemExit(f"--scorer {args.scorer!r} is not an identity. The endpoint refuses "
                         f"anonymous callers on purpose, so a fit under that name would never "
                         f"be found.")

    cut = int(len(rows) * (1 - args.hold_out))
    fit, test = rows[:cut], rows[cut:]
    print(f"{len(fit):,} rows to fit on, {len(test):,} held back\n")

    cal = Calibrator(rates).fit(
        [(r["confidence"], r["record"], bool(r["right"])) for r in fit]).thin()

    known = [r for r in fit if r.get("true_findings")]
    if len(known) >= 200:
        encode = SoftmaxScorer(schema).encode
        seen = Completeness(encode).fit([(r["record"], r["true_findings"]) for r in known])
        seen.save(BAKE / f"completeness-{name}.npz")
        print(f"  completeness estimator fitted on {len(known):,} rows with a known true size")
    else:
        seen = None
        print(f"  only {len(known)} rows carry true_findings, so the shipped completeness "
              f"estimate is kept — it reads the record, not the scorer, so that is defensible")

    out = BAKE / f"calibrator-{name}.json"

    answered = [r for r in test if cal(r["confidence"], r["record"]) >= args.target]
    print(f"\nHeld out, at a {args.target:.0%} promise:")
    if not answered:
        print("  it answers nothing. Either the target is too high for this scorer, or the "
              "confidence\n  carries less signal than it looks like it does.")
    else:
        right = sum(1 for r in answered if r["right"])
        # Cluster on whoever the row says it came from. Giving every row its own identity, which
        # this did until a reviewer pointed it out, is not a clustered interval at all — it is
        # the row-wise one wearing the word "clustered", and it is too narrow whenever the same
        # patient appears more than once.
        grouped = any("patient" in r for r in answered)
        rows_for_ci = [{"who": r.get("patient", i), "right": bool(r["right"])}
                       for i, r in enumerate(answered)]
        lo, hi = clustered(rows_for_ci, len({r["who"] for r in rows_for_ci}))
        how = ("clustered on patients" if grouped else
               "per row — add a \"patient\" key to your history and this clusters on people, "
               "which it should, because repeated views of one person are not independent")
        print(f"  answers {len(answered) / len(test):.1%} of them at {right / len(answered):.1%} "
              f"[{lo:.1%}, {hi:.1%}]  ({how})")
        if lo < args.target - 0.005:
            print(f"  THE PROMISE IS NOT KEPT. The lower bound is under {args.target:.0%}, so do "
                  f"not deploy this\n  at that target — lower it, or get more rows, and measure "
                  f"again.")
        else:
            print("  the promise holds on data this fit never saw.")

    cal.save(out)
    print(f"\nwrote {out}")
    print(f"POST /api/gate with \"scorer\": \"{name}\" will now use it.")


if __name__ == "__main__":
    main()
