# The confidence was not a currency, and the page was asking the wrong person — 13 October 2026

> **Measured against the previous scorer.** On 14 October the scorer was refitted on records with
> holes in them, and the artifact this file reads from has been regenerated, so figures in the
> prose below may disagree with the JSON beside them. The prose is left as the record of what was
> measured when. What moved, and what it cost the argument, is in
> `2026-10-14-the-scorer-now-expects-holes.md`.
>
> **The motivating number is also smaller.** "40 points underconfident at 40% evidence" is 8.2
> points once the scorer has seen holes, so most of that gap was a training bug rather than a
> property of confidence under missingness. What survives is that one raw threshold still does not
> transfer across completeness.

The completeness grid is the headline result: how much to refuse depends on how much of the
record is in, by a factor of fifty. The app implemented that by **asking the visitor how complete
their record was** and reading the threshold off the curve for that level.

Nobody deploying this knows their record is 40% complete. That is the problem being solved, not
an input to it. So either one threshold works everywhere and the grid is a complication we
invented, or it does not, and we owe both an explanation and a way to pick the level without
asking. This is the measurement, and the fix.

6,000 held-out patients to fit on and 6,000 to test on, from past index 40,000 — the scorer was
fitted on the first 30,000 and the published curve measured on 30,000–36,000, so nothing here
touches either.

## The confidence is honest on a full record and badly wrong on a thin one

| record | top-1 | mean margin | ECE | |
|---|---|---|---|---|
| 100% | 99.6% | 98.2% | 0.014 | honest |
| 60% | 96.0% | 73.4% | 0.225 | **underconfident by 22.5 points** |
| 40% | 82.5% | 42.2% | 0.403 | **underconfident by 40.3 points** |
| 20% | 40.2% | 16.3% | 0.238 | underconfident by 23.8 points |
| 10% | 17.2% | 11.3% | 0.080 | underconfident by 5.9 points |

Underconfident, not over. A linear model's logits shrink as features drop out, so the margin
collapses while the argmax often survives. The direction is the safe one — it refuses too much
rather than too little — but the size is not survivable, because **the refusal threshold *is*
that number.**

## So one threshold cannot hold a promise

Pick the cut-off that delivers 95% precision on one level, then apply it to the others:

| chosen on | 100% | 60% | 40% | 20% | 10% |
|---|---|---|---|---|---|
| **100%** | 99.6% | 97.2% | 93.2% | **76.2%** | **48.1%** |
| 60% | 99.6% | 96.0% | **83.9%** | **48.7%** | **32.7%** |
| 40% | 99.6% | 97.6% | 94.4% | **79.0%** | **66.7%** |
| 20% | 99.7% | 99.2% | 98.6% | **87.8%** | **62.5%** |

A threshold chosen on complete records promises 95% and delivers 48% on a tenth of a record. One
chosen on thin records holds the promise and throws away almost every full record to do it. **The
grid is necessary, and now there is a number saying why** rather than a design decision.

## The fix, in two pieces, because one is not enough

**Calibrate on what is in hand.** Not on completeness — nobody knows that — on how many findings
there are and how unusual they are, both of which every deployment has. An isotonic fit of
P(right) against the margin, one per bucket. That alone gets:

| record | precision | coverage |
|---|---|---|
| 100% | 100.0% | 97.7% |
| 60% | 99.4% | 63.9% |
| 40% | 98.5% | 26.2% |
| 20% | **84.0%** | 2.2% |
| 10% | **52.6%** | 0.3% |

It keeps its word at the three fullest levels and breaks at both thin ones. It breaks at 20%, and
the reason is structural: three findings might be three of three — a simple presentation, complete
— or three of fifteen. The count cannot tell them apart.

**Estimate how much is missing, and refuse below a floor.** Ridge regression from the record to
how many findings this patient would have had, which is a property of the illness rather than of
the intake, and so is learnable from the findings that did arrive. **Mean error 0.057 on a 0–1
scale.** Refuse outright below 35% estimated completeness, whatever the confidence says:

| record | precision | coverage | answered | 95% interval |
|---|---|---|---|---|
| 100% | 100.0% | 97.4% | 5,845 | [99.9%, 100.0%] |
| 60% | 99.4% | 61.0% | 3,659 | [99.0%, 99.6%] |
| 40% | 98.2% | 16.2% | 971 | [97.1%, 98.8%] |
| 20% | — | 0.02% | **1** | one answered case, and it was wrong |
| 10% | silent | — | 0 | |

**Two mechanisms** (and a later experiment found the second one is optional on this scorer — see
the note at the end of this file) — the same conclusion module B reached from the other end,
where capping a predictor's strength only works if it also declines to speak when it has little
to say.

## What it is worth

30,000 records of mixed and undeclared completeness, which is what a deployment actually sees:

| | right | wrong | answered |
|---|---|---|---|
| answer everything | 67.1% | **9,874** | 100% |
| this rule | **99.6%** | **45** | 34.9% |

95% interval on the precision: [99.43%, 99.68%]. It hands over two cases in three and gets 45
wrong instead of 9,874, with nobody telling it anything about any of them.

## What changed in the product

The page no longer asks how complete the record is. It says what it thinks — *"looks about 23% of
a record"* — and the only dial left is the one a person has an opinion about: **how right does it
have to be?** When it refuses it now distinguishes the two reasons, because "not confident enough"
is the wrong thing to say when the real problem is that there is barely a record there:

> only about 23% of a record — too little to judge the answer by, whatever the confidence says

The completeness grid stays on the page above it. It is the finding; this is the product.

## What this does not say

The floor and the target were both chosen on the fit split and are reported on the test split, but
they are two numbers chosen by us and a different operating point would move every row here.

The calibrator is fitted against records thinned uniformly at random. Real records are not missing
at random — a rushed intake loses the expensive findings first — and that limit is stated in the
same place as before rather than fixed.

"Better than 99% likely to be right" is as strong as this will ever print. An isotonic fit pins the
top of its range at exactly 1.0, and a display that says *100% likely to be right* is the one
sentence this product must never produce.

## Reproducing it

    python3 scripts/run_calibration.py data/ddxplus/release_validate_patients

About six minutes on a laptop CPU. It writes the measurement to `docs/results/calibration.json`
and bakes the two pieces into `src/askfirst/baked/`.

---

**Later the same day: the floor turned out to be optional here.** This file argued that the
calibration and the completeness floor were two mechanisms and that both were needed. Then the
arm that removes the floor entirely was actually run, and the calibration alone keeps the 95%
promise in all seven leave-one-pattern-out folds while answering 40.3% of the stream against the
36.4% we ship. The floor buys 0.9 points of worst-fold precision for four points of coverage, and
a plain count of findings does nearly as well as the ridge.

It stays in, for reasons that are a judgement rather than a measurement, and those reasons are set
out in `2026-10-13-we-tried-to-delete-our-own-floor.md`. The claim that it was load-bearing is
withdrawn.
