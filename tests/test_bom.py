import pytest
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


def test_live_prices_used_and_dated(engine, tmp_path):
    from brickkit.bom.price import estimate, summary, write_estimate_md
    lines = build_bom(make(engine).flatten(), engine.catalog)
    key = lambda l: (l.bl_type, l.bl_part, l.color.bl_id)
    live = {"day": "2026-09-25", "prices": {
        key(lines[0]): {"stock": {"ok": True, "avg": 0.12}, "sold": {"ok": True, "avg": 0.08}}}}
    priced = estimate(lines, engine.catalog, live)
    first = next(p for p in priced if p.line is lines[0])
    assert first.live and (first.low, first.high) == (0.08, 0.12)
    s = summary(priced, "2026-09-25")
    assert s["source"] == "bricklink" and s["date"] == "2026-09-25" and s["live_lines"] == 1
    # the BrickLink price: the six-month sold average; a line with no data is named, not guessed
    bl = s["bricklink"]
    assert bl["usd"] == round(0.08 * lines[0].qty, 2) and bl["lines"] == 1 and len(bl["missing"]) == 1
    assert s["pick_a_brick"] is None
    write_estimate_md("Test", priced, tmp_path / "p.md", "2026-09-25")
    md = (tmp_path / "p.md").read_text()
    assert "**BrickLink: $" in md and "2026-09-25" in md and "Not priced" in md


def test_pick_a_brick_price(engine, tmp_path):
    """The Pick a Brick price: each element at its price that day; a line Pick a Brick doesn't
    sell is named, and a Standard (not Bestseller) piece is pointed out."""
    from brickkit.bom.price import estimate, headline, summary, write_estimate_md
    lines = build_bom(make(engine).flatten(), engine.catalog)
    a, b = lines[0], lines[1]
    pab = {"day": "2026-10-14", "prices": {
        a.element_id: {"ok": True, "usd": 0.25, "bestseller": True},
        b.element_id: {"ok": True, "usd": 0.1, "bestseller": False}}}
    s = summary(estimate(lines, engine.catalog, None, pab), None, "2026-10-14")
    pb = s["pick_a_brick"]
    assert pb["usd"] == round(0.25 * a.qty + 0.1 * b.qty, 2) and pb["date"] == "2026-10-14"
    assert pb["lines"] == 2 and not pb["missing"] and len(pb["standard"]) == 1
    assert s["bricklink"] is None and "Pick a Brick $" in headline(s)
    gone = {"day": "2026-10-14", "prices": {a.element_id: {"ok": False, "error": "not on Pick a Brick"},
                                             b.element_id: {"ok": True, "usd": 0.1, "bestseller": True}}}
    priced = estimate(lines, engine.catalog, None, gone)
    pb = summary(priced, None, "2026-10-14")["pick_a_brick"]
    assert pb["lines"] == 1 and len(pb["missing"]) == 1 and not pb["standard"]
    write_estimate_md("Test", priced, tmp_path / "p.md", pab_day="2026-10-14")
    md = (tmp_path / "p.md").read_text()
    assert "**Pick a Brick: $" in md and "Not sold there" in md and "one parcel" in md


def test_bricklink_oauth_header(monkeypatch):
    from brickkit.bom import live_price
    monkeypatch.setattr(live_price.time, "time", lambda: 1700000000)
    monkeypatch.setattr(live_price.secrets, "token_hex", lambda n: "abc")
    cred = dict(zip(live_price.KEYS, ("ck", "cs", "tk", "ts")))
    h = live_price._auth_header("GET", "https://api.bricklink.com/api/store/v1/items/PART/3001/price",
                                {"color_id": "5", "guide_type": "stock"}, cred)
    assert h.startswith("OAuth realm=") and 'oauth_consumer_key="ck"' in h and 'oauth_token="tk"' in h
    assert h == live_price._auth_header("GET", "https://api.bricklink.com/api/store/v1/items/PART/3001/price",
                                        {"color_id": "5", "guide_type": "stock"}, cred)


