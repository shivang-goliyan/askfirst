# Where this stands

## Resume here

Everything is built except **the AMD run, the video and the demo**. 62 commits, 66 tests, 25 dated
write-ups in `results/`, clean tree, all endpoints live.

**14 Oct: the scorer was refitted on records with holes, and three published findings did not
survive it.** `results/2026-10-14-the-scorer-now-expects-holes.md` is the one to read. Nothing
given up on a complete record (99.6%), thirty-three points gained at a fifth of one (40.2% →
73.3%), and per 1,000 records at a 95% promise **455 never reach a person against 352, with 0.1
answered wrongly against 1.7.** What it cost: the motivating "40 points underconfident" became
8.2; "expected information gain loses to a coin and then to silence" is **retracted** (it reaches
85.5% once the scorer has seen a thin record, against 77.8% for asking nothing); and the
completeness floor now costs **fourteen points of coverage for no measurable gain in precision** —
and then the floor was swept properly (fitted on one split, chosen on a second, reported on a
third) and **priced**, which inverted that: taking it off buys +145 handovers per 1,000 worth
C$1,452–3,919 and costs +1.01 wrong answers worth $4,280–169,386, so the extra wrong answers cost
1.1× to 117× the saved reviews. The floor stays on a measurement
(`results/2026-10-14-where-the-floor-belongs.md`), and "it buys nothing measurable" is retired. Every dated write-up from before
14 Oct carries a note saying its prose was measured against the previous scorer.

**The evening of 13 Oct was a second review round, and it went badly for several published
claims.** Read these five before anything else, because four of them are retractions:

| | |
|---|---|
| `2026-10-13-the-comparison-was-rigged.md` | our own conformal shift test was rigged in our favour — the baselines were refitted on six missingness patterns and we reused a calibrator fitted on all seven. Redone across all 7 folds with everything refit: we keep the promise 7/7, worst fold 98.5%, against 5/7 for the best baseline. |
| `2026-10-13-is-it-a-layer-or-is-it-our-model.md` | refit against two scorers it was never designed for. **20 of 21 scorer-fold cells**, against 14 of 21 for the best threshold. Ordering, isolated properly: **+10.6 points** on an overconfident naive Bayes, **nothing** on the other two. The earlier +2.8 on the neighbour vote was the floor, not the calibration, and is retracted. |
| `2026-10-13-we-tried-to-delete-our-own-floor.md` | **the floor is not what keeps the promise.** The calibration alone keeps 7/7 folds and answers *more* cases. And the question that was meant to delete the gate found the biggest win in the project: training the scorer on records with holes is worth **14.8 points** of raw accuracy and takes coverage from 36.4% to 46.2%. Not shipped yet. |
| `2026-10-13-the-real-queue-said-no.md` | **1 of 4 pre-registered conditions met on 72,004 real ED visits.** A loss. At a 95% target it cleared 258 people who needed a bed. The failure is the task, not the gate — the data's own ceiling is 94.0% precision at 1.0% recall — but we set a bar above what the data could supply and only found out afterwards. |
| `2026-10-13-preregistered-real-queue.md` | the bar, committed before that ran. |

**Two live bugs were found and fixed the same evening**, both in code committed hours earlier:
`/api/gate` applied our softmax's calibration to any caller who did not name their scorer and
reported the promise as available; and `fit_gate.py` saved its two artifacts under different
names, so a customer got their own calibration and our completeness. Both have tests now.

**What is new and worth showing a judge:** `POST /api/gate` — a record plus *your* model's
confidence, no scorer of ours in it — and `scripts/fit_gate.py`, which fits a calibration to a
customer's own model and refuses to look pleased when the promise does not hold. The contrast is
two curls: confidence 0.5 is worth 80.2% from our softmax and 13.9% from a naive Bayes.

**And business value finally has named operators**, read at source: Healthdirect Australia's own
paper on 1,552,592 encounters says *"VTCR is configured to overtriage to minimize patient risk"*,
and consumer symptom checkers lost 33.8 points of emergency sensitivity over five years while
gaining specificity. See `BUSINESS.md`. Still no customer and no pilot.

    ./scripts/verify.sh      # 4 min: rebuilds every artifact from public data, passes byte-for-byte

