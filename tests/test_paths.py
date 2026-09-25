from brickkit import paths


def test_paths_are_under_repo_root():
    assert paths.CACHE.parent == paths.ROOT
    assert paths.MODELS_DIR == paths.ROOT / "models"
    assert paths.DATA_DIR.name == "data"
