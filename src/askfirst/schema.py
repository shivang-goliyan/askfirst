from dataclasses import dataclass, field as dc_field
from pathlib import Path

import yaml

SCHEMA_DIR = Path(__file__).parent / "schemas"


@dataclass
class Field:
    name: str
    kind: str
    values: list
    cost: float
    delay: float
    priors: dict = dc_field(default_factory=dict)
    question: str = ""
    value_labels: dict = dc_field(default_factory=dict)
    # How often asking this returns anything at all. A blood test always comes back with a
    # number, so 1.0 is right for an ordered test; a symptom question mostly comes back "no",
    # and DDXPlus records only the yeses, so the field is simply absent from the record.
    asked_rate: float = 1.0

    def label_for(self, value):
        if value in self.value_labels:
            return self.value_labels[value]
        if self.is_scale():
            return f"{value} of {max(self.values)}"
        return str(value)

    def is_scale(self):
        """A contiguous run of integers is an intensity scale, not a category. Rendering one as
        a bare number gives "How fast did the pain appear? -> 5", which reads like a bug."""
        vals = self.values
        if len(vals) < 3:
            return False
        if any(isinstance(v, bool) or not isinstance(v, int) for v in vals):
            return False
        return sorted(vals) == list(range(min(vals), max(vals) + 1))


@dataclass
class Schema:
    domain: str
    outcomes: list
    fields: dict
    labels: dict = dc_field(default_factory=dict)
    sources: dict = dc_field(default_factory=dict)

    def label_for_outcome(self, outcome):
        """What a person — or a model being asked to score it — should see. DDXPlus names its
        conditions in French in the source file; those names are provenance and live in
        `sources`, because showing them to an English-speaking reader is wrong and scoring an
        English record against them is worse."""
        return self.labels.get(outcome, outcome)

    def values_for(self, name):
        return self.fields[name].values

    def priors_for(self, name):
        """How likely each value is before we ask. Uniform when the schema doesn't say,
        which is a defensible default and a bad one — see fit_priors."""
        spec = self.fields[name]
        declared = spec.priors
        if not declared:
            share = 1.0 / len(spec.values)
            return {v: share for v in spec.values}

        total = sum(declared.get(v, 0.0) for v in spec.values)
        if total <= 0:
            raise ValueError(f"Priors for {name!r} add up to {total}, which can't be right")
        return {v: declared.get(v, 0.0) / total for v in spec.values}

    def missing_from(self, record):
        return [f for f in self.fields if f not in record]

    def present_in(self, record):
        return [f for f in record if f in self.fields]

    def with_priors(self, fitted, rates=None):
        rates = rates or {}
        fields = {}
        for name, spec in self.fields.items():
            fields[name] = Field(
                spec.name, spec.kind, spec.values, spec.cost, spec.delay,
                dict(fitted.get(name) or spec.priors), spec.question, spec.value_labels,
                float(rates.get(name, spec.asked_rate)),
            )
        return Schema(self.domain, self.outcomes, fields, self.labels, self.sources)


def _delay_of(spec):
    for key in ("minutes", "days", "hours"):
        if key in spec:
            return float(spec[key])
    return 0.0


def load_schema(domain):
    path = SCHEMA_DIR / f"{domain}.yaml"
    if not path.exists():
        available = ", ".join(sorted(p.stem for p in SCHEMA_DIR.glob("*.yaml")))
        raise FileNotFoundError(f"No schema called {domain!r}. Try one of: {available}")

    raw = yaml.safe_load(path.read_text())
    fields = {}
    for group in ("fields", "antecedents"):
        for name, spec in (raw.get(group) or {}).items():
            fields[name] = Field(
                name=name,
                kind=spec["kind"],
                values=list(spec["values"]),
                cost=float(spec.get("cost", 0)),
                delay=_delay_of(spec),
                priors=dict(spec.get("priors") or {}),
                question=spec.get("question", ""),
                value_labels=dict(spec.get("value_labels") or {}),
                asked_rate=float(spec.get("asked_rate", 1.0)),
            )
    return Schema(
        domain=raw["domain"],
        outcomes=list(raw["outcomes"] or []),
        fields=fields,
        labels=dict(raw.get("outcome_labels") or {}),
        sources=dict(raw.get("outcome_sources") or {}),
    )


def fit_ask_rates(records, schema):
    """How often each question returns an answer at all.

    Needed because the ranker was quietly assuming every question gets answered. On DDXPlus a
    record holds only the findings the patient reported, so asking about a rare symptom comes
    back empty about 97% of the time — and a ranking that ignores that spends its one question
    on whatever would be most decisive IF present, which is usually nothing."""
    n = max(1, len(records))
    seen = {name: 0 for name in schema.fields}
    for record in records:
        for name in record:
            if name in seen:
                seen[name] += 1
    return {name: hits / n for name, hits in seen.items()}


def fit_priors(records, schema, smoothing=1.0):
    """Count how often each value actually shows up. Laplace-smoothed so a value that never
    appears in the sample doesn't get written off as impossible."""
    counts = {name: {v: smoothing for v in spec.values} for name, spec in schema.fields.items()}
    for record in records:
        for name, value in record.items():
            if name not in counts:
                continue
            # multi-choice fields arrive as a list of the values the patient reported
            for v in (value if isinstance(value, list) else [value]):
                if v in counts[name]:
                    counts[name][v] += 1.0

    fitted = {}
    for name, tally in counts.items():
        total = sum(tally.values())
        fitted[name] = {v: c / total for v, c in tally.items()}
    return fitted
