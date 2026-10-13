"""Turn a confidence into a probability that means what it says, and work out how much of the
record is missing without being told.

The scorer's margin is a good ranking signal and a bad number. Measured on held-out records it
is honest when the record is complete and underconfident by forty points when half of it is
gone — a linear model's logits shrink as features drop out, so the margin collapses while the
answer stays right. That matters more here than it usually would, because the refusal threshold
*is* that number: a cut-off chosen on complete records delivers 76% on a fifth of a record.

Two pieces, and the measurement says you need both:

`Calibrator` maps (margin, findings in hand) to P(the answer is right). Findings in hand, not
completeness — nobody deploying this knows a record is 40% complete, but everyone knows how many
things are written on it.

`Completeness` estimates what fraction of the record is present, by predicting how many findings
this patient would have had. Within 0.08 on held-out data, which is enough to refuse outright
below a floor — and below that floor no threshold reaches a useful precision anyway."""

import bisect
import json
from pathlib import Path

import numpy as np

BUCKETS = ((1, 2), (3, 4), (5, 7), (8, 11), (12, 99))
FLOOR = 0.35      # estimated completeness below which it hands over whatever the confidence says


def isotonic(xs, ys):
    """Pool-adjacent-violators. Returns the (x, y) knots of the monotone fit of ys on sorted xs.

    Monotone rather than a fitted curve on purpose: nobody has a theory about the shape of this
    mapping, and a two-parameter logistic forced through it was visibly wrong at both ends.

    Equal x values are averaged before the pooling starts. Without that they become separate
    blocks sitting at the same place on the axis, and a lookup at that x picks whichever one it
    reaches first — which is how a calibrator that had seen nine right answers out of ten came
    back with nought."""
    tally = {}
    for x, y in zip(xs, ys):
        total, n = tally.get(x, (0.0, 0.0))
        tally[x] = (total + y, n + 1.0)

    stack = []
    for x in sorted(tally):
        total, n = tally[x]
        stack.append([x, total / n, n])
        while len(stack) > 1 and stack[-2][1] > stack[-1][1]:
            top, under = stack.pop(), stack.pop()
            n = under[2] + top[2]
            stack.append([top[0], (under[1] * under[2] + top[1] * top[2]) / n, n])
    return [(x, y) for x, y, _ in stack]


def bucket_of(n):
    for lo, hi in BUCKETS:
        if lo <= n <= hi:
            return f"{lo}-{hi}"
    return f"{BUCKETS[0][0]}-{BUCKETS[0][1]}"


class Calibrator:
    """P(the answer is right | this margin, this many findings)."""

    def __init__(self, knots=None):
        self.knots = knots or {}

    def fit(self, samples):
        """samples: (margin, findings in hand, was it right)."""
        grouped = {}
        for margin, n, right in samples:
            grouped.setdefault(bucket_of(n), []).append((margin, 1.0 if right else 0.0))
        self.knots = {}
        for key, rows in grouped.items():
            rows.sort()
            self.knots[key] = isotonic([r[0] for r in rows], [r[1] for r in rows])
        return self

    def __call__(self, margin, findings):
        knots = self.knots.get(bucket_of(findings))
        if not knots:
            return margin
        xs = [k[0] for k in knots]
        i = bisect.bisect_left(xs, margin)
        if i == 0:
            return knots[0][1]
        if i >= len(knots):
            return knots[-1][1]
        (x0, y0), (x1, y1) = knots[i - 1], knots[i]
        return y1 if x1 == x0 else y0 + (y1 - y0) * (margin - x0) / (x1 - x0)

    def thin(self, keep=200):
        """An isotonic fit leaves a knot almost everywhere. Keep an evenly spaced subset so the
        shipped file is small; the curve is monotone, so what is lost is in the third decimal."""
        out = {}
        for key, knots in self.knots.items():
            if len(knots) <= keep:
                out[key] = knots
                continue
            step = len(knots) / keep
            picked = [knots[min(len(knots) - 1, int(i * step))] for i in range(keep)]
            if picked[-1] != knots[-1]:
                picked.append(knots[-1])
            out[key] = picked
        return Calibrator(out)

    def save(self, path):
        Path(path).write_text(json.dumps({
            "note": "P(correct) given the scorer's margin and how many findings are in hand",
            "buckets": {k: [[round(x, 6), round(y, 6)] for x, y in v]
                        for k, v in self.knots.items()},
        }))

    @classmethod
    def load(cls, path):
        blob = json.loads(Path(path).read_text())
        return cls({k: [tuple(p) for p in v] for k, v in blob["buckets"].items()})


class Completeness:
    """How much of the record is here? Ridge regression from the record to the number of
    findings this patient would have had, which is a property of the illness rather than of the
    intake — so it is learnable from the findings that did arrive."""

    def __init__(self, encode, weights=None):
        self.encode = encode
        self.w = weights

    def _row(self, record):
        x = self.encode(record)
        return np.concatenate([x, [len(record), 1.0]]).astype(np.float32)

    def fit(self, pairs, l2=1.0):
        """pairs: (record as it arrived, how many findings the patient really had)."""
        X = np.stack([self._row(r) for r, _ in pairs])
        y = np.array([n for _, n in pairs], dtype=np.float32)
        self.w = np.linalg.solve(X.T @ X + l2 * np.eye(X.shape[1], dtype=np.float32), X.T @ y)
        return self

    def __call__(self, record):
        if self.w is None or not record:
            return 1.0 if record else 0.0
        expected = float(self._row(record) @ self.w)
        return min(1.0, len(record) / max(expected, len(record), 1.0))

    def save(self, path):
        np.savez_compressed(path, w=self.w)

    @classmethod
    def load(cls, path, encode):
        return cls(encode, np.load(path)["w"])
