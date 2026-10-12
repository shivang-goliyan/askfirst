"""Does the call change when the computational line is taken away?

    python3 -I scripts/run_variant_ablation.py data/civic/evidence.tsv

Reporting a predictor's score says nothing about whether anyone should act on it. The question
that matters is whether it is load-bearing — and the strength it is given is the thing that
decides, which is exactly what ClinGen had to recalibrate. So this sweeps the strength from
supporting (level E) up to validated (level A) and counts how many calls move."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from askfirst.civic import (  # noqa: E402
    COMPUTATIONAL,
    call_for,
    computational_line,
    contested,
    load_groups,
    weighted_verdict,
)

SCORES = Path("src/askfirst/baked/variant_scores.json")
LEVELS = [("E", "supporting — where ACMG caps it"), ("D", "case report"),
          ("C", "preclinical"), ("B", "clinical"), ("A", "validated")]


def main(path, threshold=2.0):
    scores = {v["profile"]: v["llr"] for v in json.loads(SCORES.read_text())["variants"]}
    groups = load_groups(path)
    fought = contested(groups)

    eligible = {k: v for k, v in fought.items() if k[0] in scores}
    scoreable = {k: v for k, v in eligible.items()
                 if computational_line(scores[k[0]], threshold=threshold)}

    print(f"groups with 2+ evidence items : {len(groups)}")
    print(f"  contested (own evidence disagrees): {len(fought)}")
    print(f"  of those, variant is a scoreable substitution: {len(eligible)}")
    print(f"  and the score clears |llr| >= {threshold}: {len(scoreable)}")
    print()
    print("The gap between those last two lines is the first result: a computational predictor")
    print("has no vote at all on most of what a tumour board actually argues about.")
    print()

    print(f"{'strength given to the line':34} {'calls changed':>14} {'predictor wins':>15}")
    rows = []
    for level, blurb in LEVELS:
        changed, dominated = [], []
        for key, items in scoreable.items():
            line = computational_line(scores[key[0]], level=level, threshold=threshold)
            before = call_for(items)
            after = call_for(items + [line])
            if before != after:
                changed.append((key, before, after, scores[key[0]]))
            if after in COMPUTATIONAL:
                dominated.append(key)
        rows.append({"level": level, "changed": len(changed), "dominated": len(dominated)})
        share = len(changed) / len(scoreable) if scoreable else 0
        print(f"{level} — {blurb:28} {len(changed):>4} ({share:>5.1%}) {len(dominated):>10}")
        if level == "B" and changed:
            flips = changed[:6]

    print()
    print("'Predictor wins' means the computational label itself ended up on top of the")
    print("distribution — a prediction outranking the clinical evidence in the same group.")

    if "flips" in dir():
        print("\nExamples at clinical strength (level B), which is roughly how predictors get")
        print("treated in practice:")
        for (profile, disease, therapy), before, after, llr in flips:
            print(f"  {profile:16} llr {llr:>+6.2f}  {before!r} -> {after!r}")
            print(f"      {disease[:60]}")

    out = Path("docs/results/variant-ablation.json")
    out.write_text(json.dumps({"threshold": threshold, "contested": len(fought),
                               "eligible": len(eligible), "scoreable": len(scoreable),
                               "sweep": rows}, indent=2))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/civic/evidence.tsv",
         float(sys.argv[2]) if len(sys.argv) > 2 else 2.0)
