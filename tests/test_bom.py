from brickkit.bom.bom import build_bom, write_bricklink_xml, write_parts_csv, write_pick_a_brick_csv
from tests.test_builder import make


def test_bom_counts_and_exports(engine, tmp_path):
    lines = build_bom(make(engine).flatten(), engine.catalog)
    q = {(l.ldraw_part, l.color.name): l.qty for l in lines}
    assert q == {("3003", "White"): 4, ("3001", "Red"): 1}
    write_parts_csv(lines, tmp_path / "parts.csv")
    write_bricklink_xml(lines, tmp_path / "w.xml")
    write_pick_a_brick_csv(lines, tmp_path / "pab.csv")
    x = (tmp_path / "w.xml").read_text()
    assert "<ITEMID>3003</ITEMID>" in x and "<COLOR>1</COLOR>" in x and "<MINQTY>4</MINQTY>" in x
    assert (tmp_path / "parts.csv").read_text().startswith("qty,part,name")
    assert len((tmp_path / "pab.csv").read_text().strip().splitlines()) == 3


def test_extras_go_on_the_lists(engine, tmp_path):
    m = make(engine)
    m.extra("62501c01", "Black", 2, "light unit")
    lines = build_bom(m.flatten(), engine.catalog, m.extras)
    light = [l for l in lines if l.ldraw_part == "62501c01"]
    assert len(light) == 1 and light[0].qty == 2 and light[0].bl_type == "S"
    write_bricklink_xml(lines, tmp_path / "w.xml")
    x = (tmp_path / "w.xml").read_text()
    assert "<ITEMTYPE>S</ITEMTYPE><ITEMID>8870</ITEMID><MINQTY>2</MINQTY>" in x


def test_price_estimate(engine, tmp_path):
    from brickkit.bom.price import estimate, write_estimate_md
    lines = build_bom(make(engine).flatten(), engine.catalog)
    priced = estimate(lines, engine.catalog)
    assert all(0 < p.low <= p.high for p in priced)
    low, high = write_estimate_md("Test", priced, tmp_path / "p.md")
    assert 0 < low < high and "price estimate" in (tmp_path / "p.md").read_text()
