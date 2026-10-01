#!/bin/bash
# PreToolUse hook: while an image-to-assets pipeline run is in progress, nothing may change the
# pipeline and nothing may be committed.
#
# A run is in progress while .scratch/assetgen/run.json exists (`pack.py run-start` writes it,
# `pack.py run-end` removes it). During a run this blocks:
#   - Write/Edit/NotebookEdit of a pipeline file (the list in PROTECTED below);
#   - Bash commands that change git state (commit, push, add, checkout, restore, ...);
#   - Bash commands that name a pipeline file together with a file-changing command.
# Everything else (the run's own outputs, the per-object generators) is allowed.
# Exit 0 = allow, exit 2 = block (stderr is shown to the model).

if [ -f "project.yaml" ] || [ -d ".claude" ]; then
  ROOT="$PWD"
elif [ -n "${CLAUDE_PROJECT_DIR:-}" ] && [ -d "${CLAUDE_PROJECT_DIR}" ]; then
  ROOT="$CLAUDE_PROJECT_DIR"
else
  ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd)"
fi

LOCK="$ROOT/.scratch/assetgen/run.json"
[ -f "$LOCK" ] || exit 0

if ! command -v python3 >/dev/null 2>&1; then
  echo "assetgen-run-guard: python3 not found, the pipeline lock is NOT enforced" >&2
  exit 0
fi

HOOK_INPUT="$(cat)" GUARD_ROOT="$ROOT" GUARD_LOCK="$LOCK" python3 - <<'PY'
import fnmatch
import json
import os
import re
import sys

PROTECTED = [
    "tools/assetgen/*",
    "tools/assets/*",
    "tools/blender/assetgen/kit.py",
    "tools/blender/assetgen/README.md",
    "tools/blender/assetgen/zoom.py",
    "tools/blender/common/*",
    "tools/blender/install_blender.sh",
    "tools/godot/install_godot.sh",
    "tools/godot/qa/capture_pack_models.gd*",
    "tests/tools/assetgen/*",
    "design/asset-packs/*/pack.json",
    ".claude/*",
    ".github/*",
    ".scratch/assetgen/run.json",
]
# Literal fragments of the protected paths, to spot them inside a shell command.
FRAGMENTS = ["tools/assetgen/", "tools/assets/", "assetgen/kit.py", "assetgen/README.md", "assetgen/zoom.py", "blender/common/",
             "install_blender.sh", "install_godot.sh", "capture_pack_models.gd", "tests/tools/assetgen",
             "pack.json", ".claude/", ".github/", "assetgen/run.json"]
GIT_CHANGE = re.compile(r"\bgit\b(\s+-C\s+\S+)?\s+(commit|push|add|rm|mv|merge|rebase|reset|checkout|switch|"
                        r"restore|stash|cherry-pick|revert|apply|am|tag|pull|clean)\b")
FILE_CHANGE = re.compile(r"(\bsed\s+(-\w*\s+)*-i|\bperl\s+(-\w*\s+)*-i|\btee\b|>|\bmv\b|\bcp\b|\brm\b|\btruncate\b|"
                         r"\btouch\b|\bchmod\b|\bln\b|\binstall\b|\bdd\b|\bpatch\b)")

root = os.path.realpath(os.environ["GUARD_ROOT"])
data = json.loads(os.environ.get("HOOK_INPUT") or "{}")
tool = data.get("tool_name", "")
args = data.get("tool_input") or {}
try:
    run = json.load(open(os.environ["GUARD_LOCK"]))
except (OSError, ValueError):
    run = {}
where = f"pack {run.get('pack', '?')}, started {run.get('started', '?')}"


def block(reason: str) -> None:
    print(f"Blocked: an image-to-assets pipeline run is in progress ({where}). {reason} "
          "During a run the pipeline is locked and nothing is committed. If the pipeline itself is "
          "wrong, stop and report it to the user; the lock ends with "
          "`python3 tools/assetgen/pack.py run-end`.", file=sys.stderr)
    sys.exit(2)


def is_protected(path: str) -> bool:
    full = os.path.realpath(path if os.path.isabs(path) else os.path.join(root, path))
    if not full.startswith(root + os.sep):
        return False
    rel = os.path.relpath(full, root)
    return any(fnmatch.fnmatch(rel, pattern) for pattern in PROTECTED)


if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
    path = args.get("file_path") or args.get("notebook_path") or ""
    if path and is_protected(path):
        block(f"{path} is part of the pipeline.")
elif tool == "Bash":
    command = args.get("command", "")
    if GIT_CHANGE.search(command):
        block("Git commands that change the repository are not allowed.")
    if FILE_CHANGE.search(command) and any(fragment in command for fragment in FRAGMENTS):
        block("This command would change a pipeline file.")
sys.exit(0)
PY
