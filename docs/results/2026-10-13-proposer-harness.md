# The proposer harness, and what the CPU proposers top out at

`scripts/run_proposer_recall.py` measures the number that caps the pipeline. The engine ablates a
shortlist, so whatever the model does afterwards it can only re-rank what the proposer handed it.
A field that is not on the list is unreachable.

150 cases, 223 candidate fields, seed 13:

| proposer | @1 | @3 | @5 | @10 | @20 | per case |
|---|---|---|---|---|---|---|
| pathology (cpu) | 3.3% | 3.3% | 5.3% | 14.7% | 23.3% | 0.00s |
| marginal (cpu) | 0.0% | 2.0% | 2.0% | 20.0% | 32.7% | 0.47s |
| chance | 0.4% | 1.3% | 2.2% | 4.5% | 9.0% |

Consistent with the earlier 400-case run (26.2% at k=10, 31.8% at k=20) within the intervals, and
it confirms the pathology-conditioned proposer is the weaker of the two. Both are far under the
40% bar at k=10 that the advice feature needs.

The harness is deliberately built to be run, not read:

- It takes any proposer, so the model slots in with no code change.
- With `ASKFIRST_VLLM_URL` set, the model proposer joins the table automatically and is listed
  first.
- The slow proposer gets a wall-clock budget so one command cannot eat an afternoon.
- It prints the kill criterion and whether each proposer clears it, with Wilson intervals, so the
  output is a go/no-go rather than a number needing interpretation.

**One command, the moment credits land, answers whether the advice feature lives.**

## Scorer parsing, verified before any GPU time

The riskiest code in the model layer was picking the label's tokens out of an echoed prompt. The
first version walked tokens backwards matching the label string, which is a guess. vLLM's
completion logprobs carry **`text_offset`** — a cumulative character offset per token — and since
we build the prompt we know exactly where the label starts, so the tokens can be selected
exactly.

`tests/test_model.py` runs the scorer against a mock built to the documented response shape and
checks six things: the intended ranking is recovered, the distribution normalises, all labels
cost one request, `echo` and `max_tokens=0` are actually sent, a missing-logprobs response fails
with a useful message, and — the one that matters most — **a long condition name scores the same
as a short one at equal per-token logprob.** Without mean-normalising, the scorer would quietly
have been measuring name length. That bug would have been invisible on real hardware and would
have poisoned every distribution.
