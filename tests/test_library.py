from brickkit.ldraw.library import normalize


def test_normalize():
    assert normalize("S\\3001S01.DAT") == "s/3001s01.dat"
    assert normalize("3001") == "3001.dat"


def test_resolve_and_colours(engine):
    lib = engine.lib
    assert lib.resolve("3001") is not None
    assert lib.resolve("s\\3001s01.dat") is not None
    assert lib.resolve("48\\1-4cyli.dat") is not None
    assert lib.colors[43].name == "Trans_Light_Blue" and lib.colors[43].is_trans
    assert "Brick  2 x  4" in lib.description("3001.dat")
