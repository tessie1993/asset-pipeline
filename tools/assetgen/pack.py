#!/usr/bin/env python3
"""Pack bookkeeping for the image-to-Godot asset pipeline (``.claude/skills/image-to-assets``).

A pack is one source image and the objects found in it. Everything about a pack lives in
``design/asset-packs/<pack>/``: ``pack.json`` (objects, Canva ids, material table), the source
image, ``canva/NN_<id>_360.png`` sheets and ``objects/<id>.md`` descriptions. This tool keeps
that manifest and prints the texts the pipeline sends (the Canva prompt, the sub-agent brief)
from the templates in ``tools/assetgen/templates/``, so no step is typed from memory. There are
no preset materials: each sub-agent searches Poly Haven and ambientCG while it builds.

Usage::

    python3 tools/assetgen/pack.py init <pack> <image>
    python3 tools/assetgen/pack.py style <pack> "<art style in the user's words>"
    python3 tools/assetgen/pack.py run-start <pack>
    python3 tools/assetgen/pack.py add <pack> <id> --name N --where W --details D \
        [--layout object|block] [--mount floor|wall] [--size large|medium|small]
    python3 tools/assetgen/pack.py prompt <pack> <id>
    python3 tools/assetgen/pack.py canva <pack> [--source-media ID] [--design ID] [--transaction ID]
    python3 tools/assetgen/pack.py record <pack> <id> (--media ID [--job ID] | --refused REASON)
    python3 tools/assetgen/pack.py cutout <pack> <id> (--media ID | --failed REASON)
    python3 tools/assetgen/pack.py sheets <pack>
    python3 tools/assetgen/pack.py canva-calls <pack> <stage> [--page-ids ID ...]
    python3 tools/assetgen/pack.py canva-download <pack> <url> ...
    python3 tools/assetgen/pack.py view <pack> <id> [--elevation DEG] [--judge AZ ...]
    python3 tools/assetgen/pack.py skills <pack> <id> (<skill name> ... | --none)
    python3 tools/assetgen/pack.py describe <pack> <id>
    python3 tools/assetgen/pack.py brief <pack> <id>
    python3 tools/assetgen/pack.py material-search <words...> [--previews DIR] [--limit N]
    python3 tools/assetgen/pack.py status <pack>
    python3 tools/assetgen/pack.py run-end
    python3 tools/assetgen/pack.py export <pack> <folder outside the repository>
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import shutil
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from string import Template

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = Path(__file__).resolve().parent / "templates"

PACKS_DIR = Path("design/asset-packs")
GENERATORS_DIR = Path("tools/blender/assetgen/packs")
MODELS_DIR = Path("assets/models")
EVIDENCE_DIR = Path("production/qa/evidence")
KIT = Path("tools/blender/assetgen/kit.py")
KIT_README = Path("tools/blender/assetgen/README.md")
SKILLS_DIR = Path(".claude/skills")
RUN_LOCK = Path(".scratch/assetgen/run.json")  # read by .claude/hooks/assetgen-run-guard.sh

ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
LAYOUTS = {
    "object": "the same object from eight evenly spaced angles all the way around it (0, 45, 90, 135, 180, "
              "225, 270 and 315 degrees) in two rows of four, camera slightly above.",
    "block": "the same object shown as a small block from eight evenly spaced angles all the way around it "
             "(0, 45, 90, 135, 180, 225, 270 and 315 degrees) in two rows of four, camera raised about 35 "
             "degrees so the top surface is visible.",
}
# Degrees above the horizon each layout's sheet is asked to be drawn from (see LAYOUTS). The
# orchestrator corrects an object's angle with `view` after looking at the sheet Canva returned.
VIEW_ELEVATIONS = {"object": 15.0, "block": 35.0}
VIEW_AZIMUTHS = (0, 45, 90, 135, 180, 225, 270, 315)
MOUNTS = {"floor": "bottom", "wall": "back"}
BUDGETS = {"large": 40_000, "medium": 20_000, "small": 10_000}

POLYHAVEN_ASSETS = "https://api.polyhaven.com/assets?t=textures"
AMBIENTCG_SEARCH = ("https://ambientcg.com/api/v2/full_json?type=Material&include=imageData"
                    "&limit={limit}&q={query}")
AMBIENTCG_PREVIEW = "256-PNG"
SEARCH_LIMIT = 8
# Canva's generate-image returns LANDSCAPE_16_9 images at this size; canva-download checks it.
SHEET_SIZE = (1680, 944)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
CANVA_STAGES = ("create", "open", "add-pages", "read-pages", "place", "check", "commit", "export")
BLANK_DESIGN_BRIEF = ("A completely blank one-page landscape design with a plain white background and "
                      "no text, no images and no decoration. It is only used to place existing images and "
                      "download them.")
BUILD_CYCLES = 5  # build -> render -> compare cycles a builder runs unless it stops early for review
USER_AGENT = "nokepom-assetgen/1.0 (+https://github.com/tessie1993/nokepom)"
REQUEST_TIMEOUT_S = 60


class PackError(RuntimeError):
    """A pack command cannot be carried out; the message says why."""


# --------------------------------------------------------------------------------- #
# Manifest
# --------------------------------------------------------------------------------- #

def pack_dir(root: Path, pack: str) -> Path:
    """Folder holding ``pack``'s manifest, source image, sheets and descriptions."""
    return root / PACKS_DIR / pack


