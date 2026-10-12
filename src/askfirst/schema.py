from dataclasses import dataclass
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


@dataclass
class Schema:
    domain: str
    outcomes: list
    fields: dict

    def values_for(self, name):
        return self.fields[name].values

    def missing_from(self, record):
        return [f for f in self.fields if f not in record]

    def present_in(self, record):
        return [f for f in record if f in self.fields]


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
            )
    return Schema(domain=raw["domain"], outcomes=list(raw["outcomes"]), fields=fields)
