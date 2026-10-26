#!/usr/bin/env bash
# Application-only install: never install an OpenCV wheel over the vendor runtime.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."

if [[ ! -d /opt/cool ]]; then
  echo 'COOL installation missing. Launch the official compatible Arm AMI first.' >&2
  exit 1
fi
COOL_PYTHON="${COOL_PYTHON:-/opt/cool/venvs/python_3.12/bin/python}"
if [[ ! -x "$COOL_PYTHON" ]]; then
  echo 'Set COOL_PYTHON to an existing vendor-provided COOL Python interpreter.' >&2
  exit 1
fi
"$COOL_PYTHON" -c 'import cv2; print(cv2.__version__, cv2.__file__)'
before_cv2="$("$COOL_PYTHON" -c 'import cv2; print(cv2.__version__, cv2.__file__)')"
"$COOL_PYTHON" -m pip install -r requirements-app.txt
"$COOL_PYTHON" -m pip install --no-deps -e .
"$COOL_PYTHON" -m pip install pytest==9.0.3
after_cv2="$("$COOL_PYTHON" -c 'import cv2; print(cv2.__version__, cv2.__file__)')"
if [[ "$before_cv2" != "$after_cv2" ]]; then
  echo 'OpenCV provenance changed unexpectedly; refusing to proceed.' >&2
  exit 1
fi
"$COOL_PYTHON" scripts/verify_cool.py --json results/environment.json --require-cool
if [[ ! -f data/eval/manifest.json ]]; then
  "$COOL_PYTHON" scripts/generate_dataset.py --output data/eval --count 50
fi
"$COOL_PYTHON" -m pytest -q
"$COOL_PYTHON" scripts/evaluate.py --dataset data/eval --iterations 1
echo 'Installation and smoke evaluation complete. Review results/environment.txt.'
