# Submission copy — draft, not posted

Nothing in here goes anywhere until Shivang approves it. Numbers are the ones currently in the
repo; if a measurement moves, this file moves with it.

---

## Title

**askfirst**

## One line

Refuses to answer until the record can carry an answer — and tells you what to ask first.

## Short description

Medical AI is graded on how often it is right. The expensive failure is being confidently wrong on
a record that was never complete enough to answer from. askfirst scores how much of the answer is
actually supported by what is in front of it, hands the case to a person when it is not, and names
the single cheapest thing to go and get. Both halves are measured on held-out data, and the write-up
includes the four objectives we tried that did not work.

## Full description

**The problem.** A triage model given half a record still returns an answer with a confidence
number on it. The accuracy figure in the paper is an average over complete cases, and the cost of
the mistakes is not symmetric: a confident wrong call on an incomplete record is the expensive one.
Nobody is grading "should this have been answered at all".

**What it does.** Two things, and it will not do the first without the second.

1. **It decides whether to answer.** The confidence cut-off is read off a measured risk-coverage
   curve, one per level of record completeness, so "how much to refuse" is a setting with a number
   behind it rather than a slogan. When it refuses, the case goes to a person — that is the
   handoff, and it arrives with a work list.
2. **It says what to go and get.** For every field the record does *not* have, it asks what the
   answer would do to the distribution, and ranks them. On the costed domain it also prices them,
   so a £0 question that settles a quarter as much as a 45-minute blood test is ranked honestly
   against it.

**What we measured.** 6,000 held-out DDXPlus patients, 49 conditions, chance 2.0%. The scorer is a
softmax regression over 972 one-hot evidence features at 99.6% top-1 on complete records — chosen
deliberately, because the first version of this result used a weak baseline and the lift turned out
to be a statement about our classifier rather than about medicine. We killed that headline
ourselves and re-ran everything.

| evidence kept | answer everything | answer the confident 25% | cheapest policy |
|---|---|---|---|
| 100% | 99.6% | 100.0% | answer 98%, saves 38% |
| 40% | 82.6% | 98.3% | answer 35%, saves 77% |
| 20% | 39.9% | 73.5% | **answer nothing** — referral beats any coverage |

Refusing pays at every level of completeness, and how much to refuse changes by a factor of fifty
across them. On a complete record the product is nearly pointless, and the page says so.

**And it does not ask you how complete your record is.** It used to, which is absurd — that is the
problem, not an input to it. The scorer's confidence turns out to be honest on a complete record
and 40 points underconfident at 40% evidence, so a cut-off chosen on full records promises 95%
precision and delivers 48% on a tenth of one. It now calibrates against how many findings it has
in hand, estimates how much of the record is missing to a mean absolute error of 0.057, and refuses outright below a
floor. On 30,000 records of undeclared completeness: **99.6% right, 45 wrong, on the 35% of cases
it chooses to answer** — against 67.1% and 9,874 wrong if it answers everything.

**And it was tested against records that do not go missing at random**, which is what every
version of this did before. Remove the same number of findings seven realistic ways — the
follow-ups never happened, no history was available, the detail went and the screen stayed — and
accuracy at a fifth of a record runs from 19.2% to 73.2% depending only on which fifth. The
refusal rule was tested in 22 of 35 cells, the other 13 going silent, and keeps its promise in 20
of the 22. The two it does not are in the write-up: 93.6% on 547 answers, and a cell that
answered one case and got it wrong.

**The advice half.** One question, from a record cut to three findings, 4,000 held-out patients:
42.7% without it, 43.7% asking at random, **72.3% asking what the engine says**. The ranking rule
is `log2(number of answers the question admits)`, weighted by how often the question gets answered
at all. In clinical terms: characterise what you already know before asking about one more symptom.

**What it is worth.** The prices in the cost model are no longer ours: a triage call at C$10–27
(CCOHTA 2003), and the expected cost of a confident wrong answer from a 4.4% serious-harm rate
against an 11.1% error rate on dangerous presentations (Newman-Toker, *BMJ Qual Saf* 2024) times a
$422,000 average paid claim (CRICO). That makes a wrong answer worth 211 to 8,356 handovers, not
the 20 we had assumed. Carried honestly the objective breaks — above about 4,000:1 the cheapest
policy is to answer nothing — which is why the product sells throughput at a fixed quality bar
instead: **answering everything puts 330.5 wrong answers into every 1,000 records; holding a 95%
bar puts 1.7 there and still takes 35% of the queue off a person's desk.**

