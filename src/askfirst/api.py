"""The web app.

Two kinds of endpoint, split on purpose. The baked ones read a JSON artifact and cannot fail, so
the page always has something to show even with no GPU attached and no model loaded. The live
ones score a record on demand and are allowed to fail without taking the page down, because the
GPU will not be up for the whole judging window — credits are per account and a 72-hour window
does not fit in one.

Which scorer answers a live request depends on what is configured, and the response says which
one did, every time. Nobody should have to guess whether a number came off a GPU."""

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .ablation import (
    argmax,
    by_cost_effectiveness,
    entropy,
    rank_blind,
    rank_gaps,
    sensitivity_map,
    most_telling_gap,
)
from .model import Endpoint, ModelScorer
from .schema import load_schema

BAKE = Path(__file__).parent / "baked"
BAKED = BAKE / "curve.json"
CASES = BAKE / "cases.json"
VARIANTS = BAKE / "variants.json"
NOTES = BAKE / "notes.json"
WEIGHTS = BAKE / "ddxplus_softmax.npz"
PRIORS = BAKE / "ddxplus_priors.json"
CALIBRATOR = BAKE / "calibrator.json"
COMPLETENESS = BAKE / "completeness.npz"


def find_ui():
    """Source checkout and container put the page in different places. Look for the file
    itself rather than assuming a depth, or a wrong guess serves a blank page quietly."""
    here = Path(__file__).resolve()
    tries = [here.parent.parent.parent / "ui", here.parent.parent / "ui", Path.cwd() / "ui"]
    for d in tries:
        if (d / "index.html").exists():
            return d
    return tries[0]


UI = find_ui()

app = FastAPI(title="askfirst", docs_url="/api/docs")
_schemas = {}
_scorers = {}
_rules = {}
_gates = {}


class Case(BaseModel):
    domain: str = "clinical"
    record: dict = {}
    coverage: float = 0.25
    # how complete the record is assumed to be. The right amount to refuse depends on it:
    # measured best coverage runs from 95% on a complete record to 5% on a nearly empty one.
    # Only used where there is no calibrator — where there is one, it works this out itself.
    kept: str = "0.4"
    # how right the answer has to be before it is worth giving. This is the only dial a person
    # should have to touch, and it is the one they actually have an opinion about.
    target: float = 0.95


SCALARS = (str, int, float, bool)


def clean(record, schema):
    """Keep what the schema knows and what the scorer can actually hold.

    Anything else used to reach the scorer and come back as a 503 reading
    "Scoring failed: unhashable type: 'dict'", which is a stack trace wearing a coat."""
    kept, ignored = {}, []
    for name, value in (record or {}).items():
        if name not in schema.fields:
            ignored.append(name)
            continue
        items = value if isinstance(value, list) else [value]
        if any(not isinstance(v, SCALARS) and v is not None for v in items):
            raise HTTPException(
                422,
                f"{name!r} came in as {type(value).__name__}. A finding is a value or a list of "
                "values, not something nested.",
            )
        kept[name] = value
    return kept, ignored


def unpack(baked, schema):
    """Baked priors arrive as one probability per declared value, in order, because JSON turns
    an integer value into a string key and half the DDXPlus fields are numbered scales."""
    out = {}
    for name, row in baked.items():
        spec = schema.fields.get(name)
        if spec is None or len(row) != len(spec.values):
            continue
        out[name] = dict(zip(spec.values, row))
    return out


def schema_for(domain):
    if domain not in _schemas:
        try:
            schema = load_schema(domain)
        except FileNotFoundError as e:
            raise HTTPException(404, str(e)) from e
        if domain == "ddxplus" and PRIORS.exists():
            # counted off the same patients the scorer was fitted on. Without them the ranker
            # treats "do you have a rare symptom" as a coin flip and rates the question as
            # though it always comes back yes.
            baked = json.loads(PRIORS.read_text())
            schema = schema.with_priors(unpack(baked["priors"], schema), baked.get("rates"))
        _schemas[domain] = schema
    return _schemas[domain]


def baked_scorer(schema):
    """The fitted softmax, shipped as 88KB of weights. Loading it costs nothing and it is the
    model every number on the page was measured with, so a visitor pokes the same thing the
    claims are about rather than a sketch of it."""
    if schema.domain not in _scorers:
        from .softmax import SoftmaxScorer
        _scorers[schema.domain] = SoftmaxScorer.load(WEIGHTS, schema)
    return _scorers[schema.domain]


