"""`brickkit import`: a Studio .io or LDraw file turned into a model to carry on from
(docs/new-model.md): its exact parts and positions as a design.py."""
import zipfile
from pathlib import Path

import numpy as np

from brickkit import paths
from brickkit.io import ldraw_import as I
from brickkit.ldraw.matrix import rot

ONE = "1 0 0 0 1 0 0 0 1"

MPD = f"""0 FILE main.ldr
1 4 0 0 0 {ONE} 3001.dat
0 STEP
1 14 100 0 0 0 0 1 0 1 0 -1 0 0 Wing Left.ldr
0 STEP
1 15 0 -24 0 {ONE} 3001.dat
0 NOFILE
0 FILE Wing Left.ldr
1 16 0 0 20 {ONE} 3024.dat
0 STEP
1 1 0 -8 20 {ONE} 3024.dat
0 NOFILE
"""


def test_read_flattens_sub_models(tmp_path):
    """Sub-models are flattened: each part where it ends up, colour 16 taking its parent's
    colour, the step being the top file's (a sub-model goes on in one step)."""
    f = tmp_path / "bird.mpd"
    f.write_text(MPD)
    rows = I.read(f)
    assert [(r["part"], r["color"], r["step"]) for r in rows] == [
        ("3001.dat", 4, 0), ("3024.dat", 14, 1), ("3024.dat", 1, 1), ("3001.dat", 15, 2)]
    assert np.allclose(rows[1]["M"][:3, 3], (120, 0, 0))      # (0, 0, 20) turned, then moved
    assert rows[1]["path"] == ("wing left.ldr",) and rows[0]["path"] == ()
    wing = I.read(f, sub="Wing Left")                         # just the sub-model, its own steps
    assert [(r["color"], r["step"]) for r in wing] == [(16, 0), (1, 1)]


def test_unpack_io(tmp_path):
    """A .io is a zip with model.ldr in it; an LDraw file is read as it is."""
    io = tmp_path / "bird.io"
    with zipfile.ZipFile(io, "w") as z:
        z.writestr("model.ldr", MPD)
        z.writestr("thumbnail.png", b"png")
    out = I.unpack(io, tmp_path / "unpacked")
    assert out == tmp_path / "unpacked" / "model.ldr" and out.read_text() == MPD
    ldr = tmp_path / "bird.ldr"
    assert I.unpack(ldr, tmp_path / "x") == ldr


def test_turn_writes_rotations():
    assert I.turn(np.eye(3)) is None
    assert I.turn(rot(y=90)) == "rot(y=90)"
    assert I.turn(rot(x=180)) == "rot(x=180)"
    tilt = I.turn(rot(z=5))                                   # (a wing on its clip)
    assert tilt.startswith("R(") and np.allclose(eval(tilt, {"R": lambda *m: np.array(m).reshape(3, 3)}),
                                                 rot(z=5), atol=1e-4)


def test_reconcile_moves_a_studio_part_to_ldraws_origin(engine, tmp_path):
    """Studio keeps its own copy of each part, and a few have another origin: such a part is
    matched to LDraw's by shape and its rows moved, so it sits where the designer put it."""
    real = Path(engine.lib.resolve("3024.dat")).read_text(encoding="utf-8", errors="replace")
    studio = tmp_path / "model2.ldr"
    studio.write_text("0 FILE 3024.dat\n1 16 0 12 0 1 0 0 0 1 0 0 0 1 inner.dat\n0 NOFILE\n"
                      f"0 FILE inner.dat\n{real}\n0 NOFILE\n"
                      f"0 FILE 3001.dat\n{Path(engine.lib.resolve('3001.dat')).read_text(errors='replace')}\n")
    M = np.eye(4)
    M[:3, 3] = (40, -8, 0)
    rows = [{"part": "3024.dat", "color": 4, "M": M.copy(), "step": 0, "path": ()},
            {"part": "3001.dat", "color": 4, "M": np.eye(4), "step": 0, "path": ()}]
    fixed, lost = I.reconcile(engine, rows, studio)
    assert lost == [] and len(fixed) == 1 and fixed[0].startswith("3024.dat -> 3024.dat")
    assert np.allclose(rows[0]["M"][:3, 3], (40, 4, 0), atol=0.01)    # 12 lower, as Studio drew it
    assert np.allclose(rows[1]["M"], np.eye(4))                       # (LDraw's own: left alone)


