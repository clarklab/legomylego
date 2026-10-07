"""Exact supplemental LDraw moulds and the blind socket in the cake's cherry."""
from collections import Counter
from hashlib import sha256

import pytest

from brickkit.checks import run_checks
from brickkit.io.mpd import read_mpd, write_mpd
from brickkit.model.builder import Model


def test_supplemental_mould_has_verifiable_upstream_source(engine):
    catalog = engine.catalog
    assert catalog.is_supplemental("76959")
    assert not catalog.is_approximate("76959")
    assert not catalog.is_supplemental("3001")
    for name in ("76959.dat", "s/76959s01.dat"):
        source = catalog.supplemental_sources[name]
        assert source["url"] == f"https://library.ldraw.org/library/unofficial/parts/{name}"
        assert sha256(engine.lib.resolve(name).read_bytes()).hexdigest() == source["sha256"]
        assert source["license"] == "CC-BY-4.0"
    assert "6425510" in catalog.element("76959", "Reddish Brown").element_ids
    assert engine.geom.mesh("76959").certified


def test_supplemental_part_is_reported_and_unknown_custom_parts_rejected(engine, monkeypatch):
    model = Model("Mould", "mould", {}, engine.catalog)
    model.main.place("76959", "Reddish Brown")
    result = run_checks(engine.context(model), ["real_elements"])[0]
    assert result.status == "pass" and result.stats["not_real"] == 0
    assert any(item.get("source") == engine.catalog.supplemental_sources["76959.dat"]["url"]
               and item["severity"] == "info" for item in result.items)
    monkeypatch.setattr(engine.catalog, "supplemental_sources", {})
    result = run_checks(engine.context(model), ["real_elements"])[0]
    assert result.status == "fail", "a custom file must not silently become a real approved part"


def test_mpd_embeds_supplemental_part_and_child_once(engine, tmp_path):
    model = Model("Mould", "mould", {}, engine.catalog)
    model.main.place("76959", "Reddish Brown", (-20, 0, 0))
    model.main.place("76959", "Reddish Brown", (20, 0, 0))
    path = write_mpd(model, tmp_path / "mould.mpd", engine.lib)
    text = path.read_text()
    for name in ("76959.dat", "s/76959s01.dat"):
        assert text.count(f"0 FILE {name}\n") == 1
    assert Counter((part, color) for part, color, _ in read_mpd(path)) == Counter(
        (part.part, part.color.ldraw) for part in model.flatten())


def _candle(engine, x=0, y=-8, flame_x=0):
    model = Model("Candle", "candle", {}, engine.catalog)
    model.main.place("3262", "Red")
    model.main.step("Seat the candle in the cherry's blind stud bore")
    model.main.place("37762", "White", (x, y, 0))
    model.main.step("Insert the flame")
    model.main.place("37775", "Trans-Orange", (x + flame_x, y - 27, 0))
    return model


def test_candle_and_flame_fit_cherry_socket(engine):
    results = run_checks(engine.context(_candle(engine)), ["connections", "collisions", "buildability"])
    assert [result.status for result in results] == ["pass"] * 3


@pytest.mark.parametrize("offsets", [{"x": 3}, {"y": -20}, {"flame_x": 3}])
def test_candle_socket_rejects_off_axis_or_withdrawn_parts(engine, offsets):
    result = run_checks(engine.context(_candle(engine, **offsets)), ["connections"])[0]
    assert result.status == "fail"


@pytest.mark.parametrize("offsets", [{"x": 3}, {"y": -3}])
def test_candle_socket_collision_is_not_exempted(engine, offsets):
    result = run_checks(engine.context(_candle(engine, **offsets)), ["collisions"])[0]
    assert result.status == "fail"
    assert any("3262" in item["a"] and "37762" in item["b"] for item in result.items)
