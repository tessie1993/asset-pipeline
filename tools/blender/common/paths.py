"""Repository paths and JSON loading for the Blender generators."""
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "assets" / "data" / "sky_village"
MODELS_DIR = REPO_ROOT / "assets" / "models"


def load_json(path: Path) -> Any:
    """Return the parsed JSON document at ``path``."""
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)
