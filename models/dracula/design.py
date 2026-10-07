"""Dracula: a tiny Quick Bricks figure, 32 pieces, 3 studs wide - big round eyes, grey skin,
two white fangs over a red mouth, slicked-back black hair with a widow's peak and swept-back
sides, and black shoes poking out under his cape.

Built from the 12-page plans in reference/ (page_01..page_12.png): one step here per page,
pages 1-11, page 12 being the finished figure. NOTES.md has the page-by-page parts list.

Frame: LDU, -Y up, the front faces -Z. The body is one stud deep (z = 0) and three wide
(x = -20, 0, 20); the feet reach one stud forward (z = -20). The feet's plates sit on y = 0.
A cheese slope's (54200's) origin is its bottom, a plate's or brick's its top."""
import numpy as np

from brickkit.ldraw.matrix import rot

PLATE, BRICK = 8, 24
SIDE = (-20, 20)                  # the two outer columns


def orient(ex, ey, ez=None) -> np.ndarray:
    """3x3 rotation whose columns are where the part's local X, Y and Z axes point."""
    ex, ey = np.asarray(ex, float), np.asarray(ey, float)
    ez = np.cross(ex, ey) if ez is None else np.asarray(ez, float)
    return np.column_stack([ex, ey, ez])


# the layers' tops, from the floor up
FEET = 0                          # the two 1 x 2 plates
LEGS = FEET - BRICK               # the 1 x 3 brick
CAPE = LEGS - PLATE               # three black plates
SHIRT = CAPE - PLATE              # black, white, black
FANGS = SHIRT - PLATE             # the fang plates and the red mouth
CHIN = FANGS - PLATE              # grey plates under the eyes
NOSE_BRICK = FANGS - BRICK        # the middle grey brick, its stud forward for the nose
FACE = CHIN - BRICK               # the eye bricks; the middle's grey plate
HAIR = FACE - PLATE               # black plates (the middle two high: the widow's peak)
CROWN = HAIR - PLATE              # the middle's second plate
TOP = CROWN - PLATE               # the tile on top
SIDE_STUD = 10                    # a 1 x 1 brick's side studs: 10 below its top

# on a side stud, a part's studs (local -Y) face out; a cheese slope's high back (local +Z)
# hangs down, so its slope faces up and out
EAR = {-1: orient((0, 0, 1), (1, 0, 0), (0, 1, 0)),          # the left side (-X)
       1: orient((0, 0, -1), (-1, 0, 0), (0, 1, 0))}         # the right side (+X)
FORWARD = orient((-1, 0, 0), (0, 0, 1), (0, 1, 0))            # facing front (-Z)
EYE = orient((0, 1, 0), (0, 0, 1), (1, 0, 0))   # facing front, turned so the glint is top left


def build(model):
    m = model.main

    m.step("The feet: two 1 x 2 plates, a stud apart")
    for x in SIDE:
        m.place("3023", "cape", (x, FEET, -10), rot(y=90))

    m.step("The legs: a 1 x 3 brick across their back studs")
    m.place("3622", "cape", (0, LEGS, 0))

    m.step("Shoes on the front studs")
    for x in SIDE:
        m.place("54200", "cape", (x, FEET, -20))

    m.step("The cape: three 1 x 1 plates")
    for x in (-20, 0, 20):
        m.place("3024", "cape", (x, CAPE, 0))

    m.step("The shirt front in the middle")
    for x in (-20, 0, 20):
        m.place("3024", "shirt" if x == 0 else "cape", (x, SHIRT, 0))

    m.step("The fangs, and the red mouth between them")
    for x in SIDE:
        m.place("15070", "fang", (x, FANGS, 0))          # the tooth hangs down in front
    m.place("3024", "mouth", (0, FANGS, 0))

    m.step("The face: grey plates, and a brick with a stud in front for the nose")
    for x in SIDE:
        m.place("3024", "skin", (x, CHIN, 0))
    m.place("87087", "skin", (0, NOSE_BRICK, 0))

    m.step("Bricks with studs in front and on the outside, for the eyes and the hair")
    m.place("26604", "skin", (-20, FACE, 0), rot(y=90))     # studs front and left
    m.place("26604", "skin", (20, FACE, 0))                 # studs front and right
    m.place("3024", "skin", (0, FACE, 0))

    m.step("Black hair, one plate higher in the middle: the widow's peak")
    for x in (-20, 0, 20):
        m.place("3024", "hair", (x, HAIR, 0))
    m.place("3024", "hair", (0, CROWN, 0))

    m.step("Slick it back: slopes on top and on each side, a tile in the middle")
    m.place("54200", "hair", (-20, HAIR, 0), rot(y=90))     # falling away to the left
    m.place("54200", "hair", (20, HAIR, 0), rot(y=-90))     # and to the right
    m.place("3070b", "hair", (0, TOP, 0))
    for s in (-1, 1):
        m.place("54200", "hair", (30 * s, FACE + SIDE_STUD, 0), EAR[s])

    m.step("The eyes and the nose")
    for x in SIDE:
        m.place("98138p07", "eye", (x, FACE + SIDE_STUD, -10 - PLATE), EYE)
    m.place("54200", "skin", (0, NOSE_BRICK + SIDE_STUD, -10), FORWARD)
