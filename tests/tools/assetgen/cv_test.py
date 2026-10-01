"""Tests for tools/assetgen/cv.py on synthetic images (needs the CV libraries:
bash tools/assetgen/install_cv.sh).

Run: python3 -m unittest discover -s tests/tools/assetgen -p "*_test.py"
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools" / "assetgen"))
import cv  # noqa: E402
import pack  # noqa: E402

np = cv.np
cv2 = cv.cv2


def canvas(width: int, height: int, colour=(0, 0, 0, 0)) -> "np.ndarray":
    image = np.zeros((height, width, 4), np.uint8)
    image[:] = colour
    return image


@unittest.skipIf(cv2 is None, "CV libraries not installed (bash tools/assetgen/install_cv.sh)")
class CVTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_views_are_found_in_reading_order_on_transparent_and_plain_backgrounds(self) -> None:
        transparent = canvas(400, 300)
        cv2.rectangle(transparent, (220, 40), (300, 260), (50, 90, 160, 255), -1)
        cv2.rectangle(transparent, (30, 60), (150, 250), (50, 90, 160, 255), -1)
        cv2.rectangle(transparent, (35, 30), (60, 55), (50, 90, 160, 255), -1)  # touches the first: one drawing
        boxes, method = cv.find_views(transparent)
        self.assertEqual(method, "alpha")
        self.assertEqual(len(boxes), 2)
        self.assertLess(boxes[0][0], boxes[1][0])
        self.assertLessEqual(boxes[0][1], 30)
        plain = canvas(400, 300, (235, 238, 240, 255))
        cv2.circle(plain, (100, 150), 60, (40, 80, 140, 255), -1)
        cv2.circle(plain, (300, 150), 40, (40, 80, 140, 255), -1)
        boxes, method = cv.find_views(plain)
        self.assertEqual((len(boxes), method), (2, "plain background"))
        busy = np.random.default_rng(1).integers(0, 255, (300, 400, 4), dtype=np.uint8)
        busy[..., 3] = 255
        self.assertEqual(cv.find_views(busy)[0], [])

    def test_object_mask_uses_alpha_a_plain_background_or_grabcut(self) -> None:
        shape = canvas(200, 200)
        cv2.rectangle(shape, (50, 40), (150, 160), (60, 60, 200, 255), -1)
        mask, method = cv.object_mask(shape)
        self.assertEqual(method, "alpha")
        self.assertEqual(cv.bbox(mask), (50, 40, 151, 161))
        plain = shape.copy()
        plain[plain[..., 3] == 0] = (240, 240, 240, 255)
        mask, method = cv.object_mask(plain)
        self.assertEqual(method, "plain background")
        self.assertEqual(cv.bbox(mask), (50, 40, 151, 161))
        busy = np.random.default_rng(2).integers(80, 180, (200, 200, 4), dtype=np.uint8)
        busy[..., 3] = 255
        busy[40:161, 50:151] = (20, 20, 230, 255)
        mask, method = cv.object_mask(busy)
        self.assertTrue(method.startswith("grabcut"))
        x0, y0, x1, y1 = cv.bbox(mask)
        self.assertLess(abs(x0 - 50) + abs(y0 - 40) + abs(x1 - 151) + abs(y1 - 161), 30)

    def test_measure_view_reports_proportions_symmetry_and_colours(self) -> None:
        shape = canvas(300, 300)
        cv2.rectangle(shape, (100, 50), (200, 250), (40, 80, 140, 255), -1)
        cv2.rectangle(shape, (100, 50), (200, 100), (200, 200, 200, 255), -1)
        measured = cv.measure_view(shape)
        self.assertAlmostEqual(measured["aspect"], 101 / 201, places=2)
        self.assertGreater(measured["symmetry"], 0.95)
        self.assertGreater(measured["fill"], 0.95)
        self.assertEqual(len(measured["colours"]), 2)
        self.assertAlmostEqual(sum(colour["share"] for colour in measured["colours"]), 1.0, places=2)
        self.assertGreater(measured["directions"].get("vertical", 0) + measured["directions"].get("horizontal", 0), 0.9)

    def test_proportions_need_a_front_and_a_side_at_a_similar_elevation(self) -> None:
        views = [{"azimuth": 0, "elevation": 10}, {"azimuth": 270, "elevation": 12}]
        text = cv.proportions(views, [{"aspect": 1.5}, {"aspect": 0.5}])
        self.assertIn("1.50 : 1 : 0.50", text)
        self.assertIsNone(cv.proportions([views[0]], [{"aspect": 1.5}]))
        self.assertIsNone(cv.proportions([views[0], {"azimuth": 90, "elevation": 60}], [{"aspect": 1}, {"aspect": 1}]))

    def test_compare_ignores_scale_and_names_what_is_missing_or_extra(self) -> None:
        reference = canvas(300, 300, (240, 240, 240, 255))
        cv2.rectangle(reference, (100, 50), (200, 250), (40, 80, 140, 255), -1)
        same_shape = canvas(400, 400)
        cv2.rectangle(same_shape, (150, 100), (200, 200), (40, 80, 140, 255), -1)
        result = cv.compare_view(reference, same_shape)
        self.assertGreater(result["overlap"], 0.95)
        self.assertLess(abs(result["aspect_change"]), 0.05)
        self.assertEqual((result["missing"], result["extra"]), ([], []))
        right_half_missing = canvas(400, 400)
        cv2.rectangle(right_half_missing, (150, 100), (200, 200), (40, 80, 140, 255), -1)
        cv2.rectangle(right_half_missing, (176, 100), (200, 150), (0, 0, 0, 0), -1)
        result = cv.compare_view(reference, right_half_missing)
        self.assertLess(result["overlap"], 0.95)
        self.assertIn("top-right", [name for name, _ in result["missing"]])
        empty = canvas(100, 100)
        self.assertIn("error", cv.compare_view(reference, empty))

    def test_colour_zones_show_where_each_reference_colour_is_missing(self) -> None:
        reference = canvas(300, 300, (240, 240, 240, 255))
        cv2.rectangle(reference, (100, 50), (200, 250), (40, 80, 140, 255), -1)
        cv2.rectangle(reference, (100, 50), (200, 150), (230, 230, 120, 255), -1)  # top half light blue
        render = canvas(300, 300)
        cv2.rectangle(render, (100, 50), (200, 250), (40, 80, 140, 255), -1)
        cv2.rectangle(render, (100, 50), (200, 100), (230, 230, 120, 255), -1)  # only a quarter light blue
        zones = cv.compare_view(reference, render)["zones"]
        self.assertEqual(len(zones), 2)
        light = next(zone for zone in zones if zone["colour"] == "#78e6e6")
        self.assertAlmostEqual(light["area"], 0.5, delta=0.08)
        self.assertTrue(light["missing"])
        brown = next(zone for zone in zones if zone["colour"] != "#78e6e6")
        self.assertGreater(brown["area"], 1.4)
        self.assertTrue(brown["extra"])

    def test_compare_command_reports_one_line_per_view_and_writes_its_images(self) -> None:
        image = self.root / "upload.png"
        reference = np.full((200, 400, 3), 240, np.uint8)
        cv2.rectangle(reference, (40, 40), (140, 160), (40, 80, 140), -1)
        cv2.rectangle(reference, (240, 50), (300, 160), (40, 80, 140), -1)
        cv2.imwrite(str(image), reference)
        pack.init(self.root, "demo", image, skip_canva=True)
        pack.set_style(self.root, "demo", "the style of the reference image")
        pack.add(self.root, "demo", "thing", name="thing", where="middle", details="a block", references=[image])
        boxes, _ = cv.find_views(cv.read_image(image))
        pack.set_views(self.root, "demo", "thing", [[1, 0, 0, *boxes[0]], [1, 90, 0, *boxes[1]]])
        lines = cv.measure_command(self.root, "demo", "thing")
        self.assertTrue(any(line.startswith("REF proportions") for line in lines))
        evidence = pack.evidence_dir(self.root, "demo", "thing")
        files = []
        for number, (width, height) in enumerate(((100, 120), (60, 110)), start=1):
            render = canvas(256, 256)
            cv2.rectangle(render, (60, 60), (60 + width, 60 + height), (40, 80, 140, 255), -1)
            path = evidence / f"thing_view_{number}.png"
            cv2.imwrite(str(path), render)
            files.append({"view": number, "file": str(path.relative_to(self.root))})
        pack.build_report_path(self.root, "demo", "thing").write_text(json.dumps({"build": 2, "views": files}))
        lines = cv.compare_command(self.root, "demo", "thing")
        self.assertEqual(sum(line.startswith("CV build 2 view") for line in lines), 2)
        report = json.loads(pack.cv_report_path(self.root, "demo", "thing").read_text())
        self.assertEqual(report["build"], 2)
        self.assertGreater(report["mean_overlap"], 0.9)
        for name in ("thing_compare.png", "thing_cv_survey_1.png", "thing_cv_survey_2.png"):
            self.assertTrue((evidence / name).exists(), name)
        self.assertLessEqual(cv.read_image(evidence / "thing_compare.png").shape[1], cv.SHEET_MAX_WIDTH)
        closeup = cv.closeup_command(self.root, "demo", "thing", 1, [0.0, 0.0, 0.5, 0.5], 2)
        self.assertIn("reference left, render right", closeup[0])
        observed = cv.observe_command(self.root, "demo", "thing", 1, grid=2)
        self.assertTrue(observed[0].startswith("OBSERVE view 1"))
        self.assertTrue(any(line.startswith("OBSERVE 1 r1c1") for line in observed))
        self.assertTrue((evidence / "thing_cv_observe_1.png").exists())
        sampled = cv.sample_command(self.root, "demo", "thing", 1, [[0.1, 0.1, 0.9, 0.9]])
        self.assertEqual([line.split(":")[0].rsplit(" ", 1)[1] for line in sampled], ["reference", "render"])
        self.assertIn("lightness spread", sampled[0])

    def test_region_stats_see_variation_and_texture(self) -> None:
        flat = np.full((60, 60, 3), (40, 80, 140), np.uint8)
        mask = np.ones((60, 60), np.uint8)
        busy = np.random.default_rng(3).integers(0, 255, (60, 60, 3), dtype=np.uint8)
        flat_stats, busy_stats = cv.region_stats(flat, mask), cv.region_stats(busy, mask)
        self.assertLess(flat_stats["lightness_spread"], 0.01)
        self.assertGreater(busy_stats["lightness_spread"], 0.1)
        self.assertGreater(busy_stats["texture"], flat_stats["texture"])

    def test_contact_sheet_lays_out_labelled_thumbnails(self) -> None:
        paths = []
        for index in range(3):
            path = self.root / f"thumb_{index}.png"
            cv2.imwrite(str(path), np.full((40, 60, 3), 60 * index, np.uint8))
            paths.append(path)
        out = cv.contact_sheet(paths + [self.root / "missing.png"], ["a", "b", "c", "d"], self.root / "sheet.png", per_row=2)
        sheet = cv.read_image(out)
        self.assertEqual(sheet.shape[0], 2 * (cv.CONTACT_CELL + 22 + 4))


if __name__ == "__main__":
    unittest.main()
