"""A PEZ dispenser as near its real size as bricks allow, under any head (models/pez_*).

The real thing is about 10.5 cm tall with its head; its stem is narrow from side to side and
deep from front to back, on a thin foot that is longer than it is wide. Here:

    foot    a 2 x 4 plate, long from front to back, with two jumper plates on its middle (the
            stem is one stud wide, on a foot two wide) and a tile at each end: 16 x 32 mm
    stem    one stud wide and two deep, 64 mm tall: four times two plates and two bricks with
            a stud on each side, and on those studs two 2 x 4 tiles each side. 14.4 x 16 mm
    hinge   a locking hinge plate on top, its fingers past the back; the head's own hinge
            plate stands upright on the back of the head. The head tips back about that hinge
            in clicks of 22.5 degrees, as a real one tips back to give a sweet
    sweet   a 1 x 2 tile on the hinge plate: the head rests on it, and it shows when the head
            is tipped back

Frame: LDU (stud 20, plate 8), -Y up, the front faces -Z, the table is y = 0. A head is built
in its own frame, the same but with y = 0 at its underside (HEAD above the table): its
middle column is x = 0, its back row is HEAD_BACK, and at the foot of that row it must have
the brick `head_mount` places (the upright hinge plate goes on its two studs).

Palette roles: `stem` (everything but the sweet), `sweet`."""
from __future__ import annotations

import numpy as np

from ..ldraw.matrix import rot, translate

EY = np.array([0.0, 1.0, 0.0])
FOOT = 16                 # top of the foot
STEM = FOOT + 4 * 40      # top of the stem's last brick
HEAD = STEM + 16          # the head's underside: on the sweet, which is on the hinge plate
HINGE = (STEM + 6.0, 30.0)   # the hinge's axis (it runs from side to side): its height, its z
HEAD_BACK = 14.0          # z of the middle of the head's back row (its back face is 10 further)
TIP = 67.5                # how far the head tips back: three clicks
SIDES = rot(y=90)         # a brick's two side studs (its own +-Z) to the left and the right
BACK = rot(y=180)         # a side stud (its own -Z) to the back


def orient(ex, ey) -> np.ndarray:
    """A rotation given by where a part's own X and Y axes point (its Z follows)."""
    ex, ey = np.asarray(ex, float), np.asarray(ey, float)
    return np.column_stack([ex, ey, np.cross(ex, ey)])


def y(h) -> float:
    """Height above the table (or above a head's underside) -> the frame's y."""
    return -float(h)


def build_stem(model, sub=None) -> None:
    """The foot, the stem, its hinge plate and the sweet, in `sub` (the main model if not
    given): 27 pieces, the same for every head."""
    m = sub or model.main
    m.step("The foot: a 2 x 4 plate, long from front to back. On its middle two plates with "
           "one stud each, side by side across it, and a 1 x 2 tile at each end")
    m.place("3020", "stem", (0, y(8), 0), rot(y=90), tag="foot")
    for z in (-10, 10):
        m.place("15573", "stem", (0, y(FOOT), z), tag="foot")
    for z in (-30, 30):
        m.place("3069b", "stem", (0, y(FOOT), z), tag="foot")
    for k in range(4):
        base = FOOT + 40 * k
        m.step(("The stem stands on the foot's two studs, one stud wide and two deep. Two "
                "1 x 2 plates, then two bricks with a stud on each side, studs to the left "
                "and the right", "Two more plates and two more of those bricks",
                "The same again", "And once more: the stem's full height")[k])
        for h in (8, 16):
            m.place("3023", "stem", (0, y(base + h), 0), rot(y=90), tag="stem")
        for z in (-10, 10):
            m.place("47905", "stem", (0, y(base + 40), z), SIDES, tag="stem")
    for side, text in ((-1, "Press two 2 x 4 tiles onto the studs of one side, one above the "
                            "other: the stem's smooth side"), (1, "And two on the other side")):
        m.step(text)
        for k in range(2):
            m.place("87079", "stem", (18 * side, y(FOOT + 40 + 80 * k), 0),
                    orient((0, -1, 0), (-side, 0, 0)), tag="sides")
    m.step("On top: the hinge plate with two fingers, fingers past the back of the stem, and "
           "on it a 1 x 2 tile: the sweet")
    m.place("54657", "stem", (0, y(STEM + 8), 0), orient((0, 0, 1), EY), tag="hinge")
    m.place("3069b", "sweet", (0, y(HEAD), 0), rot(y=90), tag="sweet")


