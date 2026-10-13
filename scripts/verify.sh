#!/usr/bin/env bash
# Regenerate every headline number in this repo from the public data, and fail if any of them
# disagrees with what is published.
#
#   ./scripts/verify.sh          the fast pass, about 4 minutes
#   ./scripts/verify.sh --all    everything, about 40 minutes
#
# The point is that nobody has to take a number here on trust. The fast pass rebuilds the baked
# risk-coverage curve and the calibration from 60,000 patients and diffs them against the
# committed artifacts; the test suite then fails if any document quotes a figure the artifacts do
# not support. --all adds the two long measurements, which are long because they are honest
# rather than because they are slow: 4,000 patients x 3 record sizes x 223 candidate questions.
set -uo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
PY="${PY:-.venv/bin/python}"
DATA="${DATA:-data/ddxplus/release_validate_patients}"
failed=0

say() { printf '\n\033[1m%s\033[0m\n' "$*"; }
check() {
  if git diff --quiet -- "$1"; then
    printf '  reproduced, byte for byte: %s\n' "$1"
  else
    printf '  CHANGED: %s\n' "$1"
    git --no-pager diff --stat -- "$1"
    failed=1
  fi
}

if [ ! -f "$DATA" ]; then
  echo "No DDXPlus at $DATA. scripts/fetch_data.sh prints where to get it and under what licence."
  exit 2
fi

say "1/5  the risk-coverage curve the page serves  (~90s)"
$PY scripts/bake_curve.py "$DATA" >/dev/null || failed=1
check src/askfirst/baked/curve.json

say "2/5  the calibration, the completeness estimator and the answer-rate priors  (~2 min)"
$PY scripts/bake_demo.py "$DATA" >/dev/null || failed=1
$PY scripts/run_calibration.py "$DATA" >/dev/null || failed=1
check docs/results/calibration.json
check src/askfirst/baked/calibrator.json

say "3/5  the variant ablation  (~20s)"
$PY -I scripts/run_variant_ablation.py data/civic/evidence.tsv >/dev/null || failed=1
check docs/results/variant-ablation.json
check src/askfirst/baked/variants.json

say "4/5  the gate against the standard selective-prediction baselines, seven folds  (~3 min)"
$PY scripts/run_conformal.py "$DATA" 2000 >/dev/null || failed=1
check docs/results/conformal.json

if [ -f data/nhamcs-raw/layout-2022.json ]; then
  say "5/5  the real queue  (~90s)"
  $PY scripts/run_nhamcs.py data/nhamcs-raw >/dev/null || failed=1
  check docs/results/nhamcs.json
else
  say "5/5  skipping the real queue — no NHAMCS on disk, see scripts/fetch_data.sh"
fi

if [ "${1:-}" = "--all" ]; then
  say "and the long ones — three scorers, and the arms that try to delete the gate  (~55 min)"
  $PY scripts/run_portability.py "$DATA" 1200 >/dev/null || failed=1
  check docs/results/portability.json
  $PY scripts/run_make_it_unnecessary.py "$DATA" 1200 >/dev/null || failed=1
  check docs/results/make-it-unnecessary.json
  $PY scripts/run_floor_sweep.py "$DATA" 2000 >/dev/null || failed=1
  check docs/results/floor-sweep.json
  $PY scripts/run_decision_value.py "$DATA" 4000 >/dev/null || failed=1
  check docs/results/decision-value.json
  $PY scripts/run_missingness.py "$DATA" >/dev/null || failed=1
  check docs/results/missingness.json
  $PY scripts/run_value.py "$DATA" >/dev/null || failed=1
  check docs/results/value.json
else
  say "skipping the long measurements — pass --all for those"
fi

say "and the documents, against the artifacts"
$PY -m pytest tests -q || failed=1

if [ "$failed" = "0" ]; then
  say "Everything reproduced and every published figure matches its artifact."
else
  say "Something did not reproduce. The diff above is the disagreement."
fi
exit "$failed"
