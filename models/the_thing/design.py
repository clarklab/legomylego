"""The Thing: a Quick Bricks model, zeldar's design, built as zeldar's instructions build it
(reference/: the app's picture, its parts list and its 36 pages, as screenshots). Each step
here is a page there, except page 3, whose two layers of legs are two steps here. Every page
was checked by laying a render from the app's camera over it (ortho, 45 degrees round, 30 up).

Frame: LDU (stud 20, plate 8, brick 24), -Y up, the front faces -Z. The table is y = 0, where
the feet stand; the body is centred on x = 0. The chest is five studs wide (x = -40 .. 40) and
two deep (z = -10, 10). Colours are palette roles from model.toml.

How it goes together: the shorts and legs, the chest widening on two inverted slopes, the
shoulders, and an arm on each side, its first plate's stud in a technic brick's hole, so it
turns. The head hangs in front of the chest: a half pin in a technic brick's hole holds a
bracket, its 2 x 2 plate level and studs down, and the face is built upside down under that
plate. Three bricks on their backs above it carry the eyes and nose. The brow and the top of the
head sit half a stud forward of the studs below them: a 1 x 2 plate's middle tube goes into a
hollow side stud (the 87087s'), and the brow tiles hang centred on the brackets' hollow studs
the same way."""
import numpy as np

from brickkit.ldraw.matrix import rot

PLATE, BRICK = 8, 24
EX, EY, EZ = np.eye(3)


def axes(x, y, z):
    """A rotation given by where a part's own X, Y and Z axes point."""
    return np.column_stack((x, y, z)).astype(float)


WAIST = -32                 # the top of the shorts
CHEST = WAIST - BRICK       # the top of the inverted slopes
SHOULDER = CHEST - BRICK    # the top of the technic bricks
TOP = SHOULDER - PLATE      # the top of the plates over them
CAP = TOP - BRICK           # the top of the shoulders
HOLE = CAP + 10             # the middle technic brick's hole, where the head hangs
ARM_HOLE = SHOULDER + 10    # the side technic bricks' holes, where the arms turn

FLIP = rot(z=180)           # upside down: studs down
BACK = axes(-EX, EZ, EY)    # on its back: studs to the front
SNOT = rot(x=90)            # a bracket turned so its 1 x 2 plate stands up, studs to the
#                             front, and its 2 x 2 plate lies level in front, studs down

# The arms turn on their studs; as in the pages they hang back a little from straight down
SWING = {-1: -20.0, 1: -15.0}

X0 = 10                     # the head bracket's middle: the half pin is in its left stud hole
P0, P1, P2 = X0 - 30, X0 - 10, X0 + 10      # the face's three columns, left to right
FACE_Z = -50                # the front row of the bracket's studs, where the face hangs
BROW_Z = -52                # the brow plates' front studs: half a stud forward of the side
#                             studs (z = -42) whose holes their middle tubes go into


def arm_frame(side):
    """Where an arm's own frame sits: its first plate's stud in the hole, its studs pointing
    into the body, down the arm along its +Z, swung back a little."""
    R = rot(x=-SWING[side]) @ axes(side * EZ, side * EX, EY)
    return np.array((side * 50, ARM_HOLE, 0.0)), R


def arm_place(m, side, part, pos, R, tag):
    O, A = arm_frame(side)
    m.place(part, "orange", tuple(np.round(O + A @ np.asarray(pos, float), 4)),
            np.round(A @ R, 12), tag=tag)


def build_arm(m, side, steps):
    """One arm, a page at a time. `steps` groups its four parts into pages."""
    fwd = -side                     # the way forward along the arm's own X
    parts = {
        "shoulder": ("3024", (0, 0, 0), np.eye(3), "arm"),
        "corner": ("2420", (0, PLATE, 20), rot(y=180) if fwd < 0 else rot(y=90), "arm"),
        "hand": ("61252", (20 * fwd, 2 * PLATE, 20), rot(y=-90 * fwd), "hand"),
        "upper": ("3023", (0, 2 * PLATE, 10), rot(y=90), "arm"),
    }
    for caption, names in steps:
        m.step(caption)
        for n in names:
            part, pos, R, tag = parts[n]
            arm_place(m, side, part, pos, R, tag)


