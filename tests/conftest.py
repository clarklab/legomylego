import pytest

from brickkit import paths
from brickkit.engine import Engine


@pytest.fixture(scope="session")
def engine():
    if not (paths.CACHE / "ldraw" / "LDConfig.ldr").exists():
        pytest.skip("part libraries missing: run `.venv/bin/python -m brickkit fetch`")
    return Engine()
