# Data, and what we are allowed to do with it

Everything the repository ships or depends on has to be redistributable, because the submission
requires a public repository. Anything that is not redistributable is listed here as excluded,
with the reason.

## Included

| Source | Licence | Verified | Used for |
|---|---|---|---|
| DDXPlus | CC-BY | figshare record states CC-BY — re-check before release | Module A primary. ~1.3M synthetic patients, 49 pathologies, 110 symptoms, 113 antecedents, with a differential and a ground-truth pathology per patient |
| MedQA | MIT | multiple secondary sources agree; confirm at source | Module A cross-check on real exam-style items |
| CIViC | CC0 1.0 | project states CC0 for data, MIT for their code | Module B. Evidence items, variants, assertions. Bulk TSV and VCF, plus an open API; monthly dumps are mirrored on AWS Open Data and listable without an account |

DDXPlus is synthetic, generated from a proprietary knowledge base and a rule-based system. That is
a strength for privacy and a weakness for validity: a model can learn the generator instead of the
medicine. This is why MedQA is held out as a cross-check and why the limitation is stated in the
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

## Models

| Model | Licence | Used for | Runs on |
|---|---|---|---|
| ESM-2 (facebookresearch/esm) | **MIT** | PP3/BP4 computational evidence from log-likelihood ratios | MI300X |
| An open instruct model via vLLM | per model card, must be permissive | Outcome scoring in steps 2-4 of the engine | MI300X |

**AlphaMissense is excluded.** Its predictions are released CC-BY-NC-SA, which is a
non-commercial licence and incompatible with shipping under MIT. ESM-2 covers the same need.

A known time sink, recorded here so it is budgeted rather than discovered: mapping a variant from
HGVS notation to a position in a specific protein sequence requires transcript selection and is
reliably fiddlier than the model work around it.
