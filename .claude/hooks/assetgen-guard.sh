#!/bin/bash
# Hook entry for the image-to-assets guards (tools/assetgen/guard.py), as PreToolUse ("pre") and
# PostToolUse ("post"). Does nothing unless a pipeline run is in progress
# (.scratch/assetgen/run.json, written by `pack.py run-start`). During a run it executes the copy of
# guard.py in the run's snapshot, so changing the pipeline cannot switch the guards off.
#   pre:  refuses edits outside the pack's folders, git changes, unprepared Blender builds and
#         Canva prompts that are not exactly `pack.py prompt` (exit 2, reason on stderr)
#   post: restores changed pipeline files, quarantines stray files, points builders at their CV compare

MODE="${1:-pre}"
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd)}"
[ -f "$ROOT/.scratch/assetgen/run.json" ] || exit 0

if ! command -v python3 >/dev/null 2>&1; then
  echo "assetgen-guard: python3 not found, the pipeline guards are NOT enforced" >&2
  exit 0
fi

GUARD="$ROOT/.scratch/assetgen/snapshot/files/tools/assetgen/guard.py"
[ -f "$GUARD" ] || GUARD="$ROOT/tools/assetgen/guard.py"
exec python3 "$GUARD" "$MODE" --root "$ROOT"
