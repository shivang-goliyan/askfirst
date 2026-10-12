# askfirst

**Finds the one missing fact that would change the answer — and refuses to answer until it has it.**

Ask a model to decide something from an incomplete record and it will decide anyway. It sounds
exactly as confident when the one result that settles the case is absent. On cases with
information deliberately withheld, a recent evaluation measured a frontier model's hallucination
rate at 0.808 (arXiv 2608.09080).

askfirst does not decide. It sits in front of the model that does, and answers a narrower
question: *is there enough here?* When there isn't, it refuses and names what to go and find,
ranked by how much each missing item would move the answer — and by what it costs to get.

Two domains, one engine.

## Module A — clinical records

```
Record #4471 — 34F, chest pain 2h, HR 104, BP 138/86, no ECG, no troponin

  SUFFICIENCY  38 / 100     not enough to decide

  Go get:   troponin        if elevated, the answer changes with p = 0.71
            ECG             if abnormal,  the answer changes with p = 0.64
            d-dimer         marginal,     p = 0.11

  Cheapest decisive test:   troponin   (~4 min, lowest unit cost of the three)
```

## Module B — cancer variant classification

A genetic variant found in a tumour gets classified against the ACMG/AMP evidence codes. When the
evidence is thin the verdict is **"variant of uncertain significance"** — a non-answer that helps
nobody, and there are hundreds of thousands of them. Published work in 2026 found that adding
external functional and population evidence resolved roughly 17% of a sample of such variants,
and that experimental plus predictive evidence could in principle resolve around 75% of them.

The field is good at asking *what happens if we add evidence*. askfirst asks the prospective
version instead: **which single missing piece of evidence should you go and get first?**

```
BRCA2 c.7958T>C — currently UNCERTAIN SIGNIFICANCE

  Evidence present:   PM2 (absent from controls), BP4 (computational: benign)
  Evidence missing:   PS3 functional assay      would resolve with p = 0.68
                      PP1 segregation data      would resolve with p = 0.41
                      PS4 case-control          would resolve with p = 0.12

  Cheapest path to a classification:  PP1 — the family data may already exist
```

Same engine, different field schema. The schema is data, not code, which is why one project
covers both.


### Computing the computational evidence line

PP3 and BP4 are the ACMG/AMP codes for computational evidence. Rather than looking them up,
askfirst computes them: ESM-2 (MIT licensed) scores the variant against the reference sequence on
MI300X, and the log-likelihood ratio becomes a PP3 or BP4 call against published, calibrated
thresholds.

Three constraints on this, which are not negotiable:

- **Supporting strength only.** ACMG places computational evidence in its weakest tier on
  purpose. A score from this module can never be what resolves a variant, and will not be
  presented as though it were.
- **Calibrated thresholds or none.** ClinGen recalibrated PP3/BP4 because predictors were being
  over-weighted. We use published cutoffs, or we report the raw score and label it uncalibrated.
  We do not invent thresholds.
- **ESM-2, not AlphaMissense.** AlphaMissense predictions are CC-BY-NC-SA, which is incompatible
  with shipping under MIT. ESM-2 is MIT.

This module reads and scores sequences. It does no structure prediction, no binding prediction,
and nothing wet-lab. It outputs no diagnosis, no therapy, and no statement that a variant is
pathogenic.

## How it works

1. The record is parsed into atomic fields — each symptom, each measurement, each evidence code.
2. An open model scores the case. We keep the full distribution over outcomes, not just the text.
3. Every field that *is* present is deleted in turn and the case re-scored. How far the
   distribution moves is that field's influence. This builds a sensitivity map of the record.
4. Fields that are *absent* are ranked by expected influence, calibrated against that map, then
   re-ranked by cost and turnaround time.
5. If the outcome is unstable under ablation, askfirst refuses and returns the ranked gaps.

Step 2 is why this needs open weights. You cannot read a closed API's answer distribution or its
internal state, so you cannot measure what its answer actually rests on. Step 3 is the compute
cost: one case costs as many forward passes as it has fields, which is what the GPU is for.

## What this is not

- Not a diagnostic tool, and not medical advice. It outputs no diagnosis and no therapy.
- Not clinically validated. No clinician has reviewed its output. Every figure is measured
  behaviour on public data and nothing more.
- Not molecular design. Module B reads *existing published evidence about* variants. It does no
  structure prediction, no binding prediction, no wet-lab work of any kind.

## Prior work

A model that seeks missing clinical information before deciding is an established line of work,
and the comparison against it is the point rather than something to avoid:

- **MediQ** (arXiv 2406.00922, NeurIPS 2024) — the benchmark for interactive clinical reasoning
  from partial information. Prompting models to ask questions *lowered* accuracy by 11.3%;
  confidence estimation through self-consistency recovered +22.3%, which still left a 10.3% gap
  against being handed the full record up front. Their data covers two sub-benchmarks,
  iCRAFT-MD and iMedQA.
- **Q4Dx** (Nature Scientific Reports, 2026) — questioning-efficiency benchmark built by
  systematically removing information from cases.
- **ALFA** (arXiv 2502.14860) — aligning models to ask better clinical questions.
- **BALAR / MedClarify** — choose the next question by expected information gain over a
  predefined question set.

Those methods select from a question set, or prompt the model to ask. askfirst measures which
*absent* field most destabilises the model's own answer distribution, and then prices the answer.
The number we care about is that +22.3%, measured on their benchmark, against ours.

## Data

Everything shipped is redistributable. See [docs/DATA.md](docs/DATA.md).

| Source | Licence | Used for |
|---|---|---|
| DDXPlus | CC-BY | Module A primary — ~1.3M synthetic patients, 110 symptoms, 113 antecedents |
| MedQA | MIT | Module A cross-check on real exam-style items |
| CIViC | **CC0** | Module B — evidence items, variants, assertions; bulk TSV and open API |
| ClinVar | NCBI, terms to confirm | Module B — variant classifications and review status |

DDXPlus is synthetic, so Module A carries no privacy constraint. MIMIC-IV is deliberately not a
dependency: its data use agreement forbids redistribution, which a public repository cannot honour.

## Metric

The evaluation was written down before the model was built, including the kill criterion. See
[docs/METRIC.md](docs/METRIC.md).

## Running it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
scripts/fetch_data.sh          # prints what to download, from where, under what licence
python -m askfirst.demo        # ablation loop on a bundled sample, CPU only
```

The CPU path exists so the engine can be built and tested without a GPU. The served version runs
an open model through vLLM on AMD MI300X.
