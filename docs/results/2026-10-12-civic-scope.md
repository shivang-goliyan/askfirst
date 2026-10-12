# What CIViC can and cannot carry, 12 October 2026

Measured on the 1 October 2026 CIViC release, 4,940 accepted evidence items.

The unit a tumour board argues about is one molecular profile, one disease, one therapy question.
Grouping that way:

| | count |
|---|---|
| distinct profile / disease / therapy groups | 3,746 |
| groups with 2 or more evidence items (ablatable at all) | **585** |
| groups with 3 or more | 273 |
| groups with 5 or more | 52 |
| largest single group | 25 items |
| **groups whose own evidence disagrees with itself** | **182** |

Evidence levels run A (validated) through E (inferential), which is a strength hierarchy in the
same spirit as the ACMG tiers, and direction is Supports or Does Not Support with a 1-5 trust
rating. That is enough structure to build a weighted verdict and ablate it.

## The honest conclusion

**Module B is demo-strong and evaluation-weak, and the split of labour follows from that.**

182 contested groups is a good demo and a small measured result. It is not a sample that can
carry a headline number, and no amount of engineering changes that — it is how much curated
evidence exists. Anyone claiming a confident accuracy figure off 182 cases with this much
heterogeneity is overreaching.

So: **Module A (DDXPlus, thousands of cases) carries the measurement. Module B carries the
generalisation claim** — the same engine, a different schema, a real contested question in
oncology — plus the ESM-2 computational evidence line, which is genuinely ours to compute.

## The demo case this found

`DNMT3A R882` in acute myeloid leukaemia, the largest contested group, where CIViC's own curated
evidence contradicts itself: level-B items both Supporting and Not Supporting "Poor Outcome", at
ratings 3 and 4. The weighted verdict lands at Poor Outcome 0.56, Positive 0.26.

That is a better demo than a synthetic example, because the disagreement is real, it is in a
public knowledge base anyone can check, and it is exactly the situation where "what should we go
and get?" is the right question instead of "what is the answer?".

## Caveat on the hand-written variant schema

`schemas/variant.yaml` encodes the ACMG/AMP codes, which is the right framing for the product but
was written by hand, not derived from data. CIViC's evidence types are what we can actually
measure on. Keep both, and do not present the ACMG schema as if it had been validated here.
