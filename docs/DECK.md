# The deck, slide by slide

Eleven slides. Every number carries the file it came from, so the person building the slides never
has to invent one and the person checking them on 17 Oct can trace each one in a minute. If a
number is not in `docs/results/`, it does not go on a slide.

---

## 1 — Title

> **askfirst**
> It finds the one missing fact that would change the answer, and refuses to answer until it has it.

Live URL. Repo URL. Track 2, Health and Wellbeing.

## 2 — The failure, shown not described

A commercial vision model was asked to read 15 photographs of real syringes. It was explicitly
offered "unknown" as a valid answer.

- Wrong on **9 of 15**.
- Said **unknown zero times out of 15**.
- Read **1.0 mL from an empty syringe**.
- Gave **two different answers to the same image file** — byte-identical, same checksum.
- Worst single error **+71%**.

*Source: our own run, logged. Supporting published work: MeasureBench (arXiv 2510.26865) puts a
frontier model at 19.8% on measurement reading, 2.0% on composite gauges.*

The problem is not that it was wrong. The problem is that it was **certain** and wrong, and nothing
in the output distinguished that case from a correct one.

## 3 — What askfirst is

Not a diagnosis tool. A gate in front of whichever model makes the call, answering a narrower and
more answerable question: **is there enough here?**

Five steps, one diagram:

1. Record split into atomic fields.
2. Open model scores it — the full distribution is kept, not a sampled answer.
3. Each present field removed in turn → what the answer rests on.
4. Each absent field ranked by expected information gain, then by cost and minutes.
5. Unstable under ablation → refuse, return the ranked gaps, hand over.

## 4 — The measurement

1,500 held-out DDXPlus patients, 49 conditions, 2% chance.

| coverage | accuracy | confident wrong |
|---|---|---|
| 100% | 21.0% | 1,185 |
| 25% | 56.3% | 164 |
| 10% | **85.3%** | 22 |
| 5% | 98.7% | 1 |

**21.0% → 85.3% by answering one case in ten.** Margin beats entropy as the confidence signal at
every coverage level. *Source: `docs/results/2026-10-13-the-refusal-works.md`.*

Footnote on the slide, not buried: the 98.7% row is 74 of 75 answered cases; the honest floor is
**92.8%**, Wilson 95%.

## 5 — What refusing is worth

A confident wrong decision costs 100, a referral to a person costs 5.

**79.00 per case → 4.82. 94% cheaper. 74,183 saved per thousand cases.**

Then the slide that wins the business criterion — the robustness table. Seven price ratios, saving
from 41% to 99%, optimum never leaving 5-10% coverage. **We do not need to know a buyer's cost of
a wrong confident answer; the sign of the result does not depend on it.**
*Source: `docs/results/2026-10-13-economics.md`.*

## 6 — Why this needs an open model on AMD

Step 2 is the whole argument. The product is built on the **distribution** — entropy, information
gain, a calibrated threshold. A closed API returns text, not a distribution. There is no version
of this that works behind one.

So: open weights, served on vLLM on an MI300X, scored with `echo` + prompt logprobs.

And the honest framing of what the hardware buys, which is not "faster":

> **A better model does not make the answers cheaper. It makes more of them answerable.**

The CPU baseline reaches its optimum at 5% coverage because a naive Bayes is 21% accurate overall.
A stronger scorer moves that optimum to higher coverage at the same cost. That is the measured
baseline the GPU run improves on, and the comparison is the AMD result.

## 7 — The honesty slide

Keep it. Four of six winners in this series shipped a visible don't-be-confidently-wrong mechanism,
and judges in this track reward stated limits.

- Four dead ends, dated, in the repo — including one where **our own ranking objective made results
  worse than asking at random** (18.8% vs 26.0%), which we measured, diagnosed and replaced.
- The question-ranking half is **neutral**: 28.4% vs 26.0%, intervals overlapping. It ships as an
  aid, not a claim.
- DDXPlus is synthetic. Stated, not buried.
- Not clinically validated. No clinician has reviewed any output.

## 8 — Safety, as the track requires

One slide, five answers, pointing at `docs/SAFETY.md`. Incorrect responses → measured, 1,185 → 22.
Sensitive data → none enters, MIMIC-IV deliberately excluded. Uncertainty → it is the output.
High-risk decisions → never made; the only decision is answer-or-hand-over. Human review → refusal
*is* the handoff, and it carries a ranked costed work list.

## 9 — Prior art, and the head-to-head

**MediQ**, NeurIPS 2024 (arXiv 2406.00922), posed the interactive version first — and found that
naive prompting to ask questions **lowered** accuracy by 11.3%; their self-consistency fix gave
+22.3%, leaving a 10.3% gap against full information. **Q4Dx** (Nature Sci Rep 2026) built an
evaluation by systematically removing information from cases, which is our design, already
published.

Saying this on camera is strictly better than being told it. The contribution is not the idea —
it is the calibrated refusal, its price, and the measurement that the advice half does not work yet.

## 10 — The second domain, briefly

The same engine on variant interpretation. CIViC, CC0, 4,940 evidence rows, 585 ablatable groups
of which **182 are contested** — cases where the same knowledge base both supports and does not
support a call. Demo case: **DNMT3A R882 in AML**, level-B evidence on both sides at ratings 3
and 4.

Say the limit in the same breath: 182 groups is a demo, not a headline. Module A carries the number.

## 11 — Who pays, and what it costs to run

The buyer is anyone already deploying a model against incomplete records and carrying the cost of
its confident mistakes: triage and teleconsult services, decision-support vendors who need a
safety layer they can show a regulator, lab networks deciding which test to run next.

The unit economics are the pitch. One assessment is one generation plus a sweep the CPU does for
free. The expensive thing in the current pipeline is **not** the refusal — it is an exhaustive
223-field sweep with a language model at ~22 seconds of GPU per case, which is why the design
inverts it: the model proposes about ten fields in one pass, and the cheap scorer ablates
exhaustively at no cost.

Close on the live URL and invite them to try to make it answer something it should not.

---

## Build notes for whoever makes this

- Dark, plain, one accent colour. The numbers are the design.
- Slide 4 is the hero — one table, big type, nothing else on it.
- Screenshots come from the deployed URL, not localhost. A judge will notice.
- Cover image: the coverage dial at 10% with "85.3%" legible at thumbnail size.
- No slide that says "AI-powered". The mechanism is specific; name it.
