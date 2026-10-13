# The advice works, and the principled objective was the problem — 13 October 2026

> **Measured against the previous scorer.** On 14 October the scorer was refitted on records with
> holes in them, and the artifact this file reads from has been regenerated, so figures in the
> prose below may disagree with the JSON beside them. The prose is left as the record of what was
> measured when. What moved, and what it cost the argument, is in
> `2026-10-14-the-scorer-now-expects-holes.md`.
>
> **This file's central finding is retracted.** Expected information gain losing to a coin and
> then to silence was an artifact of a scorer that had never seen a thin record. Refitted, it
> reaches 85.5% against 77.8% for asking nothing. Our ranking still wins, 88.8%, by three points
> rather than thirty.

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

| findings in hand | no question | ask at random | expected information, **as the literature states it** | whatever *this patient* can answer | by answer breadth | **breadth × rate (ships)** | *oracle* |
|---|---|---|---|---|---|---|---|
| 2 | 27.7% | 28.5% | **25.5%** | 44.7% | 46.7% | **61.6%** | *63.0%* |
| 3 | 42.7% | 43.7% | **41.3%** | 60.9% | 60.7% | **72.3%** | *74.7%* |
| 5 | 69.9% | 70.4% | **68.0%** | 81.9% | 80.2% | **86.7%** | *87.6%* |

95% intervals at three findings (n=4,000): random [42.2%, 45.2%], expected information
[39.8%, 42.8%], breadth [59.1%, 62.2%], breadth × rate [70.9%, 73.7%].

**Candidates are every one of the 223 fields not already in the record**, which is what the app
ranks over. An earlier version of this table used a shortlist — the fields this patient really
has plus 25 decoys — which quietly guaranteed every answerable question was on the list. Both
reviewers caught it. The harder pool makes random collapse (43.7% against 47.9%), makes breadth
alone fall eight points, and makes **the shipped order rise**, because the answer-rate term
finally has something to filter.

Two things to take from that table.

**Expected information gain is worse than asking nothing at all.** Not worse than random — worse
than leaving the record alone, at all three starting sizes, with intervals that do not touch. It
picks a question, you go and get the answer, and the decision gets *worse*.

That now holds against the objective **implemented properly**, which it did not before. A review
pointed out that our P(value) was the population marginal — the same for every patient — which is
not what BALAR or MedClarify do and is a strawman version of them. It is now computed the way the
literature states it, by going through the outcomes:

    P(value | record) = Σ over outcomes of P(value | outcome) × P(outcome | record)

with the first term counted once from the 30,000 fitting patients and the second taken from the
scorer. **Doing it correctly is worth about one point and does not change the conclusion.**

**Ranking by `log2(number of answers the question admits)` adds 16 to 33 points over a coin** — 28.6 at three findings, 33.0 at two, 16.3 at five, and
lands within 2 points of an oracle that is told which questions this patient can actually answer.

## Why the principled objective loses

Expected information gain is `H(outcome) − Σ P(value) × H(outcome | value)`. **An earlier version
of this note wrote only the second term and called it the objective, which is the expected
remaining entropy rather than the gain.** Worse, the `P(value)` we use is the fitted marginal and
not `P(value | record)` taken from the model, which is why the quantity on the page can come out
negative when a true mutual information cannot. What is measured below is a marginal-prior
approximation, and the comparison should be read against that rather than against a faithful
implementation of BALAR. On a record with three findings those beliefs
are wrong, so maximising an expectation computed from them is worse than not using them. Answer
breadth asks a different question — *how much could this tell me?* — and needs no beliefs at all.

In clinical terms the advice it produces is the obvious thing: **characterise what you already know
before asking about one more symptom.** Of DDXPlus's 223 fields only 13 admit more than two
answers — pain intensity, where it is, how fast it came on, what it feels like — and they carry
most of the discriminating signal. Ranking by breadth finds them without being told which they are.

## The ablation that matters, and the one that corrected it

Breadth × answer rate is the order the engine ships. The obvious objection is that the rate term
is doing the work — that this is really "ask whatever usually gets answered" in disguise. It is
not: **the population answer rate on its own scores 41.1%, below a coin and below asking nothing
at all.** Breadth alone gets 60.7%, and the product gets **72.3%**.

That multiplier is worth **11.6 points**, with intervals that do not touch — [59.1%, 62.2%]
against [70.9%, 73.7%]. An earlier version of this note said it was worth about one point and was
"kept because it never measured worse". That was an artifact of the shortlisted candidate pool,
which had already removed most of the unanswerable questions the rate term exists to filter. On
the real pool it is half the rule.

**But a conditional answer rate is a different thing, and it is not worthless.** Asking whatever
*this patient* is likeliest to be able to answer — P(the question returns anything | record),
from the same conditional table — scores **64.2%**, far above a coin and far above the population
rate. It is still seven points behind breadth, and both are behind the oracle. An earlier version
of this note said flatly that answer rate is worth nothing; that was true of the marginal and
false of the conditional, and the distinction is the interesting part rather than a detail.

## Why the bits come out negative, which is not the priors' fault

The page prints information gains like −0.193 bits, and a mutual information cannot be negative.
The first guess was the marginal priors. It is not: on a three-finding record, **210 of 220
candidate questions still have negative gain after conditioning properly.**

The real reason is that the scorer is discriminative. H(outcome | value) is obtained by re-running
a classifier with one more feature switched on, and a classifier is under no obligation to reduce
its own entropy when you do that — it is not performing a Bayesian update of the posterior it just
produced. Information gain is only guaranteed non-negative when both terms come from one coherent
joint model, and here they do not. That is worth stating because it means the objective was never
going to behave, whatever the priors, as long as the thing computing the entropies is a separately
trained classifier.

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
3. **Expected information gain** — 39.9% against 43.7% for random and 42.7% for asking nothing.
   The principled choice the literature uses, and the only one that is worse than silence.
4. **Answer breadth** — 60.7%, or 72.3% weighted by how often the question gets answered. No model
   beliefs involved.

Four attempts, three of them worse than a coin, and the winner is a property of the question rather
than anything learned. That pattern is now the most reliable finding in this project.

## The order is the same for every patient, and that is the point

Worth stating outright rather than leaving for a reviewer to notice: `breadth × answer rate` are
both properties of the *question*, so the top of the "go get" list is identical for a 79-year-old
with COPD, a 30-year-old in atrial fibrillation and a 53-year-old having an asthma attack. We
checked on the live API; all three return the same first four questions.

That is not a bug being excused. It is the result. Four patient-specific objectives were tried —
flip probability, pathology-conditioned discrimination, expected information gain, answer rate —
and three of them lost to a coin. **We went looking for a patient-specific ranking and found that
a patient-independent one wins**, on this benchmark, by 28.6 points at three findings.

What *is* patient-specific is everything shown beside the order: what the current answer rests on,
what each answer would settle in bits, how often one more fact would change the decision. Those
move case by case. The ordering does not, and a judge who clicks two patients will see that
immediately, so it belongs in the write-up rather than in their mouth.

It also means the advice half does not need an open model at all. The refusal half does — the
calibration, the ablation and the sensitivity map are all functions of the full distribution —
and conflating the two would overstate why the hardware matters.

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
