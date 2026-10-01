#!/bin/bash
# SessionStart hook: install Blender with the BlendKit add-on (plugins/blendkit), Godot, the CV
# libraries (OpenCV, NumPy for tools/assetgen/cv.py) and the ImageSorcery plugin (plugins/imagesorcery)
# in the background on Linux cloud sessions.
#
# The installers download hundreds of megabytes, so they run detached and this hook returns at once;
# each writes its exit code to .scratch/tool-install/<tool>.status when it finishes. All installers are
# idempotent (a pinned version already on disk is kept), so a resumed session only relinks the binaries.
# Skipped outside Linux and outside Claude Code on the web (CLAUDE_CODE_REMOTE), where a developer runs
# the installers themselves.

ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
LOG_DIR="$ROOT/.scratch/tool-install"

[ "$(uname -s)" = "Linux" ] || exit 0
[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0

mkdir -p "$LOG_DIR"
touch "$ROOT/.scratch/.gdignore"  # Godot never imports the scratch area
rm -f "$LOG_DIR"/*.status
# BlendKit installs into Blender, so it runs after Blender in the same job.
for tool in blender godot cv imagesorcery; do
  case "$tool" in
    cv) installer="$ROOT/tools/assetgen/install_cv.sh" ;;
    imagesorcery) installer="$ROOT/plugins/imagesorcery/install.sh" ;;
    *) installer="$ROOT/tools/$tool/install_$tool.sh" ;;
  esac
  (
    bash "$installer" > "$LOG_DIR/$tool.log" 2>&1
    status=$?
    echo $status > "$LOG_DIR/$tool.status"
    if [ "$tool" = "blender" ] && [ $status -eq 0 ]; then
      bash "$ROOT/plugins/blendkit/install.sh" > "$LOG_DIR/blendkit.log" 2>&1
      echo $? > "$LOG_DIR/blendkit.status"
    fi
  ) < /dev/null > /dev/null 2>&1 &
  disown
done
echo "Installing Blender with BlendKit, Godot, the CV libraries and ImageSorcery in the background (logs: .scratch/tool-install/)"
exit 0
