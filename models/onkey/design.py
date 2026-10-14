"""Onkey: theroldangrace's little monkey head, taken in from their build video (NOTES.md) and
modelled our own way where the video doesn't show how it goes together.

A head four studs wide and four deep on two long arms that lie on the table, a rounded hand at
the end of each. On the face: a tan muzzle in two halves (a curved brick on a tan plate for the
upper lip; two inverted curved bricks for the jaw), two googly eyes (a white cone with a black
round tile), a little nose, tan ears with a darker inner ear beside the face, a rounded top
and a tuft. Each ear stands on its arm: two tall bricks with studs on one side, on a plate
across the arm, hold its three tiles.

The jaw drops. Its two inverted curved bricks hang under two tan 1 x 3 tiles, and each tile
stands on a little column (two 1 x 1 plates on a plate with a clip) whose clip holds the bar of
a plate with a handle, low down inside the head, below the jaw's foot: the jaw swings forward
and down about that bar, and nothing behind it is in its way. The tan plate the upper lip
stands on is in the middle of the same layer as the jaw's two tiles, so shut, the muzzle is
one smooth pill, as in the video: a curved brick and a plate above the line, a curved brick
below it.

Frame: LDU (stud 20, plate 8, brick 24), -Y up, the face looks to -Z; the table is y = 0.
Across the head: x = -30, -10, 10, 30; front row z = -30, back row z = 30. Heights are given
above the table (`y(h)`). Colours are palette roles from model.toml."""
import numpy as np

from brickkit.ldraw.matrix import rot, translate

EY = np.array([0.0, 1.0, 0.0])          # down
SIDES = (1, -1)                         # our right (x > 0), then our left
ARM_Z = -30                             # the arms lie under the head's front row
EYE_H = 78                              # the middle of each eye: the side studs of the eye row
EAR_H = 72                              # the middle of each ear (a D, 2 studs out, 4 tall)
HINGE = (22.0, 10.0)                    # the jaw's bar: its height, its z (it runs along x)
OPEN = 7.0                              # how far the jaw drops, in degrees (about as in the video)


def y(h) -> float:
    """Height above the table -> the frame's y."""
    return -float(h)


def axes(ex, ey):
    """A rotation given by where a part's own X and Y axes point (its Z follows)."""
    ex, ey = np.asarray(ex, float), np.asarray(ey, float)
    return np.column_stack([ex, ey, np.cross(ex, ey)])


FACING = axes((1, 0, 0), (0, 0, 1))     # a part on a stud that faces the front: its top to -Z


def ring(out, up):
    """A macaroni tile (27925) facing the front, its quarter ring opening `out` (+-1: to our
    right or left) and `up` (+-1). The ring's corner is its own (-10, 10); its origin is the
    1 x 1 hole inside the ring."""
    o = np.array([float(out), 0, 0])
    u = np.array([0, -float(up), 0])
    for ex, mz in ((o, u), (u, o)):     # own +X and own -Z go out and up, one way round
        R = np.column_stack([ex, (0, 0, 1), -mz])
        if np.linalg.det(R) > 0:
            return R
    raise ValueError("no turn")


def build_arm(model):
    """One arm, lying on the table: a 1 x 6 plate whose first two studs go under the head, a
    rounded 1 x 1 piece for the forearm, and a 1 x 2 brick with a rounded top for the hand. The
    third stud is left for the ear."""
    arm = model.submodel("arm", "Arm")
    arm.step("An arm: a 1 x 6 plate, a rounded 1 x 1 piece on its fourth stud, and the hand on "
             "the end: a 1 x 2 brick with a rounded top. Make two")
    arm.place("3666", "body", (60, y(8), 0), tag="arm")
    arm.place("49307", "body", (70, y(8), 0), tag="arm")
    arm.place("3004", "body", (100, y(32), 0), tag="hand")
    arm.place("3563", "body", (100, y(32), 0), tag="hand")
    return arm


