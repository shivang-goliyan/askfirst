"""Protein-level variants, and the one check that stops this whole module being nonsense.

CIViC names its variants at the protein level already — "BRAF V600E", not a c. HGVS string — so
the coordinate mapping that usually eats a day reduces to reading three fields out of a label.
That only holds for plain single-substitution profiles; everything else (fusions, exon-level
calls, "DNMT3A R882" with no alternate residue) is left alone rather than guessed at.

The check that matters: UniProt's canonical sequence must actually carry the wild-type residue at
that position. If it does not, the label and the sequence disagree — usually a different isoform
numbering — and any score computed from them is meaningless while looking perfectly fine. So
nothing gets scored until that assertion passes, and the ones that fail are counted out loud."""

import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

AMINO = "ACDEFGHIKLMNPQRSTVWY"
SUB = re.compile(rf"^([A-Za-z0-9][A-Za-z0-9._-]*)\s+([{AMINO}])(\d+)([{AMINO}])$")
UNIPROT = "https://rest.uniprot.org/uniprotkb/search"


@dataclass(frozen=True)
class Substitution:
    profile: str
    gene: str
    wt: str
    pos: int
    mut: str

    def short(self):
        return f"{self.gene} {self.wt}{self.pos}{self.mut}"

    def silent(self):
        return self.wt == self.mut


def parse_substitution(profile):
    """"BRAF V600E" -> a substitution. Anything else -> None, deliberately."""
    m = SUB.match(profile.strip())
    if not m:
        return None
    gene, wt, pos, mut = m.groups()
    return Substitution(profile.strip(), gene, wt, int(pos), mut)


def _get(url, tries=3):
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.loads(r.read().decode())
        except (urllib.error.URLError, TimeoutError):
            if attempt == tries - 1:
                raise
            time.sleep(1.5 * (attempt + 1))
    return None


def fetch_sequence(gene, cache_dir, polite=0.2):
    """The reviewed human entry for a gene symbol, cached on disk. Returns None when UniProt has
    no reviewed entry under that symbol, which happens and is not an error."""
    cache = Path(cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    hit = cache / f"{gene}.json"
    if hit.exists():
        return json.loads(hit.read_text()) or None

    query = f"gene_exact:{gene}+AND+organism_id:9606+AND+reviewed:true"
    data = _get(f"{UNIPROT}?query={query}&fields=accession,id,sequence&format=json&size=5")
    time.sleep(polite)

    entries = [
        {
            "accession": r["primaryAccession"],
            "name": r.get("uniProtkbId", ""),
            "sequence": r["sequence"]["value"],
        }
        for r in data.get("results", [])
        if r.get("sequence", {}).get("value")
    ]
    out = {"gene": gene, "entries": entries}
    hit.write_text(json.dumps(out))
    return out if entries else None


def pick_entry(sub, record):
    """Prefer the entry whose sequence actually carries the wild-type residue. With several
    reviewed entries under one symbol this is the only way to choose that is not a coin flip."""
    if not record:
        return None, "no reviewed human entry"
    agreeing = [
        e for e in record["entries"]
        if len(e["sequence"]) >= sub.pos and e["sequence"][sub.pos - 1] == sub.wt
    ]
    if agreeing:
        return agreeing[0], "ok"
    short = [e for e in record["entries"] if len(e["sequence"]) < sub.pos]
    if short and len(short) == len(record["entries"]):
        return None, "position past the end of the sequence"
    return None, "wild-type residue disagrees with the sequence"
