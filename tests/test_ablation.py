import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from askfirst.ablation import (
    by_cost_effectiveness,
    rank_gaps,
    sensitivity_map,
    sufficiency,
    total_variation,
)
from askfirst.metrics import topk_recovery
from askfirst.schema import load_schema
from askfirst.stub import make_scorer

CASE = {"heart_rate": "high", "smoker": True}


def test_loads_both_schemas():
    assert load_schema("clinical").domain == "clinical"
    assert load_schema("variant").domain == "variant"


def test_unknown_schema_explains():
    try:
        load_schema("nonsense")
    except FileNotFoundError as e:
        assert "clinical" in str(e)
    else:
        raise AssertionError("should have complained")


def test_distance_bounds():
    assert total_variation({"a": 1.0}, {"a": 1.0}) == 0.0
    assert total_variation({"a": 1.0}, {"b": 1.0}) == 1.0


def test_gaps_are_ranked():
    schema = load_schema("clinical")
    gaps = rank_gaps(CASE, make_scorer(schema), schema)
    assert gaps
    assert gaps[0].flip_prob >= gaps[-1].flip_prob


def test_troponin_ranks_high():
    schema = load_schema("clinical")
    names = [g.field for g in rank_gaps(CASE, make_scorer(schema), schema)]
    assert topk_recovery(names, "troponin", 3)


def test_sufficiency_in_range():
    schema = load_schema("clinical")
    assert 0.0 <= sufficiency(CASE, make_scorer(schema), schema) <= 100.0


def test_present_fields_have_influence():
    schema = load_schema("clinical")
    infl = sensitivity_map(CASE, make_scorer(schema), schema)
    assert [i.field for i in infl] and all(i.shift >= 0 for i in infl)


def test_priors_normalise():
    schema = load_schema("clinical")
    weights = schema.priors_for("troponin")
    assert abs(sum(weights.values()) - 1.0) < 1e-9
    assert weights["normal"] > weights["very_raised"]


def test_uniform_when_undeclared():
    schema = load_schema("variant")
    weights = schema.priors_for("PM2")
    assert set(weights.values()) == {0.5}


def test_flip_prob_is_not_lumpy():
    schema = load_schema("clinical")
    gaps = rank_gaps(CASE, make_scorer(schema), schema)
    probs = {round(g.flip_prob, 4) for g in gaps}
    assert len(probs) > 2


def test_flip_prob_is_a_probability():
    schema = load_schema("clinical")
    for gap in rank_gaps(CASE, make_scorer(schema), schema):
        assert 0.0 <= gap.flip_prob <= 1.0
        assert abs(sum(o.prior for o in gap.by_value) - 1.0) < 1e-9


def test_fitted_priors_follow_data():
    from askfirst.schema import fit_priors
    schema = load_schema("clinical")
    sample = [{"troponin": "raised"} for _ in range(50)]
    tuned = schema.with_priors(fit_priors(sample, schema))
    assert tuned.priors_for("troponin")["raised"] > 0.8


def test_most_telling_picks_likeliest():
    schema = load_schema("clinical")
    gaps = {g.field: g for g in rank_gaps(CASE, make_scorer(schema), schema)}
    tell = gaps["troponin"].most_telling()
    assert tell is not None and tell.flips


def test_cheap_and_useless_drops_out():
    schema = load_schema("clinical")
    gaps = rank_gaps(CASE, make_scorer(schema), schema)
    ranked = by_cost_effectiveness(gaps)
    best = max(g.info_gain for g in gaps)
    assert all(g.info_gain >= 0.25 * best for g in ranked)
    free_but_weak = [g for g in gaps if g.cost == 0 and g.info_gain < 0.25 * best]
    assert free_but_weak, "clinical schema should have a free low-information field"
    assert all(g.value_per_cost() == 0.0 for g in free_but_weak)


def test_scales_read_as_scales():
    field = load_schema("ddxplus").fields["E_59"]
    assert field.is_scale()
    assert field.label_for(5) == "5 of 10"


def test_categories_are_not_scales():
    schema = load_schema("clinical")
    assert not schema.fields["heart_rate"].is_scale()
    assert schema.fields["heart_rate"].label_for("high") == "high"


def test_weak_scores_say_nothing():
    from askfirst.civic import computational_line
    assert computational_line(0.4, threshold=2.0) is None
    assert computational_line(-0.4, threshold=2.0) is None


