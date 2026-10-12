"""Turn DDXPlus's evidence definitions into a field schema. Run from the repo root:
    python3 -I scripts/build_schema.py data/ddxplus/release_evidences.json
"""
import json
import sys
from pathlib import Path

OUT = Path("src/askfirst/schemas/ddxplus.yaml")


def quote(v):
    return f'"{v}"' if isinstance(v, str) else str(v)


def main(path):
    ev = json.load(open(path))
    lines = [
        "# Generated from DDXPlus release_evidences.json (CC BY 4.0). Do not hand-edit;",
        "# rerun scripts/build_schema.py instead.",
        "#",
        "# Every field here is a question a clinician asks, so acquisition cost is uniform.",
        "# Cost-aware ranking is exercised by the clinical and variant schemas, not this one.",
        "domain: ddxplus",
        "outcomes: []   # filled from release_conditions.json at load time",
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

        row = (
            f'  {key}: {{kind: {kind}, cost: 1, minutes: 1, '
            f'values: [{", ".join(quote(v) for v in values)}], '
            f'question: {json.dumps(spec["question_en"])}}}'
        )
        (antecedents if spec["is_antecedent"] else lines).append(row)

    OUT.write_text("\n".join(lines + antecedents) + "\n")
    binary = sum(1 for s in ev.values() if s["data_type"] == "B")
    print(f"wrote {OUT}  —  {len(ev)} fields "
          f"({binary} binary, {len(ev) - binary} multi-valued)")


if __name__ == "__main__":
    main(sys.argv[1])
