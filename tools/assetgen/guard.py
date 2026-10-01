#!/usr/bin/env python3
"""Hook logic of the image-to-assets pipeline. It acts only while a run is in progress
(``.scratch/assetgen/run.json``, written by ``pack.py run-start``) and keeps that run honest:

- **Locked and clean**: only the run's own pack folders change. Edits elsewhere are refused before
  they happen (Write/Edit, file-changing shell commands, git); after every tool call any pipeline
  file that changed anyway is restored from the snapshot ``run-start`` took, and any new file
  outside the pack's folders is moved to ``.scratch/assetgen/quarantine/``.
- **Builders set up, then measure every build**: a Blender build of a pack generator is refused
  until the object's views, CV measurements, skills, budget and notes analysis exist, and again
  until the CV compare of the previous build is written up in the notes.
- **Context budget**: a builder makes at most ``BUILDS_PER_BUILDER`` cycle builds (plus one final
  build); then it hands off through its notes and a fresh builder continues.
- **No bias added to Canva**: a Canva image is generated only from the exact text
  ``pack.py prompt`` prints, with the source image as the only reference.
- **The critic only looks**: an ``asset-critic`` agent never starts Blender and writes nothing but
  its review file (``production/qa/evidence/<pack>/<id>/<id>_review_<n>.md``).

The hook scripts in ``.claude/hooks/`` run it; during a run they run the copy in the snapshot, so
editing this file cannot switch the checks off::

    python3 tools/assetgen/guard.py pre  --root <repo> < hook input   # exit 2 + reason refuses the call
    python3 tools/assetgen/guard.py post --root <repo> < hook input   # restores; prints context for the model
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import shlex
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pack  # noqa: E402

SNAPSHOT_DIR = Path(".scratch/assetgen/snapshot")
QUARANTINE_DIR = Path(".scratch/assetgen/quarantine")
# Never part of the pipeline snapshot, never strays: version control, run scratch, Godot's cache.
EXCLUDED_DIRS = {".git", ".scratch", ".godot", "__pycache__"}
OUTPUT_ROOTS = (pack.PACKS_DIR, pack.GENERATORS_DIR, pack.MODELS_DIR, pack.EVIDENCE_DIR)
# Run state in .scratch that only pack.py and this module write.
LOCKED_SCRATCH = (SNAPSHOT_DIR, QUARANTINE_DIR, pack.AGENTS_DIR, pack.RUN_LOCK)
WRITE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")
CANVA_GENERATE = "mcp__Canva__generate-image"
CRITIC = "asset-critic"
REVIEW_FILE = re.compile(r"^production/qa/evidence/([a-z][a-z0-9_]*)/([a-z][a-z0-9_]*)/\2_review_[0-9]+\.md$")
RUNS_BLENDER = re.compile(r"(^|[\s;&|(/])blender(\s|$)")

GIT_CHANGE = re.compile(r"\bgit\b(\s+-C\s+\S+)?(\s+-c\s+\S+)*\s+(commit|push|add|rm|mv|merge|rebase|reset|checkout|"
                        r"switch|restore|stash|cherry-pick|revert|apply|am|tag|pull|clean|update-index|"
                        r"filter-branch|worktree)\b")
HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1[^\n]*\n.*?\n[ \t]*\2[ \t]*(?=\n|$)", re.DOTALL)
CONTROL = {";", "&&", "||", "|", "&", "|&", "(", ")", ";;", "{", "}"}
REDIRECT = {">", ">>", ">|", "&>", "&>>", ">&"}
PREFIXES = {"sudo", "env", "nohup", "command", "exec", "time", "builtin"}
CHANGES_ALL = {"rm", "rmdir", "unlink", "truncate", "touch", "tee", "shred"}
CHANGES_AFTER_FIRST = {"chmod", "chown", "chgrp"}
CHANGES_DESTINATION = {"cp", "install", "ln", "rsync"}


# --------------------------------------------------------------------------------- #
# Run state and paths
# --------------------------------------------------------------------------------- #

def run_state(root: Path) -> dict | None:
    """The run in progress, or None."""
    return pack.read_json(root / pack.RUN_LOCK)


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _rel(root: Path, path: str | Path, cwd: Path | None = None) -> str | None:
    """``path`` relative to the repository (posix), or None when it lies outside it."""
    path = Path(os.path.expanduser(str(path)))
    if not path.is_absolute():
        path = (cwd or root) / path
    try:
        return Path(os.path.normpath(path)).relative_to(Path(os.path.normpath(root))).as_posix()
    except ValueError:
        return None


def _inside(rel: str, area: Path | str) -> bool:
    area = Path(area).as_posix()
    return rel == area or rel.startswith(area + "/")


def pack_area_rels(pack_name: str) -> list[str]:
    """The run pack's own folders, relative to the repository."""
    return [(root_dir / pack_name).as_posix() for root_dir in OUTPUT_ROOTS]