**The AMD day, in order** (`GPU-DAY.md`): serve the model, re-run ESM-2 650M on MI300X and bake
those scores, re-run the variant ablation, swap the baked notes for live extraction, capture one
`rocprofv3` trace. All of it is rehearsed — see the rehearsal notes below — so the day is
measurement rather than discovery.

**Rehearsals were run on rented NVIDIA and on the Anthropic API. Nothing from them is baked into a
measured result**, and the three `rehearsal-*.json` artifacts are labelled as such. Modal has no
AMD GPUs; it was used the way `scripts/fake_vllm.py` was used.

**Not done, and honest about it:** MedQA was pre-registered as the cross-check and never run
(`results/2026-10-13-the-cross-check-we-did-not-run.md`), so every number here is DDXPlus-only. No
clinician has reviewed any output. There is no customer and no pilot.


**Live at https://askfirst.kgbnetwork.com** since 12 Oct — CPU only, no GPU attached, which is the point: the headline curve is baked and cannot go dark. Redeploy with `./scripts/deploy/vm.sh`; see [DEPLOY-APP.md](DEPLOY-APP.md).

The live case on that page is now the real thing: twelve held-out DDXPlus patients scored by the
fitted softmax that ships in the image, not a hand-written sketch. Take findings away and it stops
answering. The costed hand-built case is still there on its own tab, because DDXPlus prices every
question the same and the cheapest-first ordering needs something to chew on.

**The page stopped asking how complete your record is** (13 Oct, 11:45). It used to make the
visitor pick a completeness level and read the threshold off that curve, which is the one thing a
deployment cannot know. Fixed with two pieces — an isotonic calibration on findings in hand,
and a ridge estimate of how much of the record is missing (mean absolute error 0.057) that refuses
outright below 35%. On 30,000 records of undeclared completeness: **99.96% right, 5 wrong, on
45.8% of cases**, against 81.8% and 5,460 wrong answering everything.

The motivating measurement — the margin **40 points underconfident at 40% evidence** — was cut to
**8.2 points** by refitting the scorer on records with holes (14 Oct), so most of it was a bug in
how we trained rather than a property of confidence under missingness. What survives is that one
raw threshold still does not transfer: a cut-off chosen on 60%-complete records promises 95% and
delivers 44.9% on a tenth of one. The only dial left on the
live case is the target precision. Write-up: `results/2026-10-13-the-page-stops-asking.md`.

**And then the uniform-missingness assumption got tested** (13 Oct, 12:30). Every number before
this hid evidence at random. Cut the same number of findings seven different realistic ways and
top-1 at a fifth of a record runs from **8.9% to 96.4%** — an eighty-seven point spread at one
nominal completeness, so "20% of a record" is not one thing. The calibrated rule is tested in 26
of the 35 cells — the other 9 go silent. **24 of the 26 clear 95%**; the two that do not answered
19 cases and 1 case, so neither carries weight. An earlier version of this line said "holds in all
22", which the artifact never supported — the script only flags a cell as broken when its interval
excludes the target, and failing to prove a break is not a promise kept.

**The cell we said we could not fix is fixed, by the scorer rather than by the gate.** Every arm
of the ladder on "standard questions, no follow-ups" at 40% evidence now clears the target
(99.8–99.9%, from 91.5–93.6%), because the scorer was refitted on records with holes. The script
used to print "this cell is the honest limit of the method" from a hardcoded string that could not
change when the numbers did; it now derives that sentence from the ladder. An earlier version of
that ladder claimed the fix worked and
that one ingredient alone was worse than neither — it came from a scratch script, and when it was
moved into `run_missingness.py` so anyone could reproduce it, the effect vanished. The corrected
table and the retraction are both in `results/2026-10-13-missing-not-at-random.md`.

**The prices were made up, so they got looked up** (13 Oct, 14:30). Every economics figure here
priced a wrong answer at 100 and a handover at 5, and nobody had argued for either. Published:
a triage call is C$10–27 (CCOHTA 2003); the expected cost of a confident wrong answer is
P(harm|error) × cost of a harm = 4.4%/11.1% on dangerous presentations (Newman-Toker, BMJ Qual Saf
2024) × $422,000 average paid claim (CRICO 2009–13) → **$4,220 to $167,000, a ratio of 211:1 to
8,356:1 against our 20:1.** Every saving published here is therefore conservative.

