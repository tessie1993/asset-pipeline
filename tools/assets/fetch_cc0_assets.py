"""Download the CC0 source assets listed in a manifest, pinned by SHA-256.

Raw downloads go to a cache **outside the repository**; only processed, budgeted
outputs are committed. The manifest (``assets/data/meadow/meadow_asset_sources.json``)
is the record of what was used: source, author, licence, page, files and checksums.

Every download is checked against the byte size its source advertises, so a
connection that closes early is retried instead of being accepted as complete.

Commands::

    # Restore every asset from the manifest and verify its checksum.
    python3 tools/assets/fetch_cc0_assets.py fetch

    # Look up an asset on its source, download it, and record it in the manifest.
    python3 tools/assets/fetch_cc0_assets.py add polyhaven texture forrest_ground_01 \\
        --resolution 2k --role ground_leaf_litter
    python3 tools/assets/fetch_cc0_assets.py add ambientcg texture Grass004 \\
        --resolution 2k --role ground_grass

    # Rewrite docs/third-party/meadow-cc0-assets/NOTICE.md from the manifest.
    python3 tools/assets/fetch_cc0_assets.py notice

Manifest schema (``schema_version`` 1)::

    {
      "schema_version": 1,
      "licenses": {"<source>": {"spdx": "CC0-1.0", "url": "<licence page>"}},
      "assets": {
        "<asset id>": {
          "source": "polyhaven" | "ambientcg",
          "kind": "texture" | "model",
          "role": "<what the project uses it for>",
          "resolution": "1k" | "2k" | ...,
          "author": "<credited author(s)>",
          "page_url": "<asset page>",
          "files": [{"name": "<cache file name>", "url": "<download url>",
                     "sha256": "<hex>", "size": <bytes>}]
        }
      }
    }

Environment: ``NOKEPOM_ASSET_CACHE`` overrides the cache directory
(default ``~/.cache/nokepom/cc0_assets``).
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import sys
import time
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = REPO_ROOT / "assets" / "data" / "meadow" / "meadow_asset_sources.json"
DEFAULT_NOTICE = REPO_ROOT / "docs" / "third-party" / "meadow-cc0-assets" / "NOTICE.md"
DEFAULT_CACHE = Path(os.environ.get("NOKEPOM_ASSET_CACHE", Path.home() / ".cache" / "nokepom" / "cc0_assets"))

# Poly Haven asks API users to identify themselves; some CDNs also reject the default Python agent.
USER_AGENT = "nokepom-asset-fetch/1.0 (+https://github.com/tessie1993/nokepom)"
REQUEST_TIMEOUT_S = 120
CHUNK_BYTES = 1 << 20
MAX_ATTEMPTS = 4
RETRY_BACKOFF_BASE_S = 2  # waits 2 s, 4 s, 8 s between attempts
SCHEMA_VERSION = 1

POLYHAVEN_API = "https://api.polyhaven.com"
POLYHAVEN_PAGE = "https://polyhaven.com/a/{asset_id}"
AMBIENTCG_API = "https://ambientcg.com/api/v2/full_json"
AMBIENTCG_PAGE = "https://ambientcg.com/view?id={asset_id}"

# Poly Haven texture map keys that the pipeline uses (see /files/<id> of a texture asset).
POLYHAVEN_TEXTURE_MAPS = ("Diffuse", "nor_gl", "arm", "Displacement")
POLYHAVEN_TEXTURE_FORMAT = "jpg"


class FetchError(RuntimeError):
    """A download, lookup or checksum failed."""


@dataclass(frozen=True)
class RemoteFile:
    """One downloadable file as advertised by a source's API."""

    name: str
    url: str
    size: int


# --------------------------------------------------------------------------------- #
# HTTP and hashing
# --------------------------------------------------------------------------------- #

def _request(url: str) -> urllib.request.Request:
    return urllib.request.Request(url, headers={"User-Agent": USER_AGENT})


def get_json(url: str) -> Any:
    """Return the parsed JSON document served at ``url``."""
    try:
        with urllib.request.urlopen(_request(url), timeout=REQUEST_TIMEOUT_S) as response:
            return json.load(response)
    except (OSError, http.client.HTTPException, json.JSONDecodeError) as error:
        raise FetchError(f"GET {url} failed: {error}") from error


