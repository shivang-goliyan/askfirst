"""Prose in, findings out, on a CPU.

The measured extractor is an open model asking each of the schema's 223 questions one at a time
and reading *yes* against *no* off the log probabilities. It recovers 72% of findings at 87.3%
precision and it needs a GPU (`2026-10-13-prose-in-findings-out.md`). That is the good one.

This is the one that runs anywhere. It matches the schema's own wording against the note: the
content words of each binary question, and the value labels of everything else. No model, no
accelerator, about a millisecond a note. It exists because a gate you cannot feed is not a
product, and until today the only way to feed this one was to tick boxes.

It is worse than the open model and the number is in `2026-10-14-reading-a-note-without-a-gpu.md`.
What makes it usable anyway is a property that was measured before it existed: **a weaker reader
costs coverage, not safety.** Findings it misses make the record look thinner, and a thinner
record is what the gate refuses — so extraction error turns into caution rather than into a
confident mistake.

Two things it does that a naive matcher does not, both because the first version was embarrassing:

- **Negation.** "denies chest pain", "no fever", "without cough" must not fire the finding. The
  first version read a note that said "no haemoptysis" and recorded haemoptysis.
- **Longest match first.** "pain" fires inside "painless" and "chest pain radiating to the jaw"
  should beat "pain". Phrases are tried longest-first and consumed.
"""

import re

# Words that carry no signal. Dropped from question text before it becomes a trigger, because
# "Do you have a cough?" should trigger on "cough" and not on "do", "you" or "have".
EMPTY = {
    "a", "about", "above", "after", "all", "also", "an", "and", "any", "are", "as", "at", "be",
    "been", "being", "believe", "but", "by", "can", "consulting", "could", "did", "do", "does",
    "ever", "feel", "felt", "find", "following", "for", "from", "had", "has", "have", "how",
    "if", "in", "is", "it", "its", "just", "like", "may", "more", "most", "much", "no", "not",
    "of", "on", "one", "or", "other", "over", "own", "recently", "related", "require",
    "required", "same", "she", "should", "since", "so", "some", "such", "than", "that", "the",
    "their", "them", "then", "there", "these", "they", "think", "this", "those", "through",
    "to", "too", "under", "up", "very", "was", "we", "were", "what", "when", "where", "which",
    "while", "who", "why", "will", "with", "would", "you", "your", "yourself", "problems",
    "condition", "symptoms", "last", "weeks", "days", "months", "years", "time", "please",
    "characterize", "intensity", "pain",
}

# Everything that turns a finding off. Scanned in a window before the match.
DENIED = (
    "no", "not", "non", "none", "never", "without", "denies", "denied", "deny", "denying",
    "negative", "absent", "absence", "free", "unremarkable", "rules", "ruled", "nil",
)
WINDOW = 5          # words before the match that a negation can reach, within one clause
# A negation does not reach across a full stop, a semicolon or a line break. Without this,
# "Denies fever and denies cough. Known high blood pressure." threw away the blood pressure,
# because "denies" sat three words behind "high" on the other side of a sentence boundary.
BREAK = re.compile(r"[.;:\n!?]")
MIN_TRIGGER = 4     # a trigger shorter than this is noise, not a word


