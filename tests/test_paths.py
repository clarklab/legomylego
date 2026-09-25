import os
from pathlib import Path

from brickkit import paths


def test_paths_are_under_repo_root():
    if "BRICKKIT_CACHE" in os.environ:          # documented override (e.g. in git worktrees)
        assert paths.CACHE == Path(os.environ["BRICKKIT_CACHE"])
    else:
        assert paths.CACHE.parent == paths.ROOT
    assert paths.MODELS_DIR == paths.ROOT / "models"
    assert paths.DATA_DIR.name == "data"