def writable(rel: str, pack_name: str) -> bool:
    """Whether a run of ``pack_name`` may change the repository path ``rel``."""
    if _inside(rel, ".scratch"):
        return not any(_inside(rel, locked) for locked in LOCKED_SCRATCH)
    if _inside(rel, ".godot"):
        return True  # Godot's import cache
    if rel == (pack.PACKS_DIR / pack_name / "pack.json").as_posix():
        return False  # changed only through pack.py
    return any(_inside(rel, area) for area in pack_area_rels(pack_name))


# --------------------------------------------------------------------------------- #
# Snapshot, verify, restore, quarantine
# --------------------------------------------------------------------------------- #

def _walk(root: Path, base: Path):
    """Files under ``base`` (relative posix paths), skipping :data:`EXCLUDED_DIRS`."""
    if not base.exists():
        return
    for directory, dirs, files in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED_DIRS)
        for name in sorted(files):
            yield (Path(directory) / name).relative_to(root).as_posix()


def _is_output(rel: str) -> bool:
    return any(_inside(rel, output_root) for output_root in OUTPUT_ROOTS)


def pipeline_files(root: Path) -> list[str]:
    """Every file of the repository outside the pack folders (the pipeline itself)."""
    return [rel for rel in _walk(root, root) if not _is_output(rel)]


def other_pack_files(root: Path, pack_name: str) -> list[str]:
    """Files in the pack folders of every pack but ``pack_name``."""
    own = pack_area_rels(pack_name)
    return [rel for output_root in OUTPUT_ROOTS for rel in _walk(root, root / output_root)
            if not any(_inside(rel, area) for area in own)]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot(root: Path, pack_name: str) -> dict:
    """Copy and fingerprint the pipeline as it is now (and fingerprint the other packs), so any
    change during the run can be found and undone."""
    target = root / SNAPSHOT_DIR
    shutil.rmtree(target, ignore_errors=True)
    files = {}
    for rel in pipeline_files(root):
        source = root / rel
        copy = target / "files" / rel
        copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, copy)
        stat = source.stat()
        files[rel] = {"sha256": _sha256(source), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns}
    others = {}
    for rel in other_pack_files(root, pack_name):
        stat = (root / rel).stat()
        others[rel] = [stat.st_size, stat.st_mtime_ns]
    manifest = {"pack": pack_name, "taken": _now(), "files": files, "others": others}
    (target / "manifest.json").write_text(json.dumps(manifest) + "\n", encoding="utf-8")
    return {"files": len(files), "other_pack_files": len(others)}


def clear_snapshot(root: Path) -> None:
    shutil.rmtree(root / SNAPSHOT_DIR, ignore_errors=True)


def verify(root: Path, restore: bool = True) -> dict:
    """Compare the repository with the run's snapshot. With ``restore``, every changed or deleted
    pipeline file is copied back and every new file outside the run pack's folders is moved to the
    quarantine folder."""
    manifest = pack.read_json(root / SNAPSHOT_DIR / "manifest.json")
    result = {"restored": [], "quarantined": [], "other_packs_changed": []}
    if manifest is None:
        return result
    files = manifest["files"]
    for rel, info in files.items():
        path = root / rel
        if path.exists():
            stat = path.stat()
            if stat.st_size == info["size"] and stat.st_mtime_ns == info["mtime_ns"]:
                continue
            if stat.st_size == info["size"] and _sha256(path) == info["sha256"]:
                continue
        result["restored"].append(rel)
        if restore:
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.is_dir():
                shutil.rmtree(path)
            shutil.copy2(root / SNAPSHOT_DIR / "files" / rel, path)
    others = manifest["others"]
    current_others = set(other_pack_files(root, manifest["pack"]))
    for rel, (size, mtime_ns) in others.items():
        path = root / rel
        if not path.exists() or path.stat().st_size != size or path.stat().st_mtime_ns != mtime_ns:
            result["other_packs_changed"].append(rel)
    strays = sorted((set(pipeline_files(root)) - set(files)) | (current_others - set(others)))
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    for rel in strays:
        result["quarantined"].append(rel)
        if restore:
            target = root / QUARANTINE_DIR / stamp / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(root / rel), target)
    return result


