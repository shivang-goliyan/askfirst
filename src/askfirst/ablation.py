"""Leave-one-out influence for fields that are present, and expected information gain for
fields that are not. The second one is the product; the first one calibrates it.

Ranking by flip probability was the first thing tried and it is actively harmful: it selects for
whatever is most likely to change the answer, which is volatility, not information. A field that
flips the decision half the time is a coin, and following that advice measured WORSE than asking
at random. Expected information gain asks how much the answer gets SETTLED instead, which is
what the question was always meant to mean.

Expected influence is weighted by how likely each value is. Treating a troponin as equally
likely to come back normal, raised or very raised is not a neutral assumption — it is a wrong
one, and it makes the ranking lumpy on top of being wrong."""

import math
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
    entropy: float = 0.0


def entropy(dist):
    return -sum(p * math.log(p, 2) for p in dist.values() if p > 0)


def answer_breadth(spec):
    """How much a question COULD tell you: log2 of the number of answers it admits.

    This is what decides the order, and it beat every cleverer objective we tried. 1,000
    held-out patients, three findings in hand, one question allowed, 25 fields the patient does
    not have mixed into the candidate pool:

        no question                      41.7%
        ask at random                    46.2%
        ask by expected information      38.2%   <- worse than asking nothing
        ask whatever usually answers     42.8%   <- also worse than random
        ask the widest question          66.9%
        widest, weighted by answer rate  72.7%
        (upper bound: widest question the patient can actually answer, 70.2%)

    Expected information gain sums P(value) x H(outcome | value) using the model's own beliefs,
    and on a sparse record those beliefs are wrong — so maximising expected information under a
    miscalibrated model is worse than guessing. How much a question could tell you needs no
    beliefs at all. In clinical terms: characterise the pain before asking about one more symptom.

    Answer rate on its own is worth nothing, which is the ablation that says breadth is really
    the mechanism and not a proxy for "questions that tend to get answered".
    """
    return math.log2(max(1, len(spec.values)))


@dataclass
class Gap:
    field: str
    info_gain: float
    flip_prob: float
    expected_shift: float
    worst_shift: float
    cost: float
    delay: float
    breadth: float = 1.0
    yield_rate: float = 1.0
    by_value: list = dc_field(default_factory=list)

    def value_per_cost(self, floor=0.05):
        """Bits per unit of cost, but only once the gap clears a floor of usefulness. Without a
        floor a nearly-free and nearly-useless field outranks a decisive one — a pulse oximeter
        reading beat an ECG this way, which is bad advice at any price."""
        if self.info_gain < floor:
            return 0.0
        return self.info_gain / (self.cost + 1.0)

    def most_telling(self):
        """The value worth quoting in a UI: the likeliest one that changes the answer."""
        flipping = [o for o in self.by_value if o.flips]
        return max(flipping, key=lambda o: o.prior) if flipping else None


def by_cost_effectiveness(gaps, relative_floor=0.25):
    """Order gaps by bits per unit of cost, after dropping anything that settles far less than
    the best option on the table. Primary ranking stays information gain, which is the ordering
    that measured well; this is the view for someone who has to pay for the test."""
    if not gaps:
        return []
    best = max(g.info_gain for g in gaps)
    worth_it = [g for g in gaps if g.info_gain >= relative_floor * best]
    return sorted(worth_it, key=lambda g: (-g.value_per_cost(), -g.info_gain))


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
    base_entropy = entropy(base)
    settled = argmax(base)
    candidates = candidates or schema.missing_from(record)

    gaps = []
    for name in candidates:
        values = schema.values_for(name)
        if not values:
            continue

        priors = schema.priors_for(name)
        rate = schema.fields[name].asked_rate
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
                entropy=entropy(dist),
            ))

        # The branch where the question comes back empty. It leaves the distribution exactly
        # where it was, so it contributes the base entropy and never flips anything — but it
        # has to be counted, or a question that usually returns nothing is rated as though it
        # always returns its most decisive answer.
        spec = schema.fields[name]
        answered = sum(r.prior * r.entropy for r in rows)
        gaps.append(Gap(
            field=name,
            info_gain=rate * (base_entropy - answered),
            flip_prob=rate * sum(r.prior for r in rows if r.flips),
            expected_shift=rate * sum(r.prior * r.shift for r in rows),
            worst_shift=max(r.shift for r in rows),
            cost=spec.cost,
            delay=spec.delay,
            breadth=answer_breadth(spec),
            yield_rate=rate,
            by_value=rows,
        ))

    # Breadth, discounted by how often the question comes back with anything; expected
    # information only breaks ties. Ranking by expected information gain measured WORSE than
    # asking nothing at all (38.2% against 41.7%), and worse than a coin (46.2%). Breadth alone
    # gives 66.9% and breadth x answer rate gives 72.7% — better even than being told which
    # questions this patient can answer. The bits are still computed and still shown; they just
    # do not decide the order, because they are an expectation taken under beliefs that are
    # wrong on exactly the sparse records where the advice matters.
    return sorted(
        gaps, key=lambda g: (-(g.breadth * g.yield_rate), -g.info_gain, -g.expected_shift)
    )


def sufficiency(record, scorer, schema, gaps=None):
    """0-100. High when nothing we could still learn is likely to change the answer."""
    gaps = rank_gaps(record, scorer, schema) if gaps is None else gaps
    if not gaps:
        return 100.0
    return round(100.0 * (1.0 - max(g.flip_prob for g in gaps)), 1)
