"""A stand-in for the vLLM server, so the GPU day is spent measuring instead of debugging.

    python3 -I scripts/fake_vllm.py 8111 &
    ASKFIRST_VLLM_URL=http://127.0.0.1:8111/v1 python3 -I scripts/run_proposer_recall.py ...

Credits are about 50 GPU-hours per account at $1.99 an hour, and the client code has never
spoken to a real server — only to a mock inside a unit test, which exercises the parsing but not
the plumbing. First contact failing on real hardware is the expensive way to find a typo.

This answers in the shape the vLLM OpenAI-compatible server documents: echo with max_tokens=0
returns one logprob per prompt token, `text_offset` is the cumulative character offset of each
token's start, and the first token's logprob is null because nothing precedes it. The numbers are
deterministic nonsense derived from the token text — the point is the shape and the plumbing, and
nothing measured here is a result.
"""

import hashlib
import json
import math
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODEL = "fake/instella-shaped-thing"
TOKEN = re.compile(r"\s+|\w+|[^\s\w]")


def tokenise(text):
    """Offsets have to be real even if the tokens are not, because text_offset is what the
    scorer slices the label with."""
    out, pos = [], 0
    for piece in TOKEN.findall(text):
        out.append((piece, pos))
        pos += len(piece)
    return out


def logprob_for(token, salt=""):
    h = hashlib.sha256((salt + token).encode()).digest()
    raw = int.from_bytes(h[:4], "big") / 0xFFFFFFFF
    return -0.05 - 6.0 * raw ** 2          # mostly near zero, occasional surprise


def completion(prompt, echo, want_logprobs):
    toks = tokenise(prompt)
    tokens = [t for t, _ in toks]
    offsets = [o for _, o in toks]
    # seed on the WHOLE prompt, not a prefix. Seeded on a prefix every ablation of a record
    # returns an identical distribution, information gain comes out as exactly 0.000, and the
    # ablation path never actually gets exercised — which is the one thing worth rehearsing.
    salt = hashlib.sha256(prompt.encode()).hexdigest()[:16]
    values = [None] + [logprob_for(t, salt) for t in tokens[1:]]

    choice = {"index": 0, "text": prompt if echo else "", "finish_reason": "length"}
    if want_logprobs is not None:
        choice["logprobs"] = {
            "tokens": tokens,
            "token_logprobs": values,
            "text_offset": offsets,
            "top_logprobs": [None] + [{t: v} for t, v in zip(tokens[1:], values[1:])],
        }
    return choice


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _send(self, payload, code=200):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.rstrip("/").endswith("/models"):
            return self._send({"object": "list",
                               "data": [{"id": MODEL, "object": "model", "owned_by": "nobody"}]})
        self._send({"error": {"message": f"no route for {self.path}"}}, 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        path = self.path.rstrip("/")

        if path.endswith("/completions") and not path.endswith("chat/completions"):
            prompts = body.get("prompt")
            prompts = prompts if isinstance(prompts, list) else [prompts]
            choices = []
            for i, p in enumerate(prompts):
                c = completion(p, body.get("echo", False), body.get("logprobs"))
                c["index"] = i
                choices.append(c)
            return self._send({
                "id": "cmpl-fake", "object": "text_completion", "created": 0,
                "model": body.get("model", MODEL), "choices": choices,
                "usage": {"prompt_tokens": sum(len(tokenise(p)) for p in prompts),
                          "completion_tokens": 0, "total_tokens": 0},
            })

        if path.endswith("chat/completions"):
            asked = body.get("messages", [{}])[-1].get("content", "")
            codes = re.findall(r"^([A-Za-z_][A-Za-z0-9_]*):", asked, re.M)
            wanted = re.search(r"most worth obtaining next", asked)
            k = 10
            m = re.search(r"choose the (\d+) items", asked)
            if m:
                k = int(m.group(1))
            # pick deterministically but not in menu order, or the harness would score the
            # ordering of our own menu rather than anything the model did
            ranked = sorted(codes, key=lambda c: hashlib.md5(c.encode()).hexdigest())
            reply = ", ".join(ranked[:k]) if wanted or codes else "nothing to suggest"
            return self._send({
                "id": "chatcmpl-fake", "object": "chat.completion", "created": 0,
                "model": body.get("model", MODEL),
                "choices": [{"index": 0, "finish_reason": "stop",
                             "message": {"role": "assistant", "content": reply}}],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            })

        self._send({"error": {"message": f"no route for {self.path}"}}, 404)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8111
    print(f"fake vLLM on http://127.0.0.1:{port}/v1 serving {MODEL!r}", flush=True)
    # threaded on purpose: keep-alive plus one thread means a second client's connection
    # queues behind the first one's idle socket, which looks exactly like a hung GPU
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
