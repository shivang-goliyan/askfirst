"""A scorer that is not a toy, so the refusal result is not an artefact of a weak one.

The naive Bayes gets 21% top-1 over 49 pathologies. That makes the risk-coverage curve look
spectacular and invites the obvious objection: of course filtering helps when the underlying
model is bad. The honest way to answer that is to put a real classifier behind the same curve and
see whether refusing still buys anything.

Multinomial logistic regression over one-hot evidence, trained with Adam. Same interface as
NaiveBayes — fit on patients, call with a record, get a distribution — so every existing script
picks it up without changes."""

import numpy as np


class SoftmaxScorer:
    def __init__(self, schema, l2=1e-4, seed=13):
        self.schema = schema
        self.l2 = l2
        self.rng = np.random.default_rng(seed)
        self.index = self._build_index(schema)
        self.outcomes = list(schema.outcomes)
        self.pos = {o: i for i, o in enumerate(self.outcomes)}
        self.W = None
        self.b = None

    @staticmethod
    def _build_index(schema):
        """One feature per binary field, one per value for everything else."""
        index, n = {}, 0
        for name, spec in schema.fields.items():
            if spec.kind == "binary":
                index[(name, None)] = n
                n += 1
            else:
                for value in spec.values:
                    index[(name, value)] = n
                    n += 1
        index["_n"] = n
        return index

    @property
    def width(self):
        return self.index["_n"]

    def encode(self, record):
        x = np.zeros(self.width, dtype=np.float32)
        for name, value in record.items():
            spec = self.schema.fields.get(name)
            if spec is None:
                continue
            if spec.kind == "binary":
                slot = self.index.get((name, None))
                if slot is not None and value not in (False, None, 0, "0"):
                    x[slot] = 1.0
            else:
                for v in (value if isinstance(value, list) else [value]):
                    slot = self.index.get((name, v))
                    if slot is not None:
                        x[slot] = 1.0
        return x

    def _matrix(self, patients):
        X = np.zeros((len(patients), self.width), dtype=np.float32)
        y = np.zeros(len(patients), dtype=np.int64)
        for i, p in enumerate(patients):
            X[i] = self.encode(p["evidences"])
            y[i] = self.pos.get(p["pathology"], 0)
        return X, y

    def fit(self, patients, epochs=400, lr=0.05, report=None):
        X, y = self._matrix(patients)
        n, d = X.shape
        k = len(self.outcomes)

        W = np.zeros((d, k), dtype=np.float32)
        b = np.zeros(k, dtype=np.float32)
        mW = np.zeros_like(W); vW = np.zeros_like(W)
        mb = np.zeros_like(b); vb = np.zeros_like(b)
        hot = np.zeros((n, k), dtype=np.float32)
        hot[np.arange(n), y] = 1.0

        for step in range(1, epochs + 1):
            z = X @ W + b
            z -= z.max(axis=1, keepdims=True)
            e = np.exp(z)
            p = e / e.sum(axis=1, keepdims=True)
            diff = (p - hot) / n

            gW = X.T @ diff + self.l2 * W
            gb = diff.sum(axis=0)

            for param, grad, m, v in ((W, gW, mW, vW), (b, gb, mb, vb)):
                m *= 0.9
                m += 0.1 * grad
                v *= 0.999
                v += 0.001 * grad * grad
                param -= lr * (m / (1 - 0.9 ** step)) / (np.sqrt(v / (1 - 0.999 ** step)) + 1e-8)

            if report and (step % report == 0 or step == 1):
                loss = -np.log(p[np.arange(n), y] + 1e-12).mean()
                acc = (p.argmax(axis=1) == y).mean()
                print(f"  epoch {step:>4}  loss {loss:.4f}  train acc {acc:.1%}", flush=True)

        self.W, self.b = W, b
        return self

    def __call__(self, record):
        if self.W is None:
            raise RuntimeError("Nothing fitted yet — call fit() first.")
        z = self.encode(record) @ self.W + self.b
        z -= z.max()
        e = np.exp(z)
        p = e / e.sum()
        return {o: float(p[i]) for i, o in enumerate(self.outcomes)}

    def save(self, path):
        """Weights are 972x49 float32 — about 190 KB, small enough to ship, which means the app
        can score a real case on CPU instead of only showing a baked curve."""
        np.savez_compressed(path, W=self.W, b=self.b, outcomes=np.array(self.outcomes, dtype=object))

    @classmethod
    def load(cls, path, schema):
        blob = np.load(path, allow_pickle=True)
        model = cls(schema)
        model.W, model.b = blob["W"], blob["b"]
        stored = list(blob["outcomes"])
        if stored != model.outcomes:
            # the weights were fitted against a different label order, so using them with this
            # schema would silently map every prediction to the wrong condition
            model.outcomes = stored
            model.pos = {o: i for i, o in enumerate(stored)}
        return model
