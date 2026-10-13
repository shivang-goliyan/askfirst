"""Turn DDXPlus's evidence definitions into a field schema. Run from the repo root:
    python3 -I scripts/build_schema.py data/ddxplus/release_evidences.json
"""
import json
import sys
from pathlib import Path

OUT = Path("src/askfirst/schemas/ddxplus.yaml")


def quote(v):
    return f'"{v}"' if isinstance(v, str) else str(v)


def main(path, conditions_path=None):
    ev = json.load(open(path))
    outcomes, english = [], {}
    if conditions_path:
        cond = json.load(open(conditions_path))
        # The join key is cond-name-eng, verified against the data: release_conditions.json is
        # keyed in French ("Pneumothorax spontane"), while the patient CSV's PATHOLOGY column
        # holds the English name ("Anemia"). This file previously keyed outcomes on the French
        # name on the stated assumption that the CSV matched it — it does not, and the overlap
        # with the labels was 1 of 42. Anything scoring against schema.outcomes was comparing
        # French predictions to English ground truth.
        english = {}
        for french, spec in cond.items():
            key = spec.get("cond-name-eng") or french
            english[key] = french
        outcomes = sorted(english)
    lines = [
        "# Generated from DDXPlus release_evidences.json (CC BY 4.0). Do not hand-edit;",
        "# rerun scripts/build_schema.py instead.",
        "#",
        "# Every field here is a question a clinician asks, so acquisition cost is uniform.",
        "# Cost-aware ranking is exercised by the clinical and variant schemas, not this one.",
        "domain: ddxplus",
        "outcomes:",
        *(f"  - {json.dumps(o)}" for o in outcomes),
        "",
        "# The source file's own French name for each, kept so the provenance is traceable.",
        "# Provenance only. These are not display labels and nothing should score against them.",
        "outcome_sources:",
        *(f"  {json.dumps(k)}: {json.dumps(v)}" for k, v in sorted(english.items())),
        "",
        "fields:",
    ]
    antecedents = ["", "antecedents:"]

    for key, spec in sorted(ev.items()):
        values = spec.get("possible-values") or []
        if spec["data_type"] == "B":
            kind, values = "binary", ["present", "absent"]
        elif spec["data_type"] == "C":
            kind = "categorical"
        else:
            kind = "multi"

        labels = {
            v: (meaning.get("en") or str(v))
            for v, meaning in (spec.get("value_meaning") or {}).items()
        }
        row = (
            f'  {key}: {{kind: {kind}, cost: 1, minutes: 1, '
            f'values: [{", ".join(quote(v) for v in values)}], '
            f'question: {json.dumps(spec["question_en"])}'
            + (f', value_labels: {json.dumps(labels, ensure_ascii=False)}' if labels else "")
            + "}"
        )
        (antecedents if spec["is_antecedent"] else lines).append(row)

    OUT.write_text("\n".join(lines + antecedents) + "\n")
    binary = sum(1 for s in ev.values() if s["data_type"] == "B")
    print(f"wrote {OUT}  —  {len(ev)} fields "
          f"({binary} binary, {len(ev) - binary} multi-valued), {len(outcomes)} outcomes")


if __name__ == "__main__":
    main(*sys.argv[1:3])
