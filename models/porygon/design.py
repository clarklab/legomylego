"""Porygon: a tiny Quick Bricks Porygon, 19 pieces, 4 studs long and 4 across its feet - a pink
head and body, a blue beak, chest, feet and tail, and a round eye on each side of its head.

A design by QSKSw (Rebrickable MOC-31400). It was read from a LEGO Digital Designer file,
whose only steps are the program's automatic guide, so the build order here is our own: from
the base plate up, each piece landing on something. NOTES.md has the parts list step by step,
how the file was read, and the two loose spare pieces in it that are left out.

Frame: LDU (stud 20, plate 8, brick 24), -Y up, the front (the beak) faces -Z. Side to side
the body is two studs wide (x = -10, 10) and the feet stand a stud further out (x = -30, 30).
Front to back there are four rows: the beak (z = -30), the chest and head (z = -10), the back
(z = 10) and the tail (z = 30). The base plate's top is y = 0.
A plate's, brick's or tile's origin is its top; a slope's (54200, 85984) is its bottom, and
as it comes its low edge faces the front."""
import numpy as np

from brickkit.ldraw.matrix import rot

PLATE, BRICK = 8, 24
BODY = (-10, 10)                  # the body's two columns
FEET = (-30, 30)                  # the feet, a stud further out each side
BEAK, CHEST, BACK, TAIL = -30, -10, 10, 30      # the four rows, front to back

BASE = 0                          # the 2 x 4 plate's top
BELLY = BASE - BRICK              # the two bricks' tops
NECK = BELLY - PLATE              # the 2 x 2 plate, and the two 1 x 1 plates behind it
NAPE = NECK - PLATE               # the 1 x 2 plate on those two
HEAD = NECK - BRICK               # the bricks with a stud on the side
CROWN = HEAD - PLATE              # the tile on top
SIDE_STUD = 10                    # a 1 x 1 brick's side stud: 10 below its top

TURNED = rot(y=180)               # a slope with its low edge to the back
STUD_OUT = {-1: rot(y=90), 1: rot(y=-90)}       # an 87087's side stud facing left, right


def orient(ex, ey, ez) -> np.ndarray:
    """3x3 rotation whose columns are where the part's local X, Y and Z axes point."""
    return np.column_stack([ex, ey, ez])


# an eye on a side stud, its top (local -Y) facing out. The print's pupil sits off the middle
# of the tile, towards local -X and -Z, with its glint on the -Z side: both eyes are turned so
# the pupil is up and forward (the glint in front on the right eye, on top on the left)
EYE = {1: orient((0, 1, 0), (-1, 0, 0), (0, 0, 1)),       # the right side (+X)
       -1: orient((0, 0, 1), (1, 0, 0), (0, 1, 0))}       # the left side (-X)


def build(model):
    m = model.main

    m.step("The base: a 2 x 4 plate, its long side across")
    m.place("3020", "trim", (0, BASE, 0))

    m.step("The body: a blue 1 x 2 brick in front, a pink 2 x 2 brick behind, hanging over the back")
    m.place("3004", "trim", (0, BELLY, CHEST))
    m.place("3003", "body", (0, BELLY, 20))                     # rows BACK and TAIL

    m.step("The front of the feet: a small slope on each end, falling forward")
    for x in FEET:
        m.place("54200", "trim", (x, BASE, CHEST), tag="feet")

    m.step("The back of the feet: two more, falling backward")
    for x in FEET:
        m.place("54200", "trim", (x, BASE, BACK), TURNED, tag="feet")

    m.step("A 2 x 2 plate on the blue brick, reaching forward, and two 1 x 1 plates behind it")
    m.place("3022", "trim", (0, NECK, -20))                     # rows BEAK and CHEST
    for x in BODY:
        m.place("3024", "body", (x, NECK, BACK))

    m.step("The tail: a slope on the back studs, its high edge behind")
    m.place("85984", "trim", (0, BELLY, TAIL), tag="tail")

    m.step("The head: two bricks with a stud on the side, studs facing out")
    for s in (-1, 1):
        m.place("87087", "body", (10 * s, HEAD, CHEST), STUD_OUT[s])

    m.step("The beak: a slope in front of the head, falling forward")
    m.place("85984", "trim", (0, NECK, BEAK), tag="beak")

    m.step("Behind the head: a 1 x 2 plate, and a slope falling backward")
    m.place("3023", "body", (0, NAPE, BACK))
    m.place("85984", "body", (0, NAPE, BACK), TURNED)

    m.step("A tile on top of the head")
    m.place("3069b", "body", (0, CROWN, CHEST))

    m.step("The eyes: one on each side")
    for s in (-1, 1):
        m.place("98138p07", "eye", ((20 + PLATE) * s, HEAD + SIDE_STUD, CHEST), EYE[s],
                tag="eye")
