"""Does following the tool's advice actually improve the decision?

Recovery asks "can it name the field we deleted". That rewards guessing what a patient probably
had. The product claims something different: that the field it points at is worth going to get.
So measure that directly — hide a field, let the engine nominate what to ask for, reveal the
real answer, and see whether the decision got better than if you had asked something at random.

    python3 -I scripts/run_decision_value.py data/ddxplus/release_validate_patients 300
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from askfirst.ablation import argmax, rank_gaps
from askfirst.ddxplus import NaiveBayes, load_patients
from askfirst.schema import fit_priors, load_schema


def wilson(hits, n, z=1.96):
    if not n:
        return 0.0, 0.0
    p = hits / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return max(0.0, c - h), min(1.0, c + h)


def main(path, cases):
    random.seed(11)
    patients = load_patients(path, limit=6000)
    schema = load_schema("ddxplus")
    scorer = NaiveBayes().fit(patients[:4000])
    schema = schema.with_priors(fit_priors([p["evidences"] for p in patients[:4000]], schema))

    held = [p for p in patients[4000:] if len(p["evidences"]) >= 6]
    before = guided = blind = n = 0

    for patient in held[:cases]:
        full = patient["evidences"]
        truth = patient["pathology"]
        hidden = random.sample(list(full), 3)
        reduced = {k: v for k, v in full.items() if k not in hidden}
        if not reduced:
            continue

        n += 1
        before += argmax(scorer(reduced)) == truth

        # the engine nominates one field out of everything still unknown
        gaps = rank_gaps(reduced, scorer, schema, candidates=hidden + random.sample(
            [f for f in schema.fields if f not in reduced and f not in hidden], 25))
        pick = gaps[0].field if gaps else None

        # reveal the honest answer: the patient's value if they had it, otherwise a negative
        def reveal(field):
            got = dict(reduced)
            if field in full:
                got[field] = full[field]
            return got

        if pick:
            guided += argmax(scorer(reveal(pick))) == truth
        coin = random.choice(hidden + ["E_1"])
        blind += argmax(scorer(reveal(coin))) == truth

    print(f"cases {n}   three fields hidden per patient\n")
    for label, hits in (("no extra question ", before),
                        ("ask at random     ", blind),
                        ("ask what it says  ", guided)):
        lo, hi = wilson(hits, n)
        print(f"{label}  accuracy {hits / n:6.1%}   95% CI [{lo:.1%}, {hi:.1%}]")
    if n:
        print(f"\nlift from following the advice: "
              f"{(guided - blind) / n:+.1%} over asking at random, "
              f"{(guided - before) / n:+.1%} over not asking")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 300)
