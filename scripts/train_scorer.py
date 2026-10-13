"""Fit the scorer once and keep it, so no measurement has to retrain and none of them disagree.

    python3 scripts/train_scorer.py data/ddxplus/release_validate_patients

Why this exists at all: the first version of every measurement here used a naive Bayes, which
scores 22.7% top-1 on held-out DDXPlus. That made refusing look spectacular for the wrong reason.
A plain softmax regression on the same features gets 99.6%, which means the dataset was never the
hard part and the earlier headline was a statement about the baseline. Fitting a real scorer and
keeping it is how that stops happening twice.

**It is now fitted on records with holes in them**, and that came out of an experiment meant to
make this whole product unnecessary (`docs/results/2026-10-13-we-tried-to-delete-our-own-floor.md`).
Fitting on complete records and then asking about thin ones is a mismatch we created: a deleted
finding arrives looking exactly like one that was asked about and denied. Two masked copies of
each patient fix it, and the measurement is one-sided:

    held-out top-1          complete   60%     40%     20%     10%
    complete records only      99.6%  95.9%   83.0%   40.2%   18.0%
    with masked copies         99.6%  97.7%   93.6%   73.3%   44.2%

Nothing is given up on a complete record and a fifth of a record gains thirty-three points.

The masking is **uniform at random**, deliberately, even though the seven realistic patterns in
`missing.py` make a slightly better model on the worst of those patterns (0.448 against 0.419 at
a fifth of a record). Two reasons. A scorer that has seen all seven patterns makes every
leave-one-pattern-out experiment in this repo weaker, because the pattern the post-processors are
asked to generalise to is one the scorer was trained on. And training on the patterns costs a
tenth of a point on complete records, where uniform masking costs nothing at all."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from askfirst.ablation import argmax  # noqa: E402
from askfirst.ddxplus import NaiveBayes, load_patients  # noqa: E402
from askfirst.missing import augment, cut, mechanisms  # noqa: E402
from askfirst.schema import load_schema  # noqa: E402
from askfirst.softmax import SoftmaxScorer  # noqa: E402

OUT = Path("src/askfirst/baked/ddxplus_softmax.npz")
TRAIN = 30000
TEST = 6000
COPIES = 2        # masked copies of each training patient
LEVELS = (1.0, 0.6, 0.4, 0.2, 0.1)


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

    # uniform at random on purpose — see the note at the top of this file
    uniform = {"at random": mechanisms(schema)["at random"]}
    rows = train + augment(train, uniform, copies=COPIES)
    print(f"{len(rows)} training rows: each patient once whole and {COPIES} times with holes in "
          f"it, cut uniformly at random")

    started = time.time()
    model = SoftmaxScorer(schema).fit(rows, epochs=400, lr=0.05)
    print(f"fitted in {time.time() - started:.0f}s on CPU, {model.width} features")

    nb = NaiveBayes().fit(train)
    plain = SoftmaxScorer(schema).fit(train, epochs=400, lr=0.05)
    print()
    print(f"{'scorer':24} {'top-1':>8} {'top-3':>8}")
    print(f"{'naive bayes':24} {accuracy(nb, held):>7.1%} {accuracy(nb, held, 3):>8.1%}")
    print(f"{'softmax, whole records':24} {accuracy(plain, held):>7.1%} "
          f"{accuracy(plain, held, 3):>8.1%}")
    print(f"{'softmax, with holes':24} {accuracy(model, held):>7.1%} "
          f"{accuracy(model, held, 3):>8.1%}")

    # and the part that is the whole reason for the change
    print(f"\n{'top-1 as the record thins':24} " + " ".join(f"{f:>7.0%}" for f in LEVELS))
    for name, m in (("whole records only", plain), ("fitted with holes", model)):
        row = []
        for frac in LEVELS:
            data = held if frac == 1.0 else [
                {"evidences": c["evidences"], "pathology": c["pathology"]}
                for c in cut(held, frac, mechanisms(schema)["at random"])]
            row.append(accuracy(m, data))
        print(f"{name:24} " + " ".join(f"{a:>7.1%}" for a in row))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    model.save(OUT)
    print(f"\nwrote {OUT} ({OUT.stat().st_size / 1024:.0f} KB)")
    print("The gap between those rows is why every number here was re-measured, twice.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/ddxplus/release_validate_patients")
