#!/usr/bin/env python3
"""Cut the forest sprites and write the readable descriptions and the text-to-image prompts.

Everything is derived from ``assets/data/forest/profiles/forest_*.json``, the style blocks in
``assets/data/forest/forest_style.json`` and the measured palette, so the description a person
reads, the prompt sent to the image generator and the model a generator script builds all come
from the same source.

Subcommands::

    sprites [--upscaled-dir DIR]   cut every sprite crop from the mockup into
                                   design/levels/reference/forest/sprites/<name>.png (native size);
                                   with --upscaled-dir also write 3x-upscaled copies for image-generator uploads
    docs                           write design/levels/forest/object_descriptions.md and prompts.md
    prompt <name> [--sheet turnaround|terrain_topdown]
                                   print one prompt (a profile name, or "scene")

Requires Pillow. Run from anywhere; paths are resolved from the repository root.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "assets" / "data" / "forest"
PROFILES_DIR = DATA_DIR / "profiles"
STYLE_FILE = DATA_DIR / "forest_style.json"
SPRITES_DIR = REPO_ROOT / "design" / "levels" / "reference" / "forest" / "sprites"
DOCS_DIR = REPO_ROOT / "design" / "levels" / "forest"
UPSCALE = 3

sys.path.insert(0, str(REPO_ROOT / "tools" / "blender" / "forest"))
import palette  # noqa: E402  (plain-Python module, no bpy)


def load_profiles() -> list[dict]:
    """Every ``forest_*.json`` profile, terrain last, otherwise sorted by name."""
    profiles = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(PROFILES_DIR.glob("forest_*.json"))]
    return sorted(profiles, key=lambda profile: (profile["kind"] == "terrain", profile["name"]))


def load_style() -> dict:
    """Style blocks with the ``{palette_<slot>_<tone>}`` tokens filled from the measured palette."""
    style = json.loads(STYLE_FILE.read_text(encoding="utf-8"))
    tokens = {f"palette_{slot}_{tone}": palette.hex_for(slot, tone) for slot in palette.slot_names() for tone in palette.TONES}
    style["palette_sentence"] = style["palette_sentence"].format(**tokens)
    return style


def sprite_boxes(profile: dict) -> list[tuple[str, list[int], str]]:
    """``(file stem, crop box, what it shows)`` for the profile's main sprite and its extras."""
    boxes = [(profile["name"], profile["sprite"]["crop"], profile["sprite"]["shows"])]
    boxes += [(f"{profile['name']}_{extra['name']}", extra["crop"], extra["shows"]) for extra in profile.get("sprite_extra", [])]
    return boxes


def cut_sprites(upscaled_dir: Path | None) -> None:
    """Write every sprite crop, checking each box lies inside the mockup."""
    SPRITES_DIR.mkdir(parents=True, exist_ok=True)
    if upscaled_dir:
        upscaled_dir.mkdir(parents=True, exist_ok=True)
    for profile in load_profiles():
        image = Image.open(REPO_ROOT / profile["sprite"]["image"]).convert("RGB")
        for stem, box, _ in sprite_boxes(profile):
            x0, y0, x1, y1 = box
            if not (0 <= x0 < x1 <= image.width and 0 <= y0 < y1 <= image.height):
                raise SystemExit(f"{stem}: crop {box} lies outside the {image.width}x{image.height} mockup")
            crop = image.crop(tuple(box))
            crop.save(SPRITES_DIR / f"{stem}.png")
            if upscaled_dir:
                crop.resize((crop.width * UPSCALE, crop.height * UPSCALE), Image.Resampling.LANCZOS).save(upscaled_dir / f"{stem}.png")
            print(f"sprite {stem}: {crop.width}x{crop.height}")


def object_prompt(profile: dict, style: dict) -> str:
    """The 360-degree turnaround prompt for one component.

    The whole mockup is attached as the first reference image (and the component's sprite crop as the
    second), so the prompt first says what the whole picture contains and looks like, then tells the
    generator which single component to find in it and regenerate on its own (terrain becomes a diorama block).
    """
    is_terrain = profile["kind"] == "terrain"
    subject = style["terrain_prompt"] if is_terrain else profile["description"]
    layout = style["terrain_turnaround_layout"] if is_terrain else style["turnaround_layout"]
    task = style["component_task"].format(title=profile["title"], where=profile["where_in_image"])
    return "\n\n".join([
        f"Reference image: {style['scene_reference']}",
        f"Task: {task}",
        f"Component description: {subject}",
        f"Focus: {profile['turnaround_focus']}.",
        f"Layout: {layout}",
        f"Art style: {style['master_style']}",
        style["palette_sentence"] + ".",
        f"Exclude: {style['negative']}",
    ])


def topdown_prompt(style: dict) -> str:
    """The top-down ground guide prompt for the terrain."""
    return "\n\n".join([style["terrain_topdown_prompt"], f"Art style: {style['master_style']}", style["palette_sentence"] + ".",
                        f"Exclude: {style['negative']}"])


def scene_prompt(style: dict) -> str:
    """The whole-scene prompt (matches the mockup)."""
    return "\n\n".join([style["scene_prompt"], f"Art style: {style['master_style']}", style["palette_sentence"] + ".",
                        f"Exclude: {style['negative']}"])


