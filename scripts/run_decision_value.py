"""Does following the tool's advice actually improve the decision?

    python3 scripts/run_decision_value.py data/ddxplus/release_validate_patients 1000

Recovery asked "can it name the field we deleted", which rewards guessing what a patient probably
had. This asks the thing the product claims: that the field it points at is worth going to get.
Start from a record, let the engine nominate one thing to obtain, obtain it honestly, and compare
against asking at random and against not asking.

Three changes from the first version of this script:

The scorer is the softmax one, 99.6% on complete records. The old naive Bayes at 22.6% made every
comparison here a comparison between two bad guesses.

And it starts from a THIN record rather than hiding three fields from a full one. Hiding three of
sixteen leaves the record about 80% complete, where the scorer is already at 98% and one more
finding cannot show up. Advice is worth something exactly where the record is sparse, so that is
where it gets measured."""

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from askfirst.ablation import argmax, rank_gaps  # noqa: E402
from askfirst.ddxplus import load_patients  # noqa: E402
from askfirst.metrics import wilson  # noqa: E402
from askfirst.ablation import answer_breadth, entropy  # noqa: E402
from askfirst.schema import (  # noqa: E402
    fit_ask_rates, fit_conditional, fit_priors, load_schema,
)
from askfirst.softmax import SoftmaxScorer  # noqa: E402

WEIGHTS = Path("src/askfirst/baked/ddxplus_softmax.npz")
START = (2, 3, 5)          # findings in hand before the question
POOL = 25                  # distractors mixed in with the fields the patient really has
OUT = Path("docs/results/decision-value.json")


def marginal_gain(gap, schema, base_entropy):
    """The same gap scored the way it was before: population marginals and a fixed answer rate.
    Recomputed from the rows the conditional pass already produced, so the model is only run
    once per candidate."""
    spec = schema.fields[gap.field]
    priors = schema.priors_for(gap.field)
    answered = sum(priors.get(row.value, 0.0) * row.entropy for row in gap.by_value)
    return spec.asked_rate * (base_entropy - answered)


