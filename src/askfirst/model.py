"""The open model, served by vLLM on an AMD MI300X.

Two jobs, and they are deliberately different sizes.

The PROPOSER is one generation per case: read the record, name the fields a clinician would want
next. This is where medical knowledge belongs, and it is the thing a statistical scorer cannot do
— measured: a naive Bayes shortlist recalls 31.8% at k=20 because it knows co-occurrence and not
medicine.

The SCORER returns a distribution over outcomes. Not a sampled answer — the actual log
probabilities, which is the whole reason this has to be an open model on hardware we control.
You cannot read a closed API's distribution, and without the distribution there is no entropy, no
information gain and no calibrated refusal.

Request shapes here follow the vLLM OpenAI-compatible server: `echo=True` with `max_tokens=0`
returns logprobs over the prompt tokens, and `prompt` accepts a list so a whole label set costs
one round trip. Verified against the vLLM stable docs, not guessed — but verify again against the
live endpoint before trusting a number, because that is the rule."""

import math
import os
import re


class Endpoint:
    """Thin wrapper so the rest of the code never imports an HTTP client."""

    def __init__(self, base_url=None, model=None, api_key="EMPTY"):
        self.base_url = base_url or os.environ.get("ASKFIRST_VLLM_URL")
        self.model = model or os.environ.get("ASKFIRST_MODEL")
        self.api_key = api_key
        self._client = None

    def available(self):
        return bool(self.base_url)

    def client(self):
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as e:
                raise RuntimeError(
                    "The vLLM path needs the openai package. pip install -e '.[serve]'"
                ) from e
            if not self.base_url:
                raise RuntimeError(
                    "No endpoint configured. Set ASKFIRST_VLLM_URL to the vLLM server, "
                    "e.g. http://127.0.0.1:8000/v1 — see scripts/serve_vllm.sh"
                )
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client

    def resolved_model(self):
        if self.model:
            return self.model
        names = self.client().models.list()
        if not names.data:
            raise RuntimeError("The endpoint is up but serving no models.")
        return names.data[0].id


def describe(record, schema):
    """Plain prose, because that is what the model was trained on. Field codes mean nothing to
    it, so send the questions instead."""
    lines = []
    for name, value in record.items():
        spec = schema.fields.get(name)
        question = getattr(spec, "question", None) or name
        if spec is not None:
            shown = (
                ", ".join(spec.label_for(v) for v in value)
                if isinstance(value, list) else spec.label_for(value)
            )
        else:
            shown = ", ".join(map(str, value)) if isinstance(value, list) else str(value)
        lines.append(f"- {question} -> {shown}")
    return "\n".join(lines) if lines else "- nothing recorded yet"


