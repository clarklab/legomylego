import numpy as np

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


# finger hinges: LDCad centres a SNAP_FGR's finger sequence on the snap's position unless it
# says [center=false], so a hinge pair engages whichever way round its two halves face
def _about(point, R):
    p = np.asarray(point, float)
    M = np.eye(4)
    M[:3, :3] = R
    M[:3, 3] = p - R @ p
    return M


def _hinges(engine, placements):
    return [c for c in find_connections(world(engine, placements)) if c.kind == "hinge"]


def test_click_hinge_on_end_connects_at_any_angle(engine):
    # 54657 (two fingers) and 44301b (one finger) face each other across the line x = 30,
    # y = 2 (along Z); the joint holds at any angle about that line
    for a in (0, 22.5, 45, 53.13, 90, -60):
        M = _about((30, 2, 0), rot(z=a)) @ transform((60, 0, 0), rot(y=180))
        assert len(_hinges(engine, [("54657.dat", transform()), ("44301b.dat", M)])) == 1, a


def test_side_finger_hinge_connects_either_way_round(engine):
    # 60471 (two fingers on its side) and 44567b (one): the panel half turned to face it
    for a in (0, 54.4, -54.4, 135):
        M = _about((0, 2, -20), rot(x=a)) @ transform((0, 0, -40), rot(y=180))
        assert len(_hinges(engine, [("60471.dat", transform()), ("44567b.dat", M)])) == 1, a


def test_half_sphere_canopy_clicks_onto_one_finger_hinges(engine):
    """50747 (Windscreen 6 x 6 x 3 Canopy Half Sphere with Dual 2 Fingers) locks onto single
    finger click hinges; the overlay in brickkit/data/shadow gives its fingers LDCad's
    locking-hinge group, which the library's own file leaves out."""
    # its two pairs of fingers are on the line y = 0, z = 0 at x = -20 and 20; a 44567b's
    # single finger (at (0, 2, -20) in its own frame) in each pair, at any angle about the line
    for a in (0, 90, -45):
        for x in (-20, 20):
            M = _about((x, 0, 0), rot(x=a)) @ transform((x, -2, 20))
            kinds = [c.kind for c in find_connections(world(engine, [("50747.dat", transform()),
                                                                     ("44567b.dat", M)]))]
            assert kinds == ["hinge"], (a, x, kinds)


def test_hinge_fingers_must_interleave(engine):
    # two single fingers (or two pairs) in the same place would clash: not a hinge
    M = transform((60, 0, 0), rot(y=180))
    assert not _hinges(engine, [("44301b.dat", transform()), ("44301b.dat", M)])
    assert not _hinges(engine, [("54657.dat", transform()), ("54657.dat", M)])


def test_studs_connect_in_compound_angled_frames(engine):
    """In frames made of several 45- or 30-degree turns, the feet of two collinear connectors
    can land exactly on the matcher's bucket boundaries, where float noise must not split the
    pair (a plate crossing another on a panel turned 45 degrees two ways)."""
    import itertools
    for R, off in itertools.product(
            (rot(z=45) @ rot(y=45), rot(x=45) @ rot(y=45), rot(y=30) @ rot(x=60),
             rot(z=45) @ rot(x=30) @ rot(y=45)),
            ((13.7, -5.2, 33.1), (0, 0, 0), (10.5, 2.5, -7.25), (100, -366, -40))):
        W = transform(off, R)
        cross = W @ transform((0, -8, 0), rot(y=90))
        studs = [c for c in find_connections(world(engine, [("3020.dat", W), ("3020.dat", cross)]))
                 if c.kind == "stud"]
        assert len(studs) == 4, (np.round(R, 3).tolist(), off, len(studs))


def test_3x2_wedge_plates_sit_on_studs(engine):
    """43722a/43723a (wedge plate 3 x 2) get their stud holes from brickkit's shadow overlays."""
    for p in ("43722a.dat", "43723a.dat", "43722b.dat", "43723b.dat"):
        conns = find_connections(world(engine, [("3031.dat", transform()),
                                                (p, transform((0, -8, 10)))]))
        assert len([c for c in conns if c.kind == "stud"]) == 4, p
