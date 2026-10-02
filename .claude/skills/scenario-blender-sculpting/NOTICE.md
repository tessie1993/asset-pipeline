# Notice

This skill is `scenario-blender-sculpting` from https://github.com/scenario-labs/skills (commit
`d87071d22edb5eb5871c9034f89cada518657891`, `skills/dcc/blender/scenario-blender-sculpting/`), MIT License,
© 2026 Scenario; see `LICENSE`. It is one of the family's skills that build assets (expert,
sculpting, retopology, uv-baking, texturing-shading, hard-surface, geometry-nodes, hair,
lighting-rendering); they import `scenario-blender-expert/scripts` by a relative path, so the
folders stay side by side. Unchanged from the original.

In this repository's container, Workbench and EEVEE renders (`bx_review` review sheets, some
`*_review` helpers) need a display: run those scripts as `xvfb-run -a blender -b ...`. Live-session
tools (`bx_gui`, the MCP bridge) are not available headless; the pipeline's own builds render with
Cycles.
