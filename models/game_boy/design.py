"""Game Boy: Phoenix_bricks' Micro Game Boy (Rebrickable MOC-238888), built from the designer's
plans, every piece where they put it. 25 pieces, 4.5 cm tall.

It stands as you see it, and its lower half is built studs down: the rounded corner at the
bottom right is a curved brick upside down, and everything above it presses on with its studs
into the piece below. Two pairs of brackets on their sides turn the studs forward for the
screen and then up again for the top.

Frame: LDU (stud 20, plate 8, brick 24), -Y up, the front faces -Z; the table is y = 0.
Columns across the front: x = -20 (the D-pad's), 0, 20 (the rounded corner's). Colours are
palette roles from model.toml."""
import numpy as np

from brickkit.ldraw.matrix import rot

COLS = (-20, 0, 20)
DOWN = rot(z=180)                 # a piece upside down: its studs point at the table
BODY_TOP = 56                     # the grey body's flat top, where the screen's brackets sit
SCREEN = 70                       # the height of the studs the screen's tiles go on
TOP = 84                          # the brackets' studs that point up again


def axes(ex, ey):
    """A rotation given by where a part's own X and Y axes point (its Z follows)."""
    ex, ey = np.asarray(ex, float), np.asarray(ey, float)
    return np.column_stack([ex, ey, np.cross(ex, ey)])


CORNER = axes((0, 0, -1), (0, -1, 0))     # the curved brick: upside down, its round end at x = 20
FLOOR = axes((1, 0, 0), (0, 0, 1))        # a bracket lying on its side studs, its plate standing
#                                           at the back with studs forward (and a tile on a
#                                           forward stud, face to the front)
ROOF = axes((-1, 0, 0), (0, 0, 1))        # a bracket hung on forward studs: plate studs forward,
#                                           its side studs up
UPRIGHT = axes((0, -1, 0), (0, 0, 1))     # a 1 x 2 tile standing on a forward stud
ALONG = axes((0, 0, 1), (0, 1, 0))        # an axle running front to back


def y(h) -> float:
    """Height above the table -> the frame's y."""
    return -float(h)


def build_dpad(model):
    """The D-pad: the end of a black axle, through two axle-hole bricks one behind the other."""
    pad = model.submodel("dpad", "D-pad")
    pad.step("The D-pad: push the black axle through a brick with a cross hole, held upside "
             "down, until a little of it shows at the front")
    pad.place("73230", "body", (0, y(24), 0), DOWN, tag="dpad_brick")
    pad.place("32062", "dpad", (0, y(34), 4), ALONG, tag="dpad", insert=(0, 0, 1))
    pad.step("Push a second cross-hole brick, right way up, onto the axle's long end, and put "
             "the little slope on it, high edge to the front")
    pad.place("73230", "body", (0, y(44), 20), tag="back", insert=(0, 0, 1))
    pad.place("54200", "body", (0, y(44), 20), rot(y=180), tag="back")
    return pad


def build(model):
    m = model.main
    pad = build_dpad(model)

    m.step("Everything in the grey body goes on upside down. Start with the curved brick, round "
           "end down, and press the 1 x 2 tile onto its stud from below. Two 1 x 1 plates go "
           "on the tile's free end")
    m.place("6091", "body", (0, 0, 0), CORNER, tag="corner")
    m.place("3069b", "body", (-10, 0, 0), DOWN, tag="foot", insert=(0, 1, 0))
    for h in (8, 16):
        m.place("3024", "body", (COLS[0], y(h), 0), DOWN)

    m.step("Two bricks with a stud on the side, studs to the front: one on the ledge, one on "
           "the curved brick. A 1 x 1 plate tops the lower one")
    m.place("87087", "body", (COLS[1], y(16), 0), DOWN, tag="b_side")
    m.place("87087", "body", (COLS[2], y(32), 0), DOWN, tag="a_side")
    m.place("3024", "body", (COLS[1], y(40), 0), DOWN)

    m.step("Press the D-pad onto the two plates, its second brick hanging behind, and lock it "
           "in with the 1 x 2 plate across the top")
    m.use(pad, (COLS[0], 0, 0), tag="pad_unit")
    m.place("3023", "body", (-10, y(48), 0), DOWN, tag="lock")

    m.step("The screen's frame. Lay the two brackets with the upright end on their side studs, "
           "so their plates stand along the back with studs to the front: the 1 x 1 over the "
           "D-pad, the 1 x 2 beside it")
    m.place("36840", "frame", (COLS[0], y(SCREEN), 2), FLOOR, tag="frame")
    m.place("99780", "frame", (10, y(SCREEN), 2), FLOOR, tag="frame")

    m.step("Press the other two brackets onto those studs, plates to the front and side studs "
           "up: the 1 x 2 on the left this time, so the joins do not line up")
    m.place("99781", "frame", (-10, y(SCREEN), -6), ROOF, tag="frame", insert=(0, 0, -1))
    m.place("36841", "frame", (COLS[2], y(SCREEN), -6), ROOF, tag="frame", insert=(0, 0, -1))

    m.step("Two 1 x 3 plates on the studs on top, then the top edge: a 1 x 1 plate on the left "
           "and a 1 x 2 tile")
    for h in (TOP + 8, TOP + 16):
        m.place("3623", "frame", (0, y(h), 4), tag="frame")
    m.place("3024", "body", (COLS[0], y(TOP + 24), 4), tag="switch")
    m.place("3069b", "body", (10, y(TOP + 24), 4), tag="top")

    m.step("The screen: three clear 1 x 2 tiles standing side by side, each on one of the "
           "studs facing forward")
    for x in COLS:
        m.place("3069b", "glass", (x, y(SCREEN + 10), -14), UPRIGHT, tag="screen",
                insert=(0, 0, -1))

    m.step("The A and B buttons: a round tile on each stud on the front")
    m.place("98138", "button", (COLS[1], y(26), -18), FLOOR, tag="buttons", insert=(0, 0, -1))
    m.place("98138", "button", (COLS[2], y(42), -18), FLOOR, tag="buttons", insert=(0, 0, -1))
