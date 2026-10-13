# askfirst

**Refuses to answer until the record can carry an answer — and tells you what to ask first.**

**Live: [askfirst.kgbnetwork.com](https://askfirst.kgbnetwork.com)** · [the deck](https://askfirst.kgbnetwork.com/deck.html)

Take 500 clinical questions, delete the correct option, and put *"insufficient information"* on
the page instead. **GPT-5 takes the way out 19.2% of the time** and picks one of the remaining
wrong answers for the other 80.8%, at a mean confidence of 0.69 (arXiv 2608.09080, Table IV).

So we deleted four fifths of a patient record and asked an open model again. **Its confidence fell
12%. A classifier fitted to the same data lost 83% of its confidence on the same deletion.** That
gap is the product: askfirst works out how much of a record is missing *without being told*, to
off by 0.057 on average, and refuses below a floor whatever the confidence says. On **30,000 held-out records
of undeclared completeness it answers 45.8% of them at 99.96% — 5 wrong instead of 5,460** — and
hands the rest to a person with a ranked list of what to go and get.

Then we stopped giving it fields. Feeding it **prose**, through a reader that loses 28% of the
findings, it answered seven fewer cases in a hundred and introduced **zero wrong answers**: what
the reader misses makes the record look thinner, and a thinner record is exactly what the gate
refuses. The error turns into caution instead of a confident mistake, which is the only test of
this idea that counts.

Every number here regenerates from public data in four minutes with `./scripts/verify.sh`, and a
test fails naming any document that drifts from its artifact.

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
how much strength it is granted — because *supporting* is where an uncalibrated predictor belongs
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

- **Supporting strength only.** The 2015 ACMG/AMP framework used computational evidence at its weakest tier; ClinGen's 2022 recalibration permits more for predictors calibrated against a reference set, and this one has not been. So supporting is where it belongs on
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
three-finding record, 4,000 patients: 77.8% asking nothing, 78.5% asking at random, **88.8%
asking what the engine says**. Ranking by expected information gain — the objective the
literature uses, now implemented the way it states it, with P(value | record) taken through the
outcomes rather than from a population marginal — scores 41.3%, worse than asking nothing at all.

## How it works

1. **A record arrives**, as coded fields or as prose. If it is prose, an open model reads it into
   fields — 72% of them, at 87% precision, which is the job that model is good at.
2. **A fitted scorer returns a distribution** over outcomes. Not a sampled answer: the posterior,
   because everything downstream is a function of it.
3. **Two checks about the record itself**, neither of which depends on what did the scoring. How
   much of the record is here, with a mean absolute error of 0.057 — below 35% it hands over whatever the
   confidence says. And could this have come from a patient at all: no real record in 60,000 holds
   more than 38 findings, so above 44 it refuses without scoring.
4. **One check about the answer.** The margin is turned into P(this is right) by a calibration
   fitted on how many findings are in hand and how unusual they are. Clear the bar you set, or
   hand over.
5. **Either way it reports what the answer rests on** — each present field deleted in turn and
   re-scored — and **what to go and get**, widest question first.

Step 5's ablation is what the page *shows* you. Steps 3 and 4 are what makes the call; an earlier
version of this list said the ablation drove the refusal, and that stopped being true when the
calibrated gate shipped.

The open weights matter at steps 1 and 2: you cannot read a closed API's distribution, and you
cannot ask it 208 yes/no questions about a note for the price of one shared prefix.

## The page does not ask you how complete your record is

It used to, and reading a threshold off a completeness level the visitor declares is the one
thing a deployment cannot do. The app now calibrates P(right) against how many findings it has in
hand, estimates how much of the record is missing to a mean absolute error of 0.057, and refuses
outright below a floor. On 30,000 records of undeclared completeness it is **99.96% right on the
45.8% it answers — 5 wrong, against 5,460** if it answers everything
(`docs/results/2026-10-13-the-page-stops-asking.md`).

The original motivation for this was that the margin was **40 points underconfident at 40%
evidence**. Refitting the scorer on records with holes in them cut that to **8.2 points**, so most
of it was a bug in how we trained rather than a property of confidence under missingness
(`docs/results/2026-10-14-the-scorer-now-expects-holes.md`). What survives is the part that
motivates the gate: one raw threshold still does not transfer. A cut-off chosen on 60%-complete
records promises 95% and delivers **44.9%** on a tenth of one.

## Records do not go missing at random

So we stopped assuming they do. The same number of findings removed seven realistic ways — the
follow-ups never happened, no history was available, the detail went and the screen stayed — and
at a fifth of a record top-1 runs from **8.9% to 96.4% depending only on which fifth** — an
eighty-seven point spread at one nominal completeness. The calibrated refusal is tested in 26 of
the 35 cells — the other 9 go silent. **24 of those 26 clear 95%**; the two that do not answered
19 cases and 1 case respectively, so neither carries any weight.
(`docs/results/2026-10-13-missing-not-at-random.md`).

## What it is worth, at prices we did not invent

The economics here used to price a wrong answer at 100 and a handover at 5, with no argument for
either. Published figures put a triage call at C$10–27 and the expected cost of a confident wrong
answer at $4,220–$167,000 — **a ratio of 211:1 to 8,356:1 against our 20:1**, so every saving in
this repo is conservative. Carried honestly, though, expected-cost minimisation says *switch the
product off*: above about 4,000:1 the cheapest policy answers nothing and refers everything. That
is a flaw in the objective — clinicians are finite and the queue has to go somewhere. The number
that survives is throughput at a fixed bar: **answering everything puts 176 wrong answers into
every 1,000 records; holding a 95% bar puts 0.13 there and still takes 45.5% of the queue**
(`docs/results/2026-10-13-what-it-is-worth.md`).

## What this is not

- Not a diagnostic tool, not a medical device, and not medical advice. When it accepts a case it
  **does name the condition it thinks most likely** — an earlier version of this line said it
  "outputs no diagnosis", which is not what the code does (`api.py` returns `answer.label`). The
  accurate description is a research prototype for *selective* diagnosis: it either names a
  condition or hands over, and the handover is the part that was measured. It prescribes nothing.
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

## We offered a frontier model the door

Not an accuracy contest — ours is fitted on 30,000 labelled patients from this generator and
Claude is zero-shot, so comparing top-1 would be a rigged race. The fair question is who knows to
stop. 200 held-out patients, `claude-opus-5-5`, every call offering `INSUFFICIENT` as a real
answer and telling it not to guess:

| same 150 patients, 40% of a record | abstains | right when it answers |
|---|---|---|
| Claude Opus 5.5, effort low | 8.0% | 14.5% |
| Claude Opus 5.5, effort high | **2.7%** | **4.1%** |
| this gate | **83.8%** | **98.2%** |

Abstention does climb as the record thins — 0% → 7.5% → 35% — which is better than the published
GPT-5 figure and better than we predicted. It is still off by an order of magnitude: at a fifth of
a record it answers two cases in three while being right in one case in 125. And raising the
effort made it abstain **less**, so it is not a thinking-budget problem
(`docs/results/2026-10-13-a-frontier-model-offered-the-door.md`).

This is not a claim that we diagnose better than Claude. It is a gate; Claude is the kind of thing
it gates; and the better the model behind it, the more the gate is worth.

## Why not conformal prediction?

Because someone will ask, and the answer should be a measurement. Selective prediction with a
precision target is conformal prediction's problem (Vovk, Gammerman & Shafer, 2005), and our rule
is a **Mondrian predictor** — a threshold per group, the group being how many findings are in hand
and how unusual they are — with an isotonic fit instead of a quantile, plus a record-level floor.

Implemented the standard version against ours. **The first version of this comparison was
rigged in our favour and a reviewer caught it** — it refitted only the baselines on six
missingness patterns while scoring us with a calibrator that had seen all seven. Those numbers
are withdrawn. Redone with every component refitted per fold, all seven leave-one-pattern-out
folds, the floor offered to the baselines, and intervals bootstrapped over patients:

| fitted on all seven, tested on all seven | precision | queue taken |
|---|---|---|
| one global threshold | 94.9% *(misses)* | 80.1% |
| **a threshold per group (Mondrian partition)** | **97.1%** | **74.0%** |
| a threshold per group + the same floor | 98.2% | 51.4% |
| ours: isotonic in-group + the floor | 99.9% | 46.6% |

**In distribution the standard tool beats us on coverage** — same bar, twenty-seven more points.
Under shift, across all seven folds, ours is the only rule that keeps the 95% promise every time:
**7 of 7, worst fold 99.7%**, against 6 of 7 for the per-group threshold (worst 94.5%) and 6 of 7
when that threshold is given our floor as well (worst 94.9%).

**And refitting the scorer on records with holes narrowed that gap rather than widening it.** The
completeness floor on its own went from keeping 3 of 7 folds to keeping 6 of 7; a better-calibrated
scorer helps the simple rules more than it helps us. Same finding as the three-scorer experiment
below, arriving from the other direction: the gate is worth most when the model is worst
(`docs/results/2026-10-14-the-scorer-now-expects-holes.md`).

One row of that experiment costs us something: stop the **raw, uncalibrated margin ranking** at
exactly our coverage and it is equally precise. On *this* scorer the calibration is not buying
ordering — what it buys is a stopping point chosen *without* seeing the answers, and every rule
above that had to choose blind, except ours, broke the promise at least once in seven folds. Isolate ordering properly — same eligible pool, same
size, only the sort key differing — and it buys **+10.6 points** on an overconfident naive Bayes,
where the raw ranking breaks the promise and the calibration keeps it, and **nothing** on the
other two (next section). It buys nothing here because our own scorer already ranks well, which
is not a thing a buyer knows about theirs in advance.

These baselines are selective prediction over a Mondrian partition, not conformal prediction
sets, and they carry no conformal guarantee; calling them conformal was sloppy and is corrected
in the write-up. The trade is robustness bought with coverage, and the over-delivery (99.5% when
asked for 95%) remains a defect we can name and have not fixed
(`docs/results/2026-10-13-the-comparison-was-rigged.md`).

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
  predefined question set. We implemented that objective and measured it **losing to a coin and
  then to silence**: 41.3% against 43.7% for asking at random and 42.7% for asking nothing at all.
  **That result is retracted.** It was an artifact of a scorer that had never seen a thin record,
  so its posterior — and therefore every entropy computed from it — was wrong on exactly the
  sparse cases where the advice matters. Refit the scorer on records with holes and information
  gain reaches **85.5%** against 77.8% for asking nothing: clearly useful, and it was the
  measurement that was broken, not the objective.

  Our ranking still wins — **88.8%** for breadth × answer rate against 85.5% for information gain,
  one question from a three-finding record, 4,000 held-out patients — but by three points rather
  than by thirty, and against a baseline that works. The honest claim is now "a cheap property of
  the question beats the principled objective here", not "the principled objective is wrong"
  (`docs/results/2026-10-13-breadth-beats-information.md`,
  `docs/results/2026-10-14-the-scorer-now-expects-holes.md`).

Those methods select from a question set, or prompt the model to ask. askfirst scores every
*absent* field against the model's own answer distribution and shows what each would settle — but
it orders them by how many answers the question admits, because that measured better than any of
the distribution-derived objectives we tried, including theirs. The honest statement of the
difference is that **we went looking for a patient-specific ranking and found that a
patient-independent one wins.**

## Is it a layer, or is it just our model?

The other sentence that sinks this is "your gate is fitted to your own scorer, so it is a model".
So we refitted it against two scorers it was not designed for, picked for *how their confidence
is wrong* rather than how good they are: a naive Bayes that is **overconfident** because it
multiplies dependent findings, and a nearest-neighbour vote whose confidence **saturates** at
1.00 and stays there. All three see identical features, so only the inductive bias differs.

**3 scorers × 7 leave-one-pattern-out folds = 21 cells.** Every rule refitted per scorer and per
fold; a cell counts as held only when the bootstrap *lower* bound clears 94.5%.

| rule | cells where the 95% promise held | worst cell | mean coverage |
|---|---|---|---|
| one global threshold | 7 of 21 | 89.9% | 51.0% |
| a threshold per group (Mondrian partition) | 13 of 21 | 89.8% | 54.3% |
| a threshold per group + **our** completeness floor | 15 of 21 | 87.0% | 38.2% |
| **the gate** | **20 of 21** | **96.0%** | 33.1% |

The one cell it misses is the naive Bayes under random thinning — 96.0% [93.6%, 98.2%] on 275
accepted rows, underpowered rather than broken, and reported as a failure anyway.

**And what the calibration buys turns out to depend on the scorer.** Give both arms the same
eligibility (ceiling and floor), take the same number of rows from each, and change only the sort
key — so the difference is ordering and nothing else:

| scorer | ranked by the calibration | ranked by the raw margin | ordering alone |
|---|---|---|---|
| logistic regression (ours) | 99.75% | 99.73% | **+0.02 points** |
| naive Bayes | 99.29% *(keeps the promise)* | 88.69% *(breaks it)* | **+10.60 points** |
| nearest-neighbour vote | 99.73% | 99.72% | **+0.01 points** |

So: the calibration buys ordering on exactly one of the three, and it is the one whose confidence
is worst. On the other two it buys only the stopping point. **The better your model's confidence
already is, the less this buys you — and nobody deploying a triage model knows in advance which
case they are in.** That is the product.

An earlier version of this table compared the gate against a *prefix* of the margin ranking,
which cannot separate the calibration's ordering from the floor's refusals. Isolating it cost us
the +2.8 we had claimed on the neighbour vote — that was entirely the floor — and turned +9.9 on
the naive Bayes into +10.6.

The mechanical reason, shown rather than argued: the neighbour scorer's confidence sits at 0.999
or above on **54.5% of rows**, and inside that one pile accuracy runs **91.8%** on four findings
or fewer against **100%** on twelve or more. An 8.2-point spread inside what is, to a threshold, a
single number. A threshold sees the number; the gate reads the record.

Worth noting what *does not* happen: after refitting, our own scorer saturates on 31.8% of rows
too — and inside its pile thin and full records are both right every time, a 0.0-point gap. A
saturated confidence is only a warning sign when the model has not been trained for thin records.
That is the same conditional as everywhere else here.



It costs coverage — 29.5% against 47.9% — and we over-deliver precision when asked for 95%,
which is the open engineering item (`docs/results/2026-10-13-is-it-a-layer-or-is-it-our-model.md`).

## The first time it met a real queue, it did not transfer

Everything above is DDXPlus: synthetic patients, with evidence hidden the seven ways *we* chose.
So we took **72,004 real emergency department visits** from the CDC's NHAMCS public-use files —
fitted on 2018–2019, measured on 2021–2022, 374 test sites sharing none with the fit years, and
a shift we did not choose: fully-charted visits fall from 43.3% to 39.1% across the pandemic.

**Four conditions were pre-registered before it ran.** One was met.

| | |
|---|---|
| the promise holds under real shift | **not met** |
| the calibration buys ≥1 point of ordering on sparse charts | **not met** (+0.36) |
| the gate refuses sparse charts at ≥2× the rate | **not met** (1.24×) |
| sparse charts are genuinely harder | met (85.7% vs 86.6%) |

And the number that matters more than the four: at a 95% target, of the **11,052 visits the gate
cleared to go home, 258 needed a bed** — 2.3% of the cleared visits, 5.5% of every escalation in
the test years. **On this task, on this data, it is not deployable.**

**Why, which is the useful part.** The failure is not the gate, it is the task — and we measured
that rather than guessing. AUC for escalation from the triage form alone is **0.8214**, a working
scorer. But the ceiling *any* rule can reach on this data is 94.0% precision at 1.0% recall, 79.4%
at 8.4%, 71.3% at 15.1%. **A 95% bar at 10% coverage does not exist here for any rule.** Our gate
sits on that frontier at its conservative end. We set a bar above what the data could supply, and
we should have measured the frontier before writing the bar, not after.

**What it changes about the product.** The gate needs a scorer that can be *certain*, and that
needs a task with room in it. DDXPlus has 49 conditions and 223 findings, so a confident correct
posterior is reachable. A 15-field triage form over a binary outcome at a 14.7% base rate does
not — the posterior is almost never extreme, so a precision gate either answers nothing or
answers the easy majority class. So the buyer in `BUSINESS.md` is narrower than claimed: **an
operator whose engine produces a rich differential over many conditions**, not acuity prediction
from vitals. That is now a measurement rather than an opinion.

Full result, including the three named follow-ups and what the pre-registration got wrong about
itself: `docs/results/2026-10-13-the-real-queue-said-no.md`.

## We tried to delete our own floor, and mostly succeeded

Two questions from a reviewer, both designed to remove parts of this rather than improve them.

**Does the learned completeness estimator earn its place?** No, not on our own scorer:

| arm | folds kept | worst fold | mean coverage |
|---|---|---|---|
| **no floor at all** — just the calibration and the ceiling | **7 of 7** | 99.5% | **61.1%** |
| a bare count, smallest that holds on the fit split | 7 of 7 | 99.5% | 61.1% *(it picked n=0)* |
| `findings / mean record size`, same 0.35 floor | 7 of 7 | 99.5% | 44.5% |
| a count giving up the same coverage (n=5) | 7 of 7 | 99.5% | 47.9% |
| **the learned ridge** — what ships | 7 of 7 | 99.5% | 47.2% |

Read that row by row. The calibration **alone** keeps the promise in all seven folds at **61.1%**
coverage. Adding our floor takes it to 47.2% and the worst fold does not move: **99.5% either
way.** On our own scorer the completeness floor now costs **fourteen points of coverage and buys
nothing measurable** — and counting the findings (n=5) does marginally better than the regression.

That is worse for the floor than it looked yesterday, when it cost four points and bought 0.9.
Refitting the scorer on records with holes is what did it: a scorer that is honest on a thin
record already declines thin records through the calibration, so the floor has nothing left to
catch.

**So the claim that the floor is what keeps the promise is withdrawn** — here, in `calibrate.py`'s
docstring, and in the write-up that first made it. It is still on by default, for three reasons
and one of them is not a measurement:

1. It rescues a badly-shaped rule — a per-group threshold goes from 13 of 21 scorer-fold cells to
   15 of 21 when it is given the floor.
2. It is the half that runs for a stranger's scorer with nothing fitted.
3. Answering a two-finding record because the arithmetic cleared a bar is the behaviour this
   product exists to refuse. That is a judgement, and at 140 cases per 1,000 going to a person
   who did not need to see them it is an expensive one. `FLOOR` is one constant in
   `calibrate.py`; the table above is what turning it off would buy.

**Does training the scorer on records with holes make the gate unnecessary?** It makes the gate
considerably more valuable:

| scorer | answering everything | one global threshold on it | with the gate |
|---|---|---|---|
| shipped, complete records only | 67.1% | — | 7/7, 36.4% coverage |
| **trained for holes** | **82.3%** | **1 of 7 folds** | 7/7, **47.0%** |
| trained for holes, same row count as shipped | 81.9% | 1 of 7 | 7/7, 46.2% |

Masking augmentation is worth **14.8 points** of raw accuracy, and the same-row-count control says
it is the holes and not the extra data. It is the largest single improvement measured in this
project and it came out of an attempt to make the project unnecessary. Meanwhile a bare threshold
on the *better* scorer keeps the promise in **1 of 7 folds** — making the model better made the
naive rule more dangerous — and the gate turns the improvement into **36.4% → 46.2%** of the queue
taken off a person at the same promise.

Write-up, including the four things it does not establish:
`docs/results/2026-10-13-we-tried-to-delete-our-own-floor.md`.

## Someone else's model can use it in two curls

The fair reading of the old code was that this was a model with a gate bolted on, not a gate:
`rule_for()` returned nothing for a scorer it could not encode for, and the response admitted it
had borrowed a cut-off. The product claim was "a gate in front of whatever you already use" and
the artifact did not do that.

It does now. `POST /api/gate` takes a record and *your* model's confidence, and no scorer of ours
appears anywhere in it:

```bash
curl -s https://askfirst.kgbnetwork.com/api/gate -H 'content-type: application/json' -d '{
  "record": {"E_55": true, "E_54": true, "E_57": true, "E_56": true, "E_60": true,
             "E_61": true, "E_62": true, "E_77": true, "E_88": true, "E_133": true,
             "E_152": true, "E_204": true},
  "confidence": 0.93,
  "scorer": "your-model",
  "target": 0.95
}'
```

Two of the three checks need nothing fitted and work on the first call, because they read the
**record** rather than the score: the ceiling (no real record holds more than 38 findings) and
the completeness floor (below ~35% of a record estimated present, it hands over whatever the
confidence says). The advice needs nothing either — the ranking that won our measurement is
breadth × answer rate, and both terms come off the schema and the priors rather than a model.

The third check — the precision promise — **does not transfer, and the endpoint says so instead
of pretending.** An unknown scorer gets `"available": false` and the command that would fix it.
That is not modesty, it is measured: a cut-off borrowed from the softmax delivered 54.7% where it
promised 80% on an open model's own confidence.

```bash
python3 scripts/fit_gate.py your-history.jsonl --scorer your-model
```

One JSON object per line — the record, your confidence, whether you were right. It fits the
calibration, holds 30% back, and **tells you if the promise does not hold rather than writing the
file and looking pleased.** A worked example ships in the repo, fitted against the naive Bayes
standing in for a customer's model: 16,800 rows, and on the 5,040 it never saw it answers 12.0%
of them at 99.5% [99.0%, 100.0%].

The contrast is the argument, and you can see it in two calls to the same endpoint. Same record,
same confidence of **0.8**, opposite decisions:

| `"confidence": 0.8` on the same twelve findings | what it is worth | what the gate does |
|---|---|---|
| `"scorer": "softmax"` | **65.7%** likely right | **hands over** |
| `"scorer": "example-bayes"` | top of its fitted range | **answers** |

Not a difference in a probability — a difference in what to *do* with an identical number. The
refitted softmax's confidence is honest, so 0.8 really does mean about two thirds. The naive Bayes
almost never gets that confident, so 0.8 from it is a strong signal. A threshold holds the number
and cannot see which of those it is holding.

Fitting also replaces the completeness estimator with one fitted to **that operator's** intake:
on the same record the shipped estimate says 61% present and the example fit says 74%, because
records do not go short the same way in two places. That substitution is the moat in `BUSINESS.md`
expressed as a file on disk rather than as an argument.

## It does not need a form

The engine scores structured findings; the world produces prose. An open model reads one into the
other — **72% of findings recovered at 87% precision** over 100 records. It is wrong often enough
to matter, which is the point: scored from the note instead of the record it answers 34% of cases
rather than 41% at the same bar and introduces **zero wrong answers**. What the reader misses
makes the record look thinner, and a thinner record is exactly what the completeness gate refuses.
The error becomes caution instead of a confident mistake
(`docs/results/2026-10-13-prose-in-findings-out.md`).

That is also the honest job for the hardware. Measured as a *scorer* the same model gets 35.3%
against the fitted softmax's 99.6%; measured as a *reader* it earns its place.

## Who pays

An operator whose cost line is clinician-minutes **and whose engine produces a rich differential**
— teleconsultation platforms, symptom-checker vendors, virtual-triage engines. They already have
the cost, already have a person at the other end for a refusal to reach, and already carry the
liability for a confident wrong call. Deterministic protocol lines are *not* buyers: there is no
posterior to calibrate. Nor is acuity prediction from vitals, which we measured and rejected.

**And the failure is documented in production, by people with no stake in our answer.** Australia's
national health line published an evaluation of its AI virtual-triage engine over **1,552,592
encounters**: nurses agreed with it 83.3% of the time and *"where they did not agree, nurses
generally set a higher triage level"* — alongside the operator's own sentence, *"VTCR is configured
to overtriage to minimize patient risk."* A deployed engine at national scale is deliberately set
to over-escalate because nobody has measured how far it can be trusted on a thin record.

Meanwhile consumer symptom checkers, re-audited on the same 45 vignettes five years apart, went
from **85.7% to 51.9%** sensitivity on emergencies while specificity rose 82.1% → 93.3% (*JMIR*
2022;24(5):e31810). More confident, less safe, in exactly the direction this refuses in.

Per 1,000 records at a 95% bar: **455 never reach a person**, 0.13 are answered wrongly against
176 if everything is answered, **C$4,546–12,274 of review capacity returned**, and a **cost to
serve of $0.0004** — an assessment is 44.5 ms of CPU with no GPU and no model call. Priced at C$500
per thousand that is a 7–19× return for the buyer at close to 100% gross margin.

The defensibility came out of a limitation: the calibration has to be fitted against the way
records go short where it runs, and we measured that getting it wrong costs about 1.1 points of
precision — on intervals that overlap, so it is a real effect we cannot size precisely yet. The deployed thing is fitted to one operator's intake behaviour and does not transfer.

**Nobody has bought it, there is no pilot, and no approach has been made to anyone named above.**
The throughput is measured on synthetic patients and the one real queue we tried it on said no.
What the evidence above establishes is that this failure happens in production — not that anyone
would buy a fix from us. Full case, including what would have to be true:
[docs/BUSINESS.md](docs/BUSINESS.md).

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

## Check it yourself

    ./scripts/verify.sh

Four minutes. It rebuilds the risk-coverage curve, the calibration, the completeness estimator and
the variant ablation from the public data, diffs each against the committed artifact, and then
runs a test that fails naming any document quoting a figure the artifacts do not support.
`--all` adds the two long measurements. It passes, byte for byte.

Three numbers have drifted in this repo in two days and two of them were caught by a reviewer
rather than by us, which is why this exists.

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
