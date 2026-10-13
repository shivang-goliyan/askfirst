"""Numbers in the shop window have to agree with the artifact they came from.

Two headline claims have already drifted in this repo — one of them survived in four files after
being retracted in a fifth. These assertions are cheap and they close that off: if a measurement
is re-run and moves, the test fails and names the file that still has the old figure.

Only headline figures are covered. Asserting every number in every document would make the suite
fail for an honest rounding change, which trains people to ignore it."""

import json
import re
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
    """HTML comes back with its stylesheet removed. A colour like --hot:#ff9f45 contains "45",
    which is how this suite once passed a deck that quoted 38 where the artifact said 45."""
    out = {}
    for name in names:
        body = (ROOT / name).read_text()
        if name.endswith(".html"):
            body = re.sub(r"<style>.*?</style>", "", body, flags=re.S)
        out[name] = body
    return out


def quotes(body, figure):
    """The figure as a reader would see it, not as a substring of something else."""
    return re.search(rf"(?<![\d.]){re.escape(figure)}(?![\d.%])", body) is not None


def pct(x, places=1):
    return f"{x * 100:.{places}f}%"


def test_curve_figures_quoted_right():
    curve = load("curve.json")
    for level, where in (("1.0", SHOP), ("0.4", ("README.md", "docs/STATE.md")),
                         ("0.2", ("README.md", "docs/STATE.md"))):
        rows = curve["levels"][level]
        figure = pct(rows[-1]["accuracy"])
        for name, body in text(*where).items():
            assert quotes(body, figure), f"{name} is missing the answer-everything figure {figure} at {level}"


def test_advice_figures_quoted_right():
    """The arms we actually headline. "bits" is the marginal-prior version, kept in the
    experiment for comparison but no longer the one quoted — "truebits" is the objective as the
    literature states it, and that is what the claim is made against."""
    row = load("decision-value.json")["3"]
    for key in ("none", "random", "truebits", "likely"):
        figure = pct(row[key])
        hits = [n for n, b in text(*SHOP).items() if quotes(b, figure)]
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
        assert quotes(body, str(mixed["wrong"])), f"{name} has a stale wrong-answer count"
        assert quotes(body, f"{cal['completeness_error']:.3f}"), (
            f"{name} has a stale completeness error")
        # and the number it used to say, which must not survive anywhere
        assert not quotes(body, "38 wrong"), f"{name} still says 38 wrong"


def test_the_floor_and_ceiling_are_stated():
    from askfirst.calibrate import CEILING, FLOOR
    body = (ROOT / "docs/SAFETY.md").read_text()
    assert f"{FLOOR * 100:.0f}%" in body, "SAFETY.md does not say where the floor is"
    assert str(CEILING) in body, "SAFETY.md does not say where the ceiling is"


def test_cost_to_serve_quoted_right():
    """This one drifted quietly: four files said 58 ms and $0.0005 when the artifact had never
    held either number. Nothing caught it because the cost line had no assertion."""
    cost = load("cost-to-serve.json")
    usd = f"${cost['mean_usd_per_1000']:.4f}"
    ms = f"{cost['mean_cpu_ms']:.0f} ms"
    for name, body in text("README.md", "ui/deck.html", "docs/BUSINESS.md").items():
        assert quotes(body, usd), f"{name} does not quote the measured cost {usd}"
        assert ms in body, f"{name} does not quote the measured {ms} per assessment"
        assert "58 ms" not in body, f"{name} still quotes 58 ms, which was never measured"


def test_conformal_fold_tally_quoted_right():
    """The comparison this guards was rigged once already: the baselines were refitted on six
    missingness patterns and ours was not. These assertions pin the fair version."""
    conf = load("conformal.json")
    folds = conf["across_folds"]
    ours = folds["ours: isotonic in-group + the floor"]
    mondrian = folds["a threshold per group (Mondrian partition)"]
    body = text("README.md")["README.md"]
    assert quotes(body, f"{ours['folds_kept']} of {ours['folds']}"), (
        "README does not say how many folds our rule kept the promise in")
    assert quotes(body, pct(ours["worst_precision"])), "README lost our worst fold"
    assert quotes(body, pct(mondrian["worst_precision"])), "README lost the baseline's worst fold"
    for ghost in ("98.9%", "92.7% and stops"):
        assert ghost not in body, f"README still quotes the retracted figure {ghost!r}"


