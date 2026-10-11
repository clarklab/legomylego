"""BMO, the little living game console from Adventure Time: our own design, as small as it
goes with the face and the buttons still there. 44 pieces, 3 cm wide, 4.8 cm tall.

The body is a core three studs wide and two deep whose bricks have studs on their sides. Two
panels stand on the studs that face forward, each a 2 x 3 plate with its tiles on: the screen
with the face, and the buttons below it. Tiles on the studs that face sideways are the body's
sides, one plate thick, so the screen has a thin teal frame; they come a little further
forward than the panels, and three tiles on top close the box. Each arm sits on one stud in
the middle of a side tile, so it swings.

Frame: LDU (stud 20, plate 8, brick 24), -Y up, the face looks to -Z; the table is y = 0.
Across the core: x = -20, 0, 20; front row z = 0, back row z = 20. Colours are palette roles
from model.toml."""
import numpy as np

from brickkit.ldraw.matrix import rot

FRONT = rot(x=90)                 # a plate or tile standing on a stud that faces the front
COLS = (-20, 0, 20)
SIDES = (1, -1)                   # his left (our right, x > 0), then his right
B = 32                            # the body's underside: a foot plate and a round brick of leg
PAD = B + 20                      # the middle of the buttons panel (it stands on studs at B + 30)
SCREEN = B + 60                   # the middle of the screen (on studs at B + 70)
TOP = B + 80                      # the top of the core: the lid goes on here
FACE = -18                        # z of the front of a standing panel plate: tiles go on here
SKIN = 38                         # |x| of the outside of the side tiles
EYE = "98138p2e"                  # a white round tile printed with a black dot, off its middle:
#                                   each eye is turned so its dot is towards the other
SMILE, SMILE_TURN = "98138p2n", 180   # ... and one with a black curved line, turned to smile


def y(h) -> float:
    """Height above the table -> the frame's y."""
    return -float(h)


def axes(ex, ey):
    """A rotation given by where a part's own X and Y axes point (its Z follows)."""
    ex, ey = np.asarray(ex, float), np.asarray(ey, float)
    return np.column_stack([ex, ey, np.cross(ex, ey)])


def side(s):
    """A tile on a stud that faces sideways (s = 1: his left), its long way up."""
    return axes((0, -1, 0), (-s, 0, 0))


def build_screen(model):
    """The face, lying flat as it is built: its top row is the far one (z = 10)."""
    face = model.submodel("screen", "Screen")
    face.step("The screen: on a light green 2 x 3 plate, a round tile with a black dot on "
              "each end of one long row for the eyes, each dot towards the other, and a light "
              "green tile between them")
    face.place("3021", "screen", (0, 0, 0), tag="screen")
    for x in (-20, 20):
        face.place(EYE, "print", (x, -8, 10), rot(y=180 if x > 0 else 0), tag="eyes")
    face.place("3070b", "screen", (0, -8, 10), tag="screen")
    face.step("The other row: the round tile with a curved line in the middle, turned so it "
              "smiles, and a light green tile either side")
    face.place(SMILE, "print", (0, -8, -10), rot(y=SMILE_TURN), tag="mouth")
    for x in (-20, 20):
        face.place("3070b", "screen", (x, -8, -10), tag="screen")
    return face


def build_pad(model):
    """The buttons, lying flat as they are built: the top row is the far one (z = 10)."""
    pad = model.submodel("pad", "Buttons")
    pad.step("The buttons: on a teal 2 x 3 plate, the grille tile along one long row "
             "for the slot, and the small green button beside it")
    pad.place("3021", "body", (0, 0, 0), tag="pad")
    pad.place("2412b", "slot", (-10, -8, 10), tag="slot")
    pad.place("6141", "green", (20, -8, 10), tag="buttons")
    pad.step("The other row: the yellow D-pad (a 1 x 1 plate) under the slot's end, the blue "
             "triangle (a little slope, its high edge to the slot) and the big red button")
    pad.place("3024", "dpad", (-20, -8, -10), tag="dpad")
    pad.place("54200", "triangle", (0, 0, -10), tag="buttons")
    pad.place("98138", "red", (20, -8, -10), tag="buttons")
    return pad


def front_row(m, top, tag):
    """The core's front row: three 1 x 1 bricks with studs forward; the two at the ends have a
    second stud, out to the side."""
    m.place("26604", "core", (-20, y(top), 0), rot(y=90), tag=tag)
    m.place("87087", "body", (0, y(top), 0), tag=tag)
    m.place("26604", "core", (20, y(top), 0), tag=tag)


def back_row(m, top, tag):
    """The core's back row: a stud out to the side at each end, a plain brick between."""
    m.place("87087", "body", (-20, y(top), 20), rot(y=90), tag=tag)
    m.place("3005", "body", (0, y(top), 20), tag=tag)
    m.place("87087", "body", (20, y(top), 20), rot(y=-90), tag=tag)


def build(model):
    m = model.main
    face = build_screen(model)
    pad = build_pad(model)

    m.step("Two feet: a 1 x 3 plate each, front to back, with a round brick on the middle "
           "stud for a leg. Join the legs with a 2 x 3 plate, its front row on them")
    for s in SIDES:
        m.place("3623", "body", (20 * s, y(8), 0), rot(y=90), tag="feet")
    for s in SIDES:
        m.place("3062b", "body", (20 * s, y(B), 0), tag="legs")
    m.place("3021", "body", (0, y(B + 8), 10), tag="core")

    m.step("A second 2 x 3 plate, then the front row of the core: a grey brick with studs on "
           "two sides at each end, studs forward and out, and a teal one between them, stud "
           "forward")
    m.place("3021", "body", (0, y(B + 16), 10), tag="core")
    front_row(m, B + 40, "core_low")
    m.step("The back row: a brick with a stud on its side at each end, studs out, and a plain "
           "one between. Two more 2 x 3 plates on top")
    back_row(m, B + 40, "core_low")
    for h in (48, 56):
        m.place("3021", "body", (0, y(B + h), 10), tag="core")

    m.step("The same six bricks again: the front row with studs forward and out, the back "
           "row with studs out")
    front_row(m, TOP, "core_high")
    back_row(m, TOP, "core_high")

    m.step("The lid: three 1 x 3 tiles side by side, front to back, each sticking out a stud "
           "over the front")
    for x in COLS:
        m.place("63864", "body", (x, y(TOP + 8), 0), rot(y=90), tag="lid")

    m.step("Press the buttons onto the lower row of studs on the front, and the screen onto "
           "the upper row, under the lid, eyes up")
    m.use(pad, (0, y(PAD), FACE), FRONT, tag="pad", insert=(0, 0, -1))
    m.use(face, (0, y(SCREEN), FACE), FRONT, tag="face", insert=(0, 0, -1))

    for s in SIDES:
        m.step(("His left side" if s > 0 else "His right side, the same") + ": the tile with "
               "one stud on the lower front studs, the plain 2 x 2 tile above it, and the "
               "1 x 4 tile up the back. Then an arm on the one stud, thick end down")
        m.place("87580", "body", (SKIN * s, y(PAD), -10), side(s), tag="sides", insert=(s, 0, 0))
        m.place("3068b", "body", (SKIN * s, y(SCREEN), -10), side(s), tag="sides", insert=(s, 0, 0))
        m.place("2431", "body", (SKIN * s, y(B + 40), 20), side(s), tag="sides", insert=(s, 0, 0))
        m.place("11477", "body", (SKIN * s, y(PAD - 10), -10), axes((0, 0, -s), (-s, 0, 0)),
                tag="arms", insert=(s, 0, 0))
