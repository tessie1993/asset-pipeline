#!/usr/bin/env bash
# plugins/imagesorcery/install.sh — install ImageSorcery MCP (sunriseapps/imagesorcery-mcp, MIT,
# pinned) in this folder, apart from the pipeline, and register it with Claude Code as
# `imagesorcery`: image tools the builders call themselves (crop, resize, find, detect, ocr, ...).
# The pipeline adds nothing to its tools or their answers.
#
# As its README says: a virtual environment (here `.venv`, git-ignored), `pip install
# imagesorcery-mcp`, then `imagesorcery-mcp --post-install` (downloads the YOLOE models and
# MobileCLIP, installs Ultralytics' CLIP). Telemetry stays off (telemetry.enabled = false in its
# config.toml, DISABLE_TELEMETRY=true for the server); the server reads and writes only the
# pipeline's evidence folders and .scratch (IMAGESORCERY_AVAILABLE_PATHS). Idempotent: an installed
# pinned version with its models is kept.
#
# Usage: bash plugins/imagesorcery/install.sh
# Afterwards start a new Claude Code session so the server's tools load.

set -euo pipefail

readonly VERSION="0.12.0"
readonly HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly ROOT="$(cd "$HERE/../.." && pwd)"
readonly VENV="$HERE/.venv"
readonly MODELS=(yoloe-11l-seg.pt yoloe-11l-seg-pf.pt yoloe-11s-seg.pt yoloe-11s-seg-pf.pt)

python=""
for candidate in python3.12 python3.13 python3.11 python3.10 python3; do
  if command -v "$candidate" >/dev/null 2>&1 \
      && "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 10))' 2>/dev/null; then
    python="$candidate"
    break
  fi
done
[[ -n "$python" ]] || { echo "Python 3.10 or newer is required" >&2; exit 1; }

# Where the server keeps its config.toml, models/ and mobileclip_blt.ts: it changes to this folder on
# start (three levels above its package, as in imagesorcery_mcp/server.py).
home_of() {
  "$VENV/bin/python" -c 'import pathlib, importlib.util; print(pathlib.Path(importlib.util.find_spec("imagesorcery_mcp").origin).resolve().parents[2])'
}

installed() {
  [[ -x "$VENV/bin/imagesorcery-mcp" ]] || return 1
  [[ "$("$VENV/bin/python" -c 'from importlib.metadata import version; print(version("imagesorcery-mcp"))' 2>/dev/null)" == "$VERSION" ]] || return 1
  local home
  home="$(home_of)" || return 1
  [[ -f "$home/mobileclip_blt.ts" ]] || return 1
  for model in "${MODELS[@]}"; do
    [[ -f "$home/models/$model" ]] || return 1
  done
  "$VENV/bin/python" -c 'import clip' 2>/dev/null
}

if installed; then
  echo "ImageSorcery MCP $VERSION and its models already in $VENV"
else
  [[ -x "$VENV/bin/python" ]] || "$python" -m venv "$VENV"
  "$VENV/bin/pip" install --quiet --disable-pip-version-check "imagesorcery-mcp==$VERSION"
  "$VENV/bin/imagesorcery-mcp" --post-install
  installed || { echo "ImageSorcery's post-install did not leave every model in $(home_of)" >&2; exit 1; }
fi

home="$(home_of)"
"$VENV/bin/python" - "$home/config.toml" <<'EOF'
import pathlib, sys, toml
path = pathlib.Path(sys.argv[1])
config = toml.loads(path.read_text()) if path.exists() else {}
config.setdefault("telemetry", {})["enabled"] = False
path.write_text(toml.dumps(config))
EOF

if command -v claude >/dev/null 2>&1; then
  if claude mcp get imagesorcery >/dev/null 2>&1; then
    echo "Claude Code already has an MCP server named imagesorcery"
  else
    claude mcp add --scope user imagesorcery \
      -e DISABLE_TELEMETRY=true \
      -e "IMAGESORCERY_AVAILABLE_PATHS=$ROOT/production/qa/evidence:$ROOT/.scratch" \
      -- "$VENV/bin/imagesorcery-mcp"
  fi
else
  echo "Claude Code not found: register the server yourself: $VENV/bin/imagesorcery-mcp (name it imagesorcery)"
fi

echo "ImageSorcery MCP $VERSION installed in $VENV (models in $home/models)."
