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
