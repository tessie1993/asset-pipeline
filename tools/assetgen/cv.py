#!/usr/bin/env python3
"""Computer-vision tools for the asset builders (OpenCV and NumPy, no Blender): find the object's
views in any reference image, measure them, and compare every build's renders with them.

Everything here is an observation, never a verdict: the numbers say what differs and where, the
builder decides why and what to change. Each command writes at most one image per view.

    python3 tools/assetgen/cv.py views   <pack> <id> [--ref N]        # find the object views in a reference image
    python3 tools/assetgen/cv.py grid    <pack> <id> [--ref N]        # the image with a pixel grid, to read boxes
    python3 tools/assetgen/cv.py measure <pack> <id>                  # measure the recorded views
    python3 tools/assetgen/cv.py observe <pack> <id> [--view N]       # magnified tiles: details, variation, wear
    python3 tools/assetgen/cv.py sample  <pack> <id> --view N --box X0 Y0 X1 Y1 [--box ...]  # colour statistics
    python3 tools/assetgen/cv.py compare <pack> <id>                  # last build vs reference (the kit runs it)
    python3 tools/assetgen/cv.py closeup <pack> <id> --view N --box X0 Y0 X1 Y1 [--scale S]

Install the libraries once: ``bash tools/assetgen/install_cv.sh`` (pinned, into .scratch/pydeps).
"""
from __future__ import annotations

import argparse
import datetime
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / ".scratch" / "pydeps"))
import pack  # noqa: E402

try:
    import cv2  # noqa: E402
    import numpy as np  # noqa: E402
except ImportError as error:  # reported by main(); the module still imports for pack-only use
    cv2 = np = None
    IMPORT_ERROR = error

GREY = (211, 211, 211)  # background the images are shown on (BGR)
REFERENCE_OUTLINE = (40, 40, 230)  # red
RENDER_OUTLINE = (230, 210, 40)  # cyan
MISSING_TINT = (200, 60, 200)  # magenta: in the reference, not in the render
EXTRA_TINT = (40, 200, 230)  # yellow: in the render, not in the reference
NORM_HEIGHT = 384  # silhouettes are compared at this height, bottom-centre aligned
REGIONS = ("top-left", "top-centre", "top-right", "middle-left", "centre", "middle-right",
           "bottom-left", "bottom-centre", "bottom-right")
DIFF_REPORTED = 0.06  # a region is named when this share of it is missing or extra
SHEET_MAX_WIDTH = 1500  # px; images wider than this cost more to read without showing more
SHEET_MAX_CELL = 360
SURVEY_TILE = 220
MIN_COMPONENT = 0.004  # share of the image a blob needs to count as a view
COLOURS = 5
SAMPLE_PIXELS = 20000
LUMA = (0.0722, 0.7152, 0.2126)  # BGR weights


class CVError(RuntimeError):
    """A CV command cannot be carried out; the message says why."""


# --------------------------------------------------------------------------------- #
# Images
# --------------------------------------------------------------------------------- #

def read_image(path: Path) -> np.ndarray:
    """``path`` as an 8-bit BGRA array."""
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise CVError(f"cannot read {path}")
    if image.dtype != np.uint8:
        image = (image // 257).astype(np.uint8)
    if image.ndim == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGRA)
    elif image.shape[2] == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
    return image


def write_image(path: Path, image: np.ndarray) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(path), image):
        raise CVError(f"cannot write {path}")
    return path


def on_grey(image: np.ndarray) -> np.ndarray:
    """A BGRA image composited over the grey background, as BGR."""
    alpha = image[..., 3:4].astype(np.float32) / 255.0
    grey = np.array(GREY, dtype=np.float32)
    return (image[..., :3].astype(np.float32) * alpha + grey * (1.0 - alpha)).astype(np.uint8)


def fit_width(image: np.ndarray, size: int) -> np.ndarray:
    """``image`` scaled down (never up) so its longer side is at most ``size`` pixels: a bigger
    image costs more to read without showing more."""
    longest = max(image.shape[:2])
    if longest <= size:
        return image
    scale = size / longest
    return cv2.resize(image, (max(1, round(image.shape[1] * scale)), max(1, round(image.shape[0] * scale))),
                      interpolation=cv2.INTER_AREA)


def label(image: np.ndarray, text: str, origin=(6, 18), scale: float = 0.5) -> None:
    for colour, thickness in (((255, 255, 255), 3), ((20, 20, 20), 1)):
        cv2.putText(image, text, origin, cv2.FONT_HERSHEY_SIMPLEX, scale, colour, thickness, cv2.LINE_AA)


def hex_colour(bgr) -> str:
    b, g, r = (int(round(float(c))) for c in bgr)
    return f"#{r:02x}{g:02x}{b:02x}"


def brightness(bgr) -> float:
    return float(np.dot(np.asarray(bgr, dtype=np.float32) / 255.0, LUMA))


# --------------------------------------------------------------------------------- #
# Masks: which pixels are the object
# --------------------------------------------------------------------------------- #

def _has_transparency(image: np.ndarray) -> bool:
    return bool((image[..., 3] < 250).mean() > 0.01)


def _lab(bgr: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(bgr.astype(np.float32) / 255.0, cv2.COLOR_BGR2LAB)


def plain_background(image: np.ndarray) -> tuple[np.ndarray, float] | None:
    """The Lab colour and spread of a plain background along the image's border, or None."""
    height, width = image.shape[:2]
    band = max(2, round(0.03 * min(height, width)))
    lab = _lab(image[..., :3])
    border = np.concatenate([lab[:band].reshape(-1, 3), lab[-band:].reshape(-1, 3),
                             lab[:, :band].reshape(-1, 3), lab[:, -band:].reshape(-1, 3)])
    median = np.median(border, axis=0)
    distance = np.linalg.norm(border - median, axis=1)
    if np.mean(distance < 10.0) < 0.85:
        return None
    return median, float(np.percentile(distance, 90))


def _clean(mask: np.ndarray, min_share: float = 0.002) -> np.ndarray:
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    keep = np.zeros_like(mask)
    floor = min_share * mask.size
    for index in range(1, count):
        if stats[index, cv2.CC_STAT_AREA] >= floor:
            keep[labels == index] = 1
    return keep


def _grabcut(region: np.ndarray) -> np.ndarray:
    height, width = region.shape[:2]
    scale = min(1.0, 600.0 / max(height, width))
    small = cv2.resize(region[..., :3], (max(8, round(width * scale)), max(8, round(height * scale))),
                       interpolation=cv2.INTER_AREA)
    mask = np.zeros(small.shape[:2], np.uint8)
    rect = (1, 1, small.shape[1] - 2, small.shape[0] - 2)
    background, foreground = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    cv2.grabCut(small, mask, rect, background, foreground, 4, cv2.GC_INIT_WITH_RECT)
    result = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 1, 0).astype(np.uint8)
    return cv2.resize(result, (width, height), interpolation=cv2.INTER_NEAREST)


