"""Technique warnings: locking hinges set between clicks, parts sitting on studs their snap
data has no holes for; and the swivel hinge's two halves bought as one piece."""
import numpy as np

from brickkit.bom.bom import build_bom
from brickkit.checks import run_checks
from brickkit.ldraw.matrix import rot, transform
from brickkit.model.builder import Model


def run(engine, model, name):
    return run_checks(engine.context(model), [name])[0]


def _about(point, R):
    p = np.asarray(point, float)
    M = np.eye(4)
    M[:3, :3] = R
    M[:3, 3] = p - R @ p
    return M


def _hinged(engine, angle):
    """A locking hinge plate with two fingers on its side on a plate, and the one-finger half
    turned `angle` degrees about their common line."""
    m = Model("H", "h", {}, engine.catalog)
    m.main.place("3022", "Black")
    m.main.step()
    m.main.place("60471", "Black", (10, -8, 0), rot(y=90))      # fingers along Z at x = -10
    m.main.step()
    M = _about((-10, -6, 0), rot(z=angle)) @ transform((-30, -8, 0), rot(y=-90))
    m.main.place("44567b", "Black", M[:3, 3], M[:3, :3])
    return m


def _notes(r, word):
    return [i for i in r.items if word in i["problem"]]


def test_locking_hinge_on_a_click_is_fine(engine):
    for a in (0, 22.5, 45, -67.5, 90):
        m = _hinged(engine, a)
        assert run(engine, m, "connections").stats["by_kind"].get("hinge") == 1, a
        r = run(engine, m, "technique")
        assert not _notes(r, "locking hinge"), (a, r.items)


def test_locking_hinge_between_clicks_warns(engine):
    for a in (10, 37, -50):
        r = run(engine, _hinged(engine, a), "technique")
        notes = _notes(r, "locking hinge")
        assert len(notes) == 1 and r.status == "warn", (a, r.items)


def test_hinge_angle_is_measured_about_the_hinge():
    from brickkit.checks.technique import hinge_angle, off_click
    axis = np.array([1.0, 0, 0])
    assert abs(hinge_angle(axis, np.eye(3), rot(x=30)) - 30) < 1e-6
    assert abs(hinge_angle(axis, rot(y=180), rot(x=-45) @ rot(z=180)) % 22.5) < 1e-6
    assert off_click(44.0, 22.5) == 1.0 and off_click(-23.5, 22.5) == 1.0


def test_part_on_studs_without_holes_warns(engine, monkeypatch):
    """A part whose snap data lacks its stud holes, set on studs, gets a warning (here 3024's
    holes are hidden from the check)."""
    m = Model("N", "n", {}, engine.catalog)
    m.main.place("3022", "Black")
    m.main.step()
    m.main.place("3024", "Black", (-10, -8, -10))
    assert not _notes(run(engine, m, "technique"), "no stud holes")
    real = engine.shadow.connectors

    def no_holes(name):
        cs = real(name)
        if "3024" in name:
            return [c for c in cs if not (c.kind == "cyl" and c.gender == "F")]
        return cs
    monkeypatch.setattr(engine.shadow, "connectors", no_holes)
    notes = _notes(run(engine, m, "technique"), "no stud holes")
    assert len(notes) == 1 and "3024" in notes[0]["part"]


def test_swivel_halves_are_bought_as_one_hinge(engine):
    m = Model("S", "s", {}, engine.catalog)
    m.main.place("3022", "Black")
    m.main.place("2429", "Black", (0, -8, -10))
    m.main.place("2430", "Black", _about((0, 0, -10), rot(y=40))[:3, 3] + (0, -8, 0),
                 rot(y=40))
    lines = {l.ldraw_part: l for l in build_bom(m.flatten(), engine.catalog)}
    assert "2430" not in lines
    assert lines["2429"].qty == 1 and lines["2429"].rb_part == "73983"
    assert lines["2429"].bl_part == "73983" and not lines["2429"].rare
    assert run(engine, m, "real_elements").status == "pass"
