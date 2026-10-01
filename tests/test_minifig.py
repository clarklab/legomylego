"""Minifigures: components as sold (Rebrickable / BrickLink assemblies) against LDraw pieces,
the standard figure geometry, the parts lists and the checks."""
import numpy as np
import pytest

from brickkit.bom.bom import build_bom, minifig_count, write_bricklink_xml
from brickkit.checks import run_checks
from brickkit.io.mpd import read_mpd, write_mpd
from brickkit.model.builder import Model
from brickkit.model.minifig import grip_up

NED = dict(head="3626cpr0754", torso="973c01h01pr9741", legs=("970c05", "Dark Blue"),
           hair=("62810", "Reddish Brown"), accessory=("18041", "Flat Silver"),
           pose={"arm_r": grip_up()})


def figure(engine, at=(0, 0, 10), **kw):
    m = Model("Fig", "fig", {}, engine.catalog)
    m.main.place("3958", "Dark Bluish Gray")
    m.main.step("The figure")
    fig = m.minifig("ned", at, **{**NED, **kw})
    return m, fig


def test_ldraw_headers_cross_reference_prints(engine):
    cat = engine.catalog
    assert cat.rb_part("3626cp01") == "3626cpr0001"          # a printed head, by its header
    assert cat.xref.ldraw_for("3626cpr0001") == ["3626cp01"]
    assert cat.rb_part("3001") == "3001"                     # plain parts unchanged
    # minifigure parts count for the sets their figures come in, with those sets' years
    e = cat.element("3626cpr0001", "Yellow")
    assert e.set_count > 10 and e.last_year >= 2016


def test_torso_assembly_resolves_to_ldraw_pieces(engine):
    figs = engine.catalog.figs
    t = figs.component("torso", "973c01h01pr9741")          # colour: the one it came in
    assert t.color.name == "White" and not t.stand_in
    assert t.arm_color.name == "Yellow" and t.hand_color.name == "Yellow"
    assert t.bl_part == "973pb3974c01" and t.source == "76382p3w"
    assert [p.slot for p in t.pieces] == ["torso", "arm_r", "arm_l", "hand_r", "hand_l"]
    assert t.piece("torso").part == "973p3w.dat" and t.piece("torso").color.name == "White"
    assert t.piece("arm_r").color.name == "Yellow"
    # the same torso by its LDraw shortcut or its BrickLink number
    assert figs.component("torso", "76382p3w").rb_part == t.rb_part
    assert figs.component("torso", "973pb3974c01").rb_part == t.rb_part
    with pytest.raises(ValueError):
        figs.component("head", "973c01h01pr9741")


def test_legs_and_heads(engine):
    figs = engine.catalog.figs
    legs = figs.component("legs", "970c05", "Dark Blue")
    assert legs.bl_part == "970c00" and legs.leg_color.name == "Dark Blue"
    assert [p.part for p in legs.pieces] == ["3815b.dat", "3816c.dat", "3817c.dat"]
    two = figs.component("legs", "970c14", "Dark Bluish Gray")   # grey legs, darker hips
    assert two.bl_part == "970c86" and two.piece("hips").color.name == "Dark Bluish Gray"
    assert two.piece("leg_l").color.name == "Light Bluish Gray"
    printed = figs.component("legs", "970c03pr0408")
    assert printed.piece("leg_r").part == "3816cp71.dat" and printed.bl_part.startswith("970c00pb")
    head = figs.component("head", "3626cpr0001", "Yellow")
    assert head.pieces[0].part == "3626cp01.dat" and head.bl_part


def test_print_without_ldraw_model_is_a_stand_in(engine):
    t = engine.catalog.figs.component("torso", "973c05h01pr0807")   # Sea Captain, 2013
    assert t.stand_in and t.piece("torso").part == "973.dat"
    assert t.piece("torso").color.name == "Dark Blue" and t.piece("hand_l").color.name == "Yellow"
    m, fig = figure(engine, torso=t)
    assert fig.stand_ins == [t]
    r = run_checks(engine.context(m), ["real_elements"])[0]
    assert r.stats["stand_ins"] == 1
    assert any(i["severity"] == "info" and "no model" in i["problem"] for i in r.items)


def test_figure_geometry_and_checks(engine):
    m, fig = figure(engine)
    placed = m.flatten()
    by = {p.part: p for p in placed}
    # feet on the plate's studs, the body 1.2 LDU behind them
    assert np.allclose(by["3815b.dat"].M[:3, 3], (0, -40, 11.2))
    assert np.allclose(by["3626cpq0.dat"].M[:3, 3], (0, -96, 11.2))
    results = {r.name: r for r in run_checks(engine.context(m))}
    assert all(r.status == "pass" for r in results.values()), \
        {n: r.items[:3] for n, r in results.items() if r.status != "pass"}
    kinds = results["connections"].stats["by_kind"]
    assert kinds.get("clip") == 1 and kinds.get("kit", 0) >= 6
    # the harpoon stands upright with its point up (LDraw draws it point up, -Y), leaning
    # out with the arm (the shoulder pins tilt the arms by 9.8 degrees)
    harpoon = by["18041.dat"]
    assert abs(harpoon.M[1, 1] - np.cos(np.radians(9.79))) < 0.01


