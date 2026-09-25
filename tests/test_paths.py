import os
from pathlib import Path

from brickkit import paths


def test_paths_are_under_repo_root():
    if os.environ.get("BRICKKIT_CACHE"):
        # the documented override (e.g. a git worktree sharing the main checkout's cache)
        assert paths.CACHE == Path(os.environ["BRICKKIT_CACHE"])
    else:
        assert paths.CACHE.parent == paths.ROOT
    assert paths.MODELS_DIR == paths.ROOT / "models"
    assert paths.DATA_DIR.name == "data"
