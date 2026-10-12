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

    def label_for(self, value):
        return self.value_labels.get(value, str(value))


@dataclass
class Schema:
    domain: str
    outcomes: list
    fields: dict
    labels: dict = dc_field(default_factory=dict)

    def label_for_outcome(self, outcome):
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

    def with_priors(self, fitted):
        fields = {}
        for name, spec in self.fields.items():
            fields[name] = Field(
                spec.name, spec.kind, spec.values, spec.cost, spec.delay,
                dict(fitted.get(name) or spec.priors), spec.question, spec.value_labels,
            )
        return Schema(self.domain, self.outcomes, fields, self.labels)


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
            )
    return Schema(
        domain=raw["domain"],
        outcomes=list(raw["outcomes"] or []),
        fields=fields,
        labels=dict(raw.get("outcome_labels") or {}),
    )


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
