def test_palette_colours_map_across_systems(engine):
    cat = engine.catalog
    tlb = cat.color("Trans-Light Blue")
    assert tlb.ldraw == 43 and tlb.rb_id == 41 and tlb.bl_id == 15 and tlb.is_trans
    assert cat.color("Trans_Light_Blue") == tlb and cat.color(43) == tlb
    assert cat.color("Coral").bl_id == 220
    assert cat.color("Dark Bluish Gray").ldraw == 72
    for name in ["Trans-Red", "Dark Red", "White", "Light Nougat", "Trans-Clear", "Black",
                 "Light Bluish Gray", "Tan"]:
        c = cat.color(name)
        assert c.rb_id is not None and c.bl_id is not None, name


def test_real_element_lookup(engine):
    cat = engine.catalog
    e = cat.element("3001.dat", "White")
    assert e is not None and e.element_ids and e.set_count > 100 and not e.rare
    assert cat.element("1974.dat", "Trans-Light Blue") is not None
    assert "Brick 2 x 4" in cat.part_name("3001.dat")


def test_missing_element_offers_substitutes(engine):
    cat = engine.catalog
    col = next(c for c in cat.colors.by_code.values()
               if c.rb_id is not None and cat.element("3001.dat", c) is None)
    assert cat.substitutes("3001.dat", col)
