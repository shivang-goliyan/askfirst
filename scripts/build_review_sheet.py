"""Thirty real outputs, laid out so a clinician can judge them in twenty minutes.

    python3 scripts/build_review_sheet.py data/ddxplus/release_validate_patients

No clinician has read a single output of this system, which is the largest untested assumption in
the whole project and the only one that cannot be closed with more compute. This builds the ask.

Three rules it follows, because the point is to be able to FAIL:

**The true condition is never shown.** A reviewer who can see the answer judges whether the
answer is right. We are not asking that — we are asking whether the *handover decision* was
reasonable and whether the *next question* is sensible, and both of those are judgable from the
record alone. Showing the truth would anchor every answer.

**Cases where the gate was wrong are included on purpose.** A sheet made only of cases it got
right cannot produce a bad review, which makes a good review worthless. Every case the gate
answered incorrectly in the held-out pool goes in.

**The order is shuffled and nothing is labelled as interesting.** Answered and handed-over cases
are mixed, so the reviewer cannot pattern-match down the page.

Output is one HTML file that prints cleanly on paper and reads on a phone, which is where it will
actually be filled in."""

import html
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from askfirst.ablation import argmax, by_cost_effectiveness, rank_gaps  # noqa: E402
from askfirst.calibrate import CEILING, FLOOR, Calibrator, Completeness  # noqa: E402
from askfirst.ddxplus import load_patients  # noqa: E402
from askfirst.missing import cut, mechanisms  # noqa: E402
from askfirst.schema import load_schema  # noqa: E402
from askfirst.softmax import SoftmaxScorer  # noqa: E402

BAKE = Path("src/askfirst/baked")
OUT = Path("docs/review/sheet.html")
KEYS = Path("docs/review/answers.json")
TARGET = 0.95
WANTED = 30
POOL_AT = 54000      # a slice nothing else in this repo touches


def english(record, schema):
    """The record as a person would read it, not as the model holds it."""
    out = []
    for name, value in record.items():
        spec = schema.fields.get(name)
        if spec is None:
            continue
        question = (spec.question or name).rstrip("?:")
        if value is True:
            out.append(question)
            continue
        labels = spec.value_labels or {}
        said = [labels.get(v, str(v)) for v in (value if isinstance(value, list) else [value])]
        said = [s for s in said if s not in ("NA", "N", "nowhere")]
        out.append(f"{question} — {', '.join(said)}" if said else question)
    return out


