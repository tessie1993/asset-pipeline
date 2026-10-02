#!/bin/bash
# SubagentStart hook (matcher asset-builder|asset-part-builder): hands every /image-to-assets builder
# the guides to the Blender tools and add-ons and the generic understand/observe/compare method, so
# it knows what it can grab before it builds anything. The lead builder gets the whole workflow (one
# render cycle, its own review, the Handoff, part builders); a part builder gets its one-job rules.
# Logs each start to .scratch/assetgen/hooks.log.

ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd)}"
GUIDES="$ROOT/.claude/skills/image-to-assets/references"
LOG="$ROOT/.scratch/assetgen/hooks.log"
command -v jq >/dev/null 2>&1 || exit 0

input="$(cat)"
agent="$(printf '%s' "$input" | jq -r '.agent_type // .subagent_type // empty' 2>/dev/null)"
mkdir -p "$(dirname "$LOG")" 2>/dev/null && echo "$(date -u +%FT%TZ) SubagentStart agent=${agent:-?}" >> "$LOG" 2>/dev/null
table="$(sed -n '/^## 1\. Which tool for which job/,/^## 2\./p' "$GUIDES/blender_tools_guide.md" 2>/dev/null | sed '$d')"

common="- Enable an add-on inside the Blender script: kit.enable_addon(\"bl_ext.blender_org.<id>\", with_preferences=True) (the pipeline's own extensions: bl_ext.user_default.<id>). Check each operator returns {'FINISHED'} and that the mesh changed as intended; UI-only operators have headless alternatives in blender_tools_guide.md section 3.
- BlendKit free models and materials (plugins/blendkit/headless.py) when it is logged in: search with is_free:true and check asset[\"license\"].
- Multitask (blender_tools_guide.md section 6): run Blender in the background (Bash run_in_background, with timeout) and keep working while it runs; send independent tool calls together; while the 1-minute load (/proc/loadavg) is below nproc another background job may start, but not far above nproc; never let two jobs write the same file."

if [ "$agent" = "asset-part-builder" ]; then
  context="TOOLS AND METHOD (given to every part builder by a hook):
- Read $GUIDES/part_builder_guide.md (one job: analyse and compare before you build, plan, build in large passes, check, report and stop), then your job card, and $GUIDES/blender_tools_guide.md for the tools (every installed Blender add-on, which run headless, command-line tools, skills).
- Think about what you see and understand the thing you are making, conceptually (what it is made of, how it is built, how it behaves, how this art style draws it); that chooses the approach. For every difference from the reference: why the reference looks like that and why the build differs; the fix follows from the cause.
- Write only your job card's files (You may write) and your work folder; run Blender only on the lead's test harness (the card's Test command), never the kit's full build.
$common

$table"
else
  context="TOOLS AND METHOD (given to every builder by a hook):
- Read $GUIDES/builder_guide.md (understand the object, part inventory, detail amount, materials incl. translucency and glow, wear, the comparison and your own review, the Handoff, lead and part builders) and $GUIDES/blender_tools_guide.md (every installed Blender add-on, its operators, which run headless, the UI-only ones and their alternatives, command-line tools, skills).
- One render cycle per builder: the next step of the Handoff (or, the first time, the brief), one full build rendered as the kit renders it (every view, lit and clay; never a reduced render of the full build), the full comparison, your own review (## Cycle <n>: what matches, what differs measured and why, a ranked list of what needs improving) and the next ## Handoff, replacing the previous one; then HANDOFF. DONE only when your review finds nothing worth improving (or the cycles are used up), after the final build and pack.py done.
- Think about what you see, then build that (builder_guide.md section 1): decide what each mark in the reference shows (one solid surface or a mass of many small elements; form shading, a marking or a glow; an outline, a crease or a seam) and build the thing it shows, so it reads as that from every view and up close.
- Understand the thing you are making, conceptually, and let it choose the approach (builder_guide.md section 1): every part is a thing with a nature (an eye, wood, a body, a tree root, a roof tile, a tyre, cloth). Know what it is made of and how it is built inside, how it grows or is made, what it does and how it behaves, how it looks in life and in this art style, how it ages; that decides the construction method and tool, the sub-parts, the topology and the materials. A part built with an approach that does not fit what it is cannot be fixed by reshaping: change the approach.
- Compare to the reference often, part by part (builder_guide.md section 6): crop each part from the reference views before you start it; after every change render that part from the same angles and put it next to the reference crop; after the build run cv.py compare and cv.py closeup for each changed part and its neighbours. For every difference, understand why: why the reference looks like that and why the build differs (the cause in the build, not the symptom); the fix follows from the cause.
- Lead and part builders (builder_guide.md section 8): the builder that reads the Handoff is the lead; it splits the generator into part modules, makes the test harness, writes one job card per part task (pack.py job-card) and gives each to its own part builder (Agent tool, subagent_type asset-part-builder, run_in_background; prompt: read part_builder_guide.md and the job card), 2 to 4 at the same time; each part builder does one job, reports and ends, and rework is a new job card for a new part builder; the lead judges each part against the reference itself and does the one full build, the full comparison, the review and the Handoff.
$common

$table"
fi
jq -n --arg c "$context" '{hookSpecificOutput: {hookEventName: "SubagentStart", additionalContext: $c}}'
