"""Leave-one-out influence for fields that are present, and expected influence for fields
that are not. The second one is the product; the first one calibrates it.

Expected influence is weighted by how likely each value is. Treating a troponin as equally
likely to come back normal, raised or very raised is not a neutral assumption — it is a wrong
one, and it makes the ranking lumpy on top of being wrong."""

from dataclasses import dataclass, field as dc_field


@dataclass
class Influence:
    field: str
    shift: float


@dataclass
class Outcome:
    value: object
    prior: float
    flips: bool
    shift: float
    verdict: str


@dataclass
class Gap:
    field: str
    flip_prob: float
    expected_shift: float
    worst_shift: float
    cost: float
    delay: float
    by_value: list = dc_field(default_factory=list)

    def value_per_cost(self):
        return self.flip_prob / (self.cost + 1.0)

    def most_telling(self):
        """The value worth quoting in a UI: the likeliest one that changes the answer."""
        flipping = [o for o in self.by_value if o.flips]
        return max(flipping, key=lambda o: o.prior) if flipping else None


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
    """For each thing we don't have, try every value it could come back as, and weight the
    result by how likely that value is. flip_prob is then a real probability: the chance that
    going and getting this field changes the decision."""
    base = scorer(record)
    settled = argmax(base)
    candidates = candidates or schema.missing_from(record)

    gaps = []
    for name in candidates:
        values = schema.values_for(name)
        if not values:
            continue

        priors = schema.priors_for(name)
        rows = []
        for value in values:
            dist = scorer({**record, name: value})
            verdict = argmax(dist)
            rows.append(Outcome(
                value=value,
                prior=priors[value],
                flips=verdict != settled,
                shift=total_variation(base, dist),
                verdict=verdict,
            ))

        spec = schema.fields[name]
        gaps.append(Gap(
            field=name,
            flip_prob=sum(r.prior for r in rows if r.flips),
            expected_shift=sum(r.prior * r.shift for r in rows),
            worst_shift=max(r.shift for r in rows),
            cost=spec.cost,
            delay=spec.delay,
            by_value=rows,
        ))

    return sorted(gaps, key=lambda g: (-g.flip_prob, -g.expected_shift))


def sufficiency(record, scorer, schema):
    """0-100. High when nothing we could still learn is likely to change the answer."""
    gaps = rank_gaps(record, scorer, schema)
    if not gaps:
        return 100.0
    return round(100.0 * (1.0 - max(g.flip_prob for g in gaps)), 1)