def test_the_missingness_grid_is_counted_honestly():
    """"holds in all 22" survived in five files. It was never in the artifact: the script only
    flags a cell broken when its interval excludes the target, which is not the same thing."""
    grid = load("missingness.json")["shipped"]
    cells = [c for levels in grid.values() for c in levels.values() if c and c.get("answered")]
    clear = sum(1 for c in cells if c["precision"] >= 0.95)
    for name, body in text("README.md", "docs/STATE.md", "ui/deck.html", "docs/SUBMISSION.md",
                           "docs/DECK.md").items():
        # emphasis and line breaks sit inside the phrase, so flatten before looking for it
        flat = re.sub(r"\s+", " ", re.sub(r"\*+|</?strong>|</?em>", "", body))
        assert re.search(rf"{clear} of (?:the |those )?{len(cells)}", flat), (
            f"{name} does not say {clear} of {len(cells)} cells clear the bar")
        assert "holds in all 22" not in body or "never supported" in body, (
            f"{name} still claims the rule holds in all 22 cells")


def test_portability_figures_quoted_right():
    """Three scorers is the answer to "it is just your model", so the count has to match the
    artifact — and the cell it fails has to stay in the shop window."""
    port = load("portability.json")
    tally = port["across_scorers_and_folds"]
    ours = tally["ours: isotonic in-group + the floor"]
    rival = tally["a threshold per group + the same floor"]
    body = text("README.md")["README.md"]
    flat = re.sub(r"\s+", " ", re.sub(r"\*+|</?strong>|</?em>", "", body))
    for row in (ours, rival):
        assert f"{row['cells_kept']} of {row['cells']}" in flat, (
            f"README does not say {row['cells_kept']} of {row['cells']}")
    assert quotes(body, pct(ours["worst_precision"])), "README lost our worst cell"
    sat = next(s["saturation"] for s in port["scorers"] if s["saturation"]["gap"] is not None)
    assert quotes(body, pct(sat["share"])), "README lost the share of saturated rows"
    assert quotes(body, pct(sat["thin"]["accuracy"])), "README lost the thin-record accuracy"


def test_the_floor_retraction_stays_retracted():
    """The floor was claimed to be what keeps the promise. Measured, the calibration alone keeps
    all seven folds and answers more. This pins the retraction, because the old sentence was
    comfortable and comfortable sentences come back."""
    arms = load("make-it-unnecessary.json")["arms"]
    shipped = arms["the shipped scorer, trained on complete records only"]
    folds = shipped["folds"]
    bare = [next(r for r in folds[h] if r["rule"] == "no floor at all") for h in folds]
    ridge = [next(r for r in folds[h] if r["rule"] == "the learned ridge") for h in folds]
    kept_bare = sum(1 for r in bare if r["keeps_promise"])
    cov_bare = sum(r["coverage"] for r in bare) / len(bare)
    cov_ridge = sum(r["coverage"] for r in ridge) / len(ridge)
    assert kept_bare == len(bare), (
        "no-floor no longer keeps every fold, so the retraction needs rewriting, not asserting")
    assert cov_bare > cov_ridge, "no-floor no longer answers more than the ridge"
    for name, body in text("README.md", "docs/results/2026-10-13-the-page-stops-asking.md").items():
        assert "you need both" not in body, f"{name} still says you need both pieces"
    source = (ROOT / "src/askfirst/calibrate.py").read_text()
    assert "the measurement says you need both:" not in source, (
        "calibrate.py's docstring still claims the measurement says you need both")


def test_the_real_queue_loss_stays_in_the_window():
    """A pre-registered loss is the most deletable thing in a repo. This makes deleting it fail
    the suite rather than tidy the README."""
    nh = load("nhamcs.json")
    body = text("README.md")["README.md"]
    assert nh["conditions_met"] < 4, (
        "the real-queue test now passes, so this guard needs rewriting rather than asserting")
    assert quotes(body, str(nh["missed_escalations"])), (
        "README does not say how many cleared visits needed a bed")
    assert quotes(body, f"{nh['auc']:.4f}"), "README lost the AUC"
    assert quotes(body, pct(nh["missed_share_of_cleared"])), "README lost the miss rate"
    for met in ("not met", "not deployable"):
        assert met in body.lower(), f"README no longer says {met!r}"