def write_object_descriptions(profiles: list[dict]) -> Path:
    """Write the human-readable catalogue of every object."""
    lines = [
        "# Forest biome: object descriptions", "",
        "*Generated by `tools/assets/forest_reference.py docs` from `assets/data/forest/profiles/`. Edit the profile, not this file.*", "",
        "**How to read this.** Every point in a *look* list names its **basis**: **sprite** means it can be seen in the mockup crop "
        "(`design/levels/reference/forest/forest_biome_mockup.jpg`); **Proposal** means the mockup does not show it and it is a design choice to "
        "accept or change; **Estimate** means a size or angle measured off the picture and scaled to the 1.7 m trainer. Sizes are metres in "
        "Blender axes (x width, y depth, z height).", "",
        "| Asset | Kind | Size x / y / z (m) | Triangle budget | Sprite | Godot file |", "|---|---|---|---|---|---|",
    ]
    for p in profiles:
        s = p["size_m"]
        lines.append(f"| [{p['title']}](#{p['name'].replace('_', '-')}) | {p['kind']} | {s['x']} / {s['y']} / {s['z']} | {p['triangle_budget']:,} | "
                     f"`sprites/{p['name']}.png` | `{p['godot']['file']}` |")
    for p in profiles:
        s = p["size_m"]
        lines += ["", f"## {p['name']}", "", f"**{p['title']}** ({p['kind']})", "",
                  f"![sprite](../reference/forest/sprites/{p['name']}.png)", "",
                  f"*Sprite: {p['sprite']['shows']}.*", "", f"**Where in the mockup:** {p['where_in_image']}.", "", p["description"], "",
                  f"**Size.** {s['x']} x {s['y']} x {s['z']} m. {p['size_note']}", "",
                  f"**Origin.** {p['origin']}", "", "| Look | Basis |", "|---|---|"]
        lines += [f"| {item['feature']} | {item['basis']} |" for item in p["look"]]
        lines += ["", "**Not visible in the sprite (invented or inferred):** " + ", ".join(p["not_in_sprite"]) + ".", "",
                  "**Materials:** " + ", ".join(f"`{m}`" for m in p["materials"]) + ".", "",
                  f"**Godot.** File `{p['godot']['file']}`. Collision: {p['godot']['collision']}. "
                  + ("Markers: " + "; ".join(p['godot']['markers']) + "." if p["godot"]["markers"] else "No markers.")]
    path = DOCS_DIR / "object_descriptions.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_prompts(profiles: list[dict], style: dict) -> Path:
    """Write the master style, the scene and terrain prompts and every per-asset prompt."""
    lines = [
        "# Forest biome: art style and text-to-image prompts", "",
        "*Generated by `tools/assets/forest_reference.py docs` from `assets/data/forest/forest_style.json` and the profiles. "
        "Edit those, not this file.*", "",
        f"**Style: {style['style_name']}.** Quality target: {style['quality_target']}.", "",
        "## Master style block (append to every prompt)", "", "```text", style["master_style"], "```", "",
        "## Palette sentence (measured from the mockup, filled by `tools/blender/forest/palette.py`)", "", "```text", style["palette_sentence"], "```", "",
        "## Negative block", "", "```text", style["negative"], "```", "",
        "## 360-degree turnaround layout (objects)", "", "```text", style["turnaround_layout"], "```", "",
        f"Aspect ratio for the sheet: `{style['turnaround_aspect']}` (a 4 x 2 grid of square cells).", "",
        "## What the whole reference image contains (starts every component prompt)", "", "```text", style["scene_reference"], "```", "",
        "## Component task line (per component)", "", "```text", style["component_task"], "```", "",
        "## Scene prompt (regenerate the whole mockup)", "", "```text", scene_prompt(style), "```", "",
        "## Terrain prompts", "", "**Terrain diorama, 360-degree sheet**", "", "```text", object_prompt(next(p for p in profiles if p["kind"] == "terrain"), style), "```", "",
        "**Terrain top-down ground guide (splat colour reference)**", "", "```text", topdown_prompt(style), "```", "",
        "## Per-asset turnaround prompts", "",
        "Each prompt is sent with two image references: the WHOLE mockup first, then the component's close-up sprite crop.", "",
    ]
    for p in profiles:
        if p["kind"] == "terrain":
            continue
        lines += [f"### {p['name']}", "", "```text", object_prompt(p, style), "```", ""]
    path = DOCS_DIR / "prompts.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sprites = sub.add_parser("sprites")
    sprites.add_argument("--upscaled-dir", type=Path)
    sub.add_parser("docs")
    prompt = sub.add_parser("prompt")
    prompt.add_argument("name")
    prompt.add_argument("--sheet", choices=("turnaround", "terrain_topdown"), default="turnaround")
    args = parser.parse_args()

    if args.command == "sprites":
        cut_sprites(args.upscaled_dir)
        return 0
    profiles, style = load_profiles(), load_style()
    if args.command == "docs":
        print(f"wrote {write_object_descriptions(profiles).relative_to(REPO_ROOT)}")
        print(f"wrote {write_prompts(profiles, style).relative_to(REPO_ROOT)}")
        return 0
    if args.name == "scene":
        print(scene_prompt(style))
    elif args.sheet == "terrain_topdown":
        print(topdown_prompt(style))
    else:
        match = next((p for p in profiles if p["name"] == args.name), None)
        if match is None:
            raise SystemExit(f"no profile named {args.name!r}; have {[p['name'] for p in profiles]}")
        print(object_prompt(match, style))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
