#!/usr/bin/env python3
"""Pack bookkeeping for the image-to-assets pipeline (``.claude/skills/image-to-assets``).

A pack is the image the user gives and the objects chosen from it. Everything about a pack lives
in ``design/asset-packs/<pack>/``: ``pack.json`` (objects, art style, Canva ids, each object's
reference images and recorded views), the source image, ``canva/NN_<id>.png`` (Canva's drawing of
each object) or, in a pack that skips Canva, ``references/`` (the user's own reference images).
This tool keeps that manifest and prints the texts the pipeline sends (the Canva prompt, the
builder brief) from ``tools/assetgen/templates/``, so no step is typed from memory.

Nothing here fixes what an object is, how it looks, how big it is or from which angles it is seen:
the objects and the look come from the image and the user's answers; each builder analyses its
reference and records the views it shows (``views``) and the triangle budget it builds to
(``budget``), unless the user gave one.

Usage::

    python3 tools/assetgen/pack.py init <pack> <image> [--skip-canva]
    python3 tools/assetgen/pack.py style <pack> "<art style in the user's words>"
    python3 tools/assetgen/pack.py add <pack> <id> --name N --where W --details D \
        [--mount floor|wall] [--reference IMAGE ...] [--budget TRIANGLES]
    python3 tools/assetgen/pack.py run-start <pack>
    python3 tools/assetgen/pack.py prompt <pack> <id>
    python3 tools/assetgen/pack.py canva <pack> [--source-media ID] [--design ID] [--transaction ID]
    python3 tools/assetgen/pack.py record <pack> <id> (--media ID [--job ID] | --refused REASON)
    python3 tools/assetgen/pack.py cutout <pack> <id> (--media ID | --failed REASON)
    python3 tools/assetgen/pack.py sheets <pack>
    python3 tools/assetgen/pack.py canva-calls <pack> <stage> [--page-ids ID ...]
    python3 tools/assetgen/pack.py canva-download <pack> <url> ...
    python3 tools/assetgen/pack.py brief <pack> <id>
    python3 tools/assetgen/pack.py views <pack> <id> --view REF AZIMUTH ELEVATION X0 Y0 X1 Y1 [--view ...] \
        [--lens MM | --ortho]
    python3 tools/assetgen/pack.py skills-list
    python3 tools/assetgen/pack.py skills <pack> <id> (<skill name> ... | --none)
    python3 tools/assetgen/pack.py budget <pack> <id> <triangles> --why "<reason>"
    python3 tools/assetgen/pack.py kit-api
    python3 tools/assetgen/pack.py material-search <words...> [--previews DIR] [--limit N]
    python3 tools/assetgen/pack.py done <pack> <id>
    python3 tools/assetgen/pack.py critic-brief <pack> <id>
    python3 tools/assetgen/pack.py reviewed <pack> <id> ACCEPT|REFINE|REQUEST-INPUT
    python3 tools/assetgen/pack.py accept <pack> <id>
    python3 tools/assetgen/pack.py reopen <pack> <id>
    python3 tools/assetgen/pack.py status <pack>
    python3 tools/assetgen/pack.py run-end
    python3 tools/assetgen/pack.py export <pack> <folder outside the repository>
    python3 tools/assetgen/pack.py discard <pack>
"""
from __future__ import annotations

import argparse
import ast
import datetime
import hashlib
import json
import re
import shutil
import sys
import urllib.parse
from pathlib import Path
from string import Template

sys.path.insert(0, str(Path(__file__).resolve().parent))
import downloads  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = Path(__file__).resolve().parent / "templates"

PACKS_DIR = Path("design/asset-packs")
GENERATORS_DIR = Path("tools/blender/assetgen/packs")
MODELS_DIR = Path("assets/models")
EVIDENCE_DIR = Path("production/qa/evidence")
KIT = Path("tools/blender/assetgen/kit.py")
KIT_README = Path("tools/blender/assetgen/README.md")
BLENDER_NOTES = Path("tools/blender/assetgen/blender-5.2-notes.md")
CV_TOOL = Path("tools/assetgen/cv.py")
SKILLS_DIR = Path(".claude/skills")
RUN_LOCK = Path(".scratch/assetgen/run.json")  # read by the hooks in .claude/hooks/
PREVIEWS_DIR = Path(".scratch/assetgen/previews")

ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp")
# Where the model's origin goes: the centre of its base, or the centre of its back for things
# that hang on a wall.
MOUNTS = {"floor": "bottom", "wall": "back"}
# Words that describe a look rather than an object. The look comes only from the user's art style
# (`style`), so an object's name, place and details must not carry one into the Canva prompt.
LOOK_WORDS = ("3d", "3-d", "render", "rendered", "realistic", "photorealistic", "hyperrealistic", "photoreal",
              "stylized", "stylised", "cartoon", "cartoony", "toon", "cute", "cosy", "cozy", "low poly",
              "low-poly", "lowpoly", "high poly", "anime", "chibi", "pixar", "cinematic")
LOOK_PATTERN = re.compile(r"(?<![a-z0-9])(" + "|".join(re.escape(word) for word in LOOK_WORDS) + r")(?![a-z0-9])")
# Canva is asked for a landscape image (several views side by side); each generated image is placed
# on its own page of this size for the full-size export. The views in it are found by the builder.
CANVA_ASPECT_RATIO = "LANDSCAPE_16_9"
CANVA_PAGE = (1680, 945)
MIN_VIEW_PX = 16
DEFAULT_LENS_MM = 85.0  # the renders' camera unless the builder records another lens or --ortho
BUILD_CYCLES = 8  # the standard number of build -> render -> compare cycles per object
# Context budget: a builder makes at most this many cycle builds (plus one final build); then it writes
# a handoff in its notes and a fresh builder continues from them, so no builder's context fills up
# with every earlier cycle's images and code.
BUILDS_PER_BUILDER = 5
# Fresh-context reviews: after a builder's final build a critic that did not build the object judges
# it against the reference; a REFINE review goes back to a builder, at most this many rounds.
CRITIC_ROUNDS = 3
CRITIC_ROUTES = ("ACCEPT", "REFINE", "REQUEST-INPUT")
AGENTS_DIR = Path(".scratch/assetgen/agents")  # per-builder build counts, kept by the build gate hook

POLYHAVEN_ASSETS = f"{downloads.POLYHAVEN_API}/assets?t=textures"
AMBIENTCG_SEARCH = ("https://ambientcg.com/api/v2/full_json?type=Material&include=imageData"
                    "&limit={limit}&q={query}")
AMBIENTCG_PREVIEW = "256-PNG"
CGBOOKCASE_CATALOG = "https://www.cgbookcase.com/api/textures"
CGBOOKCASE_THUMBNAIL = "https://cgbookcase.b-cdn.net/textures/thumbnails/{name}_1K/{name}_1K_BaseColor.png?width=256"
CGBOOKCASE_FILES = ("Base_Color", "Normal", "Roughness")  # the maps kit.material needs
CATALOG_DIR = Path(".scratch/assetgen/catalogs")
CATALOG_MAX_AGE_S = 24 * 3600
SEARCH_LIMIT = 6
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
CANVA_STAGES = ("create", "open", "add-pages", "read-pages", "place", "check", "commit", "export")
BLANK_DESIGN_BRIEF = ("A completely blank one-page landscape design with a plain white background and "
                      "no text, no images and no decoration. It is only used to place existing images and "
                      "download them.")

# The analysis sections of a builder's notes (templates/builder_notes.md); each must have content
# before the first build (the build gate hook checks it).
ANALYSIS_SECTIONS = ("What it is", "Views", "Size and proportions", "Close observation", "Parts inventory",
                     "Materials and shaders", "Details and nuances", "Skills, add-ons and tools", "Build plan")
REPORT_SECTION = "Report"


class PackError(RuntimeError):
    """A pack command cannot be carried out; the message says why."""


# --------------------------------------------------------------------------------- #
# Manifest and paths
# --------------------------------------------------------------------------------- #

