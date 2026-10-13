# A better model does not just score better — it changes the safety conclusion — 13 Oct 2026

**Rehearsal, not a shipped result.** These scores were produced on a rented NVIDIA L4, for the
same reason `scripts/fake_vllm.py` exists: to find out what happens before it happens on hardware
whose whole point is that the measurement happened there. The numbers that ship will come from
the AMD run. Nothing here is baked into the app.

Module B has been reporting figures from **ESM-2 35M**, chosen because it runs on a laptop in 200
seconds, with the caveat in `2026-10-13-esm2-evidence-line.md` that "the 650M run is queued for
the GPU and the figure will be re-reported either way". This is that re-report, early.

## The bigger model is right far more often

534 variants, same crops, same masked-marginal method:

| | gets the sign wrong | median \|llr\| | clears \|llr\| ≥ 2 | time |
|---|---|---|---|---|
| ESM-2 35M (shipped) | **21.9%** | 1.14 | 201 of 534 | 200s on a laptop CPU |
| ESM-2 650M (rehearsal) | **6.6%** | 5.70 | **414 of 534** | 98s on one rented GPU |

"Gets the sign wrong" means the model prefers the mutant residue to the wild type on a variant
that carries clinical evidence. The error rate falls by two thirds. The two models **disagree on
direction for 19% of variants**, and the swings are not small — `BCL2 G101V` goes from +2.28 to
−10.68, `ERBB2 G776L` from +0.92 to −10.98.

## And that is where it stops being a benchmark improvement

The published Module B result is that **at supporting strength, 0 of 11 contested calls change** —
the line ACMG-era practice puts an uncalibrated predictor at, and nothing moves. Re-run with the
650M scores:

| strength granted | 35M: calls changed | 650M: calls changed |
|---|---|---|
| **E — supporting** | **0 of 11** | **4 of 28** |
| D — case report | 2 of 11 | 6 of 28 |
| C — preclinical | 4 of 11 | 12 of 28 |
| B — clinical | 5 of 11 | 15 of 28 |
| A — validated | 9 of 11 | 21 of 28 |

Two things changed and both matter.

**The predictor now speaks on every contested group it is eligible for** — 28 of 28, against 11 of
28 before — because it is confident enough to clear the threshold everywhere. The old headline
that "171 of 182 contested groups cannot receive a computational vote at all" was substantially a
statement about a small model being unsure.

**At supporting strength, four calls now move.** `BRAF V600E` in melanoma goes from *Poor Outcome*
to *Predicted damaging*; the same variant in colorectal cancer goes from *Sensitivity/Response* to
*Predicted damaging*; `ALK F1174L` and `ALK R1275Q` in neuroblastoma go from *Resistance* to the
same place. **Our published conclusion that "at the strength an uncalibrated predictor belongs at,
nothing moves" is a property of the weak model, not of the cap.**

Loosening or tightening the threshold does not rescue it: at \|llr\| ≥ 5 it is still 2 of 23.

## What this says, and what it says about the hardware

The honest version of the Module B claim becomes **stronger and less comfortable**: capping a
predictor's strength is not sufficient on its own, and the better the predictor gets, the less
sufficient it is. The cap was doing less work than we credited it with; the 35M model's reticence
was doing the rest. A system that puts a modern predictor into an evidence vote needs the
abstention as well as the cap, which is what module A found from the other end — and now it is not
an argument from a loosened threshold, it is what a current-size model actually does.

It is also the clearest answer this project has to *why the hardware matters*. Not "faster". A
model you can run on a laptop told us the cap was enough. A model that needs a GPU says it is not.
**The conclusion changed, not the throughput.**

## What happens next, and the discipline around it

Nothing here is baked. `src/askfirst/baked/variant_scores.json` is still the 35M run, the app
still serves the 35M ablation, and every published Module B number is still the 35M one with this
note beside it. When AMD credits land, `scripts/score_variants.py --model
facebook/esm2_t33_650M_UR50D` runs on MI300X, those scores are baked, the ablation is re-run, and
**the shipped numbers come from there**. This file exists so that the AMD day is spent measuring
rather than discovering.

If that day does not happen, this stays a rehearsal note and the shipped claims stay the 35M ones,
clearly labelled — which is why it is written down now rather than held back.

## Reproducing it

    modal run scripts/rehearsal/esm_modal.py --model facebook/esm2_t33_650M_UR50D
    python3 -I scripts/run_variant_ablation.py data/civic/evidence.tsv 2.0 \
        docs/results/rehearsal-esm650m.json

The second command writes `rehearsal-variant-ablation.json` and bakes nothing. An earlier version
of it overwrote the published artifact, which is now guarded against.
