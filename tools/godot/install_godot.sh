#!/usr/bin/env bash
# install_godot.sh — install the pinned Godot editor binary for headless runs.
#
# Linux x64 only (the container the tests and screenshot captures run in). The
# download is checked against the SHA-512 published with the release before use.
# Safe to re-run: an existing install of the pinned version is kept when it starts and
# replaced when it does not. One run at a time: the SessionStart hook runs this in the
# background.
#
# Usage: bash tools/godot/install_godot.sh
#
# Environment:
#   GODOT_INSTALL_DIR  where the binary is extracted (default /opt/godot)
#   GODOT_BIN_DIR      where the `godot` symlink is created (default /usr/local/bin)
#
# The version must match `engine.version` in project.yaml.

set -euo pipefail

readonly GODOT_VERSION="4.7.2"
readonly GODOT_BINARY="Godot_v${GODOT_VERSION}-stable_linux.x86_64"
readonly GODOT_URL="https://github.com/godotengine/godot/releases/download/${GODOT_VERSION}-stable/${GODOT_BINARY}.zip"
# From https://github.com/godotengine/godot/releases/download/4.7.2-stable/SHA512-SUMS.txt
readonly GODOT_SHA512="9aa00f7a605200940bce3027a567b782f49bd8e940dd06ae9e987bd65aee1b1467edd56ed84fcdcbdd44354bf613bdbb4e5d2913e925850368e150c59ed54c65"

readonly INSTALL_DIR="${GODOT_INSTALL_DIR:-/opt/godot}"
readonly BIN_DIR="${GODOT_BIN_DIR:-/usr/local/bin}"
readonly GODOT="${INSTALL_DIR}/${GODOT_BINARY}"

# starts <binary>: the binary runs and reports its version (a partly written one does not).
starts() {
  [[ -x "$1" ]] && timeout 60 "$1" --version > /dev/null 2>&1
}

mkdir -p "$INSTALL_DIR"
exec 9> "${INSTALL_DIR}/.install.lock"
flock 9
rm -rf "${INSTALL_DIR}"/.extract.*  # left by an interrupted run

work_dir="$(mktemp -d)"
trap 'rm -rf "$work_dir"' EXIT

if starts "$GODOT"; then
  echo "Godot ${GODOT_VERSION} already installed at ${GODOT}"
else
  echo "Downloading Godot ${GODOT_VERSION}"
  curl -fsSL -o "${work_dir}/godot.zip" "$GODOT_URL"
  echo "${GODOT_SHA512}  ${work_dir}/godot.zip" | sha512sum --check --quiet -
  # Unzip beside the target, then move it into place in one step (see install_blender.sh).
  staging="$(mktemp -d "${INSTALL_DIR}/.extract.XXXXXX")"
  unzip -oq "${work_dir}/godot.zip" -d "$staging"
  chmod +x "${staging}/${GODOT_BINARY}"
  mv -f "${staging}/${GODOT_BINARY}" "$GODOT"
  rmdir "$staging"
fi
mkdir -p "$BIN_DIR"
ln -sfn "$GODOT" "${BIN_DIR}/godot"

echo "Verified: $("$GODOT" --version)"
