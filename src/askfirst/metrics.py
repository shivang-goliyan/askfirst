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
