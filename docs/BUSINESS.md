# Who pays, how much, and why they cannot take it with them

Both reviewers scored business value lowest, and both gave the same reason: cost scenarios are
not a revenue model. This is the revenue model. Every number in it is either measured in this
repo or sourced, and the ones that are neither are marked as assumptions.

## The buyer is an operator whose cost line is clinician-minutes

Not "healthcare". Specifically: **an organisation that already pays a clinician to look at cases
one at a time, whose model produces a rich differential over many conditions.**

> **That second clause was added on the evening of 13 Oct and it cost us most of the market this
> document used to claim.** Measured on 72,004 real emergency department visits, the gate does not
> work on a binary disposition call from a fifteen-field triage form: the posterior is almost never
> extreme, so a precision gate either answers nothing or answers the easy majority class, and at a
> 95% target it cleared 258 people who needed a bed. It needs a task with room in it — 49
> conditions and 223 findings, not a form and a yes/no. So a symptom-checker or a differential
> engine is a buyer and acuity-prediction-from-vitals is not, and that is now a measurement rather
> than a preference (`results/2026-10-13-the-real-queue-said-no.md`). Nurse triage lines, teleconsultation platforms, digital front doors, and the
symptom-checker vendors who sell into them. Three properties make them the buyer:

- **They already have the cost.** A reviewed case costs them money today — C$10–27 per triage
  call (CCOHTA Technology Report 43, 2003). Nothing has to be invented for the saving to land.
- **They already have the queue.** A refusal needs somewhere to go. These operators have a person
  at the other end; a hospital EHR vendor does not, which is why they are not the first customer.
- **They already carry the liability.** A confident wrong call is their problem, and the expected
  cost of one is $4,220 to $167,000 (`2026-10-13-what-it-is-worth.md`).

## The named operators who have this problem, and the published evidence that they do

"Nobody has bought this" is still true and it is the last section of this document. What was also
true until tonight is that nobody had been *named*. This is the evidence that the failure this
product addresses is a documented property of deployed systems rather than a problem we inferred
from a synthetic dataset. Everything below was read at source this evening; where a figure is a
vendor's own claim rather than peer-reviewed, it says so.

### 1. Healthdirect Australia — the clearest case, and it is the operator's own paper

Australia's national health line runs an AI virtual triage and care referral engine (Infermedica's)
with a nurse behind it. Their published evaluation covers **1,552,592 encounters**, 1 April 2023 to
31 March 2025, across every state and territory except Queensland. Nurses agreed with the engine's
acuity recommendation in **83.3%** of encounters, and *"where they did not agree, nurses generally
set a higher triage level."*

Then the sentence that is this product's entire market, written by the operator about its own
system:

> *"This warrants further investigation, given that VTCR is configured to overtriage to minimize
> patient risk."*

