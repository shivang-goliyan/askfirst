"""Freeze a few note-to-findings examples so the page can show the prose path with no GPU.

    python3 scripts/bake_notes.py

The extraction itself needs an open model. These examples were produced by one, on a rented GPU,
and are baked so a visitor can see the whole path — prose in, findings out, refusal or answer —
on a box with no accelerator at all. Each carries what the model found, what the record really
held, and what it therefore missed, because a demo of an extraction step that hides its misses
would be the wrong demo for this project."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from askfirst.schema import load_schema  # noqa: E402

SOURCE = Path("docs/results/rehearsal-extraction.json")
OUT = Path("src/askfirst/baked/notes.json")
WANT = 4


def main():
    blob = json.loads(SOURCE.read_text())
    schema = load_schema("ddxplus")
    rows = blob["examples"]

    picked = []
    for row in rows:
        note = row["note"].strip()
        if not (200 <= len(note) <= 700):
            continue
        picked.append({
            "note": note,
            "found": [
                {"field": f, "question": schema.fields[f].question or f}
                for f in row["found"] if f in schema.fields
            ],
            "missed": [
                {"field": f, "question": schema.fields[f].question or f}
                for f in row["missed"] if f in schema.fields
            ],
            "invented": [
                {"field": f, "question": schema.fields[f].question or f}
                for f in row["invented"] if f in schema.fields
            ],
            "in_the_record": len(row["truth"]),
        })
        if len(picked) == WANT:
            break

    OUT.write_text(json.dumps({
        "model": blob["model"],
        "where": "a rented GPU, 13 Oct — not AMD, and not baked into any measured result",
        "recall": blob["recall"],
        "precision": blob["precision"],
        "cases_measured": blob["cases"],
        "note": "the note was written by the same model that read it back, which is easier than "
                "a real clinical note. Read these as a demonstration of the path, not as "
                "evidence about real notes.",
        "examples": picked,
    }, indent=1))
    print(f"wrote {OUT} — {len(picked)} notes")
    for p in picked:
        print(f"  {len(p['note']):>4} chars, found {len(p['found'])} of {p['in_the_record']}, "
              f"{len(p['invented'])} invented")


if __name__ == "__main__":
    main()
