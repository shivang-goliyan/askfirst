"""Turn CIViC's protein-level variant labels into something scoreable, and count what is lost.

    python3 -I scripts/build_variants.py data/civic/evidence.tsv

Writes data/variants.json. Nothing is scored here — this step only establishes which variants we
are allowed to score at all, which is the part that quietly goes wrong."""

import collections
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from askfirst.protein import fetch_sequence, parse_substitution, pick_entry  # noqa: E402

CACHE = "data/uniprot"
OUT = Path("data/variants.json")


def main(evidence_path):
    rows = list(csv.DictReader(open(evidence_path), delimiter="\t"))
    profiles = collections.Counter(r["molecular_profile"] for r in rows)

    parsed, unparsed = {}, 0
    for profile in profiles:
        sub = parse_substitution(profile)
        if sub:
            parsed[profile] = sub
        else:
            unparsed += 1

    genes = sorted({s.gene for s in parsed.values()})
    print(f"{len(rows)} evidence rows over {len(profiles)} molecular profiles")
    print(f"  single-substitution labels : {len(parsed)}")
    print(f"  everything else, left alone: {unparsed}")
    print(f"  distinct genes to look up  : {len(genes)}")
    print()

    seqs, missing = {}, []
    for i, gene in enumerate(genes, 1):
        rec = fetch_sequence(gene, CACHE)
        if rec:
            seqs[gene] = rec
        else:
            missing.append(gene)
        if i % 25 == 0 or i == len(genes):
            print(f"  fetched {i}/{len(genes)}", flush=True)

    kept, dropped = [], collections.Counter()
    silent = 0
    for profile, sub in sorted(parsed.items()):
        entry, why = pick_entry(sub, seqs.get(sub.gene))
        if not entry:
            dropped[why] += 1
            continue
        if sub.silent():
            silent += 1
            dropped["silent, nothing to score"] += 1
            continue
        kept.append({
            "profile": profile,
            "gene": sub.gene,
            "wt": sub.wt,
            "pos": sub.pos,
            "mut": sub.mut,
            "accession": entry["accession"],
            "sequence": entry["sequence"],
            "evidence_rows": profiles[profile],
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(kept))

    print()
    print(f"scoreable: {len(kept)} variants over {len({k['gene'] for k in kept})} genes, "
          f"covering {sum(k['evidence_rows'] for k in kept)} evidence rows")
    print("dropped, by reason:")
    for why, n in dropped.most_common():
        print(f"  {n:>4}  {why}")
    if missing:
        print(f"  no reviewed human entry for {len(missing)} symbols: {', '.join(missing[:8])}"
              + (" ..." if len(missing) > 8 else ""))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/civic/evidence.tsv")
