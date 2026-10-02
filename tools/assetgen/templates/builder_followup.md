You build ONE 3D asset in $repo for ONE render cycle, continuing from the previous builder's Handoff below. Object `$id` ($name) of pack $pack; art style: "$style". Builds so far: $builds (the standard is $cycles).

LOOK FIRST. Before you change anything, open these yourself and compare them with the Handoff's comparison; think about what they show, not only how they look:
- the reference views: $ref_views
- the reference images: $references
- the latest compare: $compare
- the renders and close-ups the Handoff names.

THEN THE CYCLE, as $guides/builder_guide.md says (read it and $guides/blender_tools_guide.md first; the Handoff's Standing rules hold): you are this cycle's lead, so the Handoff's part tasks go to part builders at the same time (section 8: `pack.py job-card`, then the Agent tool with `subagent_type: "asset-part-builder"`); one full build of the generator, in the background: `cd $repo && timeout 900 blender -b --factory-startup --python $generator -- 2>&1 | grep -E "BUILT|RENDERED|BUILD |CV |CHECK|BAKE|KIT|Error|Traceback|line [0-9]+"`; the full comparison; your review `## Cycle <n>`; the new `## Handoff` at the end of the notes, replacing this one; end with `HANDOFF $pack $id`. When your review finds nothing worth improving, or the builds reach $cycles: the final build (`-- --final`), its review `## Cycle <n>`, the Handoff brought up to date (next step "none"), `## Report`, `python3 tools/assetgen/pack.py done $pack $id`, and end with `DONE $pack $id`.

FILES: generator $generator · part modules $parts · notes $notes · evidence $evidence · work folder $scratch (job cards and the test harness in $scratch/parts/).
FINAL MESSAGE (at most 8 lines): first line `HANDOFF $pack $id`, `DONE $pack $id` or `BLOCKED $pack $id: <reason>`; then the outline overlap per view, the triangles, the top of your Needs improving list, and the path of your notes.

$handoff
