# Notice

This skill is `blender-image-to-3d` from
https://github.com/majidmanzarpour/blender-game-skills (commit
`f0ef29385a03de139957e6f700b801cdc00b7e29`, `skills/blender-image-to-3d/`), MIT License,
© 2026 Majid Manzarpour; see `LICENSE`. nokepom vendored part of it in its later pull requests;
this copy holds all of it: `SKILL.md`, `references/`, `scripts/`, `assets/` and `evals/`.

Changed from the original: the frontmatter `description`, scoped to the `/image-to-assets` agents
so it never competes with that skill, and `user-invocable: false`. Nothing else is changed.

In this repository's container, `scripts/review_render.py`, `scripts/roundtrip.py` and
`scripts/world_gate.py` render with Workbench, which needs a display: run them as
`xvfb-run -a blender -b ...`. The pipeline's own builds render with Cycles and need none.