def test_figure_off_the_stud_grid_is_loose(engine):
    m, _ = figure(engine, at=(0, 0, 0))                    # between the plate's studs
    assert run_checks(engine.context(m), ["connections"])[0].status == "fail"


def test_parts_lists_name_the_assemblies(engine, tmp_path):
    m, _ = figure(engine)
    lines = build_bom(m.flatten(), engine.catalog)
    by = {l.rb_part: l for l in lines}
    assert set(by) == {"3958", "970c05", "973c01h01pr9741", "3626cpr0754", "62810", "18041"}
    assert by["973c01h01pr9741"].kind == "torso" and by["973c01h01pr9741"].qty == 1
    assert by["973c01h01pr9741"].bl_part == "973pb3974c01"
    assert by["970c05"].bl_part == "970c00" and by["970c05"].color.name == "Dark Blue"
    assert by["973c01h01pr9741"].element_id                     # LEGO element ID
    assert minifig_count(m) == 1
    assert sum(l.qty for l in lines) == 6
    # a print with no known BrickLink number stays off the wanted list
    t = engine.catalog.figs.component("torso", "973c05h01pr0807")
    m2, _ = figure(engine, torso=t)
    missing = write_bricklink_xml(build_bom(m2.flatten(), engine.catalog), tmp_path / "w.xml")
    assert [l.rb_part for l in missing] == ["973c05h01pr0807"]
    assert "973c05h01pr0807" not in (tmp_path / "w.xml").read_text()


def test_kits_are_bought_not_built(engine, tmp_path):
    m, fig = figure(engine)
    order = [s for s, _ in m.instruction_order()]
    assert "ned" in order and "ned_torso" not in order and "ned_legs" not in order
    assert m.submodels["ned_torso"].kit is fig.torso
    # the MPD keeps the kits as submodels and flattens back to the same pieces
    path = write_mpd(m, tmp_path / "f.mpd", engine.lib)
    assert len(read_mpd(path)) == len(m.flatten())


def test_close_up_view_frames_one_figure(engine):
    from brickkit.render.scene import close_spec
    m, _ = figure(engine)
    spec = close_spec(engine, m, "ned", m.flatten())
    lo, hi = spec["bounds"]
    assert spec["name"] == "close_ned" and hi[1] - lo[1] < 150     # the figure, not the plate


def test_approximate_model_of_a_real_part(engine, tmp_path):
    """10165c01 (the Series 8 Diver's brass helmet) has no LDraw model: brickkit ships an
    approximate one, but it is a real LEGO part on the lists under its own number."""
    from brickkit.bom.bom import write_parts_csv
    cat = engine.catalog
    assert cat.is_approximate("10165c01") and engine.lib.is_custom("10165c01")
    assert not cat.is_hardware("10165c01") and cat.in_bom("10165c01")
    mesh = engine.geom.mesh("10165c01.dat")
    assert mesh.certified and mesh.volume_centroid()[0] > 0      # closed, outward
    lo, hi = mesh.bbox
    assert 40 < hi[0] - lo[0] < 50 and 40 < hi[1] - lo[1] < 55  # ~1.8 cm, like the real one
    assert 47 in set(int(c) for c in mesh.colors)               # its Trans-Clear glass
    m, _ = figure(engine, hair=None, hat=("10165c01", "Pearl Gold"),
                  accessory=dict(part="30088", color="Black", hand="right", bar=1),
                  pose={"arm_r": 45})
    results = {r.name: r for r in run_checks(engine.context(m))}
    assert all(r.status in ("pass", "warn") for r in results.values()), \
        {n: r.items[:3] for n, r in results.items() if r.status == "fail"}
    re = results["real_elements"]
    assert re.stats["approximate"] == 1
    assert any(i["part"] == "10165c01" and i["severity"] == "info" for i in re.items)
    assert any(i["part"] == "10165c01" and i["severity"] == "warn" for i in re.items)  # 1 set
    lines = build_bom(m.flatten(), cat)
    helmet = next(l for l in lines if l.rb_part == "10165c01")
    assert helmet.bl_part == "10165c01" and helmet.approximate and helmet.element_id
    write_bricklink_xml(lines, tmp_path / "w.xml")
    assert "<ITEMID>10165c01</ITEMID>" in (tmp_path / "w.xml").read_text()
    write_parts_csv(lines, tmp_path / "p.csv")
    assert "approximate 3D model" in (tmp_path / "p.csv").read_text()
    text = write_mpd(m, tmp_path / "d.mpd", engine.lib).read_text()
    assert "0 FILE 10165c01.dat" in text                       # other programs can show it


def test_bricklink_numbers_added_by_hand(engine):
    """A print LDraw has no model of gets its BrickLink number from
    data/minifig_bricklink.json."""
    t = engine.catalog.figs.component("torso", "973c23h12pr2119")
    assert t.stand_in and t.bl_part == "973pb1240c01"
