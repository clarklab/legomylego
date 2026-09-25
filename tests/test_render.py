import shutil

import numpy as np
import pytest
from PIL import Image

from brickkit.project import Project
from brickkit.render.scene import BLENDER, render_model


@pytest.mark.skipif(not shutil.which(BLENDER) and not __import__("os").path.exists(BLENDER),
                    reason="Blender not installed")
def test_render_sample(engine, tmp_path):
    model = Project("_sample").build(engine.catalog)
    files = render_model(engine, model, tmp_path, views=["three_quarter"], size=160, samples=8)
    im = np.asarray(Image.open(files[0]).convert("RGB"), float)
    assert im.shape[:2] == (160, 160)
    assert im.std() > 8          # not a blank frame