def pack_dir(root: Path, pack: str) -> Path:
    """Folder holding ``pack``'s manifest, source image and reference images."""
    return root / PACKS_DIR / pack


def load(root: Path, pack: str) -> dict:
    """Return ``pack``'s manifest."""
    path = pack_dir(root, pack) / "pack.json"
    if not path.exists():
        raise PackError(f"{PACKS_DIR / pack / 'pack.json'} not found; run: pack.py init {pack} <image>")
    return json.loads(path.read_text(encoding="utf-8"))


def save(root: Path, manifest: dict) -> None:
    """Write ``manifest`` back to its ``pack.json``."""
    path = pack_dir(root, manifest["pack"]) / "pack.json"
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def find_object(manifest: dict, object_id: str) -> dict:
    """The object ``object_id`` of ``manifest``."""
    for entry in manifest["objects"]:
        if entry["id"] == object_id:
            return entry
    raise PackError(f"{manifest['pack']} has no object {object_id!r}; add it with pack.py add")


def sheet_name(entry: dict) -> str:
    """File name of the object's Canva image: ``NN_<id>.png``."""
    return f"{entry['number']:02d}_{entry['id']}.png"


def evidence_dir(root: Path, pack: str, object_id: str) -> Path:
    """Folder of an object's renders, CV reports, notes and Godot screenshots."""
    return root / EVIDENCE_DIR / pack / object_id


def notes_path(root: Path, pack: str, object_id: str) -> Path:
    return evidence_dir(root, pack, object_id) / f"{object_id}_notes.md"


def generator_path(root: Path, pack: str, object_id: str) -> Path:
    return root / GENERATORS_DIR / pack / f"{object_id}.py"


def glb_path(root: Path, pack: str, object_id: str) -> Path:
    return root / MODELS_DIR / pack / f"{object_id}.glb"


def build_report_path(root: Path, pack: str, object_id: str) -> Path:
    """Written by the kit after every build that renders: build number, views, BUILT report."""
    return evidence_dir(root, pack, object_id) / f"{object_id}_build.json"


def cv_report_path(root: Path, pack: str, object_id: str) -> Path:
    """Written by ``cv.py compare`` after every build: the render compared with the reference."""
    return evidence_dir(root, pack, object_id) / f"{object_id}_cv.json"


def cv_reference_path(root: Path, pack: str, object_id: str) -> Path:
    """Written by ``cv.py measure``: the reference's views measured."""
    return evidence_dir(root, pack, object_id) / f"{object_id}_cv_reference.json"


def review_path(root: Path, pack: str, object_id: str, number: int) -> Path:
    """The critic's review of round ``number``."""
    return evidence_dir(root, pack, object_id) / f"{object_id}_review_{number}.md"


def read_json(path: Path) -> dict | None:
    """The JSON object at ``path``, or None when it is missing or unreadable."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _check_id(value: str, what: str) -> str:
    if not ID_PATTERN.match(value):
        raise PackError(f"{what} {value!r} must be snake_case: lower-case letters, digits and _")
    return value


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------------- #
# Images
# --------------------------------------------------------------------------------- #

def image_size(path: Path) -> tuple[int, int]:
    """Width and height of a PNG, JPEG or WebP image, read from its header."""
    data = Path(path).read_bytes()
    if data.startswith(PNG_SIGNATURE) and data[12:16] == b"IHDR":
        return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    if data[:2] == b"\xff\xd8":
        index = 2
        while index + 4 <= len(data):
            if data[index] != 0xFF:
                index += 1
                continue
            marker = data[index + 1]
            if marker == 0xFF:
                index += 1
                continue
            if marker in (0x01, 0xD8) or 0xD0 <= marker <= 0xD7:
                index += 2
                continue
            length = int.from_bytes(data[index + 2:index + 4], "big")
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                height = int.from_bytes(data[index + 5:index + 7], "big")
                width = int.from_bytes(data[index + 7:index + 9], "big")
                return width, height
            index += 2 + length
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        chunk = data[12:16]
        if chunk == b"VP8 ":
            return (int.from_bytes(data[26:28], "little") & 0x3FFF,
                    int.from_bytes(data[28:30], "little") & 0x3FFF)
        if chunk == b"VP8L":
            bits = int.from_bytes(data[21:25], "little")
            return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
        if chunk == b"VP8X":
            return int.from_bytes(data[24:27], "little") + 1, int.from_bytes(data[27:30], "little") + 1
    raise PackError(f"{path} is not a PNG, JPEG or WebP image")


def _check_image(path: Path, what: str) -> Path:
    path = Path(path)
    if not path.is_file():
        raise PackError(f"{what} {path} not found")
    if path.suffix.lower() not in IMAGE_SUFFIXES:
        raise PackError(f"{what} {path} must be one of {', '.join(IMAGE_SUFFIXES)}")
    image_size(path)
    return path


def _add_reference(root: Path, manifest: dict, object_id: str, image: Path, index: int) -> str:
    """Copy one reference image into the pack (once per distinct file); returns its path relative to
    the pack folder. The pack's own source image is used as it is."""
    folder = pack_dir(root, manifest["pack"])
    digest = _sha256(image)
    if digest == _sha256(folder / manifest["source"]):
        return manifest["source"]
    for existing in sorted((folder / "references").glob("*")):
        if existing.is_file() and _sha256(existing) == digest:
            return str(existing.relative_to(folder))
    target = folder / "references" / f"{object_id}_{index}{image.suffix.lower()}"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(image, target)
    return str(target.relative_to(folder))


# --------------------------------------------------------------------------------- #
# Pack, objects, style
# --------------------------------------------------------------------------------- #

def init(root: Path, pack: str, image: Path, skip_canva: bool = False) -> dict:
    """Create ``pack`` from the source ``image``: its folder, a copy of the image and an empty
    manifest. With ``skip_canva`` every object is built from the user's own reference images."""
    _check_id(pack, "pack name")
    folder = pack_dir(root, pack)
    if (folder / "pack.json").exists():
        raise PackError(f"pack {pack} already exists")
    image = _check_image(image, "source image")
    (folder / ("references" if skip_canva else "canva")).mkdir(parents=True, exist_ok=True)
    source_name = "source" + image.suffix.lower()
    shutil.copyfile(image, folder / source_name)
    manifest = {"pack": pack, "source": source_name, "skip_canva": skip_canva, "canva": {}, "objects": []}
    save(root, manifest)
    return manifest


def look_words(text: str) -> list[str]:
    """The words of :data:`LOOK_WORDS` found in ``text``."""
    return sorted({match.group(1) for match in LOOK_PATTERN.finditer(text.lower())})


def add(root: Path, pack: str, object_id: str, name: str, where: str, details: str,
        mount: str = "floor", references: list[Path] | None = None, budget: int | None = None) -> dict:
    """Add an object chosen from the source image; it gets the next number.

    In a pack that skips Canva the object needs at least one reference image (it may be the
    source image itself, or several images of the object). ``budget`` is a triangle budget the
    user gave; without one the builder decides it from the object's detail."""
    manifest = load(root, pack)
    _check_id(object_id, "object id")
    if any(entry["id"] == object_id for entry in manifest["objects"]):
        raise PackError(f"{pack} already has an object {object_id!r}")
    if mount not in MOUNTS:
        raise PackError(f"mount must be one of {sorted(MOUNTS)}, not {mount!r}")
    found = look_words(" ".join((name, where, details)))
    if found:
        raise PackError(f"name, where and details describe what the object is, where it is and its parts, "
                        f"materials and colours; the look comes only from the art style (pack.py style). "
                        f"Leave out: {', '.join(found)}")
    references = [_check_image(Path(path), "reference image") for path in (references or [])]
    if manifest["skip_canva"] and not references:
        raise PackError(f"{pack} skips Canva: give the object's reference image(s) with --reference")
    if not manifest["skip_canva"] and references:
        raise PackError(f"{pack} uses Canva: its reference is the Canva image; --reference is for packs "
                        "made with --skip-canva")
    if budget is not None and budget <= 0:
        raise PackError(f"the triangle budget must be a positive number, not {budget}")
    entry = {
        "id": object_id, "number": len(manifest["objects"]) + 1, "name": name, "where": where,
        "details": details, "mount": mount,
        "references": [_add_reference(root, manifest, object_id, path, index)
                       for index, path in enumerate(references, start=1)],
        "views": [], "budget": budget, "budget_why": "given by the user" if budget else None,
    }
    if not manifest["skip_canva"]:
        entry["canva"] = {}
    manifest["objects"].append(entry)
    save(root, manifest)
    return entry