# --------------------------------------------------------------------------------- #
# Shell commands: what they would change
# --------------------------------------------------------------------------------- #

def _tokens(command: str) -> list[str] | None:
    """Shell tokens of ``command`` with here-document bodies removed, or None when unparseable."""
    command = HEREDOC.sub("<<HEREDOC", command).replace("\n", " ; ")
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        return list(lexer)
    except ValueError:
        return None


def _segments(tokens: list[str]):
    segment = []
    for token in tokens:
        if token in CONTROL:
            if segment:
                yield segment
            segment = []
        else:
            segment.append(token)
    if segment:
        yield segment


ASSIGNMENT = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", re.DOTALL)
VARIABLE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)")
GENERATOR = re.compile(r"^tools/blender/assetgen/packs/([a-z][a-z0-9_]*)/([a-z][a-z0-9_]*)\.py$")


def _commands(command: str, cwd: Path):
    """``(args, redirect targets, cwd)`` per simple command of ``command``, with shell variables
    set earlier in the same command expanded and ``cd`` followed."""
    tokens = _tokens(command)
    if tokens is None:
        return
    variables: dict[str, str] = {}
    for segment in _segments(tokens):
        segment = [VARIABLE.sub(lambda m: variables.get(m.group(1) or m.group(2), m.group(0)), token)
                   for token in segment]
        args, targets, index = [], [], 0
        while index < len(segment):
            token = segment[index]
            following = segment[index + 1] if index + 1 < len(segment) else None
            if token.isdigit() and following in REDIRECT | {"<", "<<", "<<<"}:
                index += 1
                continue
            if token in REDIRECT:
                if following is not None and not following.startswith("&") and not (token == ">&" and following.isdigit()):
                    targets.append(following)
                index += 2
                continue
            if token in ("<", "<<", "<<<"):
                index += 2
                continue
            args.append(token)
            index += 1
        while args and ASSIGNMENT.match(args[0]):
            name, value = ASSIGNMENT.match(args[0]).groups()
            variables[name] = value
            args = args[1:]
        while args and args[0] in PREFIXES:
            args = args[1:]
        if args and args[0] == "timeout":
            args = args[2:]
        yield args, targets, cwd
        if args and os.path.basename(args[0]) == "cd" and len(args) > 1 and args[1] != "-":
            cwd = (cwd / os.path.expanduser(args[1])).resolve()


def changed_paths(command: str, cwd: Path) -> list[tuple[str, Path]]:
    """``(command name, path)`` for every path ``command`` would write, move or delete, as far as
    it can be told from the command line (redirections, file-changing commands, ``sed -i``,
    ``dd of=``); variables set in the command are expanded and ``cd`` is followed."""
    found = []
    for args, targets, here in _commands(command, cwd):
        found += [(">", here / os.path.expanduser(target)) for target in targets]
        name = os.path.basename(args[0]) if args else ""
        rest = args[1:]
        operands = [arg for arg in rest if not arg.startswith("-")]
        if name in CHANGES_ALL:
            found += [(name, here / arg) for arg in operands]
        elif name in CHANGES_AFTER_FIRST:
            found += [(name, here / arg) for arg in operands[1:]]
        elif name in CHANGES_DESTINATION or name == "mv":
            if "-t" in rest and rest.index("-t") + 1 < len(rest):
                found.append((name, here / rest[rest.index("-t") + 1]))
            elif name == "mv":
                found += [(name, here / arg) for arg in operands]
            elif operands:
                found.append((name, here / operands[-1]))
        elif name in ("sed", "perl") and any(arg.startswith("-i") or arg.startswith("--in-place") or
                                             (name == "sed" and re.fullmatch(r"-[a-zA-Z]*i[a-zA-Z]*", arg))
                                             for arg in rest):
            scripted = any(arg in ("-e", "-f", "--expression", "--file") for arg in rest)
            found += [(name, here / arg) for arg in (operands if scripted else operands[1:])]
        elif name == "dd":
            found += [(name, here / arg[3:]) for arg in rest if arg.startswith("of=")]
    return found