# A head ---------------------------------------------------------------------------------------
# Every head has the same heart, 24 mm square and 16 mm tall: eight tall bricks with two studs
# on one side, in a ring, under a plate that ties them. Three face the front (the face goes on
# their six studs), two each side face out (the cheeks), and the one in the middle of the back
# faces back: the head's hinge plate stands on it. In the head's frame the columns are
# x = -20, 0, 20 and the rows z = ROWS (front, middle, back); the heart's top is CORE.
ROWS = (HEAD_BACK - 40, HEAD_BACK - 20, HEAD_BACK)
CORE = 40                 # top of the tall bricks
FRONT = rot(x=90)         # a plate's or tile's studs to the front; its own +Z is then up
RIGHT = rot(z=90)         # studs to the right (+X); its own +Z is still the back
LEFT = rot(z=-90)


def on_front(head, part, role, x, h, turn=0.0, out=0.0, tag="face", slope=False):
    """A plate or tile (or with `slope` a slope, whose origin is its underside) on the front
    of the head: its middle at column x and height h, turned `turn` degrees about the way it
    faces, `out` LDU further forward than the bricks' own studs (a second layer: 8)."""
    z = ROWS[0] - 10 - out - (0 if slope else 8)
    head.place(part, role, (x, y(h), z), FRONT @ rot(y=turn), tag=tag)


def build_cheek(model, name="cheek", title="Cheek"):
    """A cheek in its own frame, to be filled in by the model: two tall bricks side by side,
    studs to +X, their feet on y = 0 and the middle of the pair at x = z = 0. What the model
    puts on their four studs has to join the two. Returns the sub-model; place it with
    `place_cheeks`."""
    cheek = model.submodel(name, title)
    return cheek


def cheek_bricks(cheek, role="head"):
    for z in (-10, 10):
        cheek.place("32952", role, (0, y(CORE), z), orient((0, 0, 1), EY), tag="cheek")


def head_face_bricks(head, role="head"):
    """The three tall bricks of the face, studs forward."""
    for x in (-20, 0, 20):
        head.place("32952", role, (x, y(CORE), ROWS[0]), tag="face_bricks")


def head_mount(head, role="head") -> None:
    """The tall brick in the middle of the back row, studs to the back: the hinge's."""
    head.place("32952", role, (0, y(CORE), HEAD_BACK), BACK, tag="mount")


def place_cheeks(head, cheek) -> None:
    """The two cheeks, one each side of the head (the same sub-assembly, turned round)."""
    z = (ROWS[1] + ROWS[2]) / 2
    head.use(cheek, (20, 0, z), tag="cheek_right")
    head.use(cheek, (-20, 0, z), rot(y=180), tag="cheek_left")


def dome_slopes(head, role, h, tag="dome"):
    """A low dome on a 3 x 3 square of studs whose top is at h: four curved 1 x 2 slopes round
    the edge, each thick at the middle of a side and thin at a corner (a pinwheel). The middle
    stud is left for `dome_top`."""
    cz = ROWS[1]
    for (ax, az), (bx, bz) in (((-1, -1), (0, -1)), ((1, -1), (1, 0)), ((1, 1), (0, 1)), ((-1, 1), (-1, 0))):
        u = np.array([bx - ax, 0.0, bz - az])
        head.place("11477", role, (10 * (ax + bx), y(h), cz + 10 * (az + bz)),
                   orient(np.cross(EY, u), EY), tag=tag)


def dome_top(head, h, parts=(("3024", "head"), ("3070b", "head")), tag="dome"):
    """The middle of the dome: `parts` [(part, role)] stacked on the middle stud, a plate
    high each (a plate under a tile brings it level with the slopes)."""
    for k, (part, role) in enumerate(parts):
        head.place(part, role, (0, y(h + 8 * (k + 1)), ROWS[1]), tag=tag)


def head_hinge(head, role: str = "stem") -> None:
    """The head's hinge plate (in its frame): upright on the mount's two studs, its one finger
    down. Call it in a step of its own, the head's last."""
    at = np.array([0.0, y(HINGE[0] - HEAD), HINGE[1]]) - np.array([0.0, 30.0, -2.0])
    head.place("44301b", role, tuple(at), orient(EY, (0, 0, -1)), tag="hinge", insert=(0, 0, 1))


def mount_head(model, head, text: str | None = None) -> None:
    """The head onto the stem: its hinge plate's finger between the stem's two, the head down
    on the sweet. And how it moves: tipped back about the hinge, TIP degrees at t = 1."""
    m = model.main
    m.step(text or "Click the head's hinge finger between the two fingers at the back of the "
           "stem, and tip the head forward until it rests on the sweet. Tip it back: it "
           "clicks, like the real thing")
    m.use(head, (0, y(HEAD), 0), tag="head", insert=(0, 0.5, 0.87))
    pivot = np.array([0.0, y(HINGE[0]), HINGE[1]])
    model.moving_group("head", "head")

    def pose(t: float) -> dict:
        R = np.eye(4)
        R[:3, :3] = rot(x=-TIP * float(t))
        return {"head": translate(*pivot) @ R @ translate(*-pivot)}
    model.pose = pose
