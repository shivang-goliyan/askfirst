# We were measuring our own baseline. Everything re-run — 13 October 2026

**This supersedes `2026-10-13-the-refusal-works.md` and `2026-10-13-economics.md`.** Both are kept
unedited, with a notice at the top, because deleting a wrong result is worse than having published
one.

## What went wrong

Two files in this repo disagreed about the same quantity. The baseline note claimed the naive Bayes
scored 65.3% top-1 over 49 pathologies; the abstention run reported 21.0% at full coverage. Chasing
that turned up three errors, in increasing order of seriousness.

**1. The 65.3% was simply wrong.** Re-measured under the same conditions: **22.6%**.

**2. The label join was broken.** `release_conditions.json` is keyed by the French
`condition_name` — `Pneumothorax spontané` — while the patient CSV's `PATHOLOGY` column holds the
English name, `Anemia`. The schema keyed outcomes on the French name, and this repo *documented*
that as a deliberate choice to protect the join. **Overlap with the actual labels was 1 of 42.**
Nothing measured on CPU was affected, because the naive Bayes builds its own label space from the
data. But `ModelScorer` scores `schema.outcomes` — so the GPU run would have compared French
predictions against English ground truth and produced noise at $1.99 a GPU-hour. The join key is
now `cond-name-eng` and the overlap is **49 of 49**.

**3. The scorer was the bottleneck, not the problem.** A multinomial logistic regression over the
same 972 one-hot evidence features, trained on 30,000 patients in **31 seconds on a laptop CPU**,
scores **99.6% top-1** on 6,000 held-out patients. Against 22.6%.

So `21.0% → 85.3% by refusing` was never a finding about clinical uncertainty. It was a finding
about a weak classifier, and with a real one the risk-coverage curve on complete records is **flat
at 100%**. The 94%-cheaper economics claim rested on the same mistake. Had that shipped, anyone who
spent twenty minutes fitting a linear model would have dismantled it.

DDXPlus is rule-based synthetic data. We had that written down as a caveat. It is not a caveat —
it is the dominant fact about the dataset, and a linear model very nearly inverts the generator.

## What the honest measurement is

The product's premise was never complete records. It is *is there enough here?* — so completeness
belongs on the grid. Trained on complete records, tested on incomplete ones, which is how it would
be deployed. 6,000 held-out patients, 49 conditions, chance 2.0%, evidence hidden uniformly at
random. Each cell is accuracy on the cases it chose to answer.

| evidence kept | avg findings | answer all | @75% | @50% | @25% | @10% |
|---|---|---|---|---|---|---|
| 100% | 15.6 | **99.6%** | 100.0% | 100.0% | 100.0% | 100.0% |
| 60% | 9.0 | 96.2% | 98.8% | 99.5% | 99.9% | 100.0% |
| 40% | 5.8 | **82.6%** | 91.6% | 96.3% | **98.3%** | 99.5% |
| 20% | 2.7 | **39.9%** | 48.9% | 59.6% | **73.5%** | 81.3% |
| 10% | 1.2 | 17.1% | 21.8% | 31.6% | 44.9% | 63.2% |

95% Wilson intervals are in `abstention.json`; at 6,000 cases the widest cell at full coverage is
±1 point, and every curve is monotone.

**Margin still beats entropy as the confidence signal** at every coverage level — at 40% of the
evidence, 91.6 / 96.3 / 98.3 / 99.5 against 89.6 / 94.8 / 96.7 / 98.5. That design decision
survives the re-measurement, which is worth more than if it had never been tested.

For contrast, at the same 40% of evidence the old naive Bayes reads 30.1% at full coverage and
85.5% at 10% — a bigger-looking lift from a far worse system, which is exactly how the first
version of this result fooled us.

## And the price

A confident wrong decision costs 100, a referral to a person costs 5, a correct answer is free.

| evidence kept | always answer | cheapest | at coverage | saving |
|---|---|---|---|---|
| 100% | 0.42 | 0.26 | **98%** | 38% |
| 60% | 3.80 | 2.05 | **80%** | 46% |
| 40% | 17.43 | 4.00 | **35%** | 77% |
| 20% | 60.15 | 5.24 | **2%** | 91% |
| 10% | 82.92 | 5.97 | **2%** | 93% |

The claim that survives is better than the one it replaces, and it is a different claim:
**refusing pays at every level of completeness, but how much to refuse changes by a factor of
fifty.** Answer 98% of complete records. Answer 2% of nearly empty ones. That is not a slogan, it
is a setting, and it is now the thing the page lets you move and the server actually obeys — the
baked threshold is read per completeness level, so the dial and the decision are one number.

Sensitivity at 20% of the evidence, across price ratios: 91%, 67%, 28%, 83%, 60%, 28%, 98% for
wrong:referral of 100:5, 100:20, 100:50, 50:5, 20:5, 10:5, 100:1. Even when a referral costs half
a wrong answer, refusing is 28% cheaper. The direction does not depend on flattering prices.

## What this costs us, stated plainly

- The four-fold headline is gone. The replacement is a 2.1x lift at 40% of the evidence and a
  1.8x lift at 20%, from a scorer that cannot be dismissed.
- Anything quoting 21.0%, 85.3%, 94% cheaper, 1,185 wrong answers, or 65.3% is wrong. Those
  appeared in the README, the deck, the video script, both state files and two results notes. All
  updated.
- **On complete records with a good scorer, this product is nearly pointless** — 99.6% already,
  and the best policy answers 98%. We will say that out loud rather than let someone find it.
- The scorer is a linear model on synthetic data. It would not get 99.6% on real records, and the
  completeness axis is a crude proxy for the ways a real record is incomplete — evidence is hidden
  uniformly at random here, and a real missing finding is not missing at random. MedQA remains the
  cross-check and this limit is stated, not buried.

## Reproducing it

    python3 scripts/train_scorer.py    data/ddxplus/release_validate_patients   # 31s, ships 88KB
    python3 scripts/run_abstention.py  data/ddxplus/release_validate_patients 6000
    python3 scripts/run_economics.py   data/ddxplus/release_validate_patients 6000
    python3 scripts/bake_curve.py      data/ddxplus/release_validate_patients 6000
