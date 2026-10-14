"""Guardian: our own model of the six-legged machine from The Legend of Zelda, worked out from
two pictures of it (reference/, local). NOTES.md says what each part of it is meant to be.

Frame: LDU (stud 20, plate 8, brick 24), -Y up, the front faces -Z. The table is y = 0 and
the body's middle is over x = z = 0. Heights below are written h (above the table): y = -h.
A plate's or brick's origin is its top; a slope's is its underside. Colours are palette roles
from model.toml.

It is three things: a round body (two 8 x 8 rims with the leg sockets between them, a dome
on top), a head on a narrow neck, and six legs. A leg is a chain of small ball joints, so it
can be posed; here all six have the same arch and differ only in where they point."""
import math

import numpy as np

from brickkit.ldraw.matrix import rot

EX, EY, EZ = np.eye(3)
UP = -EY
FRONT = rot(x=90)                 # a plate's or tile's studs towards the front (-Z)

# The legs ------------------------------------------------------------------------------------
LINK = 60.0                       # ball to socket along a 14419
ARCH = (18.0, 40.0, -4.7, -52.0, -80.0)  # each link's pitch above the level, from the body outwards
FOOT = -88.0                      # the foot's: straight down, on its claw
# where each leg's socket plate is on the body (x, z) and the way its socket faces. The round
# rim has studs for a plate there in six places only: the middle of each side, and two at the
# front and two at the back, 60 degrees round. Each leg points straight out from the middle
LEGS = (("front_right", (40, -50), (0, -1)), ("front_left", (-40, -50), (0, -1)),
        ("right", (70, 0), (1, 0)), ("left", (-70, 0), (-1, 0)),
        ("back_right", (40, 50), (0, 1)), ("back_left", (-40, 50), (0, 1)))
# the walk on the spot (model.pose): the legs in step order round the body, every other one in
# the same three; when each three lifts (t, of 0..1), how long a lift takes, how far a leg
# lifts and how far it swings forward and back as it does (degrees, in its socket)
STEP_ORDER = ("front_right", "front_left", "left", "back_left", "back_right", "right")
STEPS = ((0.04, 0.50), (0.27, 0.73))
STEP = 0.23
LIFT, SWING, INWARD = 15.0, 9.0, 12.0
SOCKET_H = 124.0                  # the sockets' height: the body stands on four round bricks, and
#                                   the third link's pitch was found so that the six claws rest on the table

# The body, by height --------------------------------------------------------------------------
RING = SOCKET_H + 4               # top of the socket plates, in the band between the two rims
RIM = RING + 16                   # top of the upper rim: the dome and the skirt stand on it
DOME = RIM + 48                   # top of the dome: its four studs
NECK = DOME + 8 + 8 + 24          # top of the neck: a collar, a pink ring, a round brick
EYE = NECK + 8 + 10               # the head's four side holes


def orient(ex, ey) -> np.ndarray:
    """A rotation given by where a part's own X and Y axes point (its Z follows)."""
    ex, ey = np.asarray(ex, float), np.asarray(ey, float)
    return np.column_stack([ex, ey, np.cross(ex, ey)])


def about(axis, degrees) -> np.ndarray:
    """A rotation of `degrees` about `axis` (right-handed)."""
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    r = math.radians(degrees)
    return np.eye(3) + math.sin(r) * K + (1 - math.cos(r)) * (K @ K)


def facing(dx, dz) -> np.ndarray:
    """Turned about the upright so that the part's own -Z faces (dx, 0, dz)."""
    return orient((-dz, 0, dx), EY)


