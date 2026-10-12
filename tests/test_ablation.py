import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from askfirst.ablation import rank_gaps, sensitivity_map, sufficiency, total_variation
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
