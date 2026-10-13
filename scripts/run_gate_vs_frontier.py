"""The refusal comparison, recomputed rather than typed by hand.

    python3 scripts/run_gate_vs_frontier.py data/ddxplus/release_validate_patients

**This is not an accuracy contest and nothing here claims we beat a frontier model at diagnosis.**
Our scorer is fitted on 30,000 labelled patients from this exact generator; the frontier model is
zero-shot with a two-line prompt. Comparing top-1 between them would be a rigged race and any
judge would say so in one sentence. The only comparison that is fair is the one this product is
about: given the same thinning record and an explicit way out, who knows to stop?

The frontier side is read off the committed rehearsal artifacts — 750 paid calls that are not
going to be made again. Our side is recomputed here, against the identical records, because the
rehearsal hardcoded a gate column that went stale the moment the scorer was refitted. A
comparison that has to be retyped when one side changes is a comparison that will be wrong.

The records are reproducible by construction: `patients[46000:46000 + cases]` from the same file,
thinned by `run_abstention.thin` at the same seed, which is what the paid run used."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from askfirst.ablation import argmax  # noqa: E402
from askfirst.calibrate import CEILING, FLOOR, Calibrator, Completeness  # noqa: E402
from askfirst.ddxplus import load_patients  # noqa: E402
from askfirst.metrics import precision_text  # noqa: E402
from askfirst.schema import load_schema  # noqa: E402
from askfirst.softmax import SoftmaxScorer  # noqa: E402
from run_abstention import WEIGHTS, thin  # noqa: E402

BAKE = Path("src/askfirst/baked")
OUT = Path("docs/results/gate-vs-frontier.json")
THEIRS = Path("docs/results/rehearsal-claude-abstention.json")
THEIRS_HIGH = Path("docs/results/rehearsal-claude-abstention-high.json")
TARGET = 0.95


def summarise(rows):
    if not rows:
        return None
    answered = [r for r in rows if not r["abstained"]]
    right = sum(1 for r in answered if r["right"])
    return {"cases": len(rows), "answered": len(answered), "right": right,
            "abstains": round(1 - len(answered) / len(rows), 4),
            "answers": round(len(answered) / len(rows), 4),
            "right_when_answering": round(right / len(answered), 4) if answered else None,
            # "100% right" is the one sentence this product must never print, and a sample with
            # no wrong answers in it is a sample rather than a promise
            "shown": precision_text(right, len(answered)) if answered else "nothing answered"}


def main(path="data/ddxplus/release_validate_patients"):
    theirs = json.loads(THEIRS.read_text())
    theirs_high = json.loads(THEIRS_HIGH.read_text()) if THEIRS_HIGH.exists() else None
    cases = theirs["cases"]
    levels = [float(x) for x in theirs["levels"]]

    schema = load_schema("ddxplus")
    model = SoftmaxScorer.load(WEIGHTS, schema)
    cal = Calibrator.load(BAKE / "calibrator.json")
    seen = Completeness.load(BAKE / "completeness.npz", model.encode)

    patients = [p for p in load_patients(path, limit=46000 + cases) if p["evidences"]]
    held = patients[46000:46000 + cases]
    print(f"{len(held)} held-out patients, the same slice the paid run used, "
          f"{len(levels)} completeness levels")
    print(f"the frontier side is {theirs['model']}, {len(theirs['rows'])} calls already paid for "
          f"(${theirs['approx_usd']:.2f}); our side is recomputed\n")

    ours = {}
    for frac in levels:
        rows = []
        for whole, short in zip(held, thin(held, frac)):
            record = short["evidences"]
            dist = model(record)
            enough = seen(record) >= FLOOR and len(record) <= CEILING
            chance = cal(max(dist.values()), record) if enough else None
            answering = bool(enough and chance is not None and chance >= TARGET)
            rows.append({"abstained": not answering,
                         "right": answering and argmax(dist) == whole["pathology"]})
        ours[str(frac)] = summarise(rows)

    frontier = {}
    for frac in levels:
        frontier[str(frac)] = summarise([r for r in theirs["rows"]
                                         if abs(float(r["kept"]) - frac) < 1e-9])

    print("Offered an explicit way out and told not to guess:\n")
    print(f"  {'record':>8} | {'frontier abstains':>17} {'right when it answers':>22} | "
          f"{'our gate abstains':>17} {'right when it answers':>22}")
    for frac in levels:
        t, o = frontier[str(frac)], ours[str(frac)]
        print(f"  {frac:>8.0%} | {t['abstains']:>17.1%} {t['shown']:>22} | "
              f"{o['abstains']:>17.1%} {o['shown']:>22}")

    high = None
    if theirs_high:
        frac = float(theirs_high["levels"][0])
        high = {"level": frac, "frontier_low": frontier[str(frac)],
                "frontier_high": summarise(theirs_high["rows"]), "ours": ours[str(frac)]}
        print(f"\nAt {frac:.0%} of a record, and what more deliberation bought:\n")
        print(f"  {'':<34} {'abstains':>10} {'answers':>9} {'right when answering':>21}")
        for name, row in (("frontier, effort low", high["frontier_low"]),
                          ("frontier, effort high", high["frontier_high"]),
                          ("this gate", high["ours"])):
            print(f"  {name:<34} {row['abstains']:>10.1%} {row['answers']:>9.1%} "
                  f"{row['shown']:>21}")

    OUT.write_text(json.dumps({
        "note": "A refusal comparison, not an accuracy contest. Our scorer is fitted on 30,000 "
                "labelled patients from this generator and the frontier model is zero-shot; "
                "comparing top-1 would be a rigged race and is not done here.",
        "target": TARGET, "cases": cases, "levels": levels,
        "frontier_model": theirs["model"], "frontier_calls": len(theirs["rows"]),
        "frontier_usd": theirs["approx_usd"],
        "frontier": frontier, "ours": ours, "at_effort_high": high,
    }, indent=1))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/ddxplus/release_validate_patients")
