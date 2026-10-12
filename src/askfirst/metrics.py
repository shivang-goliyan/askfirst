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
