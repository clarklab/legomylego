"""Non-LEGO hardware: stand-in parts, the hardware list, press fits and lift-off groups."""
import numpy as np

from brickkit.bom.bom import build_bom, build_hardware, write_hardware_csv
from brickkit.bom.price import estimate, hardware_summary, write_estimate_md
from brickkit.checks import run_checks
from brickkit.io.mpd import read_mpd, write_mpd
from brickkit.ldraw.matrix import rot, translate
from brickkit.model.builder import Model

INSERT = "bk-clock-insert-35mm"


def clock_model(engine, press=True, drop=0.0, hands=False):
    """A 6 x 6 plate with a clock insert lying on its studs, dial to the front (35 mm body:
    axis 43.75 LDU above the stud tops), the bezel just in front of the plate's edge."""
    m = Model("Clock", "clock", {}, engine.catalog)
    m.main.place("3958", "Tan")
    m.main.step("The insert, pushed in from above")
    m.main.place(INSERT, "Black", (0, -48 + drop, -68), tag="clock", insert=(0, -1, 0))
    if hands:
        m.main.place("bk-clock-hand-hour", "Black", (0, -48, -66), rot(z=300), tag="hands")
        m.main.place("bk-clock-hand-minute", "Black", (0, -48, -67.1), rot(z=60), tag="hands")
    if press:
        m.press_fit("clock", "rests in its cradle")
        m.press_fit("hands", "on the insert's spindle")
    return m


def test_stand_in_parts_are_real_meshes(engine):
    m = engine.geom.mesh(INSERT + ".dat")
    lo, hi = m.bbox
    assert m.certified and engine.lib.is_custom(INSERT) and not engine.lib.is_custom("3001")
    assert np.allclose(lo, (-47.5, -47.5, 0.0), atol=0.01)      # 38 mm bezel
    assert np.allclose(hi, (47.5, 47.5, 50.0), atol=0.01)       # 20 mm deep
    assert m.volume_centroid()[0] > 0                           # outward-facing, closed
    for hand in ("bk-clock-hand-hour", "bk-clock-hand-minute"):
        assert engine.geom.mesh(hand + ".dat").certified


def test_hardware_is_not_on_the_lego_lists(engine, tmp_path):
    m = clock_model(engine, hands=True)
    m.hardware("Spare button cell SR626SW", 2, "for the insert", (1, 2), "any shop")
    placed = m.flatten()
    lego = build_bom(placed, engine.catalog)
    assert [l.ldraw_part for l in lego] == ["3958"]
    hw = build_hardware(placed, engine.catalog, m.hardware_items)
    assert [(h.id, h.qty) for h in hw] == [(INSERT, 1), ("", 2)]    # hands count with it
    assert hw[0].low > 0 and "clock insert" in hw[0].name.lower() and hw[0].where
    s = hardware_summary(hw)
    assert s["items"] == 3 and s["low"] == hw[0].low + 2 * 1
    write_hardware_csv(hw, tmp_path / "hardware.csv")
    assert "where_to_buy" in (tmp_path / "hardware.csv").read_text()
    write_estimate_md("Clock", estimate(lego, engine.catalog), tmp_path / "p.md", hardware=hw)
    assert "Not LEGO: buy separately" in (tmp_path / "p.md").read_text()
    r = run_checks(engine.context(m), ["real_elements"])[0]
    assert r.status == "pass" and r.stats["hardware"] == 3 and r.stats["combinations"] == 1


def test_press_fit_connects_and_builds(engine):
    ok = run_checks(engine.context(clock_model(engine, hands=True)),
                    ["connections", "collisions", "buildability"])
    assert [r.status for r in ok] == ["pass"] * 3, [r.items for r in ok]
    assert ok[0].stats["by_kind"].get("press", 0) >= 3
    loose = run_checks(engine.context(clock_model(engine, press=False)), ["connections"])[0]
    assert loose.status == "fail"


def test_collision_check_sees_the_insert(engine):
    r = run_checks(engine.context(clock_model(engine, drop=6)), ["collisions"])[0]
    assert r.status == "fail"


def test_lift_off_group(engine):
    def model(lifts):
        m = Model("Lid", "lid", {}, engine.catalog)
        m.main.place("3001", "White")
        m.main.place("3001", "White", (0, -24, 0), tag="lid")
        m.moving_group("lid", "lid", lifts_off=lifts)
        m.pose = lambda t: {"lid": translate(0, -100 * t, 0)}
        return m
    assert run_checks(engine.context(model(False)), ["mechanism"])[0].status == "fail"
    assert run_checks(engine.context(model(True)), ["mechanism"])[0].status == "pass"


def test_mpd_embeds_stand_ins(engine, tmp_path):
    m = clock_model(engine)
    path = write_mpd(m, tmp_path / "c.mpd", engine.lib)
    text = path.read_text()
    assert f"0 FILE {INSERT}.dat" in text and "!LDRAW_ORG Unofficial_Part" in text
    assert [p for p, _, _ in read_mpd(path)] == ["3958.dat", INSERT + ".dat"]
