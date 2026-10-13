# Is the computational line load-bearing? — 13 October 2026

The previous result measured what ESM-2 *says*. This one measures whether it should be allowed to
say it, by putting the score into a CIViC group as one removable evidence item and asking the only
question that matters at a tumour board: **does the call change when you take it away?**

The 2015 ACMG/AMP framework used computational evidence at *supporting* strength. **An earlier
version of this note said ACMG "caps" it there and that is wrong**: ClinGen's 2022 calibrated
recommendations explicitly permit stronger weights — up to strong — for predictors that have been
calibrated against a reference set for the purpose.

That makes the argument here narrower and better specified. An ESM-2 masked-marginal score has not
been calibrated for this purpose, by us or by anyone, so *supporting* is where an uncalibrated
predictor belongs — not because a guideline forbids more, but because nothing has earned more.
Strength is the independent variable and the sweep below is the experiment.

**Read the counts, not the percentages.** The samples are 6 to 20 groups. That is too small to
carry a headline and the percentages are printed only because they are easier to compare across
rows.

## First result: most of the time it has no vote at all

| | |
|---|---|
| CIViC groups with 2+ evidence items | 585 |
| contested — the group's own evidence disagrees with itself | 182 |
| of those, where the variant is a plain single substitution we can score | **28** |
| and where the score clears \|llr\| ≥ 2.0 | **11** |

**171 of 182 contested groups — 94% — cannot receive a computational vote at all.** Either the
variant is a fusion, an exon-level call or a bare position with no alternate residue, or the model
is not surprised enough to be saying anything. That is measured rather than argued, and it is the
honest size of this evidence line's reach on the cases people actually fight about.

## The sweep: strength decides everything

Same line, same score, same groups. Only the strength it is granted changes.

| strength granted | calls changed (of 11) | predictor ends up on top |
|---|---|---|
| **E — supporting, where an uncalibrated predictor belongs** | **0** | 0 |
| D — case report | 2 | 2 |
| C — preclinical | 4 | 4 |
| **B — clinical, roughly how predictors get used in practice** | **5** | 5 |
| A — validated | 9 | 9 |

**At the strength ACMG actually permits, nothing moves. Granted clinical strength, it changes
nearly half the calls — and every single time, the computational label itself ends up on top of
the distribution,** outranking the documented clinical evidence in the same group. The cap is not
bureaucratic caution. It is the thing standing between a predictor and the call.

What that looks like at level B:

| variant | llr | call without the line | call with it |
|---|---|---|---|
| ALK R1275Q (neuroblastoma) | −5.25 | Resistance | Predicted damaging |
| **EGFR S768I (lung adenocarcinoma)** | −2.26 | **Sensitivity/Response** | Predicted damaging |
| BRAF D594G (colorectal) | −6.15 | Resistance | Predicted damaging |
| **FLT3 D835V (AML)** | −4.91 | **Sensitivity/Response** | Predicted damaging |
| DICER1 E1813Q (Sertoli-Leydig) | −4.38 | Oncogenicity | Predicted damaging |

`EGFR S768I` and `FLT3 D835V` are the two to look at. Both carry documented evidence that a drug
*works*. Over-weight a conservation score and that becomes "predicted damaging" — a prediction
about protein stability displacing a clinical observation about a therapy. Those are different
questions, and only one of them was asked.

## Second result: the cap alone is not enough

Loosening the threshold, so the line speaks on weaker scores too:

| threshold | groups it speaks on | calls changed at **E** (supporting) |
|---|---|---|
| \|llr\| ≥ 0.5 | 20 | **3** |
| \|llr\| ≥ 1.0 | 17 | **2** |
| \|llr\| ≥ 1.5 | 12 | 0 |
| \|llr\| ≥ 2.0 | 11 | 0 |
| \|llr\| ≥ 3.0 | 6 | 0 |

So the cap holds *only if the predictor also declines to speak when it has little to say*. Capped
at supporting but allowed to comment on everything, it still moves calls. **Capping strength and
knowing when to abstain are two separate mechanisms and you need both** — which is the same
finding as module A, arrived at from the other end.

## What this is allowed to conclude

**Allowed.** A computational evidence line should be capped at supporting strength *and* gated by
a score threshold, and a system using one should show the call with and without it rather than
folding it in silently. On this data, that combination moves zero calls while an over-weighted
line moves nearly half.

**Not allowed.** Any claim resting on these counts as if they were a benchmark. n is 6 to 20
groups. CIViC significance is clinical actionability, not ACMG classification, so "Resistance" and
"Predicted damaging" are not competing answers to one question — part of the absurdity on display
is precisely that a weighted vote treats them as if they were. The level→weight mapping is CIViC's
own A–E hierarchy, not ACMG's strength tiers. And the scores come from the 34M ESM-2; the 650M run
is queued for the GPU.

## Reproducing it

    python3 -I scripts/run_variant_ablation.py data/civic/evidence.tsv        # threshold 2.0
    python3 -I scripts/run_variant_ablation.py data/civic/evidence.tsv 0.5    # any threshold
