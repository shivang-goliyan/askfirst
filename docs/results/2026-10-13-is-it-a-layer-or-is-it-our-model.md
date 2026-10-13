# Is it a layer, or is it just our model? — 13 October 2026

`scripts/run_portability.py` · `docs/results/portability.json`

## The question

Two sentences sink this project if we cannot answer them, and both were put to us today by
reviewers rather than invented here:

> Any team can add a confidence threshold in an afternoon.

> Your gate is fitted to your own scorer, so it is a model, not a layer.

The second one was a fair reading of the code. `rule_for()` returned nothing for a scorer it
could not encode for, and `/api/assess` then admitted it had borrowed a cut-off from the softmax.
Meanwhile `BUSINESS.md` was selling "a gate in front of whatever you already use".

So: take the gate, refit it against scorers it was not designed for, and see whether it still
keeps the promise it makes.

## Three scorers whose confidence is wrong in three different directions

Picked for their failure modes, not their accuracy. All three see **identical features** — the
neighbour scorer borrows the softmax's encoder on purpose — so only the inductive bias differs.

| scorer | how its confidence is wrong | answering everything |
|---|---|---|
| multinomial logistic regression (ships) | **underconfident** as the record thins; a linear model's logits shrink as features drop out | 67.1% right |
| naive Bayes | **overconfident**; it multiplies dependent findings as though they were independent, so agreement compounds | 29.2% right |
| nearest-neighbour vote | **saturated**; on a thin record a handful of neighbours agree unanimously and it returns 1.00 with nothing behind it | 78.4% right |

Rules, folds and patient-clustered intervals are imported from `run_conformal.py` rather than
reimplemented, because the first version of that comparison was rigged by refitting one side and
not the other, and sharing one implementation is how that stops being possible to do by accident.
1,200 patients per split, 42,000 rows per scorer, every rule refitted per scorer **and** per
fold.

## The headline: 3 scorers × 7 leave-one-pattern-out folds = 21 cells

| rule | cells where the 95% promise held | worst cell | mean coverage |
|---|---|---|---|
| one global threshold | 9 of 21 | 89.9% | 43.0% |
| a threshold per group (Mondrian partition) | 10 of 21 | 89.8% | 47.9% |
| a threshold per group + **our** completeness floor | 14 of 21 | 87.0% | 36.6% |
| **the gate** | **20 of 21** | **96.0%** | 29.5% |

A cell counts as held only when the bootstrap **lower** bound clears 94.5%, so this is a strict
test. The one cell the gate does not pass is the naive Bayes under random thinning: 96.0% point
estimate, [93.6%, 98.2%] on 275 accepted rows. That is underpowered rather than broken, and it is
reported as a failure anyway because the rule we are applying to everyone else has to apply to us.

Handing the baseline our floor takes it from 10 of 21 to 14 of 21. So the floor is a real,
transferable ingredient — and it is not sufficient on its own.

## What the calibration actually buys, which depends on the scorer

Stop the **raw, uncalibrated margin ranking** at exactly the coverage the gate chose, and let it
pick that cut-off on the test set, which no deployable rule can do:

| scorer | the gate | raw margin at the same coverage | the calibration buys |
|---|---|---|---|
| logistic regression | 99.2% @ 36.2% | 99.4% [99.0%, 99.7%] | **−0.2 points** |
| naive Bayes | 99.3% @ 8.1% | 89.4% [86.5%, 91.8%] *(breaks)* | **+9.9 points** |
| nearest-neighbour vote | 99.7% @ 43.3% | 96.9% [96.5%, 97.3%] | **+2.8 points** |

This is the finding, and it corrects something we published four hours ago. Measured on our own
scorer alone, the calibration bought nothing but the stopping point, and we said so. Measured
across three, that turns out to have been a fact about *our scorer being well behaved*, not about
the calibration:

- On a scorer whose confidence already ranks well, the calibration adds nothing to the ordering.
  Its whole job is choosing where to stop without being shown the answers.
- On a scorer whose confidence is **badly** shaped, it adds **ten points of precision at identical
  coverage**, and the raw ranking breaks the promise where the calibration keeps it.

So the narrow claim from this morning was too narrow. The honest version: **the better your
model's confidence already is, the less this buys you — and nobody deploying a triage model knows
which case they are in, which is the problem.**

## Why one number cannot do it, shown rather than argued

The neighbour scorer pins its confidence at exactly 1.00 on **54.5% of rows**. Inside that single
pile:

| rows with confidence = 1.00 | accuracy |
|---|---|
| 4 findings or fewer | **91.8%** |
| 12 findings or more | **100.0%** |

An 8.2-point spread inside one number. To a threshold every row in that pile is identical, and
they are not identical. The gate reads the record — how many findings are in hand and how unusual
they are — so it can tell them apart. That is the entire mechanical argument for why this is not
a threshold, and it needed a scorer whose confidence saturates to become visible.

## What it costs

29.5% mean coverage against 47.9% for a per-group threshold. The gate leaves roughly 180 cases
per 1,000 with a person who did not strictly need to be there, and buys 20-of-21 instead of
10-of-21 with that. We over-deliver precision — 99%-plus when asked for 95% — and a per-group
quantile targeted at exactly 95% would convert some of that surplus into coverage. That is still
the open engineering item it was this morning, and it is now the most valuable one on the list.

## And the plumbing, since a measurement that the product does not implement is a paper

`POST /api/gate` takes a record and the caller's own confidence and contains no scorer of ours.
The ceiling, the completeness floor and the what-to-ask-next list need nothing fitted, because
they read the record rather than the score — the ranking that won the decision-value measurement
is breadth × answer rate, and both terms come off the schema and the priors. The precision
promise needs `scripts/fit_gate.py` run against that operator's history, and an unfitted caller
is told so rather than handed a borrowed curve.

The contrast is two curls. Same record, `"confidence": 0.5` → **80.2%** likely right from the
softmax, **13.9%** from the naive Bayes. One number, two unrelated meanings.

## What this does not show

Every scorer here is fitted on DDXPlus, and all three see the same encoder, so this measures
transfer across **inductive biases** and not across datasets, label spaces or clinical settings.
It is not evidence the gate works on a real queue; that is the next experiment and it is
pre-registered. And the 21 cells come from 1,200 patients viewed 35 ways, so the cells are not
independent of each other — the intervals are clustered on patients but the *count* of 20 of 21
is not an independent 21-trial result.
