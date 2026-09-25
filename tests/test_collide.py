import pytest

from brickkit.ldraw.matrix import rot, transform

I = transform()
CASES = [
    ("stacked", "3001.dat", I, "3001.dat", transform((0, -24, 0)), False),
    ("stacked offset one stud", "3001.dat", I, "3001.dat", transform((20, -24, 0)), False),
    ("overlap by a plate", "3001.dat", I, "3001.dat", transform((0, -16, 0)), True),
    ("side by side touching", "3001.dat", I, "3001.dat", transform((80, 0, 0)), False),
    ("side by side 1 LDU overlap", "3001.dat", I, "3001.dat", transform((79, 0, 0)), True),
    ("plate on brick", "3001.dat", I, "3024.dat", transform((10, -8, 10)), False),
    ("pin seated", "32523.dat", I, "2780.dat", transform((0, -10, 0), rot(z=90)), False),
    ("pin collar inside hole", "32523.dat", I, "2780.dat", transform((0, 0, 0), rot(z=90)), True),
]


@pytest.mark.parametrize("label,a,Ma,b,Mb,expected", CASES, ids=[c[0] for c in CASES])
def test_pair_collisions(engine, label, a, Ma, b, Mb, expected):
    assert engine.collide.collide_pair(a, Ma, b, Mb) is expected


def test_pairs_and_hits(engine):
    items = [("3001.dat", I), ("3001.dat", transform((0, -24, 0))),
             ("3001.dat", transform((0, -40, 0)))]
    assert engine.collide.pairs(items) == [(1, 2)]
    assert engine.collide.hits("3001.dat", transform((0, -12, 0)), items[:1])
    assert not engine.collide.hits("3001.dat", transform((0, -24, 0)), items[:1])


def test_mass_of_2x4_brick(engine):
    from brickkit.geometry.mass import part_mass
    g, cen, approx = part_mass(engine.geom.mesh("3001.dat"), is_trans=False)
    assert 2.0 < g < 3.2 and not approx
