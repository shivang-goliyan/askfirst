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
BAKED = Path("src/askfirst/baked/variants.json")
LEVELS = [("E", "supporting — where an uncalibrated predictor belongs"), ("D", "case report"),
          ("C", "preclinical"), ("B", "clinical"), ("A", "validated")]


def as_row(item):
    """One evidence item, trimmed to what a reader needs to judge it."""
    return {
        "level": item["evidence_level"],
        "direction": item["evidence_direction"],
        "significance": item["significance"] or "N/A",
        "type": item["evidence_type"],
        "rating": item["rating"],
        "source": item.get("citation") or item.get("source") or "",
        "url": item.get("evidence_civic_url", ""),
    }


def main(path, threshold=2.0, scores_path=None, bake=True):
    blob = json.loads(Path(scores_path or SCORES).read_text())
    scores = {v["profile"]: v["llr"] for v in blob["variants"]}
    print(f"scores from {blob['model']} ({blob['scored']} variants, {blob['device']})\n")
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

    # a rehearsal must not land on top of a published artifact. It did once.
    out = Path("docs/results/variant-ablation.json" if bake
               else "docs/results/rehearsal-variant-ablation.json")
    out.write_text(json.dumps({"threshold": threshold, "contested": len(fought),
                               "eligible": len(eligible), "scoreable": len(scoreable),
                               "sweep": rows}, indent=2))
    print(f"\nwrote {out}")

    # The same thing the page shows, baked, so the second domain needs no GPU and no CIViC
    # download to demonstrate. Every group that can take the line at all is in here, which is
    # eleven of them — small enough to ship whole and small enough that nobody should read a
    # percentage off it.
    cases = []
    for (profile, disease, therapy), items in sorted(scoreable.items()):
        llr = scores[profile]
        calls = {"none": call_for(items)}
        for level, _ in LEVELS:
            line = computational_line(llr, level=level, threshold=threshold)
            calls[level] = call_for(items + [line])
        cases.append({
            "profile": profile,
            "disease": disease,
            "therapy": therapy or "—",
            "llr": round(llr, 4),
            "says": computational_line(llr, threshold=threshold)["significance"],
            "evidence": [as_row(i) for i in items],
            "calls": calls,
        })

    if not bake:
        print("\n(rehearsal — nothing baked)")
        return
    meta = blob
    BAKED.write_text(json.dumps({
        "model": meta["model"],
        "threshold": threshold,
        "scored": meta["scored"],
        "counts": {"groups": len(groups), "contested": len(fought),
                   "eligible": len(eligible), "scoreable": len(scoreable)},
        "levels": [{"level": lv, "blurb": blurb,
                    "changed": r["changed"], "dominated": r["dominated"]}
                   for (lv, blurb), r in zip(LEVELS, rows)],
        "cases": cases,
    }, indent=1))
    print(f"wrote {BAKED} — {len(cases)} groups the line can speak on")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/civic/evidence.tsv",
         float(sys.argv[2]) if len(sys.argv) > 2 else 2.0,
         sys.argv[3] if len(sys.argv) > 3 else None,
         bake=len(sys.argv) <= 3)
