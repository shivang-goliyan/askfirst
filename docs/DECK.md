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
4. Each absent field ranked by how much it could tell you, then by cost and minutes.
5. Unstable under ablation → refuse, return the ranked gaps, hand over.

## 4 — The measurement

6,000 held-out DDXPlus patients, 49 conditions, 2% chance. Trained on complete records,
tested on incomplete ones.

| evidence present | findings | answer everything | answer the top 25% |
|---|---|---|---|
| all of it | 15.6 | **99.6%** | 100.0% |
| 60% | 9.0 | 96.2% | 99.9% |
| **40%** | 5.8 | **82.6%** | **98.3%** |
| **20%** | 2.7 | **39.9%** | **73.5%** |
| 10% | 1.2 | 17.1% | 44.9% |

**The scorer is 99.6% right on a complete record — then take the record away.** At three findings
it is 39.9%, and refusing the least confident takes it to 73.5%. Margin beats entropy at every
coverage level. *Source: `docs/results/2026-10-13-the-scorer-was-the-bottleneck.md`.*

Say on the slide, not in the footnote: this was measured wrong the first time. A naive Bayes at
22.6% made refusing look four times better than it is, and we found it and re-ran everything.

## 5 — What refusing is worth

A confident wrong decision costs 100, a referral to a person costs 5.

| evidence present | always answer | cheapest | answers | saving |
|---|---|---|---|---|
| all of it | 0.42 | 0.26 | **98%** | 38% |
| 60% | 3.80 | 2.05 | **80%** | 46% |
| 40% | 17.43 | 4.00 | **35%** | 77% |
| 20% | 60.15 | 5.24 | **2%** | 91% |

**Refusing pays at every level of completeness, but how much to refuse changes fifty-fold.** That
is a setting, not a slogan — and the page moves it while the server obeys the same number.

Then the robustness line: seven price ratios at 20% evidence give savings from 28% to 98%. Even
when a referral costs half a wrong answer it is 28% cheaper. **We do not need to know a buyer's
cost of a confident mistake; the direction does not depend on it.**
*Source: `docs/results/2026-10-13-the-scorer-was-the-bottleneck.md`.*

## 6 — Why this needs an open model on AMD

Step 2 is the whole argument. The product is built on the **distribution** — entropy, information
gain, a calibrated threshold. A closed API returns text, not a distribution. There is no version
of this that works behind one.

So: open weights, served on vLLM on an MI300X, scored with `echo` + prompt logprobs.

And the honest framing of what the hardware buys, which is not "faster":

> **A better model does not make the answers cheaper. It makes more of them answerable.**

The CPU model is already 99.6% on a complete record, so a bigger one buys nothing there. It buys
the thin end: at a fifth of a record the refusal goes **silent**, because no cut-off reaches a
useful precision, and every one of those cases goes to a person. A stronger scorer raises how much
of that the machine can take at the same promise. The CPU floor is measured, so the comparison
*is* the AMD result.

(This paragraph said "a naive Bayes is 21% accurate" until 13 Oct. That scorer has been dead since
the headline was re-measured; if any other slide still argues from it, it is stale too.)

## 6b — The hole in that setting, and the fix

The grid needs to know how complete the record is, and nobody deploying this knows that. Measured:
the margin is honest on a full record and **40 points underconfident at 40% evidence**, so a
cut-off chosen on complete records promises 95% and delivers **48%** on a tenth of one.

Two pieces, because one measured insufficient: calibrate on **findings in hand** (observable where
the fraction is not), and **estimate how much of the record is missing** (error 0.057), refusing
outright below a floor. On 30,000 records of undeclared completeness: **99.6% right, 45 wrong, 35%
answered** against 67.1% and 9,874.

The line to say out loud: *the page now tells you what it thinks instead of asking you.*

Then the robustness half: records do not go missing at random, and we tested seven ways they
actually go short. Accuracy at a fifth of a record runs **19.6% to 73.2%** depending only on which
fifth. The rule holds in 33 of 35 cells; it broke on the likeliest pattern, and fixing it needed
the pattern in the fit **and** a feature for how unusual the findings are, and even then it reaches
only 93.6% against a 95% promise. Say that we could not fully fix it.

## 7a — What we got wrong, 1 of 2: the measurements

Keep both of these. Four of six winners in this series shipped a visible don't-be-confidently-wrong
mechanism, and judges in this track reward stated limits. It was one slide until it stopped fitting
on a screen, which is its own kind of signal.

