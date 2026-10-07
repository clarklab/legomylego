"""Well-known locations. Override the cache with BRICKKIT_CACHE."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = Path(os.environ.get("BRICKKIT_CACHE", ROOT / ".cache"))
MODELS_DIR = ROOT / "models"
DATA_DIR = Path(__file__).resolve().parent / "data"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def video_name(slug: str, width: int, height: int) -> str:
    """A finished video's file name: the model and its size, `nautilus-1080x1080.mp4` - so
    every video has a name of its own (the square showreel, the upright Quick Bricks video)."""
    return f"{slug}-{int(width)}x{int(height)}.mp4"