def build_leg(model):
    """A leg in its own frame: the ball that goes in the body's socket is the origin, the leg
    reaches out along +X and arches up (-Y) and over. Each link's studs are on the outside of
    the arch, under a black plate and a white plate of armour; the foot ends in a claw."""
    leg = model.submodel("leg", "Leg")
    joint = np.zeros(3)
    words = ("A leg: the first link, a plate with a ball at one end and a socket at the other. On "
             "it a black 1 x 2 plate, and on that a white curved slope, its thick end at the "
             "ball. Make six legs",
             "Snap the second link's ball into the first one's socket, bent up, and cover it "
             "the same way",
             "The third link, level: the top of the arch",
             "The fourth link, bent down",
             "The fifth link, bent down further")
    for pitch, text in zip(ARCH, words):
        a = math.radians(pitch)
        d = np.array([math.cos(a), -math.sin(a), 0.0])           # the way the link points
        n = np.array([-math.sin(a), -math.cos(a), 0.0])          # the outside of the arch
        R = orient(d, -n)
        at = joint - R @ np.array([-30.0, 4.0, 0.0])
        leg.step(text)
        leg.place("14419", "joint", tuple(at), R, tag="links", insert=tuple(d))
        leg.place("3023", "rim", tuple(at + R @ np.array([0.0, -8.0, 0.0])), R, tag="links")
        leg.place("11477", "armour", tuple(at + R @ np.array([0.0, -8.0, 0.0])),
                  orient(np.cross(-n, -d), -n), tag="armour")
        joint = at + R @ np.array([30.0, 4.0, 0.0])
    a = math.radians(FOOT)
    d = np.array([math.cos(a), -math.sin(a), 0.0])
    n = np.array([-math.sin(a), -math.cos(a), 0.0])
    R = orient(-d, -n)
    at = joint - R @ np.array([30.0, 4.0, 0.0])
    leg.step("The foot: a plate with a ball at one end only, pointing down. On its far stud a "
             "plate with a tooth, the tooth past the end: the claw. A cheese slope behind it")
    leg.place("22890", "joint", tuple(at), R, tag="foot", insert=tuple(d))
    leg.place("49668", "armour", tuple(at + R @ np.array([-10.0, -8.0, 0.0])),
              orient(np.cross(-n, -d), -n), tag="claw")
    leg.place("54200", "armour", tuple(at + R @ np.array([10.0, 0.0, 0.0])),
              orient(np.cross(-n, -d), -n), tag="armour")
    return leg


def build_head(model):
    """The head in its own frame: the underside of its base plate is y = 0, the eye faces -Z."""
    head = model.submodel("head", "Head")

    def y(h):
        return -float(h)

    head.step("The head: a round 4 x 4 plate, and on it the round brick with a hole in each side")
    head.place("60474", "stone", (0, y(8), 0), tag="head")
    head.place("6222", "stone", (0, y(32), 0), tag="head")
    head.step("Push a half pin into each of the four holes, stud out")
    for name, (dx, dz) in (("front", (0, -1)), ("right", (1, 0)), ("back", (0, 1)), ("left", (-1, 0))):
        head.place("4274", "pin", (40 * dx, y(22), 40 * dz), orient((dx, 0, dz), EY),
                   tag="pins", insert=(dx, 0, dz))
    head.step("The eye, on the front pin: a pink round plate with one stud, and the clear blue "
              "round tile on it")
    head.place("18674", "eye_ring", (0, y(22), -48), FRONT, tag="eye")
    head.place("98138", "eye", (0, y(22), -56), FRONT, tag="eye")
    head.step("A clear pink round tile on each of the other three pins")
    for dx, dz in ((1, 0), (0, 1), (-1, 0)):
        head.place("98138", "glow_clear", (48 * dx, y(22), 48 * dz),
                   orient((-dz, 0, dx), (-dx, 0, -dz)), tag="ports")
    head.step("A tan round plate, and the plain round brick: the top of the head")
    head.place("60474", "sand", (0, y(40), 0), tag="head")
    head.place("87081", "stone", (0, y(64), 0), tag="head")
    head.step("A round plate on top. In its middle a round plate with one stud and a cone: the "
              "spike")
    head.place("60474", "stone", (0, y(72), 0), tag="head")
    head.place("18674", "stone", (0, y(80), 0), tag="crown")
    head.place("59900", "stone", (0, y(104), 0), tag="crown")
    head.step("The two horns: a brick with a stud on its side at each side of the top, stud to "
              "the front")
    for side in (-1, 1):
        head.place("87087", "stone", (30 * side, y(96), -10), facing(0, -1), tag="horns")
    head.step("A pink round tile on each of those studs, and a pink cheese slope on top of each "
              "brick, sloping outwards")
    for side in (-1, 1):
        head.place("98138", "glow", (30 * side, y(86), -28), FRONT, tag="horns")
        head.place("54200", "glow", (30 * side, y(96), -10), facing(side, 0), tag="horns")
    return head


