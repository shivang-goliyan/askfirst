"""A third scorer, chosen because its confidence is shaped wrong in a different direction.

The softmax is underconfident when the record goes short — logits shrink as features drop out.
A naive Bayes is overconfident for the opposite reason: it multiplies dependent findings as
though they were independent, so agreement compounds. Both are smooth.

This one is neither. Vote among the most similar past patients and the confidence SATURATES: on
a thin record a handful of neighbours agree unanimously and the answer comes back at 1.00, with
nothing behind it. Roughly a fifth of thin records land exactly on 1.0, which is the interesting
part — a single global threshold cannot separate anything inside that pile, because to a
threshold those records are identical. The record is not identical, and a rule that reads the
record can still tell them apart.

That is the whole reason this file exists: it is the scorer the afternoon version of this
product cannot cope with."""

import numpy as np


class NeighbourScorer:
    """Similarity-weighted vote over the k nearest past patients, cosine on one-hot findings.

    Takes the encoder as an argument rather than owning one, so all three scorers in the
    portability measurement see exactly the same features and only the inductive bias differs."""

    def __init__(self, encode, outcomes, k=50):
        self.encode = encode
        self.outcomes = list(outcomes)
        self.k = k
        self.X = None
        self.y = None

    def fit(self, patients):
        pos = {o: i for i, o in enumerate(self.outcomes)}
        rows = np.stack([self.encode(p["evidences"]) for p in patients]).astype(np.float32)
        # unit rows up front, so a query is one matmul instead of n divisions
        norms = np.linalg.norm(rows, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self.X = rows / norms
        self.y = np.array([pos.get(p["pathology"], 0) for p in patients], dtype=np.int64)
        return self

    def __call__(self, record):
        flat = {o: 0.0 for o in self.outcomes}
        if self.X is None:
            raise RuntimeError("Nothing fitted yet — call fit() first.")
        q = self.encode(record)
        n = np.linalg.norm(q)
        if n == 0:
            # an empty record is similar to everyone; fall back to the training prior
            counts = np.bincount(self.y, minlength=len(self.outcomes)).astype(np.float64)
            counts /= counts.sum()
            return {o: float(counts[i]) for i, o in enumerate(self.outcomes)}

        sims = self.X @ (q / n)
        near = np.argpartition(-sims, min(self.k, len(sims) - 1))[:self.k]
        weights = np.clip(sims[near], 0.0, None)
        if weights.sum() <= 0:
            weights = np.ones_like(weights)
        tally = np.bincount(self.y[near], weights=weights, minlength=len(self.outcomes))
        tally /= tally.sum()
        for i, o in enumerate(self.outcomes):
            flat[o] = float(tally[i])
        return flat
