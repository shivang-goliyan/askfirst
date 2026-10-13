# The advice works, and the principled objective was the problem — 13 October 2026

Until today the honest position was that the refusal worked and the advice did not. The advice
half now works, measured, and what fixed it was removing the clever part.

Then it got re-measured, because two bugs turned up in our own implementation of the objective we
were beating — both of them flattering it — and a third in the harness that was flattering us.
All three are fixed and the numbers below are from after.

## The measurement

4,000 held-out patients, the softmax scorer (99.6% top-1 on complete records), a record cut down
to a handful of findings, **one question allowed**. The candidate pool is everything the patient
actually has that we have not seen, plus 25 fields they do not have, so a strategy is not rewarded
for knowing which questions have answers.

| findings in hand | no question | ask at random | by expected information | by answer rate | by answer breadth | breadth × rate | *oracle: widest the patient can answer* |
|---|---|---|---|---|---|---|---|
| 2 | 26.5% | 32.1% | 22.8% | 24.2% | 59.6% | **61.3%** | *63.0%* |
| 3 | 42.9% | 47.9% | 39.9% | 42.0% | 71.6% | **72.5%** | *74.3%* |
| 5 | 70.3% | 72.9% | 68.1% | 70.1% | 85.9% | **86.4%** | *87.1%* |

95% intervals at three findings (n=4,000): no question [41.3%, 44.4%], random [46.3%, 49.4%],
expected information [38.4%, 41.4%], answer rate [40.5%, 43.6%], breadth [70.2%, 73.0%],
breadth × rate [71.1%, 73.8%].

Two things to take from that table.

**Expected information gain is worse than asking nothing at all.** Not worse than random — worse
than leaving the record alone, at all three starting sizes, with intervals that do not touch. It
picks a question, you go and get the answer, and the decision gets *worse*.

**Ranking by `log2(number of answers the question admits)` adds 24 to 29 points over a coin**, and
lands within 2 points of an oracle that is told which questions this patient can actually answer.

## Why the principled objective loses

Expected information gain is `Σ P(value) × H(outcome | value)` — an expectation taken under the
model's own beliefs about what each answer would do. On a record with three findings those beliefs
are wrong, so maximising an expectation computed from them is worse than not using them. Answer
breadth asks a different question — *how much could this tell me?* — and needs no beliefs at all.

In clinical terms the advice it produces is the obvious thing: **characterise what you already know
before asking about one more symptom.** Of DDXPlus's 223 fields only 13 admit more than two
answers — pain intensity, where it is, how fast it came on, what it feels like — and they carry
most of the discriminating signal. Ranking by breadth finds them without being told which they are.

## The ablation that matters

Breadth × answer rate is the order the engine ships. The obvious objection is that the rate term
is doing the work — that this is really "ask whatever usually gets answered" wearing a disguise.
It is not: **answer rate on its own scores 42.0%, below a coin's 47.9% and below asking nothing.**
Breadth alone gets 71.6%. The product is worth about one further point and its interval overlaps
breadth's, so the multiplier is kept because it never measured worse, not because it is
established.

## Three bugs, all of them in our favour

**A negative answer switched the feature on.** `SoftmaxScorer.encode` treated any value that was
not `False`, `None`, `0` or `"0"` as evidence present — so `{"E_103": "absent"}` scored identically
to `{"E_103": "present"}`. Every binary question was therefore evaluated as though the answer would
come back yes. 208 of 223 fields are binary.

**The ranker assumed every question gets answered.** Priors were fitted conditional on the field
appearing in the record, and DDXPlus records only positive findings, so "do you have this rare
symptom" came out with P(yes) ≈ 1. Fixed by fitting an answer rate per field — how often asking it
returns anything at all — and giving `rank_gaps` an explicit no-answer branch that leaves the
distribution where it was. A question that comes back empty 97% of the time is now scored as such.

Both bugs inflated expected information gain. Fixing them made it worse: 43.3% → 39.9% at three
findings. The objective we are beating is now implemented correctly and loses by more.

**And one in the harness, flattering us.** The breadth arm picked with `max(gaps, key=breadth)` over
a list `rank_gaps` had already sorted — and three fields tie at the widest breadth, so `max()` was
resolving that tie by the engine's own ordering. That was worth seven points to the breadth arm.
Every arm now picks from a shuffled copy, so ties break at random. This is the second time in two
days that `max()` over a sorted list has manufactured a result here; the difference is that this
time the ablation was already in place and caught it the same hour.

## The thing I got wrong on the way here, because it is instructive

Mid-investigation I measured a "presence" strategy — ask about whatever is most likely to be there
— at 67.9% and briefly believed it. It reproduced, but the explanation was wrong: presence ties at
1.0 for exactly the graded fields, so `max()` was selecting them by list order. The mechanism was
breadth the whole time. **The first number was real and the reason for it was not**, which is the
same failure this product is built to catch, committed by the thing building it.

That is why the ablation above exists, and why it is the first thing in this directory to have
caught its own error before publication rather than after.

## Four objectives, in the order they were tried and beaten

1. **Flip probability** — 18.8% against 26.0% for random. Actively harmful. Selects for volatility.
2. **Pathology-conditioned discrimination** — 14.7% against 20.0% at k=10. "What separates
   hypotheses" is not "what is missing from this record".
3. **Expected information gain** — 39.9% against 47.9% for random and 42.9% for asking nothing.
   The principled choice the literature uses, and the only one that is worse than silence.
4. **Answer breadth** — 71.6%, or 72.5% weighted by how often the question gets answered. No model
   beliefs involved.

Four attempts, three of them worse than a coin, and the winner is a property of the question rather
than anything learned. That pattern is now the most reliable finding in this project.

## What this does not say

Only 13 of 223 DDXPlus fields admit more than two answers, and this dataset is rule-based
synthetic — its graded fields are discriminative partly by construction. On a real record the
graded fields may not dominate, and the honest claim is about this benchmark.

The record representation still cannot store "asked, and the answer was no". The *ranker* now
models that branch, which is most of what was missing, but a negative answer is dropped rather than
recorded, so the scorer cannot learn from one. Fixing that end of it means a three-state encoding
and a refit, which is a larger change than the day allows.

## Reproducing it

    python3 scripts/bake_demo.py data/ddxplus/release_validate_patients   # priors and answer rates
    python3 scripts/run_decision_value.py data/ddxplus/release_validate_patients 4000

Four minutes on a laptop CPU. 1,000 cases takes one minute and gives the same ordering with wider
intervals.
