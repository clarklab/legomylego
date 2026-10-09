import numpy as np


def test_brick_2x4_mesh(engine):
    m = engine.geom.mesh("3001.dat")
    lo, hi = m.bbox
    assert np.allclose(lo, [-40, -4, -20]) and np.allclose(hi, [40, 24, 20])
    assert m.certified
    V, cen = m.volume_centroid()
    assert 39000 < V < 40500
    assert abs(cen[0]) < 0.5 and abs(cen[2]) < 0.5


def test_main_colour_is_inherited(engine):
    assert set(np.unique(engine.geom.mesh("3001.dat").colors)) == {16}


def test_disk_cache_roundtrip(engine, tmp_path):
    from brickkit.ldraw.geometry import GeometryCache
    a = GeometryCache(engine.lib, tmp_path).mesh("3004.dat")
    b = GeometryCache(engine.lib, tmp_path).mesh("3004.dat")
    assert np.allclose(a.tris, b.tris) and a.certified == b.certified
    assert any(tmp_path.iterdir())


def test_round_meshes_for_pictures(engine):
    """Pictures draw round things with LDraw's 48-sided primitives (a round tile's rim is a
    visible 16-sided polygon otherwise); the checks keep the usual 16, same size."""
    def rim(geom):
        v = geom.mesh("98138.dat").tris.reshape(-1, 3)
        top = v[np.abs(v[:, 1] - v[:, 1].min()) < 0.6]
        out = top[np.linalg.norm(top[:, [0, 2]], axis=1) > 9.5]
        return len(np.unique(np.round(np.degrees(np.arctan2(out[:, 2], out[:, 0])), 1)))
    assert (rim(engine.geom), rim(engine.geom_round)) == (16, 48)
    assert np.allclose(np.array(engine.geom.mesh("98138.dat").bbox), np.array(engine.geom_round.mesh("98138.dat").bbox))
    assert len(engine.geom_round.mesh("3005.dat").tris) > len(engine.geom.mesh("3005.dat").tris)   # (its stud)
