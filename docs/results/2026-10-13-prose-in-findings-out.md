# The right job for the open model is reading, not deciding — 13 October 2026

**Rehearsal on a rented NVIDIA L40S. Nothing measured here is baked into a result.** The notes on
the live page were produced by this run and are frozen so the path can be shown without an
accelerator; every number on the page still comes from the CPU model.

Earlier today we measured the open model as a *scorer* and it was poor: 35.3% against a fitted
linear model's 99.6%, with a confidence that does not notice four fifths of the record is missing
(`2026-10-13-the-open-model-is-not-the-scorer.md`). That is the wrong job for it.

This is the right one. The engine needs structured findings; the world produces prose.

## Prose in, findings out

100 held-out records. Each is rendered into a nurse's note by the model, then read back into
fields by the model, and the recovered fields are compared with the record.

| | |
|---|---|
| findings recovered | **72.0%** (445 of 618) |
| of what it returned, really there | **87.3%** (65 invented across 100 records) |
| time | 70 seconds for 100 notes and 20,800 judgements |

**The first attempt got 26% and invented four codes a note.** It handed the model all 223
questions as a menu and asked it to write out the codes it found. The notes were fine; the
searching was not — it missed "attends a daycare" and "is a smoker" from a note that said both.
Asking one question at a time and reading the answer off the log probabilities of *yes* against
*no* took recall from 26% to 72% and precision from 38% to 87%. The note is a shared prefix, so
208 questions cost barely more than one.

## The number that decides whether this is shippable

An extraction step that loses a quarter of the findings sounds like it should poison everything
downstream. Scored twice — once from the real record, once from what the model read out of its
own note, same scorer, same gate, same 95% bar:

| | top-1 | answers | precision | wrong |
|---|---|---|---|---|
| the real record | 95.0% | 41.0% | 100.0% | **0** |
| read out of a prose note | 74.0% | **34.0%** | 100.0% | **0** |

Ten cases stopped being answered, three started, and **no wrong answer was introduced.**

**What the extraction misses makes the record look thinner, and a thinner record is exactly what
the completeness gate refuses.** The error does not compound into a confident mistake; it turns
into caution. That is the property this product claims, and this is the first time it has been
demonstrated end to end through a messy input path rather than on records handed over clean.

It is worth being precise about why: the gate is a function of the record, not of the scorer's
mood. Fewer findings means a lower estimated completeness, which means the floor fires. A system
that decided on confidence alone would have been free to be just as sure on the degraded record.

## What this does not say

**The note was written by the same model that read it back.** That is easier than a real clinical
note in every way that matters — vocabulary, structure, and the absence of anything irrelevant.
72% and 87% are upper bounds and should be read as a demonstration of the path rather than as
evidence about real notes. We have no licensed corpus of real notes; saying so is better than
quoting a number as though we did.

**Only the 208 binary fields are measured.** In DDXPlus a recorded binary field is always a
positive finding, so "is it in the record" and "did the note say yes" are the same question. The
15 graded fields record an answer that may be negative, and an early version of this measurement
counted a recorded *negative* about overseas travel as a finding the model had missed, which was
our error rather than the model's.

**n=100, and the 100% precision above rests on 34 answered cases.** The Wilson interval on that
is [89.8%, 100%]. The zero is a real zero and the interval is what it is.

## Why this is the AMD workload

Reading is what a language model is for, and on this evidence it does it well enough to be useful
while being wrong often enough to need the gate behind it. That is a better argument for the
hardware than the one we had this morning, because it is a job the model wins rather than one it
loses — and the thing it feeds is measured to absorb its errors rather than amplify them.

When credits land this runs on MI300X instead, and the baked notes are replaced by live
extraction with the model named in the response, as every other scorer already is.

## Reproducing it

    modal run scripts/rehearsal/extract_modal.py --cases 100
    python3 scripts/bake_notes.py
