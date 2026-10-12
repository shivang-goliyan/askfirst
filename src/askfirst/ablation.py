"""Leave-one-out influence for fields that are present, and expected influence for fields
that are not. The second one is the product; the first one calibrates it."""

from dataclasses import dataclass


@dataclass
class Influence:
    field: str
    shift: float


@dataclass
class Gap:
    field: str
    flip_prob: float
    spread: float
    cost: float
    delay: float

    def value_per_cost(self):
        return self.flip_prob / (self.cost + 1.0)


def total_variation(p, q):
    keys = set(p) | set(q)
    return 0.5 * sum(abs(p.get(k, 0.0) - q.get(k, 0.0)) for k in keys)


def argmax(dist):
    return max(dist, key=dist.get)


def sensitivity_map(record, scorer, schema):
    """How much does the answer move when we take away something we already have?"""
    base = scorer(record)
    out = []
    for name in schema.present_in(record):
        without = {k: v for k, v in record.items() if k != name}
        out.append(Influence(name, total_variation(base, scorer(without))))
    return sorted(out, key=lambda i: -i.shift)


def rank_gaps(record, scorer, schema, candidates=None):
    """For each thing we don't have, try every value it could come back as and see how often
    the answer changes. Fields whose possible values disagree with each other are worth getting."""
    base = scorer(record)
    settled = argmax(base)
    candidates = candidates or schema.missing_from(record)

    gaps = []
    for name in candidates:
        values = schema.values_for(name)
        if not values:
            continue
        outcomes = [scorer({**record, name: v}) for v in values]
        flips = sum(1 for d in outcomes if argmax(d) != settled)
        spread = max(total_variation(base, d) for d in outcomes)
        spec = schema.fields[name]
        gaps.append(Gap(name, flips / len(values), spread, spec.cost, spec.delay))

    return sorted(gaps, key=lambda g: (-g.flip_prob, -g.spread))


def sufficiency(record, scorer, schema):
    """0-100. High when nothing we could still learn would change the answer."""
    gaps = rank_gaps(record, scorer, schema)
    if not gaps:
        return 100.0
    return round(100.0 * (1.0 - max(g.flip_prob for g in gaps)), 1)
