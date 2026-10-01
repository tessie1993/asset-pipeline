#!/usr/bin/env bash
# install_blender.sh — install the pinned Blender release and the terrain, vegetation and material add-ons.
#
# Linux x64 only (the container the generators run in). Every download is checked
# against its published SHA-256 before use. Safe to re-run: an existing install of
# the pinned version is kept when it starts, replaced when it does not (an interrupted
# extraction), and the add-ons are reinstalled in place. One run at a time: the
# SessionStart hook runs this in the background.
#
# Usage: bash tools/blender/install_blender.sh
#
# Environment:
#   BLENDER_INSTALL_DIR  where the release is extracted (default /opt/blender)
#   BLENDER_BIN_DIR      where the `blender` symlink is created (default /usr/local/bin)
#
# The add-ons go into Blender's `user_default` extension repository and are enabled
# in the user preferences. Generators run with --factory-startup, which ignores those
# preferences, so a generator enables the add-on it uses itself:
#   addon_utils.enable("bl_ext.user_default.<id>", default_set=False)

set -euo pipefail

readonly BLENDER_VERSION="5.2.2"
readonly BLENDER_ARCHIVE="blender-${BLENDER_VERSION}-linux-x64"
readonly BLENDER_URL="https://download.blender.org/release/Blender${BLENDER_VERSION%.*}/${BLENDER_ARCHIVE}.tar.xz"
# From https://download.blender.org/release/Blender5.2/blender-5.2.2.sha256
readonly BLENDER_SHA256="84098912789dc450e95697c4184fb8a90acbe5111c2ba4aede3fecb57806a168"

# Terrain, vegetation and material add-ons from extensions.blender.org, as "<id> <archive url>".
# Each archive URL embeds the SHA-256 of the file it serves.
readonly EXTENSIONS=(
  "antlandscape https://extensions.blender.org/download/sha256:230571bc14c50952f3af99b70fdb365cf0cee503382975dc38149407a5a4c8c0/add-on-antlandscape-v0.2.0.zip"
  "erosion_terrain_extension https://extensions.blender.org/download/sha256:286a6033d576511099b35f1ac48dc6a35c0854c087d26199a9f9769ad8d04b2d/add-on-erosion-terrain-extension-v1.0.0.zip"
  "scatter_objects https://extensions.blender.org/download/sha256:3fda488f56523b799e3937c802119f1da986391e193cb4d443177e6e132c764b/add-on-scatter-objects-v0.2.0.zip"
  "terrainmixer https://extensions.blender.org/download/sha256:802d22cc5d7dbce0221d3399bc23b8f96799ba5c66421d7261016bd64d5800ac/add-on-terrainmixer-v3.1.3.zip"
  "modular_tree https://extensions.blender.org/download/sha256:7ffad885c79f7e1c062ea4a7404bf3f31e0f37b96126735d5876c35c8590c1b4/add-on-modular-tree-v5.5.2-linux-x64.zip"
  "ambientcg_material_importer https://extensions.blender.org/download/sha256:e6c8d6243c731ce2be49de5213c5ae2bb7641d27abd85dbd250ef54e92023575/add-on-ambientcg-material-importer-v1.5.0.zip"
  "sapling_tree_gen https://extensions.blender.org/download/sha256:27a478262e1c86612a9c3daffe7f4dce2802f5bc2294033462e5adc6d9c0080f/add-on-sapling-tree-gen-v0.3.7.zip"
  "space_colonization_tree_generator https://extensions.blender.org/download/sha256:4b3ed3c3d2ff48e8bd3eec520098e42d24937f4167ed3fd9210a870369a9ef83/add-on-space-colonization-tree-generator-v1.0.0.zip"
  "easy_tree https://extensions.blender.org/download/sha256:9ba32029650173c303037155c629dd85953699dbd8e62bd5e71da6927c84a4ff/add-on-easy-tree-v1.0.1.zip"
)

readonly INSTALL_DIR="${BLENDER_INSTALL_DIR:-/opt/blender}"
readonly BIN_DIR="${BLENDER_BIN_DIR:-/usr/local/bin}"
readonly RELEASE_DIR="${INSTALL_DIR}/${BLENDER_ARCHIVE}"
readonly BLENDER="${RELEASE_DIR}/blender"

# download_verified <url> <sha256> <dest>
download_verified() {
  curl -fsSL -o "$3" "$1"
  echo "$2  $3" | sha256sum --check --quiet -
}

# starts <binary>: the binary runs and reports its version (a half-extracted one does not).
starts() {
  [[ -x "$1" ]] && timeout 120 "$1" --version > /dev/null 2>&1
}

mkdir -p "$INSTALL_DIR"
exec 9> "${INSTALL_DIR}/.install.lock"
flock 9
rm -rf "${INSTALL_DIR}"/.extract.*  # left by an interrupted run

work_dir="$(mktemp -d)"
trap 'rm -rf "$work_dir"' EXIT

if starts "$BLENDER"; then
  echo "Blender ${BLENDER_VERSION} already installed at ${BLENDER}"
else
  if [[ -e "$RELEASE_DIR" ]]; then
    echo "Removing ${RELEASE_DIR}: it does not start (an interrupted extraction)"
    rm -rf "$RELEASE_DIR"
  fi
  echo "Downloading Blender ${BLENDER_VERSION}"
  download_verified "$BLENDER_URL" "$BLENDER_SHA256" "${work_dir}/blender.tar.xz"
  # Extract beside the target, then move it into place in one step, so an interrupted run
  # never leaves a half-extracted release where the next run would take it as installed.
  staging="$(mktemp -d "${INSTALL_DIR}/.extract.XXXXXX")"
  tar -xJf "${work_dir}/blender.tar.xz" -C "$staging"
  mv "${staging}/${BLENDER_ARCHIVE}" "$RELEASE_DIR"
  rmdir "$staging"
  starts "$BLENDER" || { echo "Blender ${BLENDER_VERSION} does not start after installing" >&2; exit 1; }
fi
mkdir -p "$BIN_DIR"
ln -sfn "$BLENDER" "${BIN_DIR}/blender"

for entry in "${EXTENSIONS[@]}"; do
  read -r id url <<<"$entry"
  sha256="${url#*sha256:}"
  sha256="${sha256%%/*}"
  echo "Installing add-on ${id}"
  download_verified "$url" "$sha256" "${work_dir}/${id}.zip"
  "$BLENDER" --command extension install-file --repo user_default --enable "${work_dir}/${id}.zip"
done

# Verify under the startup mode the generators use.
ids=("${EXTENSIONS[@]%% *}")
"$BLENDER" --background --factory-startup --python-exit-code 1 --python-expr "
import addon_utils
for ext_id in '${ids[*]}'.split():
    if addon_utils.enable(f'bl_ext.user_default.{ext_id}', default_set=False) is None:
        raise RuntimeError(f'add-on {ext_id} failed to load')
print('Verified: every add-on loads under --factory-startup')
"
