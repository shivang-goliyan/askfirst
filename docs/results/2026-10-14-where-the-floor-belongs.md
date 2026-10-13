# Where the floor belongs, and why "it buys nothing" was the wrong question — 14 October 2026

`scripts/run_floor_sweep.py` · `docs/results/floor-sweep.json`

`FLOOR = 0.35` was picked by hand, on the reasoning that below about a third of a record nothing
reaches a useful precision anyway. Two experiments then disagreed about whether it earns its keep,
and both of them were asking the wrong question.

## What the two earlier experiments said

`2026-10-13-we-tried-to-delete-our-own-floor.md`, re-run against the refitted scorer: the
calibration **alone** keeps the 95% promise in all seven missingness folds at 61.1% coverage;
adding the floor drops that to 47.2% and the worst fold does not move, 99.5% either way. Fourteen
points of coverage for no measurable precision.

`2026-10-13-is-it-a-layer-or-is-it-our-model.md`: the floor takes a badly-shaped per-group
threshold from 13 of 21 scorer-fold cells to 15 of 21.

Both are true. Neither says where the floor belongs, so this sweeps it.

## Getting the protocol right took three attempts, and the first two are the interesting part

**Attempt one** applied every condition to the test rows and picked the winner. That is choosing a
hyperparameter on the evaluation set, which is the thing this repo had already been caught doing
once the same day.

**Attempt two** fitted the calibration on one split and chose the floor on that same split. It
picked a floor of **zero** — and on held-out data a completeness level broke: at a tenth of a
record the no-floor rule landed at 97.41% with a lower bound of 94.50%, just under the bar. The
choice did not transfer.

**Attempt three**, which is what the script now does: the calibration is **fitted** on one split,
the floor is **chosen** on a second, and everything is **reported** on a third. 2,000 patients and
70,000 rows each.

At that sample size the choice does transfer. Floor zero holds every completeness level on both the
choosing split and the reporting split — the tenth-of-a-record cell is 97.54% [96.12%, 98.79%]
where it was chosen and 97.43% [96.07%, 98.59%] where it is reported — and every floor in the
sweep keeps all seven folds. So attempt two's failure was a small-sample artifact, and it would
have been published as a finding if the third split had not existed.

## The sweep

| floor | coverage | wrong answers in 70,000 rows | every completeness level holds |
|---|---|---|---|
| **0%** | **61.1%** | 104 | yes |
| 15% | 58.1% | 59 | yes |
| 35% *(ships)* | 46.6% | 33 | yes |
| 50% | 33.9% | — | yes |

Read on precision alone, the rule says take the floor off: 61.1% coverage against 46.6%, the
promise kept at every level, seven folds out of seven. Fourteen and a half more points of the
queue never reaching a person.

## And then price it, with this repo's own numbers

Precision was the wrong objective, and we had the right one written down three weeks of work ago.
At a **fixed precision target**, more coverage means more *absolute* wrong answers — the rate holds
and the count grows. The published prices say what that costs:

Per 1,000 records, removing the floor entirely:

| | |
|---|---|
| records that never reach a person | **+145** → C$1,452 – C$3,919 of review capacity returned |
| additional wrong answers | **+1.01** → $4,280 – $169,386 of expected cost |

**The extra wrong answers cost 1.1× to 117× what the saved reviews are worth.** The prices are
CCOHTA's C$10–27 per triage call and Newman-Toker × CRICO's $4,220–$167,000 for the expected cost
of a confident wrong answer, both from `2026-10-13-what-it-is-worth.md`, and neither invented here.

The halfway option does not rescue it: a 15% floor buys +116 handovers for +0.37 wrong answers,
which is roughly break-even at the bottom of the harm band and badly negative anywhere else.

## So the floor stays, and now for a reason

It stays at 0.35. Not on the safety judgement the README has been resting on since yesterday — on
the measurement: **at the published harm prices, no reduction in the floor pays for itself, and the
lower it goes the worse the trade.**

That also retires the sentence "the floor buys nothing measurable", which this project published
yesterday and which was wrong in an instructive way. It buys nothing in *precision*, which is what
the fold tables measure. It buys a great deal in *expected cost*, which is what a buyer has. A
precision target holds the rate fixed and lets the count of wrong answers float, and the count is
the thing that is expensive.

## What this does not settle

- **Every price in it is a published average applied to synthetic patients.** An operator whose
  real cost of a missed case is at the bottom of that band — a low-acuity queue where a wrong
  answer means an unnecessary callback rather than a missed infarct — would be right to lower the
  floor, and the table above is what they would gain. `FLOOR` is one constant in `calibrate.py`.
- **The sweep is on one scorer and one dataset.** The floor that pays on DDXPlus with a
  hole-trained softmax is not a universal constant, and `fit_gate.py` does not currently sweep it
  for a customer's own model. It should.
- **Nothing here was checked by anyone who treats patients.** The entire argument turns on a ratio
  between the cost of a review and the cost of a missed case, and that ratio is a clinical and
  actuarial question we have answered out of two papers.