def object_mask(region: np.ndarray) -> tuple[np.ndarray, str]:
    """``(mask, method)`` of the object in ``region`` (BGRA): its alpha where it has one, else
    everything that differs from a plain background, else GrabCut (approximate)."""
    if _has_transparency(region):
        mask, method = (region[..., 3] > 127).astype(np.uint8), "alpha"
    else:
        background = plain_background(region)
        if background is not None:
            colour, spread = background
            distance = np.linalg.norm(_lab(region[..., :3]) - colour, axis=2)
            mask, method = (distance > max(12.0, 2.5 * spread)).astype(np.uint8), "plain background"
        else:
            mask, method = _grabcut(region), "grabcut (approximate: busy background)"
    return _clean(mask), method


def bbox(mask: np.ndarray) -> tuple[int, int, int, int] | None:
    """``(x0, y0, x1, y1)`` around the mask's pixels (exclusive end), or None when empty."""
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


# --------------------------------------------------------------------------------- #
# Pack access
# --------------------------------------------------------------------------------- #

def _entry(root: Path, pack_name: str, object_id: str) -> tuple[dict, dict]:
    try:
        manifest = pack.load(root, pack_name)
        return manifest, pack.find_object(manifest, object_id)
    except pack.PackError as error:
        raise CVError(str(error)) from error


def _reference(root: Path, pack_name: str, entry: dict, number: int) -> Path:
    paths = pack.reference_paths(root, pack_name, entry)
    if not paths:
        raise CVError(f"{entry['id']} has no reference image yet")
    if not 1 <= number <= len(paths):
        raise CVError(f"--ref must be 1 to {len(paths)}")
    return paths[number - 1]


def reference_view(root: Path, pack_name: str, view: dict) -> np.ndarray:
    """The recorded view's box of its reference image (BGRA)."""
    image = read_image(pack.pack_dir(root, pack_name) / view["image"])
    x0, y0, x1, y1 = view["box"]
    return image[y0:y1, x0:x1].copy()


def _view_name(number: int, view: dict) -> str:
    return f"view {number} (az {view['azimuth']:g}, el {view['elevation']:g})"


# --------------------------------------------------------------------------------- #
# views and grid: reading the reference image
# --------------------------------------------------------------------------------- #

def _components(image: np.ndarray) -> tuple[list[list[int]], str]:
    """Unpadded boxes of the separate things in ``image`` and how the background was told apart."""
    height, width = image.shape[:2]
    if _has_transparency(image):
        mask, method = (image[..., 3] > 127).astype(np.uint8), "alpha"
    else:
        background = plain_background(image)
        if background is None:
            return [], "no transparent or plain background"
        colour, spread = background
        mask = (np.linalg.norm(_lab(image[..., :3]) - colour, axis=2) > max(12.0, 2.5 * spread)).astype(np.uint8)
        method = "plain background"
    reach = max(3, round(0.012 * max(height, width)))
    joined = cv2.dilate(mask, np.ones((reach, reach), np.uint8))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(joined, connectivity=8)
    boxes = []
    for index in range(1, count):
        if stats[index, cv2.CC_STAT_AREA] < MIN_COMPONENT * height * width:
            continue
        x, y, w, h = (int(v) for v in stats[index][:4])
        tight = bbox(np.logical_and(labels[y:y + h, x:x + w] == index, mask[y:y + h, x:x + w] > 0))
        if tight is not None:  # the box hugs the thing's own pixels, not the joining margin
            boxes.append([x + tight[0], y + tight[1], x + tight[2], y + tight[3]])
    merged = True
    while merged:  # parts of one drawing whose boxes overlap belong together
        merged = False
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                a, b = boxes[i], boxes[j]
                if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                    boxes[i] = [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]
                    del boxes[j]
                    merged = True
                    break
            if merged:
                break
    return boxes, method


def find_views(image: np.ndarray, depth: int = 0) -> tuple[list[list[int]], str]:
    """Boxes ``[x0, y0, x1, y1]`` around each separate drawing or photo of the object in
    ``image``, in reading order, and how the background was told apart. A large region with a plain
    background of its own (a picture inside a screenshot, a backdrop inside a photo) is searched
    again inside, so the boxes end up around the objects themselves."""
    height, width = image.shape[:2]
    boxes, method = _components(image)
    if not boxes and depth == 0:
        return [], method + ": read the boxes with `cv.py grid`"
    refined = []
    for x0, y0, x1, y1 in boxes:
        area = (x1 - x0) * (y1 - y0)
        if depth < 3 and area >= 0.25 * width * height:
            inner, inner_method = find_views(image[y0:y1, x0:x1], depth + 1)
            if inner and sum((b[2] - b[0]) * (b[3] - b[1]) for b in inner) < 0.85 * area:
                refined += [[b[0] + x0, b[1] + y0, b[2] + x0, b[3] + y0] for b in inner]
                method = f"{method}, then {inner_method} inside a region"
                continue
        refined.append([x0, y0, x1, y1])
    if depth > 0:
        return refined, method
    padded = []
    for x0, y0, x1, y1 in refined:
        pad = max(2, round(0.03 * max(x1 - x0, y1 - y0)))
        padded.append([max(0, x0 - pad), max(0, y0 - pad), min(width, x1 + pad), min(height, y1 + pad)])
    padded.sort(key=lambda box: (round((box[1] + box[3]) / 2 / (height / 4)), box[0]))
    return padded, method


