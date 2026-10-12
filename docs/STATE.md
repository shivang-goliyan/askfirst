# Where this stands

## What works, measured

**The refusal.** 1,500 held-out DDXPlus patients, 49 conditions, 2% chance. Answer only the most
confident share and accuracy on what you answered climbs from **21.0% to 85.3% at 10% coverage**.
Priced — a confident wrong decision at 100, a referral at 5 — always answering costs 79.00 per
case against 4.82, which is **94% cheaper**, and the result holds across seven price ratios
(41% to 99% cheaper, optimum always 5-10% coverage).

Quote **92.8%**, not 98.7%. The 5%-coverage figure is 74 of 75 cases; Wilson CI [92.8%, 99.8%].

Margin beats entropy as the confidence signal at every coverage level.

Full numbers in `results/`. The failures are in there too, in order.

## What does not work yet

**The advice.** Ranking by expected information gain scores 28.4% against 26.0% for asking at
random and 28.0% for asking nothing — intervals overlapping. Neutral, not useful. It needs a
model with medical knowledge; a naive Bayes knows co-occurrence and nothing else.

## Dead ends, so nobody repeats them

- **Flip probability as the ranking objective was actively harmful** — 18.8% against 26.0% for
  asking at random. It selects for volatility. Replaced by expected information gain.
- **Cheap-proposes-then-model-ablates caps the system near 32%**, because naive Bayes shortlist
  recall at k=20 is 31.8% and stage two can only re-rank what stage one passes. Inverted: the
  model proposes, the cheap scorer ablates.
- **A pathology-conditioned discriminative proposer lost to the marginal one**, 14.7% against
  20.0% at k=10.
- **An exhaustive 223-field sweep with a language model is ~22s of GPU per case.** That is a
  latency problem, not a budget one, and it does not go away with more credits.

## Architecture

1. Record parsed into atomic fields.
2. Open model scores it; the full distribution is kept, not sampled text.
3. Present fields ablated one at a time, giving a sensitivity map.
4. Absent fields ranked by expected information gain, then by cost and time to obtain.
5. Unstable under ablation means refuse: return the ranked gaps and hand over.

Step 2 is why this needs open weights. You cannot read a closed API's distribution, and without
it there is no entropy, no information gain and no calibrated refusal.

## Running the measurements

    python3 -I scripts/run_abstention.py     data/ddxplus/release_validate_patients 1500
    python3 -I scripts/run_economics.py      data/ddxplus/release_validate_patients 1500
    python3 -I scripts/run_recovery.py       data/ddxplus/release_validate_patients 400
    python3 -I scripts/run_decision_value.py data/ddxplus/release_validate_patients 250
    python3 -I scripts/run_proposer_recall.py data/ddxplus/release_validate_patients 200
    python3 -I scripts/bake_curve.py         data/ddxplus/release_validate_patients 1500

With a served model, the proposer harness adds the model to the table automatically:

    ASKFIRST_VLLM_URL=http://127.0.0.1:8000/v1 \
      python3 -I scripts/run_proposer_recall.py data/ddxplus/release_validate_patients 200

**The bar is 40% recall at k=10.** Under it, the advice feature does not ship as a claim.

## Next

1. Proposer recall with a real model — the go/no-go above.
2. Model confidence against the naive Bayes margin on the risk-coverage curve. Beating
   21%-to-85.3% with real logprobs is the point: a better model does not make answers cheaper,
   it makes more of them answerable.
3. The PP3/BP4 evidence line for module B via ESM-2. The time sink there is mapping HGVS to a
   position in a protein sequence, not the model.

## Open issues

- `value_per_cost` over-rewards cheap items — a low-information, near-free field can outrank a
  decisive one. Needs a utility floor.
- Numeric fields with no `value_meaning` render raw, e.g. "How fast did the pain appear? -> 5".
- DDXPlus is rule-based synthetic, so recovering a deleted field may partly mean recovering the
  generator. MedQA is the cross-check and the limitation is stated rather than buried.
- Module B has 182 contested CIViC groups. That is a demo and a small result, not a headline.
