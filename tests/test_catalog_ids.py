from brickkit.model.builder import Model


def test_moved_alias_is_followed(engine):
    assert engine.catalog.canonical("4073.dat") == "6141.dat"
    m = Model("T", "t", {}, engine.catalog)
    assert m.main.place("4073", "Trans-Red").part == "6141.dat"


def test_rebrickable_fallback_strips_variant_letter(engine):
    cat = engine.catalog
    assert cat.element("3023b.dat", "Trans-Light Blue") is not None


def test_search_by_words_and_colour(engine):
    rows = engine.catalog.search("dish inverted", color="Trans-Light Blue")
    parts = [r[1] for r in rows]
    assert "4740" in parts and all(r[0] >= 0 for r in rows)
