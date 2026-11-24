#!/bin/sh
# One-step runner: sets up a virtual environment (first run only), then runs the
# whole pipeline + tests.  Usage:  ./run.sh            (starter + full)
#                                  ./run.sh starter    (starter only)
set -e
cd "$(dirname "$0")"
SCALES="${1:-starter full}"

if [ ! -x .venv/bin/python ]; then
  echo "[setup] creating .venv"
  if command -v uv >/dev/null 2>&1; then
    uv venv --python 3.12 .venv && uv pip install --python .venv -r requirements.txt
  else
    PY=$(command -v python3.12 || command -v python3.11 || command -v python3.10 || command -v python3)
    "$PY" -c 'import sys; assert sys.version_info >= (3, 10), "Python 3.10+ required"'
    "$PY" -m venv .venv && .venv/bin/pip install -q -r requirements.txt
  fi
fi

for s in $SCALES; do
  .venv/bin/python -m oryva all --scale "$s"
done
.venv/bin/python -m pytest -q | tee output/test_results.txt
