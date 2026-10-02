"""Tests for tools/assetgen/pack.py (offline: no command here touches the network).

Run: python3 -m unittest discover -s tests/tools/assetgen -p "*_test.py"
"""
import io
import json
import struct
import sys
import tempfile
import unittest
import zlib
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from string import Template

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools" / "assetgen"))
import pack  # noqa: E402

REPO = Path(__file__).resolve().parents[3]


def png_bytes(width: int, height: int, rgba=(200, 120, 60, 255)) -> bytes:
    """A small solid PNG of the given size (stdlib only)."""
    row = b"\x00" + bytes(rgba) * width
    raw = row * height

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return (pack.PNG_SIGNATURE + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


FILLED_ANALYSIS = """## Analysis

### What it is
a thing

### Views
view 1 is the front

### Size and proportions
0.4 m tall

### Close observation
tile r2c2: fine scratches, a darker band at the base

### Parts inventory
| # | part | count | size (m) | position and orientation | shape and how to model it | geometry detail | nuances |
|---|---|---|---|---|---|---|---|
| 1 | body | 1 | 0.4 | centre | lathe | bevelled rim | none |

### Materials and shaders
S1 painted metal, #806040 to #a08060, roughness 0.4 to 0.6, scratches

### Details and nuances
seam at the back

### Skills, add-ons and tools
kit.lathe

### Build plan
body first
"""

# A builder's review of its build and its Handoff, as builder_guide.md sections 6 and 7 describe.
REVIEW_AND_HANDOFF = """
## Cycle 1
### What matches
the outline in view 1
### Needs improving
1. the rim is 8 % too thin in view 1

## Handoff
### Understanding
a turned vessel with a rolled rim
### Next step: part tasks
1. rim: from 4 mm to 4.3 mm thick, view 1
### Standing rules
- one render cycle per builder
"""


class PackTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.image = self.root / "upload.PNG"
        self.image.write_bytes(png_bytes(40, 30))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _flow_pack(self, **extra) -> None:
        pack.init(self.root, "demo", self.image)
        pack.set_style(self.root, "demo", "style words")
        pack.add(self.root, "demo", "object_a", name="object a", where="left side",
                 details="part one, part two", **extra)

    def _skip_pack(self, **extra) -> None:
        pack.init(self.root, "demo", self.image, skip_flow=True)
        pack.set_style(self.root, "demo", "the style of the reference image")
        pack.add(self.root, "demo", "object_a", name="object a", where="left side", details="part one",
                 references=[self.image], **extra)

    # ----------------------------------------------------------------------- init and add

    def test_init_creates_the_folder_and_copies_the_source(self) -> None:
        manifest = pack.init(self.root, "demo", self.image)
        folder = self.root / "design" / "asset-packs" / "demo"
        self.assertEqual(manifest["source"], "source.png")
        self.assertFalse(manifest["skip_flow"])
        self.assertTrue((folder / "flow").is_dir())
        self.assertEqual((folder / "source.png").read_bytes(), self.image.read_bytes())
        with self.assertRaises(pack.PackError):
            pack.init(self.root, "demo", self.image)

    def test_init_refuses_what_is_not_an_image(self) -> None:
        text = self.root / "notes.txt"
        text.write_text("x")
        with self.assertRaises(pack.PackError):
            pack.init(self.root, "demo", text)

    def test_skip_flow_pack_keeps_references_and_needs_them(self) -> None:
        manifest = pack.init(self.root, "demo", self.image, skip_flow=True)
        self.assertTrue(manifest["skip_flow"])
        self.assertTrue((self.root / "design" / "asset-packs" / "demo" / "references").is_dir())
        with self.assertRaises(pack.PackError):
            pack.add(self.root, "demo", "object_a", name="a", where="w", details="d")
        entry = pack.add(self.root, "demo", "object_a", name="a", where="w", details="d", references=[self.image])
        self.assertEqual(entry["references"], ["source.png"])  # the source image itself is used as it is
        other = self.root / "other.png"
        other.write_bytes(png_bytes(10, 10))
        second = pack.add(self.root, "demo", "object_b", name="b", where="w", details="d", references=[other, other])
        self.assertEqual(second["references"], ["references/object_b_1.png", "references/object_b_1.png"])
        self.assertNotIn("flow", second)

    def test_flow_pack_refuses_references(self) -> None:
        pack.init(self.root, "demo", self.image)
        with self.assertRaises(pack.PackError):
            pack.add(self.root, "demo", "object_a", name="a", where="w", details="d", references=[self.image])

    def test_add_numbers_objects_and_checks_ids_mount_and_budget(self) -> None:
        self._flow_pack()
        second = pack.add(self.root, "demo", "object_b", name="b", where="w", details="d", mount="wall", budget=1200)
        self.assertEqual(second["number"], 2)
        self.assertEqual((second["budget"], second["budget_why"]), (1200, "given by the user"))
        self.assertEqual(pack.flow_name(second, 3, ".png"), "02_object_b_3.png")
        for bad in ({"object_id": "Object C"}, {"object_id": "object_a"}, {"object_id": "object_c", "mount": "ceiling"},
                    {"object_id": "object_c", "budget": 0}):
            arguments = {"name": "x", "where": "x", "details": "x", **bad}
            with self.assertRaises(pack.PackError):
                pack.add(self.root, "demo", **arguments)

    def test_add_refuses_look_words_so_the_look_comes_only_from_the_style(self) -> None:
        pack.init(self.root, "demo", self.image)
        for words in ("a cute stool", "3D chair", "low-poly rock", "stylized lamp"):
            with self.assertRaises(pack.PackError):
                pack.add(self.root, "demo", "object_a", name=words, where="w", details="d")
        pack.add(self.root, "demo", "object_a", name="rendering desk", where="left", details="cuter than none")
        self.assertEqual(pack.look_words("A Cosy, toon-ish 3d render"), ["3d", "cosy", "render", "toon"])

    # ----------------------------------------------------------------------- Google Flow

    def test_flow_call_sets_grid_architect_up_with_exact_prompts_and_the_source_only(self) -> None:
        self._flow_pack()
        call = pack.flow_call(self.root, "demo", "object_a")
        self.assertEqual(call["tool"], "mcp__google-flow__flow_use_grid_architect")
        arguments = call["arguments"]
        self.assertIn("the object a (part one, part two; left side in the reference)", arguments["theme_prompt"])
        self.assertTrue(arguments["theme_prompt"].endswith("Art style for every shot: style words."))
        self.assertEqual(len(arguments["shot_prompts"]), 5)
        self.assertTrue(all("object a" in shot for shot in arguments["shot_prompts"]))
        self.assertEqual(arguments["references"], [str((self.root / "design/asset-packs/demo/source.png").resolve())])
        self.assertEqual((arguments["engine"], arguments["ratio"]), (pack.FLOW_ENGINE, pack.FLOW_RATIO))
        self.assertNotIn("auto_confirm", arguments)  # it only sets up: the user generates
        texts = [arguments["theme_prompt"], *arguments["shot_prompts"]]
        self.assertFalse(any("$" in text for text in texts))
        fixed = Template((pack.TEMPLATES / "flow_theme_prompt.txt").read_text()).substitute(
            name="", details="", where="", style="")
        self.assertEqual(pack.look_words(fixed), [])

    def test_flow_call_needs_a_style_and_a_flow_pack(self) -> None:
        pack.init(self.root, "demo", self.image)
        pack.add(self.root, "demo", "object_a", name="a", where="w", details="d")
        with self.assertRaises(pack.PackError):
            pack.flow_call(self.root, "demo", "object_a")
        with self.assertRaises(pack.PackError):
            pack.set_style(self.root, "demo", "   ")
        self._tmp.cleanup()
        self.setUp()
        self._skip_pack()
        with self.assertRaises(pack.PackError):
            pack.flow_call(self.root, "demo", "object_a")

    def test_flow_record_copies_the_images_in_order_or_records_a_refusal(self) -> None:
        self._flow_pack()
        front, back = self.root / "front.png", self.root / "back.jpg"
        front.write_bytes(png_bytes(64, 36))
        back.write_bytes(b"\xff\xd8\xff\xc0\x00\x11\x08\x00\x10\x00\x20\x03\x01\x22\x00\x02\x11\x01\x03\x11\x01")
        with self.assertRaises(pack.PackError):
            pack.flow_record(self.root, "demo", "object_a", None, None)
        with self.assertRaises(pack.PackError):
            pack.flow_record(self.root, "demo", "object_a", [front], "refused too")
        result = pack.flow_record(self.root, "demo", "object_a", [front, back], None)
        self.assertEqual(result["images"], ["flow/01_object_a_1.png", "flow/01_object_a_2.jpg"])
        entry = pack.find_object(pack.load(self.root, "demo"), "object_a")
        self.assertEqual(entry["references"], result["images"])
        self.assertEqual(pack.image_size(pack.reference_paths(self.root, "demo", entry)[0]), (64, 36))
        pack.flow_record(self.root, "demo", "object_a", [front], None)  # a new round replaces the old images
        self.assertEqual(sorted(p.name for p in (self.root / "design/asset-packs/demo/flow").iterdir()),
                         ["01_object_a_1.png"])
        pack.flow_record(self.root, "demo", "object_a", None, "unsafe content")
        self.assertEqual(pack.status(self.root, "demo")[0]["next"], "refused")

    # ----------------------------------------------------------------------- images and views

    def test_image_size_reads_png_jpeg_and_webp_headers(self) -> None:
        cases = {
            "a.png": (png_bytes(7, 5), (7, 5)),
            "a.jpg": (b"\xff\xd8\xff\xe0\x00\x04ab\xff\xc0\x00\x11\x08\x00\x64\x00\xc8" + b"\x00" * 12, (200, 100)),
            "a.webp": (b"RIFF\x00\x00\x00\x00WEBPVP8X\x0a\x00\x00\x00\x00\x00\x00\x00"
                       + (299).to_bytes(3, "little") + (149).to_bytes(3, "little"), (300, 150)),
        }
        for name, (data, size) in cases.items():
            path = self.root / name
            path.write_bytes(data)
            self.assertEqual(pack.image_size(path), size, name)
        bad = self.root / "bad.png"
        bad.write_bytes(b"nothing")
        with self.assertRaises(pack.PackError):
            pack.image_size(bad)

    def test_views_are_checked_against_the_image_and_record_the_camera(self) -> None:
        self._skip_pack()
        views = pack.set_views(self.root, "demo", "object_a", [[1, -90, 10, 2, 3, 38, 29], [1, 0, 0, 0, 0, 20, 20]])
        self.assertEqual(views[0], {"ref": 1, "image": "source.png", "azimuth": 270.0, "elevation": 10.0,
                                    "box": [2, 3, 38, 29]})
        entry = pack.find_object(pack.load(self.root, "demo"), "object_a")
        self.assertEqual(entry["camera"], {"lens": pack.DEFAULT_LENS_MM})
        pack.set_views(self.root, "demo", "object_a", [[1, 0, 0, 0, 0, 20, 20]], ortho=True)
        self.assertEqual(pack.find_object(pack.load(self.root, "demo"), "object_a")["camera"], {"ortho": True})
        for bad in ([[2, 0, 0, 0, 0, 20, 20]], [[1, 0, 95, 0, 0, 20, 20]], [[1, 0, 0, 0, 0, 41, 20]],
                    [[1, 0, 0, 10, 10, 5, 20]], [[1, 0, 0, 0, 0, 8, 8]], []):
            with self.assertRaises(pack.PackError):
                pack.set_views(self.root, "demo", "object_a", bad)
        with self.assertRaises(pack.PackError):
            pack.set_views(self.root, "demo", "object_a", [[1, 0, 0, 0, 0, 20, 20]], lens=50, ortho=True)

    def test_views_signature_changes_with_the_views(self) -> None:
        self._skip_pack()
        pack.set_views(self.root, "demo", "object_a", [[1, 0, 0, 0, 0, 20, 20]])
        first = pack.views_signature(pack.find_object(pack.load(self.root, "demo"), "object_a"))
        pack.set_views(self.root, "demo", "object_a", [[1, 0, 5, 0, 0, 20, 20]])
        self.assertNotEqual(first, pack.views_signature(pack.find_object(pack.load(self.root, "demo"), "object_a")))

    # ----------------------------------------------------------------------- skills, budget, kit

    def test_skills_list_and_record(self) -> None:
        self._skip_pack()
        skill = self.root / ".claude" / "skills" / "skill_x"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text('---\nname: skill_x\ndescription: "Does x: well"\n---\nbody\n')
        manual = self.root / ".claude" / "skills" / "skill_y"
        manual.mkdir(parents=True)
        (manual / "SKILL.md").write_text("---\nname: skill_y\ndescription: y\ndisable-model-invocation: true\n---\n")
        self.assertEqual([(row["name"], row["description"]) for row in pack.skills_list(self.root)],
                         [("skill_x", "Does x: well")])
        with self.assertRaises(pack.PackError):
            pack.set_skills(self.root, "demo", "object_a", ["not_installed"])
        with self.assertRaises(pack.PackError):
            pack.set_skills(self.root, "demo", "object_a", ["skill_y"])
        self.assertEqual(pack.set_skills(self.root, "demo", "object_a", ["skill_x"]), ["skill_x"])
        self.assertEqual(pack.set_skills(self.root, "demo", "object_a", []), [])

    def test_budget_needs_a_reason_and_keeps_the_users_number(self) -> None:
        self._skip_pack()
        with self.assertRaises(pack.PackError):
            pack.set_budget(self.root, "demo", "object_a", 5000, "  ")
        self.assertEqual(pack.set_budget(self.root, "demo", "object_a", 5000, "rounded body")["budget"], 5000)
        pack.add(self.root, "demo", "object_b", name="b", where="w", details="d", references=[self.image], budget=900)
        with self.assertRaises(pack.PackError):
            pack.set_budget(self.root, "demo", "object_b", 5000, "more")

    def test_kit_api_lists_public_functions_from_the_source(self) -> None:
        kit = self.root / pack.KIT
        kit.parent.mkdir(parents=True)
        kit.write_text('def box(name, size, *, bevel=0.0):\n    """Make a box."""\n\n\ndef _hidden():\n    pass\n')
        text = pack.kit_api(self.root)
        self.assertIn("kit.box(name, size, *, bevel=0.0)", text)
        self.assertIn("    Make a box.", text)
        self.assertNotIn("_hidden", text)

    # ----------------------------------------------------------------------- notes, brief, done

    def test_notes_template_starts_empty_and_the_checks_find_what_is_missing(self) -> None:
        text = Template((pack.TEMPLATES / "builder_notes.md").read_text()).substitute(id="x", name="x")
        problems = pack.analysis_problems(text)
        self.assertEqual(len(problems), len(pack.ANALYSIS_SECTIONS))
        self.assertIn("'### Parts inventory' has no rows", problems)
        self.assertEqual(pack.analysis_problems(FILLED_ANALYSIS), [])
        gap = FILLED_ANALYSIS.replace("| 1 | body | 1 | 0.4 | centre | lathe | bevelled rim | none |",
                                      "| 1 | body | 1 | 0.4 | centre | lathe | bevelled rim | |\n| 2 | nose | 1 |")
        self.assertEqual(pack.analysis_problems(gap),
                         ["'### Parts inventory' rows 1, 2 leave cells empty: fill every column, the nuances too"])
        self.assertFalse(pack.has_cycle(FILLED_ANALYSIS, 1))
        self.assertFalse(pack.has_cycle(FILLED_ANALYSIS + "\n## Cycle 1\n<!-- nothing -->\n", 1))
        self.assertTrue(pack.has_cycle(FILLED_ANALYSIS + "\n## Cycle 1 (quick)\nlegs too long\n## Cycle 2\n", 1))
        self.assertFalse(pack.has_cycle(FILLED_ANALYSIS + "\n## Cycle 12\nx\n", 1))

    def test_brief_creates_the_notes_once_and_fills_every_placeholder(self) -> None:
        self._skip_pack(mount="wall")
        text = pack.brief(self.root, "demo", "object_a")
        notes = pack.notes_path(self.root, "demo", "object_a")
        self.assertTrue(notes.exists())
        self.assertNotIn("$", text)
        self.assertIn("tools/blender/assetgen/packs/demo/object_a.py", text)
        self.assertIn('kit.run(build, origin="back")', text)
        self.assertIn("decide what the reference's detail needs", text)
        self.assertIn("none recorded yet", text)
        self.assertIn(f"{pack.BUILDS_PER_BUILDER} cycle build per builder", text)
        self.assertIn(str(self.root / pack.GUIDES_DIR / "builder_guide.md"), text)
        self.assertIn("SET-UP", text)  # no Handoff yet: the full first-build brief
        notes.write_text("kept")
        pack.brief(self.root, "demo", "object_a")
        self.assertEqual(notes.read_text(), "kept")

    def test_brief_prints_only_the_handoff_and_the_paths_once_the_notes_have_one(self) -> None:
        self._skip_pack()
        pack.brief(self.root, "demo", "object_a")
        notes = pack.notes_path(self.root, "demo", "object_a")
        notes.write_text(notes.read_text().replace("### What it is\n", "### What it is\na turned vessel\n")
                         + REVIEW_AND_HANDOFF)
        evidence = pack.evidence_dir(self.root, "demo", "object_a")
        pack.build_report_path(self.root, "demo", "object_a").write_text(json.dumps({"build": 1}))
        (evidence / "object_a_ref_view_1.png").write_bytes(b"png")
        text = pack.brief(self.root, "demo", "object_a")
        self.assertNotIn("$", text)
        for left_out in ("SET-UP", "## Analysis", "### What it is", "## Cycle 1", "the outline in view 1", "<!--"):
            self.assertNotIn(left_out, text)
        self.assertIn("## Handoff\n### Understanding\na turned vessel with a rolled rim", text)
        self.assertTrue(text.endswith("- one render cycle per builder"))
        for path in (evidence / "object_a_ref_view_1.png", evidence / "object_a_compare.png", notes,
                     self.root / pack.GUIDES_DIR / "builder_guide.md", pack.generator_path(self.root, "demo", "object_a"),
                     pack.parts_dir(self.root, "demo", "object_a"), pack.pack_dir(self.root, "demo") / "source.png"):
            self.assertIn(str(path), text)
        self.assertIn(f"Builds so far: 1 (the standard is {pack.BUILD_CYCLES})", text)
        self.assertIn('subagent_type: "asset-part-builder"', text)

    def test_the_handoff_is_the_last_filled_one_and_never_the_templates_skeleton(self) -> None:
        template = Template((pack.TEMPLATES / "builder_notes.md").read_text()).substitute(id="x", name="x")
        self.assertIn("## Handoff", template)  # its format, inside a comment
        self.assertIsNone(pack.handoff(template))
        self.assertIsNone(pack.handoff(FILLED_ANALYSIS + "\n## Handoff\n### Understanding\n<!-- later -->\n"))
        self.assertIsNone(pack.handoff(FILLED_ANALYSIS + "\n## Handoffs\nnot the section\n"))
        old = "## Handoff\n### Next step: part tasks\n1. an older step\n"
        new = "## Handoff (build 3)\n### Next step: part tasks\n1. the current step\n"
        text = FILLED_ANALYSIS + old + "\n## Cycle 3\nthe review\n" + new + "\n## Report\nall checks pass\n"
        self.assertEqual(pack.handoff(text), new.strip())
        self.assertEqual(pack.cycles_written(text + "\n## Cycle 4\n<!-- not written yet -->\n"), 1)
        self.assertEqual(pack.cycles_written(template), 0)

    def test_job_card_is_written_from_the_template_once_with_the_parts_paths(self) -> None:
        self._skip_pack()
        card = pack.job_card(self.root, "demo", "object_a", "rim")
        self.assertEqual(card, self.root / ".scratch/assetgen/work/demo/object_a/parts/rim/job.md")
        text = card.read_text()
        self.assertNotIn("$", text)
        self.assertIn("- `tools/blender/assetgen/packs/demo/object_a_parts/rim.py`", text)
        self.assertIn("- `.scratch/assetgen/work/demo/object_a/parts/rim/`", text)
        self.assertIn("--python .scratch/assetgen/work/demo/object_a/parts/harness.py -- --part rim", text)
        for heading in ("Part", "What it is", "Comparison", "What needs doing, and why", "Reference crops",
                        "Keep fitting", "You may write", "Test", "Done when"):
            self.assertIsNotNone(pack.section(text, heading, level=2), heading)
        card.write_text("filled in by the lead")
        pack.job_card(self.root, "demo", "object_a", "rim")
        self.assertEqual(card.read_text(), "filled in by the lead")
        for bad in ("Rim", "two parts", pack.SHARED_PART):
            with self.assertRaises(pack.PackError):
                pack.job_card(self.root, "demo", "object_a", bad)
        with self.assertRaises(pack.PackError):
            pack.job_card(self.root, "demo", "object_b", "rim")
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(pack.main(["job-card", "demo", "object_a", "lid"], root=self.root), 0)
        self.assertTrue(output.getvalue().strip().endswith("parts/lid/job.md"))

    def test_brief_needs_a_style_and_a_reference(self) -> None:
        pack.init(self.root, "demo", self.image)
        pack.add(self.root, "demo", "object_a", name="a", where="w", details="d")
        with self.assertRaises(pack.PackError):
            pack.brief(self.root, "demo", "object_a")
        pack.set_style(self.root, "demo", "s")
        with self.assertRaises(pack.PackError):
            pack.brief(self.root, "demo", "object_a")

    def _finished_build(self, triangles: int = 800, final: bool = True, baked: bool = True) -> None:
        pack.generator_path(self.root, "demo", "object_a").parent.mkdir(parents=True, exist_ok=True)
        pack.generator_path(self.root, "demo", "object_a").write_text("# generator")
        pack.glb_path(self.root, "demo", "object_a").parent.mkdir(parents=True, exist_ok=True)
        pack.glb_path(self.root, "demo", "object_a").write_bytes(b"glb")
        evidence = pack.evidence_dir(self.root, "demo", "object_a")
        evidence.mkdir(parents=True, exist_ok=True)
        pack.build_report_path(self.root, "demo", "object_a").write_text(json.dumps(
            {"build": 3, "final": final, "views": [], "report": {"triangles": triangles, "dimensions_m": [1, 1, 1]},
             "bake": {"baked": baked} if final else None}))
        pack.cv_report_path(self.root, "demo", "object_a").write_text(json.dumps({"build": 3}))

    def test_done_needs_the_final_build_its_cv_compare_the_report_and_the_budget(self) -> None:
        self._skip_pack(budget=1000)
        with self.assertRaises(pack.PackError):
            pack.done(self.root, "demo", "object_a")
        self._finished_build(triangles=800, final=False)
        notes = pack.notes_path(self.root, "demo", "object_a")
        notes.write_text(FILLED_ANALYSIS + "\n## Report\nall checks pass\n")
        problems = pack.report_problems(self.root, "demo", "object_a")
        self.assertEqual(len(problems), 1)
        self.assertIn("not a final build", problems[0])
        self._finished_build(triangles=800, baked=False)
        self.assertIn("did not bake", " ".join(pack.report_problems(self.root, "demo", "object_a")))
        self._finished_build(triangles=1200)
        self.assertIn("over the budget", " ".join(pack.report_problems(self.root, "demo", "object_a")))
        self._finished_build(triangles=800)
        result = pack.done(self.root, "demo", "object_a")
        self.assertEqual((result["build"], result["triangles"]), (3, 800))

    def test_status_next_step_follows_the_object_through_the_run(self) -> None:
        self._flow_pack()
        self.assertEqual(pack.status(self.root, "demo")[0]["next"], "flow")
        sheet = self.root / "sheet.png"
        sheet.write_bytes(png_bytes(30, 20))
        pack.flow_record(self.root, "demo", "object_a", [sheet], None)
        row = pack.status(self.root, "demo")[0]
        self.assertEqual((row["next"], row["cycles"]), ("build", "-"))
        with self.assertRaises(pack.PackError):
            pack.accept(self.root, "demo", "object_a")
        pack.brief(self.root, "demo", "object_a")
        notes = pack.notes_path(self.root, "demo", "object_a")
        notes.write_text(notes.read_text() + REVIEW_AND_HANDOFF.replace("## Handoff", "## Cycle 2\nthe roof 0.04 lighter\n\n## Handoff"))
        row = pack.status(self.root, "demo")[0]
        self.assertEqual((row["next"], row["cycles"]), ("build", 2))  # the next builder continues from the Handoff
        manifest = pack.load(self.root, "demo")
        pack.find_object(manifest, "object_a")["done"] = {"build": 2}
        pack.save(self.root, manifest)
        self.assertEqual(pack.status(self.root, "demo")[0]["next"], "review")  # a builder's done goes to the user
        pack.accept(self.root, "demo", "object_a")
        self.assertEqual(pack.status(self.root, "demo")[0]["next"], "godot")
        shot = pack.evidence_dir(self.root, "demo", "object_a") / "object_a_godot_1.png"
        shot.parent.mkdir(parents=True, exist_ok=True)
        shot.write_bytes(b"png")
        self.assertEqual(pack.status(self.root, "demo")[0]["next"], "ok")
        pack.reopen(self.root, "demo", "object_a")
        self.assertEqual(pack.status(self.root, "demo")[0]["next"], "build")
        self.assertEqual(set(pack.status(self.root, "demo")[0]), {"id", *pack.STATUS_COLUMNS})

    def test_old_pack_files_with_reviews_still_load_and_go_to_the_users_review(self) -> None:
        self._skip_pack()
        manifest = pack.load(self.root, "demo")
        entry = pack.find_object(manifest, "object_a")
        entry["done"] = {"build": 4}
        entry["reviews"] = [  # written by the review rounds this pipeline had before builders reviewed themselves
            {"round": 1, "build": 3, "route": "REFINE", "review": "object_a_review_1.md", "at": "2026-01-01T00:00:00+00:00"},
            {"round": 2, "build": 4, "route": "REQUEST-INPUT", "review": "object_a_review_2.md", "at": "2026-01-02T00:00:00+00:00"}]
        pack.save(self.root, manifest)
        row = pack.status(self.root, "demo")[0]
        self.assertEqual((row["next"], row["done"], row["cycles"]), ("review", True, "-"))
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(pack.main(["status", "demo"], root=self.root), 0)
        self.assertIn("review", output.getvalue().splitlines()[1])
        pack.accept(self.root, "demo", "object_a")
        self.assertEqual(pack.status(self.root, "demo")[0]["next"], "godot")
        pack.reopen(self.root, "demo", "object_a")
        self.assertEqual(pack.status(self.root, "demo")[0]["next"], "build")
        self.assertIn("reviews", pack.find_object(pack.load(self.root, "demo"), "object_a"))  # kept, ignored

    def test_the_old_review_commands_are_gone(self) -> None:
        # History: the separate critic agent and its commands were removed; builders review their own builds.
        for argv in (["critic-brief", "demo", "object_a"], ["reviewed", "demo", "object_a", "ACCEPT"]):
            with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()):
                pack._parser().parse_args(argv)
        self.assertFalse((pack.TEMPLATES / "critic_brief.md").exists())
        self.assertFalse((REPO / ".claude" / "agents" / "asset-critic.md").exists())

    def test_the_guides_agents_and_hooks_the_pipeline_names_exist(self) -> None:
        for name in ("builder_guide.md", "part_builder_guide.md", "blender_tools_guide.md"):
            self.assertTrue((REPO / pack.GUIDES_DIR / name).is_file(), name)
        part_builder = (REPO / ".claude" / "agents" / "asset-part-builder.md").read_text()
        self.assertIn("\nmodel: sonnet\n", part_builder)
        self.assertIn("name: asset-part-builder", part_builder)
        settings = json.loads((REPO / ".claude" / "settings.json").read_text())
        commands = [hook["command"] for groups in settings["hooks"].values() for group in groups for hook in group["hooks"]]
        for script in ("assetgen-guard.sh", "install-tools.sh", "builder-tools-context.sh", "builder-tools-hint.sh"):
            self.assertTrue(any(script in command for command in commands), script)
            self.assertTrue((REPO / ".claude" / "hooks" / script).is_file(), script)
        matchers = [group["matcher"] for group in settings["hooks"]["SubagentStart"]]
        self.assertIn("asset-builder|asset-part-builder", matchers)
        for template in ("builder_brief.md", "builder_followup.md", "builder_notes.md", "job_card.md"):
            self.assertTrue((pack.TEMPLATES / template).is_file(), template)

    def test_search_words_match_whole_words(self) -> None:
        self.assertEqual(pack._matched("furniture wood table", ["fur"]), 0)
        self.assertEqual(pack._matched("faux fur geometric", ["fur"]), 1)
        self.assertEqual(pack._matched("old wooden planks", ["plank", "wood"]), 1)
        rows = pack.rank_cgbookcase([{"title": "Brown Leather 01", "files": list(pack.CGBOOKCASE_FILES),
                                       "tags": ["leather"], "releasedate": "2024-01-02"},
                                      {"title": "Grass 02", "files": ["Base_Color"], "tags": ["leather"]}],
                                     ["leather"])
        self.assertEqual([row["ref"] for row in rows], ["cgbookcase:BrownLeather01"])

    # ----------------------------------------------------------------------- run, export, discard

    def test_run_start_snapshots_and_run_end_restores_and_quarantines(self) -> None:
        self._skip_pack()
        pipeline_file = self.root / "tools" / "assetgen" / "pack_copy.py"
        pipeline_file.parent.mkdir(parents=True)
        pipeline_file.write_text("original")
        state = pack.run_start(self.root, "demo")
        self.assertEqual(state["pack"], "demo")
        with self.assertRaises(pack.PackError):
            pack.run_start(self.root, "demo")
        with self.assertRaises(pack.PackError):
            pack.discard(self.root, "demo")
        pipeline_file.write_text("changed during the run")
        (self.root / "stray.txt").write_text("left behind")
        result = pack.run_end(self.root)
        self.assertEqual(pipeline_file.read_text(), "original")
        self.assertIn("tools/assetgen/pack_copy.py", result["check"]["restored"])
        self.assertEqual(result["check"]["quarantined"], ["stray.txt"])
        self.assertFalse((self.root / "stray.txt").exists())
        self.assertFalse((self.root / pack.RUN_LOCK).exists())
        with self.assertRaises(pack.PackError):
            pack.run_end(self.root)

    def _outputs_and_helpers(self) -> None:
        """object_a finished: renders, helper images, notes, a review, a helper script and baked maps."""
        self._finished_build()
        evidence = pack.evidence_dir(self.root, "demo", "object_a")
        for name in ("object_a_view_1.png", "object_a_clay_1.png", "object_a_turn_1.png", "object_a_turnaround.png",
                     "object_a_godot_1.png", "object_a_compare.png", "object_a_cv_survey_1.png", "object_a_ref_view_1.png",
                     "object_a_review_1.md"):
            (evidence / name).write_bytes(b"png")
        pack.notes_path(self.root, "demo", "object_a").write_text("# notes")
        work = pack.work_dir(self.root, "demo", "object_a")
        work.mkdir(parents=True)
        (work / "helper.py").write_text("# helper")
        baked = self.root / pack.BAKE_DIR / "demo" / "object_a"
        baked.mkdir(parents=True)
        for name in ("object_a_basecolor.png", "object_a_orm.png", "object_a_normal.png"):
            (baked / name).write_bytes(b"png")
        (pack.pack_dir(self.root, "demo") / "scribble.md").write_text("# helper notes")

    def test_export_copies_the_outputs_outside_the_repo_and_discard_cleans_up(self) -> None:
        self._skip_pack()
        pack.add(self.root, "demo", "object_b", name="b", where="w", details="d", references=[self.image])
        self._outputs_and_helpers()
        with self.assertRaises(pack.PackError):
            pack.export(self.root, "demo", self.root / "inside")
        with tempfile.TemporaryDirectory() as outside:
            archive = pack.export(self.root, "demo", Path(outside))
            folder = Path(outside) / "demo" / "object_a"
            self.assertEqual(sorted(p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()),
                             ["object_a.glb", "renders/object_a_clay_1.png", "renders/object_a_godot_1.png",
                              "renders/object_a_turn_1.png", "renders/object_a_turnaround.png",
                              "renders/object_a_view_1.png", "textures/object_a_basecolor.png",
                              "textures/object_a_normal.png", "textures/object_a_orm.png"])
            self.assertFalse((Path(outside) / "demo" / "object_b").exists())
            self.assertTrue(archive.exists())
        removed = pack.discard(self.root, "demo")
        self.assertIn("design/asset-packs/demo", removed)
        self.assertFalse(pack.pack_dir(self.root, "demo").exists())

    def test_finish_keeps_models_textures_and_renders_and_deletes_the_helpers_and_notes(self) -> None:
        self._skip_pack()
        self._outputs_and_helpers()
        parts = pack.parts_dir(self.root, "demo", "object_a")  # a lead split the generator into part modules
        parts.mkdir(parents=True)
        for name in ("common.py", "rim.py"):
            (parts / name).write_text("# part module")
        card = pack.job_card(self.root, "demo", "object_a", "rim")
        (card.parent / "analysis.md").write_text("# the part builder's analysis")
        (pack.parts_work_dir(self.root, "demo", "object_a") / "harness.py").write_text("# the lead's harness")
        notes = pack.notes_path(self.root, "demo", "object_a")
        notes.write_text(FILLED_ANALYSIS + "\n## Report\nall checks pass\n")
        pack.done(self.root, "demo", "object_a")
        pack.run_start(self.root, "demo")
        with self.assertRaises(pack.PackError):
            pack.finish(self.root, "demo")
        pack.run_end(self.root)
        result = pack.finish(self.root, "demo")
        models = "assets/models/demo"
        evidence = "production/qa/evidence/demo/object_a"
        self.assertEqual(result["kept"], sorted([
            f"{models}/object_a.glb", f"{models}/object_a_textures/object_a_basecolor.png",
            f"{models}/object_a_textures/object_a_normal.png", f"{models}/object_a_textures/object_a_orm.png",
            f"{evidence}/object_a_clay_1.png", f"{evidence}/object_a_godot_1.png", f"{evidence}/object_a_turn_1.png",
            f"{evidence}/object_a_turnaround.png", f"{evidence}/object_a_view_1.png"]))
        for path in result["kept"]:
            self.assertTrue((self.root / path).is_file(), path)
        for gone in (notes, pack.generator_path(self.root, "demo", "object_a"),
                     pack.build_report_path(self.root, "demo", "object_a"),
                     pack.evidence_dir(self.root, "demo", "object_a") / "object_a_review_1.md",
                     pack.evidence_dir(self.root, "demo", "object_a") / "object_a_compare.png",
                     pack.evidence_dir(self.root, "demo", "object_a") / "object_a_ref_view_1.png",
                     pack.pack_dir(self.root, "demo") / "scribble.md",
                     pack.work_dir(self.root, "demo", "object_a"), self.root / pack.BAKE_DIR / "demo",
                     parts, card, pack.parts_work_dir(self.root, "demo", "object_a")):
            self.assertFalse(gone.exists(), gone)
        self.assertIn("tools/blender/assetgen/packs/demo/object_a_parts/", result["removed"])
        self.assertIn(".scratch/assetgen/work/demo/object_a/parts/", result["removed"])
        self.assertFalse((self.root / pack.GENERATORS_DIR / "demo").exists())
        self.assertTrue((pack.pack_dir(self.root, "demo") / "pack.json").exists())
        row = pack.status(self.root, "demo")[0]
        self.assertEqual((row["next"], row["triangles"], row["builds"]), ("finished", 800, 3))
        with self.assertRaises(pack.PackError):
            pack.reopen(self.root, "demo", "object_a")

    # ----------------------------------------------------------------------- texture search

    def test_polyhaven_ranking_puts_most_matched_words_first(self) -> None:
        assets = {
            "tex_one": {"name": "Tex One", "tags": ["alpha"], "categories": [], "download_count": 5,
                        "dimensions": [2000, 1000], "thumbnail_url": "u1"},
            "tex_two": {"name": "Tex Two", "tags": ["alpha", "beta"], "categories": [], "download_count": 1},
            "tex_three": {"name": "Tex Three", "tags": ["gamma"], "categories": [], "download_count": 9},
        }
        rows = pack.rank_polyhaven(assets, ["alpha", "beta"])
        self.assertEqual([row["ref"] for row in rows], ["polyhaven:tex_two", "polyhaven:tex_one"])
        self.assertEqual(rows[1]["size_m"], [2.0, 1.0])

    def test_ambientcg_rows_keep_order_and_preview(self) -> None:
        found = {"foundAssets": [
            {"assetId": "IdB", "displayName": "B", "previewImage": {pack.AMBIENTCG_PREVIEW: "ub"}},
            {"assetId": "IdA", "displayName": "A"},
        ]}
        rows = pack.ambientcg_rows(found)
        self.assertEqual([row["ref"] for row in rows], ["ambientcg:IdB", "ambientcg:IdA"])
        self.assertEqual((rows[0]["thumbnail"], rows[1]["thumbnail"]), ("ub", None))


if __name__ == "__main__":
    unittest.main()
