"""Can an open model turn a prose note into the fields the engine scores?

    modal run scripts/rehearsal/extract_modal.py --cases 100

We measured that a general model is a poor SCORER — 35.3% against a fitted linear model's 99.6%,
and a confidence that does not notice four fifths of the record is missing
(`2026-10-13-the-open-model-is-not-the-scorer.md`). That is the wrong job for it.

This is the right one. The engine needs structured findings and the world produces prose, and
turning one into the other is the thing language models are actually good at. If it works, the
open model has a real place in the product — reading, not deciding — and the hardware has a job
that is not an assertion.

Measured honestly: a held-out record is rendered to a note by the model, then extracted back by
the model, and the recovered fields are compared with the truth. Rendering and extracting with
the same model is easier than a real clinical note and the number should be read as an upper
bound. We do not have a licensed corpus of real notes, and saying so is better than pretending
the number means more than it does.
"""

import json
import re
import sys
import time
from pathlib import Path

import modal

HERE = Path(__file__).resolve().parent.parent.parent
MODEL = "Qwen/Qwen2.5-7B-Instruct"

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("vllm==0.8.5.post1", "transformers==4.51.3", "numpy<3")
)
app = modal.App("askfirst-extract", image=image)
cache = modal.Volume.from_name("askfirst-hf-cache", create_if_missing=True)

WRITE = (
    "You are a triage nurse writing an intake note. Turn these recorded findings into natural "
    "clinical prose.\n\nRules: mention EVERY finding listed, add nothing that is not listed, do "
    "not reuse the original wording, no bullet points.\n\nFindings:\n{findings}\n\nNote:"
)
# One question at a time, decided by log probability, instead of asking the model to search a
# 223-item menu and write out the codes. The menu version recovered 26% and invented four codes
# a note: the notes were fine and the searching was not. This asks the only thing a reader of a
# note is actually good at, one question at a time, and the note is a shared prefix so the whole
# sweep is one batch.
ASK = ("A nurse wrote this note.\n\n{note}\n\n"
       "Question: {question}\n"
       "Does the note say this is the case? Answer yes or no.\nAnswer:")


@app.function(gpu="L40S", volumes={"/cache": cache}, timeout=5400)
def run(records, menu, model_name):
    import os
    os.environ["HF_HOME"] = "/cache"
    from vllm import LLM, SamplingParams

    llm = LLM(model=model_name, max_model_len=8192, gpu_memory_utilization=0.90,
              enable_prefix_caching=True, dtype="bfloat16")
    tok = llm.get_tokenizer()

    def chat(prompts, max_tokens):
        texts = [tok.apply_chat_template([{"role": "user", "content": p}],
                                         tokenize=False, add_generation_prompt=True)
                 for p in prompts]
        outs = llm.generate(texts, SamplingParams(max_tokens=max_tokens, temperature=0.0))
        return [o.outputs[0].text for o in outs]

    started = time.time()
    notes = chat([WRITE.format(findings=r["findings"]) for r in records], 300)
    print(f"wrote {len(notes)} notes in {time.time() - started:.0f}s", flush=True)

    mid = time.time()
    prompts, index = [], []
    for i, note in enumerate(notes):
        for code, question in menu:
            prompts.append(tok.apply_chat_template(
                [{"role": "user", "content": ASK.format(note=note.strip(), question=question)}],
                tokenize=False, add_generation_prompt=True))
            index.append((i, code))
    print(f"{len(prompts):,} yes/no judgements", flush=True)

    outs = llm.generate(prompts, SamplingParams(max_tokens=1, logprobs=20, temperature=0.0))
    said = [set() for _ in notes]
    for out, (i, code) in zip(outs, index):
        lp = out.outputs[0].logprobs
        if not lp:
            continue
        yes = no = float("-inf")
        for entry in lp[0].values():
            word = (entry.decoded_token or "").strip().lower()
            if word.startswith("yes"):
                yes = max(yes, entry.logprob)
            elif word.startswith("no"):
                no = max(no, entry.logprob)
        if yes > no:
            said[i].add(code)
    print(f"read them back in {time.time() - mid:.0f}s", flush=True)
    return {"model": model_name, "seconds": round(time.time() - started, 1),
            "notes": notes, "said": [sorted(x) for x in said]}


@app.local_entrypoint()
def main(cases: int = 100, model: str = MODEL):
    sys.path.insert(0, str(HERE / "src"))
    from askfirst.ddxplus import load_patients
    from askfirst.model import describe
    from askfirst.schema import load_schema

    schema = load_schema("ddxplus")
    patients = [p for p in load_patients(
        str(HERE / "data/ddxplus/release_validate_patients"), limit=60000) if p["evidences"]]
    held = [p for p in patients[52000:] if 6 <= len(p["evidences"]) <= 14][:cases]

    # binary fields only: in DDXPlus a recorded binary field is always a positive finding, so
    # "is it in the record" and "did the note say yes" are the same question. The 15 graded
    # fields record an answer that may be negative, which would make the comparison meaningless.
    menu = [(name, spec.question or name) for name, spec in schema.fields.items()
            if spec.kind == "binary"]
    records = [{"findings": describe(p["evidences"], schema)} for p in held]
    print(f"{len(records)} records, {len(menu)} binary questions each")

    out = run.remote(records, menu, model)

    binary = {name for name, spec in schema.fields.items() if spec.kind == "binary"}
    hits = misses = spurious = 0
    rows = []
    for patient, note, found in zip(held, out["notes"], out["said"]):
        truth = set(patient["evidences"]) & binary
        found = set(found)
        hits += len(truth & found)
        misses += len(truth - found)
        spurious += len(found - truth)
        rows.append({"truth": sorted(truth), "found": sorted(found),
                     "missed": sorted(truth - found), "invented": sorted(found - truth),
                     "note": note.strip()})

    recall = hits / max(hits + misses, 1)
    precision = hits / max(hits + spurious, 1)
    where = HERE / "docs/results/rehearsal-extraction.json"
    where.write_text(json.dumps({"model": out["model"], "seconds": out["seconds"],
                                 "cases": len(held), "recall": round(recall, 4),
                                 "precision": round(precision, 4),
                                 "hits": hits, "missed": misses, "invented": spurious,
                                 "truth": [sorted(set(p["evidences"])) for p in held],
                                 "extracted": out["said"],
                                 "pathology": [p["pathology"] for p in held],
                                 "examples": rows[:5]}))
    print(f"\n{len(held)} records, {out['seconds']}s")
    print(f"  recall    {recall:.1%}  ({hits} of {hits + misses} real findings recovered)")
    print(f"  precision {precision:.1%}  ({spurious} codes returned that were not in the record)")
    print(f"\nwrote {where}")
