# Data, and what we are allowed to do with it

Everything the repository ships or depends on has to be redistributable, because the submission
requires a public repository. Anything that is not redistributable is listed here as excluded,
with the reason.

## Included

| Source | Licence | Verified | Used for |
|---|---|---|---|
| DDXPlus | CC-BY | figshare record states CC-BY — re-check before release | Module A primary. ~1.3M synthetic patients, 49 pathologies, 110 symptoms, 113 antecedents, with a differential and a ground-truth pathology per patient |
| MedQA | MIT | multiple secondary sources agree; confirm at source | Module A cross-check on real exam-style items |
| UniProt (Swiss-Prot) | **CC BY 4.0** | terms stated on uniprot.org/help/license; reviewed human entries fetched over the public REST API, no key | Module B. Canonical protein sequences, so a variant label can be checked against the residue it claims. Cached under `data/uniprot/`, **not committed** |
| CIViC | CC0 1.0 | project states CC0 for data, MIT for their code | Module B. Evidence items, variants, assertions. Bulk TSV and VCF, plus an open API; monthly dumps are mirrored on AWS Open Data and listable without an account |

DDXPlus is synthetic, generated from a proprietary knowledge base and a rule-based system. That is
a strength for privacy and a weakness for validity: a model can learn the generator instead of the
medicine. This is why MedQA was held out as a cross-check — it was not run, and that is recorded in (`docs/results/2026-10-13-the-cross-check-we-did-not-run.md`) — and why the limitation is stated in the
README rather than buried.

## Needs checking before it ships

| Source | Status |
|---|---|
| ClinVar | NCBI distributes it openly and it is widely redistributed, but the exact terms have not been read. Confirm at the NCBI FTP site before shipping anything derived from it |
| MedMCQA | Sources disagree: MIT, Apache-2.0, and "MIT for non-commercial research" all appear. Treat as unusable until the official repository settles it |
| PubMedQA | Licence not established |

## Excluded, deliberately

| Source | Why |
|---|---|
| MIMIC-IV | The data use agreement forbids redistribution, which a public repository cannot honour. The open demo subset is around 100 patients, too small to carry an evaluation |

## What runs where

Fetching, parsing and schema work are plain CPU and need no accelerator. The expensive part is
step 3 of the engine: scoring a case once per field it contains, and once per candidate value for
each field it lacks. A case with a dozen fields is dozens of forward passes, and the evaluation is
thousands of cases. That batch work is what the AMD GPU is for.

The served endpoint runs one open model through vLLM. It is sized for a single device, because the
credit allocation does not support multi-device tensor parallelism for a sustained window.

## NHAMCS — the one real queue

The CDC's National Hospital Ambulatory Medical Care Survey, Emergency Department component.
Public use files, no registration and no credentialing: 72,004 visits across 2018, 2019, 2021 and
2022. This is the only data in this project that is not synthetic, and the only place where a
value is missing because a person did not write it down.

| | |
|---|---|
| licence | US government work, public use file, **under the NCHS data use agreement** |
| what we use | triage-time fields only — age, sex, arrival by ambulance, three reason-for-visit codes, six vitals, pain score, triage immediacy, seen-here-in-72-hours |
| outcome | escalation: admitted here, admitted to observation then hospitalised, transferred out, or died in the department |
| record layout | parsed out of the documentation PDFs by `scripts/nhamcs_layout.py`, because the columns move between years |

**The agreement, and how it is honoured.** NCHS permits statistical reporting and analysis only;
forbids any attempt to identify a person or establishment; and forbids linking the file with
individually identifiable data from any other source. Violations carry criminal sanctions. Fitting
and evaluating a triage gate is statistical analysis. We do not link, we do not re-identify, the
files are gitignored and never committed, and **no national estimate is quoted anywhere** —
`PATWT` exists for exactly that and nothing here uses it.

Three things a reader should know before trusting a number off it:

- **"Missing" means "not documented".** The file is abstracted from the chart after the visit, so
  a blank pulse oximetry is something nobody wrote down, which is related to but not the same as
  something nobody knew at triage.
- **It clusters by hospital.** `HOSPCODE` identifies the site and some sites chart far less than
  others, so every interval over this data resamples hospitals rather than visits. The code is
  reassigned each year, so the cluster key is the year and the code together.
- **It is where the project's claims stopped transferring.** One of four pre-registered
  conditions met: `results/2026-10-13-the-real-queue-said-no.md`.

## Models

| Model | Licence | Used for | Runs on |
|---|---|---|---|
| ESM-2 35M (`esm2_t12_35M_UR50D`) | **MIT** | The computational evidence line, measured 13 Oct: 534 variants in 200s | CPU — ran on a laptop |
| ESM-2 650M (`esm2_t33_650M_UR50D`) | **MIT** | The same run at a size worth quoting; the 35M result is deliberately reported as a floor | MI300X, queued |
| An open instruct model via vLLM | per model card, must be permissive | Outcome scoring in steps 2-4 of the engine | MI300X |

**AlphaMissense is excluded.** Its predictions are released CC-BY-NC-SA, which is a
non-commercial licence and incompatible with shipping under MIT. ESM-2 covers the same need.

A known time sink, recorded here so it is budgeted rather than discovered: mapping a variant from
HGVS notation to a position in a specific protein sequence requires transcript selection and is
reliably fiddlier than the model work around it.
