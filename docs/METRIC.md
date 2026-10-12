# Evaluation, fixed in advance

> **Amended 13 October 2026.** Risk and coverage is now the PRIMARY metric; absent-field
> recovery drops to a sanity check. See `results/2026-10-13-the-refusal-works.md`. Recovery
> measures whether the system can guess what a patient probably had, which is not what the
> product claims. The original 30% top-3 kill criterion stays on the record as missed.

Written 12 October 2026, before any model was chosen or tuned. The point of writing it down now
is that the numbers below cannot be chosen later to flatter the result.

## Primary — absent-field recovery

Take a complete case. Delete exactly one field that the case's outcome depends on. Ask the system
to name what is missing. Score whether the deleted field appears at rank 1, and within rank 3.

Reported as top-1 and top-3 recovery, with a Wilson 95% interval, against the chance baseline for
the same case (one over the number of fields absent from that case).

On DDXPlus, with 110 symptoms and 113 antecedents, a typical case has around 210 absent fields, so
chance is roughly 0.5% at rank 1 and 1.4% at rank 3. There is a lot of room above that, and no
excuse for a weak result hiding behind a weak baseline.

## Secondary — flip rate

Share of cases where removing a single field changes the top outcome. Published so nobody has to
take the influence scores on trust: if the flip rate is near zero, the influence numbers are
measuring noise.

## Secondary — risk and coverage

Accuracy on the cases the system chose to answer, plotted against the share it chose to answer.
A refusal layer is only worth having if accuracy on the answered subset rises as coverage falls.

## Secondary — cost efficiency

Share of cases resolved to a decision, divided by the cost of the items the system asked for.
Compared against two baselines: ask for everything, and ask in a fixed standard order.

## Stability

Every reported figure is re-run with the inputs perturbed — paraphrase and field reordering for
text, and for any image input a rotation of plus or minus two degrees, a 3% crop and a 15%
brightness change. Cases whose verdict changes under a perturbation that preserves meaning are
counted as errors regardless of whether the original was right. This needs no labels.

## Splits

DDXPlus is split by patient before anything else happens, and the test split is not looked at
until the metrics above are final. MedQA is held out entirely as a cross-check, so that a good
DDXPlus result cannot simply mean the generator behind DDXPlus was reverse-engineered.

## Kill criterion

If top-3 absent-field recovery on the DDXPlus validation split is not at or above 30% by the end
of 14 October, the ranking approach is not working and the design gets reconsidered rather than
polished. Twenty times the chance baseline sounds generous until you remember that a clinician
with a textbook would be near ceiling.

## What will not be claimed

- No clinical validity. No clinician reviews these outputs.
- No diagnosis, and no therapy recommendation, in either module.
- No claim that performance on synthetic cases transfers to real records.