**What we got wrong, with dates on it.** Four ranking objectives were tried and three lost to a
coin — including expected information gain, the objective the literature uses, which measured worse
than asking nothing at all (41.3% against 42.7%). Then three bugs turned up in that measurement,
every one of them in our favour, and fixing them made the objective we beat *worse*. All of it is
in `docs/results/`, dated, in the order it happened.

**It does not need a form.** The engine scores structured findings; the world produces prose. An
open model reads one into the other — 72% of findings recovered from a nurse's note at 87%
precision. It is wrong often enough to matter, which is the point: scored from the note instead
of the record it answers 34% of cases rather than 41% at the same bar and introduces **zero wrong
answers**. What the reader misses makes the record look thinner, and a thinner record is exactly
what the gate refuses. The error becomes caution instead of a confident mistake. That is the
product's claim surviving a degraded input path rather than a clean one.

**And it is checkable.** `./scripts/verify.sh` rebuilds every baked artifact from the public data
in four minutes, diffs each against what is committed, and fails naming any document that quotes a
figure the artifacts do not support. It passes byte for byte.

**A second domain.** The same engine on variant interpretation. An ESM-2 score enters a contested
CIViC group as one removable evidence item, and the strength it is granted is a dial on the page.
At *supporting*, where an uncalibrated predictor belongs, 0 of 11 calls change. At *clinical*
strength, 5 of 11 change and the prediction ends up on top every time — documented drug sensitivity
becoming "predicted damaging". 171 of 182 contested groups cannot take a computational vote at all.

**Limits, stated rather than buried.** DDXPlus is rule-based synthetic data. CIViC significance is
clinical actionability, not ACMG classification. Eleven groups is a demonstration, not a benchmark.
Nothing here is clinically validated and no clinician has reviewed any output.

## AMD — TO BE WRITTEN ON THE GPU DAY

**Rehearsed, so the AMD day is measurement rather than discovery.** Three experiments were run on
a rented commodity GPU first, with nothing baked into a measured result, exactly as the vLLM
client was rehearsed against a fake server before any hour was spent:

- **ESM-2 650M against the shipped 35M.** Sign-error rate 21.9% → 6.6%, and the Module B
  conclusion changes: 4 of 28 contested calls move at supporting strength rather than 0 of 11.
  The cap held because the small model was unsure, not because the cap was sufficient. *This is
  the AMD workload with a measured reason to exist — a model that needs the hardware, producing
  an artifact that ships, changing a safety finding.*
- **The open model as a scorer — it loses.** 35.3% against the fitted softmax's 99.6%, and its
  confidence falls only 12% when four fifths of the record is removed, where ours falls 83%. This
  killed a line the deck had been using, and we would rather have found it than been shown it.
- **The open model as a reader — it wins**, which is the job above.

**Do not submit with this section as a placeholder.** It needs the measured numbers, not a
description of an intention. What goes here, from `docs/GPU-DAY.md`:

- which open model was served on MI300X with vLLM on ROCm, and its served name
- proposer recall at k=10 against the 40% bar — the go/no-go
- model confidence against the softmax margin on the completeness grid
- ESM-2 650M on ROCm against the 34M CPU floor: does the 21% wrong-sign figure move
- one `rocprofv3` trace, for a measured kernel number rather than a described one

Every response the app returns carries `scored_by`, naming what answered, and
`threshold_calibrated`, saying whether the cut-off was measured against that scorer. That is the
AMD component being visible in the working product rather than asserted in a slide.

## Links

- Live: https://askfirst.kgbnetwork.com
- Deck: https://askfirst.kgbnetwork.com/deck.html
- Module B at clinical strength: https://askfirst.kgbnetwork.com/#level=B
- Source, every measurement, and the four dead ends: https://github.com/shivang-goliyan/askfirst
- Video: *to come*

## Tags

health, clinical decision support, selective prediction, abstention, uncertainty, calibration,
risk-coverage, ESM-2, variant interpretation, vLLM, ROCm, MI300X, FastAPI, DDXPlus, CIViC

## Cover image

`docs/assets/cover.png`, 1200x630. Source is `ui/cover.html`, so it can be re-rendered when a
number moves instead of becoming a PNG nobody can edit:

    google-chrome --headless=new --window-size=1200,630 \
      --screenshot=docs/assets/cover.png file://$PWD/ui/cover.html

Dark, monospace, the same palette as the page. One idea, legible as a thumbnail: a record with
most of its fields greyed out, the verdict reading **"not answering yet"**, and the one thing to go
and get beside it. Every number on it is real — the confidence and cut-off are what the live app
returns for a three-finding record, and the 81% is the measured answer rate for that question. No
stock photography, no stethoscopes, no glowing brains.
