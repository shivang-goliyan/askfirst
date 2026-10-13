"""Everything the live page needs that can only come from the patient file.

    python3 scripts/bake_demo.py data/ddxplus/release_validate_patients

Two artifacts. First, value priors and answer rates for the DDXPlus schema, because without
them the ranker assumes every question is equally likely to come back any way it could, which
is wrong in both directions: a rare symptom is treated as a coin flip, and a question that
usually comes back empty is treated as though it always answers.

Second, a handful of real held-out patients, so the case on the page is a patient the scorer
has never seen rather than a hand-written sketch. They come from past the end of both the
fitting set and the set the risk-coverage curve was measured on, so nothing on the page was
tuned on them."""

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from askfirst.ddxplus import load_patients  # noqa: E402
from askfirst.schema import fit_ask_rates, fit_priors, load_schema  # noqa: E402

BAKED = Path("src/askfirst/baked")
FIT = 30000       # scripts/train_scorer.py fits on patients[:30000]
CURVE = 36000     # scripts/bake_curve.py measures on patients[30000:36000]
WANT = 12
SIZE = (7, 18)    # findings per patient — enough to thin, few enough to read


def pick(patients):
    """A spread of conditions and record sizes, taken in order so the choice is reproducible."""
    rng = random.Random(7)
    pool = [p for p in patients if SIZE[0] <= len(p["evidences"]) <= SIZE[1]]
    rng.shuffle(pool)
    out, used = [], set()
    for p in pool:
        if p["pathology"] in used:
            continue
        used.add(p["pathology"])
        out.append(p)
        if len(out) == WANT:
            break
    return out


def main(path):
    schema = load_schema("ddxplus")
    patients = [p for p in load_patients(path, limit=60000) if p["evidences"]]
    fitting = [p["evidences"] for p in patients[:FIT]]

    priors = fit_priors(fitting, schema)
    rates = fit_ask_rates(fitting, schema)
    # one probability per declared value, in the schema's own order. Keyed by value they would
    # come back as strings, and several fields here are numbered scales, so "3" would not match
    # the 3 in the schema and the field would end up with priors that sum to nothing.
    ordered = {
        name: [priors[name][v] for v in spec.values]
        for name, spec in schema.fields.items()
    }
    (BAKED / "ddxplus_priors.json").write_text(json.dumps({
        "fitted_on": f"{len(fitting)} patients, the same ones the scorer was fitted on",
        "order": "one probability per value, in the order the schema declares them",
        "priors": ordered,
        "rates": rates,
    }))
    answers = sum(1 for r in rates.values() if r >= 0.5)
    print(f"priors for {len(priors)} fields; {answers} of them answer at least half the time")

    unseen = patients[CURVE:]
    chosen = pick(unseen)
    (BAKED / "cases.json").write_text(json.dumps({
        "source": "DDXPlus release_validate_patients (CC BY 4.0), synthetic patients",
        "held_out": f"patients past index {CURVE}: not in the fitting set and not in the "
                    f"{CURVE - FIT} the curve was measured on",
        "patients": [
            {
                "id": i + 1,
                "age": p["age"],
                "sex": p["sex"],
                "truth": p["pathology"],
                "evidences": p["evidences"],
            }
            for i, p in enumerate(chosen)
        ],
    }, indent=1))
    print(f"{len(chosen)} patients from {len(unseen)} never-touched records:")
    for p in chosen:
        print(f"  {len(p['evidences']):>3} findings   {p['pathology']}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/ddxplus/release_validate_patients")
