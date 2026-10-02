"""Tests for tools/assetgen/guard.py, the logic behind the pipeline's hooks (offline).

Run: python3 -m unittest discover -s tests/tools/assetgen -p "*_test.py"
"""
import io
import json
import os
import shutil
import subprocess
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

REPO = Path(__file__).resolve().parents[3]

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
        pack.init(self.root, "demo", image, skip_flow=True)
        pack.set_style(self.root, "demo", "the style of the reference image")
        pack.add(self.root, "demo", "thing", name="thing", where="middle", details="a body", references=[image])
        pack.init(self.root, "other", image, skip_flow=True)
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

    def test_one_render_cycle_per_builder_with_the_final_build_allowed(self) -> None:
        self.assertEqual(pack.BUILDS_PER_BUILDER, 1)
        notes = self._set_up_object()
        agent = {"agent_id": "agent-1", "agent_type": "asset-builder"}
        for number in range(1, pack.BUILDS_PER_BUILDER + 1):
            self.assertIsNone(self.bash(BUILD, **agent), number)
            self._record_build(number)
            notes.write_text(notes.read_text() + f"\n## Cycle {number}\nthe rim 8 % too thin\n")
        reason = self.bash(BUILD, **agent)
        self.assertIn("one render cycle per builder", reason)
        self.assertIn("## Handoff", reason)
        self.assertIn("HANDOFF demo thing", reason)
        self.assertIsNone(self.bash(FINAL, **agent))  # nothing left worth improving: the final build
        self._record_build(pack.BUILDS_PER_BUILDER + 1)
        notes.write_text(notes.read_text() + f"\n## Cycle {pack.BUILDS_PER_BUILDER + 1}\nfinal\n")
        self.assertIn("one render cycle per builder", self.bash(FINAL, **agent))
        self.assertIsNone(self.bash(BUILD, agent_id="agent-2", agent_type="asset-builder"))  # a fresh builder
        self.assertEqual(pack.status(self.root, "demo")[0]["active"], "0m")

    def test_a_build_that_rendered_nothing_does_not_count(self) -> None:
        notes = self._set_up_object()
        agent = {"agent_id": "agent-1", "agent_type": "asset-builder"}
        self.assertIsNone(self.bash(BUILD, **agent))
        self.assertIsNone(self.bash(BUILD, **agent))  # the first one crashed before it rendered: try again
        self._record_build(1)
        notes.write_text(notes.read_text() + "\n## Cycle 1\nthe roof 0.04 lighter\n")
        self.assertIn("one render cycle per builder", self.bash(BUILD, **agent))
        self.assertIsNone(self.bash(FINAL, **agent))
        self.assertIsNone(self.bash(FINAL, **agent))  # the final build crashed too: again
        self._record_build(2)
        notes.write_text(notes.read_text() + "\n## Cycle 2\nfinal\n")
        self.assertIn("one render cycle per builder", self.bash(FINAL, **agent))

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

    # ----------------------------------------------------------------------- Google Flow

    def _flow_run(self) -> dict:
        pack.run_end(self.root)
        image = self.root / "upload.png"
        pack.init(self.root, "drawn", image)
        pack.set_style(self.root, "drawn", "ink lines")
        pack.add(self.root, "drawn", "thing", name="thing", where="middle", details="a body")
        pack.run_start(self.root, "drawn")
        return pack.flow_call(self.root, "drawn", "thing")["arguments"]

    def test_flow_gets_only_the_exact_grid_architect_set_up(self) -> None:
        good = self._flow_run()
        self.assertIsNone(self.pre(guard.FLOW_SETUP, **good))
        self.assertIn("exactly", self.pre(guard.FLOW_SETUP, **{**good, "theme_prompt": good["theme_prompt"] + " Cute, 3D render."}))
        self.assertIn("exactly", self.pre(guard.FLOW_SETUP, **{**good, "references": []}))
        self.assertIn("exactly", self.pre(guard.FLOW_SETUP, **{**good, "shot_prompts": good["shot_prompts"][:2]}))
        self.assertIn("exactly", self.pre(guard.FLOW_SETUP, **{**good, "engine": "Imagen 4"}))

    def test_flow_never_generates_on_its_own_during_a_run(self) -> None:
        self._flow_run()
        self.assertIn("never generates", self.pre(guard.FLOW_GENERATE, prompt="x", auto_confirm=True))

    def test_a_run_that_skips_flow_sets_nothing_up(self) -> None:
        self.assertIn("skips Google Flow", self.pre(guard.FLOW_SETUP, theme_prompt="x"))

    def test_imagesorcery_works_only_in_the_run_packs_evidence_and_scratch(self) -> None:
        view = self.root / "production/qa/evidence/demo/thing/thing_ref_view_1.png"
        self.assertIsNone(self.pre("mcp__imagesorcery__find", input_path=str(view), description="a part"))
        self.assertIsNone(self.pre("mcp__imagesorcery__crop", input_path=str(view), x1=0, y1=0, x2=9, y2=9,
                                   output_path=str(self.root / ".scratch/assetgen/work/demo/thing/crop.png")))
        self.assertIn("only on files", self.pre("mcp__imagesorcery__crop", input_path=str(view), x1=0, y1=0, x2=9, y2=9,
                                                output_path=str(self.root / "design/asset-packs/demo/crop.png")))
        self.assertIn("only on files", self.pre("mcp__imagesorcery__ocr",
                                                input_path=str(self.root / "production/qa/evidence/other/x.png")))
        self.assertIn("only on files", self.pre("mcp__imagesorcery__resize", input_path=str(view),
                                                output_path=str(self.root / ".scratch/assetgen/snapshot/x.png")))
        self.assertIn("only on files", self.pre("mcp__imagesorcery__overlay", base_image_path=str(view),
                                                overlay_image_path="/etc/x.png", output_path=str(view)))
        pack.run_end(self.root)
        self.assertIsNone(self.pre("mcp__imagesorcery__ocr", input_path="/anywhere/x.png"))

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

    def test_post_points_a_builder_at_its_cv_compare_and_review_after_a_build(self) -> None:
        self._set_up_object()
        self._record_build(4)
        message = guard.post(self.root, {"tool_name": "Bash", "tool_input": {"command": BUILD.format(root=self.root)}})
        self.assertIn("Build 4 finished", message)
        self.assertIn("review `## Cycle 4`", message)
        self.assertIn("Handoff", message)

    # ----------------------------------------------------------------------- part builders

    PART = {"agent_id": "part-1", "agent_type": "asset-part-builder"}
    LEAD = {"agent_id": "lead-1", "agent_type": "asset-builder"}

    def test_a_part_builder_writes_only_its_job_cards_files(self) -> None:
        card = pack.job_card(self.root, "demo", "thing", "handle")
        other_card = pack.job_card(self.root, "demo", "thing", "lid")
        folder = card.parent
        parts = self.root / "tools/blender/assetgen/packs/demo/thing_parts"
        reason = self.pre("Write", file_path=str(parts / "handle.py"), _extra=self.PART)
        self.assertIn("not in your work folder yet", reason)  # its first write goes to its own folder
        self.assertIsNone(self.pre("Write", file_path=str(folder / "analysis.md"), _extra=self.PART))
        self.assertIsNone(self.pre("Edit", file_path=str(parts / "handle.py"), _extra=self.PART))
        self.assertIsNone(self.bash(f"echo 'pass 2: rim thicker' >> {folder.relative_to(self.root)}/log.md", **self.PART))
        self.assertIsNone(self.pre("Write", file_path="/tmp/scratch.txt", _extra=self.PART))
        refused = [card, parts / "lid.py", parts / "common.py", self.root / GENERATOR, other_card.parent / "analysis.md",
                   folder.parent / "harness.py", pack.notes_path(self.root, "demo", "thing"),
                   self.root / "production/qa/evidence/demo/thing/thing_compare.png"]
        for path in refused:
            self.assertIn("job card", self.pre("Write", file_path=str(path), _extra=self.PART) or "", path)
        self.assertIn("job card", self.bash(f"cp /tmp/draft.py {GENERATOR}", **self.PART))
        card.write_text(card.read_text().replace("## You may write\n", "## You may write\n- `tools/blender/assetgen/packs/demo/thing_parts/lid.py`\n"))
        self.assertIsNone(self.pre("Write", file_path=str(parts / "lid.py"), _extra=self.PART))  # the lead added it
        second = {"agent_id": "part-2", "agent_type": "asset-part-builder"}
        self.assertIsNone(self.pre("Write", file_path=str(other_card.parent / "analysis.md"), _extra=second))
        self.assertIsNotNone(self.pre("Write", file_path=str(parts / "handle.py"), _extra=second))
        for path in (card, parts / "common.py", self.root / GENERATOR):  # the lead is held to no card
            self.assertIsNone(self.pre("Write", file_path=str(path), _extra=self.LEAD), path)
        state = json.loads((self.root / pack.AGENTS_DIR / "part-1.json").read_text())
        self.assertEqual((state["pack"], state["id"], state["part"]), ("demo", "thing", "handle"))

    def test_a_part_builder_runs_blender_only_on_the_harness(self) -> None:
        self._set_up_object()
        harness = ".scratch/assetgen/work/demo/thing/parts/harness.py"
        allowed = [f"timeout 900 blender -b --factory-startup --python {harness} -- --part handle 2>&1 | tail -20",
                   "cd .scratch/assetgen/work/demo/thing/parts && xvfb-run -a blender -b base.blend --python=harness.py",
                   "blender --version", "grep -n blender .scratch/assetgen/work/demo/thing/parts/handle/log.md",
                   "python3 tools/assetgen/pack.py kit-api | grep lathe", "python3 tools/assetgen/pack.py status demo",
                   "python3 tools/assetgen/cv.py sample demo thing --view 1 --box 0 0 1 1"]
        for command in allowed:
            self.assertIsNone(self.bash(command, **self.PART), command)
        refused = [BUILD, FINAL, f"f={GENERATOR} && timeout 900 blender -b --python $f --",
                   "blender -b --python tools/other.py", "blender -b base.blend --python-expr 'import bpy'",
                   "blender -b --python .scratch/assetgen/work/other/thing/parts/harness.py",
                   f"blender -b --python {harness} --python-expr 'import bpy'"]
        for command in refused:
            self.assertIn("test harness", self.bash(command, **self.PART) or "", command)
        for command in ("python3 tools/assetgen/pack.py done demo thing",
                        "cd tools/assetgen && python3 pack.py budget demo thing 900 --why more", "git commit -am x"):
            self.assertIsNotNone(self.bash(command, **self.PART), command)
        self.assertIsNone(self.bash(BUILD, **self.LEAD))  # the lead builds the whole
        pack.run_end(self.root)
        self.assertIsNone(self.bash(BUILD, **self.PART))  # nothing is checked outside a run

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

    def test_plugins_data_such_as_a_login_is_never_snapshotted(self):
        plugin = self.root / "plugins" / "blendkit"
        (plugin / ".data" / "config").mkdir(parents=True)
        (plugin / ".data" / "config" / "preferences.json").write_text('{"api_key": "secret"}')
        (plugin / "login.py").write_text("# plugin file\n")
        files = list(guard._walk(self.root, self.root))
        self.assertIn("plugins/blendkit/login.py", files)
        self.assertFalse(any("/.data/" in rel for rel in files))


