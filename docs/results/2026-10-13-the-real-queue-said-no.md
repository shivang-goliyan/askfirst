# The real queue said no — 13 October 2026

`scripts/run_nhamcs.py` · `docs/results/nhamcs.json` · bar set in
`2026-10-13-preregistered-real-queue.md`

## The result, first

**One of four pre-registered conditions met. By our own bar, set before this ran, that is a
loss.**

| | |
|---|---|
| 1. the promise holds under real shift | **not met** |
| 2. the calibration buys ≥1 point of ordering on sparse charts | **not met** |
| 3. the gate refuses sparse charts at ≥2× the rate | **not met** |
| 4. sparse charts are genuinely harder | met |

And the number that matters more than any of them: at a 95% target, of the **11,052 visits this
gate cleared to go home, 258 needed a bed.** That is 2.3% of the cleared visits and **5.5% of
every escalation in the two test years.** On this task, on this data, this is not deployable, and
no amount of framing changes that.

## What was run

72,004 real emergency department visits from the CDC's NHAMCS public use files. Fitted on
**2018–2019** (39,772 visits, 439 sites) and measured on **2021–2022** (32,232 visits, 374 sites,
none shared with the fit years — `HOSPCODE` is reassigned annually). Intervals bootstrap over
**hospitals**, because missingness here is site-driven.

The shift is real and it is not one we chose: escalations run 13.3% in the fit years and 14.7% in
the test years, and fully-charted visits fall from **43.3% to 39.1%**. The charting got worse
across the pandemic.

The decision is escalation, not diagnosis — from the triage form alone, does this visit need a
bed — where escalation means admitted here, admitted to observation and then hospitalised,
transferred out, or died in the department. Features are triage-time only: age, sex, arrival by
ambulance, three reason-for-visit codes, six vitals, pain score, triage immediacy, and
seen-here-in-72-hours. Nothing from the visit itself.

## Why it failed, which is the useful part

The failure is **not** the gate. It is the task, and we found that out by measuring the ceiling
rather than guessing at it.

**AUC for escalation from the triage form alone: 0.8214.** That is a working scorer, right where
the literature on triage-field admission prediction sits. But look at what any rule can reach on
this data, by sweeping every possible threshold on P(escalated):

| flag the top | precision | recall |
|---|---|---|
| 25 | 100.0% | 0.5% |
| 50 | 94.0% | 1.0% |
| 100 | 93.0% | 2.0% |
| 250 | 84.4% | 4.5% |
| 500 | 79.4% | 8.4% |
| 1,000 | 71.3% | 15.1% |

**A 95% escalation bar at 10% coverage does not exist on this data for any rule.** At 10% recall
the ceiling is about 79%. Our pre-registered condition 1 asked for something the data cannot
supply, and the honest reading is that **we set a bar we had no business setting** — we had no
measurement of this frontier when we wrote it down, and we should have measured the frontier
first and then set the bar underneath it.

Our gate's escalation side (11 flagged, all 11 correct) sits *on* that frontier, at the extreme
conservative end of it. It is not underperforming the data. The data has nothing else to give.

## What the gate actually does on a real queue, and why that is not enough

It becomes a **discharge certifier**. It accepts 34.3% of visits, 11,052 of which it clears to go
home, at 97.7% [97.3%, 98.0%] clustered on sites.

Against a base rate of 85.3% — always say "went home" — that is twelve points better, and
answering everything with the scorer gets 86.8%. So the gate is doing real work.

It is still not safe, for one reason that no table can soften: **258 of those cleared visits were
admissions, transfers or deaths.** A nurse triage line that cleared 11,052 people and sent 258 of
them home when they needed a bed has not saved anybody money. The product's whole claim is that
a confident wrong answer is the expensive thing, and here it produces 258 of them.

## The other three conditions, briefly

**Ordering bought nothing.** Inside the same eligible pool, at the same size, ranking by the
calibrated probability against ranking by the raw margin: **−0.03 points** overall and **+0.36**
on the sparse stratum, against the +1.00 the pre-registration asked for. On DDXPlus the
calibration bought ordering only on a badly-shaped scorer; this one is well-shaped, so this is
consistent with that finding rather than new. It is still a miss.

**The gate does refuse thin charts more, but not twice as much.** 81.6% refused where three or
fewer of six vitals are charted, against 65.8% where all six are — 1.24×, not the 2× asked for.

**Thin charts are harder, barely.** 85.7% against 86.6% answering everything. Met, and by nine
tenths of a point, which is not the ringing confirmation the condition was written to detect.

## And the ridge, as pre-registered

The pre-registration said in advance that the completeness estimator might have nothing to do
here, because an NHAMCS triage form has a **fixed** applicable field set, so completeness is
*observed* rather than estimated. That is what happened: the ridge reproduces the directly
observable fraction with a mean absolute error of 0.0374, and the gate uses the observed one
because there is no reason to use an estimate of a thing you can count.

So the learned estimator is a DDXPlus artefact — it exists because a DDXPlus record has a
variable true length. Combined with
`2026-10-13-we-tried-to-delete-our-own-floor.md`, which found the floor is not what keeps the
promise on DDXPlus either, the honest position on the completeness machinery is now: **narrower
than we have been claiming, in two independent ways, both found by trying to break it.**

## What this changes about the product

This is the most useful thing in the repo and it is a negative result, so it is worth saying
plainly what it implies.

**The gate needs a scorer that can be certain, and that needs a task with room in it.** DDXPlus
gives 49 conditions and 223 possible findings; a confident, correct posterior is reachable there,
and the gate's job is to find the cases where it has been reached. A 15-field triage form over a
binary outcome does not have that room — at 14.7% base rate and AUC 0.82 the posterior is almost
never extreme, so a precision gate either answers nothing or answers the easy majority class.

So the buyer is narrower than `BUSINESS.md` claims. Not "an operator running a probabilistic
triage engine" — **an operator whose engine produces a rich differential over many conditions
from many findings.** A symptom-checker with a 50-condition output is in. Acuity prediction from
vitals is out, and we now have the measurement that says so rather than an opinion.

## What would have to be true for the escalation side to work

Named, not attempted, so nobody mistakes this for a plan:

- **Richer features.** Chief-complaint text rather than a code, and the vitals as numbers rather
  than the five bands used here. Bands were chosen for comparability across years and they throw
  away resolution exactly where the escalation signal lives.
- **A different target.** 95% precision on escalation is above the data's ceiling. A 75% bar at
  10% recall is reachable and might still be worth money to an operator; whether it is, is a
  question for an operator and not for us.
- **The other direction.** Certifying discharges is where the signal is. That is a real product
  and it needs a safety case built around a 2.3% miss rate, which is a different document than
  this one and probably a different team.

## Honest summary

We pre-registered four conditions on real data and met one. The gate did not fail relative to
what the data permits — it sits on the achievable frontier — but the bar we set was above that
frontier, and we only know that because we measured it afterwards. Meanwhile the thing it does do
on a real queue clears 258 people who needed a bed.

Every number in this repo before today was DDXPlus. The first time it met a real queue it did not
transfer, and the reason is informational rather than fixable by tuning.
