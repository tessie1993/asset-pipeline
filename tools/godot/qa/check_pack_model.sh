#!/bin/bash
# Import one asset-pack model into Godot and capture it: the per-object Godot check of the
# image-to-assets pipeline (.claude/skills/image-to-assets/SKILL.md).
#
#   bash tools/godot/qa/check_pack_model.sh <pack> <id>
#
# Prints, for the reader to compare (observations, not a verdict):
#   BUILT <id> {...}          what the Blender build exported (the report in <id>_build.json)
#   IMPORT_ERROR <line>       each import error or warning that names this model's .glb (none: IMPORT clean)
#   GODOT_MODEL {...}         what Godot made of it (capture_pack_models.gd)
#   SHOT <path>               one screenshot per recorded view, <id>_godot_<view>.png
#
# Godot's import rewrites the project's shared import cache, so checks of different objects running
# at once take turns on one lock (.scratch/assetgen/godot.lock). Exit status: 0 when both Godot runs
# finished, 1 on a usage or missing-file error, 2 when a Godot run failed.
set -uo pipefail

if [ $# -ne 2 ]; then
  echo "usage: bash tools/godot/qa/check_pack_model.sh <pack> <id>" >&2
  exit 1
fi
PACK="$1"
ID="$2"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
GLB="assets/models/$PACK/$ID.glb"
EVIDENCE="production/qa/evidence/$PACK/$ID"
BUILD="$EVIDENCE/${ID}_build.json"
LOCK="$ROOT/.scratch/assetgen/godot.lock"

cd "$ROOT" || exit 1
for needed in "$GLB" "$BUILD"; do
  if [ ! -f "$needed" ]; then
    echo "error: $needed not found; build the object first" >&2
    exit 1
  fi
done
mkdir -p "$(dirname "$LOCK")"

exec 9>"$LOCK"
flock 9

echo "BUILT $ID $(python3 -c 'import json, sys; print(json.dumps(json.load(open(sys.argv[1]))["report"]))' "$BUILD")"

# The dummy audio driver: the container has no sound card, and ALSA errors would bury the output.
import_log="$(godot --headless --audio-driver Dummy --path . --import 2>&1)"
import_status=$?
errors="$(printf '%s\n' "$import_log" | grep -E "ERROR|WARNING" | grep -F "$ID.glb")"
if [ -n "$errors" ]; then
  printf '%s\n' "$errors" | sed 's/^/IMPORT_ERROR /'
else
  echo "IMPORT clean (no error or warning names $GLB)"
fi

rm -f "$EVIDENCE/${ID}"_godot_*.png
capture_log="$(xvfb-run -a -s "-screen 0 1280x720x24" godot --audio-driver Dummy --path . --rendering-driver opengl3 \
  --resolution 1280x720 --script res://tools/godot/qa/capture_pack_models.gd -- \
  --pack "$PACK" --models "$ID" 2>&1)"
capture_status=$?
printf '%s\n' "$capture_log" | grep -E "^GODOT_MODEL|SCRIPT ERROR|ERROR:.*capture_pack_models"
shots=0
for shot in "$EVIDENCE/${ID}"_godot_*.png; do
  [ -f "$shot" ] || continue
  echo "SHOT $shot"
  shots=$((shots + 1))
done
[ "$shots" -gt 0 ] || echo "SHOT none: the capture wrote no screenshot"

if [ $import_status -ne 0 ] || [ $capture_status -ne 0 ]; then
  echo "GODOT_RUN failed (import exit $import_status, capture exit $capture_status)"
  exit 2
fi
exit 0
