# The comparison was rigged, and we are the ones who rigged it — 13 October 2026

`scripts/run_conformal.py` · `docs/results/conformal.json`

## What we published this morning

> Under missingness shift — fit on six patterns and test on the seventh — **Mondrian falls to
> 92.7% and stops keeping its word; ours holds at 98.9%.**

That is retracted. Not because the conclusion was wrong, as it turns out, but because the
experiment could not have told us either way.

## What was actually wrong with it

The shift test refitted the baselines on six missingness patterns and tested them on the
seventh. Then it scored *our* rule on the same held-out pattern — using the shipped calibrator,
loaded off disk at `run_conformal.py:92`, which `run_calibration.py:165` had fitted against **all
seven**, the held-out one included.

So the baselines were asked to generalise to a pattern they had never seen, and we were asked to
recognise one we had been trained on. The 98.9% was a measurement of having seen the answer. A
reviewer found it in about twenty minutes by reading two files side by side, which is roughly how
long it should take.

The ugly part is why it survived. The number agreed with what we expected, and a number that
agrees with you does not get audited.

## The experiment redone, four ways harder

Every change below makes the comparison worse for us:

- **Every component is refitted per fold, ours included.** Nothing is loaded off disk. Whatever
  the fold's fit split has not seen, no rule has seen.
- **All seven leave-one-pattern-out folds**, rather than the one that flattered us.
- **The baselines are offered our completeness floor.** If the floor is the whole trick, giving
  it away should erase the gap.
- **At matched coverage the baseline may pick its operating point on the test ranking**, which
  no deployable rule can do and we never do.

Intervals are bootstrapped over patients rather than Wilson over rows, because five levels times
seven patterns is thirty-five views of each person and Wilson would treat them as thirty-five
independent observations. 2,000 patients per split, 70,000 rows each.

## In distribution: every rule fitted on all seven patterns

| rule | precision | queue taken | clustered | 95% promise |
|---|---|---|---|---|
| one global threshold | 94.9% | 57.0% | [94.4%, 95.4%] | **broken** |
| a threshold per group (Mondrian partition) | 96.2% | 52.9% | [95.7%, 96.6%] | kept |
| a threshold per group + the same floor | 97.0% | 46.3% | [96.6%, 97.4%] | kept |
| **ours: isotonic in-group + the floor** | **99.5%** | **35.8%** | [99.2%, 99.6%] | kept |
| the floor alone, no calibration | 93.7% | 51.8% | [93.2%, 94.1%] | **broken** |

The partition is doing real work — a single global threshold misses the bar that a per-group
threshold clears. That is the Mondrian idea earning its place, and it is not ours.

## Under shift: seven folds, everything refitted

| rule | worst fold | folds that kept the promise | mean coverage |
|---|---|---|---|
| one global threshold | 92.3% | 4 of 7 | 57.1% |
| a threshold per group (Mondrian partition) | 91.3% | 5 of 7 | 54.3% |
| a threshold per group + the same floor | 92.7% | 5 of 7 | 47.2% |
| **ours: isotonic in-group + the floor** | **98.5%** | **7 of 7** | 36.0% |
| the floor alone, no calibration | 88.1% | 3 of 7 | 52.3% |

The conclusion survived a fair test. Ours is the only rule that keeps a 95% promise in all seven
folds, and its worst fold is 98.5%.

**And the floor is not the whole trick.** Handing it to the per-group threshold takes that rule
from 5 of 7 to 5 of 7 — it moves the worst fold from 91.3% to 92.7% and still breaks twice.
Neither piece is sufficient alone: the floor alone keeps 3 of 7, the partition alone keeps 5 of
7, and the two together keep 7 of 7. That is the answer to "isolate the floor", and we only have
it because somebody asked.

## The finding that costs us something

| | precision | queue taken |
|---|---|---|
| ours: isotonic in-group + the floor | 99.45% | 35.8% |
| the raw margin ranking, stopped at our coverage | 99.46% | 35.8% |

Stop the uncalibrated margin ranking at exactly the coverage we chose and it is **just as
precise**. The isotonic calibration is not buying ordering. The ranking was already fine.

What the calibration buys is the *stopping point* — a cut-off chosen without being shown the
answers. That sounds like a technicality until you notice it is the entire problem: the raw
ranking in that row was allowed to read the test set to find its cut-off. Every rule in the
tables above that had to choose blind, except ours, broke the promise at least twice in seven
folds.

So the honest claim is narrower than "our calibration is more accurate". It is: **the ranking was
never the hard part. Choosing where to stop it, on a record whose shape you have not seen before,
is the hard part, and it is the part that fails silently.**

## What this costs in coverage, stated plainly

We take 36.0% of the queue where a per-group threshold takes 54.3%. At a 95% bar we are leaving
roughly 180 cases per 1,000 with a person who did not strictly need to be there — and in exchange
the promise holds in seven folds out of seven instead of five. Whether that trade is the right
one is a buyer's decision and depends on what a wrong answer costs them, which is the subject of
`2026-10-13-what-it-is-worth.md`. We over-deliver precision; a per-group quantile targeted at
exactly 95% would convert some of that surplus back into coverage, and that is still the open
engineering item it was this morning.

## On the word "conformal"

`threshold()` picks the quantile of the calibration scores whose accepted set hits a target
accuracy. That is standard selective prediction over a Mondrian-style partition. It is **not** a
conformal prediction set and it carries no conformal coverage guarantee: conformal guarantees
marginal coverage of a *set*, and what a buyer here asks for is precision conditional on having
answered, which is a different quantity (Angelopoulos & Bates, arXiv:2107.07511; Vovk, Gammerman
& Shafer 2005 for the partition). The earlier write-up implied these results showed conformal
guarantees failing. They do not. They show that the practical construction everyone actually
deploys breaks under missingness shift, which is a claim about practice, not about the theorem.

## What a reader should take from this

Two numbers we published this morning were worthless and we have withdrawn them. The replacement
is a harder experiment that we would have had no way of surviving if the idea were wrong, and one
of its rows says the calibration does less than we have been claiming.

That is the second time in two days that a result here collapsed when it was made reproducible,
and both times the tell was the same: it was built in a hurry and it agreed with us.
