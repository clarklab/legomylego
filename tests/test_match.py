from brickkit.ldraw.matrix import rot, transform
from brickkit.snaps.match import find_connections


def world(engine, placements):
    return [[c.transformed(M) for c in engine.shadow.connectors(p)] for p, M in placements]


def test_stacked_bricks_have_8_stud_connections(engine):
    conns = find_connections(world(engine, [("3001.dat", transform()),
                                            ("3001.dat", transform((0, -24, 0)))]))
    assert len(conns) == 8 and all(c.kind == "stud" for c in conns)


def test_offset_by_one_stud_has_6(engine):
    conns = find_connections(world(engine, [("3001.dat", transform()),
                                            ("3001.dat", transform((20, -24, 0)))]))
    assert len(conns) == 6


def test_half_stud_offset_does_not_connect(engine):
    conns = find_connections(world(engine, [("3001.dat", transform()),
                                            ("3001.dat", transform((10, -24, 0)))]))
    assert conns == []


def test_pin_seated_in_beam_hole(engine):
    conns = find_connections(world(engine, [("32523.dat", transform()),
                                            ("2780.dat", transform((0, -10, 0), rot(z=90)))]))
    assert any(c.kind == "pin" for c in conns)
