# askfirst

**Finds the one missing fact that would change the answer — and refuses to answer until it has it.**

**Live: [askfirst.kgbnetwork.com](https://askfirst.kgbnetwork.com)** · [the deck](https://askfirst.kgbnetwork.com/deck.html)

Ask a model to decide something from an incomplete record and it will decide anyway. It sounds
exactly as confident when the one result that settles the case is absent. Take 500 clinical
questions, delete the correct option, and offer "insufficient information" instead: GPT-5 picks
one of the remaining wrong answers **80.8% of the time**, at a mean confidence of 0.69
(arXiv 2608.09080, Table IV). Abstaining was an option on the page and it took it 19.2% of the
time.

askfirst does not decide. It sits in front of the model that does, and answers a narrower
question: *is there enough here?* When there isn't, it refuses and names what to go and find,
**widest question first** — and, where questions carry a price, what it costs to get.

That ordering is deliberately a property of the questions rather than of the patient, and it is
the whole finding: every patient-specific objective we tried lost to a coin, and this one beat
them all by 24.6 points at three findings (13 to 29 across the three record sizes). The patient-specific numbers are still on the page beside it — what the
current answer rests on, what each answer would settle, how often one more fact would change the
decision — they just do not decide the order.

Two domains, one engine.

## Module A — clinical records

Real output from the live app, not an illustration. Nothing told it the record was 31% complete;
it worked that out from what it was handed.

```
A real held-out patient — M, 79 — with 4 of their 11 findings in hand:

  Do you have severe Chronic Obstructive Pulmonary Disease (COPD)?
      -> present
  Are you experiencing shortness of breath or difficulty breathing in a significant way?
      -> present
  Do you have a cough that produces colored or more abundant sputum than usual?
      -> present
  Do you smoke cigarettes?
      -> present

  COMPLETENESS    about 31% of a record, below the 35% floor
  ANSWERING       no
  WHY             only about 31% of a record — too little to judge the answer by, whatever the confidence says
  ONE MORE FACT   would change the answer 3.8% of the time

  Go get, widest question first:
    Do you feel pain somewhere?
        165 possible answers, answered 81% of the time
    Does the pain radiate to another location?
        165 possible answers, answered 81% of the time
    Have you traveled out of the country in the last 4 weeks?
        12 possible answers, answered 100% of the time

All 11 findings in, same patient, same model:

  ANSWERING       yes — Acute COPD exacerbation / infection
  WHY             better than 99% likely to be right, which clears the 95% asked for
  COMPLETENESS    about 100% of a record

  Scored by: softmax regression on CPU, 99.6% top-1 on complete records
  The condition really was: Acute COPD exacerbation / infection
```

The second domain, where questions carry a price and the ranking has to account for it, is the
other tab on the live page.

## Module B — cancer variant classification

A genetic variant found in a tumour gets classified against the ACMG/AMP evidence codes. When the
evidence is thin the verdict is **"variant of uncertain significance"** — a non-answer that helps
nobody, and there are hundreds of thousands of them. Published work in 2026 found that adding
external functional and population evidence resolved roughly 17% of a sample of such variants,
and that experimental plus predictive evidence could in principle resolve around 75% of them.

The same ablation, asked of a different kind of evidence: **take one line out and see whether the
call changes.** Here the removable line is a protein language model's score, and the variable is
how much strength it is granted — because ACMG/AMP caps computational evidence at *supporting*
and ClinGen had to recalibrate that slot downward when predictors were trusted past it.

Real output, same as above:

```
$ curl -s askfirst.kgbnetwork.com/api/variants        # 11 contested groups the score can speak on

EGFR S768I — Lung Adenocarcinoma — Erlotinib

  The evidence already in the group:
    level C  Supports         Sensitivity/Response   rated 3/5   Hellmann et al., 2014
    level C  Supports         Resistance             rated -/5   Lund-Iversen et al., 2012

  ESM-2 says:  Predicted damaging   (llr -2.2614)

  What the group concludes, by the strength that score is granted:
    without it            Sensitivity/Response
    E  supporting         Sensitivity/Response
    D  case report        Sensitivity/Response
    C  preclinical        Sensitivity/Response
    B  clinical           Predicted damaging   <- the call changed
    A  validated          Predicted damaging   <- the call changed

  Across all 11 groups: 0 calls change at supporting strength,
  5 at clinical strength — and every one of those 5 ends with the prediction on top.
```

Same engine, different field schema. The schema is data, not code, which is why one project
covers both.

An earlier version of this section showed a BRCA2 variant with lines like *"PS3 functional assay
— would resolve with p = 0.68"*. Nothing in this repo computes that, and no such case was ever
run. It was written as an illustration before the module existed and it stayed far too long.


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

## What is measured, and where to read it

Everything below is on held-out DDXPlus patients the scorer never saw, with intervals, and every
figure has a dated write-up in [`docs/results/`](docs/results/) — including the four that did not
work and the two headlines we killed ourselves.

**Refusing pays, and how much to refuse depends on how thin the record is.** 6,000 held-out
patients, 49 conditions, chance 2.0%:

| evidence kept | answer everything | answer the confident 25% |
|---|---|---|
| 100% | 99.6% | 100.0% |
| 40% | 82.6% | 98.3% |
| 20% | 39.9% | 73.5% |

On a complete record this product is nearly pointless, and the page says so.

**The advice works, and the principled objective is what was wrong.** One question from a
three-finding record, 4,000 patients: 42.9% asking nothing, 47.9% asking at random, **72.5%
asking what the engine says**. Ranking by expected information gain — the objective the
literature uses — scores 39.9%, worse than asking nothing at all.

## How it works

1. The record is parsed into atomic fields — each symptom, each measurement, each evidence code.
2. An open model scores the case. We keep the full distribution over outcomes, not just the text.
3. Every field that *is* present is deleted in turn and the case re-scored. How far the
   distribution moves is that field's influence. This builds a sensitivity map of the record.
4. Fields that are *absent* are ranked by how many answers each question admits — measured to
   beat ranking by expected information gain, which scored worse than asking at random — then
   re-ranked by cost and turnaround time.
5. If the outcome is unstable under ablation, askfirst refuses and returns the ranked gaps.

Step 2 is why this needs open weights. You cannot read a closed API's answer distribution or its
internal state, so you cannot measure what its answer actually rests on. Step 3 is the compute
cost: one case costs as many forward passes as it has fields, which is what the GPU is for.

## The page does not ask you how complete your record is

It used to. Measured: the scorer's margin is honest on a complete record and **40 points
underconfident at 40% evidence**, so a threshold chosen on full records promises 95% precision and
delivers 48% on a tenth of one. The app now calibrates P(right) against how many findings it has
in hand, estimates how much of the record is missing to within 0.057, and refuses outright below a
floor. On 30,000 records of undeclared completeness it is **99.6% right on the 35% it answers —
45 wrong, against 9,874** if it answers everything
(`docs/results/2026-10-13-the-page-stops-asking.md`).

## Records do not go missing at random

So we stopped assuming they do. The same number of findings removed seven realistic ways — the
follow-ups never happened, no history was available, the detail went and the screen stayed — and
at a fifth of a record top-1 runs from **19.6% to 73.2% depending only on which fifth**. The
calibrated refusal survives 33 of 35 cells and is fitted against all seven patterns; hold the
likeliest one out of the fit and it breaks by three points, which is the measured cost of
calibrating against the wrong kind of missingness
(`docs/results/2026-10-13-missing-not-at-random.md`).

## What it is worth, at prices we did not invent

The economics here used to price a wrong answer at 100 and a handover at 5, with no argument for
either. Published figures put a triage call at C$10–27 and the expected cost of a confident wrong
answer at $4,220–$167,000 — **a ratio of 211:1 to 8,356:1 against our 20:1**, so every saving in
this repo is conservative. Carried honestly, though, expected-cost minimisation says *switch the
product off*: above about 4,000:1 the cheapest policy answers nothing and refers everything. That
is a flaw in the objective — clinicians are finite and the queue has to go somewhere. The number
that survives is throughput at a fixed bar: **answering everything puts 330.5 wrong answers into
every 1,000 records; holding a 95% bar puts 1.7 there and still takes 35% of the queue**
(`docs/results/2026-10-13-what-it-is-worth.md`).

## What this is not

- Not a diagnostic tool, and not medical advice. It outputs no diagnosis and no therapy.
- Not clinically validated. No clinician has reviewed its output. Every figure is measured
  behaviour on public data and nothing more.
- Not molecular design. Module B reads *existing published evidence about* variants. It does no
  structure prediction, no binding prediction, no wet-lab work of any kind.

## How it behaves when it is wrong

The honest answers to the five questions a health product has to answer — incorrect responses,
sensitive data, uncertain results, high-risk decisions and human review — are in
[docs/SAFETY.md](docs/SAFETY.md), each one pointing at code or at a measurement.

Everything else: [state of play](docs/STATE.md) · [every measurement, including the
failures](docs/results/) · [the metric, fixed in advance](docs/METRIC.md) · [data and
licences](docs/DATA.md) · [how it is deployed](docs/DEPLOY-APP.md) · [the build
plan](docs/PLAN.md).

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
  predefined question set. **We implemented that objective and measured it losing to a coin —
  and then to silence:** 39.9% against 47.9% for asking at random and 42.9% for asking nothing at
  all, one question from a three-finding record, 4,000 held-out patients. It is an expectation
  taken under the model's own beliefs, and on a sparse record those beliefs are wrong. Two bugs
  in our own implementation of it had been flattering it; fixing them made it worse. Ranking
  instead by how much a question *could* tell you scores 72.5%
  (`docs/results/2026-10-13-breadth-beats-information.md`).

Those methods select from a question set, or prompt the model to ask. askfirst scores every
*absent* field against the model's own answer distribution and shows what each would settle — but
it orders them by how many answers the question admits, because that measured better than any of
the distribution-derived objectives we tried, including theirs. The honest statement of the
difference is that **we went looking for a patient-specific ranking and found that a
patient-independent one wins.**

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

Or the whole app in a container, which is how it is deployed — CPU only, no GPU needed, because
the headline curve is baked:

```bash
docker build -t askfirst .
docker run --rm -p 7860:7860 askfirst     # then open http://127.0.0.1:7860
```

Point it at a served model and the same endpoints score against it instead; the response says
which scorer answered, every time.

```bash
ASKFIRST_VLLM_URL=http://127.0.0.1:8000/v1 docker run --rm -p 7860:7860 -e ASKFIRST_VLLM_URL askfirst
```

The CPU path exists so the engine can be built and tested without a GPU. The served version runs
an open model through vLLM on AMD MI300X. **Nothing is attached today** — every number in this
repo was produced on CPU, `/api/health` reports `model_endpoint: false`, and each response says
what actually scored it.