def builds(root: Path, command: str, cwd: Path) -> list[tuple[str, str, bool]]:
    """``(pack, object id, final)`` for every Blender build of a pack generator in ``command``,
    however it is written (relative or absolute path, a variable, after cd, under timeout or
    xvfb-run)."""
    found = []
    for args, _, here in _commands(command, cwd):
        start = next((i for i, arg in enumerate(args) if os.path.basename(arg) == "blender"), None)
        if start is None:
            continue
        rest = args[start + 1:]
        script = None
        for index, arg in enumerate(rest):
            if arg in ("--python", "-P") and index + 1 < len(rest):
                script = rest[index + 1]
            elif arg.startswith("--python="):
                script = arg.split("=", 1)[1]
        rel = _rel(root, script, here) if script else None
        match = GENERATOR.match(rel) if rel else None
        if match:
            found.append((match.group(1), match.group(2), "--final" in rest))
    return found


# --------------------------------------------------------------------------------- #
# PreToolUse checks
# --------------------------------------------------------------------------------- #

def _locked_message(state: dict, what: str) -> str:
    return (f"Refused: an image-to-assets run of pack {state.get('pack')} is in progress. {what} During a run "
            "only the pack's own folders change (design/asset-packs/<pack>/ through pack.py, "
            "tools/blender/assetgen/packs/<pack>/, assets/models/<pack>/, production/qa/evidence/<pack>/, .scratch/); "
            "the pipeline, other packs and git are locked. If the pipeline itself is wrong, stop and report the "
            "exact problem; the lock ends with `python3 tools/assetgen/pack.py run-end`.")


def check_write(root: Path, state: dict, path: str) -> str | None:
    rel = _rel(root, path)
    if rel is None or writable(rel, state["pack"]):
        return None
    return _locked_message(state, f"{rel} is outside the pack's folders.")


def check_bash(root: Path, state: dict, command: str, cwd: Path, data: dict) -> str | None:
    if GIT_CHANGE.search(command):
        return _locked_message(state, "Git commands that change the repository are not allowed.")
    for name, path in changed_paths(command, cwd):
        rel = _rel(root, path)
        if rel is not None and not writable(rel, state["pack"]):
            return _locked_message(state, f"`{name}` would change {rel}.")
    for pack_name, object_id, final in builds(root, command, cwd):
        reason = gate_build(root, state, pack_name, object_id, command, data, final)
        if reason:
            return reason
    return None


def _agent_state_path(root: Path, agent_id: str) -> Path:
    return root / pack.AGENTS_DIR / (re.sub(r"[^A-Za-z0-9_.-]", "_", agent_id) + ".json")