def set_style(root: Path, pack: str, style: str) -> str:
    """Record the art style the user asked for; every Canva prompt and brief of the pack uses it."""
    style = " ".join(style.split())
    if not style:
        raise PackError("the art style is empty; ask the user which art style they want")
    manifest = load(root, pack)
    manifest["style"] = style
    save(root, manifest)
    return style


# --------------------------------------------------------------------------------- #
# Canva
# --------------------------------------------------------------------------------- #

def _canva_pack(root: Path, pack: str) -> dict:
    manifest = load(root, pack)
    if manifest["skip_canva"]:
        raise PackError(f"{pack} skips Canva: no Canva step runs for it")
    return manifest


def prompt(root: Path, pack: str, object_id: str) -> str:
    """The Canva prompt for one object, sent with the source image as the reference."""
    manifest = _canva_pack(root, pack)
    if not manifest.get("style"):
        raise PackError(f"{pack} has no art style yet; ask the user, then run pack.py style {pack} \"<style>\"")
    entry = find_object(manifest, object_id)
    text = Template((TEMPLATES / "canva_prompt.txt").read_text(encoding="utf-8"))
    return text.substitute(name=entry["name"], details=entry["details"], where=entry["where"],
                           style=manifest["style"]).strip()


def set_canva(root: Path, pack: str, source_media: str | None, design: str | None,
              transaction: str | None = None) -> dict:
    """Record the pack-level Canva ids: the uploaded source image, the scratch export design and
    the design's open editing transaction."""
    manifest = _canva_pack(root, pack)
    if source_media:
        manifest["canva"]["source_media_id"] = source_media
    if design:
        manifest["canva"]["export_design_id"] = design
    if transaction:
        manifest["canva"]["transaction_id"] = transaction
    save(root, manifest)
    return manifest["canva"]


def record(root: Path, pack: str, object_id: str, media: str | None, job: str | None,
           refused: str | None) -> dict:
    """Record an object's Canva result: its generated image's media id, or Canva's refusal."""
    if bool(media) == bool(refused):
        raise PackError("pass exactly one of --media or --refused")
    manifest = _canva_pack(root, pack)
    entry = find_object(manifest, object_id)
    entry["canva"] = {"media_id": media, "job_id": job} if media else {"refused": refused}
    save(root, manifest)
    return entry["canva"]


def cutout(root: Path, pack: str, object_id: str, media: str | None, failed: str | None) -> dict:
    """Record the background-removed copy of an object's generated image (Canva
    ``remove-background``), or why removing the background failed."""
    if bool(media) == bool(failed):
        raise PackError("pass exactly one of --media or --failed")
    manifest = _canva_pack(root, pack)
    entry = find_object(manifest, object_id)
    if not entry["canva"].get("media_id"):
        raise PackError(f"{object_id} has no generated image to cut out; record it first")
    if media:
        entry["canva"].pop("cutout_failed", None)
        entry["canva"]["cutout_media_id"] = media
    else:
        entry["canva"].pop("cutout_media_id", None)
        entry["canva"]["cutout_failed"] = failed
    save(root, manifest)
    return entry["canva"]


def sheets(root: Path, pack: str) -> list[dict]:
    """Per object that Canva made an image for, in number order: the media id to export (the
    background-removed copy; the generated image only where removal failed and that was recorded),
    the page it gets in the scratch export design (page 1 is the design's own blank page, so object
    pages start at 2, added in this order) and the file its export is saved as."""
    manifest = _canva_pack(root, pack)
    folder = pack_dir(root, pack) / "canva"
    rows, missing = [], []
    for entry in manifest["objects"]:
        canva = entry["canva"]
        if not canva.get("media_id"):
            continue
        media = canva.get("cutout_media_id") or (canva["media_id"] if canva.get("cutout_failed") else None)
        if media is None:
            missing.append(entry["id"])
            continue
        rows.append({"page": len(rows) + 2, "id": entry["id"], "media_id": media,
                     "file": str((folder / sheet_name(entry)).relative_to(root))})
    if missing:
        raise PackError(f"background not removed yet for {', '.join(missing)}: run remove-background, then "
                        "pack.py cutout <pack> <id> --media <id> (or --failed <reason>)")
    return rows


def _canva_id(manifest: dict, key: str, flag: str) -> str:
    value = manifest["canva"].get(key)
    if not value:
        raise PackError(f"record it first: pack.py canva {manifest['pack']} {flag} <id>")
    return value


def canva_calls(root: Path, pack: str, stage: str, page_ids: list[str] | None = None) -> list[dict]:
    """The exact Canva calls of one stage of the full-size download, as ``{"tool", "arguments"}``.

    No Canva tool downloads a media file; ``export-design`` exports designs, one PNG per page. So
    each generated image is placed, unedited and filling its page, on its own page of one blank
    scratch design, and those pages are exported. Stages, in order: create, open, add-pages,
    read-pages, place, check, commit, export.
    """
    if stage not in CANVA_STAGES:
        raise PackError(f"stage must be one of {CANVA_STAGES}, not {stage!r}")
    manifest = _canva_pack(root, pack)
    rows = sheets(root, pack)
    pages = [row["page"] for row in rows]
    width, height = CANVA_PAGE
    if stage == "create":
        return [{"tool": "create-design",
                 "arguments": {"brief": BLANK_DESIGN_BRIEF, "format": "Presentation (16:9)"}}]
    design = _canva_id(manifest, "export_design_id", "--design")
    if stage == "open":
        return [{"tool": "read-design", "arguments": {
            "design_id": design, "open_transaction": True,
            "filter": {"fields": ["design_metadata", "page_metadata"]}}}]
    if stage == "export":
        return [{"tool": "get-export-formats", "arguments": {"design_id": design}},
                {"tool": "export-design", "arguments": {"design_id": design, "format": {
                    "type": "png", "pages": pages, "width": width, "height": height,
                    "lossless": True, "export_quality": "pro", "transparent_background": True}}}]
    transaction = _canva_id(manifest, "transaction_id", "--transaction")
    if stage == "add-pages":
        return [{"tool": "edit-design", "arguments": {
            "transaction_id": transaction, "page_index": 1, "finalize": "keep_open",
            "operations": [{"type": "add_page", "width": width, "height": height,
                            "title": Path(row["file"]).stem} for row in rows]}}]
    if stage in ("read-pages", "check"):
        return [{"tool": "read-design", "arguments": {
            "design_id": design, "transaction_id": transaction,
            "filter": {"fields": ["design_content"], "page_indices": pages}}}]
    if stage == "commit":
        return [{"tool": "edit-design", "arguments": {"transaction_id": transaction, "finalize": "commit"}}]
    if not page_ids or len(page_ids) != len(rows):
        raise PackError(f"place needs --page-ids with {len(rows)} ids, in page order {pages} "
                        "(from the read-pages result)")
    return [{"tool": "edit-design", "arguments": {
        "transaction_id": transaction, "page_index": row["page"], "finalize": "keep_open",
        "operations": [{"type": "insert_fill", "page_id": page_id, "asset_type": "image",
                        "asset_id": row["media_id"], "alt_text": Path(row["file"]).stem,
                        "left": 0, "top": 0, "width": width, "height": height}]}}
        for row, page_id in zip(rows, page_ids)]