def test_line_picks_a_direction():
    from askfirst.civic import DAMAGING, TOLERATED, computational_line
    assert computational_line(-5.0)["significance"] == DAMAGING
    assert computational_line(5.0)["significance"] == TOLERATED
    assert computational_line(-5.0, level="B")["evidence_level"] == "B"


def test_rating_ignores_magnitude():
    from askfirst.civic import computational_line
    mild, wild = computational_line(-2.1), computational_line(-11.8)
    assert mild["rating"] == wild["rating"]


def test_breadth_decides_the_order():
    from askfirst.ablation import answer_breadth
    schema = load_schema("clinical")
    gaps = rank_gaps(CASE, make_scorer(schema), schema)
    assert [g.breadth for g in gaps] == sorted((g.breadth for g in gaps), reverse=True)
    assert answer_breadth(schema.fields["heart_rate"]) > answer_breadth(schema.fields["smoker"])


def test_no_answer_is_not_yes():
    """A negative answer must not switch the feature on, or asking is always worth it."""
    from askfirst.softmax import SoftmaxScorer
    schema = load_schema("ddxplus")
    model = SoftmaxScorer.load("src/askfirst/baked/ddxplus_softmax.npz", schema)
    base = {"E_55": "present"}
    assert model({**base, "E_103": "absent"}) == model(base)
    assert model({**base, "E_103": "present"}) != model(base)


def test_rare_questions_count_less():
    from askfirst.schema import fit_ask_rates
    schema = load_schema("clinical")
    sample = [{"troponin": "raised"} for _ in range(9)] + [{"ecg": "normal"}]
    rates = fit_ask_rates(sample, schema)
    assert rates["troponin"] == 0.9 and rates["ecg"] == 0.1
    tuned = schema.with_priors({}, rates)
    gaps = {g.field: g for g in rank_gaps(CASE, make_scorer(tuned), tuned)}
    plain = {g.field: g for g in rank_gaps(CASE, make_scorer(schema), schema)}
    assert gaps["ecg"].info_gain < plain["ecg"].info_gain
    assert gaps["ecg"].flip_prob < plain["ecg"].flip_prob


def test_french_names_stay_provenance():
    schema = load_schema("ddxplus")
    assert schema.label_for_outcome("Pneumonia") == "Pneumonia"
    assert schema.sources["Pneumonia"] == "Pneumonie"


def test_domain_cannot_be_a_path():
    for bad in ("../../etc/passwd", "clinical/../variant", ""):
        try:
            load_schema(bad)
        except FileNotFoundError:
            pass
        else:
            raise AssertionError(f"{bad!r} should not have loaded")


def test_isotonic_only_goes_up():
    from askfirst.calibrate import isotonic
    knots = isotonic([0.1, 0.2, 0.3, 0.4, 0.5], [0, 1, 0, 1, 1])
    ys = [y for _, y in knots]
    assert ys == sorted(ys)


def test_calibration_beats_the_margin():
    from askfirst.calibrate import Calibrator
    # a margin that reads 0.4 but is right nine times in ten should come back near 0.9
    cal = Calibrator().fit([(0.4, 3, i % 10 != 0) for i in range(200)])
    assert cal(0.4, 3) > 0.8


def test_thin_records_read_as_thin():
    from askfirst.calibrate import Completeness
    seen = Completeness(lambda r: __import__("numpy").zeros(2, dtype="float32"))
    seen.fit([({"a": 1, "b": 1}, 10), ({"a": 1}, 10)] * 20)
    assert seen({"a": 1}) < seen({"a": 1, "b": 1, "c": 1, "d": 1, "e": 1})


def test_baked_rule_refuses_a_stub():
    from askfirst.calibrate import FLOOR, Calibrator, Completeness
    from askfirst.softmax import SoftmaxScorer
    schema = load_schema("ddxplus")
    model = SoftmaxScorer.load("src/askfirst/baked/ddxplus_softmax.npz", schema)
    done = Completeness.load("src/askfirst/baked/completeness.npz", model.encode)
    cal = Calibrator.load("src/askfirst/baked/calibrator.json")
    assert done({"E_55": "present"}) < FLOOR
    assert cal(0.2, 1) < cal(0.95, 12)
