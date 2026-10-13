"""Real emergency department visits, with the missingness that actually happened.

NHAMCS is the CDC's National Hospital Ambulatory Medical Care Survey. The ED public use file is
one line per visit of fixed-width ASCII, about 16,000-20,000 visits a year, and a vital is
missing from it because nobody charted it rather than because we deleted it. That is the whole
reason this module exists: every other measurement in this repo hides evidence according to a
pattern we chose.

Two things to know before reading a number off this.

**It is a survey.** `PATWT` exists to turn these visits into national estimates and nothing here
uses it, because a per-visit gate is not a national estimate. No figure derived from this module
is a statement about US emergency departments.

**"Missing" means "not documented".** The file is abstracted from the chart after the visit, so a
blank pulse oximetry is a thing nobody wrote down, which is related to but not identical to a
thing nobody knew at triage. It also clusters by hospital — some sites chart far less than others
— which is why `hospital` comes back with every record and why intervals over this data have to
resample sites rather than visits.

The NCHS data use agreement permits statistical reporting and analysis, forbids any attempt to
identify a person or establishment, and forbids linking the file with individually identifiable
data. Nothing here links, re-identifies, or is committed to the repository."""

import zipfile
from pathlib import Path

# Blank and Unknown. Both mean "there is no value here", which is the point.
NOTHING = (-9, -8)

# What is on the form at triage, and nothing from the visit itself — no labs, no imaging, no
# length of stay, nothing disposition-adjacent. Bands are the conventional clinical ones; what
# matters for this measurement is that they are fixed in advance and the same across all years.
BANDS = {
    "AGE": ((0, "under 1"), (4, "1-4"), (14, "5-14"), (24, "15-24"), (44, "25-44"),
            (64, "45-64"), (74, "65-74"), (200, "75 and over")),
    # an implied decimal between the third and fourth digits: 0986 is 98.6F
    "TEMPF": ((969, "under 97"), (990, "97.0-99.0"), (1004, "99.1-100.4"),
              (1022, "100.5-102.2"), (2000, "over 102.2")),
    "PULSE": ((49, "under 50"), (59, "50-59"), (100, "60-100"), (120, "101-120"),
              (150, "121-150"), (400, "over 150")),
    "RESPR": ((11, "under 12"), (20, "12-20"), (24, "21-24"), (30, "25-30"), (200, "over 30")),
    "BPSYS": ((89, "under 90"), (119, "90-119"), (139, "120-139"), (179, "140-179"),
              (400, "180 and over")),
    "BPDIAS": ((59, "under 60"), (79, "60-79"), (89, "80-89"), (109, "90-109"),
               (300, "110 and over")),
    "POPCT": ((89, "under 90"), (93, "90-93"), (95, "94-95"), (100, "96 and over")),
    "PAINSCALE": ((0, "none"), (3, "1-3 mild"), (6, "4-6 moderate"), (9, "7-9 severe"),
                  (10, "10 worst")),
}

CODED = {
    "SEX": {1: "female", 2: "male"},
    "ARREMS": {1: "by ambulance", 2: "not by ambulance"},
    "SEEN72": {1: "seen here in the last 72 hours", 2: "not seen here in the last 72 hours"},
    # 0 is "no triage reported" and 7 is "a unit that does not triage" — both are an absence of
    # a triage level rather than a level, so neither becomes a value
    "IMMEDR": {1: "immediate", 2: "emergent", 3: "urgent", 4: "semi-urgent", 5: "nonurgent"},
}

REASONS = ("RFV1", "RFV2", "RFV3")

# Escalated: a bed was needed somewhere. Admitted here, admitted to observation and then
# hospitalised, transferred out, or died in the department.
ESCALATION = ("ADMITHOS", "OBSHOS", "TRANOTH", "DIEDED")

TRIAGE = tuple(BANDS) + tuple(CODED) + REASONS

# What every visit should have on it. RFV2 and RFV3 are deliberately not in here: a patient with
# one complaint has one reason for visiting, so their absence is a fact about the patient rather
# than about the charting, and counting them would make "completeness" partly a measure of how
# many things were wrong with somebody. They stay as features; they just do not count toward how
# complete a record is.
CORE = tuple(BANDS) + tuple(CODED) + ("RFV1",)


def band(name, value):
    for ceiling, label in BANDS[name]:
        if value <= ceiling:
            return label
    return None


def pull(line, span):
    """One field, as an int, or None when the column holds nothing usable."""
    start, end = span
    raw = line[start - 1:end].strip()
    if not raw or raw in ("-9", "-8"):
        return None
    try:
        n = int(raw)
    except ValueError:
        return None
    return None if n in NOTHING else n