def canva_download(root: Path, pack: str, urls: list[str]) -> list[str]:
    """Download the export URLs (in page order) to the objects' Canva image files, each of which
    becomes that object's reference; returns the files written."""
    manifest = _canva_pack(root, pack)
    rows = sheets(root, pack)
    if len(urls) != len(rows):
        raise PackError(f"expected {len(rows)} export URLs (pages {[row['page'] for row in rows]}), got {len(urls)}")
    payloads = []
    for row, url in zip(rows, urls):
        data = downloads.get_bytes(url)
        if not data.startswith(PNG_SIGNATURE):
            raise PackError(f"{row['id']}: the export is not a PNG; nothing saved")
        payloads.append((row, data))
    folder = pack_dir(root, pack)
    for row, data in payloads:
        (root / row["file"]).write_bytes(data)
        entry = find_object(manifest, row["id"])
        entry["references"] = [str((root / row["file"]).relative_to(folder))]
        entry["views"] = []  # a new image: its views are recorded again
    save(root, manifest)
    return [row["file"] for row in rows]


# --------------------------------------------------------------------------------- #
# Builder set-up: views, skills, budget
# --------------------------------------------------------------------------------- #

def reference_paths(root: Path, pack: str, entry: dict) -> list[Path]:
    """The object's reference images, absolute."""
    return [pack_dir(root, pack) / name for name in entry.get("references", [])]


def set_views(root: Path, pack: str, object_id: str, views: list[list[float]], lens: float | None = None,
              ortho: bool = False) -> list[dict]:
    """Record every view of the object its reference images show: per view the reference image
    (1-based), the azimuth (degrees: 0 front, 90 seen from the right, 180 back, 270 from the left),
    the elevation (degrees above the horizon the view is seen from) and the box around the object in
    that image (pixels, x0 y0 x1 y1 from the top-left). Replaces the views recorded before.

    The camera the renders use matches how the reference was made: ``ortho`` for a drawing without
    perspective, else a ``lens`` in mm (35 strong perspective, 85 the default, 200 nearly flat)."""
    manifest = load(root, pack)
    entry = find_object(manifest, object_id)
    images = reference_paths(root, pack, entry)
    if not images:
        raise PackError(f"{object_id} has no reference image yet")
    if not views:
        raise PackError("give at least one --view REF AZIMUTH ELEVATION X0 Y0 X1 Y1")
    recorded = []
    for values in views:
        if len(values) != 7:
            raise PackError(f"a view is REF AZIMUTH ELEVATION X0 Y0 X1 Y1, got {values}")
        ref, azimuth, elevation, *box = values
        if int(ref) != ref or not 1 <= ref <= len(images):
            raise PackError(f"REF must be the reference image number, 1 to {len(images)}, not {ref}")
        if not -89.0 <= elevation <= 89.0:
            raise PackError(f"elevation must be between -89 and 89 degrees, not {elevation}")
        image = images[int(ref) - 1]
        width, height = image_size(image)
        x0, y0, x1, y1 = (int(round(value)) for value in box)
        if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
            raise PackError(f"box {x0} {y0} {x1} {y1} must lie inside {image.name} ({width} x {height}) "
                            "with x0 < x1 and y0 < y1")
        if x1 - x0 < MIN_VIEW_PX or y1 - y0 < MIN_VIEW_PX:
            raise PackError(f"box {x0} {y0} {x1} {y1} is smaller than {MIN_VIEW_PX} pixels")
        recorded.append({"ref": int(ref), "image": entry["references"][int(ref) - 1],
                         "azimuth": round(azimuth % 360.0, 2), "elevation": round(elevation, 2),
                         "box": [x0, y0, x1, y1]})
    if ortho and lens:
        raise PackError("give --lens or --ortho, not both")
    if lens is not None and not 10.0 <= lens <= 500.0:
        raise PackError(f"--lens must be 10 to 500 mm, not {lens}")
    entry["views"] = recorded
    entry["camera"] = {"ortho": True} if ortho else {"lens": lens or DEFAULT_LENS_MM}
    save(root, manifest)
    return recorded


def views_signature(entry: dict) -> str:
    """A fingerprint of the recorded views; ``cv.py measure`` stores it to show it is current."""
    return hashlib.sha1(json.dumps(entry.get("views", []), sort_keys=True).encode()).hexdigest()[:12]


def _frontmatter(text: str) -> dict:
    """``name`` and ``description`` from a SKILL.md front matter block."""
    fields = {}
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return fields
    for line in lines[1:]:
        if line.strip() == "---":
            break
        key, _, value = line.partition(":")
        if key.strip() in ("name", "description"):
            fields[key.strip()] = value.strip().strip('"').strip("'")
    return fields


def skills_list(root: Path) -> list[dict]:
    """Every installed skill (``.claude/skills/<name>/SKILL.md``): name, description, path."""
    rows = []
    for skill_md in sorted((root / SKILLS_DIR).glob("*/SKILL.md")):
        fields = _frontmatter(skill_md.read_text(encoding="utf-8"))
        rows.append({"name": skill_md.parent.name, "description": fields.get("description", ""),
                     "path": str(skill_md)})
    return rows


def set_skills(root: Path, pack: str, object_id: str, names: list[str]) -> list[str]:
    """Record the installed skills the builder uses for ``object_id`` (an empty list when it
    checked and none apply)."""
    missing = [name for name in names if not (root / SKILLS_DIR / name / "SKILL.md").is_file()]
    if missing:
        raise PackError(f"not installed in {SKILLS_DIR}: {', '.join(missing)} (see pack.py skills-list)")
    manifest = load(root, pack)
    entry = find_object(manifest, object_id)
    entry["skills"] = sorted(set(names))
    save(root, manifest)
    return entry["skills"]


def set_budget(root: Path, pack: str, object_id: str, triangles: int, why: str) -> dict:
    """Record the triangle budget the object is built to, and why that number."""
    why = " ".join(why.split())
    if triangles <= 0:
        raise PackError(f"the triangle budget must be a positive number, not {triangles}")
    if not why:
        raise PackError("say why this budget: what in the reference needs the triangles")
    manifest = load(root, pack)
    entry = find_object(manifest, object_id)
    if entry.get("budget_why") == "given by the user" and entry.get("budget") != triangles:
        raise PackError(f"the user gave {object_id} a budget of {entry['budget']:,} triangles; keep it")
    entry["budget"] = triangles
    if entry.get("budget_why") != "given by the user":
        entry["budget_why"] = why
    save(root, manifest)
    return {"budget": entry["budget"], "budget_why": entry["budget_why"]}


def kit_api(root: Path) -> str:
    """The kit's public functions with their signatures and docstrings, read from kit.py itself so
    it never drifts from the code."""
    tree = ast.parse((root / KIT).read_text(encoding="utf-8"))
    lines = [f"# {KIT}: public functions (open the file only where a docstring leaves a question)", ""]
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            lines.append(f"kit.{node.name}({ast.unparse(node.args)})")
            doc = ast.get_docstring(node)
            if doc:
                lines.extend("    " + line for line in doc.splitlines())
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


# --------------------------------------------------------------------------------- #
# Texture search
# --------------------------------------------------------------------------------- #

def _matched(haystack: str, words: list[str]) -> int:
    """How many of ``words`` are whole words of ``haystack`` (singular or plural): "fur" finds
    fur, not furniture."""
    tokens = set(re.findall(r"[a-z0-9]+", haystack.lower()))
    count = 0
    for word in (word.lower() for word in words):
        stem = word[:-1] if word.endswith("s") and len(word) > 3 else word
        if word in tokens or stem in tokens or stem + "s" in tokens or stem + "es" in tokens:
            count += 1
    return count


def rank_polyhaven(assets: dict, words: list[str]) -> list[dict]:
    """Poly Haven textures matching any of ``words`` in their id, name, tags or categories, most
    words matched first, then most downloaded."""
    ranked = []
    for asset_id, info in assets.items():
        haystack = " ".join([asset_id, info.get("name", "")] + info.get("tags", []) + info.get("categories", [])).lower()
        matched = _matched(haystack, words)
        if matched:
            size = [round(mm / 1000, 2) for mm in info.get("dimensions", [])]
            ranked.append({"ref": f"polyhaven:{asset_id}", "name": info.get("name", asset_id),
                           "size_m": size, "matched": matched, "downloads": info.get("download_count", 0),
                           "thumbnail": info.get("thumbnail_url")})
    ranked.sort(key=lambda row: (-row["matched"], -row["downloads"], row["ref"]))
    return ranked


