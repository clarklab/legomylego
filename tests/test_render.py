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
    """Every new piece of a step is in one of its pictures (measured: render/visibility.py).
    One the step's own picture cannot show gets a small picture beside it from where it can
    be seen, with everything in place (so it is seen where it clicks in): from below, from
    behind. If none of a step's pieces show, that other side is the step's picture."""
    from brickkit.model.builder import Model
    from brickkit.render import instructions as I
    model = Model("Floor", "floor", {}, engine.catalog)
    m = model.main
    m.place("3020", "Black", (0, -16, 0))              # a 2 x 4 plate, one plate up
    m.place("3024", "Black", (-30, -8, 10))            # ... on a 1 x 1 at each end
    m.place("3024", "Black", (30, -8, -10))
    m.step("A silver round plate, pushed up from underneath; a tile on top")
    m.place("6141", "Flat Silver", (10, -8, 10))
    m.place("3070b", "Black", (10, -24, 10))
    m.step("And one more underneath, by itself")
    m.place("6141", "Flat Silver", (-10, -8, -10))
    p = I.plan(engine, model, tmp_path)
    first, mixed, under = p["steps"]
    jobs = {j["name"]: j for j in p["jobs"]}
    part = lambda n: p["sets"]["floor"][n]["part"]     # noqa: E731
    assert p["unseen"] == []
    # step 1: a 1 x 1 under the 2 x 4 (the other's side shows past the plate's edge): a small
    # picture from below, the 2 x 4 in place
    assert [a["image"] for a in first.also] == ["step_0001_under.jpg"]
    job = jobs["step_0001_under"]
    assert job["elevation"] < 0 and "3024.dat" in {part(n) for n in job["new"]}
    assert {part(n) for n in job["new"]} == {"3024.dat", "3020.dat"}   # (every piece that shows there
                                                                       # is ringed: the 2 x 4 as well)
    assert len(job["visible"]) == 3 and "in here" in first.also[0]["text"]
    # step 2: the tile shows from above, the round plate only from below
    assert mixed.view == "above" and [a["image"] for a in mixed.also] == ["step_0002_under.jpg"]
    assert [part(n) for n in jobs["step_0002_under"]["new"]] == ["6141.dat"]
    # step 3: nothing of it shows from above: the step's own picture is from below
    assert under.view == "below" and under.also == [] and jobs["step_0003"]["elevation"] < 0

    # the measure itself: a plate under a bigger one is seen from below and not from above
    from brickkit.render.visibility import Sight
    parts = [("3020.dat", np.eye(4)), ("3024.dat", np.array([[1, 0, 0, 10], [0, 1, 0, 8], [0, 0, 1, 10], [0, 0, 0, 1.0]]))]
    assert Sight(engine, parts, 30, 32).seen(1, [0, 1]) < 0.1 < 0.9 < Sight(engine, parts, 30, -30).seen(1, [0, 1])
    assert Sight(engine, parts, 30, 32).seen(0, [0, 1]) > 0.9

    # ringed, and cut down to the piece: in a picture of the whole model it would be a speck
    img, mask = tmp_path / "x.jpg", tmp_path / "x_mask.png"
    Image.new("RGB", (1100, 820), "white").save(img)
    a = np.zeros((820, 1100), np.uint8)
    a[400:430, 500:540] = 255
    Image.fromarray(a).save(mask)
    I.outline_new_parts(img, mask, close=True)
    out = Image.open(img)
    assert out.size[0] <= 550 and abs(out.size[1] / out.size[0] - 0.75) < 0.02 and not mask.exists()
    assert (np.asarray(out)[..., 2] < 60).any()        # (the yellow ring is in it)


def test_step_parts_are_drawn_to_scale(tmp_path):
    """The parts in a step's box share one scale (a 1 x 4 tile is drawn longer than a 1 x 3),
    shrunk together if the biggest would not fit; a tile or a long plate has its size under it."""
    from brickkit.booklet import booklet as B
    for name, size in (("part_a.png", (138, 76)), ("part_b.png", (112, 66)), ("part_c.png", (59, 54)),
                       ("part_big.png", (800, 300))):
        Image.new("RGBA", size).save(tmp_path / name)
    parts = [{"img": "part_a.png", "name": "Tile 1 x 4"}, {"img": "part_b.png", "name": "Tile 1 x 3"},
             {"img": "part_c.png", "name": "Plate 1 x 1"}, {"img": "sub_kit.png", "name": "Legs"}]
    B._to_scale(parts, tmp_path)
    a, b, c, kit = parts
    assert a["w"] == pytest.approx(138 * B.PART_MM, abs=0.06) and a["w"] / b["w"] == pytest.approx(138 / 112, abs=0.01)
    assert (a["size"], b["size"]) == ("1 × 4", "1 × 3") and "size" not in c and "w" not in kit
    more = [{"img": "part_a.png", "name": "Plate 1 x 4"}, {"img": "part_big.png", "name": "Plate 8 x 16"}]
    B._to_scale(more, tmp_path)                        # (the big one fits; the small one shrinks with it)
    assert more[1]["w"] <= B.PART_BOX[0] + 0.05 and more[0]["w"] / more[1]["w"] == pytest.approx(138 / 800, abs=0.01)
    assert more[0]["size"] == "1 × 4"


def test_outline_tells_touching_pieces_apart(tmp_path):
    """Two new pieces that lie end to end get a line between them (the mask has a grey per
    piece), so they do not read as one long piece; noise in the mask's greys (a dithered
    render) must not fill them with yellow."""
    from brickkit.render import instructions as I
    img, mask = tmp_path / "x.jpg", tmp_path / "x_mask.png"
    Image.new("RGB", (400, 300), (120, 120, 120)).save(img)
    a = np.zeros((300, 400), np.int16)
    a[100:130, 60:160], a[100:130, 160:260], a[180:210, 100:200] = 255, 188, 121
    noise = np.random.default_rng(1).integers(-1, 2, a.shape)
    Image.fromarray(np.where(a > 0, np.clip(a + noise, 0, 255), 0).astype(np.uint8)).save(mask)
    I.outline_new_parts(img, mask)
    out = np.asarray(Image.open(img)).astype(int)
    yellow = (out[..., 0] > 200) & (out[..., 1] > 160) & (out[..., 2] < 90)
    assert yellow[115, 158:162].all()                  # the line between the two end to end
    assert yellow[115, 56] and yellow[195, 96]         # the ring round them, and round the third
    assert not yellow[104:126, 66:154].any() and not yellow[184:206, 106:194].any()   # not inside