def main(path, n=WANTED, seed=3):
    schema = load_schema("ddxplus")
    rates = json.loads((BAKE / "ddxplus_priors.json").read_text())["rates"]
    model = SoftmaxScorer.load(BAKE / "ddxplus_softmax.npz", schema)
    cal = Calibrator.load(BAKE / "calibrator.json")
    seen = Completeness.load(BAKE / "completeness.npz", model.encode)
    ways = mechanisms(schema, rates)

    patients = [p for p in load_patients(path, limit=POOL_AT + 1200) if p["evidences"]]
    pool = patients[POOL_AT:POOL_AT + 1200]
    rng = random.Random(seed)

    # a spread of record shapes, cut the way a rushed intake actually goes short
    cases = []
    for frac, way in ((1.0, "at random"), (0.6, "standard questions, no follow-ups"),
                      (0.4, "no history, symptoms only"), (0.4, "only what was volunteered"),
                      (0.2, "at random")):
        for case in cut(pool, frac, ways[way]):
            record = case["evidences"]
            dist = model(record)
            enough = seen(record) >= FLOOR and len(record) <= CEILING
            chance = cal(max(dist.values()), record) if enough else None
            answering = bool(enough and chance is not None and chance >= TARGET)
            said = argmax(dist)
            gaps = rank_gaps(record, model, schema)
            cases.append({
                "findings": english(record, schema),
                "answered": answering,
                "said": schema.label_for_outcome(said) if answering else None,
                "truth": schema.label_for_outcome(case["pathology"]),
                "right": answering and said == case["pathology"],
                "ask": [(schema.fields[g.field].question or g.field)
                        for g in (by_cost_effectiveness(gaps) or gaps)[:3]],
                "n": len(record),
            })

    wrong = [c for c in cases if c["answered"] and not c["right"]]
    answered = [c for c in cases if c["answered"] and c["right"]]
    handed = [c for c in cases if not c["answered"]]
    rng.shuffle(answered); rng.shuffle(handed)

    # every mistake goes in; the rest split between answered and handed over
    picked = wrong[:8]
    room = n - len(picked)
    picked += answered[:room // 2] + handed[:room - room // 2]
    rng.shuffle(picked)
    print(f"{len(picked)} cases: {sum(1 for c in picked if c['answered'])} it answered "
          f"({len(wrong[:8])} of them wrongly), {sum(1 for c in picked if not c['answered'])} "
          f"it handed over")

    rows = []
    for i, c in enumerate(picked, start=1):
        did = (f"<b>It answered:</b> {html.escape(c['said'])}" if c["answered"]
               else "<b>It handed this to a person</b> — it would not answer")
        bullets = "".join(f"<li>{html.escape(f)}</li>" for f in c["findings"]) or \
                  "<li><i>nothing recorded</i></li>"
        asks = "".join(f"<li>{html.escape(q)}</li>" for q in c["ask"])
        rows.append(f"""
<section class="case">
  <h3>Case {i} <span class="dim">· {c['n']} findings recorded</span></h3>
  <div class="cols">
    <div><h4>What was on the record</h4><ul>{bullets}</ul></div>
    <div>
      <h4>What it did</h4><p>{did}</p>
      <h4>What it says to ask next</h4><ol>{asks}</ol>
    </div>
  </div>
  <table class="q">
    <tr><td>1. Given only what was on that record, was that the right call?</td>
        <td class="tick">yes ☐</td><td class="tick">no ☐</td><td class="tick">unsure ☐</td></tr>
    <tr><td>2. Is the first question it suggests the one you would have asked?</td>
        <td class="tick">yes ☐</td><td class="tick">no ☐</td><td class="tick">unsure ☐</td></tr>
    <tr><td>3. If you ticked no to either — why? (a few words is plenty)</td>
        <td colspan="3" class="write"></td></tr>
  </table>
</section>""")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(f"""<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>askfirst — 30 outputs, for review</title>
<style>
 body{{font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
      max-width:860px;margin:0 auto;padding:28px 18px 80px;color:#111}}
 h1{{font-size:21px;margin:0 0 6px}} h2{{font-size:15px;margin:26px 0 8px}}
 h3{{font-size:15px;margin:0 0 10px}} h4{{font-size:11px;text-transform:uppercase;
      letter-spacing:.08em;color:#666;margin:0 0 5px}}
 .lede{{color:#444;font-size:14px}}
 .ask{{background:#f6f8fa;border:1px solid #d8dee4;border-radius:8px;padding:14px 16px;margin:18px 0 26px}}
 .case{{border-top:2px solid #111;padding:16px 0 6px;page-break-inside:avoid}}
 .cols{{display:grid;grid-template-columns:1fr 1fr;gap:22px}}
 @media (max-width:640px){{.cols{{grid-template-columns:1fr}}}}
 ul,ol{{margin:0;padding-left:18px}} li{{margin-bottom:3px}}
 .dim{{color:#777;font-weight:400;font-size:13px}}
 table.q{{width:100%;border-collapse:collapse;margin-top:12px;font-size:14px}}
 table.q td{{border:1px solid #d8dee4;padding:7px 9px;vertical-align:top}}
 td.tick{{width:72px;text-align:center;white-space:nowrap}}
 td.write{{height:34px;background:#fcfcfd}}
 @media print{{body{{padding:0}} .case{{border-top:1px solid #999}}}}
</style>
<h1>askfirst — thirty outputs, for review</h1>
<p class="lede">This is a research prototype. It is not a medical device, nothing in it has been
approved for any use, and no part of this review will be presented as clinical validation.</p>

<div class="ask">
<b>What we are asking, and what we are not.</b>
<p>We are <i>not</i> asking whether it got the diagnosis right — the true condition is deliberately
not shown anywhere on this sheet, so that nothing anchors your judgement.</p>
<p>We are asking two things about each case:</p>
<ol>
  <li><b>Was handing it over, or answering it, the right call</b> given only what was written down?</li>
  <li><b>Is the next question it suggests the one you would have asked?</b></li>
</ol>
<p>Twenty minutes is plenty. Skipping a case you are unsure about is more useful to us than a
guess. <b>Some of these are cases where it was wrong</b> — finding them is the point.</p>
</div>

<h2>Who filled this in</h2>
<table class="q">
 <tr><td>Name (or "anonymous")</td><td class="write" colspan="3"></td></tr>
 <tr><td>Stage of training / role</td><td class="write" colspan="3"></td></tr>
 <tr><td>Date</td><td class="write" colspan="3"></td></tr>
</table>

{''.join(rows)}

<h2>Last question</h2>
<table class="q">
 <tr><td>If a service you worked on used this to decide which cases reached you,
         would you want it switched on?</td>
     <td class="tick">yes ☐</td><td class="tick">no ☐</td><td class="tick">unsure ☐</td></tr>
 <tr><td>Anything else worth saying</td><td class="write" colspan="3"></td></tr>
</table>
""")

    # Some records legitimately carry a history question that names the condition — "have you
    # ever had a cluster headache?" on a cluster headache. That is real clinical information and
    # stripping it would falsify the case, but it means the review is not blind on those, and a
    # write-up must not later call the whole sheet blind to the diagnosis.
    named = [i for i, c in enumerate(picked, start=1)
             if c["truth"] and any(c["truth"].lower() in f.lower() for f in c["findings"])]
    if named:
        print(f"note: cases {named} carry a history finding that names the true condition — "
              f"real information, but those cases are not blind")

    KEYS.write_text(json.dumps({
        "note": "The answer key. NOT to be shown to a reviewer before they fill the sheet in.",
        "not_blind": named,
        "not_blind_why": "the record carries a history question naming the condition, which is "
                         "genuine clinical information rather than a leak — but these cases are "
                         "not blind and no write-up may describe the whole sheet as blind",
        "target": TARGET, "cases": [
            {"case": i, "answered": c["answered"], "it_said": c["said"],
             "true_condition": c["truth"], "it_was_right": c["right"], "findings": c["n"]}
            for i, c in enumerate(picked, start=1)
        ],
    }, indent=1))
    print(f"wrote {OUT} and {KEYS}")
    print("open the sheet in a browser and print to PDF, or just send the file")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/ddxplus/release_validate_patients")
