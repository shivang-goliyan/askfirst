# The scorer now expects holes, and it cost the story more than the product — 14 October 2026

`scripts/train_scorer.py` · `src/askfirst/baked/ddxplus_softmax.npz`

Yesterday's attempt to make this product unnecessary found a 14.8-point improvement instead
(`2026-10-13-we-tried-to-delete-our-own-floor.md`). It has been shipped. This is what moved, what
got better, and the two things it took away from us.

## The change

The scorer was fitted on complete records and then asked about records with holes in them, where
a deleted finding arrives looking exactly like one that was asked about and denied. That is a
mismatch we created. It now trains on each patient once whole and twice with holes cut uniformly
at random — 90,000 rows instead of 30,000, 127 seconds on a CPU.

| held-out top-1 | complete | 60% | 40% | 20% | 10% |
|---|---|---|---|---|---|
| complete records only (what shipped until today) | 99.6% | 95.9% | 83.0% | 40.2% | 18.0% |
| **fitted with holes** | **99.6%** | **97.7%** | **93.6%** | **73.3%** | **44.2%** |

Nothing given up where it already worked. **Thirty-three points at a fifth of a record.**

## Why uniform masking rather than the seven realistic patterns

`missing.py` has seven realistic ways a record goes short, and training on all seven makes a
slightly better model on the worst of them — 44.8% against 41.9% at a fifth of a record. We used
uniform anyway, for two reasons that both matter more than three points:

- **It keeps every leave-one-pattern-out experiment honest.** If the scorer had seen all seven
  patterns, the pattern the post-processors are asked to generalise to would be one the scorer was
  trained on, and those folds would be testing the post-processors rather than the pipeline. A
  reviewer flagged exactly this about the augmented arm in yesterday's experiment.
- **Uniform costs nothing on complete records.** Training on the patterns costs a tenth of a
  point there; uniform costs zero.

## What got better

| per 1,000 records at a 95% promise | before | after |
|---|---|---|
| never reach a person | 352 | **455** |
| answered wrongly | 1.7 | **0.13** |
| review capacity returned, at C$10–27 a call | C$3,500–9,500 | **C$4,546–12,274** |

On the 30,000-record mixed stream of undeclared completeness: answering everything goes from
67.1% to **81.8%** right, and the gate from 99.6% right with 45 wrong on 34.9% of cases to
**99.96% right with 5 wrong on 45.8%**.

Under the seven-fold missingness shift it is still the only rule that keeps the 95% promise in
all seven, and its worst fold improves from 98.5% to **99.7%**.

## What it took away — first, the motivating number

The page-stops-asking result rested on a sentence that is no longer true of the shipped scorer:

> the margin is honest on a full record and **40 points underconfident at 40% evidence**

Refitted, that gap is **8.2 points**. The scorer is now honest on complete records (ECE 0.005)
and mildly underconfident as the record thins (2.1% at 60%, 8.2% at 40%, 22.9% at a fifth).

So most of the miscalibration the calibration layer was built to correct **was a bug in how we
trained the scorer, not a property of confidence under missingness.** We fixed it at the root. The
honest version of the original claim is narrower: a linear model's logits shrink as features drop
out *when it has never seen features drop out*.

What survives is the part that actually motivates the product: **one raw threshold still does not
transfer across completeness.** A cut-off chosen on 60%-complete records promises 95% and delivers
**44.9%** on a tenth of one. That table is in `calibration.json` under `transfer` and it is the
reason the gate exists.

## And second, our margin over the simple rules

A better scorer helps the naive baselines too, and it helped them more than it helped us:

| seven folds, everything refitted per fold | before | after |
|---|---|---|
| one global threshold | 4 of 7 | 3 of 7 |
| a threshold per group (Mondrian) | 5 of 7 | **6 of 7** |
| a threshold per group + our floor | 5 of 7 | **6 of 7** |
| the completeness floor alone, no calibration | 3 of 7 | **6 of 7** |
| **the gate** | 7 of 7 | 7 of 7 |

We are still the only rule that holds every fold. But the floor alone went from breaking four
folds to breaking one, and in distribution it now keeps the promise outright where yesterday it
broke it at 93.7%.

That is the same finding as `2026-10-13-is-it-a-layer-or-is-it-our-model.md` arriving from the
other direction. There, the calibration bought **+10.6 points** of ordering on a badly-shaped
naive Bayes and nothing on a well-shaped scorer. Here we made our own scorer better-shaped and
watched our advantage over the simple rules narrow.

**So the claim this project can defend is a conditional one.** The gate's value is inversely
proportional to how well-calibrated your model already is — and since nobody deploying a triage
model knows which case they are in, and since the fix is a training change nobody has made, it is
worth having. That is a smaller claim than "the gate is what makes this safe", and it is the one
the measurements support.

## What a reader should distrust

- **Every dated write-up before today measured the previous scorer.** The artifacts under them
  have been regenerated, so a figure in prose from before 14 October may disagree with the JSON
  beside it. Each affected file carries a note saying so. The write-ups were not rewritten,
  because they are the record of what was measured when.
- **The 99.96% is five wrong answers in 13,743.** It is a sample, not a guarantee, and it is
  printed to four significant figures precisely so it never reads as 100%. A helper in
  `metrics.py` now refuses to print a precision that would round to 100%, and prints "n of n"
  rather than a percentage when a sample really did have no wrong answers.
- **None of this touches the real queue.** NHAMCS still scores 1 of 4 pre-registered conditions,
  unchanged, because that experiment fits its own scorer on real records that already have real
  holes in them. Masking augmentation has nothing to fix there, which is itself a small piece of
  evidence that the gain here is about the synthetic-record mismatch rather than about missingness
  in general.