Then the finding: **above about 4,000:1 — inside that band — expected-cost minimisation says
answer nothing and refer everything.** The objective is wrong, not the product. The number to sell
on is throughput at a bar: answering everything puts **176 wrong answers per 1,000 records**;
holding a 95% bar puts **0.1** and still takes 45.5% of the queue. Write-up:
`results/2026-10-13-what-it-is-worth.md`.

**The open model's job turned out to be reading, not deciding** (13 Oct, 17:00). Measured as a
scorer it is poor — 35.3% against the softmax's 99.6%, with a confidence that does not notice
four fifths of the record is gone. Measured as a *reader* it recovers **72% of findings from a
prose note at 87% precision**, 100 records in 70 seconds. And the number that matters: scored
from the note instead of the record, it answers 34% of cases instead of 41% at the same 95% bar
and introduces **zero wrong answers**. What the extraction misses makes the record look thinner,
and a thinner record is what the gate refuses — the error turns into caution rather than a
confident mistake. First end-to-end demonstration of the product's claim through a messy input
path. Baked notes are on the live page with what the model missed shown beside what it found.
Write-up: `results/2026-10-13-prose-in-findings-out.md`.

Module B is on the page too, baked: all eleven contested CIViC groups the ESM-2 line can speak on,
with the strength it is granted as a dial. `#level=B` links straight to the slide-worthy state —
5 of 11 calls change and the prediction lands on top every time.

## What works, measured

**Re-measured 13 Oct after finding the first version measured our own baseline.** A naive Bayes
scores 22.6% top-1 on held-out DDXPlus; a softmax regression over the same 972 features, 31 seconds
on CPU, scores **99.6%**. So the old "21.0% to 85.3% by refusing" was a statement about a weak
classifier, and on complete records the curve is flat. Details and what it cost us:
`results/2026-10-13-the-scorer-was-the-bottleneck.md`.

The honest measurement puts record completeness on the grid, because "is there enough here?" was
always the question. 6,000 held-out patients, 49 conditions, chance 2.0%, trained on complete
records and tested on incomplete ones.