- **The headline that measured our own baseline**, killed by us, re-run end to end.
- **The French-to-English label join**, caught before the GPU run rather than during it.
- **Three bugs in our own ranking measurement, all three in our favour.** Fixing the first two made
  the published method we beat *worse*.
- **"Calibrated" was a word we had not earned**, so we checked: honest on a full record, forty
  points underconfident at 40% evidence.

## 7b — What we got wrong, 2 of 2: the objectives and the assumption

- The table of four ranking objectives, three of them below a coin, ending at 72.5% for the one
  that needs no beliefs at all.
- **Records do not go missing at random.** Seven realistic patterns; 19.6% to 73.2% at a fifth of a
  record. The refusal broke on the likeliest one and we could not fully fix it — 91.5% to 93.6%
  against a 95% promise. An earlier ladder said we had; it came from a scratch script.

Not on the slide, still in the repo, say it if asked: cheap-proposes-then-model-ablates caps the
system near 32% because shortlist recall at k=20 is 31.8%. DDXPlus is synthetic. Not clinically
validated, and no clinician has reviewed any output.

## 8 — Safety, as the track requires

One slide, five answers, pointing at `docs/SAFETY.md`. Incorrect responses → measured, 39.9% → 73.5% on thin records.
Sensitive data → none enters, MIMIC-IV deliberately excluded. Uncertainty → it is the output.
High-risk decisions → never made; the only decision is answer-or-hand-over. Human review → refusal
*is* the handoff, and it carries a ranked costed work list.

## 9 — Prior art, and the head-to-head

**MediQ**, NeurIPS 2024 (arXiv 2406.00922), posed the interactive version first — and found that
naive prompting to ask questions **lowered** accuracy by 11.3%; their self-consistency fix gave
+22.3%, leaving a 10.3% gap against full information. **Q4Dx** (Nature Sci Rep 2026) built an
evaluation by systematically removing information from cases, which is our design, already
published.

**BALAR / MedClarify** pick the next question by expected information gain over a question set.
We implemented that objective and it lost to a coin — and to asking nothing at all. That is a
stronger thing to say than a citation.

Saying this on camera is strictly better than being told it. The contribution is not the idea —
it is the calibrated refusal, its price, and a measured ranking rule that beats the published one.

## 10 — The second domain, briefly

The same engine on variant interpretation. CIViC, CC0, 4,940 evidence rows, 585 ablatable groups
of which **182 are contested** — cases where the same knowledge base both supports and does not
support a call.

On the page, live, with a strength dial: an ESM-2 score enters as one removable evidence item. At
**supporting**, where ACMG caps it, **0 of 11 calls change**. At **clinical** strength, **5 of 11**
change and the prediction ends up on top every time. Show **EGFR S768I / erlotinib** — documented
sensitivity becoming "predicted damaging".

Say the limit in the same breath: eleven groups is a demo, not a headline, and **171 of 182
contested groups cannot take a computational vote at all**. Module A carries the number.
Link to point at: `askfirst.kgbnetwork.com/#level=B`.

## 11 — Who pays, with prices that came from somewhere

The placeholder prices (wrong = 100, handover = 5) were never argued for. The literature puts a
triage call at **C$10–27** (CCOHTA 2003) and the expected cost of a confident wrong answer at
**$4,220–$167,000** — 4.4% serious harm against 11.1% error per dangerous-disease case
(Newman-Toker, BMJ Qual Saf 2024) times $422,000 average paid claim (CRICO 2009–2013). **Ratio:
211:1 to 8,356:1 against our 20:1.** Say out loud that every saving in the deck is therefore
conservative.

Then the twist that is worth the slide: **above about 4,000:1, inside that band, cost minimisation
says answer nothing and refer everything.** The objective is wrong, not the product — clinicians
are finite and the queue has to go somewhere. So the number to sell on is throughput at a bar:
**answering everything puts 330 wrong answers per 1,000 records; holding a 95% bar puts 1.7 and
still takes 35% of the queue.**

Keep the old operating-cost note if there is time: one assessment is one generation plus a free
CPU sweep, and the exhaustive 223-field design would have cost 22 seconds of GPU per case.

## 11b — (old) Who pays, and what it costs to run

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
- Cover image: built, `docs/assets/cover.png`, rendered from `ui/cover.html`. A record with most
  of its fields greyed out, "not answering yet", and the one thing to go and get.
- No slide that says "AI-powered". The mechanism is specific; name it.
