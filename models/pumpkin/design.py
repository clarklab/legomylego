"""Pumpkin: a Quick Bricks model, 51 pieces, 5.4 cm across and 6.8 cm tall with its leaf - a
jack-o'-lantern cube with a rounded look: black square eyes, a mouth with three black teeth,
and a green stem with a leaf. Designed by BrixBuild (Rebrickable MOC-163756); see NOTES.md for
the credit and the reading of the plans.

It is built sideways. A core of two halves, each with a 1 x 1 brick with studs on two sides
(26604) in every corner, has studs on all four faces; panels of plates go on those studs from
the side. The base half is built upside down (its plates' studs point down) and the head half
the right way up, so the two halves meet back to back with no studs between them; the side
panels, which reach across both halves, are what hold them together.

Built from the 20 pages of plans (31 numbered steps; the originals are in inbox/pumpkin/,
local only). Sub-assemblies, as in the plans: the mouth panel (steps 5-7), the head half (9-13),
the eyes panel (14-16), the side panel (19-21, built three times) and the stem (30). The two
steps 18 and 22 are one step here: the halves only stay together once a side panel is across
both, and brickkit needs every step to leave one piece.

Frame: LDU, -Y up, the front faces -Z; the pumpkin stands on y = 0. The core is 4 studs square
(x, z from -40 to 40): columns x = -30, -10, 10, 30 and rows z = +30 (back) ... -30 (front).
Heights below are above the floor (y = minus that). A part's origin is its top (its stud base):
a flipped part's origin is its bottom face."""
import numpy as np

from brickkit.ldraw.matrix import rot

PLATE, BRICK = 8, 24


def orient(ex, ey, ez=None) -> np.ndarray:
    """3x3 rotation whose columns are where the part's local X, Y and Z axes point."""
    ex, ey = np.asarray(ex, float), np.asarray(ey, float)
    ez = np.cross(ex, ey) if ez is None else np.asarray(ez, float)
    return np.column_stack([ex, ey, ez])


def y_at(height: float) -> float:
    """LDraw y for a height above the floor."""
    return -height


FLIP = rot(x=180)                 # upside down: studs point down

# base half, built upside down on its tiles (heights of each layer's far face)
TILES = 0                         # two 2 x 4 tiles, smooth side down
POSTS = y_at(PLATE)               # the corner bricks and the 2 x 4 brick sit on the tiles
DECK = y_at(PLATE + BRICK)        # the 2 x 4 plate and the two corner plates
CAP = y_at(PLATE + BRICK + PLATE)  # the 2 x 2 plate on top

# head half, the right way up: the layers' tops, from the bottom up (heights 40 .. 112)
HANG1 = y_at(48)                  # orange 1 x 4 plate, hung under the front edge
HANG2 = y_at(56)                  # grey 1 x 4 plate and the 2 x 2 plate under the 4 x 4
FLOOR = y_at(64)                  # grey 4 x 4 plate
CROWN = y_at(88)                  # tops of the four corner bricks
LID = y_at(96)                    # orange 4 x 4 plate: the top of the pumpkin
GREEN = y_at(104)                 # the green 2 x 2 corner tile and its plate
STEM = y_at(112)                  # the stem plate

FACE = 40                         # the core's faces are 40 from its middle


def side_studs(sx: int, sz: int, flipped: bool) -> np.ndarray:
    """A 26604 (studs on its +X and -Z sides) turned so its side studs face the two outer
    faces of the corner at (sx, sz); flipped: upside down."""
    base = FLIP if flipped else np.eye(3)
    want = {(sx, 0, 0), (0, 0, sz)}
    for k in range(4):
        R = rot(y=90 * k) @ base
        got = {tuple(int(round(v)) for v in R @ d) for d in ((1, 0, 0), (0, 0, -1))}
        if got == want:
            return R
    raise ValueError((sx, sz))


# --- panels: in their own frame the face looks -Z (outward), columns run along +X, rows go
# down +Y, and the origin is the middle of the top edge of the panel's back plane (z = 0).
# A layer's plate has its studs outward, its body behind its origin: layer L's origin is at
# z = -8 (L + 1); the plate the panel hides in the core's hollow is layer -1 (z = 0).
OUT = orient((1, 0, 0), (0, 0, 1))       # studs outward, the plate's long side along X


def cell(col: int, row: int) -> tuple:
    return (-30 + 20 * col, 10 + 20 * row)


def layer_z(layer: int) -> float:
    return -PLATE * (layer + 1)