def build(model):
    m = model.main

    # Pages 1-3: the shorts and legs
    m.step("The shorts: a blue 2 x 3 plate")
    m.place("3021", "blue", (0, WAIST, 0), tag="shorts")
    m.step("Under it a blue 1 x 2 plate at each end, front to back")
    for x in (-20, 20):
        m.place("3023", "blue", (x, WAIST + PLATE, 0), rot(y=90), tag="shorts")
    for k in (2, 3):
        m.step("An orange 1 x 2 plate under each: the legs")
        for x in (-20, 20):
            m.place("3023", "orange", (x, WAIST + k * PLATE, 0), rot(y=90), tag="legs")

    # Pages 4-8: the chest
    m.step("The chest: an inverted slope on each end of the shorts, sloping out")
    m.place("3660b", "orange", (-20, CHEST, 0), rot(y=90), tag="chest")
    m.place("3660b", "orange", (20, CHEST, 0), rot(y=-90), tag="chest")
    m.step("A 1 x 2 brick between them")
    m.place("3004", "orange", (0, CHEST, 0), rot(y=90), tag="chest")
    m.step("A technic brick on each end, its hole out to the side")
    for x in (-40, 40):
        m.place("3700", "orange", (x, SHOULDER, 0), rot(y=90), tag="chest")
    m.step("A 2 x 3 brick between them")
    m.place("3002", "orange", (0, SHOULDER, 0), tag="chest")
    m.step("A 2 x 3 plate across the middle and a 1 x 2 plate on each end")
    m.place("3023", "orange", (-40, TOP, 0), rot(y=90), tag="chest")
    m.place("3021", "orange", (0, TOP, 0), tag="chest")
    m.place("3023", "orange", (40, TOP, 0), rot(y=90), tag="chest")

    # Pages 9-12: the shoulders
    m.step("A 1 x 1 plate at the back of the middle")
    m.place("3024", "orange", (0, TOP - PLATE, 10), tag="shoulders")
    m.step("A cheese slope on it, sloping down to the back")
    m.place("54200", "orange", (0, TOP - PLATE, 10), rot(y=180), tag="shoulders")
    m.step("A corner slope on each side, its stud at the inner front corner")
    m.place("3045", "orange", (-20, CAP, -10), rot(y=180), tag="shoulders")
    m.place("3045", "orange", (20, CAP, -10), rot(y=-90), tag="shoulders")
    m.step("A technic brick in front between them, its hole to the front")
    m.place("6541", "orange", (0, CAP, -10), tag="shoulders")

    # Pages 13-19: the arms, each turning on a stud in a side technic brick's hole
    build_arm(m, -1, [
        ("The right arm: a 1 x 1 plate, its stud in the technic brick's hole", ["shoulder"]),
        ("A 2 x 2 corner plate on it, its corner down, its other end forward", ["corner"]),
        ("A plate with a clip on the front of the corner plate: the hand", ["hand"]),
        ("A 1 x 2 plate on the upper arm", ["upper"]),
    ])
    build_arm(m, 1, [
        ("The left arm: a 1 x 1 plate, its stud in the technic brick's hole", ["shoulder"]),
        ("A 2 x 2 corner plate on it, its corner down, its other end forward", ["corner"]),
        ("A 1 x 2 plate on the upper arm, and a plate with a clip in front: the hand",
         ["upper", "hand"]),
    ])

    # Pages 20-21: the bracket the head hangs from
    m.step("A half pin in the hole at the front")
    m.place("4274", "pin", (0, HOLE, -20), rot(y=90), tag="neck")
    m.step("A bracket on the half pin: its 1 x 2 plate upright, studs to the front, and its "
           "2 x 2 plate level, studs down")
    m.place("99207", "orange", (X0, HOLE, -28), SNOT, tag="neck")

    # Pages 22-27: the face, upside down under the bracket's plate
    m.step("Under the front of the bracket: a black 1 x 1 plate (the mouth) and an orange one")
    m.place("3024", "black", (P1, TOP + PLATE, FACE_Z), FLIP, tag="mouth")
    m.place("3024", "orange", (P2, TOP + PLATE, FACE_Z), FLIP, tag="face")
    m.step("Under them a 1 x 1 plate and a bracket, its stud out to the side: the ear")
    m.place("3024", "orange", (P1, TOP + 2 * PLATE, FACE_Z), FLIP, tag="face")
    m.place("36841", "orange", (P2, TOP + 2 * PLATE, FACE_Z), rot(x=180) @ rot(y=-90),
            tag="ear")
    m.step("A 1 x 3 plate under them, out a stud to the left")
    m.place("3623", "orange", (P1, TOP + 3 * PLATE, FACE_Z), FLIP, tag="face")
    m.step("On the end of it a bracket, its stud out to the side (the other ear), and a 1 x 1 "
           "plate on that")
    m.place("36841", "orange", (P0, TOP + 2 * PLATE, FACE_Z), rot(x=180) @ rot(y=90),
            tag="ear")
    m.place("3024", "orange", (P0, TOP + PLATE, FACE_Z), FLIP, tag="face")
    m.step("A bracket on them beside the first, the same way round")
    m.place("73825", "orange", (P0, HOLE, -28), SNOT, tag="face")
    m.step("Three cheese slopes, upside down, in a row in the gap behind the face: one behind each "
           "column of the face, the thin end to the chest. The face hides the left two; only "
           "the right one shows")
    for x in (P0, P1, P2):
        m.place("54200", "orange", (x, TOP, -30), rot(x=180), tag="chin")

    # Pages 28-30: the eyes and nose, on bricks on their backs
    m.step("Three bricks on their backs on the brackets' studs, studs to the front: a brick "
           "with a side stud at each end, its side stud up")
    for x, part in ((P0, "87087"), (P1, "3005"), (P2, "87087")):
        m.place(part, "orange", (x, HOLE, -52), BACK, tag="eye_row")
    m.step("The eyes")
    for x in (P0, P2):
        m.place("98138pz0", "black", (x, HOLE, -60), BACK @ rot(y=180), tag="eyes")
    m.step("The nose: a cheese slope, thick end down")
    m.place("54200", "orange", (P1, HOLE, -52), rot(x=90) @ rot(y=180), tag="nose")

    # Pages 31-36: the brow and the top of the head
    m.step("A 1 x 2 plate on each side stud, its middle on the stud, running front to back")
    for x in (P0, P2):
        m.place("3023", "orange", (x, CAP - PLATE, BROW_Z + 10), rot(y=90), tag="brow")
    m.step("A 1 x 3 plate across their backs")
    m.place("3623", "orange", (P1, CAP - 2 * PLATE, BROW_Z + 20), tag="brow")
    m.step("A bracket on the front of each, hanging down over the eye")
    for x in (P0, P2):
        m.place("36841", "orange", (x, CAP - 2 * PLATE, BROW_Z), tag="brow")
    m.step("The top of the head: a 1 x 2 plate in the middle")
    m.place("3023", "orange", (P1, CAP - 3 * PLATE, BROW_Z + 10), rot(y=90), tag="head_top")
    m.step("And one each side")
    for x in (P0, P2):
        m.place("3023", "orange", (x, CAP - 3 * PLATE, BROW_Z + 10), rot(y=90), tag="head_top")
    m.step("The brow: a 1 x 2 tile on each bracket, its middle on the stud")
    for x in (P0, P2):
        m.place("3069b", "orange", (x, CAP - 2 * PLATE + 10, BROW_Z - 22), BACK, tag="brow")