def test_choose_element_follows_pick_a_brick():
    """Newest ID, but not from the block Pick a Brick doesn't stock when an older ID exists, and
    swapped for the ID an upload showed it accepts (data/pick_a_brick.json)."""
    from brickkit.bom.bom import choose_element
    assert choose_element(["243101", "6548255"]) == "243101"                  # White 1x4 tile
    assert choose_element(["6156667", "6550161", "6552162"]) == "6156667"     # White 2x3 tile
    assert choose_element(["394126", "614326", "614376"]) == "614326"         # Black 2x2 round brick
    assert choose_element(["6386637", "6511024"]) == "6511024"                # accepted as is
    assert choose_element(["6550138"]) == "6550138"                           # nothing else to use
    assert choose_element(["4121715"]) == "6279875"       # Black friction pin: the ID it is sold as
    assert choose_element(["428226", "428276"]) == "428226"                   # Black 2 x 16 plate
    assert choose_element([]) == ""


def test_pick_a_brick_csv_leaves_out_unavailable(tmp_path, monkeypatch):
    import csv
    from brickkit.bom import bom
    from brickkit.bom.bom import BomLine, write_pick_a_brick_csv
    from brickkit.catalog.colors import Color
    monkeypatch.setattr(bom, "pick_a_brick_data", lambda: {"unavailable": ["4121715"]})
    black = Color(name="Black", ldraw=0, rgb="#1B2A34", alpha=255, rb_id=0, bl_id=11)
    lines = [BomLine("2780", "2780", "2780", "Pin", black, 2, "4121715", False),
             BomLine("3001", "3001", "3001", "Brick 2x4", black, 3, "300126", False)]
    write_pick_a_brick_csv(lines, tmp_path / "p.csv")
    rows = list(csv.reader(open(tmp_path / "p.csv")))
    assert rows == [["elementId", "quantity"], ["300126", "3"]]


def test_bricklink_numbers(engine):
    """BrickLink files some parts under another number than Rebrickable (data/bricklink_numbers.json):
    its lists use BrickLink's, the Rebrickable column keeps Rebrickable's."""
    cat = engine.catalog
    assert cat.rb_part("3070b.dat") == "3070b" and cat.bl_part("3070b.dat") == "3070"
    assert cat.bl_part("6141.dat") == "4073" and cat.bl_part("4032a.dat") == "4032"
    assert cat.bl_part("3001.dat") == "3001"


def test_prefer_what_pick_a_brick_sells(engine, monkeypatch):
    """A line whose element ID Pick a Brick doesn't sell takes another ID for the same part and
    colour that it does (LEGO renumbers pieces); a line Pick a Brick sells is left alone."""
    from brickkit.bom import pab_price
    from brickkit.bom.bom import BomLine
    white = engine.catalog.color("White")
    e = engine.catalog.element("3004.dat", white)                 # a White 1 x 2 brick: several IDs
    assert len(e.element_ids) > 1
    l = BomLine("3004", "3004", "3004", "Brick 1 x 2", white, 2, e.element_ids[0], False)
    lines = [l] + build_bom(make(engine).flatten(), engine.catalog)
    sold = e.element_ids[-1]
    monkeypatch.setattr(pab_price.PickABrick, "lookup",
                        lambda self, el: {"ok": True, "usd": 0.1, "bestseller": True} if el == sold
                        else {"ok": False, "error": "not on Pick a Brick"})
    monkeypatch.setattr(pab_price.PickABrick, "save", lambda self: None)
    pab = {"day": "2026-10-14", "prices": {x.element_id: ({"ok": True, "usd": 0.1} if x is not l
                                                         else {"ok": False}) for x in lines}}
    before = [x.element_id for x in lines]
    assert pab_price.prefer_sold(lines, pab, engine.catalog, log=lambda m: None) == 1
    assert l.element_id == sold and [x.element_id for x in lines[1:]] == before[1:]