@unittest.skipUnless(shutil.which("bash") and shutil.which("jq"), "the builder hooks need bash and jq")
class BuilderHookScriptsTestCase(unittest.TestCase):
    """.claude/hooks/builder-tools-context.sh (SubagentStart) and builder-tools-hint.sh (PostToolUse)."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        shutil.copytree(REPO / pack.GUIDES_DIR, self.root / pack.GUIDES_DIR)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def run_hook(self, name: str, data: dict) -> str:
        result = subprocess.run(["bash", str(REPO / ".claude" / "hooks" / name)], input=json.dumps(data),
                                capture_output=True, text=True, timeout=30, check=True,
                                env={**os.environ, "CLAUDE_PROJECT_DIR": str(self.root)})
        return result.stdout

    def test_every_builder_gets_the_guides_and_the_tools_table(self) -> None:
        guides = self.root / pack.GUIDES_DIR
        lead = json.loads(self.run_hook("builder-tools-context.sh", {"agent_type": "asset-builder"}))
        context = lead["hookSpecificOutput"]["additionalContext"]
        self.assertEqual(lead["hookSpecificOutput"]["hookEventName"], "SubagentStart")
        for text in (str(guides / "builder_guide.md"), str(guides / "blender_tools_guide.md"), "Handoff",
                     "asset-part-builder", "| Job | First choice | Also |"):
            self.assertIn(text, context)
        part = json.loads(self.run_hook("builder-tools-context.sh", {"agent_type": "asset-part-builder"}))
        context = part["hookSpecificOutput"]["additionalContext"]
        for text in (str(guides / "part_builder_guide.md"), "job card", "| Job | First choice | Also |"):
            self.assertIn(text, context)
        log = (self.root / ".scratch" / "assetgen" / "hooks.log").read_text()
        self.assertIn("SubagentStart agent=asset-builder", log)
        self.assertIn("SubagentStart agent=asset-part-builder", log)

    def test_a_failed_blender_run_gets_a_hint_and_anything_else_nothing(self) -> None:
        guide = self.root / pack.GUIDES_DIR / "blender_tools_guide.md"
        failed = {"tool_name": "Bash", "tool_response": {"stdout": "RuntimeError: Operator bpy.ops.mesh.set_edge_flow.poll() "
                                                                   "failed, context is incorrect", "stderr": ""}}
        hint = json.loads(self.run_hook("builder-tools-hint.sh", failed))["hookSpecificOutput"]
        self.assertEqual(hint["hookEventName"], "PostToolUse")
        self.assertIn(str(guide), hint["additionalContext"])
        missing = {"tool_name": "Bash", "tool_response": {"stdout": "", "stderr": "ModuleNotFoundError: No module named 'bl_ext"}}
        self.assertIn("kit.enable_addon", self.run_hook("builder-tools-hint.sh", missing))
        self.assertEqual(self.run_hook("builder-tools-hint.sh", {"tool_name": "Bash", "tool_response": {"stdout": "BUILT ok"}}), "")


if __name__ == "__main__":
    unittest.main()
