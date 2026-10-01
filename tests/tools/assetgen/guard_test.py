"""Tests for tools/assetgen/guard.py, the logic behind the pipeline's hooks (offline).

Run: python3 -m unittest discover -s tests/tools/assetgen -p "*_test.py"
"""
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools" / "assetgen"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402
import pack  # noqa: E402
from pack_test import FILLED_ANALYSIS, png_bytes  # noqa: E402

GENERATOR = "tools/blender/assetgen/packs/demo/thing.py"
BUILD = f"cd {{root}} && blender -b --factory-startup --python {GENERATOR} -- 2>&1 | grep -E 'BUILT|CV '"
FINAL = f"cd {{root}} && blender -b --factory-startup --python {GENERATOR} -- --final 2>&1 | tail -5"


class GuardTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        (self.root / "tools" / "assetgen").mkdir(parents=True)
        (self.root / "tools" / "assetgen" / "pack.py").write_text("# pipeline file\n")
        (self.root / ".claude").mkdir()
        (self.root / ".claude" / "settings.json").write_text("{}\n")
        image = self.root / "upload.png"
        image.write_bytes(png_bytes(60, 40))
        pack.init(self.root, "demo", image, skip_canva=True)
        pack.set_style(self.root, "demo", "the style of the reference image")
        pack.add(self.root, "demo", "thing", name="thing", where="middle", details="a body", references=[image])
        pack.init(self.root, "other", image, skip_canva=True)
        pack.run_start(self.root, "demo")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def pre(self, tool: str, **tool_input) -> str | None:
        data = {"tool_name": tool, "tool_input": tool_input, "cwd": str(self.root)}
        data.update(tool_input.pop("_extra", {}))
        data["tool_input"] = tool_input
        return guard.pre(self.root, data)

    def bash(self, command: str, **extra) -> str | None:
        return self.pre("Bash", command=command.format(root=self.root), _extra=extra)

    # ----------------------------------------------------------------------- writes

    def test_nothing_is_checked_outside_a_run(self) -> None:
        pack.run_end(self.root)
        self.assertIsNone(self.pre("Write", file_path=str(self.root / "tools/assetgen/pack.py")))
        self.assertIsNone(self.bash("git commit -m x"))

    def test_writes_are_limited_to_the_run_packs_folders(self) -> None:
        allowed = [GENERATOR, "production/qa/evidence/demo/thing/thing_notes.md", "assets/models/demo/thing.glb",
                   "design/asset-packs/demo/references/x.png", ".scratch/assetgen/previews/demo/a.png", "/tmp/elsewhere.txt"]
        for path in allowed:
            self.assertIsNone(self.pre("Write", file_path=path if path.startswith("/") else str(self.root / path)), path)
        refused = ["tools/assetgen/pack.py", ".claude/settings.json", "design/asset-packs/demo/pack.json",
                   "production/qa/evidence/other/x.md", "README.md", ".scratch/assetgen/snapshot/manifest.json",
                   ".scratch/assetgen/run.json", ".scratch/assetgen/agents/a.json"]
        for path in refused:
            self.assertIsNotNone(self.pre("Edit", file_path=str(self.root / path)), path)

    def test_shell_commands_that_would_change_the_pipeline_are_refused(self) -> None:
        refused = ["git commit -am x", "git -C {root} checkout -- tools", "echo x > tools/assetgen/pack.py",
                   "sed -i 's/a/b/' tools/assetgen/pack.py", "mv tools/assetgen/pack.py /tmp/", "rm -rf .claude",
                   "cd tools/assetgen && echo hi > note.txt", "cp /tmp/x.py tools/assetgen/x.py",
                   "rm -f production/qa/evidence/other/x.png 2>/dev/null", "tee -a README.md < /dev/null",
                   "touch design/asset-packs/demo/pack.json", "dd if=/dev/zero of=tools/assetgen/pack.py count=1"]
        for command in refused:
            self.assertIsNotNone(self.bash(command), command)
        allowed = ["python3 tools/assetgen/cv.py compare demo thing 2>&1 | tail -5",
                   "python3 tools/assetgen/pack.py status demo > /tmp/status.txt",
                   "rm -f production/qa/evidence/demo/thing/old.png 2>/dev/null",
                   f"cat > {GENERATOR} <<'EOF'\nimport os\nos.remove('tools/assetgen/pack.py'); rm tools/assetgen/pack.py\nEOF",
                   "cp /tmp/draft.py " + GENERATOR, "ls -la tools > /dev/null", "git status && git diff --stat",
                   "sed 's/a/b/' tools/assetgen/pack.py | head"]
        for command in allowed:
            self.assertIsNone(self.bash(command), command)

    # ----------------------------------------------------------------------- build gate

    def _set_up_object(self) -> Path:
        pack.set_views(self.root, "demo", "thing", [[1, 0, 5, 0, 0, 60, 40]])
        entry = pack.find_object(pack.load(self.root, "demo"), "thing")
        evidence = pack.evidence_dir(self.root, "demo", "thing")
        evidence.mkdir(parents=True, exist_ok=True)
        pack.cv_reference_path(self.root, "demo", "thing").write_text(
            json.dumps({"views_signature": pack.views_signature(entry)}))
        pack.set_skills(self.root, "demo", "thing", [])
        pack.set_budget(self.root, "demo", "thing", 4000, "a body")
        notes = pack.notes_path(self.root, "demo", "thing")
        notes.write_text(FILLED_ANALYSIS + "\n## Cycles\n")
        return notes

    def _record_build(self, number: int, compared: bool = True) -> None:
        pack.build_report_path(self.root, "demo", "thing").write_text(json.dumps({"build": number, "views": []}))
        if compared:
            pack.cv_report_path(self.root, "demo", "thing").write_text(json.dumps({"build": number}))

    def test_a_build_waits_for_the_whole_set_up(self) -> None:
        reason = self.bash(BUILD)
        for missing in ("record the views", "set up the skills", "triangle budget", "notes"):
            self.assertIn(missing, reason)
        notes = self._set_up_object()
        self.assertIsNone(self.bash(BUILD))
        pack.set_views(self.root, "demo", "thing", [[1, 90, 5, 0, 0, 60, 40]])
        self.assertIn("cv.py measure", self.bash(BUILD))  # new views must be measured again
        self._set_up_object()
        notes.write_text(FILLED_ANALYSIS.replace("a thing", "<!-- -->"))
        self.assertIn("What it is", self.bash(BUILD))

    def test_each_build_waits_for_the_last_builds_cv_compare_and_its_cycle_notes(self) -> None:
        notes = self._set_up_object()
        self._record_build(1, compared=False)
        self.assertIn("no CV compare", self.bash(BUILD))
        self._record_build(1)
        self.assertIn("## Cycle 1", self.bash(BUILD))
        notes.write_text(notes.read_text() + "\n## Cycle 1\nthe body is too wide; narrow it\n")
        self.assertIsNone(self.bash(BUILD))

    def test_a_builder_hands_off_after_its_build_budget_with_one_final_build_allowed(self) -> None:
        notes = self._set_up_object()
        agent = {"agent_id": "agent-1", "agent_type": "asset-builder"}
        for number in range(1, pack.BUILDS_PER_BUILDER + 1):
            self.assertIsNone(self.bash(BUILD, **agent), number)
            self._record_build(number)
            notes.write_text(notes.read_text() + f"\n## Cycle {number}\nnotes\n")
        self.assertIn("HANDOFF demo thing", self.bash(BUILD, **agent))
        self.assertIsNone(self.bash(FINAL, **agent))
        self._record_build(pack.BUILDS_PER_BUILDER + 1)
        notes.write_text(notes.read_text() + f"\n## Cycle {pack.BUILDS_PER_BUILDER + 1}\nfinal\n")
        self.assertIn("context budget", self.bash(FINAL, **agent))
        self.assertIsNone(self.bash(BUILD, agent_id="agent-2", agent_type="asset-builder"))  # a fresh builder
        self.assertEqual(pack.status(self.root, "demo")[0]["active"], "0m")

    def test_builds_are_recognised_however_they_are_written(self) -> None:
        variants = [f"f={GENERATOR} && blender -b --factory-startup --python $f -- 2>&1 | tail",
                    "cd tools/blender/assetgen/packs/demo && blender -b --python thing.py --",
                    f"timeout 600 blender -b --python {{root}}/{GENERATOR} -- --views 1",
                    f"xvfb-run -a -s '-screen 0 640x480x24' blender -b --python={GENERATOR}"]
        for command in variants:
            self.assertIn("set-up is not finished", self.bash(command) or "", command)
        self.assertEqual(guard.builds(self.root, "blender -b --python tools/other.py", self.root), [])
        self.assertIsNone(self.bash(f"f={GENERATOR} && sed -i 's/0.1/0.2/' $f"))

    def test_a_cycle_written_by_the_same_command_counts(self) -> None:
        notes = self._set_up_object()
        self._record_build(1)
        command = (f"cat >> {notes.relative_to(self.root)} <<'E'\n## Cycle 1\nlegs too short; lengthen them\nE\n"
                   + BUILD)
        self.assertIsNone(self.bash(command))
        self.assertIn("## Cycle 1", self.bash(BUILD))

    def test_builds_of_another_pack_are_refused(self) -> None:
        self.assertIn("pack demo", self.bash(BUILD.replace("/demo/", "/other/")))

    # ----------------------------------------------------------------------- Canva

    def _canva_run(self) -> str:
        pack.run_end(self.root)
        image = self.root / "upload.png"
        pack.init(self.root, "drawn", image)
        pack.set_style(self.root, "drawn", "ink lines")
        pack.add(self.root, "drawn", "thing", name="thing", where="middle", details="a body")
        pack.set_canva(self.root, "drawn", "MSOURCE", None)
        pack.run_start(self.root, "drawn")
        return pack.prompt(self.root, "drawn", "thing")

    def test_canva_gets_only_the_exact_prompt_with_the_source_image(self) -> None:
        text = self._canva_run()
        good = {"prompt": text, "imageReferences": [{"type": "MEDIA", "id": "MSOURCE"}],
                "aspectRatio": pack.CANVA_ASPECT_RATIO}
        self.assertIsNone(self.pre(guard.CANVA_GENERATE, **good))
        self.assertIn("exactly", self.pre(guard.CANVA_GENERATE, **{**good, "prompt": text + " Cute, 3D render."}))
        self.assertIn("imageReferences", self.pre(guard.CANVA_GENERATE, **{**good, "imageReferences": []}))
        self.assertIn("aspectRatio", self.pre(guard.CANVA_GENERATE, **{**good, "aspectRatio": "SQUARE_1_1"}))

    def test_a_run_that_skips_canva_generates_nothing(self) -> None:
        self.assertIn("skips Canva", self.pre(guard.CANVA_GENERATE, prompt="x"))

    # ----------------------------------------------------------------------- after a tool call

    def test_post_restores_the_pipeline_and_quarantines_strays(self) -> None:
        pipeline = self.root / "tools" / "assetgen" / "pack.py"
        pipeline.write_text("broken\n")
        (self.root / "notes.tmp").write_text("x")
        (self.root / "production" / "qa" / "evidence" / "demo").mkdir(parents=True, exist_ok=True)
        (self.root / "production" / "qa" / "evidence" / "demo" / "keep.txt").write_text("own file")
        message = guard.post(self.root, {"tool_name": "Bash", "tool_input": {"command": "python3 x.py"}})
        self.assertEqual(pipeline.read_text(), "# pipeline file\n")
        self.assertIn("restored: tools/assetgen/pack.py", message)
        self.assertIn("notes.tmp", message)
        self.assertFalse((self.root / "notes.tmp").exists())
        self.assertTrue((self.root / "production/qa/evidence/demo/keep.txt").exists())
        self.assertIsNone(guard.post(self.root, {"tool_name": "Read", "tool_input": {}}))

    def test_post_points_a_builder_at_its_cv_compare_after_a_build(self) -> None:
        self._set_up_object()
        self._record_build(4)
        message = guard.post(self.root, {"tool_name": "Bash", "tool_input": {"command": BUILD.format(root=self.root)}})
        self.assertIn("Build 4 finished", message)
        self.assertIn("## Cycle 4", message)

    def test_the_hook_entry_point_exits_2_with_the_reason(self) -> None:
        data = json.dumps({"tool_name": "Bash", "tool_input": {"command": "git push"}, "cwd": str(self.root)})
        errors = io.StringIO()
        with mock.patch("sys.stdin", io.StringIO(data)), redirect_stderr(errors):
            self.assertEqual(guard.main(["pre", "--root", str(self.root)]), 2)
        self.assertIn("Git commands", errors.getvalue())
        output = io.StringIO()
        (self.root / "tools" / "assetgen" / "pack.py").write_text("changed")
        with mock.patch("sys.stdin", io.StringIO(data)), redirect_stdout(output):
            self.assertEqual(guard.main(["post", "--root", str(self.root)]), 0)
        self.assertEqual(json.loads(output.getvalue())["hookSpecificOutput"]["hookEventName"], "PostToolUse")


if __name__ == "__main__":
    unittest.main()
