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
    rank_gaps,
    sensitivity_map,
    sufficiency,
)
from .model import Endpoint, ModelScorer
from .schema import load_schema

BAKE = Path(__file__).parent / "baked"
BAKED = BAKE / "curve.json"
CASES = BAKE / "cases.json"
VARIANTS = BAKE / "variants.json"
WEIGHTS = BAKE / "ddxplus_softmax.npz"
PRIORS = BAKE / "ddxplus_priors.json"


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


class Case(BaseModel):
    domain: str = "clinical"
    record: dict = {}
    coverage: float = 0.25
    # how complete the record is assumed to be. The right amount to refuse depends on it:
    # measured best coverage runs from 95% on a complete record to 5% on a nearly empty one.
    kept: str = "0.4"


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

    try:
        dist = scorer(case.record)
    except Exception as e:
        raise HTTPException(503, f"Scoring failed: {e}") from e

    gaps = rank_gaps(case.record, scorer, schema)
    confidence = max(dist.values()) if dist else 0.0
    threshold = threshold_for(case.coverage, case.kept)
    answering = confidence >= threshold
    # the cut-off was measured against the softmax. A model on a GPU has its own confidence
    # scale, so borrowing this number for it is an assumption, and the response says so.
    calibrated = schema.domain == "ddxplus" and not Endpoint().available()

    ranked = sorted(dist.items(), key=lambda kv: -kv[1])[:5]
    return {
        "scored_by": which,
        "answering": answering,
        "why": (
            "confident enough at this coverage setting" if answering
            else "not confident enough — handing over, with what to get next"
        ),
        "confidence": round(confidence, 4),
        "threshold": round(threshold, 4),
        "threshold_calibrated": calibrated,
        "entropy_bits": round(entropy(dist), 3),
        "sufficiency": sufficiency(case.record, scorer, schema, gaps),
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
            for i in sensitivity_map(case.record, scorer, schema)[:6]
        ],
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