def _download_once(url: str, destination: Path, expected_size: int) -> str:
    """Stream ``url`` to ``destination`` once; return its sha256 hex digest."""
    digest = hashlib.sha256()
    size = 0
    partial = destination.with_suffix(destination.suffix + ".part")
    try:
        with urllib.request.urlopen(_request(url), timeout=REQUEST_TIMEOUT_S) as response, partial.open("wb") as handle:
            while chunk := response.read(CHUNK_BYTES):
                digest.update(chunk)
                handle.write(chunk)
                size += len(chunk)
    except (OSError, http.client.HTTPException) as error:
        raise FetchError(f"GET {url} failed after {size} bytes: {error}") from error
    if size != expected_size:
        raise FetchError(f"GET {url} returned {size} bytes, expected {expected_size}")
    partial.replace(destination)
    return digest.hexdigest()


def download(url: str, destination: Path, expected_size: int) -> str:
    """Download ``url`` to ``destination``, retrying with backoff; return its sha256 hex digest.

    A transfer only counts as complete when it delivered exactly ``expected_size`` bytes.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return _download_once(url, destination, expected_size)
        except FetchError as error:
            if attempt == MAX_ATTEMPTS:
                raise
            delay = RETRY_BACKOFF_BASE_S ** attempt
            print(f"  attempt {attempt}/{MAX_ATTEMPTS} failed ({error}); retrying in {delay} s")
            time.sleep(delay)
    raise AssertionError("unreachable: the last attempt returns or raises")


def sha256_of(path: Path) -> str:
    """Return the SHA-256 hex digest of the file at ``path``."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


# --------------------------------------------------------------------------------- #
# Manifest
# --------------------------------------------------------------------------------- #

def load_manifest(path: Path) -> dict[str, Any]:
    """Return the manifest at ``path`` (an empty one when the file does not exist yet)."""
    if not path.exists():
        return {"schema_version": SCHEMA_VERSION, "licenses": {}, "assets": {}}
    with path.open(encoding="utf-8") as handle:
        manifest = json.load(handle)
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise FetchError(f"{path}: unsupported schema_version {manifest.get('schema_version')!r}")
    return manifest


