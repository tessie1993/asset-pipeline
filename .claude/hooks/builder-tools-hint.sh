#!/bin/bash
# PostToolUse(Bash) hook: when a Blender run fails in a way the choice of add-on or tool explains
# (an operator that needs the UI, an add-on that is not enabled), point the agent at the fix in the
# Blender tools guide. Silent otherwise. Logs each hint to .scratch/assetgen/hooks.log.

ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd)}"
GUIDE="$ROOT/.claude/skills/image-to-assets/references/blender_tools_guide.md"
LOG="$ROOT/.scratch/assetgen/hooks.log"
command -v jq >/dev/null 2>&1 || exit 0

input="$(cat)"
out="$(printf '%s' "$input" | jq -r '.tool_response | if type == "object" then ([.stdout, .stderr] | map(select(. != null)) | join("\n")) else tostring end' 2>/dev/null)"
hint=""
case "$out" in
  *"poll() failed, context is incorrect"*)
    hint="That operator needs Blender's 3D viewport (UI only) and cannot run headless. Use the headless alternative in $GUIDE section 3 (EdgeFlow -> LoopTools Curve/Relax or CurveFitting; Auto Mirror -> a Mirror modifier with bisect; F2 or PolyQuilt -> bmesh, kit.quad_remesh or instant-meshes), or do it with bmesh, modifiers or Geometry Nodes." ;;
  *"No module named 'bl_ext"*|*"key \"bl_ext."*"not found"*|*"Add-on not loaded"*|*"addon not loaded"*)
    hint="An add-on is not enabled in this Blender run (the kit starts Blender with --factory-startup). Enable it inside the script first: kit.enable_addon(\"bl_ext.blender_org.<id>\", with_preferences=True), or bl_ext.user_default.<id> for the pipeline's own extensions. The installed ids are in $GUIDE section 3." ;;
esac
[ -z "$hint" ] && exit 0
mkdir -p "$(dirname "$LOG")" 2>/dev/null && echo "$(date -u +%FT%TZ) PostToolUse hint" >> "$LOG" 2>/dev/null
jq -n --arg c "$hint" '{hookSpecificOutput: {hookEventName: "PostToolUse", additionalContext: $c}}'
