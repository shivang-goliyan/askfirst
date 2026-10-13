"""The gate, asked for directly by somebody else's model.

`/api/gate` is the surface that makes this a layer rather than a model with a page attached, so
the things it must never do are worth pinning: borrow a calibration across scorers, print a
certainty, or let a record through that could not have come from a patient."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastapi.testclient import TestClient  # noqa: E402

from askfirst.api import app  # noqa: E402
from askfirst.calibrate import CEILING  # noqa: E402

client = TestClient(app)
DECENT = {f"E_{i}": True for i in (55, 54, 57, 133, 152, 204, 56, 60, 61, 62, 77, 88)}


def ask(**body):
    body.setdefault("record", DECENT)
    body.setdefault("scorer", "softmax")
    r = client.post("/api/gate", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def test_unknown_scorer_promises_nothing():
    d = ask(confidence=0.999, scorer="some-vendors-model")
    assert d["answering"] is False
    assert d["precision_promise"]["available"] is False
    assert d["precision_promise"]["chance_right"] is None
    assert d["precision_promise"]["how_to_fit"]["script"] == "scripts/fit_gate.py"


def test_record_checks_need_no_fit():
    """The half that transfers for free still has to run for a scorer we know nothing about."""
    d = ask(confidence=0.999, scorer="some-vendors-model")
    assert d["record_level"]["completeness"] is not None
    assert d["record_level"]["could_be_a_patient"] is True
    assert d["go_get"], "a refusal with no advice is half a product"


def test_thin_record_refused_outright():
    d = ask(record={"E_55": True, "E_54": "V_10"}, confidence=1.0)
    assert d["answering"] is False
    assert d["record_level"]["enough_record"] is False


def test_impossible_record_refused():
    d = ask(record={f"E_{i}": True for i in range(1, CEILING + 20)}, confidence=0.96)
    assert d["answering"] is False
    assert d["record_level"]["could_be_a_patient"] is False


def test_refusal_quotes_no_odds():
    """Asked about a record the floor already rejected, an isotonic fit answers 1.0. Nothing may
    report that, least of all beside a refusal."""
    for body in ({"record": {"E_55": True}, "confidence": 1.0},
                 {"record": {f"E_{i}": True for i in range(1, CEILING + 20)}, "confidence": 1.0}):
        d = ask(**body)
        assert d["precision_promise"]["chance_right"] is None
        assert "100%" not in d["why"]


def test_never_claims_certainty():
    d = ask(confidence=1.0)
    assert "100%" not in d["why"]


def test_distribution_becomes_confidence():
    d = ask(distribution={"a": 0.7, "b": 0.2, "c": 0.1})
    flat = ask(confidence=0.7)
    assert d["precision_promise"]["chance_right"] == flat["precision_promise"]["chance_right"]


def test_no_number_is_rejected():
    r = client.post("/api/gate", json={"record": DECENT, "scorer": "softmax"})
    assert r.status_code == 422


def test_fitted_scorer_uses_its_own():
    """A calibration fitted to another model must be the one that answers for it, and its
    completeness estimate must be that operator's rather than ours."""
    theirs = ask(confidence=0.9, scorer="example-bayes")
    ours = ask(confidence=0.9, scorer="softmax")
    assert theirs["precision_promise"]["available"] is True
    assert theirs["record_level"]["estimated_by"] == "example-bayes"
    assert ours["record_level"]["estimated_by"] == "shipped"
    assert theirs["record_level"]["completeness"] != ours["record_level"]["completeness"]


def test_readme_contrast_still_holds():
    """The README prints two numbers off this endpoint to make its central argument. If a
    refitted calibrator moves them, the README is wrong and this is how we find out."""
    readme = (Path(__file__).parent.parent / "README.md").read_text()
    for scorer in ("softmax", "example-bayes"):
        chance = ask(confidence=0.5, scorer=scorer)["precision_promise"]["chance_right"]
        assert f"{chance * 100:.1f}%" in readme, (
            f"README does not quote {chance * 100:.1f}% for {scorer} at confidence 0.5")
