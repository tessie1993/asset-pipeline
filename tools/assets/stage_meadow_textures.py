"""Copy the meadow's bark and scanned-prop textures from the download cache into the project.

Run::

    python3 tools/assets/stage_meadow_textures.py [--cache <dir>] [--out assets/textures/meadow]

Needs the CC0 sources in the cache (``python3 tools/assets/fetch_cc0_assets.py fetch``). Two groups:

- Bark: which Poly Haven bark a tree species wears is the ``bark`` key of
  ``assets/data/meadow/meadow_tree_params.json``; written as ``bark_<species>_albedo.jpg`` / ``_normal.jpg``.
- Scans: every asset the families of ``assets/data/meadow/meadow_scan_params.json`` use, written as
  ``scan_<asset>_albedo.jpg`` / ``_normal.jpg``.

Files are copied byte for byte from the Poly Haven download (no re-encode): ``_albedo`` is the colour map,
``_normal`` the tangent-space normal map, OpenGL (+Y up) convention. A ``.import`` file goes beside each,
so Godot imports the normal maps as normal maps (which a ``hint_normal`` sampler does not otherwise trigger
outside the editor) and keeps both lossless. Godot fills in the ``uid`` and ``path`` of an import file the
first time it imports it; existing import files are left alone.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TREE_PARAMS_PATH = REPO_ROOT / "assets" / "data" / "meadow" / "meadow_tree_params.json"
SCAN_PARAMS_PATH = REPO_ROOT / "assets" / "data" / "meadow" / "meadow_scan_params.json"
MANIFEST_PATH = REPO_ROOT / "assets" / "data" / "meadow" / "meadow_asset_sources.json"
DEFAULT_OUT = REPO_ROOT / "assets" / "textures" / "meadow"
DEFAULT_CACHE = Path(os.environ.get("NOKEPOM_ASSET_CACHE", Path.home() / ".cache" / "nokepom" / "cc0_assets"))

# Poly Haven cache file suffixes for the maps used, by output name.
SOURCE_SUFFIX = {"albedo": "diff", "normal": "nor_gl"}

IMPORT_TEMPLATE = """[remap]

importer="texture"
type="CompressedTexture2D"

[deps]

source_file="res://{source}"

[params]

compress/mode=0
compress/high_quality=false
compress/lossy_quality=0.7
compress/uastc_level=0
compress/rdo_quality_loss=0.0
compress/hdr_compression=1
compress/normal_map={normal_map}
compress/channel_pack=0
mipmaps/generate=true
mipmaps/limit=-1
roughness/mode=0
roughness/src_normal=""
process/channel_remap/red=0
process/channel_remap/green=1
process/channel_remap/blue=2
process/channel_remap/alpha=3
process/fix_alpha_border=false
process/premult_alpha=false
process/normal_map_invert_y=false
process/hdr_as_srgb=false
process/hdr_clamp_exposure=false
process/size_limit=0
detect_3d/compress_to=0
"""


def find_source(cache: Path, asset_id: str, suffix: str, resolution: str) -> Path:
    """The cached map file: texture assets keep it beside the asset, model assets in a ``textures`` folder."""
    name = f"{asset_id}_{suffix}_{resolution}.jpg"
    for candidate in (cache / "polyhaven" / asset_id / name, cache / "polyhaven" / asset_id / "textures" / name):
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"{name} is missing from {cache / 'polyhaven' / asset_id}: "
                            "run tools/assets/fetch_cc0_assets.py fetch")


def stage(stem: str, asset_id: str, resolution: str, cache: Path, out: Path) -> list[Path]:
    """Copy one asset's maps to ``<stem>_albedo.jpg`` / ``<stem>_normal.jpg`` and write their import files."""
    copied = []
    for role, suffix in SOURCE_SUFFIX.items():
        target = out / f"{stem}_{role}.jpg"
        shutil.copyfile(find_source(cache, asset_id, suffix, resolution), target)
        import_path = target.with_name(target.name + ".import")
        if not import_path.exists():
            resource = target.relative_to(REPO_ROOT).as_posix()
            import_path.write_text(IMPORT_TEMPLATE.format(source=resource, normal_map=int(role == "normal")))
        copied.append(target)
    return copied


def jobs() -> dict[str, str]:
    """Output stem -> asset id for every texture set the project uses."""
    tree_params = json.loads(TREE_PARAMS_PATH.read_text())
    scan_params = json.loads(SCAN_PARAMS_PATH.read_text())
    result = {f"bark_{species}": spec["bark"] for species, spec in tree_params["species"].items()}
    for family in scan_params["families"].values():
        for source in family["sources"]:
            result[f"scan_{source['asset']}"] = source["asset"]
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage the meadow bark and scan textures.")
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    assets = json.loads(MANIFEST_PATH.read_text())["assets"]
    args.out.mkdir(parents=True, exist_ok=True)
    for stem, asset_id in jobs().items():
        for path in stage(stem, asset_id, assets[asset_id]["resolution"], args.cache, args.out):
            print(path.relative_to(REPO_ROOT))


if __name__ == "__main__":
    main()
