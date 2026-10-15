#!/bin/sh
# Run from any directory. This verifies artifacts; it never retrains or starts servers.
set -eu
TASK_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$TASK_ROOT"
TASK_PYTHON=${PYTHON_BIN:-.venv/bin/python}
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. "$TASK_PYTHON" -m pytest -q -p no:cacheprovider tests
"$TASK_PYTHON" -m modules.regional.cli verify-artifacts
npm --prefix frontend run lint
npm --prefix frontend test
npm --prefix frontend run build
if [ "${1:-}" = "--legacy-r" ]; then
  Rscript tests/test_m0_hygiene.R
fi
