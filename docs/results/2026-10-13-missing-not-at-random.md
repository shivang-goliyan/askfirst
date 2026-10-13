# "20% of a record" is not one thing — 13 October 2026

Every measurement in this repo until now hid evidence **uniformly at random**. That is the
easiest possible assumption and it is not how anything goes missing. An intake that runs out of
time gets through the standard questions and not the follow-ups. A walk-in has symptoms and no
history. A triage note says there is pain and not where it is.

Each of those removes a different *kind* of evidence. So: same 6,000 held-out patients, same
scorer, the same **number** of findings taken away every time, and only the choice of which ones
changes.

## The headline grid is not one curve, it is seven

Top-1 accuracy answering everything:

| how the record got cut short | 100% | 60% | 40% | 20% | 10% |
|---|---|---|---|---|---|
| at random *(what we had been measuring)* | 99.6% | 96.2% | 82.4% | 39.7% | 17.3% |
| the detail goes, the screen stays | 99.6% | 95.7% | 87.9% | 36.4% | 12.9% |
| **only the detail survives** | 99.6% | 96.5% | 89.0% | **73.2%** | 35.1% |
| no history, symptoms only | 99.6% | 97.8% | 86.7% | 45.1% | 20.5% |
| history only, nothing current | 99.6% | 94.1% | 68.2% | 19.2% | 9.1% |
| **standard questions, no follow-ups** | 99.6% | 94.8% | 68.7% | **19.6%** | 2.8% |
| only what was volunteered | 99.6% | 96.3% | 89.1% | 55.0% | 16.8% |

At a fifth of a record the answer ranges from **19.6% to 73.2%** depending only on *which* fifth.
Uniform thinning sits in the middle of that range, which is lucky rather than principled — it was
never argued for, it was just the obvious thing to write.

Two things fall out of this that we did not go looking for.

**It confirms the breadth result from a completely different direction.** Keeping only the wide,
graded fields and throwing away every binary screen is the best way to lose 80% of a record:
73.2% against uniform's 39.7%. Keeping the questions everyone gets asked is the worst: 19.6%. The
advice engine ranks exactly those graded fields first, and it was not tuned on any of this.

**History alone is nearly worthless here.** 19.2% at a fifth of a record against 45.1% for
symptoms alone. DDXPlus is synthetic and that number should not be carried anywhere near a real
clinic, but within this benchmark the asymmetry is large and consistent.

## Does the calibrated refusal survive it?

The rule from `2026-10-13-the-page-stops-asking.md`: calibrate P(right) against the record, refuse
below 35% estimated completeness. Fitted against all seven patterns — the **patients** are held
out, the patterns are not, and the next section is the honest version of that.

| how the record got cut short | 100% | 60% | 40% | 20% | 10% |
|---|---|---|---|---|---|
| at random | 99.9% | 99.4% | 98.8% | silent | silent |
| the detail goes, the screen stays | 99.9% | 100.0% | 98.7% | *(1 case)* | silent |
| only the detail survives | 99.9% | 98.5% | 96.5% | silent | silent |
| no history, symptoms only | 99.9% | 99.2% | 98.9% | silent | silent |
| history only, nothing current | 99.9% | 99.2% | 98.6% | silent | silent |
| standard questions, no follow-ups | 99.9% | 97.8% | **93.6%** | silent | silent |
| only what was volunteered | 99.9% | 99.9% | 99.2% | silent | silent |

Thirty-three of thirty-five cells keep the promise or go silent. The worst, 93.6% on 547 answered
cases, has a 95% interval of [91.2%, 95.4%] — it includes the target, so the promise is not
broken, but it is the one cell that comes near it, and it is the likeliest pattern of all.

## What happens if that pattern was never in the fit

Refit with *"standard questions, no follow-ups"* removed entirely, then test on it:

| | 40% evidence | interval |
|---|---|---|
| fitted against all seven patterns | 93.6% | [91.2%, 95.4%] |
| that pattern held out of the fit | **92.5%** | **[90.2%, 94.3%]** — excludes the target |

And the ladder underneath it. **This table replaced an earlier one and the correction matters**,
so the first version is below it.

| the pattern is in the fit | the calibration knows how unusual the findings are | result |
|---|---|---|
| no | no | 91.5% |
| no | yes | 92.5% |
| yes | no | 92.9% |
| yes | yes | **93.6%** |

Each ingredient helps a little, they help more together, and **together they still do not reach
95%.** The honest reading is that this cell is the limit of the method rather than something we
fixed. The shipped rule under-delivers on the likeliest missingness pattern at 40% evidence by
about a point and a half, with an interval of [91.2%, 95.4%] that still contains the target.

The feature is how unusual the findings in hand are: the average of `1 − P(this question gets
answered)` over the record. A record holding only the questions everyone gets asked says much
less than one of the same size holding things a patient volunteered, and a count cannot tell them
apart. It is worth about a point, which is worth having and is not a fix.

### The version of this table that was published first, and was wrong

The first ladder here read 91.2 / 91.0 / **89.9** / **95.3**, and the paragraph under it claimed
that training on the pattern without the feature was *worse than not training on it at all*, and
that the two together restored the promise. Neither survives.

Those numbers came from a throwaway probe that used a different subset of patterns for the
held-out fit and different band edges, and was never run from the script in this repo. When the
ladder was added to `run_missingness.py` so anyone could reproduce it, the effect vanished: the
real relationship is monotonic and modest.

A headline built on a script that only existed in a scratch directory is a headline nobody can
check, including us. That is the whole failure mode this project is about, and it is the second
time it has happened here — see the `max()` tie-break in
`2026-10-13-breadth-beats-information.md`. The ladder is now computed by the same script that
prints the tables above it.

## What this means for anyone deploying it

**Fit the calibration against the way records go short where it will run.** Not against uniform
thinning, which is what every version of this before today did. The cost of getting that wrong is
measured above: about two points of precision on a promise of ninety-five, on the single likeliest
shape a rushed intake takes — and fitting it right recovers most but not all of that.

The floor does the rest of the work. At a fifth of a record and below, every pattern goes silent,
including the ones where top-1 is 73% and it would have been tempting to answer.

## What this does not say

Seven patterns are seven guesses at how records go missing, written by us. They are not measured
against a real intake, because we do not have one. They span the space well enough to show the
spread is large and to break our own rule once, which is what they were for.

DDXPlus is rule-based synthetic. The *direction* of each row is believable; the size of the gap
between them is a property of this generator.

Uniform thinning remains the number quoted in the headline grid, because it is the one measured
on 6,000 patients across five levels with intervals, and because it sits mid-range rather than
flattering us. Every other row here is now in the repo next to it.

## Reproducing it

    python3 scripts/run_missingness.py data/ddxplus/release_validate_patients

About eight minutes on a laptop CPU, including the refit for the held-out-pattern test.