def gate_for(schema):
    """The checks that are about the RECORD rather than the model: is there enough of it, and
    could it have come from a patient at all. Neither depends on what is doing the scoring, so
    neither is allowed to switch itself off when a different scorer is attached."""
    if schema.domain != "ddxplus" or not COMPLETENESS.exists():
        return None
    if schema.domain not in _gates:
        from .calibrate import Completeness
        from .softmax import SoftmaxScorer
        _gates[schema.domain] = Completeness.load(
            COMPLETENESS, SoftmaxScorer.load(WEIGHTS, schema).encode)
    return _gates[schema.domain]


def rule_for(schema, scorer):
    """The calibrated probability. It is fitted against one scorer's margins and does NOT
    transfer to another, so when a model is attached this returns None, the response says the
    precision promise does not apply, and the record-level gate above still runs."""
    if schema.domain != "ddxplus" or not CALIBRATOR.exists() or not COMPLETENESS.exists():
        return None
    if not hasattr(scorer, "encode"):
        return None
    if schema.domain not in _rules:
        from .calibrate import Calibrator, Completeness
        _rules[schema.domain] = Calibrator.load(CALIBRATOR)
    return _rules[schema.domain]


def pick_scorer(schema):
    """The open model when there is one, the fitted CPU model otherwise. The caller is told
    which answered, every time, because a number off a GPU and a number off a laptop should
    never be indistinguishable in the response."""
    endpoint = Endpoint()
    if endpoint.available():
        return ModelScorer(schema, endpoint), endpoint.describe()
    if schema.domain == "ddxplus" and WEIGHTS.exists():
        return baked_scorer(schema), "softmax regression on CPU, 99.6% top-1 on complete records"
    if schema.domain == "clinical":
        from .stub import make_scorer
        return make_scorer(schema), "hand-written baseline, no GPU attached"
    raise HTTPException(
        503,
        f"No scorer for {schema.domain!r} without a model endpoint. "
        "Set ASKFIRST_VLLM_URL, or use a domain that ships a CPU model.",
    )


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "model_endpoint": Endpoint().available(),
        "baked_curve": BAKED.exists(),
        "schemas": sorted(p.stem for p in (Path(__file__).parent / "schemas").glob("*.yaml")),
    }


@app.get("/api/curve")
def curve():
    """Measured once, served cold. This is the headline and it never depends on a GPU."""
    if not BAKED.exists():
        raise HTTPException(503, "Curve not baked yet. Run scripts/bake_curve.py")
    return json.loads(BAKED.read_text())


@app.get("/api/cases")
def cases():
    """Real held-out patients, so the live case is not a hand-written sketch."""
    if not CASES.exists():
        raise HTTPException(503, "No demo cases baked yet. Run scripts/bake_demo.py")
    baked = json.loads(CASES.read_text())
    schema = schema_for("ddxplus")
    for patient in baked["patients"]:
        patient["findings"] = [
            {
                "field": name,
                "question": schema.fields[name].question or name,
                "value": value,
                "label": ", ".join(
                    schema.fields[name].label_for(v)
                    for v in (value if isinstance(value, list) else [value])
                ),
            }
            for name, value in patient["evidences"].items()
            if name in schema.fields
        ]
        patient["truth_label"] = schema.label_for_outcome(patient["truth"])
    return baked


@app.get("/api/notes")
def notes():
    """Prose in, findings out. The extraction needs an open model, so these were produced by one
    and frozen — the page can show the whole path on a box with no accelerator, and each example
    carries what the model MISSED as well as what it found."""
    if not NOTES.exists():
        raise HTTPException(503, "No notes baked yet. Run scripts/bake_notes.py")
    return json.loads(NOTES.read_text())


@app.get("/api/variants")
def variants():
    """Module B, baked. Eleven contested CIViC groups where an ESM-2 score is allowed to vote,
    and what each call becomes at every strength the line could be granted."""
    if not VARIANTS.exists():
        raise HTTPException(503, "Nothing baked yet. Run scripts/run_variant_ablation.py")
    return json.loads(VARIANTS.read_text())


@app.get("/api/schema/{domain}")
def describe_schema(domain: str):
    schema = schema_for(domain)
    return {
        "domain": schema.domain,
        "outcomes": [
            {"key": o, "label": schema.label_for_outcome(o)} for o in schema.outcomes
        ],
        "fields": [
            {
                "name": name,
                "question": spec.question or name,
                "values": [
                    {"value": v, "label": spec.label_for(v)} for v in spec.values
                ],
                "cost": spec.cost,
                "delay": spec.delay,
            }
            for name, spec in schema.fields.items()
        ],
    }


