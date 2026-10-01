"""glTF export for Godot: +Y up, modifiers applied, custom properties as glTF extras."""
from pathlib import Path

import bpy


def export_glb(filepath: Path, selection: list[bpy.types.Object] | None = None,
               animations: bool = False) -> Path:
    """Export the scene (or ``selection``) to ``filepath`` as a .glb and return the path.

    +Y up, modifiers applied, custom properties as glTF extras, animations only when requested.
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    if selection is not None:
        bpy.ops.object.select_all(action="DESELECT")
        for obj in selection:
            obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=str(filepath),
        export_format="GLB",
        use_selection=selection is not None,
        export_yup=True,
        export_apply=True,
        export_extras=True,
        export_animations=animations,
        export_animation_mode="ACTIONS",
        export_image_format="AUTO",
    )
    return filepath