def load(root: Path, pack: str) -> dict:
    """Return ``pack``'s manifest."""
    path = pack_dir(root, pack) / "pack.json"
    if not path.exists():
        raise PackError(f"{path.relative_to(root)} not found; run: pack.py init {pack} <image>")
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
    """File name of the object's Canva 360 sheet: ``NN_<id>_360.png``."""
    return f"{entry['number']:02d}_{entry['id']}_360.png"


def _check_id(value: str, what: str) -> str:
    if not ID_PATTERN.match(value):
        raise PackError(f"{what} {value!r} must be snake_case: lower-case letters, digits and _")
    return value


# --------------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------------- #

def init(root: Path, pack: str, image: Path) -> dict:
    """Create ``pack`` from the source ``image``: folders, a copy of the image and an empty manifest."""
    _check_id(pack, "pack name")
    folder = pack_dir(root, pack)
    if (folder / "pack.json").exists():
        raise PackError(f"pack {pack} already exists")
    if not image.is_file():
        raise PackError(f"source image {image} not found")
    for sub in ("canva", "objects"):
        (folder / sub).mkdir(parents=True, exist_ok=True)
    source_name = "source" + image.suffix.lower()
    shutil.copyfile(image, folder / source_name)
    manifest = {"pack": pack, "source": source_name, "canva": {}, "objects": []}
    save(root, manifest)
    return manifest


def add(root: Path, pack: str, object_id: str, name: str, where: str, details: str,
        layout: str = "object", mount: str = "floor", size: str = "medium") -> dict:
    """Add an object to ``pack``; it gets the next sheet number."""
    manifest = load(root, pack)
    _check_id(object_id, "object id")
    if any(entry["id"] == object_id for entry in manifest["objects"]):
        raise PackError(f"{pack} already has an object {object_id!r}")
    for value, allowed, what in ((layout, LAYOUTS, "layout"), (mount, MOUNTS, "mount"), (size, BUDGETS, "size")):
        if value not in allowed:
            raise PackError(f"{what} must be one of {sorted(allowed)}, not {value!r}")
    entry = {
        "id": object_id, "number": len(manifest["objects"]) + 1, "name": name, "where": where,
        "details": details, "layout": layout, "mount": mount, "size": size, "canva": {},
        "view_elevation_deg": VIEW_ELEVATIONS[layout], "judge_views": list(VIEW_AZIMUTHS),
    }
    manifest["objects"].append(entry)
    save(root, manifest)
    return entry


def set_style(root: Path, pack: str, style: str) -> str:
    """Record the art style the user asked for; every Canva prompt of the pack uses it."""
    style = " ".join(style.split())
    if not style:
        raise PackError("the art style is empty; ask the user which art style they want")
    manifest = load(root, pack)
    manifest["style"] = style
    save(root, manifest)
    return style


def prompt(root: Path, pack: str, object_id: str) -> str:
    """The Canva prompt for one object, sent with the source image as the reference."""
    manifest = load(root, pack)
    if not manifest.get("style"):
        raise PackError(f"{pack} has no art style yet; ask the user, then run pack.py style {pack} \"<style>\"")
    entry = find_object(manifest, object_id)
    text = Template((TEMPLATES / "canva_prompt.txt").read_text(encoding="utf-8"))
    return text.substitute(name=entry["name"], details=entry["details"], where=entry["where"],
                           style=manifest["style"], camera=LAYOUTS[entry["layout"]]).strip()


