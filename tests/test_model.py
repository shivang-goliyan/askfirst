"""Tests the vLLM response parsing against a mock built to the documented shape.

The point is to find out whether _label_logprob picks the right tokens BEFORE spending GPU
hours on it. A wrong boundary gives a plausible-looking distribution that is quietly garbage,
which is the worst kind of bug to carry onto rented hardware."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from askfirst.model import Endpoint, ModelScorer
from askfirst.schema import load_schema


class FakeLogprobs:
    def __init__(self, tokens, token_logprobs, text_offset):
        self.tokens = tokens
        self.token_logprobs = token_logprobs
        self.text_offset = text_offset


class FakeChoice:
    def __init__(self, index, logprobs):
        self.index = index
        self.logprobs = logprobs


class FakeReply:
    def __init__(self, choices):
        self.choices = choices


class FakeCompletions:
    """Tokenises on whitespace and hands back the shape vLLM documents, assigning each prompt
    the logprob the test asked for on its label tokens."""

    def __init__(self, per_label):
        self.per_label = per_label
        self.calls = []

    def create(self, model, prompt, echo, logprobs, max_tokens, temperature):
        self.calls.append({"echo": echo, "max_tokens": max_tokens, "n": len(prompt)})
        out = []
        for i, text in enumerate(prompt):
            tokens, offsets, offset = [], [], 0
            for piece in text.split(" "):
                tokens.append(piece + " ")
                offsets.append(offset)
                offset += len(piece) + 1
            label = next(k for k in self.per_label if text.endswith(k))
            boundary = len(text) - len(label)
            values = [None] + [
                (self.per_label[label] if off >= boundary else -3.0)
                for off in offsets[1:]
            ]
            out.append(FakeChoice(i, FakeLogprobs(tokens, values, offsets)))
        return FakeReply(out)


class FakeClient:
    def __init__(self, per_label):
        self.completions = FakeCompletions(per_label)


def scorer_with(per_label, outcomes):
    schema = load_schema("clinical")
    schema.outcomes = outcomes
    endpoint = Endpoint(base_url="http://fake/v1", model="fake-model")
    endpoint._client = FakeClient(per_label)
    return ModelScorer(schema, endpoint), schema


def test_recovers_intended_ranking():
    s, _ = scorer_with({"admit": -0.1, "discharge": -5.0}, ["admit", "discharge"])
    dist = s({"heart_rate": "high"})
    assert dist["admit"] > dist["discharge"]


def test_distribution_normalises():
    s, _ = scorer_with({"admit": -0.5, "discharge": -1.0, "observe": -2.0},
                       ["admit", "discharge", "observe"])
    dist = s({"heart_rate": "high"})
    assert abs(sum(dist.values()) - 1.0) < 1e-9


def test_one_request_for_all_labels():
    s, _ = scorer_with({"admit": -0.5, "discharge": -1.0, "observe": -2.0},
                       ["admit", "discharge", "observe"])
    s({"heart_rate": "high"})
    calls = s.endpoint._client.completions.calls
    assert len(calls) == 1 and calls[0]["n"] == 3


def test_sends_echo_and_zero_tokens():
    s, _ = scorer_with({"admit": -0.5, "discharge": -1.0}, ["admit", "discharge"])
    s({})
    call = s.endpoint._client.completions.calls[0]
    assert call["echo"] is True and call["max_tokens"] == 0


def test_long_label_not_penalised():
    """A long name and a short one with the same per-token logprob must score the same,
    or the scorer is measuring name length."""
    s, _ = scorer_with({"admit": -1.0, "a very long condition name": -1.0},
                       ["admit", "a very long condition name"])
    dist = s({})
    assert abs(dist["admit"] - dist["a very long condition name"]) < 1e-6


def test_refuses_without_logprobs():
    schema = load_schema("clinical")
    schema.outcomes = ["admit"]
    endpoint = Endpoint(base_url="http://fake/v1", model="m")

    class Bare:
        completions = type("C", (), {"create": staticmethod(
            lambda **k: FakeReply([FakeChoice(0, None)]))})()

    endpoint._client = Bare()
    try:
        ModelScorer(schema, endpoint)({})
    except RuntimeError as e:
        assert "echo" in str(e)
    else:
        raise AssertionError("should have refused")
