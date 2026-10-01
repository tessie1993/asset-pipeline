"""HTTP helpers for the asset pipeline: JSON lookups, size-checked downloads with retries, and
the Blendkit material library.

Downloads (texture sets, HDRIs, thumbnails) go to a cache **outside the repository**, so a pack's
working files never carry library downloads. ``ASSETGEN_CACHE`` overrides the cache folder
(default ``~/.cache/asset-pipeline``).
"""
from __future__ import annotations

import http.client
import json
import os
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any

DEFAULT_CACHE = Path(os.environ.get("ASSETGEN_CACHE", Path.home() / ".cache" / "asset-pipeline"))

# Poly Haven asks API users to identify themselves; some CDNs also reject the default Python agent.
USER_AGENT = "asset-pipeline/1.0 (+https://github.com/tessie1993/asset-pipeline)"
REQUEST_TIMEOUT_S = 120
CHUNK_BYTES = 1 << 20
MAX_ATTEMPTS = 4
RETRY_BACKOFF_BASE_S = 2  # waits 2 s, 4 s, 8 s between attempts

POLYHAVEN_API = "https://api.polyhaven.com"


class FetchError(RuntimeError):
    """A lookup or download failed; the message says which and why."""


def _request(url: str) -> urllib.request.Request:
    return urllib.request.Request(url, headers={"User-Agent": USER_AGENT})


def get_json(url: str) -> Any:
    """The parsed JSON document served at ``url``."""
    try:
        with urllib.request.urlopen(_request(url), timeout=REQUEST_TIMEOUT_S) as response:
            return json.load(response)
    except (OSError, http.client.HTTPException, json.JSONDecodeError) as error:
        raise FetchError(f"GET {url} failed: {error}") from error


def get_bytes(url: str) -> bytes:
    """The body served at ``url``."""
    try:
        with urllib.request.urlopen(_request(url), timeout=REQUEST_TIMEOUT_S) as response:
            return response.read()
    except (OSError, http.client.HTTPException) as error:
        raise FetchError(f"GET {url} failed: {error}") from error


def _download_once(url: str, destination: Path, expected_size: int | None) -> None:
    size = 0
    partial = destination.with_suffix(destination.suffix + ".part")
    try:
        with urllib.request.urlopen(_request(url), timeout=REQUEST_TIMEOUT_S) as response, partial.open("wb") as handle:
            while chunk := response.read(CHUNK_BYTES):
                handle.write(chunk)
                size += len(chunk)
    except (OSError, http.client.HTTPException) as error:
        raise FetchError(f"GET {url} failed after {size} bytes: {error}") from error
    if expected_size is not None and size != expected_size:
        raise FetchError(f"GET {url} returned {size} bytes, expected {expected_size}")
    partial.replace(destination)


def download(url: str, destination: Path, expected_size: int | None = None) -> Path:
    """Download ``url`` to ``destination``, retrying with backoff; returns ``destination``.

    With ``expected_size`` a transfer only counts as complete when it delivered exactly that many
    bytes, so a connection that closes early is retried instead of being kept.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            _download_once(url, destination, expected_size)
            return destination
        except FetchError as error:
            if attempt == MAX_ATTEMPTS:
                raise
            delay = RETRY_BACKOFF_BASE_S ** attempt
            print(f"  attempt {attempt}/{MAX_ATTEMPTS} failed ({error}); retrying in {delay} s")
            time.sleep(delay)
    raise AssertionError("unreachable: the last attempt returns or raises")


def asset_cache_dir(cache: Path, source: str, asset_id: str) -> Path:
    """Folder holding the downloaded files of one library asset."""
    return cache / source / asset_id


# --------------------------------------------------------------------------------- #
# Blendkit (formerly BlenderKit): free CC0 Blender materials, no login needed
# --------------------------------------------------------------------------------- #

BLENDKIT_API = "https://www.blenderkit.com/api/v1"
BLENDKIT_LICENCE = "cc_zero"  # only CC0: the royalty-free licence forbids reselling assets in a pack
BLENDKIT_RESOLUTIONS = ("resolution_2K", "resolution_1K", "blend")  # preferred file, best first


def blendkit_search(words: list[str], limit: int) -> list[dict]:
    """Free CC0 Blendkit materials matching ``words``, best match first."""
    query = "+".join(urllib.parse.quote(word) for word in words)
    url = (f"{BLENDKIT_API}/search/?query={query}+asset_type:material+is_free:true+license:{BLENDKIT_LICENCE}"
           f"&page_size={limit}&dict_parameters=1")
    return get_json(url).get("results", [])


def blendkit_asset(asset_base_id: str) -> dict:
    """The Blendkit search record of one material (by its asset base id)."""
    results = get_json(f"{BLENDKIT_API}/search/?query=asset_base_id:{asset_base_id}&dict_parameters=1").get("results", [])
    if not results:
        raise FetchError(f"Blendkit has no material {asset_base_id}")
    asset = results[0]
    if asset.get("license") != BLENDKIT_LICENCE or not asset.get("isFree"):
        raise FetchError(f"Blendkit material {asset_base_id} is not free CC0 ({asset.get('license')})")
    return asset


def blendkit_download(asset: dict, cache: Path = DEFAULT_CACHE) -> Path:
    """Download a Blendkit material's .blend (2K textures when offered) into the cache, once."""
    files = {entry["fileType"]: entry for entry in asset.get("files", [])}
    kind = next((name for name in BLENDKIT_RESOLUTIONS if name in files), None)
    if kind is None:
        raise FetchError(f"Blendkit material {asset['assetBaseId']} has no downloadable .blend")
    target = asset_cache_dir(cache, "blendkit", asset["assetBaseId"]) / f"{kind}.blend"
    if target.exists():
        return target
    # The download endpoint answers with a signed URL for this "scene"; any uuid will do.
    signed = get_json(f"{files[kind]['downloadUrl']}?scene_uuid={uuid.uuid4()}")["filePath"]
    return download(signed, target, files[kind].get("fileUploadSize") if kind == "blend" else None)
