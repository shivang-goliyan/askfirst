# We tried to delete our own floor, and mostly succeeded — 13 October 2026

> **Measured against the previous scorer.** On 14 October the scorer was refitted on records with
> holes in them, and the artifact this file reads from has been regenerated, so figures in the
> prose below may disagree with the JSON beside them. The prose is left as the record of what was
> measured when. What moved, and what it cost the argument, is in
> `2026-10-14-the-scorer-now-expects-holes.md`.

`scripts/run_make_it_unnecessary.py` · `docs/results/make-it-unnecessary.json`

A reviewer asked two questions designed to remove parts of this product rather than improve them,
and both were better questions than anything we had thought to ask ourselves.

> The completeness estimator is a ridge regression predicting how many findings this patient
> would have had. Does `findings in hand / average record size` do the same job?

> The scorer is fitted on complete records and then handed records with holes in them, where a
> deleted finding is represented exactly like one that was asked about and denied. Train it on
> records with holes instead, and the confidence may come out honest by itself — in which case
> the calibration is fixing a problem you created.

Five arms, same 95% promise, same mixed stream, seven leave-one-pattern-out folds, everything
refitted per fold, intervals bootstrapped over patients.

## Question one: is the learned completeness estimator earning its place?

| arm | folds kept | worst fold | mean coverage |
|---|---|---|---|
| **no floor at all** — the calibration and the ceiling, nothing else | **7 of 7** | 97.5% | **40.3%** |
| a bare count, smallest that holds on the fit split (it picked n=0) | 7 of 7 | 97.5% | 40.3% |
| `findings / mean record size` against the same 0.35 floor | 7 of 7 | 98.3% | 34.3% |
| a count giving up the same coverage (n=4) | 7 of 7 | 98.0% | 36.8% |
| **the learned ridge** — what ships | 7 of 7 | 98.4% | 36.4% |

**The answer is no, not on this scorer.** Read that table honestly and it says:

- The calibration **alone** keeps the promise in all seven folds and answers **more** cases than
  we do — 40.3% against 36.4%. The floor costs us four points of coverage and buys 0.9 points of
  worst-fold precision.
- A count floor chosen to give up the same coverage gets 98.0% where the ridge gets 98.4%. Four
  tenths of a point. The learned estimator is not meaningfully better than counting the findings.
- The bare-count arm picked **n = 0**, because nothing needed to be excluded for the target to be
  met on the fit split. An arm that selects "no floor" is an arm telling you the floor is optional.

So the claim this repo has been making — that the completeness floor is what keeps the promise, and
that neither piece works without the other — **is not supported on our own scorer, and that
sentence has been corrected where it appeared — the docstring in `calibrate.py` and the
write-up that first made it.** What is left of the floor is narrower and still
real:

1. **It rescues a badly-shaped rule.** Handed to a per-group quantile threshold it moves that rule
   from 10 of 21 scorer-fold cells to 14 of 21 (`2026-10-13-is-it-a-layer-or-is-it-our-model.md`).
2. **It is the check that reads the record rather than the score**, so it runs for a stranger's
   model without being refitted, and on the saturated nearest-neighbour scorer it is the piece
   doing the work — the calibration's ordering there is worth +0.01 points and the floor's
   refusals are worth 2.8.
3. **It is a safety property, not an accuracy one.** A rule that answers a record with two
   findings on it because the arithmetic cleared a bar is the behaviour this product exists to
   refuse, whether or not the measurement rewards it.

That third one is a judgement and not a measurement, and it is the only reason the floor stays in
at a cost of four points of coverage. A reader who disagrees with the judgement should turn it off;
`FLOOR` is one constant in `calibrate.py` and the measurement above says what it costs.

## Question two: does training on records with holes make the gate unnecessary?

It does not. It makes the gate considerably more valuable.

| scorer | answering everything | one global threshold on it | with the gate |
|---|---|---|---|
| the shipped scorer, complete records only | 67.1% | — | 7/7, **36.4%** coverage |
| **trained for holes**, 60,000 rows | **82.3%** | **1 of 7 folds**, worst 92.2% | 7/7, **47.0%** |
| trained for holes, 30,000 rows (same row count as shipped) | **81.9%** | 1 of 7, worst 92.7% | 7/7, **46.2%** |

Three things fall out of it.

