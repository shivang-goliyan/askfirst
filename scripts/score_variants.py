"""Score each variant with ESM-2, as one line of evidence that can later be taken away again.

    python3 scripts/score_variants.py --model facebook/esm2_t12_35M_UR50D --limit 50
    python3 scripts/score_variants.py --model facebook/esm2_t33_650M_UR50D     # on the GPU

The score is the masked marginal: mask the variant position, ask the model what belongs there,
and take log P(mutant) - log P(wild type). Negative means the model expected the wild-type
residue more strongly, which is the usual direction for a damaging substitution.

What this is NOT: a pathogenicity call. These scores have no calibrated threshold here, and
ClinGen had to re-weight exactly this class of predictor downward because it was being trusted
too far. ACMG/AMP caps computational evidence at "supporting" and so does this — the score enters
the engine as one removable line, and the interesting question is whether removing it changes the
verdict, not what the number is.

Sequences longer than the model's window are cropped around the variant, and the crop is recorded
per variant rather than assumed to be harmless."""

import argparse
import json
import time
from pathlib import Path

VARIANTS = Path("data/variants.json")
OUT = Path("data/variant_scores.json")
WINDOW = 1022  # ESM-2 takes 1024 positions including <cls> and <eos>


def crop(seq, pos, window=WINDOW):
    """Centre a window on the variant. Returns the cropped sequence and the new 1-based position."""
    if len(seq) <= window:
        return seq, pos, False
    half = window // 2
    start = max(0, min(pos - 1 - half, len(seq) - window))
    return seq[start:start + window], pos - start, True


def main(model_name, limit, out_path):
    import torch
    from transformers import AutoTokenizer, EsmForMaskedLM

    variants = json.loads(VARIANTS.read_text())
    variants.sort(key=lambda v: -v["evidence_rows"])
    if limit:
        variants = variants[:limit]

    tok = AutoTokenizer.from_pretrained(model_name)
    model = EsmForMaskedLM.from_pretrained(model_name)
    model.eval()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    print(f"{model_name} on {device}, {sum(p.numel() for p in model.parameters()) / 1e6:.0f}M params")
    print(f"scoring {len(variants)} variants\n")

    scored, failed = [], []
    started = time.time()
    for i, v in enumerate(variants, 1):
        seq, pos, cropped = crop(v["sequence"], v["pos"])
        if seq[pos - 1] != v["wt"]:
            failed.append({**{k: v[k] for k in ("profile", "gene", "pos")},
                           "why": "wild-type residue lost in the crop"})
            continue

        ids = tok(seq, return_tensors="pt")
        masked = ids["input_ids"].clone()
        masked[0, pos] = tok.mask_token_id          # +1 for <cls>
        with torch.no_grad():
            logits = model(input_ids=masked.to(device),
                           attention_mask=ids["attention_mask"].to(device)).logits
        logp = torch.log_softmax(logits[0, pos].float(), dim=-1)

        wt_id = tok.convert_tokens_to_ids(v["wt"])
        mut_id = tok.convert_tokens_to_ids(v["mut"])
        score = float(logp[mut_id] - logp[wt_id])

        scored.append({
            "profile": v["profile"], "gene": v["gene"], "accession": v["accession"],
            "wt": v["wt"], "pos": v["pos"], "mut": v["mut"],
            "evidence_rows": v["evidence_rows"],
            "llr": round(score, 4),
            "logp_wt": round(float(logp[wt_id]), 4),
            "logp_mut": round(float(logp[mut_id]), 4),
            "argmax": tok.convert_ids_to_tokens(int(logp.argmax())),
            "cropped": cropped,
            "seq_len": len(v["sequence"]),
        })
        if i % 25 == 0 or i == len(variants):
            rate = i / (time.time() - started)
            print(f"  {i}/{len(variants)}  {rate:.1f}/s", flush=True)

    out = {
        "model": model_name,
        "device": device,
        "scored": len(scored),
        "failed": failed,
        "seconds": round(time.time() - started, 1),
        "variants": scored,
    }
    Path(out_path).write_text(json.dumps(out))

    scored.sort(key=lambda s: s["llr"])
    print(f"\n{len(scored)} scored in {out['seconds']}s, {len(failed)} skipped")
    print("\nmost constrained positions (model most surprised by the substitution):")
    for s in scored[:8]:
        print(f"  {s['profile']:18} llr {s['llr']:>8.3f}   model would put {s['argmax']} there")
    print("\nleast constrained:")
    for s in scored[-5:]:
        print(f"  {s['profile']:18} llr {s['llr']:>8.3f}   model would put {s['argmax']} there")
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="facebook/esm2_t12_35M_UR50D")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    main(a.model, a.limit, a.out)