A deployed engine at national scale is **deliberately set to over-escalate**, because nobody has
measured how far it can be trusted on an incomplete record. That is a calibrated refusal layer's
job description. (*Mayo Clinic Proceedings: Digital Health*, 2026; figures confirmed via
[Medical Republic](https://www.medicalrepublic.com.au/ai-triage-works-sending-people-to-the-right-care-healthdirect-finds/123169),
primary article at ScienceDirect `S2949761225001385`.)

It is also the right *shape* of buyer by our own measurement: Infermedica's engine returns a
ranked condition list with probabilities, which is a rich differential — the thing the real-queue
experiment showed this gate needs (`results/2026-10-13-the-real-queue-said-no.md`).

### 2. Consumer symptom checkers, measured getting *more willing to answer* over five years

Schmieding et al. re-ran Semigran's 2015 audit on the same 45 vignettes five years later
(*J Med Internet Res* 2022;24(5):e31810). Median triage accuracy barely moved — 59.1% in 2015,
**55.8%** in 2020. What moved was the trade:

| the median app, same 45 vignettes | 2015 | 2020 |
|---|---|---|
| sensitivity on emergencies | 85.7% | **51.9%** |
| specificity | 82.1% | **93.3%** |

Emergency sensitivity fell **33.8 points** while specificity rose 11.2. The abstract's own summary
is *"missing >40% of emergencies."* Across a cohort of deployed consumer products, over five
years, the industry became **more confident and less safe in exactly the direction this gate
refuses in.** Nobody had to be persuaded that the problem exists; it was measured twice, five years
apart, by people with no stake in our answer.

(Semigran et al., *BMJ* 2015;351:h3480 established the baseline: 23 checkers, 45 vignettes,
appropriate triage advice ranging 33%–78% across checkers. A figure of "86 of 202 emergency
evaluations under-triaged" circulates for the 2022 follow-up; it is a calculation from Table 3 and
**not** something the authors report, so it is not quoted here.)

### 3. The frontier models being put in front of patients

Offered an explicit `INSUFFICIENT` option, a frontier model took it 0% of the time on a complete
record and 35% on a tenth of one, answering 92.5% of the time at 40% evidence while right 15.1% —
and at higher reasoning effort it abstained **less** and was right less
(`results/2026-10-13-a-frontier-model-offered-the-door.md`, our own measurement, 750 calls, $3.20).
This is not a claim about diagnosis. It is a claim about refusal, and it is the one capability that
does not arrive with a better model.

### Who is *not* the buyer, now that we have measured it

- **Deterministic protocol lines** — NHS Pathways, Schmitt-Thompson, Pharmacy First. No posterior,
  nothing to calibrate. They were in an earlier draft of this document and they should not have
  been.
- **Acuity prediction from vitals.** Measured and rejected on 72,004 real ED visits: the data's
  own ceiling is 94.0% precision at 1.0% recall, so a 95% bar does not exist there for any rule
  (`results/2026-10-13-the-real-queue-said-no.md`).

### What this evidence is and is not

It establishes that **named operators run probabilistic triage engines at scale and that those
engines are documented over-escalating or under-detecting.** It does **not** establish that any of
them would buy this, that they have budget, or that they would let a student team near their queue.
No approach has been made to anyone named here, and nothing on this page should be read as a
relationship. It moves the demand case from "we think this matters" to "three independent published
sources say this exact failure is happening in production", which is a real step and not a customer.

## What they buy, in one sentence

**A gate in front of whatever they already use, which answers the share of the queue it can hold
to a precision they set, and hands the rest over with a ranked list of what to ask next.**

It does not replace their triage model, their protocol or their clinicians. It decides which cases
need the expensive one.

Until today that sentence was a claim the code did not support — the gate only ran against our own
scorer. It is now `POST /api/gate`: send a record and your model's confidence. The two
record-level checks work on the first call with nothing fitted, because they read the record
rather than the score, and so does the what-to-ask-next list. The precision promise needs a fit
against their history (`scripts/fit_gate.py`), and an unfitted caller is told that rather than
handed a borrowed curve. **The thing they pay for is the fit, which is also the reason they
cannot take it with them** — see below.

## The unit economics, measured rather than modelled

| per 1,000 records | |
|---|---|
| never reach a person | **352** (measured, at a 95% bar, on records of undeclared completeness) |
| answered wrongly | **1.7** (against 330.5 if everything is answered) |
| review capacity returned | **C$3,500 – C$9,500** at C$10–27 a call |
| **cost to serve** | **$0.0004** |

The cost line is the one that is easy to miss. An assessment is 44.5 ms of CPU — 47 ms on the
thinnest records, which are the slowest because the gate does more work before giving up — with
no GPU, no model call and 142 MB resident. On the commodity instance this is already deployed to,
a thousand assessments cost **four hundredths of one cent**. The product that returns thousands of dollars of
capacity per thousand records costs less than a cent to run per *million*.

That asymmetry is the business: **gross margin is a rounding error away from 100%**, and it stays
there whether a customer sends a thousand records a month or ten million.

## Pricing

Price on capacity returned, not on volume consumed, because the value scales with their clinician
cost and the cost to serve does not scale at all.

**C$500 per 1,000 assessed records**, roughly 5–15% of the capacity returned at the measured
rates. A customer running 50,000 records a month pays C$25,000 and gets back C$175,000–475,000 of
review capacity. Our cost to serve that volume is **under three cents**.

Two things follow. There is no usage tier where this becomes unprofitable. And there is a lot of
room to discount into a first reference customer without the model breaking, which matters when
nobody has bought it yet.

## Why they cannot take it with them

This is the part we did not have until today, and it came out of a limitation rather than a
feature.

**The calibration has to be fitted against the way records go short where it runs.** Measured:
records do not go missing at random, and a calibration fitted on the wrong missingness pattern
loses about **1.1 points** of precision on the likeliest shape a rushed intake takes — 92.5%
against 93.6%, with intervals that overlap ([90.2%, 94.3%] against [91.2%, 95.4%])
(`2026-10-13-missing-not-at-random.md`). Seven realistic patterns span a 54-point range in
accuracy at the same nominal completeness.

So the deployed product is not a model you can copy. It is a model **fitted to one operator's
intake behaviour**, and it gets better as their records accumulate. A competitor arriving a year
later does not inherit that, and neither does the customer if they leave. We did not design that
moat; we measured it while trying to work out why one cell was failing.

It is now a file rather than an argument. `fit_gate.py` writes a completeness estimator fitted to
that operator's missingness, and `/api/gate` uses theirs instead of ours when it exists: on the
same twelve-finding record the shipped estimate says 61% of a record is present and the worked
example says 74%, because the two were fitted against intakes that go short differently. The
number the floor compares against is therefore theirs, and it is the artifact that leaves with
the contract.

## What would have to be true, and is not yet

**A reference customer.** Nobody has bought this. There is no letter of intent, no pilot and no
conversation, and the 352-per-1,000 figure is measured on synthetic patients rather than on
anyone's queue. That is the single biggest gap in this document and pretending otherwise would
be the same error the product exists to catch.

**That the precision bar holds on their data.** It holds on seven missingness patterns here. A
pilot is the only way to know whether an eighth one breaks it, and the honest sales motion is to
fit on a month of their historical records and report the grid back before anyone signs anything.

**A regulatory posture.** This is triage support with a human takeover, not a diagnostic device,
and the refusal is the product rather than a disclaimer. That is the right side of the line in
most jurisdictions and it is not legal advice; it needs a real answer before a real customer.

## The honest summary

The cost side is measured and extraordinary. The value side is measured on synthetic data and
sourced prices. The demand side is unproven. A judge should mark this as a credible unit-economics
case with no customer evidence, because that is exactly what it is.