def build(model):
    m = model.main
    leg = build_leg(model)
    head = build_head(model)

    def y(h):
        return -float(h)

    # A socket, in its own frame: the socket plate's top is y = 0, its socket faces -Z. The plate
    # above and the one below keep the two rims a plate clear of the socket's cup
    socket = model.submodel("socket", "Socket")
    socket.step("A socket: a black 1 x 2 plate, the plate with a socket on its side, and a black "
                "1 x 2 plate on top. Make six")
    socket.place("3023", "rim", (0, 8, 0), tag="sockets")
    socket.place("14704", "joint", (0, 0, 0), tag="sockets")
    socket.place("3023", "rim", (0, -8, 0), tag="sockets")

    # The body ----------------------------------------------------------------------------
    body = model.submodel("body", "Body")
    body.step("The body starts with a black round 8 x 8 plate. Under its middle goes a pink "
              "round 4 x 4 plate: the glow underneath, and where the stand goes")
    body.place("74611", "rim", (0, y(RING - 16), 0), tag="rim")
    body.place("60474", "glow", (0, y(RING - 24), 0), tag="belly")
    body.step("A black round 4 x 4 brick in the middle: the core")
    body.place("87081", "rim", (0, y(RIM - 8), 0), tag="core")
    for k, (name, (x, z), (dx, dz)) in enumerate(LEGS):
        if k % 2 == 0:
            body.step(("Two sockets at the front of the rim, sockets to the front",
                       "One in the middle of each side, socket out",
                       "Two at the back, sockets to the back")[k // 2])
        body.use(socket, (x, y(RING), z), facing(dx, dz), tag="sockets")
    body.step("Pink round 1 x 1 bricks on the free studs round the edge: the lights. Two at the "
              "front and two at the back")
    for x, z in ((10, -70), (-10, -70), (10, 70), (-10, 70)):
        body.place("3062b", "glow", (x, y(RIM - 8), z), tag="lights")
    body.step("And two each side, either side of the middle socket")
    for x, z in ((50, -30), (50, 30), (-50, -30), (-50, 30)):
        body.place("3062b", "glow", (x, y(RIM - 8), z), tag="lights")
    body.step("The second black round 8 x 8 plate on top of them all")
    body.place("74611", "rim", (0, y(RIM), 0), tag="rim")
    body.step("The dome: four quarter domes, their studs together in the middle")
    for turn in (0, 90, 180, 270):
        R = rot(y=turn)
        body.place("88293", "stone", tuple(R @ np.array([10.0, 0.0, -10.0]) + (0, y(DOME), 0)), R,
                   tag="dome")
    body.step("Round the dome, on the rim: a tan 1 x 2 slope in the middle of each side, "
              "sloping outwards")
    for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        body.place("85984", "sand", (70 * dx, y(RIM), 70 * dz), orient((-dz, 0, dx), EY), tag="skirt")
    body.step("A pink round tile on each of the four corner studs between them")
    for sx in (1, -1):
        for sz in (1, -1):
            body.place("98138", "glow", (50 * sx, y(RIM + 8), 50 * sz), tag="lights")
    body.step("On the dome's four studs a dark tan round 4 x 4 plate, with four tan quarter-ring "
              "tiles round its edge: the ring on top of the dome")
    body.place("60474", "sand_dark", (0, y(DOME + 8), 0), tag="collar")
    for turn in (0, 90, 180, 270):
        R = rot(y=turn)
        body.place("27925", "sand", tuple(R @ np.array([10.0, 0.0, -10.0]) + (0, y(DOME + 16), 0)), R,
                   tag="collar")
    body.step("The neck, in the middle of the ring: a pink round 2 x 2 plate and a round 2 x 2 "
              "brick")
    body.place("4032a", "eye_ring", (0, y(DOME + 16), 0), tag="neck")
    body.place("3941", "stone", (0, y(NECK), 0), tag="neck")

    # The figure --------------------------------------------------------------------------
    m.step("The stand: four black round 2 x 2 bricks, stacked. It carries the body, so the legs "
           "only have to hold their pose")
    for k in range(4):
        m.place("3941", "rim", (0, y(24 * (k + 1)), 0), tag="stand")
    m.step("Press the body onto the stand, by the middle of the pink plate underneath")
    m.use(body, (0, 0, 0), tag="body")
    words = ("Snap the first leg's ball into a front socket, the leg pointing straight out "
             "from the middle of the body", "The other front leg", "A leg in the middle of each "
             "side: the right one", "And the left one", "A back leg", "The sixth leg. Bend the "
             "legs until all six claws rest on the table")
    for k, (name, (x, z), (dx, dz)) in enumerate(LEGS):
        m.step(words[k])
        socket = np.array([x + 20 * dx, y(SOCKET_H), z + 20 * dz], float)
        out = socket * (1.0, 0.0, 1.0) / math.hypot(socket[0], socket[2])     # straight out
        # (the ball goes in along the socket's own axis, whichever way the leg then points)
        m.use(leg, tuple(socket), orient(out, EY), tag=name, insert=(dx, 0, dz))
    m.step("Press the head onto the neck, the eye to the front")
    m.use(head, (0, y(NECK), 0), tag="head")

    # How it moves: each leg turns in its socket, about its ball. The pose is a walk on the
    # spot, t from 0 to 1: the legs lift in threes (front right, left, back right; then the
    # other three), twice each, every leg down again where it started. A corner leg already
    # stands as far out of line with its socket as the cup allows (the socket faces front or
    # back, the leg points out from the middle), so it can only lift while it swings back
    # into line: it steps in towards the front or the back. A side leg swings to and fro
    hips, into_line = {}, {}
    for name, (x, z), (dx, dz) in LEGS:
        model.moving_group(name, name)
        hip = np.array([x + 20 * dx, y(SOCKET_H), z + 20 * dz], float)
        out = hip * (1.0, 0.0, 1.0) / math.hypot(hip[0], hip[2])               # the way the leg points
        hips[name] = hip
        into_line[name] = float(np.sign(np.round(np.cross(out, (dx, 0.0, dz)) @ -EY, 6)))

    def pose(t: float) -> dict:
        res = {}
        for k, name in enumerate(STEP_ORDER):
            hip = hips[name]
            out = hip * (1.0, 0.0, 1.0) / math.hypot(hip[0], hip[2])
            us = [u for u in ((t - t0) / STEP for t0 in STEPS[k % 2]) if 0.0 < u < 1.0]
            lift = sum(math.sin(math.pi * u) ** 2 for u in us)
            sway = sum(math.sin(2 * math.pi * u) for u in us) * lift
            swing = into_line[name] * INWARD * lift if into_line[name] else SWING * sway
            R = about(-EY, swing) @ about(np.cross(out, -EY), LIFT * lift)
            M = np.eye(4)
            M[:3, :3] = R
            M[:3, 3] = hip - R @ hip
            res[name] = M
        return res
    model.pose = pose
