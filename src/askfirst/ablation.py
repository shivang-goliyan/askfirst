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

    This is what decides the order, and it beat every cleverer objective we tried. 4,000
    held-out patients, three findings in hand, one question allowed, 25 fields the patient does
    not have mixed into the candidate pool:

        no question                      42.7%
        ask at random                    43.7%
        ask by expected information      39.9%   <- worse than asking nothing
        ask whatever usually answers     42.0%   <- also worse than random
        ask the widest question          60.7%
        widest, weighted by answer rate  72.3%
        (upper bound: widest question the patient can actually answer, 74.3%)

    Because both terms are properties of the QUESTION, the resulting order is the same for every
    patient. That is the finding rather than an oversight: four patient-specific objectives were
    tried and three lost to a coin.

    What this computes is not the literature's expected information gain. P(value) here is the
    fitted marginal, not P(value | record) taken from the model, so the quantity can come out
    negative and a true mutual information cannot. It is a marginal-prior approximation, and the
    comparison above should be read as against that rather than against a faithful BALAR.

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


def answer_odds(name, schema, base, conditional):
    """How likely each answer is GIVEN what we already believe, not in the population.

        P(value | record) = sum over outcomes of P(value | outcome) x P(outcome | record)

    The first term is counted once from labelled patients, the second is what the scorer just
    returned. Whatever mass is left over is the chance the question comes back with nothing,
    which is a real outcome and is not renormalised away.

    Without this the weights are population marginals — identical for every patient — and that
    is the thing a reviewer correctly called a strawman version of the published objective."""
    spec = schema.fields[name]
    table = conditional.get(name) if conditional else None
    if not table:
        return schema.priors_for(name), spec.asked_rate

    weight = {}
    for value in spec.values:
        weight[value] = sum(table.get(o, {}).get(value, 0.0) * p for o, p in base.items())
    answered = sum(weight.values())
    if answered <= 0:
        return schema.priors_for(name), spec.asked_rate
    rate = min(1.0, answered)
    return {v: w / answered for v, w in weight.items()}, rate


def rank_gaps(record, scorer, schema, candidates=None, conditional=None):
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

        priors, rate = answer_odds(name, schema, base, conditional)
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
    # asking nothing at all (41.3% against 42.7%), and worse than a coin (43.7%). Breadth alone
    # gives 60.7% and breadth x answer rate gives 72.3%, against 74.3% for being told which
    # questions this patient can answer. The bits are still computed and still shown; they just
    # do not decide the order, because they are an expectation taken under beliefs that are
    # wrong on exactly the sparse records where the advice matters.
    return sorted(
        gaps, key=lambda g: (-(g.breadth * g.yield_rate), -g.info_gain, -g.expected_shift)
    )


def most_telling_gap(record, scorer, schema, gaps=None):
    """The chance that going and getting one more fact changes the decision.

    This used to be served as "sufficiency, 0-100", the complement of this number, and it was
    misleading in the one place it mattered. On a thin record nothing flips the leading answer —
    not because the record is adequate but because the model is unsure of everything, so no
    single fact moves the top of a flat distribution. The page was printing "sufficiency 96/100"
    directly above "too little to judge the answer by". Same arithmetic, honest name: how much
    one more fact could still move things, where high means unsettled."""
    gaps = rank_gaps(record, scorer, schema) if gaps is None else gaps
    if not gaps:
        return 0.0
    return round(max(g.flip_prob for g in gaps), 4)


def sufficiency(record, scorer, schema, gaps=None):
    """Kept for the command-line demo and the tests. Not served to anyone — see above."""
    return round(100.0 * (1.0 - most_telling_gap(record, scorer, schema, gaps)), 1)
