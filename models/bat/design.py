"""Bat: a tiny Quick Bricks bat, 22 pieces, 10 studs across the wings - angry yellow eyes, two
white fangs, pointed ears and little clip feet.

Built from the plans in reference/ (screen_01..03.png: an instructions app's page overview and
its parts list). NOTES.md has the page-by-page reading and what had to be worked out.

Frame: LDU, -Y up, the front faces -Z. Everything is one stud deep (z = 0). The head is four
studs wide (x = -30, -10, 10, 30); each wing reaches three more. The feet's tops are y = 0.

The plans start from the head's 1 x 2 brick and add to it above and below (the feet last, in
the hand). Here it is built from the feet up, so every piece has something to land on."""
import math

import numpy as np

from brickkit.ldraw.matrix import rot

PLATE, BRICK = 8, 24
SIDE_STUD = 10                    # a 1 x 1 brick's side stud: 10 below its top
EYE_TILT = 30.0                   # degrees the eyes tip in towards the nose: angry

FEET = 0                          # the clip plates' tops
CHIN = FEET - BRICK               # the two inverted slopes
CHEEK = CHIN - PLATE              # the fang plates and the plates beside them
HEAD = CHEEK - BRICK              # the 1 x 2 brick and the bricks with side studs
TOP = HEAD - PLATE                # the wings' tiles and the plate between them
EAR = TOP - BRICK                 # the ears' slopes


def eye(tilt: float) -> np.ndarray:
    """A half-round tile on a front stud: its top faces front, its straight edge up, tipped
    `tilt` degrees (clockwise from the front)."""
    a = math.radians(tilt)
    ex = (math.cos(a), math.sin(a), 0.0)            # along the straight edge
    ez = (math.sin(a), -math.cos(a), 0.0)           # from the round side to the straight edge
    return np.column_stack([ex, (0.0, 0.0, 1.0), ez])


def build(model):
    m = model.main

    m.step("The feet: two clip plates, the clips forward")
    for x in (-10, 10):
        m.place("61252", "body", (x, FEET, 0))

    m.step("The chin: two inverted slopes, tips out")
    m.place("3665b", "body", (-10, CHIN, 0), rot(y=90))
    m.place("3665b", "body", (10, CHIN, 0), rot(y=-90))

    m.step("The fangs, and a plate on each side of them")
    for x in (-10, 10):
        m.place("15070", "fang", (x, CHEEK, 0))          # the tooth hangs down in front
    for x in (-30, 30):
        m.place("3024", "body", (x, CHEEK, 0))

    m.step("The head: a 1 x 2 brick between two bricks with a stud in front")
    m.place("3004", "body", (0, HEAD, 0))
    for x in (-30, 30):
        m.place("87087", "body", (x, HEAD, 0))

    m.step("The wings: a 1 x 4 tile out from each side, an inverted slope pressed up under it")
    for s in (-1, 1):
        m.place("2431", "body", (60 * s, TOP, 0))
        m.place("4287c", "body", (50 * s, HEAD, 0), rot(y=-90 * s), insert=(0, 1, 0))

    m.step("A plate on top of the head")
    m.place("3023", "body", (0, TOP, 0))

    m.step("Angry eyes: half-round tiles on the front studs, tipped in towards the nose")
    for s in (-1, 1):
        m.place("1748", "eye", (30 * s, HEAD + SIDE_STUD, -10 - PLATE), eye(-EYE_TILT * s))

    m.step("The ears: a slope on each side of the top plate, a small slope on its stud")
    for s in (-1, 1):
        m.place("3040b", "body", (30 * s, EAR, 0), rot(y=90 * s))      # falling to the middle
        m.place("54200", "body", (30 * s, EAR, 0), rot(y=90 * s))