def gate_build(root: Path, state: dict, pack_name: str, object_id: str, command: str, data: dict,
               final: bool = False) -> str | None:
    """Refuse a Blender build until the builder's set-up is complete and the previous build's CV
    compare is written up; cap each builder's builds (context budget). None allows the build."""
    if pack_name != state["pack"]:
        return f"Refused: the run in progress is pack {state['pack']}; {pack_name} is not being built now."
    try:
        manifest = pack.load(root, pack_name)
        entry = pack.find_object(manifest, object_id)
    except pack.PackError as error:
        return f"Refused: {error}"
    notes = pack.notes_path(root, pack_name, object_id)
    text = notes.read_text(encoding="utf-8") if notes.exists() else ""
    cv_tool = f"python3 {pack.CV_TOOL}"
    problems = []
    if not entry.get("views"):
        problems.append(f"record the views your reference shows: `{cv_tool} views {pack_name} {object_id}`, "
                        f"then `python3 tools/assetgen/pack.py views {pack_name} {object_id} --view ...`")
    else:
        measured = pack.read_json(pack.cv_reference_path(root, pack_name, object_id))
        if not measured or measured.get("views_signature") != pack.views_signature(entry):
            problems.append(f"measure the recorded views: `{cv_tool} measure {pack_name} {object_id}`")
    if "skills" not in entry:
        problems.append(f"set up the skills: `python3 tools/assetgen/pack.py skills-list`, read the SKILL.md of each "
                        f"that fits, then `pack.py skills {pack_name} {object_id} <names>` (or `--none`)")
    if not entry.get("budget"):
        problems.append(f"decide the triangle budget: `pack.py budget {pack_name} {object_id} <triangles> --why \"...\"`")
    if not notes.exists():
        problems.append(f"your notes {notes} do not exist; run `pack.py brief {pack_name} {object_id}`")
    else:
        problems += [f"notes: {problem}" for problem in pack.analysis_problems(text)]
    if problems:
        return ("Refused: set-up is not finished. Before the first build:\n- " + "\n- ".join(problems) +
                f"\n(Notes: {notes})")
    build = pack.read_json(pack.build_report_path(root, pack_name, object_id))
    if build:
        number = build["build"]
        cv = pack.read_json(pack.cv_report_path(root, pack_name, object_id))
        if not cv or cv.get("build") != number:
            return (f"Refused: build {number} has no CV compare. Run `{cv_tool} compare {pack_name} {object_id}`; "
                    "if it fails, report the exact error.")
        written_now = f"## Cycle {number}" in command and notes.name in command  # this command writes it first
        if not pack.has_cycle(text, number) and not written_now:
            return (f"Refused: write `## Cycle {number}` in {notes} first: what the CV lines and the compare image "
                    f"of build {number} show — what matches and why, what differs and why (its cause in the model), "
                    "and the fix for each. Then build again.")
    agent_id = data.get("agent_id")
    if agent_id:
        path = _agent_state_path(root, agent_id)
        counts = pack.read_json(path) or {"pack": pack_name, "id": object_id, "builds": 0, "final_builds": 0}
        if counts["builds"] >= pack.BUILDS_PER_BUILDER and (not final or counts["final_builds"] >= 1):
            return (f"Refused: context budget reached ({counts['builds']} builds by this builder). Do not build again. "
                    f"Write `## Handoff` at the end of {notes}: what is right now (keep it), what is still wrong and "
                    "why, the next fixes in order, and what worked (skills, tools, settings). Then end with the first "
                    f"line `HANDOFF {pack_name} {object_id}`: a fresh builder continues from your notes.")
        counts["builds" if not final or counts["builds"] < pack.BUILDS_PER_BUILDER else "final_builds"] += 1
        counts.update(pack=pack_name, id=object_id, last_build_at=_now(), agent_type=data.get("agent_type"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(counts) + "\n", encoding="utf-8")
    return None


def check_canva(root: Path, state: dict, args: dict) -> str | None:
    """A Canva image is generated only from an object's exact prompt and the recorded source image."""
    manifest = pack.load(root, state["pack"])
    if manifest["skip_canva"]:
        return "Refused: this run skips Canva; no Canva image is generated for it."
    text = (args.get("prompt") or "").strip()
    prompts = set()
    for entry in manifest["objects"]:
        try:
            prompts.add(pack.prompt(root, state["pack"], entry["id"]))
        except pack.PackError as error:
            return f"Refused: {error}"
    if text not in prompts:
        return ("Refused: the Canva prompt must be exactly the text `python3 tools/assetgen/pack.py prompt <pack> <id>` "
                "prints, unchanged — no words added, removed or reworded (the look comes only from the user's art style).")
    source = manifest["canva"].get("source_media_id")
    if not source:
        return "Refused: upload the source image and record it first (`pack.py canva <pack> --source-media <id>`)."
    references = [(item.get("type"), item.get("id")) for item in args.get("imageReferences") or []]
    if references != [("MEDIA", source)]:
        return f'Refused: imageReferences must be exactly [{{"type": "MEDIA", "id": "{source}"}}], the recorded source image.'
    if args.get("aspectRatio") != pack.CANVA_ASPECT_RATIO:
        return f"Refused: aspectRatio must be {pack.CANVA_ASPECT_RATIO}."
    return None


def _review_file(rel: str | None, pack_name: str) -> bool:
    match = REVIEW_FILE.match(rel or "")
    return bool(match) and match.group(1) == pack_name


def check_critic(root: Path, state: dict, tool: str, args: dict, cwd: Path) -> str | None:
    """The critic only looks: no Blender, no file but its review."""
    only = (f"Refused: the critic only looks. It never starts Blender and writes nothing but its review file "
            f"(production/qa/evidence/{state['pack']}/<id>/<id>_review_<n>.md); the CV tools it runs write their own images.")
    if tool in WRITE_TOOLS:
        path = args.get("file_path") or args.get("notebook_path") or ""
        return None if _review_file(_rel(root, path), state["pack"]) else only
    if tool == "Bash":
        command = args.get("command", "")
        if RUNS_BLENDER.search(HEREDOC.sub("", command)):
            return only
        for _, path in changed_paths(command, cwd):
            rel = _rel(root, path)
            if rel is not None and not _review_file(rel, state["pack"]) and not _inside(rel, ".scratch"):
                return only
    return None


def pre(root: Path, data: dict) -> str | None:
    """The reason to refuse this tool call, or None to allow it."""
    state = run_state(root)
    if state is None:
        return None
    tool = data.get("tool_name", "")
    args = data.get("tool_input") or {}
    if data.get("agent_type") == CRITIC:
        reason = check_critic(root, state, tool, args, Path(data.get("cwd") or root))
        if reason:
            return reason
    if tool in WRITE_TOOLS:
        path = args.get("file_path") or args.get("notebook_path") or ""
        return check_write(root, state, path) if path else None
    if tool == "Bash":
        cwd = Path(data.get("cwd") or root)
        return check_bash(root, state, args.get("command", ""), cwd, data)
    if tool == CANVA_GENERATE:
        return check_canva(root, state, args)
    return None


# --------------------------------------------------------------------------------- #
# PostToolUse
# --------------------------------------------------------------------------------- #

def post(root: Path, data: dict) -> str | None:
    """Undo pipeline changes and quarantine stray files; after a build, point the builder at its
    CV compare. Returns context for the model, or None."""
    state = run_state(root)
    if state is None:
        return None
    messages = []
    result = verify(root, restore=True)
    if result["restored"]:
        messages.append("The pipeline is locked during a run; these files were changed and have been restored: "
                        + ", ".join(result["restored"]) + ". Change only the pack's own files.")
    if result["quarantined"]:
        messages.append("Files created outside the pack's folders were moved to .scratch/assetgen/quarantine/: "
                        + ", ".join(result["quarantined"]) + ". Keep your work in the pack's folders or .scratch/.")
    if result["other_packs_changed"]:
        messages.append("Other packs' files changed during this run (they are locked): "
                        + ", ".join(result["other_packs_changed"][:20]) + ".")
    if data.get("tool_name") == "Bash":
        command = (data.get("tool_input") or {}).get("command", "")
        for pack_name, object_id, _ in builds(root, command, Path(data.get("cwd") or root))[:1]:
            if pack_name != state["pack"]:
                continue
            report = pack.read_json(pack.build_report_path(root, pack_name, object_id)) or {}
            number = report.get("build", "?")
            evidence = pack.evidence_dir(root, pack_name, object_id)
            messages.append(f"Build {number} finished. Read its CV lines, open {evidence / (object_id + '_compare.png')} "
                            f"(renders, reference, outline overlay per view), and open a survey "
                            f"({object_id}_cv_survey_<view>.png) only for views whose CV lines list differences. Then write "
                            f"`## Cycle {number}` in your notes; the next build is refused until you do.")
    return "\n".join(messages) or None


# --------------------------------------------------------------------------------- #
# Hook entry point
# --------------------------------------------------------------------------------- #

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="image-to-assets hook checks")
    parser.add_argument("mode", choices=("pre", "post"))
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    root = args.root.resolve()
    if args.mode == "pre":
        reason = pre(root, data)
        if reason:
            print(reason, file=sys.stderr)
            return 2
        return 0
    context = post(root, data)
    if context:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": context}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