def why(answering, decision):
    """Say which of the three things stopped it, because 'not confident' is the wrong answer
    when the real problem is that there is barely a record here."""
    if not decision["could_be_a_patient"]:
        return (f"{decision['findings']} findings in one record. The largest record in the data "
                f"this was fitted on holds 37, so this did not come from a patient and nothing "
                f"measured here applies to it.")
    if decision["completeness"] is not None and not decision["enough_record"]:
        return (f"only about {decision['completeness']:.0%} of a record — too little to judge "
                f"the answer by, whatever the confidence says")
    if decision["rule"] != "calibrated":
        return ("over the borrowed cut-off — but that cut-off was fitted against a different "
                "scorer, so it carries no precision promise here" if answering
                else "not confident enough — handing over, with what to get next")
    # an isotonic fit pins the top of its range at exactly 1.0, and "100% likely to be right"
    # is the one sentence this product must never print
    odds = decision["chance_right"]
    said = "better than 99%" if odds >= 0.995 else f"about {odds:.0%}"
    if answering:
        return f"{said} likely to be right, which clears the {decision['target']:.0%} asked for"
    return (f"{said} likely to be right, short of the {decision['target']:.0%} asked for "
            f"— handing over, with what to get next")


def as_gap(g, schema):
    """One missing field, described for a human: what to ask, what it settles, what it costs."""
    spec = schema.fields[g.field]
    tell = g.most_telling()
    return {
        "field": g.field,
        "question": spec.question or g.field,
        "answers": len(spec.values),
        "breadth_bits": round(g.breadth, 3),
        "yield_rate": round(g.yield_rate, 4),
        "info_gain_bits": round(g.info_gain, 4),
        "flip_prob": round(g.flip_prob, 4),
        "cost": g.cost,
        "delay": g.delay,
        "per_cost": round(g.value_per_cost(), 5),
        "if_this": (
            {
                "value": tell.value,
                "label": spec.label_for(tell.value),
                "then": schema.label_for_outcome(tell.verdict),
            } if tell else None
        ),
    }


@app.post("/api/assess")
def assess(case: Case):
    """Score a record, decide whether to answer, and say what to go and get if not."""
    schema = schema_for(case.domain)
    scorer, which = pick_scorer(schema)
    record, ignored = clean(case.record, schema)
    target = min(1.0, max(0.0, case.target))

    # Before anything is scored. A record that could not have come from a patient is refused
    # without a single forward pass, which is free on a laptop and is the point on a rented GPU.
    from .calibrate import CEILING
    if gate_for(schema) and len(record) > CEILING:
        return {
            "scored_by": "nothing — this was not scored",
            "answering": False,
            "why": why(False, {"could_be_a_patient": False, "findings": len(record),
                               "rule": "refused before scoring"}),
            "decision": {"rule": "refused before scoring", "target": None,
                         "chance_right": None, "completeness": None, "floor": None,
                         "enough_record": None, "findings": len(record), "ceiling": CEILING,
                         "could_be_a_patient": False},
            "confidence": 0.0, "threshold": 0.0, "threshold_calibrated": False,
            "ignored_fields": ignored, "entropy_bits": 0.0, "one_more_fact_flips": 0.0,
            "answer": None, "ranked": [], "go_get": [], "go_get_by_cost": [], "rests_on": [],
        }

    try:
        dist = scorer(record)
    except Exception as e:
        raise HTTPException(503, f"Scoring failed: {e}") from e

    gaps = rank_gaps(record, scorer, schema)
    confidence = max(dist.values()) if dist else 0.0
    threshold = threshold_for(case.coverage, case.kept)
    # the cut-off was measured against the softmax. A model on a GPU has its own confidence
    # scale, so borrowing this number for it is an assumption, and the response says so.
    calibrated = schema.domain == "ddxplus" and not Endpoint().available()

    from .calibrate import CEILING, FLOOR
    gate = gate_for(schema)
    cal = rule_for(schema, scorer) if calibrated else None

    # The record-level gate runs whatever is scoring. It was conditional on there being NO model
    # attached until a review pointed out that attaching one on a GPU turned the whole safety
    # mechanism off and left a cut-off borrowed from a different scorer doing the work alone.
    complete = gate(record) if gate else None
    plausible = len(record) <= CEILING if gate else True
    enough = complete is None or complete >= FLOOR

    if cal:
        chance = cal(confidence, record)
        answering = plausible and enough and chance >= target
        rule = "calibrated"
    else:
        chance = None
        answering = plausible and enough and confidence >= threshold
        rule = ("uncalibrated for this scorer — cut-off borrowed from the softmax"
                if gate else "threshold read off the baked curve")

    decision = {
        "rule": rule,
        "target": target if cal else None,
        "chance_right": round(chance, 4) if chance is not None else None,
        "completeness": round(complete, 4) if complete is not None else None,
        "floor": FLOOR if gate else None,
        "enough_record": enough,
        "findings": len(record),
        "ceiling": CEILING if gate else None,
        "could_be_a_patient": plausible,
    }

    ranked = sorted(dist.items(), key=lambda kv: -kv[1])[:5]
    return {
        "scored_by": which,
        "answering": answering,
        "why": why(answering, decision),
        "decision": decision,
        "confidence": round(confidence, 4),
        "threshold": round(threshold, 4),
        "threshold_calibrated": calibrated,
        "ignored_fields": ignored,
        "entropy_bits": round(entropy(dist), 3),
        "one_more_fact_flips": most_telling_gap(record, scorer, schema, gaps),
        "answer": (
            {"key": ranked[0][0], "label": schema.label_for_outcome(ranked[0][0])}
            if answering and ranked else None
        ),
        "ranked": [
            {"key": k, "label": schema.label_for_outcome(k), "p": round(v, 4)}
            for k, v in ranked
        ],
        "go_get": [as_gap(g, schema) for g in gaps[:6]],
        "go_get_by_cost": [as_gap(g, schema) for g in by_cost_effectiveness(gaps)[:6]],
        "rests_on": [
            {
                "field": i.field,
                "question": schema.fields[i.field].question or i.field,
                "influence": round(i.shift, 4),
            }
            for i in sensitivity_map(record, scorer, schema)[:6]
        ],
    }


