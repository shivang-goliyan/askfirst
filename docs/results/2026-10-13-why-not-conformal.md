# Why not conformal prediction? — 13 October 2026

Selective prediction with a precision target is not a new idea, and **conformal prediction** is
the framework for it (Vovk, Gammerman & Shafer, *Algorithmic Learning in a Random World*, 2005).
Mondrian — class- or group-conditional — predictors calibrate a separate threshold per partition
instead of one globally. A reviewer who knows the field will ask why we did not simply use it, and
the only acceptable answer is a measurement.

So here is the standard version, implemented, against ours. Same scorer, same stream, same 95%
target, 105,000 calibration rows and 105,000 test rows — 3,000 held-out patients across seven
missingness patterns and five completeness levels.

## In distribution, the standard tool beats us

| rule | precision | coverage | 95% interval |
|---|---|---|---|
| split-conformal, one global threshold | **94.5%** | 57.8% | [94.3%, 94.7%] |
| **Mondrian, a threshold per group** | **95.9%** | **53.5%** | [95.7%, 96.1%] |
| ours — isotonic inside the group, plus the floor | 99.5% | **35.1%** | [99.4%, 99.6%] |

Read that honestly. **Mondrian conformal meets the 95% bar and answers 53.5% of the queue where we
answer 35.1%.** It is eighteen points better on the thing a buyer pays for. Our rule over-delivers
precision — asked for 95%, it returns 99.5% — and coverage is what over-delivery costs.

The single global threshold misses the target outright (94.5%, interval excluding 95%), which is
the textbook argument for conditioning and is why the group partition exists at all.

## Under shift, both conformal variants break their promise and ours holds

The comparison above fits every rule on the same mixture the test is drawn from. That is the
friendly case and not the one a deployment is in. Fit on six ways a record goes short, test on the
seventh:

| rule | precision | coverage |
|---|---|---|
| split-conformal, one threshold | **93.8%** | 51.8% |
| Mondrian, a threshold per group | **92.7%** | 49.7% |
| ours | **98.9%** | 30.1% |

**Mondrian falls from 95.9% to 92.7% and stops keeping its word.** Conformal guarantees rest on
exchangeability between calibration and test, and `2026-10-13-missing-not-at-random.md` is a
measurement of exactly that assumption failing: records do not go short the same way twice, and at
a fifth of a record accuracy ranges from 19.2% to 73.2% depending only on *which* fifth.

Ours falls from 99.5% to 98.9% and keeps the promise. The reason is the part that has no conformal
equivalent: **a refusal below an estimated-completeness floor, which is a property of the record
rather than of the score.** A threshold — global or per group — can only ever rank scores. It has
no way to say *this record is too thin to judge by any score*, which is the one thing that
survives the distribution moving under it.

## What this actually says

**The honest trade is robustness bought with coverage.** We give up eighteen points of coverage in
the friendly case to hold the promise in the unfriendly one. For a buyer whose cost is a confident
wrong answer that is the right side of the trade, and for a buyer whose cost is review capacity it
may not be. It should be sold as a choice rather than as a win.

**The over-delivery is a defect, not a feature.** Asked for 95% we return 99.5%, because the dial
is a floor and the isotonic fit is conservative at the top of its range. A quantile inside each
group — the Mondrian construction — is better calibrated to the target than our isotonic fit is.
The obvious improvement, which we have not made, is to keep the completeness floor and replace the
isotonic step with a per-group quantile, which should recover most of the eighteen points without
giving up the robustness. That is a change we can state but have not measured, so it is not in the
product.

**And the framework was always the right one to name.** Our rule is a Mondrian predictor with the
partition chosen as *(findings in hand × how unusual they are)* and an isotonic fit in place of a
quantile, plus a record-level gate. Describing it in those terms is more useful than the vocabulary
we had been using, and it makes the one genuinely new part — the floor — easy to see.

## Reproducing it

    python3 scripts/run_conformal.py data/ddxplus/release_validate_patients

About six minutes on a laptop CPU.
