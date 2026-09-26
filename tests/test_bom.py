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
    write_estimate_md("Test", priced, tmp_path / "p.md", "2026-09-25")
    assert "Priced 2026-09-25" in (tmp_path / "p.md").read_text()


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
