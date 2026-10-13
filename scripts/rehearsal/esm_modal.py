"""Run the ESM-2 scoring on a rented GPU, as a rehearsal for the AMD day.

    modal run scripts/rehearsal/esm_modal.py --model facebook/esm2_t33_650M_UR50D

This is NOT where the shipped numbers come from. It exists for the same reason
`scripts/fake_vllm.py` exists: to find out whether the bigger model changes anything, and to
find the bugs, before any of it happens on hardware that is being paid for by the hour and whose
whole point is that the measurement happened there.

The scoring is a copy of `scripts/score_variants.py` rather than an import, because Modal runs
the body remotely and the repo is not on that machine. If one changes, change both — there is a
test that the two agree on a handful of variants.
"""

import json
import sys
import time
from pathlib import Path

import modal

HERE = Path(__file__).resolve().parent.parent.parent
WINDOW = 1022

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("torch==2.6.0", "transformers==4.49.0", "numpy<3")
)
app = modal.App("askfirst-esm-rehearsal", image=image)
cache = modal.Volume.from_name("askfirst-hf-cache", create_if_missing=True)


def crop(seq, pos, window=WINDOW):
    if len(seq) <= window:
        return seq, pos, False
    half = window // 2
    start = max(0, min(pos - 1 - half, len(seq) - window))
    return seq[start:start + window], pos - start, True


@app.function(gpu="L4", volumes={"/cache": cache}, timeout=3600)
def score(variants, model_name):
    import os
    os.environ["HF_HOME"] = "/cache"
    import torch
    from transformers import AutoTokenizer, EsmForMaskedLM

    tok = AutoTokenizer.from_pretrained(model_name)
    model = EsmForMaskedLM.from_pretrained(model_name).eval().to("cuda")
    params = sum(p.numel() for p in model.parameters()) / 1e6
    name = torch.cuda.get_device_name(0)
    print(f"{model_name} — {params:.0f}M params on {name}", flush=True)

    scored, failed = [], []
    started = time.time()
    for i, v in enumerate(variants, 1):
        seq, pos, cropped = crop(v["sequence"], v["pos"])
        if seq[pos - 1] != v["wt"]:
            failed.append({"profile": v["profile"], "why": "wild-type residue lost in the crop"})
            continue
        ids = tok(seq, return_tensors="pt")
        masked = ids["input_ids"].clone()
        masked[0, pos] = tok.mask_token_id
        with torch.no_grad():
            logits = model(input_ids=masked.to("cuda"),
                           attention_mask=ids["attention_mask"].to("cuda")).logits
        logp = torch.log_softmax(logits[0, pos].float(), dim=-1)
        wt_id, mut_id = tok.convert_tokens_to_ids(v["wt"]), tok.convert_tokens_to_ids(v["mut"])
        scored.append({
            "profile": v["profile"], "gene": v["gene"], "accession": v["accession"],
            "wt": v["wt"], "pos": v["pos"], "mut": v["mut"],
            "evidence_rows": v["evidence_rows"],
            "llr": round(float(logp[mut_id] - logp[wt_id]), 4),
            "logp_wt": round(float(logp[wt_id]), 4),
            "logp_mut": round(float(logp[mut_id]), 4),
            "argmax": tok.convert_ids_to_tokens(int(logp.argmax())),
            "cropped": cropped, "seq_len": len(v["sequence"]),
        })
        if i % 100 == 0:
            print(f"  {i}/{len(variants)}", flush=True)

    return {"model": model_name, "device": f"{name} (rented, rehearsal only)",
            "params_m": round(params), "scored": len(scored), "failed": failed,
            "seconds": round(time.time() - started, 1), "variants": scored}


@app.local_entrypoint()
def main(model: str = "facebook/esm2_t33_650M_UR50D", limit: int = 0):
    variants = json.loads((HERE / "data/variants.json").read_text())
    variants.sort(key=lambda v: -v["evidence_rows"])
    if limit:
        variants = variants[:limit]
    print(f"sending {len(variants)} variants to {model}")
    out = score.remote(variants, model)
    where = HERE / "docs/results/rehearsal-esm650m.json"
    where.write_text(json.dumps(out))
    print(f"\n{out['scored']} scored in {out['seconds']}s on {out['device']}")
    print(f"wrote {where}")