def read_year(archive, layout, reasons=None):
    """Every visit in one year's file, as a record of charted findings plus what happened.

    `reasons` is the set of reason-for-visit codes worth keeping as their own value; everything
    else becomes "other". It has to be decided on the fit years and passed in, or the test years
    would be contributing to the vocabulary they are then scored against."""
    where = {f["name"]: (f["start"], f["end"]) for f in layout["fields"]}
    for need in TRIAGE + ESCALATION + ("HOSPCODE",):
        if need not in where:
            raise SystemExit(f"{layout['year']} has no {need} in its layout")

    out = []
    with zipfile.ZipFile(archive) as zf:
        with zf.open(zf.infolist()[0]) as fh:
            for raw in fh:
                line = raw.decode("latin-1").rstrip("\r\n")
                if len(line) < layout["declared_width"]:
                    continue
                found = {}
                for name in BANDS:
                    value = pull(line, where[name])
                    if value is None:
                        continue
                    label = band(name, value)
                    if label is not None:
                        found[name] = label
                for name, codes in CODED.items():
                    value = pull(line, where[name])
                    if value in codes:
                        found[name] = codes[value]
                for name in REASONS:
                    value = pull(line, where[name])
                    if value is None:
                        continue
                    # -9 is already gone; the blank code is a run of 9s
                    if value >= 99990:
                        continue
                    found[name] = str(value) if reasons is None or value in reasons else "other"

                escalated = any((pull(line, where[f]) or 0) == 1 for f in ESCALATION)
                # HOSPCODE is re-assigned each year, so hospital 12 in 2018 is not hospital 12
                # in 2022. Anything clustering across pooled years has to use the pair, and
                # using the bare code would silently merge unrelated sites.
                site = pull(line, where["HOSPCODE"])
                out.append({
                    "evidences": found,
                    "pathology": "escalated" if escalated else "discharged",
                    "hospital": f"{layout['year']}-{site}",
                    "year": layout["year"],
                })
    return out


def reason_vocabulary(archives, layouts, keep=60):
    """The reason-for-visit codes common enough to be worth their own feature, counted on the
    fit years only. There are hundreds; most appear a handful of times and would be noise with a
    coefficient attached."""
    from collections import Counter
    tally = Counter()
    for archive, layout in zip(archives, layouts):
        where = {f["name"]: (f["start"], f["end"]) for f in layout["fields"]}
        with zipfile.ZipFile(archive) as zf:
            with zf.open(zf.infolist()[0]) as fh:
                for raw in fh:
                    line = raw.decode("latin-1").rstrip("\r\n")
                    for name in REASONS:
                        value = pull(line, where[name])
                        if value is not None and value < 99990:
                            tally[value] += 1
    return {code for code, _ in tally.most_common(keep)}


def charted(record):
    """How many of the items every visit should have this visit actually has.

    Unlike DDXPlus, the denominator here is known: the form is the same for everybody, so
    completeness is observed rather than estimated. That is worth saying because it means the
    ridge estimator has nothing to do on this data."""
    return sum(1 for name in CORE if name in record)


def completeness(record):
    return charted(record) / len(CORE)


def vitals_charted(record):
    return sum(1 for name in ("TEMPF", "PULSE", "RESPR", "BPSYS", "BPDIAS", "POPCT")
               if name in record)


def find(root="data/nhamcs-raw"):
    """The years on disk, as (year, archive, layout path) sorted by year."""
    import json
    root = Path(root)
    out = []
    for archive in sorted(root.glob("*.zip")):
        year = "".join(c for c in archive.stem if c.isdigit())
        layout = root / f"layout-{year}.json"
        if layout.exists():
            out.append((year, archive, json.loads(layout.read_text())))
    return out


def schema_for(records):
    """A Schema over the triage form, so the scorer, the calibration and the ranker all work
    unchanged. Answer rates are measured on whatever records are passed in, which has to be the
    fit years only — a rate measured on the test years is the test years telling the calibration
    how unusual its own findings are."""
    from .schema import Field, Schema

    values, seen = {}, {}
    for name in BANDS:
        values[name] = [label for _, label in BANDS[name]]
    for name, codes in CODED.items():
        values[name] = list(codes.values())
    for name in REASONS:
        values[name] = []
    for record in records:
        for name, value in record["evidences"].items():
            seen[name] = seen.get(name, 0) + 1
            if name in REASONS and value not in values[name]:
                values[name].append(value)

    n = max(1, len(records))
    fields = {}
    for name in TRIAGE:
        fields[name] = Field(
            name=name, kind="categorical", values=sorted(values[name]), cost=0.0, delay=0.0,
            priors={}, question=QUESTIONS.get(name, name),
            asked_rate=seen.get(name, 0) / n,
            section="fields" if name in CORE else "antecedents",
        )
    return Schema(domain="nhamcs", outcomes=["discharged", "escalated"], fields=fields,
                  labels={"escalated": "needed a bed", "discharged": "went home"}, sources={})


QUESTIONS = {
    "AGE": "How old is the patient?",
    "SEX": "Sex",
    "TEMPF": "Temperature",
    "PULSE": "Heart rate",
    "RESPR": "Respiratory rate",
    "BPSYS": "Systolic blood pressure",
    "BPDIAS": "Diastolic blood pressure",
    "POPCT": "Pulse oximetry",
    "PAINSCALE": "Pain score",
    "ARREMS": "Did they arrive by ambulance?",
    "SEEN72": "Seen in this department in the last 72 hours?",
    "IMMEDR": "Triage immediacy",
    "RFV1": "Main reason for the visit",
    "RFV2": "Second reason, if any",
    "RFV3": "Third reason, if any",
}
