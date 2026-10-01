#!/usr/bin/env bash
# install_blender.sh — install the pinned Blender release, its add-ons, Instant Meshes and xatlas.
#
# Linux x64 only (the container the generators run in). Every download is checked
# against its published SHA-256 before use. Safe to re-run: an existing install of
# the pinned version is kept when it starts, replaced when it does not (an interrupted
# extraction), and the add-ons are reinstalled in place. One run at a time: the
# SessionStart hook runs this in the background.
#
# Besides Blender and the add-ons below it installs, for the builders' kit
# (tools/blender/assetgen/kit.py):
#   - Instant Meshes (BSD-3), the quad remesher kit.quad_remesh prefers, as `instant-meshes`;
#   - xatlas (MIT), the UV atlas the final bake charts with, into Blender's own Python.
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

# Add-ons from extensions.blender.org, as "<id> <archive url>": terrain, vegetation, materials, and
# the modelling helpers builders use headless (extra mesh objects: rocks, round cubes, gears, gems;
# ivy; LoopTools; mmgpy adaptive remeshing; procedural tile and brick node groups; automatic UV
# seams). Each archive URL embeds the SHA-256 of the file it serves.
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
  "extra_mesh_objects https://extensions.blender.org/download/sha256:c85ce4bb2820d5af26b4dad66bf1a0fdeb4bfeffc668c5e4f098f1e416ed434b/add-on-extra-mesh-objects-v0.4.1.zip"
  "ivygen https://extensions.blender.org/download/sha256:7e60967a11cabacb9bca0128e65dcfb96cec8794a934bc7dc2e353ae720cff98/add-on-ivygen-v0.1.5.zip"
  "looptools https://extensions.blender.org/download/sha256:ff1ca3b3fff73094379da8b1fa2c1acbc9d88d26b7dfc73bb9de5941a6b50108/add-on-looptools-v4.7.7.zip"
  "mmgpy https://extensions.blender.org/download/sha256:c673b30af6827a697bd775e7086d2b90717c21ec9cfd3f8d759870101432f682/add-on-mmgpy-v0.16.2-linux-x64.zip"
  "proceduraltiles https://extensions.blender.org/download/sha256:4c6040e0c5654c066fa66f48321857d44e26ca1726d3c8c70cd04050cb6efc30/add-on-proceduraltiles-v0.0.4.zip"
  "zeeks_auto_uv_unwrap https://extensions.blender.org/download/sha256:9400842cc077f621b0583bd9466b2330a044671982871e6b7aab30e9b04e2edf/add-on-zeeks-auto-uv-unwrap-v2.0.0.zip"
)

# Instant Meshes (https://github.com/wjakob/instant-meshes, BSD-3): an unversioned 2019 build, so
# it is pinned by the SHA-256 of the archive.
readonly INSTANT_MESHES_URL="https://instant-meshes.s3.eu-central-1.amazonaws.com/instant-meshes-linux.zip"
readonly INSTANT_MESHES_SHA256="0ca8b7126f0e4cef89b02bf2febb9ca3f9a27c893445696bfc660868eccb7c0c"
# xatlas (https://github.com/mworchel/xatlas-python, MIT) for Blender's Python 3.13.
readonly XATLAS_URL="https://files.pythonhosted.org/packages/85/84/df846c46097331af6a10d3675edefc2ab893cb784c02fc7ab1e8cc580457/xatlas-0.0.11-cp313-cp313-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"
readonly XATLAS_SHA256="1c2ba5ca5e26dba5e9a04aab98ee5de0e5a0e8c87a1feae83da11052b83d86dd"

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

# Instant Meshes: extracted beside Blender, linked as `instant-meshes`.
download_verified "$INSTANT_MESHES_URL" "$INSTANT_MESHES_SHA256" "${work_dir}/instant-meshes.zip"
rm -rf "${INSTALL_DIR}/instant-meshes"
mkdir -p "${INSTALL_DIR}/instant-meshes"
python3 -m zipfile -e "${work_dir}/instant-meshes.zip" "${INSTALL_DIR}/instant-meshes"
instant_meshes="$(find "${INSTALL_DIR}/instant-meshes" -type f -name "Instant Meshes" | head -n 1)"
[[ -n "$instant_meshes" ]] || { echo "Instant Meshes binary not found in the archive" >&2; exit 1; }
chmod +x "$instant_meshes"
ln -sfn "$instant_meshes" "${BIN_DIR}/instant-meshes"

# xatlas: the wheel is a zip; its module goes into Blender's own site-packages.
download_verified "$XATLAS_URL" "$XATLAS_SHA256" "${work_dir}/xatlas.whl"
site_packages="$("$BLENDER" --background --factory-startup --python-expr \
  "import site; print('SITE', site.getsitepackages()[0])" 2>/dev/null | sed -n 's/^SITE //p' | head -n 1)"
[[ -n "$site_packages" ]] || { echo "Blender's site-packages not found" >&2; exit 1; }
python3 -m zipfile -e "${work_dir}/xatlas.whl" "$site_packages"

# Verify under the startup mode the generators use.
ids=("${EXTENSIONS[@]%% *}")
"$BLENDER" --background --factory-startup --python-exit-code 1 --python-expr "
import addon_utils
for ext_id in '${ids[*]}'.split():
    if addon_utils.enable(f'bl_ext.user_default.{ext_id}', default_set=False) is None:
        raise RuntimeError(f'add-on {ext_id} failed to load')
import xatlas
print('Verified: every add-on and xatlas load under --factory-startup')
"
"${BIN_DIR}/instant-meshes" --help > /dev/null 2>&1 || true
echo "Instant Meshes: ${BIN_DIR}/instant-meshes"
