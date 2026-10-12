# Shortlist recall, and why it inverts the design

n = 400 held-out DDXPlus patients, one evidence deleted at random per patient, 223 candidate
fields, naive Bayes scorer, seed 7. Run time 3m11s on CPU.

| k | recall | 95% CI | chance | lift |
|---|---|---|---|---|
| 1 | 9.5% | [7.0%, 12.8%] | 0.48% | **19.8x** |
| 3 | 14.5% | [11.4%, 18.3%] | 1.44% | 10.1x |
| 5 | 19.5% | [15.9%, 23.7%] | 2.40% | 8.1x |
| 10 | 26.2% | [22.2%, 30.8%] | 4.79% | 5.5x |
| 20 | **31.8%** | [27.4%, 36.5%] | 9.59% | 3.3x |
| 50 | 43.0% | [38.2%, 47.9%] | 23.97% | 1.8x |

## Two findings, and the second one matters more

**1. The pre-registered bar is missed, and it is not a sampling fluke.** `docs/METRIC.md` set
30% at top-3 by 14 October. At n = 400 the figure is 14.5% with an interval of
[11.4%, 18.3%] — the whole interval sits below half the bar. The 150-case run was not unlucky.

**2. The propose-then-ablate design I proposed yesterday does not survive this table.** The plan
was: cheap scorer shortlists 20 of 223, open model ablates the shortlist. But shortlist recall at
k = 20 is **31.8%**. The true field is absent from the shortlist two times in three, and stage
two can only re-rank what stage one hands it. **The architecture would cap the finished system at
about 32% however good the model is.** Buying recall with a longer list does not work either:
k = 50 costs 2.5x the GPU and returns 43%, and the lift has collapsed to 1.8x by then.

## The diagnosis, and it is not "ranking doesn't work"

Lift decays from 19.8x at k = 1 to 1.8x at k = 50. A scorer that is sharp at the very top and
noisy below it is a scorer with a little real signal and no breadth. Which is what naive Bayes
over 223 independent evidences is: it knows which findings **co-occur statistically** and nothing
whatever about medicine. It cannot know that chest pain implies you check an ECG and a troponin,
because that knowledge is not in the co-occurrence table.

A language model does know that.

## So invert it

Not cheap-proposes then model-verifies. **Model proposes, cheap scorer verifies.**

1. **Propose** — the open model reads the record and names ~10 fields a clinician would want.
   This is where medical knowledge belongs, and it is **one generation per case**, not 450
   forward passes.
2. **Verify** — ablate those ~10 exhaustively with the cheap scorer, which is free, to get the
   flip probabilities and the cost ranking.

This is better on every axis that matters. GPU cost per case drops from roughly 450 forward
passes to about one. The stage holding the domain knowledge is the stage that generates the
candidate set, so the cap moves from naive Bayes' 32% to whatever the model's clinical recall is.
And the cheap arithmetic stays where arithmetic belongs — the probabilities a judge is shown are
computed, not generated, which is the whole point of the project.

The measurement that now caps the pipeline is the model's proposal recall at k = 10. That is the
first thing to run when a GPU exists, and it is one generation per case, so it is cheap to find
out.

## Note on what this does not change

The engine is unaffected. `rank_gaps` does not care who produced the candidate list, which is why
it already takes `candidates` as an argument. What changed is who fills it.