def set_canva(root: Path, pack: str, source_media: str | None, design: str | None,
              transaction: str | None = None) -> dict:
    """Record the pack-level Canva ids: the uploaded source image, the scratch export design and
    the design's open editing transaction."""
    manifest = load(root, pack)
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
    manifest = load(root, pack)
    entry = find_object(manifest, object_id)
    entry["canva"] = {"media_id": media, "job_id": job} if media else {"refused": refused}
    save(root, manifest)
    return entry["canva"]


def _get_json(url: str):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_S) as response:
        return json.load(response)


def rank_polyhaven(assets: dict, words: list[str]) -> list[dict]:
    """Poly Haven textures matching any of ``words`` in their id, name, tags or categories, most
    words matched first, then most downloaded."""
    lowered = [word.lower() for word in words]
    ranked = []
    for asset_id, info in assets.items():
        haystack = " ".join([asset_id, info.get("name", "")] + info.get("tags", []) + info.get("categories", [])).lower()
        matched = sum(word in haystack for word in lowered)
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


def _save_previews(rows: list[dict], folder: Path) -> None:
    """Download each row's thumbnail into ``folder`` and record its path as ``preview``."""
    folder.mkdir(parents=True, exist_ok=True)
    for row in rows:
        if not row.get("thumbnail"):
            continue
        target = folder / (row["ref"].replace(":", "_") + ".png")
        request = urllib.request.Request(row["thumbnail"], headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_S) as response:
            target.write_bytes(response.read())
        row["preview"] = str(target)


def material_search(words: list[str], previews: Path | None = None, limit: int = SEARCH_LIMIT) -> dict[str, list[dict]]:
    """Textures for ``words`` from Poly Haven and ambientCG; with ``previews``, their thumbnails
    are saved there so they can be looked at before one is chosen."""
    polyhaven = rank_polyhaven(_get_json(POLYHAVEN_ASSETS), words)[:limit]
    found = _get_json(AMBIENTCG_SEARCH.format(limit=limit, query=urllib.parse.quote(" ".join(words))))
    ambientcg = ambientcg_rows(found)[:limit]
    if previews is not None:
        _save_previews(polyhaven + ambientcg, previews)
    return {"polyhaven": polyhaven, "ambientcg": ambientcg}


def set_view(root: Path, pack: str, object_id: str, elevation: float | None,
             judge: list[int] | None) -> dict:
    """Record what the object's Canva sheet actually shows: the angle above the horizon it was
    drawn from, and the views that agree with each other (the ones the build is judged on)."""
    manifest = load(root, pack)
    entry = find_object(manifest, object_id)
    if elevation is not None:
        if not 0.0 <= elevation <= 90.0:
            raise PackError(f"elevation must be between 0 and 90 degrees, not {elevation}")
        entry["view_elevation_deg"] = elevation
    if judge is not None:
        unknown = sorted(set(judge) - set(VIEW_AZIMUTHS))
        if unknown or not judge:
            raise PackError(f"judge views must be a non-empty subset of {list(VIEW_AZIMUTHS)}, got {judge}")
        entry["judge_views"] = sorted(set(judge))
    save(root, manifest)
    return {"view_elevation_deg": entry["view_elevation_deg"], "judge_views": entry["judge_views"]}


def set_skills(root: Path, pack: str, object_id: str, names: list[str]) -> list[str]:
    """Record the installed skills (``.claude/skills/<name>/SKILL.md``) relevant to modelling
    ``object_id``; its builder is told to read and use them."""
    missing = [name for name in names if not (root / SKILLS_DIR / name / "SKILL.md").is_file()]
    if missing:
        raise PackError(f"not installed in {SKILLS_DIR}: {', '.join(missing)}")
    manifest = load(root, pack)
    entry = find_object(manifest, object_id)
    entry["skills"] = sorted(set(names))
    save(root, manifest)
    return entry["skills"]


def _skills_text(root: Path, entry: dict) -> str:
    """The object's relevant skills as a list of SKILL.md paths for the brief."""
    names = entry["skills"]
    if not names:
        return "- the orchestrator checked the installed skills and found none relevant"
    return "\n".join(f"- `{name}`: {root / SKILLS_DIR / name / 'SKILL.md'}" for name in names)