def test_import_model_end_to_end(engine, tmp_path, monkeypatch):
    """A file with its own steps becomes models/SLUG: a design.py that builds the same parts
    in the same places (set down on y = 0), the palette its colours need, and it passes."""
    from brickkit.checks import run_checks
    from brickkit.project import Project
    monkeypatch.setattr(paths, "MODELS_DIR", tmp_path / "models")
    src = tmp_path / "in" / "stack.ldr"
    src.parent.mkdir()
    src.write_text(f"1 4 200 -100 40 {ONE} 3001.dat\n0 STEP\n"
                   f"1 14 200 -124 40 {ONE} 3003.dat\n0 STEP\n"
                   f"1 1 210 -132 50 0 0 1 0 1 0 -1 0 0 3024.dat\n0 STEP\n")
    r = I.import_model(engine, "stack", src, name="Stack")
    assert (r["parts"], r["steps"], r["own_steps"], r["unknown"]) == (3, 3, True, [])
    d = tmp_path / "models" / "stack"
    text = (d / "design.py").read_text()
    assert text.count("m.step(") == 3 and "m.place('3001', 'red', (0, -24, 0))" in text
    assert "m.place('3024', 'blue', (10, -56, 10), rot(y=90))" in text
    toml = (d / "model.toml").read_text()
    assert 'red = "Red"' in toml and 'yellow = "Yellow"' in toml and 'blue = "Blue"' in toml
    assert (d / "NOTES.md").exists() and (d / "reference").is_dir()
    proj = Project("stack", tmp_path / "models")
    model = proj.build(engine.catalog)
    assert len(model.flatten()) == 3
    res = {c.name: c.status for c in run_checks(engine.context(model, proj.checks_config),
                                                ["connections", "collisions", "buildability"])}
    assert set(res.values()) == {"pass"}, res


def test_import_works_out_steps(engine, tmp_path, monkeypatch):
    """A file without steps (Studio models often have none): a build order is worked out, each
    piece going onto something already there, pairs of the same piece in one step."""
    monkeypatch.setattr(paths, "MODELS_DIR", tmp_path / "models")
    src = tmp_path / "in" / "pile.ldr"
    src.parent.mkdir()
    rows = [f"1 15 0 -72 0 {ONE} 3003.dat", f"1 4 0 0 0 {ONE} 3001.dat",
            f"1 14 -20 -24 0 {ONE} 3003.dat", f"1 14 20 -24 0 {ONE} 3003.dat",
            f"1 1 0 -48 0 {ONE} 3001.dat", f"1 15 0 -80 0 {ONE} 3024.dat",
            f"1 2 0 -88 0 {ONE} 3024.dat"]
    src.write_text("\n".join(rows) + "\n")
    r = I.import_model(engine, "pile", src)
    assert r["parts"] == 7 and not r["own_steps"] and r["steps"] == 6
    text = (tmp_path / "models" / "pile" / "design.py").read_text()
    places = [ln.split("'")[1] + ln.split("(")[2].split(")")[0] for ln in text.splitlines() if "m.place(" in ln]
    assert places[0] == "30010, -24, 0" and places[-1] == "30240, -112, 0"        # bottom up
    assert places[1][:4] == places[2][:4] == "3003" and text.count("m.step(") == 6


def _box(lo, hi):
    """The six faces of a box, as quads."""
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    c = lambda *p: np.array(p, float)       # noqa: E731
    return [c((x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)), c((x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)),
            c((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)), c((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)),
            c((x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)), c((x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1))]


def test_slide_lines_up_flat_faces():
    """Studio draws the logo on a stud, so its copy of a part can be a little taller than
    LDraw's: the two are lined up by their flat faces, not by the corners of their boxes."""
    studio = _box((0, 0, 0), (40, 8, 20)) + _box((8, -4.45, 8), (12, 0, 12))      # a plate, a tall stud
    ours = [v + (0, 0.25, 0) for v in _box((0, 0, 0), (40, 8, 20)) + _box((8, -4, 8), (12, 0, 12))]
    assert I._slide(studio, ours, 1, 0.5) == -0.25                # (corner to corner: 0.2 out)
    assert I._slide(studio, studio, 1, 0.5) == 0.0