**Masking augmentation is worth 14.8 points of raw accuracy, and it is the holes rather than the
extra data.** The naive version doubles the training rows, so the control uses half complete and
half cut and lands on exactly the row count the shipped scorer saw: 81.9% against 67.1%. The gain
survives. This is the largest single improvement measured in this project and it came out of an
attempt to make the project unnecessary.

**A threshold on the better scorer is worse, not better.** One global threshold on the augmented
scorer keeps the promise in **1 of 7 folds** while answering 79% of the stream. Making the model
better made the naive rule *more* dangerous, because a well-calibrated-looking confidence on a
thin record is exactly the thing that fails quietly.

**The gate converts the improvement into coverage.** 36.4% to 46.2% of the queue taken off a
person at the same 95% promise — a 27% relative increase — with all seven folds still held.

So the honest summary of the second question: **training for missingness is the single best thing
we could do to this product, and it increases the value of the gate rather than removing it.**
That is now the top item on the list, ahead of the per-group quantile.

## What this experiment does not establish

- **One masked copy per patient is a limited attempt.** Resampling masks every epoch, several
  masked views per patient, or an explicit missing-indicator feature are all stronger and none of
  them was tried. If a richer augmentation *did* make the calibration redundant, this experiment
  would not have found out.
- **The augmented scorer saw all seven missingness patterns before the fold loop.** Only the
  thresholds and the gate exclude the held-out pattern. So these folds test a held-out
  *post-processor fitting condition*, not a pattern unseen by the whole pipeline. The shipped and
  augmented scorers are not on equal footing in that respect, and the comparison between them is
  therefore generous to the augmented one.
- **The count arm is matched on the fit split, not the test split.** Integer thresholds move
  coverage in jumps, so "the same coverage" is approximate, and `count_matching` compares counts
  without applying the ceiling that the evaluation applies. Both were named by a reviewer and
  neither is fixed here.
- **The augmented arms were only compared as threshold-versus-full-gate.** There is no
  calibration-without-floor arm on the augmented scorer, so this cannot say whether augmentation
  leaves the floor any role at all.

## The honest summary

We set out to delete two pieces of our own product. One of them — the learned completeness
estimator — does not survive the test on our own scorer, and the claim that it was load-bearing
has been retracted wherever it appeared. The other question found a 14.8-point improvement we had
not thought to look for, and showed that the better the scorer gets, the worse a bare threshold
behaves.

Both outcomes are more useful than the confirmation we would have got by not asking.

---

## Re-measured 14 October, against the scorer this experiment produced

The experiment above found that training on records with holes was worth 14.8 points. That was
shipped the next morning, which means every arm here had to be run again — and the finding about
the floor got considerably worse for the floor.

| arm, seven folds, the hole-trained scorer | folds kept | worst fold | mean coverage |
|---|---|---|---|
| **no floor at all** | 7 of 7 | 99.5% | **61.1%** |
| a bare count, smallest that holds (picked n=0) | 7 of 7 | 99.5% | 61.1% |
| `findings / mean record size` | 7 of 7 | 99.5% | 44.5% |
| a count giving up the same coverage (n=5) | 7 of 7 | 99.5% | 47.9% |
| **the learned ridge — what ships** | 7 of 7 | 99.5% | 47.2% |

**The floor now costs fourteen points of coverage and the worst fold does not move: 99.5% either
way.** Yesterday it cost four points and bought 0.9. A count of findings does marginally better
than the regression.

The mechanism is clear enough in hindsight. The floor existed to catch records the calibration
would misjudge, and the calibration misjudged thin records because the scorer had never seen one.
Fix the scorer and the calibration declines thin records on its own, leaving the floor to decline
records that were going to be declined anyway — at a cost of 140 cases per 1,000 going to a person
who did not need to see them.

It is still on. The reasons are in the README and only one of them is a measurement: it rescues a
badly-shaped rule (a per-group threshold goes from 13 of 21 scorer-fold cells to 15 of 21 with it),
it runs unfitted for a stranger's model, and answering a two-finding record because the arithmetic
cleared a bar is the behaviour this product exists to refuse. That last one is a judgement, it is
the one actually keeping the floor in the product, and the table above is the price of it.

**And the augmentation result held up on the control.** Same row count as the shipped scorer,
81.9% against 67.1% answering everything, so it is the holes and not the extra data. A bare
threshold on the better scorer still keeps the promise in **1 of 7** folds while answering 79% of
the stream: making the model better made the naive rule more dangerous, which is the most
counter-intuitive thing measured in this project and the one we would most like a reviewer to
check.
