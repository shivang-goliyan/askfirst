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
