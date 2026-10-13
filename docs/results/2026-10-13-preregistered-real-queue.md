# Pre-registration: the gate on a real emergency department queue — 13 October 2026

**Written before the first number exists.** Committed before `run_nhamcs.py` is run even once.

Every measurement in this repo so far is DDXPlus: synthetic patients, and records cut short seven
ways *we chose*. The sharpest criticism of it, made twice today by two different reviewers, is
that the mixture is manufactured — 90.7% of the accepted cases in the headline come from the two
fullest completeness levels, and nothing argues that any of it resembles a real intake queue.

So: a real one. And the reason this document exists is that we have already had two results
collapse today when they were made reproducible, and both times the tell was that the number
agreed with us. This time the bar is set first.

## The data

**NHAMCS** — the CDC's National Hospital Ambulatory Medical Care Survey, Emergency Department
component. Public use files, no registration, no credentialing: `ed2018.zip` … `ed2022.zip` from
`ftp.cdc.gov/pub/Health_Statistics/NCHS/Datasets/NHAMCS/`, with the record layout parsed out of
the documentation PDFs by `scripts/nhamcs_layout.py` (the declared field widths sum to 2,458 for
2018 and 2,382 for 2022, matching the actual record length in each data file byte for byte, which
is how we know the layout is right).

Roughly **70,000 real emergency department visits** across four years.

**Use restrictions, honoured.** The NCHS data use agreement permits statistical reporting and
analysis only, forbids any attempt to identify a person or establishment, and forbids linking the
file to individually identifiable data. Fitting and evaluating a triage gate is statistical
analysis. We do not link, we do not re-identify, the data is not committed to this repository, and
no national estimate is quoted anywhere — NHAMCS is a weighted survey and `PATWT` exists for
estimates we are deliberately not making.

## What is being decided

Not a diagnosis. **Escalation**: from what is charted at triage, does this visit need a bed?

`escalated` = admitted to this hospital (`ADMITHOS`), admitted to observation and then
hospitalised (`OBSHOS`), transferred to another hospital (`TRANOTH`), or died in the ED
(`DIEDED`). Everything else is discharged.

Predictors are **triage-time fields only**: age, sex, arrival by ambulance, the first three
reason-for-visit codes, six vitals (temperature, pulse, respiratory rate, systolic and diastolic
blood pressure, pulse oximetry), pain score, triage immediacy, and seen-here-in-the-last-72-hours.
Nothing from the visit itself — no labs, no imaging, no length of stay, no disposition-adjacent
field.

## Why this is the right test and not a flattering one

**The missingness is not ours.** A vital is missing because nobody charted it. In the 2022
documentation that runs from 5.3% (respiratory rate) to 44.0% (pain score), with triage immediacy
blank on 27.8% and explicitly *not imputed since 2012*. CDC imputes only age, sex, race and
ethnicity, each with a flag; we use none of those four as features except age and sex, and we
report that. Nothing in the feature table is manufactured, and none of the seven patterns we
invented applies.

**The shift is not ours either.** Fit on **2018–2019**, test on **2021–2022**. That is a real
case-mix shift across the pandemic, chosen because it is the first distribution shift in this
project that we did not cut ourselves.

**The intervals cluster on hospitals.** `HOSPCODE` (1–188) identifies the site. Missingness in
this file is site-driven — some hospitals never chart pulse oximetry — so resampling visits
would understate the uncertainty badly. The bootstrap resamples **hospitals**.

## Two things that will be different, stated now

1. **The completeness estimator may be unnecessary here, by construction.** The ridge regression
   exists because a DDXPlus record has a variable true length, so "how much is missing" has to be
   estimated. An NHAMCS triage form has a *fixed* applicable field set, so completeness is
   directly observable: charted divided by applicable. If the ridge adds nothing on this data
   that is not a failure of the gate, it is a limit on how general the estimator is, and it goes
   in the write-up in those words.
2. **The base rate does the work if we let it.** Discharge is the large majority class, so
   "answer everything, predict discharge" is already precise. Every number below is reported
   **separately for the escalation side**, and always beside the raw-margin cut at equal
   coverage. A headline that only works because most people go home is not a headline.

## The bar, set now

**A WIN requires all four.**

1. **The promise holds under real shift.** Fitted on 2018–2019 and tested on 2021–2022, at
   `target: 0.95`, precision on accepted **escalation** calls ≥ 95% with a hospital-clustered
   lower bound ≥ 93%, at coverage ≥ 10% of escalations.
2. **The calibration buys ordering where it should.** Inside the same eligibility and at equal
   coverage, ranking by the calibrated probability beats ranking by the raw margin by ≥ 1 point
   on the **sparse stratum** (three or fewer of the six vitals charted). This is the row that
   cost us on DDXPlus, where it bought nothing on a well-behaved scorer. On real, site-driven
   missingness it should buy something. If it does not, say so.
3. **The gate refuses where the record is thin.** Refusal rate on charts missing three or more
   vitals is at least **twice** the refusal rate on fully charted visits.
4. **Thin charts are genuinely harder.** Answering everything, precision on sparse charts is
   measurably below precision on full charts. If it is not, the completeness floor is dead weight
   on real data and the write-up says that.

**A LOSS is any one of these, and each gets published as the headline of its own section:**

- The promise breaks on 2021–2022 → *"the gate does not survive a shift we did not choose."*
- The raw margin matches the calibration within 0.5 points everywhere, sparse stratum included →
  *"on a real queue the calibration bought only the stopping point."*
- Sparse charts are no less accurate than full ones → *"missingness did not cost accuracy here,
  and the floor is unnecessary on this data."*
- Coverage at a 95% escalation bar is under 10% → *"on a real queue it is too conservative to be
  worth deploying at this target."*

**None of these four may be used to excuse another.** Failing (4) does not make (2) optional.

## What this still will not show

No clinician has reviewed any of it. NHAMCS is abstracted from the chart after the visit, so
"missing" means "not documented", which is related to but not the same as "not known at the time
of triage". A hospital-clustered interval on 188 sites is still one country and one survey
instrument. And a gate that works on NHAMCS escalation is not a gate that is safe to deploy — it
is a gate that survived one honest test on real records.
