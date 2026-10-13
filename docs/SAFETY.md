# How this behaves when it is wrong

The health track asks five questions directly, and the product was designed around the answers
rather than retrofitted to them. Each answer below points at code or at a measurement, because an
answer with nothing behind it is a paragraph.

**This is a research prototype. No clinician has reviewed any output. It does not diagnose and it
is not medical advice.** The data is synthetic — DDXPlus is rule-based — and the variant examples
come from a public knowledge base.

## 1. Incorrect responses

The product exists because of this question. Being wrong *while confident* is the failure mode it
is built to remove, and the removal is measured rather than asserted.

On 6,000 held-out cases holding a fifth of the evidence, answering everything is right 39.9% of
the time. Answering only the most confident quarter is right 73.5%. Priced at 100 for a confident
wrong decision and 5 for a referral, cost per case falls from 60.15 to 5.24 — and the direction
holds across all seven price ratios tested, down to a referral costing half a wrong answer
(`docs/results/2026-10-13-the-scorer-was-the-bottleneck.md`).

The scorer behind that is 99.6% accurate on *complete* records, so this is not a weak model being
flattered by a filter. The first version of this measurement was exactly that, and it was caught
and replaced rather than shipped.

It is still wrong sometimes, and the interface never hides that. The accuracy on answered cases is
printed next to the answer, with its confidence interval, at whatever bar the dial is set to.

## 2. Sensitive information

Nothing personal enters the system. Demo records are synthetic DDXPlus cases; the variant cases are
CIViC, which is CC0. MIMIC-IV was excluded on purpose — its data use agreement forbids
redistribution, which is incompatible with a public repository (`docs/DATA.md`).

The deployed app stores nothing a visitor types. There is no account, no upload, no logging of case
content, no analytics. Fields are scored and the response is returned.

## 3. Uncertain results

Uncertainty is the output, not a footnote on it. Every assessment returns:

- the full distribution over outcomes, not a single label;
- entropy in bits;
- the confidence against the threshold that decided whether to answer at all;
- an estimate of **how much of the record is actually here**, and a refusal below a floor;
- **how often one more fact would change the decision** — served as that, not as a
  "sufficiency" score, because the old name read as 96/100 on a record too thin to judge;
- for each missing field, how many answers it admits (which is what decides the order, measured),
  its expected information gain in bits (shown, but measured to be a worse ordering than random),
  what it costs and how many minutes it takes;
- for each present field, how much the current answer **rests on** it, from the ablation map.

The number on the dial and the number the server uses to refuse are the same number, read off the
same baked curve. They were two separate values during the build, which is a bug we found and
fixed — the dial would have looked decorative while the server answered everything.

## 4. High-risk decisions

The system does not make them. It never selects a treatment, a dose or a disposition; the outcome
space is a label over a public dataset. Its only decision is **answer or hand over**, and that
decision is tuned to be pessimistic: holding a 95% bar, it answers about **35%** of a mixed stream
and hands over the other two in three.

Costs are asymmetric by design. A referral is cheap and a confident wrong answer is expensive, so
the threshold is set from that asymmetry rather than from accuracy alone.

## 5. Human review, and knowing when to ask for it

Refusal **is** the handoff, and it is the common path rather than the exception. A refusal returns
a ranked, costed work list — what to get, in what order, why each item matters in bits, what it
costs and how long it takes — so the person receiving the case gets a next action rather than a
shrug.

Refusal applies to the **answer**, never to the interaction. Every case produces a work item:

- **Confident** — the answer, plus the fields it rests on.
- **Not confident** — the ranked gaps, their cost and delay, and the handoff.

Coverage of useful output is 100%. Coverage of confident wrong answers is what gets driven to zero.

## What we will not claim

- Not clinically validated. Not reviewed by a clinician. Not for use on real patients.
- On a complete record this product is nearly pointless: the scorer is already 99.6% right and the
  cheapest policy answers 98% of cases. It earns its keep on thin records, and we say where the
  line is rather than leaving it vague.
- DDXPlus is rule-based synthetic data, so recovering a deleted field may partly mean recovering
  the generator. MedQA was pre-registered as the cross-check and **was not run**, so nothing here is evidence that the method survives a different dataset (`docs/results/2026-10-13-the-cross-check-we-did-not-run.md`).
- The question-ranking half now **is** measured useful — 88.8% against 78.5% for asking at random,
  with one question from three findings — but only after the principled objective was thrown out:
  ranking by expected information gain scored *worse than asking nothing at all*. The working rule
  is a property of the question, not of the model's beliefs.
- Three bugs in that measurement were found by us, after publishing a first version of it, and all
  three had pointed in our favour. They are listed in the write-up rather than quietly corrected.
- **The word "calibrated" was doing work it had not earned, and we checked.** The scorer's margin
  is honest on a complete record and 40 points underconfident at 40% evidence, so a single
  threshold cannot hold a precision promise across records of different completeness. The app now
  calibrates against how many findings it has, estimates how much of the record is missing, and
  refuses outright below a floor — two mechanisms, because one measured insufficient. On a mixed
  stream it is 99.6% right on the 34% of cases it answers, against 67.1% answering everything.
- **An impossible record is refused as impossible.** Tick all 223 boxes and the shipped model used
  to answer "Pneumonia" at a calibrated 0.96 — the calibration had only ever seen subsets of real
  records, so a superset ran off the end of it. The largest record in the fitting data holds 37
  findings; anything above 44 is now refused with that stated. The response still shows what the
  calibration would have claimed, as the evidence for why the check exists
  (`docs/results/2026-10-13-trying-to-break-it.md`).
- It will never print "100% likely to be right". The calibration's top block sits at exactly 1.0
  and the display is capped below it on purpose.
- **Records do not go missing at random, and we stopped pretending they do.** Seven realistic
  patterns measured; at a fifth of a record, accuracy runs from 8.9% to 96.4% depending only on
  which fifth. The calibration is fitted against all seven. Anyone deploying this should refit it
  against the way records go short where it runs — the cost of not doing so is three points of
  precision on a promise of ninety-five, measured.
- The concept is not novel. MediQ (NeurIPS 2024) posed the interactive version of this problem
  first; the contribution here is the calibrated refusal and its price, not the idea.
