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


def test_instructions_show_a_piece_that_goes_on_underneath(engine, tmp_path):
    """A step's picture cannot show a new piece that something covers. Such a step gets a small
    extra picture with the piece ringed: from the same side, before the others go over it (a
    plate with another put on it in the same step), or from the other side (a round plate
    pushed up into a floor from below)."""
    from brickkit.model.builder import Model
    from brickkit.render import instructions as I
    model = Model("Floor", "floor", {}, engine.catalog)
    m = model.main
    m.place("3020", "Black", (0, -16, 0))              # a 2 x 4 plate, one plate up
    m.place("3024", "Black", (-30, -8, 10))            # ... on a 1 x 1 at each end
    m.place("3024", "Black", (30, -8, -10))
    m.step("A silver round plate, pushed up from underneath")
    m.place("6141", "Flat Silver", (10, -8, 10))
    m.step("And a tile on top")
    m.place("3070b", "Black", (10, -24, 10))
    p = I.plan(engine, model, tmp_path)
    first, under, top = p["steps"]
    jobs = {j["name"]: j for j in p["jobs"]}
    part = lambda n: p["sets"]["floor"][n]["part"]     # noqa: E731
    # step 1: the two 1 x 1s go on first, the 2 x 4 over them: seen from above, without it
    assert [a["image"] for a in first.also] == ["step_0001_first.jpg"] and first.also[0]["text"].startswith("First")
    job = jobs["step_0001_first"]
    assert sorted(part(n) for n in job["new"]) == ["3024.dat", "3024.dat"] and job["elevation"] > 0
    assert sorted(part(n) for n in job["visible"]) == ["3024.dat", "3024.dat"]
    # step 2: the round plate goes up into what is built: seen from below
    assert [a["image"] for a in under.also] == ["step_0002_also.jpg"] and under.also[0]["text"].startswith("From below")
    job = jobs["step_0002_also"]
    assert [part(n) for n in job["new"]] == ["6141.dat"] and job["elevation"] < 0 and job["highlight"]
    assert top.also == []

    # ringed, and cut down to the piece: in a picture of the whole model it would be a speck
    img, mask = tmp_path / "x.jpg", tmp_path / "x_mask.png"
    Image.new("RGB", (1100, 820), "white").save(img)
    a = np.zeros((820, 1100), np.uint8)
    a[400:430, 500:540] = 255
    Image.fromarray(a).save(mask)
    I.outline_new_parts(img, mask, close=True)
    out = Image.open(img)
    assert out.size[0] < 500 and abs(out.size[1] / out.size[0] - 0.75) < 0.02 and not mask.exists()
    assert (np.asarray(out)[..., 2] < 60).any()        # (the yellow ring is in it)
