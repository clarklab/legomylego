from brickkit.checks import run_checks
from brickkit.model.builder import Model


def test_catch_all_group(engine):
    m = Model("G", "g", {}, engine.catalog)
    m.main.place("3001", "White", tag="stand")
    m.main.place("3001", "White", (0, -24, 0))
    m.main.place("3001", "White", (0, -48, 0), tag="lid")
    m.moving_group("lid", "lid")
    m.moving_group("body", "*", exclude={"stand"})
    stand, body, lid = m.flatten()
    assert m.group_of(stand) is None and m.group_of(body) == "body" and m.group_of(lid) == "lid"


def test_allowed_contact(engine):
    def model(allow):
        m = Model("C", "c", {}, engine.catalog)
        m.main.place("3001", "White", tag="a")
        m.main.place("3001", "White", (0, -4, 0), tag="b")           # sunk 4 LDU into the first
        if allow:
            m.allow_contact("a", "b")
        return m
    assert run_checks(engine.context(model(False)), ["collisions"])[0].status == "fail"
    assert run_checks(engine.context(model(True)), ["collisions"])[0].status == "pass"


def test_captive_piece_is_not_loose(engine):
    def model(captive):
        m = Model("K", "k", {}, engine.catalog)
        s = m.main
        s.place("3001", "White")
        s.place("3005", "White", (100, -24, 0), tag="slider")       # held by a guide, no studs
        s.step()
        s.place("3001", "White", (0, -24, 0))
        if captive:
            m.captive("slider")
        return m
    assert run_checks(engine.context(model(False)), ["buildability"])[0].status == "fail"
    assert run_checks(engine.context(model(True)), ["buildability"])[0].status == "pass"
