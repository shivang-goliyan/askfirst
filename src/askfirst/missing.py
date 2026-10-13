"""Why a record is short, which turns out to matter more than how short it is.

Every measurement here started by hiding evidence uniformly at random, which is the easiest
possible assumption and not how anything goes missing. An intake that runs out of time gets
through the standard questions and not the follow-ups. A walk-in has symptoms and no history. A
triage note says there is pain and not where it is.

Those remove different *kinds* of evidence, and at a fifth of a record the difference between
them is worth fifty points of accuracy — so "20% of a record" is not one thing."""

import random

from .ablation import answer_breadth


def mechanisms(schema, rates=None):
    """Name to sort key. The highest keys survive, and ties break at random so that nothing
    quietly inherits the order the schema happens to list its fields in."""
    rates = rates or {}

    def wide(name):
        spec = schema.fields.get(name)
        return answer_breadth(spec) if spec else 0.0

    def part(name):
        spec = schema.fields.get(name)
        return spec.section if spec else "fields"

    return {
        "at random": lambda n, r: (r.random(),),
        "the detail goes, the screen stays": lambda n, r: (-wide(n), r.random()),
        "only the detail survives": lambda n, r: (wide(n), r.random()),
        "no history, symptoms only": lambda n, r: (part(n) == "fields", r.random()),
        "history only, nothing current": lambda n, r: (part(n) == "antecedents", r.random()),
        "standard questions, no follow-ups": lambda n, r: (rates.get(n, 0.0), r.random()),
        "only what was volunteered": lambda n, r: (-rates.get(n, 0.0), r.random()),
    }


def cut(patients, frac, key, seed=13):
    """Take the same number of findings away as uniform thinning would, and only change which."""
    rng = random.Random(seed)
    out = []
    for patient in patients:
        items = list(patient["evidences"].items())
        keep = max(1, int(len(items) * frac))
        items.sort(key=lambda kv: key(kv[0], rng), reverse=True)
        out.append({
            "evidences": dict(items[:keep]),
            "pathology": patient["pathology"],
            "true_n": len(patient["evidences"]),
        })
    return out


def augment(patients, ways, copies=1, levels=(0.6, 0.4, 0.2, 0.1), seed=5):
    """Masked copies of each patient, for training a scorer that will be handed thin records.

    The scorer used to be fitted on complete records and then asked about records with holes in
    them, where a deleted finding is represented exactly like one that was asked about and
    denied. That is a mismatch we created: measured, it costs 9 points of top-1 at 40% of a
    record and 30 points at a fifth, and fixing it costs a tenth of a point on complete records.

    `ways` is deliberately an argument rather than `mechanisms(...)` called in here. Training on
    all seven realistic patterns makes a slightly better model and makes every
    leave-one-pattern-out experiment weaker, because the scorer would have seen the pattern the
    post-processors are being asked to generalise to. Passing uniform thinning alone keeps the
    scorer agnostic, so those folds still test the whole pipeline — and it gets nearly all of
    the gain."""
    rng = random.Random(seed)
    keys = list(ways.values())
    out = []
    for c in range(copies):
        for i, patient in enumerate(patients):
            frac = rng.choice(levels)
            key = keys[rng.randrange(len(keys))]
            short = cut([patient], frac, key, seed=seed + c * 100003 + i)[0]
            out.append({"evidences": short["evidences"], "pathology": short["pathology"],
                        "age": patient.get("age"), "sex": patient.get("sex")})
    return out
