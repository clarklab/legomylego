import numpy as np


def _studs(conns, gender):
    return [c for c in conns if c.kind == "cyl" and c.gender == gender and c.secs
            and abs(c.secs[0][1] - 6) < 0.1]


def test_brick_2x4_has_8_studs_and_8_antistuds(engine):
    cs = engine.shadow.connectors("3001.dat")
    assert len(_studs(cs, "M")) == 8
    assert len(_studs(cs, "F")) == 8


def test_duplicates_removed(engine):
    assert len(_studs(engine.shadow.connectors("3004.dat"), "M")) == 2


def test_stud_axis_points_up_from_top_face(engine):
    stud = _studs(engine.shadow.connectors("3001.dat"), "M")[0]
    assert np.allclose(stud.axis, [0, -1, 0])
    assert abs(stud.origin[1]) < 1e-6


def test_grid_expands(engine):
    from brickkit.snaps.shadow import grid_frames
    assert len(grid_frames("C 4 C 2 20 20")) == 8
    xs = sorted({round(f[0, 3]) for f in grid_frames("C 4 C 2 20 20")})
    assert xs == [-30, -10, 10, 30]


def test_technic_pin_has_two_pin_halves(engine):
    halves = [c for c in engine.shadow.connectors("2780.dat")
              if c.gender == "M" and c.secs and c.secs[0] == ("R", 8.0, 2.0)]
    assert len(halves) == 2


def test_overlay_adds_snaps_the_shadow_library_lacks(engine):
    """74611 (Plate Round 8 x 8 with hole) has no LDCad shadow file: the bundled overlay in
    brickkit/data/shadow gives it anti-studs, and its studs still come from the LDraw part."""
    cs = engine.shadow.connectors("74611.dat")
    assert len(_studs(cs, "F")) == 44
    assert len(_studs(cs, "M")) == 44


def test_overlay_metas_merge_after_the_library(engine, tmp_path):
    from brickkit.snaps.shadow import ShadowLibrary
    (tmp_path / "parts").mkdir()
    (tmp_path / "parts" / "3004.dat").write_text(
        "0 !LDCAD SNAP_CYL [gender=F] [caps=one] [secs=R 6 4] [pos=0 0 0]\n")
    base = engine.shadow
    lib = ShadowLibrary(base.index.root, engine.lib, overlays=[tmp_path, tmp_path / "missing"])
    assert len(lib.metas("3004.dat")) == len(base.metas("3004.dat")) + 1