class ModelScorer:
    """A distribution over outcomes, from real log probabilities.

    Scores every candidate outcome in one batched request by asking the server to echo the
    prompt and return its token logprobs, then summing the logprobs of the outcome's own tokens
    and normalising across outcomes."""

    def __init__(self, schema, endpoint=None, instruction=None):
        self.schema = schema
        self.endpoint = endpoint or Endpoint()
        self.instruction = instruction or (
            "Read the patient record and give the single most likely condition."
        )

    def _prompt(self, record, outcome):
        """Returns the full prompt and the character offset where the outcome text begins.

        We build the prompt, so we know exactly where the label starts. Handing that boundary to
        the scorer beats trying to find the label again afterwards by walking tokens backwards
        and hoping the string matches."""
        shown = self.schema.label_for_outcome(outcome)
        head = (
            f"{self.instruction}\n\nRecord:\n{describe(record, self.schema)}"
            f"\n\nCondition: "
        )
        return head + shown, len(head)

    def __call__(self, record):
        outcomes = self.schema.outcomes
        if not outcomes:
            raise ValueError("The schema has no outcomes to score against.")

        built = [self._prompt(record, o) for o in outcomes]
        reply = self.endpoint.client().completions.create(
            model=self.endpoint.resolved_model(),
            prompt=[p for p, _ in built],
            echo=True,
            logprobs=0,
            max_tokens=0,
            temperature=0.0,
        )

        totals = {}
        for choice in reply.choices:
            outcome = outcomes[choice.index]
            _, boundary = built[choice.index]
            totals[outcome] = self._label_logprob(choice, boundary)

        top = max(totals.values())
        weights = {k: math.exp(v - top) for k, v in totals.items()}
        mass = sum(weights.values())
        return {k: v / mass for k, v in weights.items()}

    @staticmethod
    def _label_logprob(choice, boundary):
        """Mean logprob of the tokens at or past the boundary.

        text_offset is a cumulative character offset per token, so everything from the boundary
        onward is the label and nothing else. Mean rather than sum, or long condition names get
        punished for being long instead of for being unlikely.

        The first prompt token has no logprob — there is nothing before it to condition on — so
        None entries are skipped rather than treated as zero."""
        lp = getattr(choice, "logprobs", None)
        if lp is None or not getattr(lp, "token_logprobs", None):
            raise RuntimeError(
                "The endpoint returned no prompt logprobs. echo=True with max_tokens=0 is "
                "required. If the server refuses, check --max-logprobs on the vLLM side."
            )

        offsets = list(getattr(lp, "text_offset", None) or [])
        values = list(lp.token_logprobs or [])
        tokens = list(getattr(lp, "tokens", None) or [])

        if offsets and len(offsets) == len(values):
            picked = [v for off, v in zip(offsets, values) if off >= boundary and v is not None]
        else:
            # no text_offset: fall back to counting back over the label's characters
            picked, seen = [], 0
            want = sum(len(t) for t in tokens) - boundary
            for token, value in zip(reversed(tokens), reversed(values)):
                if value is None:
                    continue
                picked.append(value)
                seen += len(token)
                if seen >= want:
                    break

        if not picked:
            raise RuntimeError(
                f"No tokens found past character {boundary}. Either echo was ignored or the "
                "server tokenised the prompt differently than its offsets claim."
            )
        return sum(picked) / len(picked)


class ModelProposer:
    """One generation per case: which fields would a clinician want next.

    Measured recall at k=10 is what caps the whole pipeline, so this is the first thing to
    evaluate once an endpoint exists — not the last."""

    PROMPT = (
        "You are helping a clinician decide what to ask or measure next.\n\n"
        "Record so far:\n{record}\n\n"
        "From the list below, choose the {k} items most worth obtaining next. "
        "Reply with their codes only, comma separated, nothing else.\n\n{menu}"
    )

    def __init__(self, schema, endpoint=None, menu_size=60):
        self.schema = schema
        self.endpoint = endpoint or Endpoint()
        self.menu_size = menu_size

    def _menu(self, record):
        rows = []
        for name in self.schema.missing_from(record)[: self.menu_size]:
            spec = self.schema.fields[name]
            question = getattr(spec, "question", None) or name
            rows.append(f"{name}: {question}")
        return "\n".join(rows)

    def __call__(self, record, k=10):
        client = self.endpoint.client()
        reply = client.chat.completions.create(
            model=self.endpoint.resolved_model(),
            messages=[{
                "role": "user",
                "content": self.PROMPT.format(
                    record=describe(record, self.schema), k=k, menu=self._menu(record)
                ),
            }],
            temperature=0.0,
            max_tokens=200,
        )
        text = reply.choices[0].message.content or ""
        picked = re.findall(r"\b[A-Za-z]+_\d+\b", text)

        unknown = [p for p in picked if p not in self.schema.fields]
        kept = [p for p in picked if p in self.schema.fields and p not in record]
        if unknown:
            # worth seeing rather than silently dropping — a model inventing field codes is a
            # signal the menu or the prompt is wrong
            kept.append(f"#invented:{len(unknown)}")
        return [p for p in kept if not p.startswith("#")][:k]