def run_start(root: Path, pack: str) -> dict:
    """Mark a pipeline run of ``pack`` as in progress: until run_end, the run guard hook blocks
    changes to the pipeline and every git commit or push."""
    load(root, pack)
    lock = root / RUN_LOCK
    if lock.exists():
        raise PackError(f"a run is already in progress ({lock.read_text().strip()}); end it with pack.py run-end")
    lock.parent.mkdir(parents=True, exist_ok=True)
    state = {"pack": pack, "started": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
    lock.write_text(json.dumps(state) + "\n", encoding="utf-8")
    return state


def run_end(root: Path) -> dict:
    """End the run in progress; returns what it was."""
    lock = root / RUN_LOCK
    if not lock.exists():
        raise PackError("no run is in progress")
    state = json.loads(lock.read_text(encoding="utf-8"))
    lock.unlink()
    return state


def cutout(root: Path, pack: str, object_id: str, media: str | None, failed: str | None) -> dict:
    """Record the background-removed copy of an object's generated image (Canva
    ``remove-background``), or why removing the background failed."""
    if bool(media) == bool(failed):
        raise PackError("pass exactly one of --media or --failed")
    manifest = load(root, pack)
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
    """Per object that Canva made an image for, in sheet-number order: the media id to export
    (the background-removed copy; the generated image only where removal failed and that was
    recorded), the page it gets in the scratch export design (page 1 is the design's own blank
    page, so object pages start at 2, added in this order) and the file its export is saved as."""
    manifest = load(root, pack)
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
    each generated image is placed, unedited and at its own size, on its own page of one blank
    scratch design, and those pages are exported. Stages, in order: create, open, add-pages,
    read-pages, place, check, commit, export.
    """
    if stage not in CANVA_STAGES:
        raise PackError(f"stage must be one of {CANVA_STAGES}, not {stage!r}")
    manifest = load(root, pack)
    rows = sheets(root, pack)
    pages = [row["page"] for row in rows]
    width, height = SHEET_SIZE
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


def png_size(data: bytes) -> tuple[int, int] | None:
    """Width and height of a PNG from its header, or None when ``data`` is not a PNG."""
    if not data.startswith(PNG_SIGNATURE) or data[12:16] != b"IHDR":
        return None
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def canva_download(root: Path, pack: str, urls: list[str]) -> list[str]:
    """Download the export URLs (in page order) to the sheets' files, checking each is a PNG of
    :data:`SHEET_SIZE`; returns the files written."""
    rows = sheets(root, pack)
    if len(urls) != len(rows):
        raise PackError(f"expected {len(rows)} export URLs (pages {[row['page'] for row in rows]}), got {len(urls)}")
    written = []
    for row, url in zip(rows, urls):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_S * 2) as response:
            data = response.read()
        size = png_size(data)
        if size != SHEET_SIZE:
            raise PackError(f"{row['id']}: the export is {'not a PNG' if size is None else size}, "
                            f"expected a {SHEET_SIZE[0]}x{SHEET_SIZE[1]} PNG; nothing saved for it")
        (root / row["file"]).write_bytes(data)
        written.append(row["file"])
    return written


def describe(root: Path, pack: str, object_id: str) -> Path:
    """Create ``objects/<id>.md`` from the template (reference images embedded) unless it exists."""
    manifest = load(root, pack)
    entry = find_object(manifest, object_id)
    path = pack_dir(root, pack) / "objects" / f"{object_id}.md"
    if not path.exists():
        text = Template((TEMPLATES / "object_description.md").read_text(encoding="utf-8"))
        path.write_text(text.substitute(
            id=object_id, name=entry["name"], where=entry["where"],
            sheet_name=sheet_name(entry), source_name=manifest["source"], mount=entry["mount"],
            origin=MOUNTS[entry["mount"]], size=entry["size"], budget=f"{BUDGETS[entry['size']]:,}",
            elevation=f"{entry['view_elevation_deg']:g}", judge_views=_views_text(entry),
        ), encoding="utf-8")
    return path


def _views_text(entry: dict) -> str:
    """The views an object is judged on, as text: "all eight" or the listed angles."""
    views = entry["judge_views"]
    if list(views) == list(VIEW_AZIMUTHS):
        return "all eight views"
    return "the views at " + ", ".join(f"{angle}°" for angle in views) + " (the others contradict them)"


def brief(root: Path, pack: str, object_id: str) -> str:
    """The instructions for the sub-agent that models one object."""
    manifest = load(root, pack)
    entry = find_object(manifest, object_id)
    if not manifest.get("style"):
        raise PackError(f"{pack} has no art style yet; run pack.py style {pack} \"<style>\"")
    if "skills" not in entry:
        raise PackError(f"{object_id}: the installed skills were not checked yet; run pack.py skills "
                        f"{pack} {object_id} <names> (or --none after checking)")
    folder = pack_dir(root, pack)
    origin = MOUNTS[entry["mount"]]
    text = Template((TEMPLATES / "subagent_brief.md").read_text(encoding="utf-8"))
    return text.substitute(
        repo=root, id=object_id, name=entry["name"], where=entry["where"],
        sheet=folder / "canva" / sheet_name(entry), source=folder / manifest["source"],
        description=folder / "objects" / f"{object_id}.md",
        generator=root / GENERATORS_DIR / pack / f"{object_id}.py", readme=root / KIT_README,
        kit=root / KIT, skills=root / SKILLS_DIR, judge_views=_views_text(entry),
        previews=root / ".scratch" / "assetgen" / "previews" / pack / object_id,
        compare=root / EVIDENCE_DIR / pack / object_id / f"{object_id}_compare.png",
        run_origin="" if origin == "bottom" else f', origin="{origin}"',
        budget=f"{BUDGETS[entry['size']]:,} triangles", cycles=BUILD_CYCLES,
        relevant_skills=_skills_text(root, entry), pack=pack, style=manifest["style"],
        zoom_example=root / EVIDENCE_DIR / pack / object_id / f"{object_id}_zoom_<azimuth>.png",
        notes=root / EVIDENCE_DIR / pack / object_id / f"{object_id}_notes.md",
    ).strip()


def export(root: Path, pack: str, destination: Path) -> Path:
    """Copy the pack's deliverables into ``destination/<pack>/`` (outside the repository) and zip
    it; returns the zip. Per object: the .glb, the Canva sheet, the render sheet, the comparison
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
        evidence = root / EVIDENCE_DIR / pack / object_id
        files = [root / MODELS_DIR / pack / f"{object_id}.glb", pack_dir(root, pack) / "canva" / sheet_name(entry)]
        files += [evidence / f"{object_id}_{suffix}.png" for suffix in ("sheet", "compare", "godot_front", "godot_back")]
        present = [path for path in files if path.exists()]
        if present:
            (folder / object_id).mkdir()
            for path in present:
                shutil.copyfile(path, folder / object_id / path.name)
    return Path(shutil.make_archive(str(folder), "zip", root_dir=destination, base_dir=pack))


STATUS_COLUMNS = ("canva", "sheet", "description", "generator", "glb", "blender", "godot")


def status(root: Path, pack: str) -> list[dict]:
    """Per object: which pipeline outputs exist so far."""
    manifest = load(root, pack)
    folder = pack_dir(root, pack)
    rows = []
    for entry in manifest["objects"]:
        object_id = entry["id"]
        evidence = root / EVIDENCE_DIR / pack / object_id
        rows.append({
            "id": object_id,
            "canva": "refused" if "refused" in entry["canva"] else bool(entry["canva"].get("media_id")),
            "sheet": (folder / "canva" / sheet_name(entry)).exists(),
            "description": (folder / "objects" / f"{object_id}.md").exists(),
            "generator": (root / GENERATORS_DIR / pack / f"{object_id}.py").exists(),
            "glb": (root / MODELS_DIR / pack / f"{object_id}.glb").exists(),
            "blender": (evidence / f"{object_id}_compare.png").exists(),
            "godot": (evidence / f"{object_id}_godot_front.png").exists(),
        })
    return rows


# --------------------------------------------------------------------------------- #
# Command line
# --------------------------------------------------------------------------------- #

def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("init", help="create a pack from a source image")
    command.add_argument("pack")
    command.add_argument("image", type=Path)
    command = commands.add_parser("add", help="add an object found in the source image")
    command.add_argument("pack")
    command.add_argument("id")
    command.add_argument("--name", required=True, help="short name of the object")
    command.add_argument("--where", required=True, help="where it is in the source image")
    command.add_argument("--details", required=True, help="parts, materials and colours seen in the image")
    command.add_argument("--layout", default="object", choices=sorted(LAYOUTS),
                         help="object: drawn from slightly above; block: a mostly flat piece whose top "
                              "matters, drawn from about 35 degrees")
    command.add_argument("--mount", default="floor", choices=sorted(MOUNTS))
    command.add_argument("--size", default="medium", choices=sorted(BUDGETS))
    for name in ("prompt", "describe", "brief"):
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
    command = commands.add_parser("canva-download", help="download the export URLs to the sheet files")
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
    command = commands.add_parser("material-search", help="find textures on Poly Haven and ambientCG")
    command.add_argument("words", nargs="+")
    command.add_argument("--previews", type=Path, help="folder to save the results' thumbnails in")
    command.add_argument("--limit", type=int, default=SEARCH_LIMIT, help="results per library")
    command = commands.add_parser("view", help="record the sheet's camera angle and consistent views")
    command.add_argument("pack")
    command.add_argument("id")
    command.add_argument("--elevation", type=float, help="degrees above the horizon the sheet is drawn from")
    command.add_argument("--judge", type=int, nargs="+", help="azimuths of the views that agree with each other")
    command = commands.add_parser("style", help="record the art style the user asked for")
    command.add_argument("pack")
    command.add_argument("style")
    command = commands.add_parser("export", help="copy the deliverables to one folder outside the repo, zipped")
    command.add_argument("pack")
    command.add_argument("destination", type=Path)
    command = commands.add_parser("skills", help="record the installed skills relevant to an object")
    command.add_argument("pack")
    command.add_argument("id")
    command.add_argument("names", nargs="*")
    command.add_argument("--none", action="store_true", help="checked, and no installed skill is relevant")
    command = commands.add_parser("run-start", help="start a pipeline run: the pipeline is locked until run-end")
    command.add_argument("pack")
    commands.add_parser("run-end", help="end the pipeline run in progress")
    command = commands.add_parser("status", help="show which outputs exist per object")
    command.add_argument("pack")
    command = commands.add_parser("sheets", help="export page and file name per Canva image")
    command.add_argument("pack")
    return parser


def main(argv: list[str] | None = None, root: Path = REPO_ROOT) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "init":
            print(json.dumps(init(root, args.pack, args.image), indent=2))
        elif args.command == "add":
            print(json.dumps(add(root, args.pack, args.id, args.name, args.where, args.details,
                                 args.layout, args.mount, args.size), indent=2))
        elif args.command == "prompt":
            print(prompt(root, args.pack, args.id))
        elif args.command == "canva":
            print(json.dumps(set_canva(root, args.pack, args.source_media, args.design, args.transaction), indent=2))
        elif args.command == "canva-calls":
            print(json.dumps(canva_calls(root, args.pack, args.stage, args.page_ids), indent=2))
        elif args.command == "canva-download":
            print("\n".join(canva_download(root, args.pack, args.urls)))
        elif args.command == "cutout":
            print(json.dumps(cutout(root, args.pack, args.id, args.media, args.failed), indent=2))
        elif args.command == "record":
            print(json.dumps(record(root, args.pack, args.id, args.media, args.job, args.refused), indent=2))
        elif args.command == "material-search":
            print(json.dumps(material_search(args.words, args.previews, args.limit), indent=2))
        elif args.command == "view":
            print(json.dumps(set_view(root, args.pack, args.id, args.elevation, args.judge), indent=2))
        elif args.command == "style":
            print(set_style(root, args.pack, args.style))
        elif args.command == "export":
            print(export(root, args.pack, args.destination))
        elif args.command == "skills":
            if bool(args.names) == args.none:
                raise PackError("give the relevant skill names, or --none when none are relevant")
            print(json.dumps(set_skills(root, args.pack, args.id, args.names), indent=2))
        elif args.command == "run-start":
            print(json.dumps(run_start(root, args.pack), indent=2))
        elif args.command == "run-end":
            print(json.dumps(run_end(root), indent=2))
        elif args.command == "describe":
            print(describe(root, args.pack, args.id).relative_to(root))
        elif args.command == "brief":
            print(brief(root, args.pack, args.id))
        elif args.command == "sheets":
            for row in sheets(root, args.pack):
                print(f"page {row['page']:>3}  {row['media_id']:<14} {row['file']}")
        elif args.command == "status":
            rows = status(root, args.pack)
            print("id".ljust(20) + "".join(column.ljust(13) for column in STATUS_COLUMNS))
            for row in rows:
                print(row["id"].ljust(20) + "".join(str(row[column]).ljust(13) for column in STATUS_COLUMNS))
    except PackError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