class Reading(BaseModel):
    """Somebody else's scorer, reporting in.

    The decision this product makes needs two things and neither of them is our model: the
    record, and a number saying how sure something is. So it can be asked for directly, which is
    what makes this a layer rather than a model with a web page attached."""

    domain: str = "ddxplus"
    record: dict = {}
    confidence: float | None = None
    distribution: dict | None = None
    target: float = 0.95
    scorer: str = "unnamed"


def completeness_for(schema, named):
    """How much of the record is here, estimated against ONE operator's intake behaviour.

    The record-level half of the gate reads the record and not the scorer, so the shipped
    estimate is a defensible default for anybody. But records do not go short the same way in
    two places — seven realistic patterns span 54 points of accuracy at the same nominal
    completeness — so an operator who has run `fit_gate.py` on their own history gets theirs
    used instead of ours. That substitution is the thing a customer cannot take with them."""
    path = BAKE / f"completeness-{named}.npz"
    if not path.exists():
        return gate_for(schema), "shipped"
    key = f"seen:{path.name}"
    if key not in _gates:
        from .calibrate import Completeness
        from .softmax import SoftmaxScorer
        _gates[key] = Completeness.load(path, SoftmaxScorer.load(WEIGHTS, schema).encode)
    return _gates[key], named


def calibration_for(domain, scorer):
    """A calibration belongs to one scorer and is useless on another — measured, not assumed:
    an 80% cut-off borrowed from the softmax delivers 54.7% on the open model's own confidence.

    So they are stored per scorer and looked up by name. A caller we have no fit for gets the
    record-level verdict and an honest nothing where the precision promise would be."""
    name = "".join(c if c.isalnum() or c in "-_" else "-" for c in scorer.lower())[:48]
    path = BAKE / (f"calibrator-{name}.json" if name not in ("", "unnamed") else "calibrator.json")
    if name in ("", "unnamed", "softmax", "askfirst"):
        path = CALIBRATOR
    if not path.exists():
        return None, name
    from .calibrate import Calibrator
    key = f"cal:{path.name}"
    if key not in _rules:
        _rules[key] = Calibrator.load(path)
    return _rules[key], name


def odds(chance):
    """An isotonic fit tops out at exactly 1.0. Nothing here says it is certain."""
    return "better than 99%" if chance >= 0.995 else f"about {chance:.0%}"


