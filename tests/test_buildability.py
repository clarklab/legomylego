from brickkit.checks import run_checks
from brickkit.model.builder import Model
from tests.test_builder import make


def check(engine, model):
    return run_checks(engine.context(model), ["buildability"])[0]


def test_simple_model_is_buildable(engine):
    assert check(engine, make(engine)).status == "pass"


def test_part_trapped_under_roof_fails(engine):
    m = Model("B", "b", {}, engine.catalog)
    s = m.main
    s.place("3001", "White")
    s.step()
    s.place("3005", "White", (-30, -24, -10))
    s.place("3005", "White", (30, -24, -10))
    s.step()
    s.place("3001", "White", (0, -48, 0))
    s.step()
    s.place("3004", "White", (0, -24, -10))
    r = check(engine, m)
    assert r.status == "fail"
    assert any(i["part"].startswith("3004") for i in r.items)


def test_same_step_order_is_free(engine):
    m = Model("B", "b", {}, engine.catalog)
    s = m.main
    s.place("3001", "White")
    s.step()
    s.place("3001", "White", (0, -48, 0))   # roof listed first, rests on the 1x1s
    s.place("3005", "White", (-30, -24, -10))
    s.place("3005", "White", (30, -24, -10))
    s.place("3004", "White", (0, -24, -10))
    assert check(engine, m).status == "pass"


def test_click_hinge_snaps_on(engine):
    """A hinge top (6134) clicks onto its base (3937): the fingers interlock, so no straight
    slide separates them, but snap-fit (hinge/clip) partners must not block the insertion."""
    m = Model("H", "h", {}, engine.catalog)
    s = m.main
    s.place("3020", "White")
    s.step()
    s.place("3937", "White", (-20, -24, -10))
    s.step()
    s.place("6134", "White", (-20, -24, -10))
    assert check(engine, m).status == "pass"


def test_snap_partner_does_not_excuse_other_parts(engine):
    """Snapping on only ignores the part it snaps onto: bricks either side still block it."""
    m = Model("H", "h", {}, engine.catalog)
    s = m.main
    s.place("3795", "White")
    s.step()
    s.place("3937", "White", (-20, -24, -10))
    s.place("3005", "White", (-50, -24, -10))
    s.place("3005", "White", (10, -24, -10))
    s.step()
    s.place("6134", "White", (-20, -24, -10))
    r = check(engine, m)
    assert r.status == "fail" and any(i["part"].startswith("6134") for i in r.items)


def test_loose_piece_after_step_fails(engine):
    m = Model("L", "l", {}, engine.catalog)
    m.main.place("3001", "White")
    m.main.step()
    m.main.place("3001", "White", (0, -200, 0))
    r = check(engine, m)
    assert r.status == "fail" and any("loose" in i["problem"] for i in r.items)