def words(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def clauses(text):
    """The text split where a negation stops reaching, with each piece's offset."""
    out, at = [], 0
    for piece in BREAK.split(text):
        out.append((at, piece))
        at += len(piece) + 1
    return out


def denied_before(clause, index):
    """Is this word, inside this clause, behind a negation?"""
    return any(w in DENIED for w in words(clause)[max(0, index - WINDOW):index])


def content_of(spec):
    """The words in a question that carry its meaning."""
    return [w for w in words(spec.question) if w not in EMPTY and len(w) >= MIN_TRIGGER]


SIDES = {"r": "right", "l": "left"}


def labels_of(spec):
    """For a non-binary field, the ways a note might write each value label.

    The schema writes a region as `hypochondrium(R)`. A note writes `hypochondrium (R)`, or
    `hypochondrium(R)`, or `right hypochondrium` — and the side is not decoration, it is which
    side of the patient. So each label becomes a small set of spellings rather than one."""
    out = {}
    for value, label in (spec.value_labels or {}).items():
        label = (label or "").strip()
        if not label or label in ("NA", "N", "Y", "nowhere"):
            continue
        low = label.lower()
        flat = re.sub(r"\s+", " ", re.sub(r"[()]", " ", low)).strip()
        if len(flat) < 3:
            continue
        spellings = {flat, low}
        side = re.match(r"^(.*?)\s*\(([rl])\)$", low)
        if side:
            stem, which = side.group(1).strip(), SIDES[side.group(2)]
            spellings |= {f"{stem}({which[0]})", f"{stem} ({which[0]})",
                          f"{which} {stem}", f"{stem} {which}"}
        out[value] = {sp for sp in spellings if len(sp) >= 3}
    return out


class Reader:
    """A lexical reader. Deliberately dumb, measured, and honest about which it is.

    The first version fired a binary field when any one long word from its question appeared in
    the note. That recovered 81.8% of findings at **43.3% precision** — nine invented findings a
    note — because "chronic" appears in the question for COPD and in the phrase "chronic cough",
    which is a different field. Invented findings are the dangerous direction: a missing finding
    makes the record look thinner and the gate refuses it, while an invented one makes the record
    look fuller than it is.

    So a binary field now needs a *share* of its question's content words present, not one of
    them, and the share is `overlap`."""

    def __init__(self, schema, overlap=0.6, least=2):
        self.schema = schema
        self.overlap = overlap
        self.least = least
        self.binary, self.labelled = {}, []
        for name, spec in schema.fields.items():
            if spec.kind == "binary":
                content = content_of(spec)
                if content:
                    self.binary[name] = content
            else:
                for value, spellings in labels_of(spec).items():
                    for spelling in spellings:
                        self.labelled.append((spelling, name, value))
        self.labelled.sort(key=lambda row: -len(row[0]))

    @staticmethod
    def all_denied(spots):
        """True when every mention of this field sits behind a negation in its own clause."""
        return bool(spots) and all(flag for _, flag in spots)

    def __call__(self, note):
        low = note.lower()
        # every word, with whether a negation reaches it inside its own clause
        where = {}
        for _, clause in clauses(low):
            said = words(clause)
            for i, w in enumerate(said):
                where.setdefault(w, []).append((clause, denied_before(clause, i)))

        found, refused = {}, []

        # non-binary fields: the label is the evidence, and it has to appear verbatim
        taken = []
        for label, name, value in self.labelled:
            for m in re.finditer(rf"(?<![a-z0-9]){re.escape(label)}(?![a-z0-9])", low):
                if any(not (m.end() <= s or m.start() >= e) for s, e in taken):
                    continue
                taken.append((m.start(), m.end()))
                head = note[:m.start()]
                tail = BREAK.split(head)[-1]
                if any(w in DENIED for w in words(tail)[-WINDOW:]):
                    refused.append({"field": name, "value": value, "phrase": label,
                                    "why": "the note denies it"})
                    break
                spec = self.schema.fields[name]
                if spec.kind == "multi":
                    found.setdefault(name, [])
                    if value not in found[name]:
                        found[name].append(value)
                else:
                    found.setdefault(name, value)
                break

        # binary fields: a share of the question's content words, not one of them
        for name, content in self.binary.items():
            hits = [w for w in content if w in where]
            if len(hits) < min(self.least, len(content)):
                continue
            if len(hits) / len(content) < self.overlap:
                continue
            spots = [hit for w in hits for hit in where[w]]
            if self.all_denied(spots):
                refused.append({"field": name, "value": None,
                                "phrase": " ".join(hits), "why": "the note denies it"})
                continue
            found[name] = True
        return found, refused
