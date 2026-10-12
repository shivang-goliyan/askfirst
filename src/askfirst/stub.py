"""A hand-written scorer so the engine can be developed and tested with no model and no GPU.
Swap it for the vLLM client and nothing above it changes."""

WEIGHTS = {
    ("troponin", "very_raised"): {"escalate": 4.0},
    ("troponin", "raised"): {"admit": 3.0},
    ("troponin", "normal"): {"discharge": 1.2, "observe": 0.8},
    ("ecg", "ischaemic"): {"escalate": 3.0},
    ("ecg", "arrhythmia"): {"admit": 2.0},
    ("ecg", "normal"): {"discharge": 0.8},
    ("ct_chest", "pe"): {"escalate": 4.0},
    ("ct_chest", "dissection"): {"escalate": 5.0},
    ("d_dimer", "raised"): {"observe": 1.5, "admit": 0.5},
    ("heart_rate", "high"): {"observe": 1.0},
    ("spo2", "low"): {"admit": 1.5},
    ("temperature", "fever"): {"observe": 1.0},
    ("prior_mi", True): {"admit": 1.0},
}


def softmax(scores):
    top = max(scores.values())
    exp = {k: pow(2.718281828, v - top) for k, v in scores.items()}
    total = sum(exp.values())
    return {k: v / total for k, v in exp.items()}


def make_scorer(schema):
    def score(record):
        scores = {o: 0.35 for o in schema.outcomes}
        for name, value in record.items():
            for outcome, w in WEIGHTS.get((name, value), {}).items():
                scores[outcome] = scores.get(outcome, 0.0) + w
        return softmax(scores)

    return score
