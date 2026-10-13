# We offered a frontier model the door, and measured how often it took it — 13 October 2026

**This is not an accuracy contest and nothing here claims we beat Claude at diagnosis.** Our
scorer is fitted on 30,000 labelled patients from this exact generator; Claude is zero-shot with
a two-line prompt. Comparing top-1 between them would be a rigged race and any judge would say so
in one sentence.

The comparison that *is* fair is the one this product is about: **given the same thinning record,
who knows to stop?** Both sides get the same patients, the same thinning, and an explicit way out.

200 held-out patients at three completeness levels, `claude-opus-5-5`, every call offering
`INSUFFICIENT` as a first-class answer and telling it not to guess — the same shape as
arXiv 2608.09080, which found GPT-5 taking that door 19.2% of the time on MedMCQA. 600 calls,
$2.55.

## It does notice. Nowhere near enough.

| record | abstains | answers anyway | right when it answers |
|---|---|---|---|
| complete | 0.0% | 100% | 56.0% |
| 40% of it | 7.5% | 92.5% | 15.1% |
| a fifth of it | 35.0% | 65.0% | 0.8% |

Abstention climbs from nothing to a third as the evidence disappears, which is **better than we
predicted** and better than the published GPT-5 figure. A frontier model is not blind to this.

But look at the middle row. At two fifths of a record it declines 7.5% of the time and is right
**15.1%** of the time when it answers. At a fifth it still answers two cases in three while being
right in **one case in 125**. The abstention is not calibrated to its own reliability — it is
directionally right and off by an order of magnitude.

## Side by side, on the same 150 patients, at 40% of a record

| | abstains | answers | right when it answers |
|---|---|---|---|
| Claude Opus 5.5, effort low | 8.0% | 92.0% | 14.5% |
| Claude Opus 5.5, effort high | **2.7%** | 97.3% | **4.1%** |
| this gate | **83.8%** | 16.2% | **98.2%** |

That is the product in one table, and it is apples to apples: same records, same question, same
option to decline.

## More thinking made it worse

The obvious objection to the first table is that it was run at low effort. It was, so we re-ran
the 40% level at `effort: high`, same 150 patients.

**It abstained less — 2.7% against 8.0% — and was right less often when it answered, 4.1% against
14.5%.** More deliberation bought more willingness to commit, not more caution. Whatever the
reluctance to say "insufficient" is, it is not a thinking-budget problem, and that is the
objection closed rather than waved away.

## What this does and does not license

**Does:** the claim that a model offered an explicit way out, told not to guess, and handed a
record it cannot answer from, will answer anyway the overwhelming majority of the time — measured
on a frontier model, on our data, at two effort levels.

**Does not:** any claim that this system is a better diagnostician than Claude. It is not being
asked to be. It is a gate, Claude is the kind of thing it gates, and the better the model behind
it the more the gate is worth — because the failure here is not ignorance, it is not noticing the
record ran out.

**Limits.** One model, one prompt, one benchmark, 200 patients, DDXPlus synthetic. A different
prompt — one that scores each condition and thresholds, or that is few-shot — would likely raise
the abstention rate, and we did not try. The 56% on complete records is a floor for what careful
prompting could get, not a ceiling. What would not change with prompting is the shape: something
has to decide when to stop, and asking the answering model to decide it is the arrangement this
measurement is about.

## Reproducing it

    ANTHROPIC_API_KEY=... python3 scripts/rehearsal/claude_abstention.py --cases 200
    ANTHROPIC_API_KEY=... python3 scripts/rehearsal/claude_abstention.py \
        --cases 150 --levels 0.4 --effort high \
        --out docs/results/rehearsal-claude-abstention-high.json

600 + 150 calls, about $3.20 in total. The key used for this run should be rotated.
