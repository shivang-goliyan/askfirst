# A general model's confidence does not notice how much of the record is missing — 13 Oct 2026

**Rehearsal on a rented NVIDIA L40S. Nothing baked.** Same discipline as the ESM-2 run: answer
the question here, spend AMD hours measuring rather than discovering.

The deck has been saying *"a better model does not make the answers cheaper, it makes more of
them answerable."* Nobody had checked. 300 held-out patients at three completeness levels, 49
condition labels scored by prompt log-probability — 44,100 prompts, 332 seconds on one GPU.

## The open model loses badly, which is the smaller finding

| record | Qwen2.5-3B-Instruct | our softmax |
|---|---|---|
| complete | **35.3%** | 99.6% |
| 40% of it | **20.7%** | 82.5% |
| a fifth of it | **13.7%** | 40.2% |

Chance is 2.0%, so the model has real signal. It is also nowhere close. This is not a fair fight
and was never going to be: the softmax was fitted on 30,000 labelled patients drawn from exactly
this distribution, and the model is zero-shot with a two-line prompt. **It does not establish that
no open model could do better** — a larger one, few-shot examples, or the candidate list in the
prompt would all help, and none of that was tried.

## The confidence not moving is the real finding

| record | its confidence | our softmax's |
|---|---|---|
| complete | 12.4% | 98.2% |
| a fifth of it | 10.9% | 16.3% |
| **fall** | **12%** | **83%** |

**Take four fifths of the record away and the open model is about as confident as it was.** Our
linear model's margin collapses by 83%; the general model's barely moves.

### An earlier version of this note said there was "nothing in it to calibrate". That was wrong.

A reviewer checked the artifact and found the opposite: **within a single record size, its
confidence separates right from wrong very well.**

| record | overall | its own most-confident 30 | its least-confident 30 |
|---|---|---|---|
| complete | 35.3% | **93.3%** | 16.7% |
| 40% of it | 20.7% | **80.0%** | 6.7% |
| a fifth of it | 13.7% | **53.3%** | 6.7% |

So selective prediction works on it. The claim had to be narrowed, and the narrower one is more
useful: **its confidence ranks, but it does not transfer.** A cut-off chosen on complete records
to deliver 80% precision delivers **54.7%** at 40% evidence and **53.3%** at a fifth:

| cut-off chosen on | 100% | 40% | 20% |
|---|---|---|---|
| complete records | 80.0% | **54.7%** | **53.3%** |
| 40% records | 92.1% | 80.0% | **43.8%** |

(95% is unreachable for this model at any coverage, so the table asks for 80%.)

That is the same disease our own softmax has — and `2026-10-13-the-page-stops-asking.md` is the
whole story of fixing it, by conditioning the calibration on how many findings are in hand. The
difference is the size of the handle: our margin falls 83% as the record thins, so there is a
strong signal to condition on. This one falls 12%, so there is very little. It is a harder thing
to calibrate, not an impossible one, and saying "impossible" was an overclaim.

## What that does to the argument for the hardware

It kills the line the deck had been using, so the line is gone. **On this benchmark a bigger
general model does not make more cases answerable; it makes far fewer.** We would rather find
that here than have a judge find it on the video.

What survives is more specific and is measured:

**The protein model.** `2026-10-13-the-cap-is-not-enough.md` — ESM-2 650M cuts the sign-error rate
from 21.9% to 6.6% and changes the Module B conclusion: at supporting strength 4 of 28 calls move
rather than 0 of 11. That is a model that needs a GPU, producing an artifact that ships, changing
a safety finding. It is the strongest AMD case the project has.

**The distribution.** Entropy, ablation and the calibrated threshold are all functions of the full
posterior, which a closed API does not return. That argument is unaffected by anything here — it
is about open weights rather than about model size.

**And this measurement.** Establishing that a general model's confidence does not track evidence
took a GPU and 44,100 scored prompts. The negative result is a result, and it is the reason the
product ships a fitted scorer with a completeness estimate rather than trusting a general model's
self-reported certainty.

## What this does not say

One model, one size, one prompt, one benchmark, 300 patients. DDXPlus is synthetic and its records
are lists of coded findings rather than the prose an instruct model is good at — the format
flatters the fitted model and disadvantages the general one. The honest claim is narrow: *this*
model at *this* size with *this* prompt does not beat a fitted linear model on *this* data, and
its confidence does not respond to evidence. Whether a 70B model or a better prompt would change
the first finding is untested. The second — that confidence barely moves — is the one that would
survive a larger model, and is the one worth re-running on AMD.

## Reproducing it

    modal run scripts/rehearsal/llm_grid_modal.py --cases 300

The vLLM offline path is used rather than the HTTP client, because the client is already
rehearsed against `scripts/fake_vllm.py` and what is being tested here is the science.
