"""CIViC evidence, grouped into the unit a tumour board actually argues about: one molecular
profile, one disease, one therapy question.

Evidence levels run A (validated) to E (inferential), which is a strength hierarchy in the same
spirit as the ACMG tiers. Direction is Supports or Does Not Support, and rating is 1-5 trust.
A group where the evidence disagrees with itself is the interesting case."""

import csv
from collections import defaultdict

LEVEL_WEIGHT = {"A": 1.0, "B": 0.6, "C": 0.35, "D": 0.2, "E": 0.1}
TYPES = ("Predictive", "Prognostic", "Diagnostic", "Predisposing", "Functional", "Oncogenic")


def load_groups(path, min_items=2):
    grouped = defaultdict(list)
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            key = (row["molecular_profile"], row["disease"], row["therapies"])
            grouped[key].append(row)
    return {k: v for k, v in grouped.items() if len(v) >= min_items}


def contested(groups):
    """Groups whose own evidence points in more than one direction. These are the cases where
    asking what to go and get is a real question rather than a formality."""
    return {
        k: v for k, v in groups.items()
        if len({r["significance"] for r in v}) > 1
        or len({r["evidence_direction"] for r in v}) > 1
    }


def as_record(items):
    """One field per evidence type, holding the strongest level seen for it."""
    best = {}
    for row in items:
        kind = row["evidence_type"]
        level = row["evidence_level"]
        if kind not in best or LEVEL_WEIGHT.get(level, 0) > LEVEL_WEIGHT.get(best[kind], 0):
            best[kind] = level
    return best


def weighted_verdict(items):
    """Trust-weighted vote over significance, so a validated level-A item outweighs three
    preclinical ones. Returns a distribution, which is what the engine ablates."""
    tally = defaultdict(float)
    for row in items:
        sig = row["significance"] or "N/A"
        try:
            trust = float(row["rating"] or 3) / 5.0
        except ValueError:
            trust = 0.6
        weight = LEVEL_WEIGHT.get(row["evidence_level"], 0.1) * trust
        if row["evidence_direction"] == "Does Not Support":
            weight *= -0.5
        tally[sig] += weight

    floor = min(list(tally.values()) + [0.0])
    shifted = {k: v - floor + 1e-6 for k, v in tally.items()}
    total = sum(shifted.values())
    return {k: v / total for k, v in shifted.items()}
