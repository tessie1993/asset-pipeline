#!/bin/bash
# PostToolUse hook: every image Canva generates gets its background removed.
#
# A hook cannot call Canva itself (Canva is reached only through Claude's MCP tools), so when a
# Canva image-generation result names a new media id, this tells Claude to run Canva's
# remove-background on it next. In an image-to-assets run, `pack.py sheets` also refuses to
# download a sheet until its cutout (or the reason removal failed) is recorded.
# Always exits 0; the instruction goes back to Claude as additional context.

if ! command -v python3 >/dev/null 2>&1; then
  echo "canva-remove-background: python3 not found; remove the background of new Canva images by hand" >&2
  exit 0
fi

HOOK_INPUT="$(cat)" python3 - <<'PY'
import json
import os
import re

data = json.loads(os.environ.get("HOOK_INPUT") or "{}")
text = json.dumps(data.get("tool_response"))
media_ids = sorted(set(re.findall(r"reusable Canva media id is (M[A-Za-z0-9_-]+)", text)))
if media_ids:
    listed = ", ".join(media_ids)
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": (
            f"Canva generated {listed}. Every Canva image gets its background removed: call "
            "mcp__Canva__remove-background with sourceMedia {\"type\": \"MEDIA\", \"id\": \"<id>\"} for "
            "each, and use the returned image instead. In an image-to-assets run, record it with "
            "`python3 tools/assetgen/pack.py cutout <pack> <object id> --media <new id>` (or "
            "`--failed \"<reason>\"` if removal fails)."
        ),
    }}))
PY
exit 0