def ambientcg_rows(found: dict) -> list[dict]:
    """Rows for ambientCG search results, in the order ambientCG returned them."""
    return [{"ref": f"ambientcg:{asset['assetId']}", "name": asset.get("displayName", asset["assetId"]),
             "thumbnail": (asset.get("previewImage") or {}).get(AMBIENTCG_PREVIEW)}
            for asset in found.get("foundAssets", [])]


def rank_cgbookcase(catalog: list, words: list[str]) -> list[dict]:
    """cgbookcase textures that have the maps kit.material needs, most words matched first, newest
    first among equals (the API gives no download counts)."""
    ranked = []
    for texture in catalog:
        if not all(name in texture.get("files", []) for name in CGBOOKCASE_FILES):
            continue
        haystack = " ".join([texture.get("title", "")] + texture.get("tags", []) + texture.get("categories", [])
                            + texture.get("colors", [])).lower()
        matched = _matched(haystack, words)
        if matched:
            name = texture["title"].replace(" ", "")
            ranked.append({"ref": f"cgbookcase:{name}", "name": texture["title"], "matched": matched,
                           "released": texture.get("releasedate", ""), "maps": texture.get("files", []),
                           "thumbnail": CGBOOKCASE_THUMBNAIL.format(name=name)})
    ranked.sort(key=lambda row: (-row["matched"], row["released"] and -int(row["released"].replace("-", "")), row["ref"]))
    return ranked


def blendkit_rows(results: list[dict]) -> list[dict]:
    """Rows for Blendkit's free CC0 materials (Blender node materials, often procedural)."""
    rows = []
    for asset in results:
        parameters = asset.get("dictParameters") or {}
        rows.append({"ref": f"blendkit:{asset['assetBaseId']}", "name": asset.get("name", ""),
                     "size_m": parameters.get("textureSizeMeters"), "procedural": parameters.get("procedural"),
                     "thumbnail": asset.get("thumbnailMiddleUrl") or asset.get("thumbnailSmallUrl")})
    return rows


def _catalog(root: Path, name: str, url: str):
    """A library's whole catalog, downloaded at most once a day."""
    path = root / CATALOG_DIR / f"{name}.json"
    if path.exists() and datetime.datetime.now().timestamp() - path.stat().st_mtime < CATALOG_MAX_AGE_S:
        return json.loads(path.read_text(encoding="utf-8"))
    catalog = downloads.get_json(url)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(catalog), encoding="utf-8")
    return catalog


def material_search(words: list[str], previews: Path | None = None, limit: int = SEARCH_LIMIT,
                    root: Path = REPO_ROOT) -> dict[str, list[dict]]:
    """Texture sets and materials for ``words`` from Poly Haven, ambientCG, cgbookcase and Blendkit
    (free CC0 only). With ``previews``, their thumbnails are saved there and, when the CV
    libraries are installed, laid out in one labelled ``sheet.png`` to look at before choosing."""
    found = {}
    errors = {}
    searches = {
        "polyhaven": lambda: rank_polyhaven(_catalog(root, "polyhaven", POLYHAVEN_ASSETS), words),
        "ambientcg": lambda: ambientcg_rows(downloads.get_json(
            AMBIENTCG_SEARCH.format(limit=limit, query=urllib.parse.quote(" ".join(words))))),
        "cgbookcase": lambda: rank_cgbookcase(_catalog(root, "cgbookcase", CGBOOKCASE_CATALOG), words),
        "blendkit": lambda: blendkit_rows(downloads.blendkit_search(words, limit)),
    }
    for library, search in searches.items():
        try:
            found[library] = search()[:limit]
        except downloads.FetchError as error:
            found[library] = []
            errors[library] = str(error)
    if previews is not None:
        previews.mkdir(parents=True, exist_ok=True)
        shown = []
        for rows in found.values():
            for row in rows:
                if not row.get("thumbnail"):
                    continue
                target = previews / (row["ref"].replace(":", "_") + ".png")
                try:
                    target.write_bytes(downloads.get_bytes(row["thumbnail"]))
                except downloads.FetchError:
                    continue
                row["preview"] = str(target)
                shown.append((target, row["ref"]))
        try:
            import cv  # the CV libraries are optional here
            if cv.cv2 is not None and shown:
                found["sheet"] = str(cv.contact_sheet([path for path, _ in shown], [ref for _, ref in shown],
                                                      previews / "sheet.png"))
        except Exception as error:  # a missing sheet never stops the search
            errors["sheet"] = str(error)
    if errors:
        found["errors"] = errors
    return found


# --------------------------------------------------------------------------------- #
# Builder notes
# --------------------------------------------------------------------------------- #

def section(text: str, heading: str, level: int = 3) -> str | None:
    """The body of the markdown section ``heading`` (at ``level``), or None when it is missing."""
    marks = "#" * level
    match = re.search(rf"^{marks} {re.escape(heading)}[ \t]*$", text, flags=re.MULTILINE)
    if not match:
        return None
    rest = text[match.end():]
    end = re.search(rf"^#{{1,{level}}} ", rest, flags=re.MULTILINE)
    return rest[:end.start()] if end else rest


def _filled(body: str) -> str:
    """``body`` without HTML comments, table rules and blank space."""
    body = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)
    return "\n".join(line for line in body.splitlines() if line.strip() and not SEPARATOR.fullmatch(line)).strip()


SEPARATOR = re.compile(r"\s*\|?[\s:|-]+\|?\s*")


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def inventory_rows(body: str) -> list[list[str]]:
    """The parts inventory's rows as cells, without its header and rule lines."""
    lines = [line for line in body.splitlines() if line.strip().startswith("|")]
    rows = []
    for index, line in enumerate(lines):
        if SEPARATOR.fullmatch(line):
            continue
        if index + 1 < len(lines) and SEPARATOR.fullmatch(lines[index + 1]):
            continue  # a header row
        rows.append(_cells(line))
    return rows


def inventory_columns(body: str) -> int:
    """How many columns the inventory's header has."""
    lines = [line for line in body.splitlines() if line.strip().startswith("|")]
    for index, line in enumerate(lines[:-1]):
        if SEPARATOR.fullmatch(lines[index + 1]) and not SEPARATOR.fullmatch(line):
            return len(_cells(line))
    return 0


def analysis_problems(text: str) -> list[str]:
    """The analysis sections of a builder's notes that are missing or still empty."""
    problems = []
    for heading in ANALYSIS_SECTIONS:
        body = section(text, heading)
        if body is None:
            problems.append(f"'### {heading}' is missing")
        elif heading == "Parts inventory":
            rows = inventory_rows(body)
            columns = inventory_columns(body)
            if not rows:
                problems.append("'### Parts inventory' has no rows")
            incomplete = [row[0] or str(number) for number, row in enumerate(rows, start=1)
                          if len(row) < columns or not all(row[:columns])]
            if incomplete:
                problems.append(f"'### Parts inventory' rows {', '.join(incomplete)} leave cells empty: fill every "
                                "column, the nuances too")
        elif not _filled(body):
            problems.append(f"'### {heading}' is empty")
    return problems


def has_cycle(text: str, number: int) -> bool:
    """Whether the notes have a filled ``## Cycle <number>`` section."""
    match = re.search(rf"^## Cycle {number}\b.*$", text, flags=re.MULTILINE)
    if not match:
        return False
    rest = text[match.end():]
    end = re.search(r"^## ", rest, flags=re.MULTILINE)
    return bool(_filled(rest[:end.start()] if end else rest))


# --------------------------------------------------------------------------------- #
# Brief, completion, status
# --------------------------------------------------------------------------------- #