def main(path, cases=1000):
    random.seed(11)
    patients = [p for p in load_patients(path, limit=40000) if p["evidences"]]
    schema = load_schema("ddxplus")
    fitting = [p["evidences"] for p in patients[:30000]]
    schema = schema.with_priors(fit_priors(fitting, schema), fit_ask_rates(fitting, schema))
    scorer = SoftmaxScorer.load(WEIGHTS, schema)
    # P(value | outcome), so the information-gain arm can weight each possible answer by what we
    # already believe about this patient instead of by how common the answer is in the population
    conditional = fit_conditional(
        [(p["evidences"], p["pathology"]) for p in patients[:30000]], schema)

    held = [p for p in patients[30000:] if len(p["evidences"]) >= 8]
    print(f"scorer: softmax, 99.6% top-1 on complete records")
    print(f"{min(cases, len(held))} patients, one question allowed, "
          f"{POOL} distractors in the candidate pool\n")
    print(f"{'start with':>11} {'no question':>12} {'ask at random':>14} "
          f"{'marginal bits':>14} {'true bits':>11} {'by breadth':>12} "
          f"{'breadth x rate':>16} {'oracle widest':>14}")

    out = {}
    for start in START:
        tally = {k: 0 for k in ("none", "random", "bits", "truebits", "rate", "condrate",
                                "breadth", "likely", "oracle")}
        n = 0
        for patient in held[:cases]:
            full = patient["evidences"]
            truth = patient["pathology"]
            have = random.sample(list(full), min(start, len(full)))
            reduced = {k: full[k] for k in have}
            unseen = [f for f in full if f not in reduced]
            if not unseen:
                continue

            n += 1
            pool = unseen + random.sample([f for f in schema.fields if f not in full], POOL)
            gaps = rank_gaps(reduced, scorer, schema, candidates=pool,
                             conditional=conditional)
            base_entropy = entropy(scorer(reduced))
            if not gaps:
                continue

            def reveal(field):
                got = dict(reduced)
                if field in full:
                    got[field] = full[field]
                return got

            # Shuffled before any arm picks, so max() breaks its ties at random instead of
            # inheriting the order rank_gaps sorted them into. Three fields tie at the widest
            # breadth here, and letting the engine's own ordering settle that tie flattered the
            # breadth arm by seven points — the same mistake, caught by the same ablation.
            shuffled = list(gaps)
            random.shuffle(shuffled)

            picks = {
                "random": random.choice(pool),
                # the objective as the literature states it, weighted by what we believe
                # about THIS patient, and the version we shipped before, weighted by the
                # population marginal. Both read off one pass over the candidates.
                "truebits": max(shuffled, key=lambda g: g.info_gain).field,
                "bits": max(shuffled,
                            key=lambda g: marginal_gain(g, schema, base_entropy)).field,
                # how likely the question is to be answered AT ALL given what we believe about
                # this patient, as against the population rate the engine actually ships with
                "condrate": max(shuffled, key=lambda g: g.yield_rate).field,
                "breadth": max(shuffled, key=lambda g: g.breadth).field,
                # the engine's own order. Both terms are schema properties, so they are read
                # off the schema and not off the conditional pass — this arm is production.
                "likely": max(shuffled, key=lambda g: g.breadth
                              * schema.fields[g.field].asked_rate).field,
                # the two halves of that product on their own, because last time a ranking was
                # credited to the wrong mechanism and the ablation is what caught it
                "rate": max(shuffled, key=lambda g: schema.fields[g.field].asked_rate).field,
                # upper bound, not a policy: the widest question the patient can actually answer
                "oracle": max([g for g in shuffled if g.field in full] or shuffled,
                              key=lambda g: g.breadth).field,
            }
            tally["none"] += argmax(scorer(reduced)) == truth
            for name, field in picks.items():
                tally[name] += argmax(scorer(reveal(field))) == truth

        row = {k: v / n for k, v in tally.items()}
        row["n"] = n
        row["ci"] = {k: list(wilson(tally[k], n)) for k in tally}
        out[start] = row
        print(f"{start:>11} {row['none']:>11.1%} {row['random']:>13.1%} "
              f"{row['bits']:>14.1%} {row['truebits']:>11.1%} {row['breadth']:>12.1%} "
              f"{row['likely']:>16.1%} {row['oracle']:>14.1%}")

    print("\n95% intervals, so the overlap can be judged rather than asserted:")
    for start, row in out.items():
        c = row["ci"]
        print(f"  start {start} (n={row['n']}):  "
              f"random [{c['random'][0]:.1%}, {c['random'][1]:.1%}]  "
              f"marginal bits [{c['bits'][0]:.1%}, {c['bits'][1]:.1%}]  "
              f"true bits [{c['truebits'][0]:.1%}, {c['truebits'][1]:.1%}]  "
              f"answerable [{c['condrate'][0]:.1%}, {c['condrate'][1]:.1%}]  "
              f"rate [{c['rate'][0]:.1%}, {c['rate'][1]:.1%}]  "
              f"breadth [{c['breadth'][0]:.1%}, {c['breadth'][1]:.1%}]  "
              f"breadth x rate [{c['likely'][0]:.1%}, {c['likely'][1]:.1%}]")

    OUT.write_text(json.dumps({str(k): v for k, v in out.items()}, indent=2))
    print(f"\nwrote {OUT}")
    print("'marginal bits' weights each answer by how common it is in the population.")
    print("'true bits' weights it by P(value | record), through the outcomes — the objective as")
    print("the literature states it. It gains about a point and still loses to a coin, and still")
    print("loses to asking nothing at all. 'answerable' asks whatever this patient is likeliest")
    print("to be able to answer, which is a real signal and still well short of breadth.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/ddxplus/release_validate_patients",
         int(sys.argv[2]) if len(sys.argv) > 2 else 1000)
