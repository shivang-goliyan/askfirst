# The prices were invented, so we went and looked them up — 13 October 2026

> **Measured against the previous scorer.** On 14 October the scorer was refitted on records with
> holes in them, and the artifact this file reads from has been regenerated, so figures in the
> prose below may disagree with the JSON beside them. The prose is left as the record of what was
> measured when. What moved, and what it cost the argument, is in
> `2026-10-14-the-scorer-now-expects-holes.md`.

Every economics number in this repo priced a confident wrong answer at 100 and a handover at 5.
Those were placeholders. Nobody argued for them, and the ratio between them is the only thing any
conclusion depends on. So: what does the published literature imply the ratio is?

## What a handover costs

Three Canadian jurisdictions put the cost per triage call at **C$10 to C$27** (CCOHTA Technology
Report 43, Nov 2003; INAHTA Brief 2004/53). It is twenty years old, it is Canadian, and it is the
clearest published per-call figure we could find. Nothing below leans on its precision — $20 is
used as a round middle.

## What a confident wrong answer costs

Not a malpractice payout. Most wrong answers harm nobody. The expected cost is
`P(this error ends in serious harm) × what a serious harm costs`, and both terms have a source.

**P(harm | error).** Newman-Toker et al., *BMJ Qual Saf* 2024;33(2):109–120, report a weighted
mean error rate of **11.1%** and a serious harm rate of **4.4%** per dangerous-disease case. That
divides out to roughly **40% of errors on those presentations ending in serious harm** — our
arithmetic, not their figure, and a **ceiling rather than an average**, because it is measured on
vascular events, infections and cancers: the presentations selected for being dangerous. An
unselected triage queue is far below it. We use **1% as a floor** and say plainly that it is a
guess bounded by their number.

**What a serious harm costs.** CRICO's Comparative Benchmarking System gives an average payment of
**$422,000** on ambulatory diagnosis-related cases filed 2009–2013, with 35% of those cases closing
with any payment at all. A paid claim is a poor proxy in both directions: it misses every harm that
never becomes a claim, and it measures the legal cost rather than the human one.

| | expected cost of one confident wrong answer | ratio to a $20 handover |
|---|---|---|
| floor — 1% of errors cause serious harm | $4,220 | **211 : 1** |
| ceiling — 40%, on dangerous presentations | $167,112 | **8,356 : 1** |
| **what this repo had been assuming** | $100 vs $5 | **20 : 1** |

**Our placeholder was between ten and four hundred times too kind to answering.** Every "refusing
is X% cheaper" figure published here is therefore conservative, which is the direction one would
choose to be wrong in, but it was luck rather than judgement.

## And then the interesting part

Sweep the price of being wrong against every policy the product can take, on 210,000 records —
6,000 held-out patients, seven ways of going short, five levels each:

| wrong : handover | cheapest policy answers | cost per case | against answering everything |
|---|---|---|---|
| 2 : 1 | 49.9% | 10.97 | 1× |
| 20 : 1 *(our placeholder)* | 35.2% | 13.65 | 10× |
| 211 : 1 *(literature floor)* | 28.2% | 15.05 | 93× |
| 1,000 : 1 | 28.2% | 17.61 | 375× |
| 4,000 : 1 | **nothing at all** | 20.00 | 1,322× |
| 8,356 : 1 *(literature ceiling)* | **nothing at all** | 20.00 | 2,760× |

Somewhere between 1,000:1 and 4,000:1 — **inside the band the literature implies** — the cheapest
policy stops being "answer the confident ones" and becomes "answer none of them, refer everything,
pay the $20." Expected-cost minimisation, carried honestly to the real asymmetry of medicine,
tells you to switch the product off.

That is not a flaw in the product. It is a flaw in the objective. **Nobody runs a clinical service
by minimising expected cost**, because the handover has a cost the model does not contain: there
are only so many clinicians, and the queue has to go somewhere. The question a buyer actually has
is the other one.

## The question a buyer actually has

*How much of the queue can the machine take, while holding a bar I set?*

| promise | precision kept | queue it takes | wrong per 1,000 records |
|---|---|---|---|
| **answer everything** | 66.9% | 100% | **330.5** |
| at least 80% right | 97.6% | 44.9% | 10.6 |
| at least 90% right | 98.8% | 39.9% | 4.6 |
| **at least 95% right** | **99.5%** | **35.2%** | **1.7** |
| at least 98% right | 99.9% | 31.0% | 0.4 |
| at least 99% right | 99.9% | 29.2% | 0.2 |

**Answering everything puts 330 wrong answers into every thousand records. Holding a 95% bar puts
1.7 there, and still takes a third of the queue off a person's desk.**

Per 1,000 records at that bar: **352 never reach a person**, which at C$10–C$27 a call is
**C$3,500–C$9,500 of review capacity returned per thousand records**. We are deliberately not
putting a number on the harm avoided. That would need the ratio above applied to synthetic
patients, and it is the one multiplication in this document nobody should do.

## The 210,000 is 6,000 people, and the intervals now say so

Two reviewers made the same catch independently. "210,000 records" is 6,000 held-out patients seen
thirty-five ways — seven missingness patterns at five levels each — and a binomial interval over
those rows assumes an independence that repeated views of one patient do not have. The complete
record of a given patient appears in every pattern.

The intervals in the table above are therefore a **bootstrap over patients**, not over rows: the
people are resampled, every view each resampled person contributed comes with them, and the
precision is recomputed, 400 times. At the 95% bar that gives **[99.4%, 99.6%]** where the naive
row-wise Wilson gave [99.49%, 99.73%] — wider, as it should be, and not wide enough to change
anything.

The point estimates still describe an equal-weight mixture of five completeness levels and seven
patterns that we chose. A different mixture moves every number in the table, and nothing here
argues that this mixture resembles a real intake queue. It was built to span the space, not to
model one.

## What this does not say

**The throughput table is measured on DDXPlus, which is rule-based synthetic data.** The ratio
argument above it is about the published literature and does not depend on our data at all; the
table below it depends on our data entirely. They are separate claims and should be quoted
separately.

**The dial is a floor, not a target.** Ask for 80% and you get 97.6%, because the bar admits
everything above it and the mass sits near the top. That is safe and it is not fine-grained
control; anyone wanting a specific coverage should read it off this table rather than from the
number they typed.

**$422,000 is what a claim paid, not what a harm cost.** The 35% payment rate and every harm that
never became a claim are both missing from it, in opposite directions, and we have not tried to
correct for either.

## Reproducing it

    python3 scripts/run_value.py data/ddxplus/release_validate_patients

About five minutes on a laptop CPU.

## Sources

- CCOHTA, *Telephone Triage Services: Systematic Review and a Survey of Canadian Call Center
  Programs*, Technology Report 43, Nov 2003 — INAHTA Brief 2004/53.
- Newman-Toker DE, Nassery N, Schaffer AC, et al. *Burden of serious harms from diagnostic error
  in the USA.* BMJ Qual Saf 2024;33(2):109–120. doi:10.1136/bmjqs-2021-014130.
- CRICO Strategies, Comparative Benchmarking System, diagnosis-related cases filed 2009–2013, as
  reported by Harvard Risk Management Foundation.