@app.post("/api/gate")
def gate(reading: Reading):
    """The gate, with no scorer of ours anywhere in it.

    Send a record and your own model's confidence; get back whether the record can carry an
    answer, and what to ask if it cannot. Two of the three checks need nothing from us — the
    ceiling is a property of the record and the completeness floor is estimated from the record
    alone — so they work on the first call, for anybody. The third, the precision promise, is a
    calibration fitted to one scorer's confidence, and if we do not hold one for yours this says
    so instead of quietly borrowing the wrong curve."""
    from .calibrate import CEILING, FLOOR

    schema = schema_for(reading.domain)
    record, ignored = clean(reading.record, schema)
    target = min(1.0, max(0.0, reading.target))

    confidence = reading.confidence
    if confidence is None and reading.distribution:
        values = [v for v in reading.distribution.values() if isinstance(v, (int, float))]
        if not values:
            raise HTTPException(422, "The distribution had no numbers in it.")
        total = sum(values)
        confidence = max(values) / total if total > 0 else max(values)
    if confidence is None:
        raise HTTPException(
            422, "Send either a confidence between 0 and 1, or a distribution to take it from.")
    confidence = min(1.0, max(0.0, float(confidence)))

    cal, named = calibration_for(schema.domain, reading.scorer)
    seen, fitted_to = completeness_for(schema, named)
    complete = seen(record) if seen else None
    plausible = len(record) <= CEILING
    enough = complete is None or complete >= FLOOR

    # Only consult the calibration once the record has passed. Asked about a record the floor
    # or the ceiling has already rejected it answers 1.0 — an isotonic fit pins the top of its
    # range there — and "100% likely to be right" is the one sentence this product must never
    # print, least of all beside a refusal.
    chance = cal(confidence, record) if cal and plausible and enough else None
    if not cal:
        answering, rule = False, "no calibration fitted for this scorer"
    elif chance is None:
        answering, rule = False, "the record was refused before anything was scored"
    else:
        answering = chance >= target
        rule = f"calibrated against {named!r}"

    advice = rank_blind(record, schema)
    return {
        "answering": answering,
        "rule": rule,
        "why": (
            f"{len(record)} findings in one record, and the largest real one holds 38 — this did "
            f"not come from a patient" if not plausible else
            f"only about {complete:.0%} of a record — too little to judge an answer by, whatever "
            f"the confidence says" if not enough else
            "the record carries enough to judge an answer, but we hold no calibration for "
            f"{named!r}, so there is no precision promise to make. Fit one with "
            "scripts/fit_gate.py and this endpoint will keep it." if not cal else
            f"{odds(chance)} likely to be right, which clears the {target:.0%} asked for"
            if answering else
            f"{odds(chance)} likely to be right, short of the {target:.0%} asked for"
        ),
        "record_level": {
            "findings": len(record),
            "could_be_a_patient": plausible,
            "ceiling": CEILING,
            "completeness": round(complete, 4) if complete is not None else None,
            "floor": FLOOR,
            "enough_record": enough,
            "estimated_by": fitted_to,
            "needs_no_fit": fitted_to == "shipped",
        },
        "precision_promise": {
            "available": bool(cal),
            "scorer": named,
            "target": target if cal else None,
            "chance_right": round(chance, 4) if chance is not None else None,
            # 1.0 here is the top of the fitted range, not a claim of certainty. A machine
            # reading this field should know that; the prose above already refuses to say it.
            "chance_is_capped_at": 1.0,
            "chance_means": "the top of the isotonic fit, which is 1.0, not certainty",
            "how_to_fit": None if cal else {
                "script": "scripts/fit_gate.py",
                "needs": "your scorer's confidence and whether it was right, on records of "
                         "varying completeness — a few thousand rows is enough",
                "why": "a cut-off borrowed across scorers was measured delivering 54.7% where "
                       "it promised 80%",
            },
        },
        "go_get": [
            {"field": g.field,
             "question": schema.fields[g.field].question or g.field,
             "answers": len(schema.values_for(g.field)),
             "usually_answered": round(g.yield_rate, 4)}
            for g in advice[:6]
        ],
        "advice_rule": "breadth x answer rate, which needs no model and measured 72.3% against "
                       "42.7% for asking nothing",
        "ignored_fields": ignored,
        "not_a_diagnosis": "This names a condition when it accepts and hands over when it does "
                           "not. It is not a medical device and no clinician has reviewed it.",
    }


def threshold_for(coverage, kept="0.4"):
    """Read the confidence cut-off straight off the baked curve, so the dial in the page and the
    decision taken here are the same number rather than two guesses that drift apart.

    One curve per level of record completeness, because that is what the measurement showed
    matters — the best policy answers 95% of complete records and 5% of nearly empty ones."""
    if not BAKED.exists():
        return 0.0
    baked = json.loads(BAKED.read_text())
    levels = baked.get("levels") or {}
    rows = levels.get(str(kept)) or baked.get("rows") or []
    if not rows:
        return 0.0
    nearest = min(rows, key=lambda r: abs(r["coverage"] - coverage))
    return float(nearest["threshold"])


if UI.exists():
    app.mount("/", StaticFiles(directory=str(UI), html=True), name="ui")

    @app.get("/")
    def index():
        return FileResponse(str(UI / "index.html"))