def build(model):
    m = model.main

    # ---- the mouth panel: a plate of teeth hidden behind two corner plates (steps 5-7) ----
    mouth = model.submodel("mouth", "Mouth panel")
    mouth.step("The three teeth: a 1 x 2 plate, its studs out, the teeth up")
    # long side along X; the teeth (local -Z) point up; sits in the core's hollow, row 1
    mouth.place("15208", "teeth", (0, 30, layer_z(-1)),
                orient((-1, 0, 0), (0, 0, 1), (0, 1, 0)), tag="teeth")
    mouth.step("Two corner plates on the teeth plate's studs, round the open mouth")
    mouth.place("2420", "rind", (*cell(0, 1), layer_z(0)),
                orient((1, 0, 0), (0, 0, 1), (0, -1, 0)))        # the left arm goes up
    mouth.place("2420", "rind", (*cell(3, 1), layer_z(0)),
                orient((0, -1, 0), (0, 0, 1), (-1, 0, 0)))       # the right arm goes up
    mouth.step("A plate on each upper corner and a 1 x 2 plate along the bottom")
    mouth.place("3024", "rind", (*cell(0, 0), layer_z(1)), OUT)
    mouth.place("3024", "rind", (*cell(3, 0), layer_z(1)), OUT)
    mouth.place("3023", "rind", (0, cell(1, 1)[1], layer_z(1)), OUT)

    # ---- the eyes panel (steps 14-16) ----
    eyes = model.submodel("eyes", "Eyes panel")
    eyes.step("A 2 x 4 plate with a 1 x 2 plate on its top middle")
    eyes.place("3020", "rind", (0, 20, layer_z(0)), OUT)
    eyes.place("3023", "rind", (0, cell(1, 0)[1], layer_z(1)), OUT)
    eyes.step("Two 1 x 2 plates with a stud in the middle, along the bottom row")
    for x in (-20, 20):
        eyes.place("3794b", "rind", (x, cell(0, 1)[1], layer_z(1)), OUT)
    eyes.step("A black tile on each stud: the eyes")
    for x in (-20, 20):
        eyes.place("3070b", "eye", (x, cell(0, 1)[1], layer_z(2)), OUT, tag="eyes")

    # ---- a side panel, four rows of four studs, built three times (steps 19-21) ----
    side = model.submodel("side", "Side panel")
    side.step("A 4 x 4 plate with a 2 x 4 plate across its middle rows")
    side.place("3031", "rind", (0, 40, layer_z(0)), OUT)
    side.place("3020", "rind", (0, 40, layer_z(1)), OUT)
    side.step("A 1 x 2 plate on the top row and another on the bottom row")
    for row in (0, 3):
        side.place("3023", "rind", (0, cell(1, row)[1], layer_z(1)), OUT)
    side.step("A 2 x 2 plate in the middle")
    side.place("3022", "rind", (0, 40, layer_z(2)), OUT)

    # ---- the stem (step 30): a plate with a handle, a leaf clipped on it ----
    stem = model.submodel("stem", "Stem")
    stem.step("A leaf clipped on the handle of a round plate")
    stem.place("26047", "stem", (0, 0, 0), None)
    stem.place("16770", "leaf", (0, 2, -20), rot(x=-75))

    # ---- the head half, the right way up, drawn upside down in the plans (steps 9-13) ----
    head = model.submodel("head", "Head half")
    head.step("The top: a 4 x 4 plate (it is built upside down, studs down)")
    head.place("3031", "rind", (0, LID, 0))
    head.step("Four bricks with studs on two sides, one in each corner, studs out")
    for sx in (-1, 1):
        for sz in (-1, 1):
            head.place("26604", "core", (30 * sx, CROWN, 30 * sz), side_studs(sx, sz, False))
    head.step("A grey 4 x 4 plate across them and a 2 x 2 plate under its middle")
    head.place("3031", "core", (0, FLOOR, 0))
    head.place("3022", "core", (0, HANG2, 0), insert=(0, 1, 0))      # pushed up from below
    head.step("Two 1 x 4 plates, grey then orange, under the front edge")
    head.place("3710", "core", (0, HANG2, -30))
    head.place("3710", "rind", (0, HANG1, -30), insert=(0, 1, 0))
    head.step("The green stem base: a corner tile and a 1 x 1 plate")
    head.place("14719", "stem", (10, GREEN, -10), orient((0, 0, 1), (0, 1, 0)))
    head.place("3024", "stem", (-10, GREEN, 10))
    head.step("The eyes panel goes on the front of the head")
    head.use(eyes, (0, y_at(88), -FACE))

    # ---- the base half, built upside down on two tiles (steps 1-4) ----
    m.step("Two 2 x 4 tiles side by side, smooth side down")
    for z in (-20, 20):
        m.place("87079", "rind", (0, TILES, z), FLIP)

    m.step("Four bricks with studs on two sides in the corners, studs out, and a 2 x 4 brick")
    for sx in (-1, 1):
        for sz in (-1, 1):
            m.place("26604", "core", (30 * sx, POSTS, 30 * sz), side_studs(sx, sz, True))
    m.place("3001", "core", (0, POSTS, 0), FLIP)

    m.step("A 2 x 4 plate along the back, and two corner plates leaving the front open")
    m.place("3020", "core", (0, DECK, 20), FLIP)
    m.place("2420", "core", (-30, DECK, -10), FLIP)
    m.place("2420", "core", (30, DECK, -10), orient((0, 0, -1), (0, -1, 0)))

    m.step("A 2 x 2 plate in the middle")
    m.place("3022", "core", (0, CAP, 0), FLIP)

    m.step("The mouth panel goes on the front of the base")
    m.use(mouth, (0, y_at(48), -FACE))

    m.step("The head half sits on the base, and a side panel across the back ties them")
    m.use(head, (0, 0, 0), insert=(0, -1, 0))
    m.use(side, (0, y_at(88), FACE), rot(y=180), tag="side_back")

    m.step("A side panel on each side")
    m.use(side, (FACE, y_at(88), 0), rot(y=-90), tag="side_right")
    m.use(side, (-FACE, y_at(88), 0), rot(y=90), tag="side_left")

    m.step("The stem on the green plate")
    m.use(stem, (-10, STEM, 10), tag="stem")
