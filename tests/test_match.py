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


# ball joints: LDCad describes them as SNAP_GEN [bounding=sph R] [placement=free]; a ball turns
# in its socket, so the pair must stay connected whatever the ball's orientation
def _kinds(engine, placements):
    return [c.kind for c in find_connections(world(engine, placements))]


def test_technic_ball_connects_in_socket_at_any_angle(engine):
    for R in (None, rot(x=35), rot(z=-60), rot(x=20, y=45, z=10)):
        kinds = _kinds(engine, [("92013.dat", transform()),
                                ("32474.dat", transform((40, 10, 0), R))])
        assert "ball" in kinds, R


def test_towball_connects_in_socket_at_any_angle(engine):
    # both balls sit at (30, 4, 0) in their parts: turn the ball plate about its ball
    for R in (rot(y=180), rot(y=180) @ rot(z=30), rot(y=150) @ rot(x=-40)):
        M = transform((30, 4, 0), R) @ transform((-30, -4, 0))
        assert "ball" in _kinds(engine, [("14418.dat", transform()), ("22890.dat", M)])


def test_ball_off_centre_or_wrong_size_does_not_connect(engine):
    # 2 LDU away from the socket centre
    assert "ball" not in _kinds(engine, [("92013.dat", transform()),
                                         ("32474.dat", transform((42, 10, 0)))])
    # a 5.9 mm towball in a Technic ball socket: different size
    assert "ball" not in _kinds(engine, [("92013.dat", transform()),
                                         ("22890.dat", transform((10, 6, 0)))])


def test_large_ball_53585_fits_ball_socket_bricks(engine):
    """53585 (Technic Ball Joint with through axle hole) and 67696 (Brick 2 x 2 with wide ball
    socket, the football figures' shoulder joint) get their ball-joint snaps from the overlays
    in brickkit/data/shadow."""
    for socket in ("67696.dat", "92013.dat"):
        for R in (None, rot(x=90), rot(z=40, y=15)):
            assert "ball" in _kinds(engine, [(socket, transform()),
                                             ("53585.dat", transform((40, 10, 0), R))])