def _references_text(root: Path, pack: str, manifest: dict, entry: dict) -> str:
    lines = []
    for number, path in enumerate(reference_paths(root, pack, entry), start=1):
        if manifest["skip_canva"]:
            kind = ("the user's image (the object is " + entry["where"] + " in it)"
                    if path.name == manifest["source"] else "the user's reference image of the object")
        else:
            kind = "Canva's drawing of the object, background removed, in the user's art style"
        lines.append(f"{number}. {path} — {kind}")
    return "\n".join(lines)


def _views_text(entry: dict) -> str:
    views = entry.get("views") or []
    if not views:
        return "none recorded yet (you record them in SET-UP)"
    return "; ".join(f"view {number}: reference {view['ref']}, azimuth {view['azimuth']:g}°, elevation "
                     f"{view['elevation']:g}°, box {' '.join(str(v) for v in view['box'])}"
                     for number, view in enumerate(views, start=1))


def _budget_text(entry: dict) -> str:
    if entry.get("budget_why") == "given by the user":
        return f"{entry['budget']:,} triangles, given by the user (keep it)"
    if entry.get("budget"):
        return f"{entry['budget']:,} triangles, recorded by you ({entry['budget_why']})"
    return ("not set: in SET-UP decide what the reference's detail needs and record it with "
            "`pack.py budget`")


def brief(root: Path, pack: str, object_id: str) -> str:
    """The instructions for the builder that models one object. Creates the object's notes from
    the template the first time."""
    manifest = load(root, pack)
    entry = find_object(manifest, object_id)
    if not manifest.get("style"):
        raise PackError(f"{pack} has no art style yet; run pack.py style {pack} \"<style>\"")
    if not entry.get("references"):
        raise PackError(f"{object_id} has no reference image yet: download its Canva image first "
                        "(pack.py canva-download)")
    notes = notes_path(root, pack, object_id)
    if not notes.exists():
        notes.parent.mkdir(parents=True, exist_ok=True)
        text = Template((TEMPLATES / "builder_notes.md").read_text(encoding="utf-8"))
        notes.write_text(text.substitute(id=object_id, name=entry["name"]), encoding="utf-8")
    origin = MOUNTS[entry["mount"]]
    evidence = evidence_dir(root, pack, object_id)
    text = Template((TEMPLATES / "builder_brief.md").read_text(encoding="utf-8"))
    return text.substitute(
        repo=root, pack=pack, id=object_id, name=entry["name"], where=entry["where"],
        details=entry["details"], style=manifest["style"], source=pack_dir(root, pack) / manifest["source"],
        references=_references_text(root, pack, manifest, entry), views=_views_text(entry),
        notes=notes, generator=generator_path(root, pack, object_id), readme=root / KIT_README,
        skills=root / SKILLS_DIR, evidence=evidence, budget=_budget_text(entry), cycles=BUILD_CYCLES,
        run_origin="" if origin == "bottom" else f', origin="{origin}"',
        mount="hangs on a wall (origin at the centre of its back)" if origin == "back"
              else "stands on the ground (origin at the centre of its base)",
        previews=root / PREVIEWS_DIR / pack / object_id, builds_per_builder=BUILDS_PER_BUILDER,
        compare=evidence / f"{object_id}_compare.png", blender_notes=root / BLENDER_NOTES,
    ).strip()


def report_problems(root: Path, pack: str, object_id: str) -> list[str]:
    """Why the object cannot be marked done yet (empty when it can)."""
    manifest = load(root, pack)
    entry = find_object(manifest, object_id)
    problems = []
    if not generator_path(root, pack, object_id).exists():
        problems.append("no generator")
    if not glb_path(root, pack, object_id).exists():
        problems.append("no .glb exported")
    build = read_json(build_report_path(root, pack, object_id))
    if build is None:
        problems.append("no rendered build")
    else:
        if not build.get("final"):
            problems.append(f"build {build['build']} is not a final build: build once more with --final")
        elif not (build.get("bake") or {}).get("baked"):
            problems.append(f"build {build['build']} did not bake its textures (the final build bakes them)")
        cv = read_json(cv_report_path(root, pack, object_id))
        if cv is None or cv.get("build") != build["build"]:
            problems.append(f"build {build['build']} has no CV compare (cv.py compare)")
        triangles = build.get("report", {}).get("triangles")
        if entry.get("budget") and triangles and triangles > entry["budget"]:
            problems.append(f"{triangles:,} triangles, over the budget of {entry['budget']:,}")
    notes = notes_path(root, pack, object_id)
    text = notes.read_text(encoding="utf-8") if notes.exists() else ""
    report = section(text, REPORT_SECTION, level=2)
    if report is None or not _filled(report):
        problems.append(f"the notes have no '## {REPORT_SECTION}' section with the final report")
    return problems


def done(root: Path, pack: str, object_id: str) -> dict:
    """Mark the object built: its final build, CV compare and report all exist."""
    problems = report_problems(root, pack, object_id)
    if problems:
        raise PackError(f"{object_id} is not done: " + "; ".join(problems))
    manifest = load(root, pack)
    entry = find_object(manifest, object_id)
    build = read_json(build_report_path(root, pack, object_id))
    entry["done"] = {"at": _now(), "build": build["build"],
                     "triangles": build["report"].get("triangles"),
                     "dimensions_m": build["report"].get("dimensions_m")}
    save(root, manifest)
    return entry["done"]


def critic_brief(root: Path, pack: str, object_id: str) -> str:
    """The instructions for the critic of the object's next review round."""
    manifest = load(root, pack)
    entry = find_object(manifest, object_id)
    if "done" not in entry:
        raise PackError(f"{object_id} is not done yet: the critic reviews a finished final build")
    previous = entry.get("reviews", [])
    number = len(previous) + 1
    if number > CRITIC_ROUNDS:
        raise PackError(f"{object_id} has had all {CRITIC_ROUNDS} review rounds; the user reviews it now")
    evidence = evidence_dir(root, pack, object_id)
    if previous:
        last = review_path(root, pack, object_id, previous[-1]["round"])
        earlier = (f"VERIFY FIRST: the previous review is {last}. For each of its Fixes, say whether the build "
                   f"now shows it done (DONE / NOT DONE / PARTLY, with the view and box), in a section "
                   f"`## Fixes checked` before the verdicts.")
    else:
        earlier = "This is the first review round."
    text = Template((TEMPLATES / "critic_brief.md").read_text(encoding="utf-8"))
    return text.substitute(
        repo=root, pack=pack, id=object_id, name=entry["name"], style=manifest["style"],
        references=_references_text(root, pack, manifest, entry), views=_views_text(entry),
        notes=notes_path(root, pack, object_id), evidence=evidence, compare=evidence / f"{object_id}_compare.png",
        turnaround=evidence / f"{object_id}_turnaround.png", review=review_path(root, pack, object_id, number),
        round=number, rounds=CRITIC_ROUNDS, build=entry["done"]["build"], previous=earlier,
    ).strip()


def reviewed(root: Path, pack: str, object_id: str, route: str) -> dict:
    """Record the route of the critic's review just written (``ACCEPT``, ``REFINE`` or ``REQUEST-INPUT``)."""
    if route not in CRITIC_ROUTES:
        raise PackError(f"the route must be one of {', '.join(CRITIC_ROUTES)}")
    manifest = load(root, pack)
    entry = find_object(manifest, object_id)
    if "done" not in entry:
        raise PackError(f"{object_id} is not done: there is no build to review")
    number = len(entry.get("reviews", [])) + 1
    path = review_path(root, pack, object_id, number)
    if not path.exists():
        raise PackError(f"the critic's review {path} does not exist yet")
    record = {"round": number, "build": entry["done"]["build"], "route": route, "review": str(path), "at": _now()}
    entry.setdefault("reviews", []).append(record)
    save(root, manifest)
    return record


