# An hour spent trying to make it say something stupid — 13 October 2026

Black-box probing of the deployed app, written down whether or not it found anything, because a
clean adversarial pass nobody can see is indistinguishable from one that was never run.

## The one that worked

**Tick every box.** Send a record with all 223 fields present:

```
ALL 223 fields present        ANSWERS   complete=100%  P(right)=0.959   "Pneumonia"
every binary field present    ANSWERS   complete=100%  P(right)=0.958   "Unstable angina"
```

A patient with every symptom in the book does not exist, and the system answered confidently —
the single most likely thing a judge pokes, and it fell over.

**Why.** The calibration has only ever been fitted on *subsets* of real records: thinning removes
findings, it never adds them. A superset is off the end of everything it has seen, and an isotonic
fit extrapolates by holding its last value, so it reported 0.96 with no basis whatsoever.

**The fix, measured rather than guessed.** The largest record among the 30,000 patients the scorer
was fitted on holds **37 findings**; the largest in all 60,000 holds **38**. Nothing real comes
near 223. The ceiling is set at 44 and a record above it is refused outright:

> 223 findings in one record. The largest record in the data this was fitted on holds 37, so this
> did not come from a patient and nothing measured here applies to it.

The response still carries `chance_right: 0.9589` next to that refusal, deliberately. It is the
evidence that the calibration *would* have said 0.96, which is the whole reason the ceiling exists.

No measured number moves: every real record is at or below 38, so the ceiling never fires on
anything any result in this directory was computed from. A test holds that.

**What it does not catch.** A real patient with twenty invented findings added scores 30 findings
and passes, and the plausibility ratio for it (7.8) sits inside the range real records occupy
(up to 10). Gross impossibility is detectable; mild contamination is not, and we are not going to
pretend otherwise.

## The ones that held

| attack | result |
|---|---|
| `target: 0` and `target: -5` on a thin record | refused — the completeness floor is not negotiable from the request |
| two different patients' findings merged | refused, P = 0.943 |
| only the twelve most commonly recorded fields | refused, P = 0.505 — the weak spot from the missingness work, holding |
| empty record | refused |
| 10,000-character value, emoji keys, HTML in a value | ignored, no reflection, refused |
| `domain: "../etc"` | 404 naming the three real schemas |

## Three input bugs, fixed

**A nested value crashed into a 503.** `{"E_55": {"a": 1}}` reached the scorer and came back as
`Scoring failed: unhashable type: 'dict'` — a stack trace wearing a coat. Now a 422: *"'E_55' came
in as dict. A finding is a value or a list of values, not something nested."*

**The target was not bounded.** `target: -5` and `target: 2.0` were accepted as given. Clamped to
[0, 1]. The floor had been doing the safety work on its own, which is one mechanism where there
should be two.

**Unknown fields counted toward the record.** `{"NOPE": "present"}` read as 6% of a record rather
than nothing. Unknown keys are now dropped and listed back in `ignored_fields`, so a caller with a
typo is told rather than quietly misread.

## Reproducing it

The probe scripts are not in the repo — they are twenty lines of `urllib` against
`/api/assess` and anyone can rewrite them in five minutes. The two things worth keeping are in
`tests/test_ablation.py`: `test_impossible_records_refused` and `test_nested_values_rejected`.
