"""Does an open model's confidence beat our softmax on a thin record?

    modal run scripts/rehearsal/llm_grid_modal.py

This is the product question the AMD day exists to answer. A linear model is 99.6% right on a
complete record and 39.9% at a fifth of one, and the whole argument for hardware is that a bigger
model does not make answers cheaper, it makes more of them answerable. Nobody has checked.

Rehearsal on a rented NVIDIA GPU, same discipline as the ESM-2 run: find the answer and the bugs
here, spend AMD hours measuring. Nothing is baked. vLLM is used offline rather than through the
HTTP client, because the client is already rehearsed against scripts/fake_vllm.py and what is
being tested here is the science, not the transport.
"""

import json
import sys
import time
from pathlib import Path

import modal

HERE = Path(__file__).resolve().parent.parent.parent
MODEL = "Qwen/Qwen2.5-3B-Instruct"

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("vllm==0.8.5.post1", "transformers==4.51.3", "numpy<3")
)
app = modal.App("askfirst-llm-grid", image=image)
cache = modal.Volume.from_name("askfirst-hf-cache", create_if_missing=True)

INSTRUCTION = "Read the patient record and give the single most likely condition."


@app.function(gpu="L40S", volumes={"/cache": cache}, timeout=5400)
def score(cases, labels, model_name):
    """cases: list of {"lines": [...], "truth": label, "kept": frac}. Returns a posterior per
    case, built from the summed log probability of each label under the same prompt."""
    import os
    os.environ["HF_HOME"] = "/cache"
    import math
    from vllm import LLM, SamplingParams

    llm = LLM(model=model_name, max_model_len=2048, gpu_memory_utilization=0.90,
              enable_prefix_caching=True, dtype="bfloat16")
    params = SamplingParams(max_tokens=1, prompt_logprobs=0, temperature=0.0)

    prompts, index = [], []
    for i, case in enumerate(cases):
        body = "\n".join(case["lines"]) if case["lines"] else "- nothing recorded yet"
        head = f"{INSTRUCTION}\n\nRecord:\n{body}\n\nCondition:"
        for label in labels:
            prompts.append(f"{head} {label}")
            index.append((i, label, len(head)))

    print(f"{len(prompts):,} prompts for {len(cases)} cases x {len(labels)} labels", flush=True)
    started = time.time()
    outs = llm.generate(prompts, params)
    print(f"generated in {time.time() - started:.0f}s", flush=True)

    # sum the log probability of the tokens that belong to the label, which start after the
    # prompt's head. vLLM gives one entry per prompt token, the first of which is None.
    totals = [{} for _ in cases]
    for out, (i, label, head_len) in zip(outs, index):
        ids = out.prompt_token_ids
        lp = out.prompt_logprobs or []
        seen, total, counted = 0, 0.0, 0
        text = out.prompt
        # walk back from the end: the label is the tail of the prompt
        tail = len(text) - head_len
        chars = 0
        for pos in range(len(ids) - 1, 0, -1):
            entry = lp[pos]
            if not entry:
                continue
            tok = next(iter(entry.values()))
            piece = getattr(tok, "decoded_token", None) or ""
            chars += len(piece)
            total += float(tok.logprob)
            counted += 1
            if chars >= tail:
                break
        totals[i][label] = total / max(counted, 1)

    posteriors = []
    for row in totals:
        top = max(row.values())
        exp = {k: math.exp(v - top) for k, v in row.items()}
        z = sum(exp.values())
        posteriors.append({k: v / z for k, v in exp.items()})
    return {"model": model_name, "seconds": round(time.time() - started, 1),
            "posteriors": posteriors}


@app.local_entrypoint()
def main(cases: int = 300, model: str = MODEL):
    sys.path.insert(0, str(HERE / "src"))
    sys.path.insert(0, str(HERE / "scripts"))
    from askfirst.ddxplus import load_patients
    from askfirst.model import describe
    from askfirst.schema import load_schema
    from run_abstention import thin

    schema = load_schema("ddxplus")
    patients = [p for p in load_patients(
        str(HERE / "data/ddxplus/release_validate_patients"), limit=60000) if p["evidences"]]
    held = patients[46000:46000 + cases]
    labels = list(schema.outcomes)

    built = []
    for frac in (1.0, 0.4, 0.2):
        for whole, short in zip(held, thin(held, frac)):
            lines = describe(short["evidences"], schema).split("\n")
            built.append({"lines": lines, "truth": whole["pathology"], "kept": frac,
                          "n": len(short["evidences"])})
    print(f"{len(built)} cases, {len(labels)} labels")
    out = score.remote(built, labels, model)

    rows = []
    for case, post in zip(built, out["posteriors"]):
        best = max(post, key=post.get)
        rows.append({"kept": case["kept"], "n": case["n"], "truth": case["truth"],
                     "said": best, "margin": post[best], "right": best == case["truth"]})
    where = HERE / "docs/results/rehearsal-llm-grid.json"
    where.write_text(json.dumps({"model": out["model"], "seconds": out["seconds"],
                                 "cases": cases, "rows": rows}))
    print(f"\n{'record':>8} {'top-1':>8} {'mean margin':>13}")
    for frac in (1.0, 0.4, 0.2):
        here = [r for r in rows if r["kept"] == frac]
        acc = sum(r["right"] for r in here) / len(here)
        margin = sum(r["margin"] for r in here) / len(here)
        print(f"{frac:>8.0%} {acc:>8.1%} {margin:>13.1%}")
    print(f"\nwrote {where}")
