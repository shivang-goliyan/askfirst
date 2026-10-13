# Where this stands

**Live at https://askfirst.kgbnetwork.com** since 12 Oct — CPU only, no GPU attached, which is the point: the headline curve is baked and cannot go dark. Redeploy with `./scripts/deploy/vm.sh`; see [DEPLOY-APP.md](DEPLOY-APP.md).

The live case on that page is now the real thing: twelve held-out DDXPlus patients scored by the
fitted softmax that ships in the image, not a hand-written sketch. Take findings away and it stops
answering. The costed hand-built case is still there on its own tab, because DDXPlus prices every
question the same and the cheapest-first ordering needs something to chew on.

**The page stopped asking how complete your record is** (13 Oct, 11:45). It used to make the
visitor pick a completeness level and read the threshold off that curve, which is the one thing a
deployment cannot know. Measured: the margin is honest on a full record and **40 points
underconfident at 40% evidence**, so a threshold chosen on complete records promises 95% and
delivers 48% on a tenth of one. Fixed with two pieces — an isotonic calibration on findings in
hand, and a ridge estimate of how much of the record is missing (error 0.057) that refuses
outright below 35%. On 30,000 records of undeclared completeness: **99.6% right, 45 wrong, on
34.9% of cases**, against 67.1% and 9,874 wrong answering everything. The only dial left on the
live case is the target precision. Write-up: `results/2026-10-13-the-page-stops-asking.md`.

**And then the uniform-missingness assumption got tested** (13 Oct, 12:30). Every number before
this hid evidence at random. Cut the same number of findings seven different realistic ways and
top-1 at a fifth of a record runs from **19.2% to 73.2%** — "20% of a record" is not one thing.
The calibrated rule survives 33 of 35 cells; its worst is 93.6% [91.2%, 95.4%] on the likeliest
pattern of all. Hold that pattern out of the fit and it breaks properly: 92.5% [90.2%, 94.3%].
**We could not fully fix that cell.** Fitting against the pattern and adding a feature for how
unusual the findings are takes it from 91.5% to 93.6%, short of the 95% promised; each ingredient
helps a little and monotonically. An earlier version of that ladder claimed the fix worked and
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
on is throughput at a bar: answering everything puts **330.5 wrong answers per 1,000 records**;
holding a 95% bar puts **1.7** and still takes 35.2% of the queue. Write-up:
`results/2026-10-13-what-it-is-worth.md`.

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

One question, from a record cut to three findings, 4,000 held-out patients: **42.9% without it,
47.9% asking at random, 72.2% asking what the engine says.** Intervals [46.3%, 49.4%] against
[71.1%, 73.8%]. An oracle told which questions this patient can actually answer gets 74.3%.

What fixed it was deleting the clever part. Ranking by **expected information gain measured worse
than asking nothing at all** (41.0% against 42.9%, with the objective implemented faithfully —
P(value | record) through the outcomes, not a population marginal), because it is an expectation taken under the
model's own beliefs and those beliefs are wrong on exactly the sparse records where advice matters.
Ranking by **answer breadth** — log2 of how many answers a question admits — needs no beliefs and
adds 13 to 29 points over a coin (24.3 at three findings). In clinical terms: characterise what you already know before
asking about one more symptom.

Re-measured after three bugs turned up, all of them in our favour: a negative answer was switching
the evidence feature *on*, the ranker assumed every question gets answered, and the harness let
`max()` break a three-way breadth tie using the engine's own sort order (worth seven points to us).
Answer rate on its own scores 42.0%, below a coin — so breadth is the mechanism, not a proxy for
"questions that tend to get answered". Write-up:
`results/2026-10-13-breadth-beats-information.md`.

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
  generator. MedQA is the cross-check and the limitation is stated rather than buried.
- Module B has 182 contested CIViC groups. That is a demo and a small result, not a headline.
