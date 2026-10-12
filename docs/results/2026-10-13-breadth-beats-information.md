# The advice works, and the principled objective was the problem — 13 October 2026

Until today the honest position was that the refusal worked and the advice did not. The advice
half now works, measured, and what fixed it was removing the clever part.

## The measurement

800–1,000 held-out patients, the softmax scorer (99.6% top-1 on complete records), a record cut
down to a handful of findings, **one question allowed**. The candidate pool is everything the
patient actually has that we have not seen, plus 25 fields they do not have, so a strategy is not
rewarded for knowing which questions have answers.

| findings in hand | no question | ask at random | by expected information | **by answer breadth** | vs random |
|---|---|---|---|---|---|
| 2 | 29.2% | 34.7% | 30.3% | **57.7%** | **+23.0** |
| 3 | 41.7% | 46.2% | 43.3% | **67.1%** | **+20.9** |
| 5 | 69.0% | 72.4% | 69.3% | **85.3%** | **+12.9** |

95% intervals at three findings: random [43.1%, 49.3%], information [40.3%, 46.4%], breadth
[64.1%, 69.9%]. Nowhere near touching.

**Ranking by expected information gain is consistently worse than asking at random.** Ranking by
`log2(number of answers the question admits)` adds 13 to 23 points.

## Why the principled objective loses

Expected information gain is `Σ P(value) × H(outcome | value)` — an expectation taken under the
model's own beliefs about what each answer would do. On a record with three findings those beliefs
are wrong, so maximising an expectation computed from them is worse than not using them. Answer
breadth asks a different question — *how much could this tell me?* — and needs no beliefs at all.

In clinical terms the advice it produces is the obvious thing: **characterise what you already know
before asking about one more symptom.** Of DDXPlus's 223 fields only 13 are graded — pain
intensity, where it is, how fast it came on, what it feels like — and they carry most of the
discriminating signal. Ranking by breadth finds them without being told.

The strategy needs no oracle. Picking the widest question out of the whole pool, distractors
included, scores 83.5% on a fixed 800-case set; picking the widest question the patient *actually
has* scores 84.1%. The gap is within noise, so knowing which questions have answers is worth
almost nothing — it is the shape of the question that matters.

## The thing I got wrong on the way here, because it is instructive

Mid-investigation I measured a "presence" strategy — ask about whatever is most likely to be there
— at 67.9% and briefly believed it. It reproduces (70.2% on a fixed case set) but the explanation
was wrong: presence ties at 1.0 for exactly the graded fields, so `max()` was selecting them by
list order. The mechanism was breadth the whole time, and breadth measured on its own is 13 points
better. **The first number was real and the reason for it was not**, which is the same failure this
product is built to catch, committed by the thing building it.

## Four objectives, in the order they were tried and beaten

1. **Flip probability** — 18.8% against 26.0% for random. Actively harmful. Selects for volatility.
2. **Pathology-conditioned discrimination** — 14.7% against 20.0% at k=10. "What separates
   hypotheses" is not "what is missing from this record".
3. **Expected information gain** — 43.3% against 46.2% for random. Still slightly harmful, and the
   principled choice the literature uses.
4. **Answer breadth** — 67.1%. No model beliefs involved.

Four attempts, three of them worse than a coin, and the winner is a property of the question rather
than anything learned. That pattern is now the most reliable finding in this project.

## What this does not say

Only 13 of 223 DDXPlus fields are graded, and this dataset is rule-based synthetic — its graded
fields are discriminative partly by construction. On a real record the graded fields may not
dominate, and the honest claim is about this benchmark.

The representation also cannot express "asked, and the answer was no". DDXPlus lists only positive
findings, so a question about something the patient lacks returns the record unchanged rather than
adding a negative. That understates binary questions, and fixing it means a three-state encoding —
recorded as a limitation rather than patched on the day.

## Reproducing it

    python3 scripts/run_decision_value.py data/ddxplus/release_validate_patients 1000
