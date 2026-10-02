#!/bin/bash
# PostToolUse(Bash) hook: when a Blender run fails in a way the choice of add-on or tool explains,
# point the agent at the fix in the tools guide. Silent otherwise.
GUIDES="/tmp/claude-0/-home-user-asset-pipeline/2396fed5-5999-5364-b5d1-d9749bebc958/scratchpad"
GUIDE="$GUIDES/blender_tools_guide.md"
input="$(cat)"
out="$(printf '%s' "$input" | jq -r '.tool_response | if type == "object" then ([.stdout, .stderr] | map(select(. != null)) | join("\n")) else tostring end' 2>/dev/null)"
hint=""
case "$out" in
  *"poll() failed, context is incorrect"*)
    hint="That operator needs Blender's 3D viewport (UI only) and cannot run headless. Use the headless alternative in $GUIDE section 3 (EdgeFlow -> LoopTools Curve/Relax or CurveFitting; Auto Mirror -> a Mirror modifier with bisect; F2 or PolyQuilt -> bmesh, kit.quad_remesh or instant-meshes), or do it with bmesh, modifiers or Geometry Nodes." ;;
  *"No module named 'bl_ext"*|*"key \"bl_ext."*"not found"*|*"Add-on not loaded"*|*"addon not loaded"*)
    hint="An add-on is not enabled in this Blender run (the kit starts Blender with --factory-startup). Enable it inside the generator first: kit.enable_addon(\"bl_ext.blender_org.<id>\", with_preferences=True), or bl_ext.user_default.<id> for the pipeline's own extensions. The installed ids are in $GUIDE section 3." ;;
esac
[ -z "$hint" ] && exit 0
echo "$(date -u +%FT%TZ) PostToolUse hint" >> "$GUIDES/hooks/builder-tools.log"
jq -n --arg c "$hint" '{hookSpecificOutput: {hookEventName: "PostToolUse", additionalContext: $c}}'
