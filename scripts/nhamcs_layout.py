"""Read the record layout out of the NHAMCS documentation, because the data file is 38 MB of
fixed-width ASCII with nothing in it to say where one field ends and the next begins.

    python3 scripts/nhamcs_layout.py data/nhamcs-raw            # writes one layout per year

Each year's PDF carries a table like

    ITEM      FIELD      FILE
     NO.     LENGTH      LOCATION         [ITEM NAME], DESCRIPTION, AND CODES

    3           4          4-7            [ARRTIME] ARRIVAL TIME (military time)

and the column positions move between years, which is the whole reason this is a script rather
than a hardcoded dictionary. Four years are used — two to fit on and two to be surprised by —
so four layouts have to agree about what a field is called and disagree about where it lives.

It checks itself: every field must be contiguous with the one before it, the lengths must add up
to the record length the data file actually has, and a field name appearing twice is an error
rather than a last-one-wins.

Needs `pdftotext -layout` to have been run on the documentation PDF first; the loader says how."""

import json
import re
import sys
from pathlib import Path

# "6          3        16-18      [AGE] PATIENT AGE ..." and the single-column form "19".
ROW = re.compile(r"^\s*(\d{1,3})\s+(\d{1,3})\s+(\d{1,5})(?:\s*-\s*(\d{1,5}))?\s+\[([A-Z0-9_]+)\]")


def layout_from(text):
    """Every field the documentation declares, in file order."""
    fields, seen = [], {}
    for line in text.splitlines():
        m = ROW.match(line)
        if not m:
            continue
        item, length, start, end, name = m.groups()
        length, start = int(length), int(start)
        end = int(end) if end else start
        if end - start + 1 != length:
            # a wrapped line or a page header that happens to match; the lengths are the check
            continue
        if name in seen:
            # the PDF repeats a few headers; keep the first and make sure they agree
            if seen[name] != (start, end):
                raise SystemExit(f"{name} is declared twice, at {seen[name]} and {(start, end)}")
            continue
        seen[name] = (start, end)
        fields.append({"name": name, "item": int(item), "start": start, "end": end,
                       "length": length})
    fields.sort(key=lambda f: f["start"])
    return fields


def gaps(fields):
    """Where the layout is not contiguous. A gap means a field was missed, which would put every
    later field one column out and produce a file that parses into nonsense silently."""
    out, at = [], 1
    for f in fields:
        if f["start"] != at:
            out.append({"after": at - 1, "next_field": f["name"], "starts_at": f["start"]})
        at = f["end"] + 1
    return out, at - 1


def main(root):
    root = Path(root)
    found = sorted(root.glob("doc*.txt"))
    if not found:
        raise SystemExit(f"No doc*.txt in {root}. Run:\n"
                         f"  pdftotext -layout {root}/doc22-ed-508.pdf {root}/doc22.txt")
    for path in found:
        year = f"20{path.stem.replace('doc', '')}"
        fields = layout_from(path.read_text(errors="replace"))
        holes, width = gaps(fields)
        out = root / f"layout-{year}.json"
        out.write_text(json.dumps({"year": year, "declared_width": width,
                                   "fields": fields, "gaps": holes}, indent=1))
        print(f"{year}: {len(fields):>4} fields, declared width {width}, "
              f"{len(holes)} gap{'' if len(holes) == 1 else 's'} -> {out.name}")
        for hole in holes[:5]:
            print(f"    gap after column {hole['after']}, {hole['next_field']} starts at "
                  f"{hole['starts_at']}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/nhamcs-raw")
