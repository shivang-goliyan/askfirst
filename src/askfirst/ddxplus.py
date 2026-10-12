"""DDXPlus patients, and a naive Bayes scorer over their evidences.

The scorer is here so the engine can be measured on real data before any GPU exists, and so
there is an honest baseline for the open model to beat later. It is not the product."""

import ast
import csv
import math
from collections import defaultdict

SKIP = {"age", "sex", "pathology"}


def _value_of(raw):
    if raw.startswith("V_"):
        return raw
    try:
        return int(raw)
    except ValueError:
        return raw


def parse_evidences(cell):
    """'E_7', 'E_54_@_V_180' and 'E_56_@_2' all turn up in the same list."""
    record = {}
    for item in ast.literal_eval(cell):
        if "_@_" in item:
            name, raw = item.split("_@_", 1)
            record.setdefault(name, []).append(_value_of(raw))
        else:
            record[item] = "present"
    return {k: (v[0] if isinstance(v, list) and len(v) == 1 else v) for k, v in record.items()}


def load_patients(path, limit=None):
    out = []
    with open(path, newline="") as fh:
        for i, row in enumerate(csv.DictReader(fh)):
            if limit is not None and i >= limit:
                break
            out.append({
                "age": int(row["AGE"]),
                "sex": row["SEX"],
                "pathology": row["PATHOLOGY"],
                "evidences": parse_evidences(row["EVIDENCES"]),
            })
    return out


class NaiveBayes:
    """P(pathology) times the product of P(field=value | pathology) over whatever the record
    actually holds. Dropping a field just drops its term, which is what makes it ablatable."""

    def __init__(self, smoothing=1.0):
        self.smoothing = smoothing
        self.prior = defaultdict(float)
        self.seen = defaultdict(float)
        self.joint = defaultdict(float)
        self.labels = []

    def fit(self, patients):
        for p in patients:
            label = p["pathology"]
            self.prior[label] += 1.0
            for name, value in p["evidences"].items():
                for v in (value if isinstance(value, list) else [value]):
                    self.joint[(label, name, v)] += 1.0
                    self.seen[(label, name)] += 1.0
        total = sum(self.prior.values())
        self.prior = {k: v / total for k, v in self.prior.items()}
        self.labels = sorted(self.prior)
        return self

    def _likelihood(self, label, name, value):
        hits = self.joint.get((label, name, value), 0.0) + self.smoothing
        total = self.seen.get((label, name), 0.0) + self.smoothing * 2.0
        return hits / total

    def __call__(self, record):
        scores = {}
        for label in self.labels:
            logp = math.log(max(self.prior[label], 1e-12))
            for name, value in record.items():
                if name in SKIP:
                    continue
                for v in (value if isinstance(value, list) else [value]):
                    logp += math.log(max(self._likelihood(label, name, v), 1e-12))
            scores[label] = logp

        top = max(scores.values())
        weights = {k: math.exp(v - top) for k, v in scores.items()}
        total = sum(weights.values())
        return {k: v / total for k, v in weights.items()}