def build_jaw_half(model):
    """Half the jaw, upside down to how it hangs: an inverted curved brick, its thin end out,
    and a tan 1 x 1 tile on the low stud of its thick end (it fills the step in its top)."""
    half = model.submodel("jaw_half", "Half the jaw")
    half.step("Half the jaw: an inverted curved brick and a tan 1 x 1 tile on its lower stud. "
              "Make two")
    half.place("24201", "tan", (0, 0, 0), tag="jaw")
    half.place("3070b", "tan", (0, 0, 20), tag="jaw")
    return half


def build(model):
    m = model.main
    arm = build_arm(model)
    jaw_half = build_jaw_half(model)
    L = 8                                       # everything from the jaw up stands a plate higher
                                                # than the hinge's plates

    # --- the base and the arms ------------------------------------------------------------
    m.step("The arms, side by side under the front row, their hands out to the sides, and a "
           "1 x 4 plate on the back row")
    for s in SIDES:
        m.use(arm, (0, 0, ARM_Z), rot(y=0 if s > 0 else 180), tag="arms")
    m.place("3710", "body", (0, y(8), 30), tag="base")
    m.step("A 1 x 4 plate on the back row, and on it the jaw's hinge: two plates with a handle, "
           "handles to the front")
    m.place("3710", "body", (0, y(16), 30), tag="base")
    for s in SIDES:
        m.place("48336", "hinge", (20 * s, y(24), 30), tag="hinge")
    m.step("Push a plate with a clip onto each handle from the front, clip to the back: they "
           "hang on the handles. Then a 1 x 4 plate across the arms' inner ends, and another on "
           "that")
    for s in SIDES:
        m.place("61252", "clip", (30 * s, y(24), -10), rot(y=180), tag="jaw", insert=(0, 0, -1))
    for h in (16, 24):
        m.place("3710", "body", (0, y(h), -30), tag="core")
    m.step("Two 1 x 1 plates on each clip plate: the jaw will stand on these. Two 1 x 2 plates "
           "in the middle at the front, a 1 x 4 plate on the handles and a 2 x 4 plate on that")
    for s in SIDES:
        for h in (32, 40):
            m.place("3024", "clip", (30 * s, y(h), -10), tag="jaw")
    for h in (32, 40):
        m.place("3023", "body", (0, y(h), -30), tag="core")
    m.place("3710", "body", (0, y(32), 30), tag="core")
    m.place("3020", "body", (0, y(40), 20), tag="core")
    m.step("A tan 2 x 3 plate on the middle, sticking out a stud in front: the upper lip stands "
           "on it. Two 1 x 4 plates behind it")
    m.place("3021", "tan", (0, y(40 + L), -30), rot(y=90), tag="lip")
    for z in (10, 30):
        m.place("3710", "body", (0, y(40 + L), z), tag="core")

    # --- the jaw and the lip ----------------------------------------------------------------
    m.step("A tan 1 x 3 tile on each column, sticking out in front")
    for s in SIDES:
        m.place("63864", "tan", (30 * s, y(40 + L), -30), rot(y=90), tag="jaw")
    m.step("The jaw: push a half up under the front of each tile, thin ends out")
    for s in SIDES:
        m.use(jaw_half, (30 * s, y(32 + L), -50), axes((0, 0, s), EY), tag="jaw",
              insert=(0, 1, 0))
    m.step("A tan 1 x 2 plate on the front of the tan plate")
    m.place("3023", "tan", (0, y(48 + L), -50), tag="lip")
    m.step("The upper lip: a tan curved brick over it (the plate fits up inside it)")
    m.place("93273", "tan", (0, y(40 + L), -50), rot(y=90), tag="lip")

    # --- the face ---------------------------------------------------------------------------
    m.step("A 4 x 4 plate over the whole head, and another on it")
    for h in (48, 56):
        m.place("3031", "body", (0, y(h + L), 0), tag="core")

    # --- the ears, on the arms --------------------------------------------------------------
    m.step("The ear posts: on each arm's free stud a 1 x 2 plate, front to back, half of it "
           "sticking out behind; a 1 x 1 tile on its front stud and two 1 x 1 plates on its "
           "back one")
    for s in SIDES:
        m.place("3023", "body", (50 * s, y(16), -20), rot(y=90), tag="ears")
        m.place("3070b", "body", (50 * s, y(24), -30), tag="ears")
        for h in (24, 32):
            m.place("3024", "body", (50 * s, y(h), -10), tag="ears")
    m.step("Two tall bricks with studs on one side on each, one on the other, studs to the front")
    for s in SIDES:
        for h in (72, 112):
            m.place("32952", "body", (50 * s, y(h), -10), tag="ears")
    m.step("The ears: on each post a darker half circle, flat side in, and a tan macaroni tile "
           "above it and below it, round side out")
    for s in SIDES:
        half = axes((0, 1, 0), (0, 0, 1)) @ (rot(y=180) if s > 0 else np.eye(3))
        m.place("1748", "inner", (50 * s, y(EAR_H), -28), half, tag="ears", insert=(0, 0, -1))
        m.place("27925", "tan", (50 * s, y(EAR_H + 10), -28), ring(s, 1), tag="ears",
                insert=(0, 0, -1))
        m.place("27925", "tan", (50 * s, y(EAR_H - 10), -28), ring(s, -1), tag="ears",
                insert=(0, 0, -1))

    m.step("The eye row along the front: at each end a brick with a stud on its front, and "
           "between them a 1 x 2 brick with a hole")
    for s in SIDES:
        m.place("87087", "body", (30 * s, y(80 + L), -30), tag="face")
    m.place("3700", "body", (0, y(80 + L), -30), tag="face")
    m.step("Behind them: a 1 x 4 brick, and a 2 x 4 brick on the back two rows")
    m.place("3010", "body", (0, y(80 + L), -10), tag="face")
    m.place("3001", "body", (0, y(80 + L), 20), tag="face")

    m.step("The eyes: a white cone on each end stud, and a black round tile on each cone")
    for s in SIDES:
        m.place("33492", "eye", (30 * s, y(EYE_H), -56), FACING, tag="eyes", insert=(0, 0, -1))
        m.place("98138", "pupil", (30 * s, y(EYE_H), -64), FACING, tag="eyes", insert=(0, 0, -1))
    m.step("The nose: a half pin in the hole, and a round tile on its end")
    m.place("4274", "pin", (0, y(EYE_H), -40), axes((0, 0, -1), EY), tag="nose", insert=(0, 0, -1))
    m.place("98138", "body", (0, y(EYE_H), -48), FACING, tag="nose", insert=(0, 0, -1))

    # --- the forehead and the top -----------------------------------------------------------
    m.step("The forehead: two 2 x 4 bricks")
    for z in (-20, 20):
        m.place("3001", "body", (0, y(104 + L), z), tag="forehead")
    m.step("The top of the head: curved bricks round the edge, each curving down to the "
           "outside, and in the middle two tan 2 x 2 plates (out of sight) and a 2 x 2 plate "
           "with one stud")
    for s in SIDES:
        m.place("37352", "body", (20 * s, y(128 + L), -30), tag="top")
        m.place("37352", "body", (20 * s, y(128 + L), 30), rot(y=180), tag="top")
        m.place("37352", "body", (30 * s, y(128 + L), 0), axes((0, 0, s), EY), tag="top")
    for h in (112, 120):
        m.place("3022", "inside", (0, y(h + L), 0), tag="top")
    m.place("87580", "body", (0, y(128 + L), 0), tag="top")
    m.step("The tuft: a round plate and a little rounded piece on top")
    m.place("6141", "body", (0, y(136 + L), 0), tag="tuft")
    m.place("49307", "body", (0, y(136 + L), 0), tag="tuft")

    # --- the jaw drops ----------------------------------------------------------------------
    model.moving_group("jaw", "jaw")
    pivot = np.array([0.0, y(HINGE[0]), HINGE[1]])

    def pose(t: float) -> dict:
        R = np.eye(4)
        R[:3, :3] = rot(x=OPEN * float(t))
        return {"jaw": translate(*pivot) @ R @ translate(*-pivot)}
    model.pose = pose