def accept(root: Path, pack: str, object_id: str) -> dict:
    """Record that the user accepted the object as it is now."""
    manifest = load(root, pack)
    entry = find_object(manifest, object_id)
    if "done" not in entry:
        raise PackError(f"{object_id} is not done yet: its builder finishes with pack.py done")
    entry["accepted"] = {"at": _now(), "build": entry["done"]["build"]}
    save(root, manifest)
    return entry["accepted"]


def reopen(root: Path, pack: str, object_id: str) -> dict:
    """The object goes back to a builder (the critic's REFINE or the user's changes): done and
    accepted are cleared; the reviews stay, the next builder reads them."""
    manifest = load(root, pack)
    entry = find_object(manifest, object_id)
    entry.pop("done", None)
    entry.pop("accepted", None)
    save(root, manifest)
    return entry


def last_builder_activity(root: Path, pack: str, object_id: str) -> float | None:
    """Minutes since a builder of the object last started a build, or None."""
    latest = None
    for path in (root / AGENTS_DIR).glob("*.json"):
        state = read_json(path) or {}
        if state.get("pack") == pack and state.get("id") == object_id and state.get("last_build_at"):
            moment = datetime.datetime.fromisoformat(state["last_build_at"])
            latest = moment if latest is None or moment > latest else latest
    if latest is None:
        return None
    return round((datetime.datetime.now(datetime.timezone.utc) - latest).total_seconds() / 60.0, 1)


def next_step(manifest: dict, entry: dict, godot: bool) -> str:
    """What the orchestrator does next for the object (the run can resume from this alone)."""
    canva = entry.get("canva", {})
    if "refused" in canva:
        return "refused"
    if not entry.get("references"):
        return "canva"
    if "done" not in entry:
        return "build"
    rounds = entry.get("reviews", [])
    reviewed_now = bool(rounds) and rounds[-1]["build"] == entry["done"]["build"]
    if not reviewed_now and len(rounds) < CRITIC_ROUNDS:
        return "critic"
    if reviewed_now and rounds[-1]["route"] == "REFINE" and len(rounds) < CRITIC_ROUNDS:
        return "refine"
    if reviewed_now and rounds[-1]["route"] == "REQUEST-INPUT":
        return "ask"
    if "accepted" not in entry:
        return "review"
    if not godot:
        return "godot"
    return "ok"


STATUS_COLUMNS = ("reference", "views", "skills", "budget", "builds", "cv", "triangles", "size_m", "done", "critic",
                  "accepted", "godot", "active", "next")


def status(root: Path, pack: str) -> list[dict]:
    """Per object: where it stands and the orchestrator's next step for it."""
    manifest = load(root, pack)
    rows = []
    for entry in manifest["objects"]:
        object_id = entry["id"]
        evidence = evidence_dir(root, pack, object_id)
        build = read_json(build_report_path(root, pack, object_id)) or {}
        cv = read_json(cv_report_path(root, pack, object_id)) or {}
        godot = any(evidence.glob(f"{object_id}_godot_*.png"))
        minutes = last_builder_activity(root, pack, object_id)
        rows.append({
            "id": object_id, "reference": bool(entry.get("references")), "views": len(entry.get("views", [])),
            "skills": "skills" in entry, "budget": entry.get("budget") or False, "builds": build.get("build", 0),
            "cv": bool(build) and cv.get("build") == build.get("build"),
            "triangles": build.get("report", {}).get("triangles", "-"),
            "size_m": "x".join(f"{value:g}" for value in build.get("report", {}).get("dimensions_m", [])) or "-",
            "done": "done" in entry,
            "critic": (f"{entry['reviews'][-1]['round']}:{entry['reviews'][-1]['route']}" if entry.get("reviews") else "-"),
            "accepted": "accepted" in entry,
            "godot": godot, "active": "-" if minutes is None else f"{minutes:g}m",
            "next": next_step(manifest, entry, godot),
        })
    return rows


# --------------------------------------------------------------------------------- #
# Run lock, export, discard
# --------------------------------------------------------------------------------- #

def run_start(root: Path, pack: str) -> dict:
    """Start a pipeline run of ``pack``: until run_end the hooks lock the pipeline (no edits, no
    git changes), restore any pipeline file that changes anyway from the snapshot taken here, and
    gate every Blender build on the builder's set-up and CV compare."""
    import guard

    load(root, pack)
    lock = root / RUN_LOCK
    if lock.exists():
        raise PackError(f"a run is already in progress ({lock.read_text().strip()}); end it with pack.py run-end")
    lock.parent.mkdir(parents=True, exist_ok=True)
    state = {"pack": pack, "started": _now()}
    state["snapshot"] = guard.snapshot(root, pack)
    lock.write_text(json.dumps(state) + "\n", encoding="utf-8")
    return state


def run_end(root: Path) -> dict:
    """End the run in progress. The pipeline is checked against the run-start snapshot one last time
    (any changed pipeline file is restored, any file left outside the pack's folders is moved to
    ``.scratch/assetgen/quarantine/``), then the lock and the run's scratch state are removed."""
    import guard

    lock = root / RUN_LOCK
    if not lock.exists():
        raise PackError("no run is in progress")
    state = json.loads(lock.read_text(encoding="utf-8"))
    check = guard.verify(root, restore=True)
    guard.clear_snapshot(root)
    shutil.rmtree(root / AGENTS_DIR, ignore_errors=True)
    shutil.rmtree(root / PREVIEWS_DIR / state["pack"], ignore_errors=True)
    lock.unlink()
    state["check"] = check
    return state


def export(root: Path, pack: str, destination: Path) -> Path:
    """Copy the pack's deliverables into ``destination/<pack>/`` (outside the repository) and zip
    it; returns the zip. Per object: the .glb, its reference images, the comparison, the turnaround
    and the Godot screenshots that exist."""
    destination = destination.resolve()
    if destination == root.resolve() or root.resolve() in destination.parents:
        raise PackError(f"{destination} is inside the repository; export to a folder outside it")
    manifest = load(root, pack)
    folder = destination / pack
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    shutil.copyfile(pack_dir(root, pack) / manifest["source"], folder / manifest["source"])
    for entry in manifest["objects"]:
        object_id = entry["id"]
        evidence = evidence_dir(root, pack, object_id)
        files = [glb_path(root, pack, object_id), evidence / f"{object_id}_compare.png",
                 evidence / f"{object_id}_turnaround.png"]
        files += sorted(evidence.glob(f"{object_id}_godot_*.png"))
        present = [path for path in files if path.exists()]
        if present:
            (folder / object_id).mkdir()
            for path in present:
                shutil.copyfile(path, folder / object_id / path.name)
            for number, path in enumerate(reference_paths(root, pack, entry), start=1):
                if path.exists():
                    shutil.copyfile(path, folder / object_id / f"{object_id}_reference_{number}{path.suffix}")
    return Path(shutil.make_archive(str(folder), "zip", root_dir=destination, base_dir=pack))


def pack_areas(root: Path, pack: str) -> list[Path]:
    """The folders a pack's run writes to."""
    return [pack_dir(root, pack), root / GENERATORS_DIR / pack, root / MODELS_DIR / pack, root / EVIDENCE_DIR / pack]


def discard(root: Path, pack: str) -> list[str]:
    """Delete the pack's working files from the repository (after its export, when the user does not
    want it committed), so the repository holds only the pipeline again."""
    if (root / RUN_LOCK).exists():
        raise PackError("a run is in progress; end it first (pack.py run-end)")
    load(root, pack)
    removed = []
    for area in pack_areas(root, pack):
        if area.exists():
            shutil.rmtree(area)
            removed.append(str(area.relative_to(root)))
    return removed


# --------------------------------------------------------------------------------- #
# Command line
# --------------------------------------------------------------------------------- #

