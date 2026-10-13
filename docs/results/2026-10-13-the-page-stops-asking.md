# The confidence was not a currency, and the page was asking the wrong person — 13 October 2026

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

**Calibrate on findings in hand.** Not on completeness — nobody knows that — on the count, which
every deployment has. An isotonic fit of P(right) against the margin, one per bucket of record
size. That alone gets:

| record | precision | coverage |
|---|---|---|
| 100% | 99.9% | 97.2% |
| 60% | 99.4% | 61.2% |
| 40% | 98.8% | 23.5% |
| 20% | **84.1%** | 1.4% |
| 10% | silent | — |

It keeps its word at three levels and is correctly silent at the thinnest. It breaks at 20%, and
the reason is structural: three findings might be three of three — a simple presentation, complete
— or three of fifteen. The count cannot tell them apart.

**Estimate how much is missing, and refuse below a floor.** Ridge regression from the record to
how many findings this patient would have had, which is a property of the illness rather than of
the intake, and so is learnable from the findings that did arrive. **Mean error 0.053 on a 0–1
scale.** Refuse outright below 35% estimated completeness, whatever the confidence says:

| record | precision | coverage | 95% interval |
|---|---|---|---|
| 100% | 99.9% | 96.9% | [99.85%, 99.98%] |
| 60% | 99.4% | 58.4% | [99.05%, 99.59%] |
| 40% | 98.6% | 15.6% | [97.63%, 99.18%] |
| 20% | silent | — | |
| 10% | silent | — | |

**Two mechanisms, and you need both** — the same conclusion module B reached from the other end,
where capping a predictor's strength only works if it also declines to speak when it has little
to say.

## What it is worth

30,000 records of mixed and undeclared completeness, which is what a deployment actually sees:

| | right | wrong | answered |
|---|---|---|---|
| answer everything | 67.1% | **9,874** | 100% |
| this rule | **99.6%** | **38** | 34.2% |

95% interval on the precision: [99.49%, 99.73%]. It hands over two cases in three and gets 38
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
