import numpy as np

from brickkit.io.mpd import read_mpd, write_mpd
from tests.test_builder import make


def test_mpd_roundtrip(engine, tmp_path):
    m = make(engine)
    path = tmp_path / "t.mpd"
    write_mpd(m, path)
    parts = read_mpd(path)
    flat = m.flatten()
    assert len(parts) == len(flat)
    for (part, code, M), p in zip(parts, flat):
        assert part == p.part and code == p.color.ldraw and np.allclose(M, p.M)
    text = path.read_text()
    assert text.startswith("0 FILE t.ldr") and "0 FILE pillar.ldr" in text
    assert text.count("0 STEP") == 4
