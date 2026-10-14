"""What came back, per reviewer, scored against the answer key.

    python3 scripts/read_replies.py replies.jsonl

Each reviewer submits on every change, so the file holds many partial rows per person — the last
row for a token is the complete one. This keeps the latest per token, then puts their judgement
next to what actually happened, which is the point: a reviewer who says "you should not have
answered that" on a case the gate got WRONG has found a real failure."""

import json
import sys
from collections import Counter
from pathlib import Path

KEYS = Path("docs/review/answers.json")


def main(path):
    rows = [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]
    if not rows:
        print("nothing in there yet")
        return
    latest = {}
    for row in rows:
        now = latest.get(row["who"])
        if now is None or row["answered"] >= now["answered"]:
            latest[row["who"]] = row

    key = {c["case"]: c for c in json.loads(KEYS.read_text())["cases"]} if KEYS.exists() else {}
    labels = {}
    invites = Path("docs/review/invites.txt")
    if invites.exists():
        for line in invites.read_text().splitlines():
            if line.startswith("#") or "\t" not in line:
                continue
            token, label = line.split("\t", 1)
            labels[token] = label

    for who, row in sorted(latest.items(), key=lambda kv: -kv[1]["answered"]):
        print(f"\n{'=' * 74}")
        print(f"{labels.get(who, '(unknown token)')}  ·  {who}  ·  {row['role'] or 'role not given'}")
        print(f"{row['answered']} cases · finished: {row['done']} · last at {row['at']}")
        if row["switch_on"]:
            print(f"would switch it on: {row['switch_on']}")
        if row["stupidest"]:
            print(f"most obviously stupid thing: {row['stupidest']}")
        print(f"{'-' * 74}")
        tally = Counter()
        for case, a in sorted(row["answers"].items(), key=lambda kv: int(kv[0])):
            k = key.get(int(case), {})
            did = ("answered " + str(k.get("it_said"))) if k.get("answered") else "handed over"
            truth = k.get("true_condition", "?")
            flag = ""
            if k.get("answered") and not k.get("it_was_right"):
                flag = "  <- THE GATE WAS WRONG HERE"
            tally[a.get("call", "-")] += 1
            print(f"  case {case:>2}  call={a.get('call', '-')} next={a.get('next', '-')}"
                  f"   it {did:<28} truly {truth}{flag}")
            if a.get("why"):
                print(f"            \"{a['why']}\"")
        total = sum(v for k, v in tally.items() if k in "yn?")
        if total:
            print(f"\n  on the handover call: {tally['y']} reasonable, {tally['n']} not, "
                  f"{tally['?']} unsure, of {total} judged")
    print(f"\n{'=' * 74}")
    print("Describe this exactly. One reviewer is one reviewer; 'clinically validated' is not a")
    print("thing that has happened. Four of the thirty cases are not blind — see answers.json.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "replies.jsonl")
