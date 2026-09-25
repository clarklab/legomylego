import numpy as np

from brickkit.ldraw.matrix import translate
from brickkit.model.builder import Model


def make(engine):
    m = Model("T", "t", {"body": "White"}, engine.catalog)
    pillar = m.submodel("pillar")
    pillar.place("3003", "body")
    pillar.step()
    pillar.place("3003", "body", (0, -24, 0))
    m.main.place("3001", "Red")
    m.main.step("pillars")
    m.main.use(pillar, (-20, -24, 0), tag="left")
    m.main.use(pillar, (20, -24, 0), tag="right")
    return m


def test_flatten_world_positions(engine):
    placed = make(engine).flatten()
    assert [p.part for p in placed] == ["3001.dat"] + ["3003.dat"] * 4
    assert np.allclose(placed[2].M[:3, 3], [-20, -48, 0])
    assert placed[1].tags == ("left",)
    assert placed[0].color.name == "Red" and placed[1].color.name == "White"


def test_instruction_order_builds_subassembly_first(engine):
    assert make(engine).instruction_order() == [("t", 0), ("pillar", 0), ("pillar", 1), ("t", 1)]


def test_pose_moves_group(engine):
    m = make(engine)
    m.moving_group("lift", "left")
    placed = m.flatten(pose={"lift": translate(0, -100, 0)})
    assert np.allclose(placed[1].M[:3, 3], [-20, -124, 0])
    assert np.allclose(placed[3].M[:3, 3], [20, -24, 0])
