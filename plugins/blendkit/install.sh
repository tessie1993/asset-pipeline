#!/usr/bin/env bash
# plugins/blendkit/install.sh — install the BlendKit add-on (BlenderKit/Blendkit, GPL-2.0-or-later,
# pinned; the release https://www.blendkit.com/get-blendkit/ serves) into the headless Blender, as an
# extension in Blender's `user_default` repository like the other add-ons. Its data (the login, the
# downloaded assets, the BlendKit-Client binary and its log) stay in this folder's `.data`, git-ignored.
#
# Needs Blender (tools/blender/install_blender.sh) first. Idempotent: the pinned version, once
# installed, is kept. Logging in is separate: python3 plugins/blendkit/login.py start.
#
# Usage: bash plugins/blendkit/install.sh

set -euo pipefail

readonly VERSION="3.21.2.260918"
readonly URL="https://github.com/BlenderKit/Blendkit/releases/download/v${VERSION}/blenderkit-v${VERSION}.zip"
readonly SHA256="e8b7cd5bf900726c56365453b5cd4ed3ba52c4ddd4a3bcb5396d6ed7e1ab786d"
readonly HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly BLENDER="${BLENDER:-blender}"

command -v "$BLENDER" >/dev/null 2>&1 || { echo "Blender not found: run tools/blender/install_blender.sh first" >&2; exit 1; }

# The installed add-on's version as its manifest gives it ("3.21.2-260918"), empty when not installed.
installed_version() {
  "$BLENDER" --background --factory-startup --python-expr "
import bpy, pathlib, tomllib
manifest = pathlib.Path(bpy.utils.user_resource('EXTENSIONS', path='user_default')) / 'blenderkit' / 'blender_manifest.toml'
print('VERSION', tomllib.loads(manifest.read_text())['version'] if manifest.exists() else '')
" 2>/dev/null | sed -n 's/^VERSION //p' | head -n 1
}

mkdir -p "$HERE/.data"
chmod 700 "$HERE/.data"
if [[ "$(installed_version)" == "${VERSION%.*}-${VERSION##*.}" ]]; then
  echo "BlendKit ${VERSION} already installed"
else
  work_dir="$(mktemp -d)"
  trap 'rm -rf "$work_dir"' EXIT
  echo "Downloading BlendKit ${VERSION}"
  curl -fsSL -o "$work_dir/blenderkit.zip" "$URL"
  echo "$SHA256  $work_dir/blenderkit.zip" | sha256sum --check --quiet -
  "$BLENDER" --command extension install-file --repo user_default --enable "$work_dir/blenderkit.zip"
fi

# Verify under the startup mode the generators use.
"$BLENDER" --background --factory-startup --python-exit-code 1 --python-expr "
import addon_utils
if addon_utils.enable('bl_ext.user_default.blenderkit', default_set=False) is None:
    raise RuntimeError('BlendKit failed to load')
print('Verified: BlendKit loads under --factory-startup')
" 2>&1 | grep -E "^Verified|Error|Traceback" || { echo "BlendKit does not load" >&2; exit 1; }
echo "BlendKit ${VERSION} installed. Log in with: python3 plugins/blendkit/login.py start"
