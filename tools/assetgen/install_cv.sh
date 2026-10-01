#!/bin/bash
# Install the CV libraries for tools/assetgen/cv.py (OpenCV and NumPy, pinned) into .scratch/pydeps
# inside the project (gitignored), leaving the system Python untouched. Idempotent: pinned versions
# already there are kept. The SessionStart hook runs it in cloud sessions; run it by hand elsewhere.
set -euo pipefail

OPENCV="5.0.0.93"
NUMPY="2.4.6"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET="$ROOT/.scratch/pydeps"
CHECK="import cv2, numpy, sys; sys.exit(not (cv2.__version__.startswith('5.0') and numpy.__version__ == '$NUMPY'))"

if PYTHONPATH="$TARGET" python3 -c "$CHECK" 2>/dev/null; then
  echo "OpenCV $(PYTHONPATH="$TARGET" python3 -c 'import cv2; print(cv2.__version__)') and NumPy $NUMPY already in $TARGET"
  exit 0
fi
mkdir -p "$TARGET"
python3 -m pip install --quiet --disable-pip-version-check --upgrade --target "$TARGET" \
  "opencv-python-headless==$OPENCV" "numpy==$NUMPY"
PYTHONPATH="$TARGET" python3 -c "import cv2, numpy; print('OpenCV', cv2.__version__, 'NumPy', numpy.__version__, 'in $TARGET')"
