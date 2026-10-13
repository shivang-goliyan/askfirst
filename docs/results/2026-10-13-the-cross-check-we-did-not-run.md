# MedQA was pre-registered as the cross-check, and we did not run it — 13 October 2026

`docs/METRIC.md` was written before the model was built and held MedQA out entirely, so that a
good result on DDXPlus could be checked against something that is not rule-based synthetic data.
Four files have been saying "MedQA is the cross-check" ever since. **It was never run, and there
is no `data/medqa` in this repo.** Two reviewers found that independently, which is the right
outcome for an unfulfilled promise and an embarrassing one.

## Why it was not run

Scoring MedQA needs a language model. There is no fitted classifier for it the way there is for
DDXPlus, because MedQA is exam-style prose with five options rather than coded findings over a
fixed outcome set.

On CPU the only feasible scorer would be something weak — bag-of-words similarity between the
vignette and each option, or a small model. **That is precisely the mistake that killed this
project's first headline.** A weak scorer makes abstention look spectacular: our original
`21.0% → 85.3% by refusing` came from a naive Bayes at 22.6% top-1, and the lift was a statement
about the baseline rather than about medicine
(`2026-10-13-the-scorer-was-the-bottleneck.md`). Running the cross-check on a deliberately weak
scorer would reproduce that error on the one dataset whose whole job is to be the honest check.

So it is GPU work, and the GPU has not arrived.

## What this costs the claims

**Everything measured in this repo is DDXPlus, and DDXPlus is rule-based synthetic.** A linear
model reaches 99.6% on complete records, which tells you how much structure the generator leaves
lying around. The completeness grid, the calibration, the missingness patterns, the advice
ranking and the throughput table are all measured on it.

The two results that are *not* DDXPlus are the variant work (CIViC, real curated evidence) and the
prose extraction (which is DDXPlus records rendered to notes, so no better). The claim that the
method generalises beyond one synthetic generator is **unsupported**, and no number in this repo
should be read as though it were.

## What would settle it

The cross-check as pre-registered: thin a MedQA vignette by removing sentences, score the five
options with the same open model on AMD, and check whether the same two things hold — that
accuracy falls as evidence is removed, and that refusing on a calibrated signal recovers
precision at a cost in coverage. It is one script and about an hour of GPU, and it is the first
thing after the AMD measurements in `docs/GPU-DAY.md`.

If the GPU day does not happen, this note stands as the answer: the cross-check was planned,
named in the pre-registration, and not done.
