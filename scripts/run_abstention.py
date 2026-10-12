"""Does refusing help?

Everything measured so far has been about the ADVICE — which field to go and get. But the louder
half of the claim is the refusal: that it keeps quiet when the record cannot support an answer.
That is a different property and it needs its own curve.

Sort cases by how confident the scorer is, answer only the most confident share, and see whether
accuracy on what you did answer climbs as you answer less. If it does not climb, the confidence
signal is worthless and so is the refusal.

    python3 -I scripts/run_abstention.py data/ddxplus/release_validate_patients 1500
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from askfirst.ablation import argmax, entropy
from askfirst.ddxplus import NaiveBayes, load_patients


def main(path, cases):
    patients = load_patients(path, limit=8000)
    scorer = NaiveBayes().fit(patients[:4000])
    held = [p for p in patients[4000:] if p["evidences"]][:cases]

    scored = []
    for patient in held:
        dist = scorer(patient["evidences"])
        scored.append({
            "right": argmax(dist) == patient["pathology"],
            "margin": max(dist.values()),
            "entropy": entropy(dist),
        })

    print(f"cases {len(scored)}   49 pathologies   chance 2.0%\n")
    print(f"{'signal':<10} {'coverage':>9} {'accuracy':>9} {'vs full':>9}")
    full = sum(s["right"] for s in scored) / len(scored)

    for name, key, reverse in (("margin", "margin", True), ("entropy", "entropy", False)):
        ranked = sorted(scored, key=lambda s: s[key], reverse=reverse)
        print(f"{name:<10} {'100%':>9} {full:>8.1%} {'-':>9}")
        for share in (0.75, 0.5, 0.25, 0.1):
            keep = ranked[: max(1, int(len(ranked) * share))]
            acc = sum(s["right"] for s in keep) / len(keep)
            print(f"{'':<10} {share:>8.0%} {acc:>8.1%} {acc - full:>+8.1%}")
        print()


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 1500)
