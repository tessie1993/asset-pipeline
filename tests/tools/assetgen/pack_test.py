"""Tests for tools/assetgen/pack.py (offline: no command here touches the network).

Run: python3 -m unittest discover -s tests/tools/assetgen -p "*_test.py"
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools" / "assetgen"))
import pack  # noqa: E402

# A 1x1 PNG, enough to stand in for a source image.
PIXEL_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6360000002000100ffff03000006000557bfabd40000000049454e44ae426082"
)


class PackTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.image = self.root / "upload.PNG"
        self.image.write_bytes(PIXEL_PNG)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _pack_with_object(self, **extra) -> None:
        pack.init(self.root, "demo", self.image)
        pack.set_style(self.root, "demo", "style words")
        pack.add(self.root, "demo", "object_a", name="object a", where="left side",
                 details="part one, part two", **extra)

    def test_init_creates_layout_and_copies_the_source(self) -> None:
        manifest = pack.init(self.root, "demo", self.image)
        folder = self.root / "design" / "asset-packs" / "demo"
        self.assertEqual(manifest["source"], "source.png")
        self.assertEqual((folder / "source.png").read_bytes(), PIXEL_PNG)
        self.assertTrue((folder / "canva").is_dir())
        self.assertTrue((folder / "objects").is_dir())
        saved = json.loads((folder / "pack.json").read_text())
        self.assertEqual(saved["objects"], [])
        self.assertNotIn("materials", saved)

    def test_init_twice_is_refused(self) -> None:
        pack.init(self.root, "demo", self.image)
        with self.assertRaises(pack.PackError):
            pack.init(self.root, "demo", self.image)

    def test_add_numbers_objects_in_order(self) -> None:
        pack.init(self.root, "demo", self.image)
        first = pack.add(self.root, "demo", "object_a", name="a", where="left", details="d")
        second = pack.add(self.root, "demo", "object_b", name="b", where="right", details="d")
        self.assertEqual((first["number"], second["number"]), (1, 2))
        self.assertEqual(pack.sheet_name(second), "02_object_b_360.png")

    def test_add_sets_the_layout_view_angle_and_all_views(self) -> None:
        pack.init(self.root, "demo", self.image)
        flat = pack.add(self.root, "demo", "object_a", name="a", where="w", details="d", layout="block")
        self.assertEqual(flat["view_elevation_deg"], pack.VIEW_ELEVATIONS["block"])
        self.assertEqual(flat["judge_views"], list(pack.VIEW_AZIMUTHS))

    def test_add_rejects_bad_ids_and_duplicates(self) -> None:
        self._pack_with_object()
        with self.assertRaises(pack.PackError):
            pack.add(self.root, "demo", "Object A", name="x", where="x", details="x")
        with self.assertRaises(pack.PackError):
            pack.add(self.root, "demo", "object_a", name="x", where="x", details="x")
        with self.assertRaises(pack.PackError):
            pack.add(self.root, "demo", "object_b", name="x", where="x", details="x", layout="spiral")

    def test_prompt_fills_every_placeholder(self) -> None:
        self._pack_with_object()
        text = pack.prompt(self.root, "demo", "object_a")
        self.assertIn("the object a (part one, part two; left side in the reference)", text)
        self.assertIn("in this art style: style words.", text)
        self.assertIn(pack.LAYOUTS["object"], text)
        self.assertNotIn("$", text)

    def test_prompt_needs_an_art_style(self) -> None:
        pack.init(self.root, "demo", self.image)
        pack.add(self.root, "demo", "object_a", name="a", where="w", details="d")
        with self.assertRaises(pack.PackError):
            pack.prompt(self.root, "demo", "object_a")
        with self.assertRaises(pack.PackError):
            pack.set_style(self.root, "demo", "   ")

    def test_export_copies_deliverables_outside_the_repo_and_zips(self) -> None:
        self._pack_with_object()
        pack.add(self.root, "demo", "object_b", name="b", where="w", details="d")
        glb = self.root / "assets" / "models" / "demo" / "object_a.glb"
        glb.parent.mkdir(parents=True)
        glb.write_bytes(b"glb")
        compare = self.root / "production" / "qa" / "evidence" / "demo" / "object_a" / "object_a_compare.png"
        compare.parent.mkdir(parents=True)
        compare.write_bytes(PIXEL_PNG)
        with self.assertRaises(pack.PackError):
            pack.export(self.root, "demo", self.root / "inside")
        with tempfile.TemporaryDirectory() as outside:
            archive = pack.export(self.root, "demo", Path(outside))
            folder = Path(outside) / "demo"
            self.assertEqual(sorted(p.name for p in (folder / "object_a").iterdir()),
                             ["object_a.glb", "object_a_compare.png"])
            self.assertFalse((folder / "object_b").exists())
            self.assertTrue((folder / "source.png").exists())
            self.assertEqual(archive, Path(outside) / "demo.zip")
            self.assertTrue(archive.exists())

    def _pack_with_two_sheets(self) -> None:
        self._pack_with_object()
        pack.add(self.root, "demo", "object_b", name="b", where="w", details="d")
        pack.record(self.root, "demo", "object_a", media="M1", job=None, refused=None)
        pack.record(self.root, "demo", "object_b", media="M2", job=None, refused=None)
        pack.cutout(self.root, "demo", "object_a", media="C1", failed=None)
        pack.cutout(self.root, "demo", "object_b", media="C2", failed=None)

    def test_sheets_need_every_background_removed_or_its_failure_recorded(self) -> None:
        self._pack_with_object()
        pack.record(self.root, "demo", "object_a", media="M1", job=None, refused=None)
        with self.assertRaises(pack.PackError):
            pack.sheets(self.root, "demo")
        with self.assertRaises(pack.PackError):
            pack.cutout(self.root, "demo", "object_a", media=None, failed=None)
        pack.cutout(self.root, "demo", "object_a", media=None, failed="tool error")
        self.assertEqual(pack.sheets(self.root, "demo")[0]["media_id"], "M1")

    def test_canva_calls_need_the_recorded_ids(self) -> None:
        self._pack_with_two_sheets()
        self.assertEqual(pack.canva_calls(self.root, "demo", "create")[0]["tool"], "create-design")
        with self.assertRaises(pack.PackError):
            pack.canva_calls(self.root, "demo", "open")
        pack.set_canva(self.root, "demo", None, "D1", None)
        with self.assertRaises(pack.PackError):
            pack.canva_calls(self.root, "demo", "add-pages")

    def test_canva_calls_add_place_and_export_every_sheet_in_page_order(self) -> None:
        self._pack_with_two_sheets()
        pack.set_canva(self.root, "demo", None, "D1", "T1")
        add = pack.canva_calls(self.root, "demo", "add-pages")[0]["arguments"]
        self.assertEqual([op["title"] for op in add["operations"]], ["01_object_a_360", "02_object_b_360"])
        self.assertEqual({(op["width"], op["height"]) for op in add["operations"]}, {pack.SHEET_SIZE})
        with self.assertRaises(pack.PackError):
            pack.canva_calls(self.root, "demo", "place", ["P2"])
        place = pack.canva_calls(self.root, "demo", "place", ["P2", "P3"])
        self.assertEqual([(c["arguments"]["page_index"], c["arguments"]["operations"][0]["page_id"],
                           c["arguments"]["operations"][0]["asset_id"]) for c in place],
                         [(2, "P2", "C1"), (3, "P3", "C2")])
        export = pack.canva_calls(self.root, "demo", "export")
        self.assertEqual([call["tool"] for call in export], ["get-export-formats", "export-design"])
        self.assertEqual(export[1]["arguments"]["format"]["pages"], [2, 3])
        self.assertTrue(export[1]["arguments"]["format"]["transparent_background"])

    def test_png_size_reads_the_header(self) -> None:
        self.assertEqual(pack.png_size(PIXEL_PNG), (1, 1))
        self.assertIsNone(pack.png_size(b"not a png"))

    def test_canva_download_refuses_a_wrong_size_and_saves_nothing(self) -> None:
        self._pack_with_two_sheets()
        exported = self.root / "export.png"
        exported.write_bytes(PIXEL_PNG)
        url = exported.as_uri()
        with self.assertRaises(pack.PackError):
            pack.canva_download(self.root, "demo", [url])
        with self.assertRaises(pack.PackError):
            pack.canva_download(self.root, "demo", [url, url])
        self.assertFalse((self.root / "design" / "asset-packs" / "demo" / "canva" / "01_object_a_360.png").exists())

    def test_block_layout_uses_the_raised_camera(self) -> None:
        self._pack_with_object(layout="block")
        self.assertIn(pack.LAYOUTS["block"], pack.prompt(self.root, "demo", "object_a"))

    def test_record_needs_exactly_one_outcome(self) -> None:
        self._pack_with_object()
        with self.assertRaises(pack.PackError):
            pack.record(self.root, "demo", "object_a", media=None, job=None, refused=None)
        self.assertEqual(pack.record(self.root, "demo", "object_a", media="M1", job="J1", refused=None),
                         {"media_id": "M1", "job_id": "J1"})

    def test_sheets_skip_refusals_and_start_at_page_two(self) -> None:
        self._pack_with_object()
        pack.add(self.root, "demo", "object_b", name="b", where="w", details="d")
        pack.add(self.root, "demo", "object_c", name="c", where="w", details="d", layout="block")
        pack.record(self.root, "demo", "object_a", media="M1", job=None, refused=None)
        pack.record(self.root, "demo", "object_b", media=None, job=None, refused="unsafe input")
        pack.record(self.root, "demo", "object_c", media="M3", job=None, refused=None)
        pack.cutout(self.root, "demo", "object_a", media="C1", failed=None)
        pack.cutout(self.root, "demo", "object_c", media="C3", failed=None)
        rows = pack.sheets(self.root, "demo")
        self.assertEqual([(row["page"], row["id"], row["media_id"]) for row in rows],
                         [(2, "object_a", "C1"), (3, "object_c", "C3")])
        self.assertTrue(rows[1]["file"].endswith("canva/03_object_c_360.png"))

    def test_view_records_the_sheet_angle_and_consistent_views(self) -> None:
        self._pack_with_object()
        result = pack.set_view(self.root, "demo", "object_a", elevation=28.0, judge=[90, 0, 45])
        self.assertEqual(result, {"view_elevation_deg": 28.0, "judge_views": [0, 45, 90]})
        pack.set_skills(self.root, "demo", "object_a", [])
        self.assertIn("the views at 0°, 45°, 90°", pack.brief(self.root, "demo", "object_a"))

    def test_view_rejects_unknown_angles(self) -> None:
        self._pack_with_object()
        with self.assertRaises(pack.PackError):
            pack.set_view(self.root, "demo", "object_a", elevation=None, judge=[10])
        with self.assertRaises(pack.PackError):
            pack.set_view(self.root, "demo", "object_a", elevation=120.0, judge=None)

    def test_describe_embeds_both_reference_images_once(self) -> None:
        self._pack_with_object()
        path = pack.describe(self.root, "demo", "object_a")
        text = path.read_text()
        self.assertIn("](../canva/01_object_a_360.png)", text)
        self.assertIn("](../source.png)", text)
        self.assertNotIn("$", text)
        path.write_text("edited by hand")
        pack.describe(self.root, "demo", "object_a")
        self.assertEqual(path.read_text(), "edited by hand")

    def test_brief_names_the_generator_and_wall_origin(self) -> None:
        self._pack_with_object(mount="wall", size="small")
        pack.set_skills(self.root, "demo", "object_a", [])
        text = pack.brief(self.root, "demo", "object_a")
        self.assertIn("tools/blender/assetgen/packs/demo/object_a.py", text)
        self.assertIn('kit.run(build, origin="back")', text)
        self.assertIn("10,000 triangles", text)
        self.assertIn("all eight views", text)
        self.assertIn(f"{pack.BUILD_CYCLES} CYCLES", text)
        self.assertIn("found none relevant", text)
        self.assertIn('art style for this pack is: "style words"', text)
        self.assertIn("tools/blender/assetgen/zoom.py -- demo object_a", text)
        self.assertNotIn("$", text)

    def test_brief_needs_the_art_style(self) -> None:
        pack.init(self.root, "demo", self.image)
        pack.add(self.root, "demo", "object_a", name="a", where="w", details="d")
        pack.set_skills(self.root, "demo", "object_a", [])
        with self.assertRaises(pack.PackError):
            pack.brief(self.root, "demo", "object_a")

    def test_brief_needs_the_skills_check_and_lists_the_skills(self) -> None:
        self._pack_with_object()
        with self.assertRaises(pack.PackError):
            pack.brief(self.root, "demo", "object_a")
        skill = self.root / ".claude" / "skills" / "skill_x"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("---\nname: skill_x\n---\n")
        with self.assertRaises(pack.PackError):
            pack.set_skills(self.root, "demo", "object_a", ["not_installed"])
        pack.set_skills(self.root, "demo", "object_a", ["skill_x"])
        self.assertIn(str(skill / "SKILL.md"), pack.brief(self.root, "demo", "object_a"))

    def test_status_reports_outputs_as_they_appear(self) -> None:
        self._pack_with_object()
        self.assertFalse(pack.status(self.root, "demo")[0]["sheet"])
        sheet = self.root / "design" / "asset-packs" / "demo" / "canva" / "01_object_a_360.png"
        sheet.write_bytes(PIXEL_PNG)
        pack.record(self.root, "demo", "object_a", media=None, job=None, refused="unsafe input")
        row = pack.status(self.root, "demo")[0]
        self.assertTrue(row["sheet"])
        self.assertEqual(row["canva"], "refused")

    def test_run_lock_is_single_and_ends(self) -> None:
        self._pack_with_object()
        state = pack.run_start(self.root, "demo")
        self.assertEqual(state["pack"], "demo")
        self.assertTrue((self.root / pack.RUN_LOCK).exists())
        with self.assertRaises(pack.PackError):
            pack.run_start(self.root, "demo")
        self.assertEqual(pack.run_end(self.root)["pack"], "demo")
        self.assertFalse((self.root / pack.RUN_LOCK).exists())
        with self.assertRaises(pack.PackError):
            pack.run_end(self.root)

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
