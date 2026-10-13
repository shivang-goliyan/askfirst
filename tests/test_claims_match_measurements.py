"""Numbers in the shop window have to agree with the artifact they came from.

Two headline claims have already drifted in this repo — one of them survived in four files after
being retracted in a fifth. These assertions are cheap and they close that off: if a measurement
is re-run and moves, the test fails and names the file that still has the old figure.

Only headline figures are covered. Asserting every number in every document would make the suite
fail for an honest rounding change, which trains people to ignore it."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

ROOT = Path(__file__).parent.parent
SHOP = ("README.md", "docs/STATE.md", "ui/deck.html", "docs/SUBMISSION.md")


def load(name):
    for base in ("src/askfirst/baked", "docs/results"):
        path = ROOT / base / name
        if path.exists():
            return json.loads(path.read_text())
    raise FileNotFoundError(name)


def text(*names):
    return {n: (ROOT / n).read_text() for n in names}


def pct(x, places=1):
    return f"{x * 100:.{places}f}%"


def test_curve_figures_quoted_right():
    curve = load("curve.json")
    for level, where in (("1.0", SHOP), ("0.4", ("README.md", "docs/STATE.md")),
                         ("0.2", ("README.md", "docs/STATE.md"))):
        rows = curve["levels"][level]
        figure = pct(rows[-1]["accuracy"])
        for name, body in text(*where).items():
            assert figure in body, f"{name} is missing the answer-everything figure {figure} at {level}"


def test_advice_figures_quoted_right():
    """The arms we actually headline. "bits" is the marginal-prior version, kept in the
    experiment for comparison but no longer the one quoted — "truebits" is the objective as the
    literature states it, and that is what the claim is made against."""
    row = load("decision-value.json")["3"]
    for key in ("none", "random", "truebits", "likely"):
        figure = pct(row[key])
        hits = [n for n, b in text(*SHOP).items() if figure in b]
        assert hits, f"nothing in the shop window quotes {key} = {figure}"


def test_dead_headline_stays_dead():
    """21.0% -> 85.3% and "94% cheaper" came from a scorer that was retired on 13 Oct."""
    for name, body in text(*SHOP).items():
        for ghost in ("94% cheaper", "85.3% by refusing"):
            if ghost in body:
                assert "killed" in body or "retract" in body or "wrong" in body, (
                    f"{name} still quotes {ghost!r} without saying it was retracted")


def test_variant_counts_quoted_right():
    ablation = load("variant-ablation.json")
    sweep = {row["level"]: row["changed"] for row in ablation["sweep"]}
    n = ablation["scoreable"]
    blocked = ablation["contested"] - n
    for name, body in text("docs/STATE.md", "ui/deck.html").items():
        assert f"{sweep['E']} of {n}" in body, f"{name} lost the supporting-strength count"
        assert f"{sweep['B']} of {n}" in body, f"{name} lost the clinical-strength count"
        assert f"{blocked} of {ablation['contested']}" in body, f"{name} lost the blocked count"


def test_value_figures_quoted_right():
    value = load("value.json")
    at95 = next(p for p in value["promises"] if p["target"] == 0.95)
    for name, body in text("README.md", "docs/STATE.md", "ui/deck.html").items():
        assert f"{at95['wrong_per_1000']:.1f}" in body, f"{name} lost the wrong-per-1000 figure"
        assert pct(at95["coverage"]) in body or pct(at95["coverage"], 0) in body, (
            f"{name} lost the share of the queue it takes")


def test_calibration_figures_quoted_right():
    """The one that got away: the calibrator was refitted on seven missingness patterns and
    seven prose files kept the figures from before the refit."""
    cal = load("calibration.json")
    mixed = cal["mixed_stream"]
    for name, body in text("README.md", "docs/STATE.md", "ui/deck.html",
                           "docs/SUBMISSION.md", "docs/DECK.md").items():
        assert str(mixed["wrong"]) in body, f"{name} has a stale wrong-answer count"
        assert f"{cal['completeness_error']:.3f}" in body, (
            f"{name} has a stale completeness error")


def test_the_floor_and_ceiling_are_stated():
    from askfirst.calibrate import CEILING, FLOOR
    body = (ROOT / "docs/SAFETY.md").read_text()
    assert f"{FLOOR * 100:.0f}%" in body, "SAFETY.md does not say where the floor is"
    assert str(CEILING) in body, "SAFETY.md does not say where the ceiling is"
