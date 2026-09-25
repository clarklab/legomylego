import numpy as np

from brickkit.checks import run_checks
from brickkit.ldraw.matrix import rot, transform, translate
from brickkit.model.builder import Model
from tests.test_builder import make


def run(engine, model, name):
    return run_checks(engine.context(model), [name])[0]


def test_stable_tower(engine):
    r = run(engine, make(engine), "stability")
    assert r.status == "pass" and r.stats["mass_g"] > 5


def test_overhang_tips_over(engine):
    m = Model("O", "o", {}, engine.catalog)
    m.main.place("3024", "White")                      # 1x1 plate footprint
    for k in range(6):
        m.main.place("3008", "White", (70, -24 - 24 * k, 0))  # 1x8 bricks hanging off one side
    assert run(engine, m, "stability").status == "fail"


def test_mechanism_sweep(engine):
    m = make(engine)
    m.moving_group("left", "left")
    m.pose = lambda t: {"left": translate(40 * t, 0, 0)}   # slides into the right pillar
    r = run(engine, m, "mechanism")
    assert r.status == "fail" and any("collide" in i["problem"] for i in r.items)
    m.pose = lambda t: {"left": translate(0, -60 * t, 0)}  # lifts off the base
    assert any("falls apart" in i["problem"] for i in run(engine, m, "mechanism").items)
    m.pose = lambda t: {"left": np.eye(4)}
    assert run(engine, m, "mechanism").status == "pass"


def test_gear_spacing(engine):
    m = Model("G", "g", {}, engine.catalog)
    m.main.place("3648b", "Light Bluish Gray", (0, 0, 0), rot(x=90), tag="g24")
    m.main.place("3647", "Light Bluish Gray", (40, 0, 0), rot(x=90), tag="g8")
    m.gear_pair("g24", "g8")
    r = run(engine, m, "mechanism")
    assert not [i for i in r.items if "gear" in i["problem"]]
    m2 = Model("G", "g", {}, engine.catalog)
    m2.main.place("3648b", "Light Bluish Gray", (0, 0, 0), rot(x=90), tag="g24")
    m2.main.place("3647", "Light Bluish Gray", (50, 0, 0), rot(x=90), tag="g8")
    m2.gear_pair("g24", "g8")
    assert any("gear" in i["problem"] for i in run(engine, m2, "mechanism").items)


def test_electrics_cable_length(engine):
    m = Model("E", "e", {}, engine.catalog)
    m.main.place("3001", "White", tag="box")
    m.main.place("3001", "White", (0, -24, 0), tag="lamp")
    m.cable("led", "box", "lamp", length=30)
    assert run(engine, m, "electrics").status == "pass"
    m.cables.clear()
    m.cable("led", "box", "lamp", length=20)
    assert run(engine, m, "electrics").status == "fail"


def test_technique_passes_simple_model(engine):
    assert run(engine, make(engine), "technique").status in ("pass", "warn")
