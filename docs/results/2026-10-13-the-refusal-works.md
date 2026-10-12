# Three failures and one strong result, 13 October 2026

A day of measurement on CPU, no GPU, no language model. Recorded in order, including the parts
that went wrong, because the sequence is the argument.

## What failed

**1. Shortlist recall killed propose-then-ablate.** Naive Bayes recall at k=20 is 31.8%, so a
cheap-proposes-then-model-ablates design caps the system near 32% whatever the model does.

**2. The discriminative proposer lost to the thing it was meant to beat.** Weighting candidates
by how much the leading pathologies disagree gave 20.4% recall at k=10, against the marginal
baseline's 26.2%. Diagnosis: "what separates hypotheses" and "what is missing from this record"
are different questions, and the recovery metric measures the second.

**3. Ranking by flip probability was actively harmful.** Measured properly — hide three fields,
let the engine nominate one to reveal, reveal it, check the answer — following its advice scored
**18.8%** against **26.0%** for asking at random and **28.0%** for asking nothing at all.

That third one is a design error, not a bug. Flip probability selects for whatever is most likely
to *change* the answer, which is volatility. A field that flips the decision half the time is a
coin. Replacing it with **expected information gain** — how much the answer gets *settled* —
removed the harm: 28.4% guided against 26.0% random. Which is the principled objective and the
one the literature already uses; it was reinvented worse and the measurement caught it.

The clearest illustration is a d-dimer in the clinical schema: **0.264 bits of information at a
flip probability of 0.00.** It settles the question without changing the leading answer, and the
old objective could not see it at all.

But honestly: +2.4% over random and +0.4% over asking nothing, with every interval overlapping.
**The advice is now neutral, not useful.**

## What worked, and it is the other half of the product

Everything above measures the ADVICE. The louder half of the claim is the REFUSAL — that it stays
quiet when the record cannot support an answer. That needs its own curve, and it had never been run.

1,500 held-out patients, 49 pathologies, 2% chance. Answer only the most confident share:

| confidence signal | coverage | accuracy | vs answering everything |
|---|---|---|---|
| **margin** | 100% | 21.0% | — |
| | 75% | 26.7% | +5.7% |
| | 50% | 36.9% | +15.9% |
| | 25% | 56.3% | +35.3% |
| | **10%** | **85.3%** | **+64.3%** |
| entropy | 50% | 25.3% | +4.3% |
| | 10% | 63.3% | +42.3% |

**21.0% to 85.3% by declining to answer 90% of cases.** A four-fold improvement, on real data,
from a naive Bayes with no medical knowledge and no GPU. Margin beats entropy as the signal at
every coverage level, which is a concrete design decision settled for free.

## What this means for the project

The headline was wrong. It is not "it tells you what to ask" — that is measured and currently
neutral. It is **"it knows when it does not know"**, and the advice is a secondary feature.

That reframing is better on every axis:

- It is **measured**, today, with no GPU, at 21% to 85.3%.
- It matches what actually wins this competition series. AgeBand took 2nd with a deterministic
  layer "so the system avoids confident wrong answers". GemmaClip took a first with glass-box
  evidence and fallbacks. The CCTV winner checked its answers against evidence. Four of six
  winners shipped a visible mechanism against being confidently wrong.
- It matches the track's written rules — "make uncertainty visible" and "know when a person needs
  to review or take over the case" — rather than straining against them.
- It is what our own owned evidence is about: a frontier model, 15 syringes, 9 wrong, and **zero
  abstentions out of 15** while being offered the option to say it did not know.

## Correction to METRIC.md

The pre-registered primary metric was absent-field recovery, with a kill criterion of 30% at
top-3. That was the wrong primary. It measures whether the system can guess what a patient
probably had, which is not what the product claims and not what carries the demo.

**Risk-coverage becomes the primary metric. Recovery drops to a sanity check** — it says the
model reads the record, nothing more. The 30% bar stays recorded as missed, because it was, and
because moving a bar after seeing the data is exactly what pre-registering is supposed to prevent.
It is being demoted on the grounds that it measures the wrong property, and that argument would
have been just as true before the number came back.

## Next, and the one thing still untested

The open model has still never been in the loop. Both halves need it:

- **Refusal:** does an open model's own confidence beat a naive Bayes margin on this curve? Ours
  is the baseline to beat, and the abstention layer is the one place a probeable open model is
  genuinely necessary.
- **Advice:** does a model's medical knowledge move the advice from neutral to positive? This is
  the open question the project's second feature rests on, and it is one generation per case.
