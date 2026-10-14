import os

import pytest

# the tests never reach BrickLink's API or lego.com, whatever keys this machine has
os.environ.setdefault("BRICKKIT_NO_BRICKLINK", "1")
os.environ.setdefault("BRICKKIT_NO_PICK_A_BRICK", "1")

from brickkit import paths
from brickkit.engine import Engine


@pytest.fixture(scope="session")
def engine():
    if not (paths.CACHE / "ldraw" / "LDConfig.ldr").exists():
        pytest.skip("part libraries missing: run `.venv/bin/python -m brickkit fetch`")
    return Engine()