def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("init", help="create a pack from the user's image")
    command.add_argument("pack")
    command.add_argument("image", type=Path)
    command.add_argument("--skip-canva", action="store_true",
                         help="no Canva: every object is built from the user's own reference image(s)")
    command = commands.add_parser("add", help="add an object chosen from the image")
    command.add_argument("pack")
    command.add_argument("id")
    command.add_argument("--name", required=True, help="short name of the object")
    command.add_argument("--where", required=True, help="where it is in the source image")
    command.add_argument("--details", required=True, help="its parts, materials and colours seen in the image")
    command.add_argument("--mount", default="floor", choices=sorted(MOUNTS))
    command.add_argument("--reference", type=Path, nargs="+", help="skip canva: the object's reference image(s)")
    command.add_argument("--budget", type=int, help="triangle budget, only when the user gave one")
    for name in ("prompt", "brief", "done", "accept", "reopen", "critic-brief"):
        command = commands.add_parser(name)
        command.add_argument("pack")
        command.add_argument("id")
    command = commands.add_parser("canva", help="record the pack-level Canva ids")
    command.add_argument("pack")
    command.add_argument("--source-media")
    command.add_argument("--design")
    command.add_argument("--transaction")
    command = commands.add_parser("canva-calls", help="print the exact Canva calls of one download stage")
    command.add_argument("pack")
    command.add_argument("stage", choices=CANVA_STAGES)
    command.add_argument("--page-ids", nargs="+", help="place: the new pages' ids, in page order")
    command = commands.add_parser("canva-download", help="download the export URLs to the objects' images")
    command.add_argument("pack")
    command.add_argument("urls", nargs="+")
    command = commands.add_parser("record", help="record an object's Canva result")
    command.add_argument("pack")
    command.add_argument("id")
    command.add_argument("--media")
    command.add_argument("--job")
    command.add_argument("--refused")
    command = commands.add_parser("cutout", help="record an object's background-removed image")
    command.add_argument("pack")
    command.add_argument("id")
    command.add_argument("--media")
    command.add_argument("--failed")
    command = commands.add_parser("views", help="record the views of the object its reference images show")
    command.add_argument("pack")
    command.add_argument("id")
    command.add_argument("--view", type=float, nargs=7, action="append", required=True,
                         metavar=("REF", "AZIMUTH", "ELEVATION", "X0", "Y0", "X1", "Y1"))
    command.add_argument("--lens", type=float, help="render lens in mm matching the reference's perspective (default 85)")
    command.add_argument("--ortho", action="store_true", help="the reference is drawn without perspective")
    commands.add_parser("skills-list", help="list the installed skills with their descriptions")
    command = commands.add_parser("skills", help="record the installed skills the builder uses")
    command.add_argument("pack")
    command.add_argument("id")
    command.add_argument("names", nargs="*")
    command.add_argument("--none", action="store_true", help="checked, and no installed skill applies")
    command = commands.add_parser("budget", help="record the object's triangle budget and why")
    command.add_argument("pack")
    command.add_argument("id")
    command.add_argument("triangles", type=int)
    command.add_argument("--why", required=True)
    commands.add_parser("kit-api", help="print the kit's public functions with signatures and docstrings")
    command = commands.add_parser("reviewed", help="record the route of the critic's review just written")
    command.add_argument("pack")
    command.add_argument("id")
    command.add_argument("route", choices=CRITIC_ROUTES)
    command = commands.add_parser("material-search",
                                  help="find texture sets and materials on Poly Haven, ambientCG, cgbookcase and Blendkit")
    command.add_argument("words", nargs="+")
    command.add_argument("--previews", type=Path, help="folder to save the results' thumbnails in")
    command.add_argument("--limit", type=int, default=SEARCH_LIMIT, help="results per library")
    command = commands.add_parser("style", help="record the art style the user asked for")
    command.add_argument("pack")
    command.add_argument("style")
    command = commands.add_parser("export", help="copy the deliverables to one folder outside the repo, zipped")
    command.add_argument("pack")
    command.add_argument("destination", type=Path)
    command = commands.add_parser("discard", help="delete the pack's working files from the repository")
    command.add_argument("pack")
    command = commands.add_parser("run-start", help="start a run: the pipeline is locked until run-end")
    command.add_argument("pack")
    command = commands.add_parser("run-end", help="check the pipeline is unchanged and end the run")
    command.add_argument("pack", nargs="?", help="the run's pack (optional; checked when given)")
    command = commands.add_parser("status", help="show where each object stands")
    command.add_argument("pack")
    command = commands.add_parser("sheets", help="export page and file name per Canva image")
    command.add_argument("pack")
    return parser


def main(argv: list[str] | None = None, root: Path = REPO_ROOT) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "init":
            print(json.dumps(init(root, args.pack, args.image, args.skip_canva), indent=2))
        elif args.command == "add":
            print(json.dumps(add(root, args.pack, args.id, args.name, args.where, args.details,
                                 args.mount, args.reference, args.budget), indent=2))
        elif args.command == "style":
            print(set_style(root, args.pack, args.style))
        elif args.command == "prompt":
            print(prompt(root, args.pack, args.id))
        elif args.command == "canva":
            print(json.dumps(set_canva(root, args.pack, args.source_media, args.design, args.transaction), indent=2))
        elif args.command == "canva-calls":
            print(json.dumps(canva_calls(root, args.pack, args.stage, args.page_ids), indent=2))
        elif args.command == "canva-download":
            print("\n".join(canva_download(root, args.pack, args.urls)))
        elif args.command == "record":
            print(json.dumps(record(root, args.pack, args.id, args.media, args.job, args.refused), indent=2))
        elif args.command == "cutout":
            print(json.dumps(cutout(root, args.pack, args.id, args.media, args.failed), indent=2))
        elif args.command == "sheets":
            for row in sheets(root, args.pack):
                print(f"page {row['page']:>3}  {row['media_id']:<14} {row['file']}")
        elif args.command == "views":
            print(json.dumps(set_views(root, args.pack, args.id, args.view, args.lens, args.ortho), indent=2))
        elif args.command == "skills-list":
            for row in skills_list(root):
                print(f"- {row['name']}: {row['description']}\n  {row['path']}")
        elif args.command == "skills":
            if bool(args.names) == args.none:
                raise PackError("give the skill names you use, or --none when you checked and none apply")
            print(json.dumps(set_skills(root, args.pack, args.id, args.names), indent=2))
        elif args.command == "budget":
            print(json.dumps(set_budget(root, args.pack, args.id, args.triangles, args.why), indent=2))
        elif args.command == "kit-api":
            print(kit_api(root), end="")
        elif args.command == "material-search":
            print(json.dumps(material_search(args.words, args.previews, args.limit, root), indent=2))
        elif args.command == "critic-brief":
            print(critic_brief(root, args.pack, args.id))
        elif args.command == "reviewed":
            print(json.dumps(reviewed(root, args.pack, args.id, args.route), indent=2))
        elif args.command == "brief":
            print(brief(root, args.pack, args.id))
        elif args.command == "done":
            print(json.dumps(done(root, args.pack, args.id), indent=2))
        elif args.command == "accept":
            print(json.dumps(accept(root, args.pack, args.id), indent=2))
        elif args.command == "reopen":
            reopen(root, args.pack, args.id)
            print(f"{args.id} reopened: start its builder with the critic's review or the user's words")
        elif args.command == "status":
            print("id".ljust(20) + "".join(column.ljust(10) for column in STATUS_COLUMNS))
            for row in status(root, args.pack):
                print(row["id"].ljust(20) + "".join(str(row[column]).ljust(10) for column in STATUS_COLUMNS))
        elif args.command == "run-start":
            state = run_start(root, args.pack)
            print(json.dumps({key: state[key] for key in ("pack", "started")} | {"snapshot_files": state["snapshot"]["files"]}, indent=2))
        elif args.command == "run-end":
            if args.pack:
                lock = read_json(root / RUN_LOCK) or {}
                if lock and lock.get("pack") != args.pack:
                    raise PackError(f"the run in progress is of pack {lock.get('pack')}, not {args.pack}")
            state = run_end(root)
            print(json.dumps({key: state[key] for key in ("pack", "started", "check")}, indent=2))
        elif args.command == "export":
            print(export(root, args.pack, args.destination))
        elif args.command == "discard":
            print("\n".join(discard(root, args.pack)) or "nothing to remove")
    except (PackError, downloads.FetchError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
