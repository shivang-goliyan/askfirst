"""Fit the scorer once and keep it, so no measurement has to retrain and none of them disagree.

    python3 scripts/train_scorer.py data/ddxplus/release_validate_patients

Why this exists at all: the first version of every measurement here used a naive Bayes, which
scores 22.7% top-1 on held-out DDXPlus. That made refusing look spectacular for the wrong reason.
A plain softmax regression on the same features gets 99.6%, which means the dataset was never the
hard part and the earlier headline was a statement about the baseline. Fitting a real scorer and
keeping it is how that stops happening twice."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from askfirst.ablation import argmax  # noqa: E402
from askfirst.ddxplus import NaiveBayes, load_patients  # noqa: E402
from askfirst.schema import load_schema  # noqa: E402
from askfirst.softmax import SoftmaxScorer  # noqa: E402

OUT = Path("src/askfirst/baked/ddxplus_softmax.npz")
TRAIN = 30000
TEST = 6000


def accuracy(scorer, data, k=1):
    hit = 0
    for p in data:
        dist = scorer(p["evidences"])
        top = [o for o, _ in sorted(dist.items(), key=lambda kv: -kv[1])[:k]]
        hit += p["pathology"] in top
    return hit / len(data)


def main(path):
    schema = load_schema("ddxplus")
    patients = [p for p in load_patients(path, limit=TRAIN + TEST + 4000) if p["evidences"]]
    train, held = patients[:TRAIN], patients[TRAIN:TRAIN + TEST]
    print(f"{len(train)} train, {len(held)} held out, {len(schema.outcomes)} conditions")

    started = time.time()
    model = SoftmaxScorer(schema).fit(train, epochs=400, lr=0.05)
    print(f"fitted in {time.time() - started:.0f}s on CPU, {model.width} features")

    nb = NaiveBayes().fit(train)
    print()
    print(f"{'scorer':14} {'top-1':>8} {'top-3':>8}")
    print(f"{'naive bayes':14} {accuracy(nb, held):>7.1%} {accuracy(nb, held, 3):>8.1%}")
    print(f"{'softmax':14} {accuracy(model, held):>7.1%} {accuracy(model, held, 3):>8.1%}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    model.save(OUT)
    print(f"\nwrote {OUT} ({OUT.stat().st_size / 1024:.0f} KB)")
    print("The gap between those two rows is why every number here was re-measured.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/ddxplus/release_validate_patients")