def views_command(root: Path, pack_name: str, object_id: str, ref: int = 1) -> list[str]:
    _, entry = _entry(root, pack_name, object_id)
    path = _reference(root, pack_name, entry, ref)
    image = read_image(path)
    boxes, method = find_views(image)
    shown = on_grey(image)
    for number, (x0, y0, x1, y1) in enumerate(boxes, start=1):
        cv2.rectangle(shown, (x0, y0), (x1 - 1, y1 - 1), (40, 40, 230), max(2, image.shape[1] // 500))
        label(shown, str(number), (x0 + 6, y0 + 30), scale=max(0.8, image.shape[1] / 1200))
    out = pack.evidence_dir(root, pack_name, object_id) / f"{object_id}_cv_views_{ref}.png"
    write_image(out, fit_width(shown, SHEET_MAX_WIDTH))
    height, width = image.shape[:2]
    lines = [f"REFERENCE {ref}: {path.name} {width}x{height}, background: {method}; {len(boxes)} view(s) found; "
             f"image with numbered boxes: {out}"]
    for number, (x0, y0, x1, y1) in enumerate(boxes, start=1):
        lines.append(f"  {number}: box {x0} {y0} {x1} {y1} ({x1 - x0}x{y1 - y0} px)")
    if boxes:
        views = " ".join(f"--view {ref} <azimuth> <elevation> {' '.join(str(v) for v in box)}" for box in boxes)
        lines.append(f"record (keep only this object's views, fill in each angle): python3 tools/assetgen/pack.py views "
                     f"{pack_name} {object_id} {views}")
    return lines


def _nice_step(size: int) -> int:
    raw = size / 12.0
    for step in (10, 20, 25, 50, 100, 200, 250, 500, 1000):
        if step >= raw:
            return step
    return 1000


def grid_command(root: Path, pack_name: str, object_id: str, ref: int = 1) -> list[str]:
    _, entry = _entry(root, pack_name, object_id)
    path = _reference(root, pack_name, entry, ref)
    image = on_grey(read_image(path))
    height, width = image.shape[:2]
    step = _nice_step(max(height, width))
    scale = min(1.0, SHEET_MAX_WIDTH / max(width, height))
    shown = cv2.resize(image, (round(width * scale), round(height * scale)), interpolation=cv2.INTER_AREA)
    for x in range(0, width, step):
        cv2.line(shown, (round(x * scale), 0), (round(x * scale), shown.shape[0]), (0, 160, 255), 1)
        label(shown, str(x), (round(x * scale) + 2, 14), scale=0.4)
    for y in range(0, height, step):
        cv2.line(shown, (0, round(y * scale)), (shown.shape[1], round(y * scale)), (0, 160, 255), 1)
        label(shown, str(y), (2, round(y * scale) + 14), scale=0.4)
    out = pack.evidence_dir(root, pack_name, object_id) / f"{object_id}_cv_grid_{ref}.png"
    write_image(out, shown)
    return [f"GRID {ref}: {out} (lines every {step} px of the original {width}x{height} image; labels are original pixels)"]


# --------------------------------------------------------------------------------- #
# measure: the reference's views
# --------------------------------------------------------------------------------- #

def dominant_colours(bgr: np.ndarray, mask: np.ndarray, count: int = COLOURS) -> list[dict]:
    pixels = bgr[mask.astype(bool)].astype(np.float32)
    if len(pixels) == 0:
        return []
    if len(pixels) > SAMPLE_PIXELS:
        pixels = pixels[np.random.default_rng(0).choice(len(pixels), SAMPLE_PIXELS, replace=False)]
    count = max(1, min(count, len(pixels)))
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
    cv2.setRNGSeed(0)
    _, labels, centres = cv2.kmeans(pixels, count, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
    shares = np.bincount(labels.ravel(), minlength=count) / len(labels)
    merged: dict[str, dict] = {}
    for centre, share in zip(centres, shares):
        if share < 0.02:
            continue
        key = hex_colour(centre)
        row = merged.setdefault(key, {"colour": key, "share": 0.0, "brightness": round(brightness(centre), 3)})
        row["share"] = round(row["share"] + float(share), 3)
    return sorted(merged.values(), key=lambda row: -row["share"])


def edge_stats(bgr: np.ndarray, mask: np.ndarray) -> tuple[float, dict]:
    """Edge pixels per object pixel inside the object (detail density) and the share of straight
    edge length per direction."""
    grey = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(grey, 60, 160)
    inner = cv2.erode(mask, np.ones((5, 5), np.uint8))
    area = int(inner.sum())
    density = float((edges[inner.astype(bool)] > 0).sum() / area) if area else 0.0
    outline = cv2.Canny(mask * 255, 50, 150)
    lines = cv2.HoughLinesP(cv2.bitwise_or(edges * (mask > 0), outline), 1, np.pi / 180, 30,
                            minLineLength=max(8, mask.shape[0] // 25), maxLineGap=4)
    totals = {"horizontal": 0.0, "vertical": 0.0, "diagonal /": 0.0, "diagonal \\": 0.0}
    for x0, y0, x1, y1 in (lines.reshape(-1, 4) if lines is not None else []):
        length = math.hypot(x1 - x0, y1 - y0)
        angle = math.degrees(math.atan2(-(y1 - y0), x1 - x0)) % 180
        key = ("horizontal" if angle < 22.5 or angle >= 157.5 else "diagonal /" if angle < 67.5
               else "vertical" if angle < 112.5 else "diagonal \\")
        totals[key] += length
    total = sum(totals.values())
    return round(density, 3), {key: round(value / total, 2) for key, value in totals.items()} if total else {}


def measure_view(region: np.ndarray) -> dict:
    mask, method = object_mask(region)
    box = bbox(mask)
    if box is None:
        return {"method": method, "empty": True}
    x0, y0, x1, y1 = box
    tight = mask[y0:y1, x0:x1]
    mirrored = tight[:, ::-1]
    union = np.logical_or(tight, mirrored).sum()
    symmetry = float(np.logical_and(tight, mirrored).sum() / union) if union else 0.0
    bgr = region[..., :3]
    mean = bgr[mask.astype(bool)].mean(axis=0)
    density, directions = edge_stats(bgr, mask)
    return {"method": method, "object_px": [x1 - x0, y1 - y0], "object_box": [x0, y0, x1, y1],
            "aspect": round((x1 - x0) / (y1 - y0), 3), "fill": round(float(tight.mean()), 3),
            "symmetry": round(symmetry, 3), "mean_colour": hex_colour(mean), "brightness": round(brightness(mean), 3),
            "colours": dominant_colours(bgr, mask), "edge_density": density, "directions": directions}


TEXTURE_MAX = 1024  # px, the longer side of a projected texture


def texture_crop(region: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """The object's pixels (BGR) with every background pixel set to the colour of the nearest object
    pixel, so a texture projected from it has no background fringe at the outline; at most
    :data:`TEXTURE_MAX` pixels on the longer side."""
    colour = region[..., :3].copy()
    if mask.any() and not mask.all():
        background = (mask == 0).astype(np.uint8)
        _, labels = cv2.distanceTransformWithLabels(background, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
        nearest = np.flatnonzero(background.ravel() == 0)  # labels count the object pixels in row order
        flat = colour.reshape(-1, 3)
        colour = flat[nearest[labels.ravel() - 1]].reshape(colour.shape)
    return fit_width(colour, TEXTURE_MAX)


def proportions(views: list[dict], measures: list[dict]) -> str | None:
    """width : height : depth from a front or back view and a side view at a similar elevation."""
    def near(angle, targets):
        return any(abs((angle - target + 180) % 360 - 180) <= 20 for target in targets)
    fronts = [(v, m) for v, m in zip(views, measures) if not m.get("empty") and near(v["azimuth"], (0, 180))]
    sides = [(v, m) for v, m in zip(views, measures) if not m.get("empty") and near(v["azimuth"], (90, 270))]
    for front, front_m in fronts:
        for side, side_m in sides:
            if abs(front["elevation"] - side["elevation"]) <= 15:
                width = front_m["aspect"]
                depth = side_m["aspect"]
                return (f"width : height : depth ≈ {width:.2f} : 1 : {depth:.2f} (views at az {front['azimuth']:g} and "
                        f"{side['azimuth']:g}; perspective and elevation make this approximate)")
    return None


def measure_command(root: Path, pack_name: str, object_id: str) -> list[str]:
    _, entry = _entry(root, pack_name, object_id)
    views = entry.get("views") or []
    if not views:
        raise CVError(f"{object_id} has no recorded views: run `cv.py views`, then `pack.py views`")
    evidence = pack.evidence_dir(root, pack_name, object_id)
    measures, lines, panels = [], [], []
    for number, view in enumerate(views, start=1):
        region = reference_view(root, pack_name, view)
        measured = measure_view(region)
        measured["view"] = number
        measures.append(measured)
        if measured.get("empty"):
            lines.append(f"REF {_view_name(number, view)}: no object found in the box ({measured['method']})")
            continue
        # The object's outline and pixels, cut tight to it: the kit carves its silhouette hull from the
        # masks and projects the crops onto the model (kit.silhouette_hull, kit.project_reference).
        x0, y0, x1, y1 = measured["object_box"]
        view_mask, _ = object_mask(region)
        tight_mask = view_mask[y0:y1, x0:x1]
        write_image(evidence / f"{object_id}_cv_mask_{number}.png", (tight_mask * 255).astype(np.uint8))
        write_image(evidence / f"{object_id}_cv_crop_{number}.png", texture_crop(region[y0:y1, x0:x1], tight_mask))
        measured["mask"] = f"{object_id}_cv_mask_{number}.png"
        measured["crop"] = f"{object_id}_cv_crop_{number}.png"
        colours = ", ".join(f"{c['colour']} {round(c['share'] * 100)}% L{c['brightness']:.2f}"
                            for c in measured["colours"])
        directions = ", ".join(f"{key} {round(value * 100)}%" for key, value in
                               sorted(measured["directions"].items(), key=lambda item: -item[1]) if value >= 0.1)
        lines.append(f"REF {_view_name(number, view)} [{measured['method']}]: object {measured['object_px'][0]}x"
                     f"{measured['object_px'][1]} px, w/h {measured['aspect']:.2f}, fill {measured['fill']:.2f}, "
                     f"left-right symmetry {measured['symmetry']:.2f}; colours {colours}; edges/px "
                     f"{measured['edge_density']:.3f}; straight edges {directions or 'few'}")
        panel = on_grey(region)
        mask, _ = object_mask(region)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(panel, contours, -1, (60, 200, 60), 2)
        scale = SHEET_MAX_CELL / max(panel.shape[:2])
        panel = cv2.resize(panel, (max(1, round(panel.shape[1] * scale)), max(1, round(panel.shape[0] * scale))),
                           interpolation=cv2.INTER_AREA)
        swatches = np.full((panel.shape[0], 60, 3), 255, np.uint8)
        top = 0
        for colour in measured["colours"]:
            height = max(4, round(colour["share"] * panel.shape[0]))
            rgb = int(colour["colour"][1:], 16)
            swatches[top:top + height] = ((rgb & 255), (rgb >> 8) & 255, rgb >> 16)
            top += height
        panel = np.concatenate([panel, swatches[:panel.shape[0]]], axis=1)
        label(panel, f"{number}: az {view['azimuth']:g} el {view['elevation']:g}")
        panels.append(panel)
    estimate = proportions(views, measures)
    if estimate:
        lines.append(f"REF proportions: {estimate}")
    sheet = None
    if panels:
        height = max(panel.shape[0] for panel in panels)
        panels = [np.pad(panel, ((0, height - panel.shape[0]), (0, 8), (0, 0)), constant_values=255) for panel in panels]
        sheet = write_image(evidence / f"{object_id}_cv_reference.png", fit_width(np.concatenate(panels, axis=1), SHEET_MAX_WIDTH))
    report = {"views_signature": pack.views_signature(entry), "at": _now(), "views": measures, "proportions": estimate}
    pack.cv_reference_path(root, pack_name, object_id).write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    if sheet:
        lines.append(f"REF image (outline in green, colour shares on the right): {sheet}")
    return lines


# --------------------------------------------------------------------------------- #
# compare: renders against the reference
# --------------------------------------------------------------------------------- #

def normalise(region: np.ndarray, mask: np.ndarray, height: int = NORM_HEIGHT) -> tuple[np.ndarray, np.ndarray]:
    """The object cropped to its outline and scaled to ``height`` pixels (BGRA, mask)."""
    x0, y0, x1, y1 = bbox(mask)
    scale = height / (y1 - y0)
    width = max(1, round((x1 - x0) * scale))
    colour = cv2.resize(region[y0:y1, x0:x1], (width, height), interpolation=cv2.INTER_AREA)
    shape = cv2.resize(mask[y0:y1, x0:x1], (width, height), interpolation=cv2.INTER_NEAREST)
    colour[..., 3] = np.where(shape > 0, 255, 0).astype(np.uint8)
    return colour, shape


def pair_canvas(reference: tuple[np.ndarray, np.ndarray], render: tuple[np.ndarray, np.ndarray]):
    """Both normalised objects on one canvas each, the same size, bottom-centre aligned."""
    width = max(reference[1].shape[1], render[1].shape[1])
    height = NORM_HEIGHT
    placed = []
    for colour, shape in (reference, render):
        left = (width - shape.shape[1]) // 2
        canvas_colour = np.zeros((height, width, 4), np.uint8)
        canvas_mask = np.zeros((height, width), np.uint8)
        canvas_colour[:, left:left + shape.shape[1]] = colour
        canvas_mask[:, left:left + shape.shape[1]] = shape
        placed.append((canvas_colour, canvas_mask))
    return placed


def _regions(mask_a: np.ndarray, mask_b: np.ndarray) -> list[tuple[str, float]]:
    """Per 3 x 3 region of the canvas: the share of it that is in ``mask_a`` and not ``mask_b``."""
    height, width = mask_a.shape
    found = []
    only = np.logical_and(mask_a > 0, mask_b == 0)
    for index, name in enumerate(REGIONS):
        row, column = divmod(index, 3)
        cell = only[row * height // 3:(row + 1) * height // 3, column * width // 3:(column + 1) * width // 3]
        share = float(cell.mean()) if cell.size else 0.0
        if share >= DIFF_REPORTED:
            found.append((name, round(share, 2)))
    return sorted(found, key=lambda item: -item[1])


def _colour_regions(reference: np.ndarray, render: np.ndarray, ref_mask: np.ndarray, render_mask: np.ndarray):
    """Regions where both have the object and the render is clearly lighter or darker."""
    height, width = ref_mask.shape
    both = np.logical_and(ref_mask > 0, render_mask > 0)
    found = []
    for index, name in enumerate(REGIONS):
        row, column = divmod(index, 3)
        rows = slice(row * height // 3, (row + 1) * height // 3)
        columns = slice(column * width // 3, (column + 1) * width // 3)
        cell = both[rows, columns]
        if cell.sum() < 0.1 * cell.size:
            continue
        ref_light = float(np.dot(reference[rows, columns, :3][cell].mean(axis=0) / 255.0, LUMA))
        render_light = float(np.dot(render[rows, columns, :3][cell].mean(axis=0) / 255.0, LUMA))
        if abs(render_light - ref_light) >= 0.08:
            found.append((name, round(render_light - ref_light, 2)))
    return found


def colour_zones(reference: np.ndarray, render: np.ndarray, ref_mask: np.ndarray, render_mask: np.ndarray,
                 count: int = COLOURS) -> list[dict]:
    """Where each main colour of the reference sits in the render: per colour zone (3 % of the object
    or more) its share of the reference, the overlap of the zone in both, the render's area of it as
    a multiple of the reference's, and the regions where it is missing or extra."""
    ref_pixels = reference[..., :3][ref_mask > 0]
    if len(ref_pixels) == 0 or not render_mask.any():
        return []
    centres = []
    for row in dominant_colours(reference[..., :3], ref_mask, count):
        rgb = int(row["colour"][1:], 16)
        bgr = np.array([[[(rgb & 255), (rgb >> 8) & 255, rgb >> 16]]], np.uint8)
        lab = _lab(bgr)[0, 0]
        if all(np.linalg.norm(lab - other) >= 12.0 for _, other in centres):
            centres.append((row["colour"], lab))
    if not centres:
        return []
    labs = np.stack([lab for _, lab in centres])

    def labels(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        distance = np.linalg.norm(_lab(image[..., :3])[:, :, None, :] - labs[None, None], axis=3)
        nearest = distance.argmin(axis=2)
        nearest[(distance.min(axis=2) > 30.0) | (mask == 0)] = -1
        return nearest

    ref_labels, render_labels = labels(reference, ref_mask), labels(render, render_mask)
    total = float((ref_mask > 0).sum())
    zones = []
    for index, (colour, _) in enumerate(centres):
        in_ref = (ref_labels == index).astype(np.uint8)
        in_render = (render_labels == index).astype(np.uint8)
        share = float(in_ref.sum()) / total
        if share < 0.03:
            continue
        union = np.logical_or(in_ref, in_render).sum()
        zones.append({"colour": colour, "share": round(share, 3),
                      "overlap": round(float(np.logical_and(in_ref, in_render).sum() / union) if union else 0.0, 3),
                      "area": round(float(in_render.sum()) / float(in_ref.sum()), 2),
                      "missing": _regions(in_ref, in_render), "extra": _regions(in_render, in_ref)})
    return sorted(zones, key=lambda zone: -zone["share"])


def _outline(image: np.ndarray, mask: np.ndarray, colour, thickness: int = 2) -> None:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(image, contours, -1, colour, thickness)


def overlay_image(reference: np.ndarray, render: np.ndarray, ref_mask: np.ndarray, render_mask: np.ndarray) -> np.ndarray:
    base = (on_grey(render).astype(np.float32) * 0.55 + 255 * 0.45).astype(np.uint8)
    missing = np.logical_and(ref_mask > 0, render_mask == 0)
    extra = np.logical_and(render_mask > 0, ref_mask == 0)
    base[missing] = (base[missing] * 0.4 + np.array(MISSING_TINT) * 0.6).astype(np.uint8)
    base[extra] = (base[extra] * 0.4 + np.array(EXTRA_TINT) * 0.6).astype(np.uint8)
    _outline(base, ref_mask, REFERENCE_OUTLINE)
    _outline(base, render_mask, RENDER_OUTLINE)
    return base


def survey_image(reference: np.ndarray, render: np.ndarray, title: str) -> np.ndarray:
    """The two normalised objects cut into 3 x 3 tiles, each tile reference | render, enlarged."""
    height, width = reference.shape[:2]
    tiles = []
    for index, name in enumerate(REGIONS):
        row, column = divmod(index, 3)
        rows = slice(row * height // 3, (row + 1) * height // 3)
        columns = slice(column * width // 3, (column + 1) * width // 3)
        pair = []
        for image in (reference, render):
            tile = on_grey(image[rows, columns])
            scale = SURVEY_TILE / max(tile.shape[:2])
            tile = cv2.resize(tile, (max(1, round(tile.shape[1] * scale)), max(1, round(tile.shape[0] * scale))),
                              interpolation=cv2.INTER_CUBIC)
            tile = np.pad(tile, ((0, SURVEY_TILE - tile.shape[0]), (0, SURVEY_TILE - tile.shape[1]), (0, 0)),
                          constant_values=255)
            pair.append(tile)
        combined = np.concatenate([pair[0], np.full((SURVEY_TILE, 4, 3), 255, np.uint8), pair[1]], axis=1)
        label(combined, f"{name}: ref | render", scale=0.45)
        tiles.append(np.pad(combined, ((0, 6), (0, 6), (0, 0)), constant_values=230))
    rows_images = [np.concatenate(tiles[i:i + 3], axis=1) for i in (0, 3, 6)]
    sheet = np.concatenate(rows_images, axis=0)
    header = np.full((26, sheet.shape[1], 3), 255, np.uint8)
    label(header, title)
    return fit_width(np.concatenate([header, sheet], axis=0), SHEET_MAX_WIDTH)


def compare_view(reference_region: np.ndarray, render: np.ndarray) -> dict:
    """Numbers and images for one view: render (BGRA, transparent background) vs reference box."""
    ref_mask, method = object_mask(reference_region)
    render_mask = (render[..., 3] > 127).astype(np.uint8)
    if bbox(ref_mask) is None:
        return {"method": method, "error": "no object found in the reference box"}
    if bbox(render_mask) is None:
        return {"method": method, "error": "the render is empty: the object is not in the frame"}
    (ref_colour, ref_shape), (render_colour, render_shape) = pair_canvas(normalise(reference_region, ref_mask),
                                                                         normalise(render, render_mask))
    union = np.logical_or(ref_shape, render_shape).sum()
    overlap = float(np.logical_and(ref_shape, render_shape).sum() / union) if union else 0.0
    ref_box, render_box = bbox(ref_mask), bbox(render_mask)
    ref_aspect = (ref_box[2] - ref_box[0]) / (ref_box[3] - ref_box[1])
    render_aspect = (render_box[2] - render_box[0]) / (render_box[3] - render_box[1])
    ref_mean = ref_colour[..., :3][ref_shape > 0].mean(axis=0)
    render_mean = render_colour[..., :3][render_shape > 0].mean(axis=0)
    ref_edges, ref_dirs = edge_stats(ref_colour[..., :3], ref_shape)
    render_edges, render_dirs = edge_stats(render_colour[..., :3], render_shape)
    return {
        "method": method, "overlap": round(overlap, 3),
        "aspect_reference": round(ref_aspect, 3), "aspect_render": round(render_aspect, 3),
        "aspect_change": round(render_aspect / ref_aspect - 1.0, 3),
        "missing": _regions(ref_shape, render_shape), "extra": _regions(render_shape, ref_shape),
        "colour_reference": hex_colour(ref_mean), "colour_render": hex_colour(render_mean),
        "brightness_reference": round(brightness(ref_mean), 3), "brightness_render": round(brightness(render_mean), 3),
        "lighter_darker": _colour_regions(ref_colour, render_colour, ref_shape, render_shape),
        "colours_reference": dominant_colours(ref_colour[..., :3], ref_shape, 4),
        "colours_render": dominant_colours(render_colour[..., :3], render_shape, 4),
        "zones": colour_zones(ref_colour, render_colour, ref_shape, render_shape),
        "edges_reference": ref_edges, "edges_render": render_edges,
        "directions_reference": ref_dirs, "directions_render": render_dirs,
        "_images": (ref_colour, render_colour, ref_shape, render_shape),
    }


def _line(number: int, view: dict, result: dict, build: int) -> str:
    name = _view_name(number, view)
    if "error" in result:
        return f"CV build {build} {name}: {result['error']}"
    def regions(items):
        return ", ".join(f"{name} {round(share * 100)}%" for name, share in items) or "none"
    tone = ", ".join(f"{name} {'lighter' if delta > 0 else 'darker'} by {abs(delta):.2f}"
                     for name, delta in result["lighter_darker"]) or "none"
    ref_colours = " ".join(c["colour"] for c in result["colours_reference"][:3])
    render_colours = " ".join(c["colour"] for c in result["colours_render"][:3])
    return (f"CV build {build} {name}: outline overlap {result['overlap']:.2f} | w/h reference "
            f"{result['aspect_reference']:.2f} render {result['aspect_render']:.2f} ({result['aspect_change']:+.0%}) | "
            f"missing in render: {regions(result['missing'])} | extra in render: {regions(result['extra'])} | "
            f"colour reference {result['colour_reference']} L{result['brightness_reference']:.2f} render "
            f"{result['colour_render']} L{result['brightness_render']:.2f}; main colours ref {ref_colours} / render "
            f"{render_colours} | render lighter/darker: {tone} | edges/px ref {result['edges_reference']:.3f} render "
            f"{result['edges_render']:.3f} | colour zones: {_zones_text(result['zones'])}")


def _zones_text(zones: list[dict]) -> str:
    parts = []
    for zone in zones[:4]:
        where = "; ".join(filter(None, [
            ("missing " + ", ".join(f"{name} {round(share * 100)}%" for name, share in zone["missing"][:3])) if zone["missing"] else "",
            ("extra " + ", ".join(f"{name} {round(share * 100)}%" for name, share in zone["extra"][:3])) if zone["extra"] else ""]))
        parts.append(f"{zone['colour']} ({round(zone['share'] * 100)}% of the reference) overlap {zone['overlap']:.2f}, "
                     f"render area x{zone['area']:.2f}" + (f", {where}" if where else ""))
    return "; ".join(parts) or "none"


def _column(images: list[np.ndarray], height: int, title: str) -> np.ndarray:
    cells = []
    for image in images:
        scale = height / image.shape[0]
        cells.append(cv2.resize(image, (max(1, round(image.shape[1] * scale)), height), interpolation=cv2.INTER_AREA))
    width = max(cell.shape[1] for cell in cells)
    cells = [np.pad(cell, ((0, 4), ((width - cell.shape[1]) // 2, width - cell.shape[1] - (width - cell.shape[1]) // 2),
                           (0, 0)), constant_values=255) for cell in cells]
    column = np.concatenate(cells, axis=0)
    label(column, title, scale=0.45)
    return np.pad(column, ((0, 0), (0, 8), (0, 0)), constant_values=255)


def compare_command(root: Path, pack_name: str, object_id: str) -> list[str]:
    _, entry = _entry(root, pack_name, object_id)
    build = pack.read_json(pack.build_report_path(root, pack_name, object_id))
    if not build:
        raise CVError(f"{object_id} has no rendered build yet")
    views = entry.get("views") or []
    evidence = pack.evidence_dir(root, pack_name, object_id)
    results, lines, columns = [], [], []
    for rendered in build.get("views", []):
        number = rendered["view"]
        if not 1 <= number <= len(views):
            continue
        view = views[number - 1]
        render = read_image(root / rendered["file"])
        result = compare_view(reference_view(root, pack_name, view), render)
        lines.append(_line(number, view, result, build["build"]))
        images = result.pop("_images", None)
        result["view"] = number
        results.append(result)
        if images is None:
            continue
        ref_colour, render_colour, ref_shape, render_shape = images
        write_image(evidence / f"{object_id}_cv_survey_{number}.png",
                    survey_image(ref_colour, render_colour, f"{object_id} {_view_name(number, view)}: reference | render"))
        cells = [on_grey(render_colour)]
        if rendered.get("clay") and (root / rendered["clay"]).exists():
            clay = read_image(root / rendered["clay"])
            clay_mask = (clay[..., 3] > 127).astype(np.uint8)
            if bbox(clay_mask) is not None:
                cells.append(on_grey(normalise(clay, clay_mask)[0]))
        cells += [on_grey(ref_colour), overlay_image(ref_colour, render_colour, ref_shape, render_shape)]
        columns.append(_column(cells, SHEET_MAX_CELL, f"{number}: overlap {result['overlap']:.2f}"))
    if columns:
        sheet = np.concatenate(columns, axis=1)
        if sheet.shape[1] > SHEET_MAX_WIDTH:
            sheet = fit_width(sheet, SHEET_MAX_WIDTH)
        legend = np.full((24, sheet.shape[1], 3), 255, np.uint8)
        clay_row = any(item.get("clay") for item in build.get("views", []))
        label(legend, "rows: render | clay (shape only) | reference | overlay" if clay_row
              else "rows: render | reference | overlay", scale=0.42)
        write_image(evidence / f"{object_id}_compare.png", np.concatenate([legend, sheet], axis=0))
    turnaround = [root / item["file"] for item in build.get("turnaround", [])]
    if turnaround:
        cells = []
        for path in turnaround:
            cell = on_grey(read_image(path))
            scale = 300 / max(cell.shape[:2])
            cells.append(cv2.resize(cell, (round(cell.shape[1] * scale), round(cell.shape[0] * scale)),
                                    interpolation=cv2.INTER_AREA))
        height = max(cell.shape[0] for cell in cells)
        cells = [np.pad(cell, ((0, height - cell.shape[0]), (0, 4), (0, 0)), constant_values=255) for cell in cells]
        per_row = math.ceil(len(cells) / 2)
        rows = []
        for start in range(0, len(cells), per_row):
            row = np.concatenate(cells[start:start + per_row], axis=1)
            rows.append(row)
        width = max(row.shape[1] for row in rows)
        rows = [np.pad(row, ((0, 4), (0, width - row.shape[1]), (0, 0)), constant_values=255) for row in rows]
        write_image(evidence / f"{object_id}_turnaround.png", fit_width(np.concatenate(rows, axis=0), SHEET_MAX_WIDTH))
    overlaps = [result["overlap"] for result in results if "overlap" in result]
    report = {"build": build["build"], "final": build.get("final", False), "at": _now(), "views": results,
              "mean_overlap": round(sum(overlaps) / len(overlaps), 3) if overlaps else None}
    pack.cv_report_path(root, pack_name, object_id).write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    if overlaps:
        worst = min(results, key=lambda result: result.get("overlap", 1.0))
        lines.append(f"CV build {build['build']} summary: mean outline overlap {report['mean_overlap']:.2f}, lowest view "
                     f"{worst['view']} ({worst['overlap']:.2f}); compare image: {evidence / (object_id + '_compare.png')}; "
                     f"survey per view: {object_id}_cv_survey_<view>.png")
    return lines


def closeup_command(root: Path, pack_name: str, object_id: str, number: int, box: list[float], scale: float) -> list[str]:
    _, entry = _entry(root, pack_name, object_id)
    views = entry.get("views") or []
    if not 1 <= number <= len(views):
        raise CVError(f"--view must be 1 to {len(views)}")
    x0, y0, x1, y1 = box
    if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
        raise CVError("--box is X0 Y0 X1 Y1 as fractions of the object (0 to 1, from its top-left)")
    region = reference_view(root, pack_name, views[number - 1])
    ref_mask, _ = object_mask(region)
    if bbox(ref_mask) is None:
        raise CVError("no object found in the reference box")
    reference = normalise(region, ref_mask)
    build = pack.read_json(pack.build_report_path(root, pack_name, object_id)) or {}
    rendered = next((item for item in build.get("views", []) if item["view"] == number), None)
    images = [reference]
    if rendered:
        render = read_image(root / rendered["file"])
        render_mask = (render[..., 3] > 127).astype(np.uint8)
        if bbox(render_mask) is not None:
            images.append(normalise(render, render_mask))
    if len(images) == 2:
        images = pair_canvas(*images)
    crops = []
    for colour, _ in images:
        height, width = colour.shape[:2]
        crop = on_grey(colour[round(y0 * height):round(y1 * height), round(x0 * width):round(x1 * width)])
        crops.append(cv2.resize(crop, (max(1, round(crop.shape[1] * scale)), max(1, round(crop.shape[0] * scale))),
                                interpolation=cv2.INTER_CUBIC))
    height = max(crop.shape[0] for crop in crops)
    crops = [np.pad(crop, ((0, height - crop.shape[0]), (0, 8), (0, 0)), constant_values=255) for crop in crops]
    out = pack.evidence_dir(root, pack_name, object_id) / f"{object_id}_cv_closeup_{number}.png"
    write_image(out, fit_width(np.concatenate(crops, axis=1), SHEET_MAX_WIDTH))
    shown = "reference left, render right" if len(crops) == 2 else "reference only: not built yet"
    return [f"CLOSEUP {_view_name(number, views[number - 1])} box {x0:g} {y0:g} {x1:g} {y1:g}: {out} ({shown})"]


CONTACT_CELL = 200  # px, each thumbnail of a material-search sheet


def contact_sheet(paths: list[Path], labels: list[str], out: Path, per_row: int = 6) -> Path:
    """Thumbnails in a labelled grid (``pack.py material-search --previews``): one image to compare
    candidate textures by pattern, scale, relief and colour."""
    cells = []
    for path, text in zip(paths, labels):
        try:
            image = on_grey(read_image(path))
        except CVError:
            continue
        scale = CONTACT_CELL / max(image.shape[:2])
        image = cv2.resize(image, (max(1, round(image.shape[1] * scale)), max(1, round(image.shape[0] * scale))),
                           interpolation=cv2.INTER_AREA)
        cell = np.full((CONTACT_CELL + 22, CONTACT_CELL, 3), 255, np.uint8)
        cell[:image.shape[0], :image.shape[1]] = image
        label(cell, text[-34:], origin=(3, CONTACT_CELL + 15), scale=0.36)
        cells.append(np.pad(cell, ((0, 4), (0, 4), (0, 0)), constant_values=220))
    if not cells:
        raise CVError("no thumbnail could be read")
    blank = np.full_like(cells[0], 255)
    rows = []
    for start in range(0, len(cells), per_row):
        row = cells[start:start + per_row]
        row += [blank] * (per_row - len(row))
        rows.append(np.concatenate(row, axis=1))
    return write_image(out, fit_width(np.concatenate(rows, axis=0), SHEET_MAX_WIDTH))


OBSERVE_TILE = 420  # px, each magnified tile of the observe sheets
OBSERVE_GRID = 3


def _texture_energy(bgr: np.ndarray, mask: np.ndarray) -> float:
    """How busy the surface is: mean absolute Laplacian of the lightness inside ``mask`` (0 flat, ~0.1 busy)."""
    grey = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    laplacian = np.abs(cv2.Laplacian(grey, cv2.CV_32F, ksize=3))
    inside = cv2.erode(mask, np.ones((3, 3), np.uint8)) > 0
    return round(float(laplacian[inside].mean()), 3) if inside.any() else 0.0


def region_stats(bgr: np.ndarray, mask: np.ndarray) -> dict:
    """Colour statistics of the object pixels in a region: what a material's variation needs."""
    pixels = bgr[mask > 0].reshape(-1, 3)
    if len(pixels) < 4:
        return {"empty": True}
    lab = cv2.cvtColor(pixels.reshape(-1, 1, 3), cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float32)
    lightness = lab[:, 0] / 255.0
    order = np.argsort(lightness)
    dark = pixels[order[: max(1, len(order) // 20)]].mean(axis=0)
    light = pixels[order[-max(1, len(order) // 20):]].mean(axis=0)
    chroma = np.hypot(lab[:, 1] - 128, lab[:, 2] - 128)
    return {"mean": hex_colour(pixels.mean(axis=0)), "darkest_5pct": hex_colour(dark), "lightest_5pct": hex_colour(light),
            "lightness_spread": round(float(lightness.std()), 3), "chroma_spread": round(float(chroma.std() / 128), 3),
            "texture": _texture_energy(bgr, mask), "colours": dominant_colours(bgr, mask, 3)}


def _stats_text(stats: dict) -> str:
    if stats.get("empty"):
        return "no object pixels"
    colours = " ".join(f"{c['colour']} {round(c['share'] * 100)}%" for c in stats["colours"])
    return (f"mean {stats['mean']}, dark {stats['darkest_5pct']} / light {stats['lightest_5pct']}, lightness spread "
            f"{stats['lightness_spread']:.3f}, colour spread {stats['chroma_spread']:.3f}, texture {stats['texture']:.3f}; "
            f"colours {colours}")


def observe_command(root: Path, pack_name: str, object_id: str, number: int | None = None,
                    grid: int = OBSERVE_GRID) -> list[str]:
    """Magnified tiles of every recorded view (or ``number``), each with its colour variation and
    texture strength: what to look at closely before modelling the details, imperfections,
    variations and materials."""
    _, entry = _entry(root, pack_name, object_id)
    views = entry.get("views") or []
    if not views:
        raise CVError(f"{object_id} has no recorded views: run `cv.py views`, then `pack.py views`")
    numbers = [number] if number else list(range(1, len(views) + 1))
    evidence = pack.evidence_dir(root, pack_name, object_id)
    lines = []
    for n in numbers:
        if not 1 <= n <= len(views):
            raise CVError(f"--view must be 1 to {len(views)}")
        region = reference_view(root, pack_name, views[n - 1])
        mask, _ = object_mask(region)
        box = bbox(mask)
        if box is None:
            lines.append(f"OBSERVE {_view_name(n, views[n - 1])}: no object found")
            continue
        x0, y0, x1, y1 = box
        colour, shape = region[y0:y1, x0:x1, :3], mask[y0:y1, x0:x1]
        height, width = shape.shape
        tiles, overall = [], region_stats(colour, shape)
        lines.append(f"OBSERVE {_view_name(n, views[n - 1])} whole object {width}x{height} px: {_stats_text(overall)}")
        for row in range(grid):
            for col in range(grid):
                ty0, ty1 = round(row * height / grid), round((row + 1) * height / grid)
                tx0, tx1 = round(col * width / grid), round((col + 1) * width / grid)
                tile_mask = shape[ty0:ty1, tx0:tx1]
                fractions = (tx0 / width, ty0 / height, tx1 / width, ty1 / height)
                name = f"r{row + 1}c{col + 1}"
                if tile_mask.mean() < 0.03:
                    tiles.append(None)
                    continue
                stats = region_stats(colour[ty0:ty1, tx0:tx1], tile_mask)
                lines.append(f"OBSERVE {n} {name} box {fractions[0]:.2f} {fractions[1]:.2f} {fractions[2]:.2f} "
                             f"{fractions[3]:.2f}: {_stats_text(stats)}")
                tile = on_grey(np.dstack([colour[ty0:ty1, tx0:tx1], tile_mask * 255]))
                scale = OBSERVE_TILE / max(tile.shape[:2])
                tile = cv2.resize(tile, (max(1, round(tile.shape[1] * scale)), max(1, round(tile.shape[0] * scale))),
                                  interpolation=cv2.INTER_CUBIC if scale > 1 else cv2.INTER_AREA)
                tile = np.pad(tile, ((0, OBSERVE_TILE - tile.shape[0]), (0, OBSERVE_TILE - tile.shape[1]), (0, 0)),
                              constant_values=255)
                label(tile, f"{name} ({fractions[0]:.2f},{fractions[1]:.2f})-({fractions[2]:.2f},{fractions[3]:.2f})",
                      scale=0.45)
                tiles.append(tile)
        blank = np.full((OBSERVE_TILE, OBSERVE_TILE, 3), 255, np.uint8)
        rows = [np.concatenate([np.pad(t if t is not None else blank, ((0, 6), (0, 6), (0, 0)), constant_values=230)
                                for t in tiles[r * grid:(r + 1) * grid]], axis=1) for r in range(grid)]
        out = write_image(evidence / f"{object_id}_cv_observe_{n}.png", fit_width(np.concatenate(rows, axis=0), SHEET_MAX_WIDTH))
        lines.append(f"OBSERVE image {n}: {out} (tiles magnified; boxes are fractions of the object for cv.py closeup/sample)")
    return lines


def sample_command(root: Path, pack_name: str, object_id: str, number: int, boxes: list[list[float]]) -> list[str]:
    """Colour statistics of the reference inside each box (fractions of the object, as closeup),
    and of the latest render in the same place when there is one."""
    _, entry = _entry(root, pack_name, object_id)
    views = entry.get("views") or []
    if not 1 <= number <= len(views):
        raise CVError(f"--view must be 1 to {len(views)}")
    region = reference_view(root, pack_name, views[number - 1])
    ref_mask, _ = object_mask(region)
    if bbox(ref_mask) is None:
        raise CVError("no object found in the reference box")
    images = [normalise(region, ref_mask)]
    build = pack.read_json(pack.build_report_path(root, pack_name, object_id)) or {}
    rendered = next((item for item in build.get("views", []) if item["view"] == number), None)
    if rendered and (root / rendered["file"]).exists():
        render = read_image(root / rendered["file"])
        render_mask = (render[..., 3] > 127).astype(np.uint8)
        if bbox(render_mask) is not None:
            images = list(pair_canvas(images[0], normalise(render, render_mask)))
    lines = []
    for box in boxes:
        x0, y0, x1, y1 = box
        if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
            raise CVError("--box is X0 Y0 X1 Y1 as fractions of the object (0 to 1, from its top-left)")
        for name, (colour, shape) in zip(("reference", "render"), images):
            h, w = shape.shape[:2]
            ys, xs = slice(round(y0 * h), round(y1 * h)), slice(round(x0 * w), round(x1 * w))
            stats = region_stats(colour[ys, xs, :3], shape[ys, xs])
            lines.append(f"SAMPLE {number} box {x0:g} {y0:g} {x1:g} {y1:g} {name}: {_stats_text(stats)}")
    return lines


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------------------------- #
# Command line
# --------------------------------------------------------------------------------- #

def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("views", "grid"):
        command = commands.add_parser(name)
        command.add_argument("pack")
        command.add_argument("id")
        command.add_argument("--ref", type=int, default=1, help="reference image number")
    for name in ("measure", "compare"):
        command = commands.add_parser(name)
        command.add_argument("pack")
        command.add_argument("id")
    command = commands.add_parser("closeup")
    command.add_argument("pack")
    command.add_argument("id")
    command.add_argument("--view", type=int, required=True)
    command.add_argument("--box", type=float, nargs=4, required=True, metavar=("X0", "Y0", "X1", "Y1"))
    command.add_argument("--scale", type=float, default=2.0)
    command = commands.add_parser("observe", help="magnified tiles of the reference with their colour variation")
    command.add_argument("pack")
    command.add_argument("id")
    command.add_argument("--view", type=int, help="one recorded view (default: every view)")
    command.add_argument("--grid", type=int, default=OBSERVE_GRID, help="tiles per side")
    command = commands.add_parser("sample", help="colour statistics of the reference (and render) in boxes")
    command.add_argument("pack")
    command.add_argument("id")
    command.add_argument("--view", type=int, required=True)
    command.add_argument("--box", type=float, nargs=4, action="append", required=True, metavar=("X0", "Y0", "X1", "Y1"))
    return parser


def main(argv: list[str] | None = None, root: Path = pack.REPO_ROOT) -> int:
    args = _parser().parse_args(argv)
    if cv2 is None:
        print(f"error: the CV libraries are not installed ({IMPORT_ERROR}); run: bash tools/assetgen/install_cv.sh",
              file=sys.stderr)
        return 2
    try:
        if args.command == "views":
            lines = views_command(root, args.pack, args.id, args.ref)
        elif args.command == "grid":
            lines = grid_command(root, args.pack, args.id, args.ref)
        elif args.command == "measure":
            lines = measure_command(root, args.pack, args.id)
        elif args.command == "compare":
            lines = compare_command(root, args.pack, args.id)
        elif args.command == "observe":
            lines = observe_command(root, args.pack, args.id, args.view, args.grid)
        elif args.command == "sample":
            lines = sample_command(root, args.pack, args.id, args.view, args.box)
        else:
            lines = closeup_command(root, args.pack, args.id, args.view, args.box, args.scale)
    except (CVError, pack.PackError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
