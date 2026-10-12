# What refusing is worth, 13 October 2026

"It declines to answer" is a weak claim. Priced, it stops being weak.

1,500 held-out DDXPlus patients, 49 pathologies, naive Bayes scorer, margin as the confidence
signal. A confident wrong decision costs 100, a referral to a person costs 5, a correct answer is
free. Sweep coverage and price the mix.

| coverage | accuracy | wrong | referred | cost per case |
|---|---|---|---|---|
| 100% | 21.0% | 1,185 | 0 | 79.00 |
| 75% | 26.7% | 825 | 375 | 56.25 |
| 50% | 36.9% | 473 | 750 | 34.03 |
| 25% | 56.3% | 164 | 1,125 | 14.68 |
| 10% | 85.3% | 22 | 1,350 | 5.97 |
| **5%** | **98.7%** | **1** | 1,425 | **4.82** |

**Always answer: 79.00 per case. Refuse when unsure: 4.82. That is 94% cheaper, or 74,183 saved
per thousand cases.**

## Is that an artefact of the prices?

No. Seven combinations, and the optimum never moves far:

| wrong : referral | best coverage | saving |
|---|---|---|
| 100 : 5 | 5% | 94% |
| 100 : 20 | 5% | 76% |
| 100 : 50 | 10% | 41% |
| 50 : 5 | 5% | 88% |
| 20 : 5 | 5% | 70% |
| 10 : 5 | 10% | 41% |
| 100 : 1 | 5% | 99% |

Even when a referral costs half what a wrong answer costs — an absurdly pessimistic ratio for any
clinical setting — refusing is still 41% cheaper. The result does not depend on choosing flattering
prices.

## Two things to say out loud before anyone quotes this

**The 98.7% rests on 75 answered cases.** 74 right out of 75. The Wilson interval is
[92.8%, 99.8%], so **92.8% is the number to quote**, not 98.7%.

*Corrected 13 Oct, same day:* this paragraph first said 75 of 76, which contradicted the table
directly above it — 1,425 referred out of 1,500 leaves 75 answered, not 76. The count came from a
different coverage step. The table was right, the sentence was wrong, and the interval moves from
[93.0%, 99.8%] to [92.8%, 99.8%]. The baked curve in `src/askfirst/baked/curve.json` stored the
correct figures throughout.

**The optimum sitting at 5% coverage is partly our own scorer's fault.** Naive Bayes is 21%
accurate overall, so the confidence signal has to cut deep before it finds a reliable subset. A
better scorer moves the optimum to higher coverage at the same cost — which is a strictly better
product, and it is the clearest statement of what the GPU actually buys:

> **A better model does not make the answers cheaper. It makes more of them answerable.**

That is the AMD workload justified in one sentence, with a measured baseline to improve on.

## And it answers the obvious objection

A system that refuses is not a system that shows nothing. Refusal applies to the ANSWER, never to
the interaction:

- **Confident** — the answer, plus the fields it rests on, from the sensitivity map.
- **Not confident** — the ranked gaps by information gain, what each costs, how long it takes,
  and a handoff.

Every case produces a work item. Coverage of useful output is 100%. Coverage of confident wrong
answers is what we drive to zero.
