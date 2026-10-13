"""What does one assessment actually cost to run?

    python3 scripts/run_cost_to_serve.py data/ddxplus/release_validate_patients

Cloud billing is CPU time, not round-trip latency, so this measures process CPU — the same thing
an instance-hour is sold by — across records of every completeness, because a THIN record is the
expensive one: fewer findings in hand means more candidate questions left to rank.

An earlier version of this number was taken from one warm request with a complete record on a
loopback socket and was optimistic for exactly that reason. This one is written down so nobody
has to take it from a commit message."""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from askfirst.ablation import most_telling_gap, rank_gaps, sensitivity_map  # noqa: E402
from askfirst.calibrate import CEILING, FLOOR, Calibrator, Completeness  # noqa: E402
from askfirst.ddxplus import load_patients  # noqa: E402
from askfirst.missing import cut, mechanisms  # noqa: E402
from askfirst.schema import load_schema  # noqa: E402
from askfirst.softmax import SoftmaxScorer  # noqa: E402
from run_abstention import KEPT, WEIGHTS  # noqa: E402

BAKE = Path("src/askfirst/baked")
OUT = Path("docs/results/cost-to-serve.json")
CASES = 200
# what the box this is deployed on costs, and what it gives you
INSTANCE = ("e2-standard-2", 0.067, 2)


def main(path):
    schema = load_schema("ddxplus")
    rates = json.loads((BAKE / "ddxplus_priors.json").read_text())["rates"]
    schema = schema.with_priors(
        {}, rates) if False else schema
    model = SoftmaxScorer.load(WEIGHTS, schema)
    cal = Calibrator.load(BAKE / "calibrator.json")
    seen = Completeness.load(BAKE / "completeness.npz", model.encode)
    patients = [p for p in load_patients(path, limit=60000) if p["evidences"]][46000:46000 + CASES]

    def assess(record):
        """Everything /api/assess does to a record, minus FastAPI and the socket."""
        dist = model(record)
        gaps = rank_gaps(record, model, schema)
        most_telling_gap(record, model, schema, gaps)
        sensitivity_map(record, model, schema)
        complete = seen(record)
        cal(max(dist.values()), record)
        return complete >= FLOOR and len(record) <= CEILING

    ways = mechanisms(schema, rates)
    rows, every = [], []
    print(f"{'record':>8} {'findings':>9} {'CPU ms':>9} {'per 1,000':>12}")
    usd_per_core_second = INSTANCE[1] / 3600 / INSTANCE[2]
    for frac in KEPT:
        cases = cut(patients, frac, ways["at random"])
        assess(cases[0]["evidences"])          # warm
        started = time.process_time()
        for case in cases:
            assess(case["evidences"])
        cpu = (time.process_time() - started) / len(cases)
        every.extend([cpu] * len(cases))
        mean_n = sum(len(c["evidences"]) for c in cases) / len(cases)
        rows.append({"kept": frac, "findings": round(mean_n, 1),
                     "cpu_ms": round(cpu * 1000, 1),
                     "usd_per_1000": round(cpu * usd_per_core_second * 1000, 6)})
        print(f"{frac:>8.0%} {mean_n:>9.1f} {cpu * 1000:>9.1f} "
              f"${cpu * usd_per_core_second * 1000:>11.4f}")

    mean = sum(every) / len(every)
    worst = max(r["cpu_ms"] for r in rows)
    print(f"\n  mean over every completeness level: {mean * 1000:.0f} ms of CPU, "
          f"${mean * usd_per_core_second * 1000:.4f} per 1,000")
    print(f"  the thin records are the expensive ones — {worst:.0f} ms at the worst level,")
    print(f"  because fewer findings in hand means more candidate questions left to rank.")
    print(f"\n  priced on {INSTANCE[0]} at ${INSTANCE[1]}/hour for {INSTANCE[2]} vCPU. "
          f"No GPU, no model call.")

    OUT.write_text(json.dumps({
        "instance": INSTANCE[0], "usd_per_hour": INSTANCE[1], "vcpu": INSTANCE[2],
        "cases_per_level": len(patients), "by_level": rows,
        "mean_cpu_ms": round(mean * 1000, 1),
        "mean_usd_per_1000": round(mean * usd_per_core_second * 1000, 6),
        "worst_cpu_ms": worst,
    }, indent=1))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/ddxplus/release_validate_patients")
