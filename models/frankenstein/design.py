"""Frankenstein: a tiny Quick Bricks figure, 17 pieces, 2 studs wide - a flat-topped grey head
with sleepy white eyes, a bar of a brow, two white neck bolts and grey arms, standing on a black
body on a black base.

Built from Agosami Brickworks' 2-page plans (Rebrickable MOC-215912): one step here per numbered
step 1-11; step 12 of the plans is the finished figure. NOTES.md has the step-by-step parts list.

Frame: LDU, -Y up, the front faces -Z. The body is two studs wide (x = -10, +10) and one deep,
standing on the back row of the 2 x 2 base (z = +10), so the base's front row is a ledge in front
of him. The base's top is y = 0. A plate's, brick's or tile's origin is its top. On a side stud a
part's studs (local -Y) face out, so its local Y points into the model."""
import numpy as np

PLATE, BRICK = 8, 24
SIDES = (-1, 1)                    # the left (-X) and right (+X) as you face him
NAME = {-1: "l", 1: "r"}
CZ = 10                            # the back row of the base: the body's middle, front to back


def orient(ex, ey, ez=None) -> np.ndarray:
    """3x3 rotation whose columns are where the part's local X, Y and Z axes point."""
    ex, ey = np.asarray(ex, float), np.asarray(ey, float)
    ez = np.cross(ex, ey) if ez is None else np.asarray(ez, float)
    return np.column_stack([ex, ey, ez])


# the layers' tops, from the floor up
BASE = 0                           # the 2 x 2 tile with two studs
LEGS = BASE - PLATE                # the 1 x 2 plate
BODY = LEGS - BRICK                # the two headlight bricks
HEAD = BODY - 40                   # the 1 x 2 x 1 2/3 brick with studs on three sides
BROW = HEAD - BRICK                # the 1 x 2 brick with two studs on its front
TOP = BROW - PLATE                 # the black tile on top
UPPER, LOWER = 10, 30              # the head's two rows of side studs, below its top
HL_STUD = 10                       # a headlight brick's side stud: 10 below its top

# a headlight brick turned so its side stud (local -Z) faces out to the side
HEADLIGHT = {s: orient((0, 0, s), (0, 1, 0)) for s in SIDES}
# a part on a side stud, its studs out to the side: local -Y out, a half-round tile's round end down
SIDE = {s: orient((0, 0, s), (-s, 0, 0)) for s in SIDES}
# a part on a front stud, its studs out to the front (-Z); the eye's black half falls to the bottom
FRONT = orient((1, 0, 0), (0, 0, 1))


def build(model):
    m = model.main

    m.step("The base: a 2 x 2 tile with two studs along its back edge")
    m.place("33909", "dark", (0, BASE, 0))

    m.step("A 1 x 2 plate on the two studs")
    m.place("3023", "dark", (0, LEGS, CZ))

    m.step("Two bricks with a side stud, the studs facing out to each side")
    for s in SIDES:
        m.place("4070", "dark", (10 * s, BODY, CZ), HEADLIGHT[s])

    m.step("A 1 x 1 plate on each side stud, its stud facing out")
    for s in SIDES:
        m.place("3024", "dark", (24 * s, BODY + HL_STUD, CZ), SIDE[s], tag=f"arm_{NAME[s]}")

    m.step("A half-round tile on each: the arms")
    for s in SIDES:
        m.place("24246", "skin", (32 * s, BODY + HL_STUD, CZ), SIDE[s], tag=f"arm_{NAME[s]}")

    m.step("The head: a brick with studs on its front and both ends")
    m.place("67329", "skin", (0, HEAD, CZ), tag="head")

    m.step("The neck bolts: a round plate on the lower stud at each end")
    for s in SIDES:
        m.place("6141", "bolt", (28 * s, HEAD + LOWER, CZ), SIDE[s], tag="bolts")

    m.step("A 1 x 2 plate with a stud across the two lower studs in front: the mouth")
    m.place("15573", "skin", (0, HEAD + LOWER, -PLATE), FRONT, tag="mouth")

    m.step("Sleepy eyes on the two upper studs in front")
    for s in SIDES:
        m.place("98138p2l", "eye", (10 * s, HEAD + UPPER, -PLATE), FRONT, tag="eyes")

    m.step("A 1 x 2 brick with two studs in front, on top of the head")
    m.place("11211", "skin", (0, BROW, CZ), tag="brow")

    m.step("A black tile on top, and the grey brow bar on the two studs in front")
    m.place("3069b", "dark", (0, TOP, CZ), tag="top")
    m.place("99563", "skin", (0, BROW + 10, -PLATE), FRONT, tag="brow")