def save_manifest(path: Path, manifest: dict[str, Any]) -> None:
    """Write ``manifest`` to ``path`` with a trailing newline."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


# --------------------------------------------------------------------------------- #
# Source lookups: each returns (author, page url, files)
# --------------------------------------------------------------------------------- #

def lookup_polyhaven(kind: str, asset_id: str, resolution: str) -> tuple[str, str, list[RemoteFile]]:
    """Resolve a Poly Haven asset to its credited authors, page and files at ``resolution``."""
    info = get_json(f"{POLYHAVEN_API}/info/{asset_id}")
    author = ", ".join(sorted(info["authors"]))
    files = get_json(f"{POLYHAVEN_API}/files/{asset_id}")
    page = POLYHAVEN_PAGE.format(asset_id=asset_id)
    if kind == "texture":
        entries = [files[map_key][resolution][POLYHAVEN_TEXTURE_FORMAT] for map_key in POLYHAVEN_TEXTURE_MAPS]
        return author, page, [RemoteFile(Path(entry["url"]).name, entry["url"], entry["size"]) for entry in entries]
    gltf = files["gltf"][resolution]["gltf"]
    listing = [RemoteFile(f"{asset_id}.gltf", gltf["url"], gltf["size"])]
    listing += [RemoteFile(name, entry["url"], entry["size"]) for name, entry in gltf["include"].items()]
    return author, page, listing


def lookup_ambientcg(kind: str, asset_id: str, resolution: str) -> tuple[str, str, list[RemoteFile]]:
    """Resolve an ambientCG material to its page and its ``<resolution>-JPG`` archive."""
    if kind != "texture":
        raise FetchError("ambientCG assets are materials: use kind 'texture'")
    result = get_json(f"{AMBIENTCG_API}?id={asset_id}&include=downloadData")
    assets = result.get("foundAssets", [])
    if not assets:
        raise FetchError(f"ambientCG has no asset {asset_id!r}")
    wanted = f"{resolution.upper()}-JPG"
    downloads = assets[0]["downloadFolders"]["default"]["downloadFiletypeCategories"]["zip"]["downloads"]
    for entry in downloads:
        if entry["attribute"] == wanted:
            archive = RemoteFile(entry["fileName"], entry["downloadLink"], entry["size"])
            return "ambientCG", AMBIENTCG_PAGE.format(asset_id=asset_id), [archive]
    available = sorted(entry["attribute"] for entry in downloads)
    raise FetchError(f"ambientCG {asset_id} has no {wanted} download (available: {available})")


LOOKUPS = {"polyhaven": lookup_polyhaven, "ambientcg": lookup_ambientcg}
LICENSES = {
    "polyhaven": {"spdx": "CC0-1.0", "url": "https://polyhaven.com/license"},
    "ambientcg": {"spdx": "CC0-1.0", "url": "https://docs.ambientcg.com/license/"},
}


# --------------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------------- #

def asset_cache_dir(cache: Path, source: str, asset_id: str) -> Path:
    """Directory holding the downloaded files of one asset."""
    return cache / source / asset_id


def unpack_archives(directory: Path) -> None:
    """Extract every ``.zip`` in ``directory`` next to itself (ambientCG ships one zip per material)."""
    for archive in directory.glob("*.zip"):
        try:
            with zipfile.ZipFile(archive) as bundle:
                bundle.extractall(directory / archive.stem)
        except zipfile.BadZipFile as error:
            raise FetchError(f"{archive} is not a valid zip archive: {error}") from error


def fetch_asset(cache: Path, source: str, asset_id: str, entry: dict[str, Any]) -> None:
    """Download the files of one manifest entry and verify each against its pinned checksum."""
    directory = asset_cache_dir(cache, source, asset_id)
    for file in entry["files"]:
        target = directory / file["name"]
        if target.exists() and sha256_of(target) == file["sha256"]:
            continue
        digest = download(file["url"], target, file["size"])
        if digest != file["sha256"]:
            target.unlink()
            raise FetchError(f"{asset_id}/{file['name']}: sha256 {digest} does not match the manifest ({file['sha256']})")
    unpack_archives(directory)


def command_fetch(args: argparse.Namespace) -> None:
    manifest = load_manifest(args.manifest)
    for asset_id, entry in manifest["assets"].items():
        print(f"fetch {entry['source']}/{asset_id}")
        fetch_asset(args.cache, entry["source"], asset_id, entry)
    print(f"OK: {len(manifest['assets'])} assets verified in {args.cache}")


def command_add(args: argparse.Namespace) -> None:
    manifest = load_manifest(args.manifest)
    author, page_url, listing = LOOKUPS[args.source](args.kind, args.asset_id, args.resolution)
    directory = asset_cache_dir(args.cache, args.source, args.asset_id)
    files = []
    for remote in listing:
        print(f"download {args.asset_id}/{remote.name}")
        digest = download(remote.url, directory / remote.name, remote.size)
        files.append({"name": remote.name, "url": remote.url, "sha256": digest, "size": remote.size})
    unpack_archives(directory)
    manifest["licenses"][args.source] = LICENSES[args.source]
    manifest["assets"][args.asset_id] = {
        "source": args.source,
        "kind": args.kind,
        "role": args.role,
        "resolution": args.resolution,
        "author": author,
        "page_url": page_url,
        "files": files,
    }
    manifest["assets"] = dict(sorted(manifest["assets"].items()))
    save_manifest(args.manifest, manifest)
    print(f"recorded {args.asset_id} in {args.manifest}")


def command_notice(args: argparse.Namespace) -> None:
    manifest = load_manifest(args.manifest)
    lines = [
        f"# {args.manifest.stem.removesuffix('_asset_sources').replace('_', ' ').capitalize()} CC0 assets",
        "",
        "Generated by `tools/assets/fetch_cc0_assets.py notice` from",
        f"`{args.manifest.relative_to(REPO_ROOT)}`. Do not edit by hand.",
        "",
        "Every asset below is released under CC0 1.0 by its source. Attribution is not required;",
        "it is listed so the provenance of each processed file in the repository is traceable.",
        "",
        "| Asset | Source | Author | Licence | Used for |",
        "|---|---|---|---|---|",
    ]
    for asset_id, entry in manifest["assets"].items():
        licence = manifest["licenses"][entry["source"]]
        lines.append(
            f"| [{asset_id}]({entry['page_url']}) | {entry['source']} | {entry['author']} "
            f"| [{licence['spdx']}]({licence['url']}) | {entry['role']} |"
        )
    args.notice.parent.mkdir(parents=True, exist_ok=True)
    args.notice.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {args.notice}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("fetch", help="download and verify every asset in the manifest").set_defaults(run=command_fetch)

    add = commands.add_parser("add", help="look up, download and record one asset")
    add.add_argument("source", choices=sorted(LOOKUPS))
    add.add_argument("kind", choices=("texture", "model"))
    add.add_argument("asset_id")
    add.add_argument("--resolution", required=True, help="e.g. 2k")
    add.add_argument("--role", required=True, help="what the project uses the asset for")
    add.set_defaults(run=command_add)

    notice = commands.add_parser("notice", help="write the provenance table from the manifest")
    notice.add_argument("--notice", type=Path, default=DEFAULT_NOTICE)
    notice.set_defaults(run=command_notice)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        args.run(args)
    except FetchError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
