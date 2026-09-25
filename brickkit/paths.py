"""Well-known locations. Override the cache with BRICKKIT_CACHE."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = Path(os.environ.get("BRICKKIT_CACHE", ROOT / ".cache"))
MODELS_DIR = ROOT / "models"
DATA_DIR = Path(__file__).resolve().parent / "data"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
