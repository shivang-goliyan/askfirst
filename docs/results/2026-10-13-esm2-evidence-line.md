# The computational evidence line, and why it cannot be trusted to vote — 13 October 2026

Module B's premise is that a variant call rests on lines of evidence, and that it matters which
line is load-bearing. ACMG/AMP has a slot for a computational predictor — PP3 when it says
damaging, BP4 when it says tolerated — and caps it at *supporting* strength. ClinGen later had to
recalibrate exactly that slot downward, because the predictors were being weighted too heavily.

This is a measurement of what that line would contribute if we let it.

## Getting to something scoreable, and what was thrown away

CIViC names variants at the protein level — `BRAF V600E`, not a c. HGVS string — so the coordinate
mapping that normally eats a day reduces to parsing a label. That is the only reason this ran at
all today.

| | |
|---|---|
| evidence rows | 4,940 over 1,987 molecular profiles |
| plain single-substitution labels | 557 |
| everything else (fusions, exon-level, `DNMT3A R882` with no alternate residue) | 1,430 — left alone, not guessed at |
| distinct genes looked up in UniProt | 107 |
| **scoreable after validation** | **534 variants, 100 genes, 1,205 evidence rows** |
| dropped: wild-type residue disagrees with the canonical sequence | **21** |
| dropped: silent substitution, nothing to score | 2 |

**Those 21 are the point of doing it this way.** A label and a sequence that disagree — usually
isoform numbering — produce a score that looks entirely normal and means nothing. Nothing is
scored until UniProt's canonical sequence is confirmed to carry the stated wild-type residue at
that position. 191 of the 534 needed a window crop to fit the model, and the crop is recorded per
variant rather than assumed harmless.

## The score

ESM-2 (`esm2_t12_35M_UR50D`, 34M parameters), masked marginal: mask the variant position, ask the
model what belongs there, take log P(mutant) − log P(wild type). 534 variants in **200 seconds on
CPU**, nothing skipped.

It behaves sensibly at the constrained end. The most surprised positions are
`BRAF G466V` (−11.85), `BRAF D594V` (−11.82), `MLH1 G67R` (−10.85), `DICER1 D1709G` (−10.79) —
real, well-documented variants where the model wants the wild-type residue back.

## And then the other end, which is the result

**For 98 of the 458 clinically-evidenced variants — 21% — the model prefers the mutant residue
over the wild type.** Not "scores it weakly". Prefers it. That needs no calibrated threshold to
interpret, which is why it is the number worth quoting: any PP3 use of this line fails outright on
those, and a naive BP4 rule would actively argue *against* a variant that CIViC documents as
clinically actionable.

Fifteen of them carry three or more supporting evidence items:

| variant | llr | evidence items | mostly |
|---|---|---|---|
| PIK3CA H1047L | **+4.82** | 4 | Sensitivity/Response |
| MYOD1 L122R | +2.79 | 9 | Poor Outcome |
| PIK3CA C420R | +1.38 | 3 | Sensitivity/Response |
| FGFR3 V555M | +1.19 | 3 | Gain of Function |
| FGFR3 N540K | +0.95 | 5 | Gain of Function |
| ERBB2 V777L | +0.85 | 5 | Sensitivity/Response |
| KIT K642E | +0.81 | 3 | Sensitivity/Response |
| **PIK3CA H1047R** | **+0.57** | **23** | Sensitivity/Response |
| TP53 G245S | +0.52 | 4 | Dominant Negative |
| AKT1 Q79K | +0.48 | 3 | Resistance |

`PIK3CA H1047R` carries **23 supporting evidence items** — it is one of the best-established
oncogenic drivers there is — and the model prefers the mutant.

## By what the clinical evidence actually says

| clinical significance | n | median llr | model prefers mutant |
|---|---|---|---|
| Predisposition | 15 | −1.42 | 2 (13%) |
| Oncogenicity | 42 | −3.23 | 7 (17%) |
| Poor Outcome | 28 | −1.83 | 4 (14%) |
| Gain of Function | 33 | −1.83 | 7 (21%) |
| Sensitivity/Response | 196 | −1.37 | 39 (20%) |
| Resistance | 162 | −1.01 | 32 (20%) |
| Dominant Negative | 38 | −0.29 | 13 (34%) |
| Loss of Function | 22 | −0.19 | 8 (36%) |

The ordering is the honest nuance: the line is *closest* to behaving as intended on
**Predisposition** — germline risk, which is the setting ACMG designed PP3/BP4 for — and worst on
somatic classes. That is not a bug in the model. ESM-2 scores evolutionary plausibility of a
protein sequence. An activating substitution in a signalling kinase can be entirely plausible as
protein and still drive a tumour, and a drug-escape mutation can be plausible by construction. The
measure and the question are different things, and the number above is the size of the gap.

## What this is allowed to conclude, and what it is not

**Allowed.** A computational evidence line, used generically across somatic variant calls, gets
the sign wrong for about one in five clinically-evidenced variants. So it must stay *supporting*
at most, it must be visibly removable, and the useful question is not what it scores but
**whether the call changes when it is taken away.** That is exactly what this engine does.

**Not allowed.** This is not a claim that ESM-2 is a bad model, nor a pathogenicity benchmark.
CIViC significance is clinical actionability, not ACMG classification, so these classes are not
pathogenic/benign labels and no AUC against them would mean what it appears to mean. No threshold
was fitted and none should be read in.

**Caveat that cuts against us, stated first.** This is the *smallest* ESM-2 at 34M parameters,
chosen because it runs on a laptop in 200 seconds. A larger model should do better, and if the
21% drops substantially on `esm2_t33_650M_UR50D` then the honest headline becomes "model size
moves this a lot", which is itself worth knowing and is a second reason to want the hardware.
**That run is queued for the GPU and the number here will be re-reported either way.**

## Reproducing it

    python3 -I scripts/build_variants.py data/civic/evidence.tsv   # no model needed
    python3    scripts/score_variants.py --model facebook/esm2_t12_35M_UR50D
    python3    scripts/score_variants.py --model facebook/esm2_t33_650M_UR50D   # the GPU run

Scores are baked to `src/askfirst/baked/variant_scores.json` so the numbers above can be checked
without a model or a GPU. Sequences come from UniProt (CC BY 4.0) and are cached, not committed.
