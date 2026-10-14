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

| evidence kept | answer everything | answer the confident quarter |
|---|---|---|
| 100% | 99.6% | 1,500 of 1,500 |
| 40% | 94.0% | 1,500 of 1,500 |
| 20% | 73.5% | 99.9% |

Refusing pays at every level of completeness, and how much to refuse changes by a factor of fifty
across them. On a complete record the product is nearly pointless, and the page says so.

**And it does not ask you how complete your record is.** It used to, which is absurd — that is the
problem, not an input to it. It calibrates against how many findings it has in hand, estimates how
much of the record is missing to a mean absolute error of 0.057, and refuses outright below a
floor. On 30,000 records of undeclared completeness: **99.96% right, 5 wrong, on the 45.8% of
cases it chooses to answer** — against 81.8% and 5,460 wrong if it answers everything.

The original motivation was that the confidence was **40 points underconfident at 40% evidence**.
Refitting the scorer on records with holes cut that to **8.2 points**, so most of it was a bug in
how we trained rather than a property of confidence under missingness, and we say so. What
survives is the part that motivates the gate: one raw threshold still does not transfer — a
cut-off chosen on 60%-complete records promises 95% and delivers **44.9%** on a tenth of one.

**And it was tested against records that do not go missing at random**, which is what every
version of this did before. Remove the same number of findings seven realistic ways — the
follow-ups never happened, no history was available, the detail went and the screen stayed — and
accuracy at a fifth of a record runs from 8.9% to 96.4% depending only on which fifth. The
refusal rule was tested in 26 of 35 cells, the other 9 going silent, and keeps its promise in 24
of 26. The two it does not answered 19 cases and 1 case, so neither carries weight.

**The advice half.** One question, from a record cut to three findings, 4,000 held-out patients:
77.8% without it, 78.5% asking at random, **88.8% asking what the engine says**. The ranking rule
is `log2(number of answers the question admits)`, weighted by how often the question gets answered
at all. In clinical terms: characterise what you already know before asking about one more symptom.

**What it is worth.** The prices in the cost model are no longer ours: a triage call at C$10–27
(CCOHTA 2003), and the expected cost of a confident wrong answer from a 4.4% serious-harm rate
against an 11.1% error rate on dangerous presentations (Newman-Toker, *BMJ Qual Saf* 2024) times a
$422,000 average paid claim (CRICO). That makes a wrong answer worth 211 to 8,356 handovers, not
the 20 we had assumed. Carried honestly the objective breaks — above about 4,000:1 the cheapest
policy is to answer nothing — which is why the product sells throughput at a fixed quality bar
instead: **answering everything puts 176 wrong answers into every 1,000 records; holding a 95%
bar puts 0.13 there and still takes 45.5% of the queue off a person's desk.**

**What we got wrong, with dates on it.** We published that expected information gain — the
objective the literature uses — measured *worse than asking nothing at all*, 41.3% against 42.7%.
**That is retracted.** It was an artifact of a scorer that had never seen a thin record, so every
entropy computed from its posterior was wrong on exactly the sparse cases where advice matters.
Refit the scorer and it reaches 85.5% against 77.8%. Our ranking still wins, 88.8%, but by three
points rather than thirty and against a baseline that works.

That is one of five retractions this week. The conformal comparison was **rigged in our favour**
and a reviewer caught it — we refitted the baselines on six missingness patterns and scored
ourselves with a calibrator that had seen all seven. "Holds in all 22 cells" was never in the
artifact. "The floor is what keeps the promise" did not survive the experiment that tried to
delete it. And a cost-to-serve figure sat in four files that the measurement had never produced.
All dated, in `docs/results/`, in the order it happened, with the wrong number next to the right
one.

**It does not need a form.** The engine scores structured findings; the world produces prose. An
open model reads one into the other — 72% of findings recovered from a nurse's note at 87%
precision. It is wrong often enough to matter, which is the point: scored from the note instead
of the record it answers 34% of cases rather than 41% at the same bar and introduces **zero wrong
answers**. What the reader misses makes the record look thinner, and a thinner record is exactly
what the gate refuses. The error becomes caution instead of a confident mistake. That is the
product's claim surviving a degraded input path rather than a clean one.

**And then we took it to a real queue, and it failed.** Everything above is DDXPlus — synthetic
patients, with evidence hidden the seven ways *we* chose. So we ran it on **72,004 real emergency
department visits** (CDC NHAMCS, 2018–2022), fitted on 2018–19 and measured on 2021–22 across 374
sites sharing none with the fit years. **Four conditions were pre-registered and committed before
it ran. One was met.**

At a 95% target it cleared 12,899 visits to go home and **303 of them needed a bed** — 6.4% of
every escalation in the test years. On that task, on that data, it is not deployable, and we
published it as a loss with the pass marks still visible.

Then we fixed the obvious excuse. The pre-registration had blamed our own feature engineering, so
the vital-sign bands went from five to twelve, the reason codes from 60 to 300, and eighteen
chronic-condition flags went in: 15 fields became 40. **The scorer improved on every measure** —
AUC 0.8214 → 0.8439 — **and the verdict did not move.** So it is the task and not the features: a
binary outcome at a 14.7% base rate never produces the extreme posteriors a precision gate needs,
and the ceiling *any* rule can reach there is 84.6% precision at 8.9% recall.

That result narrowed who this is for, and the narrowing is in `docs/BUSINESS.md`: an operator
whose engine produces a **rich differential over many conditions**, not acuity prediction from
vitals. It is a measurement now rather than a preference.

**The one thing compute cannot buy, in progress.** No clinician has read a single output of this
system — the largest untested assumption in the project. Thirty outputs are laid out for review at
a neutral URL, the true condition deliberately absent so nothing anchors the reviewer, with the
two cases the gate got wrong included and unmarked. Whatever comes back will be described exactly:
*"one final-year medical student reviewed 30 outputs"*, never "clinically validated".

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

- **the vision model reading a photograph** — `Qwen/Qwen2.5-VL-7B-Instruct`, licence verified
  apache-2.0, measured head-to-head against the CPU reader on identical images. The product takes
  a photo of a note today and pulls the text out with browser OCR, which handles printed text and
  handles handwriting badly; this is the job that genuinely needs the hardware and the one a judge
  can watch happen. Two ROCm hazards are written down in `GPU-DAY.md` before the day rather than
  during it, both of which produce *plausible text from a broken kernel*, so the first act of the
  day is an image whose text is known exactly.
- which open model was served on MI300X with vLLM on ROCm, and its served name
- proposer recall at k=10 against the 40% bar — the go/no-go
- ESM-2 650M on ROCm against the 35M CPU floor: does the 21.9% wrong-sign figure move
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