| evidence kept | avg findings | answer all | @25% coverage | cheapest policy |
|---|---|---|---|---|
| 100% | 15.6 | 99.6% | 100.0% | answer 98%, saves 38% |
| 60% | 9.0 | 96.2% | 99.9% | answer 80%, saves 46% |
| 40% | 5.8 | **82.6%** | **98.3%** | answer 35%, saves 77% |
| 20% | 2.7 | **39.9%** | **73.5%** | **answer nothing** (5.00 beats the grid's 5.24) |
| 10% | 1.2 | 17.1% | 44.9% | **answer nothing** (5.00 beats the grid's 5.97) |

**Refusing pays at every level of completeness, and how much to refuse changes across the whole
range of the grid** — 97.5% of complete records down to answering none of the thinnest. The
coverage grid itself runs 2.5% to 100%, a span of 40, so "fiftyfold" was never the right word for
it; and at the two thinnest levels the cheapest policy is not a small positive coverage at all but
zero, which the grid had no column for until a review pointed it out. That is a setting rather
than a slogan, and the baked threshold is read
per completeness level so the dial on the page and the server's decision are one number.

Margin still beats entropy at every coverage level. On complete records this product is nearly
pointless and we say so.

## Module B, measured 13 Oct

The computational evidence line **gets the sign wrong for 21% of clinically-evidenced variants** —
98 of 458, where ESM-2 prefers the mutant residue over the wild type. `PIK3CA H1047R`, with 23
supporting evidence items, is one of them. No threshold needed to say that, which is why it is the
number quoted.

534 scoreable variants over 100 genes from CIViC's protein-level labels, which is why the HGVS
mapping never became the time sink the plan feared. **21 variants were dropped because UniProt's
canonical sequence does not carry the stated wild-type residue** — those would have produced
normal-looking, meaningless scores.

Caveat first: this is the 34M ESM-2, chosen because it runs on a laptop in 200 seconds.

**Re-reported early, on a rented GPU, 13 Oct.** The 650M model gets the sign wrong on **6.6%**
rather than 21.9%, and clears the threshold on 414 of 534 variants rather than 201. Re-running the
ablation with it, **4 of 28 contested calls change at supporting strength instead of 0 of 11** —
so "the cap alone holds" is a property of the small model, and the real conclusion is that a
better predictor needs the abstention more, not less. This is the clearest answer the project has
to why the hardware matters: the conclusion changed, not the throughput. Nothing is baked; the
shipped numbers stay the 35M ones until the AMD run.
Write-up: `results/2026-10-13-the-cap-is-not-enough.md`.
Full write-up: `results/2026-10-13-esm2-evidence-line.md`.

Then the question that matters — is that line load-bearing? Put the score into a CIViC group as one
removable item and sweep the strength it is granted. **At supporting strength, where an
uncalibrated predictor belongs,
0 of 11 contested calls change. Granted clinical strength, 5 of 11 change, and every time the
computational label itself ends up on top**, outranking documented therapy-response evidence
(`EGFR S768I`, `FLT3 D835V`). Loosen the score threshold and even supporting strength moves calls,
so **capping strength and knowing when to abstain are two mechanisms and you need both** — module
A's finding from the other end. And 171 of 182 contested groups can take no computational vote at
all. n is 6-20 groups; read the counts, not the percentages.
Write-up: `results/2026-10-13-computational-line-ablation.md`.

## The advice works too, as of 13 Oct

One question, from a record cut to three findings, 4,000 held-out patients: **77.8% without it,
78.5% asking at random, 88.8% asking what the engine says.** An oracle told which questions this
patient can actually answer gets 90.1%. (Refitting the scorer on records with holes moved every
arm of this table up by thirty-odd points; the figures before 14 Oct were measured against the
previous scorer.)

We used to say what fixed it was deleting the clever part: **expected information gain measured
worse than asking nothing at all**, 41.3% against 42.7%. **Retracted 14 Oct.** That was an
artifact of a scorer that had never seen a thin record, so every entropy computed from its
posterior was wrong on exactly the sparse cases where advice matters. Refit on records with holes,
information gain reaches **85.5%** against 77.8% for silence — clearly useful.

What ships still wins: **breadth × answer rate, 88.8%**, against 85.5% for information gain and
90.1% for an oracle told which questions the patient can answer. So the claim is now "a cheap
property of the question beats the principled objective here, by three points" rather than "the
principled objective is wrong". In clinical terms the advice is unchanged: characterise what you
already know before asking about one more symptom.

Re-measured after three bugs turned up, all of them in our favour: a negative answer was switching
the evidence feature *on*, the ranker assumed every question gets answered, and the harness let
`max()` break a three-way breadth tie using the engine's own sort order (worth seven points to us).
Answer rate on its own scores 42.0%, below a coin — so breadth is the mechanism, not a proxy for
"questions that tend to get answered". Write-up:
`results/2026-10-13-breadth-beats-information.md`.

## Conformal prediction, named and measured against — 13 Oct

Our rule is a Mondrian predictor (partition = findings in hand x how unusual they are) with an
isotonic fit instead of a quantile, plus a record-level floor. Implemented the standard versions:
in distribution **Mondrian beats us — 95.9% at 53.5% coverage against our 99.5% at 35.1%**. Under
missingness shift (fit on six patterns, test on the seventh) **Mondrian falls to 92.7% and breaks
its promise; ours holds at 98.9%**. Exchangeability is what conformal rests on and what the
missingness work measured failing. Our over-delivery is a defect: the obvious fix is to keep the
floor and swap isotonic for a per-group quantile, unmeasured and therefore not shipped.
Write-up: `results/2026-10-13-why-not-conformal.md`.

## Dead ends, so nobody repeats them

- **Flip probability as the ranking objective was actively harmful** — 18.8% against 26.0% for
  asking at random. It selects for volatility. Replaced by expected information gain.
- **Cheap-proposes-then-model-ablates caps the system near 32%**, because naive Bayes shortlist
  recall at k=20 is 31.8% and stage two can only re-rank what stage one passes. Inverted: the
  model proposes, the cheap scorer ablates.
- **A pathology-conditioned discriminative proposer lost to the marginal one**, 14.7% against
  20.0% at k=10.
- **An exhaustive 223-field sweep with a language model is ~22s of GPU per case.** That is a
  latency problem, not a budget one, and it does not go away with more credits.

## Architecture

1. Record parsed into atomic fields.
2. Open model scores it; the full distribution is kept, not sampled text.
3. Present fields ablated one at a time, giving a sensitivity map.
4. Absent fields ranked by how many answers each question admits — measured to beat ranking by
   expected information gain, which lost to a coin — then by cost and time to obtain.
5. Unstable under ablation means refuse: return the ranked gaps and hand over.

Step 2 is why this needs open weights. You cannot read a closed API's distribution, and without
it there is no entropy, no information gain and no calibrated refusal.

## The GPU day is rehearsed

The client has now run end to end against a served endpoint — `scripts/fake_vllm.py`, which answers
in vLLM's documented shape. It found three bugs that the unit tests could not: the proposer parsed
field names with a pattern that silently matched nothing outside DDXPlus, the invented-code
safeguard was filtered out one line after being set, and the scorer label was a hardcoded
"open model on AMD MI300X" that printed whatever was really answering. All three fixed.
Order of work, cost arithmetic and kill criteria: [GPU-DAY.md](GPU-DAY.md).

## Running the measurements

    python3 -I scripts/run_abstention.py     data/ddxplus/release_validate_patients 1500
    python3 -I scripts/run_economics.py      data/ddxplus/release_validate_patients 1500
    python3 -I scripts/run_recovery.py       data/ddxplus/release_validate_patients 400
    python3 -I scripts/run_decision_value.py data/ddxplus/release_validate_patients 250
    python3 -I scripts/run_proposer_recall.py data/ddxplus/release_validate_patients 200
    python3 -I scripts/bake_curve.py         data/ddxplus/release_validate_patients 1500

With a served model, the proposer harness adds the model to the table automatically:

    ASKFIRST_VLLM_URL=http://127.0.0.1:8000/v1 \
      python3 -I scripts/run_proposer_recall.py data/ddxplus/release_validate_patients 200

**The bar is 40% recall at k=10.** Under it, the advice feature does not ship as a claim.

## Next

1. Proposer recall with a real model — the go/no-go above.
2. Model confidence against the naive Bayes margin on the risk-coverage curve. Beating
   the completeness grid with real logprobs is the point: a better scorer does not make answers
   cheaper, it makes more of them answerable. We have already measured one step of that axis the
   cheap way — naive Bayes at 22.6% against a linear model at 99.6% moved the best policy from
   answering 5% of cases to answering 98% — so the GPU run extends a curve rather than starting one.
3. The PP3/BP4 evidence line for module B via ESM-2. The time sink there is mapping HGVS to a
   position in a protein sequence, not the model.

## Open issues

- ~~`value_per_cost` over-rewards cheap items~~ — fixed 13 Oct. A gap under 0.05 bits now scores
  zero, and `by_cost_effectiveness` drops anything settling less than a quarter of what the best
  option settles before ranking by bits per unit cost. In the clinical schema that stops a free
  history question (0.085 bits, highest bits-per-cost of anything on the table) from outranking an
  ECG. The page exposes both orderings and labels which one it is showing.
- ~~Numeric fields render raw~~ — fixed 13 Oct. A contiguous integer range is recognised as a
  scale, so "How fast did the pain appear? -> 5" now reads "5 of 10". Display only; the join keys
  are untouched.
- DDXPlus is rule-based synthetic, so recovering a deleted field may partly mean recovering the
  generator. MedQA was pre-registered as the cross-check and **was not run** — it needs a model, and a weak CPU scorer would repeat the mistake that killed our first headline. So every number here is DDXPlus-only and the claim that the method generalises past one synthetic generator is unsupported (`docs/results/2026-10-13-the-cross-check-we-did-not-run.md`).
- Module B has 182 contested CIViC groups. That is a demo and a small result, not a headline.
