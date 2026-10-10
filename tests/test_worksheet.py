"""The class's sorting sheet (brickkit worksheet): every piece as an outline at its real size."""
import numpy as np

from brickkit import paths
from brickkit.booklet import worksheet as W
from brickkit.project import Project


def test_outline_is_real_size(engine):
    """An outline is the piece seen from above, in mm, a little larger all round so the piece
    drops in: a 2 x 2 brick is 16 mm square, a 1 x 4 plate 32 by 8, a round 2 x 2 tile round."""
    box = lambda part: W.outline(engine, [(part, np.eye(4))]).max(0)      # noqa: E731
    for part, (w, h) in (("3003.dat", (16, 16)), ("3710.dat", (32, 8)), ("41539.dat", (64, 64))):
        got = box(part)
        assert np.all(got > (w, h)) and np.all(got < np.array((w, h)) + 2 * W.EASE + 0.01)
    tile = W.outline(engine, [("14769.dat", np.eye(4))])
    r = np.linalg.norm(tile - tile.mean(0), axis=1)
    assert len(tile) > 12 and r.max() - r.min() < 0.3 and abs(r.mean() - (8 + W.EASE)) < 0.3


def test_worksheet_rows(engine):
    """The courthouse mini's sheet: an outline for every one of its 64 pieces, each line with
    its picture and a name a child can read, the figure's legs and torso among them, and
    nothing too wide for a column."""
    proj = Project("caldwell_mini", paths.MODELS_DIR)
    ctx = W.build(engine, proj, proj.build(engine.catalog))
    rows = ctx["rows"]
    assert ctx["pieces"] == sum(r["qty"] for r in rows) == 64
    assert ctx["title"].startswith("Build the") and len(ctx["facts"]) == 6
    assert all(r["img"] and (proj.out / "booklet" / r["img"]).exists() for r in rows)
    lawn = next(r for r in rows if r["name"].startswith("8 x 8 plate"))
    assert 64 < lawn["w"] < 65.3 and 64 < lawn["h"] < 65.3 and lawn["qty"] == 1
    legs = next(r for r in rows if r["name"] == "his legs")
    assert 14 < legs["w"] < 22 and 10 < legs["h"] < 20            # from the front, not from above
    column = (ctx["page_w"] - 2 * ctx["margin"] - ctx["gutter"]) / 2
    assert all(r["across"] * (r["w"] + 2.0) - 2.0 <= column - 6.0 + 1e-6 for r in rows)
