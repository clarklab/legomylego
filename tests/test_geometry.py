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
