def topk_recovery(ranked_fields, deleted, k):
    """Did we name the field that was taken out, somewhere in the top k?"""
    return deleted in ranked_fields[:k]


def flip_rate(records, scorer, schema):
    """Share of records where removing a single field changes the answer. Reported so nobody
    has to take the influence numbers on trust."""
    from .ablation import argmax, sensitivity_map

    flipped = 0
    for record in records:
        settled = argmax(scorer(record))
        for inf in sensitivity_map(record, scorer, schema):
            without = {k: v for k, v in record.items() if k != inf.field}
            if argmax(scorer(without)) != settled:
                flipped += 1
                break
    return flipped / len(records) if records else 0.0


def wilson(hits, n, z=1.96):
    """Wilson interval, because a normal approximation is embarrassing near 0 and 1 and several
    of these cells sit at 100% on a few hundred cases."""
    if n == 0:
        return 0.0, 0.0
    p = hits / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return (centre - spread) / denom, (centre + spread) / denom


def reliability(scored, bins=10):
    """Confidence against the accuracy it actually delivers, in bins.

    `scored` is a list of (confidence, right). A model whose 0.7 means 0.7 sits on the diagonal.
    One that does not is still useful for ranking and useless as a number, which matters here
    because the refusal threshold IS that number."""
    rows = []
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        take = [s for s in scored if lo <= s[0] < hi or (b == bins - 1 and s[0] == 1.0)]
        if not take:
            rows.append({"lo": lo, "hi": hi, "n": 0, "confidence": None, "accuracy": None})
            continue
        rows.append({
            "lo": lo, "hi": hi, "n": len(take),
            "confidence": sum(s[0] for s in take) / len(take),
            "accuracy": sum(1 for s in take if s[1]) / len(take),
        })
    return rows


def ece(scored, bins=10):
    """Expected calibration error: the gap between promise and delivery, weighted by how often
    each promise is made."""
    rows = [r for r in reliability(scored, bins) if r["n"]]
    total = sum(r["n"] for r in rows)
    if not total:
        return 0.0
    return sum(r["n"] / total * abs(r["accuracy"] - r["confidence"]) for r in rows)


def clustered(answered, patients, draws=400, seed=19):
    """Bootstrap over PATIENTS, not over rows. Resample the people, take every view each
    resampled person contributed, and recompute. Wilson over rows assumes independence that
    repeated views of one patient do not have.

    `answered` rows need a "who" and a "right"; `patients` is how many people were in the pool,
    which is only used to keep callers honest about what they are resampling."""
    import random as _random

    by_who = {}
    for row in answered:
        by_who.setdefault(row["who"], []).append(row["right"])
    who = list(by_who)
    if not who:
        return None, None
    rng = _random.Random(seed)
    spread = []
    for _ in range(draws):
        hits = seen = 0
        for _ in range(len(who)):
            for right in by_who[who[rng.randrange(len(who))]]:
                seen += 1
                hits += right
        if seen:
            spread.append(hits / seen)
    spread.sort()
    return spread[int(0.025 * len(spread))], spread[int(0.975 * len(spread)) - 1]
