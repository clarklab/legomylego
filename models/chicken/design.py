"""Chicken: a Quick Bricks model, zeldar's design, built as zeldar's instructions build it
(reference/: the app's picture, hero.png the Brickit page's large picture, the parts list and
the 22 pages as screenshots). One step here per page.

Frame: LDU (stud 20, plate 8, brick 24), -Y up, the front (the beak) faces -Z. The table is
y = 0, where the feet stand; the body's 3 x 3 plate is centred on x = z = 0. Colours are
palette roles from model.toml."""
import numpy as np

from brickkit.ldraw.matrix import rot

PLATE, BRICK = 8, 24
EX, EY, EZ = np.eye(3)


def axes(x, y, z):
    """A rotation given by where a part's own X, Y and Z axes point."""
    return np.column_stack((x, y, z)).astype(float)


T0 = -52                    # the top of the 3 x 3 plate: its underside is 44 above the table
T1 = T0 - BRICK             # the top of the first layer of bricks
LZ = -12                    # the legs' feet, front to back (z of the foot's stud)

STUD_BACK = rot(y=180)                    # a bracket's side studs to the back (+Z)
FLAT_BACK = axes(EX, -EZ, EY)             # a plate standing up, its stud to the back (+Z), and
#                                           a bracket's flange, so turned, lying flat, stud up
SIDE = {1: rot(y=-90), -1: rot(y=90)}     # a side stud (87087) out to +X / -X
FWD = axes(EX, EZ, -EY)                   # upright, studs (or a tile's face) forward (-Z)
FLIP = rot(z=180)                         # upside down
EYES = "3069bpx3"                         # Tile 1 x 2 with 2 Black Squares (the Minecraft
#                                           chicken's eyes: Rebrickable 3069bpr0250)
EYE_TURN = FWD                            # the squares at the bottom, as on page 20
EYE_X = 10                                # zeldar centres the face tile on the upper brick's
#                                           top stud, which is solid: a 1 x 2 tile's centre pin
#                                           cannot go in it. Half a stud over, one of the tile's
#                                           own stud places is on it and it holds


def build(model):
    m = model.main

    m.step("A white 3 x 3 plate")
    m.place("11212", "white", (0, T0, 0), tag="body")

    m.step("Turn it over. Two yellow brackets on its underside, one under each side of the middle "
           "row, their flanges flat on the plate, studs in, their plates hanging down")
    for x in (-20, 20):
        m.place("36841", "yellow", (x, -30, LZ + 22), FLAT_BACK, tag="legs")
    m.step("A yellow bracket on each, by the upper of its two studs: the leg, its plate the foot")
    for x in (-20, 20):
        m.place("73825", "yellow", (x, -8, LZ), STUD_BACK, tag="legs")
    m.step("A yellow 1 x 1 tile on each leg's lower stud, at the back")
    for x in (-20, 20):
        m.place("3070b", "yellow", (x, -10, LZ + 22), FLAT_BACK, tag="legs")

    m.step("Turn it back. Two bricks with a side stud on the middle row, the studs out to the "
           "sides: they hold the wings")
    for x in (-20, 20):
        m.place("87087", "white", (x, T1, 0), SIDE[int(np.sign(x))], tag="body")
    m.step("A 1 x 3 brick along the front and one along the back")
    for z in (-20, 20):
        m.place("3622", "white", (0, T1, z), tag="body")

    m.step("A brick with a headlight in the middle of the front, the headlight forward")
    m.place("4070", "white", (0, T1 - BRICK, -20), tag="body")
    m.step("A 1 x 1 plate on each side of it")
    for x in (-20, 20):
        m.place("3024", "white", (x, T1 - PLATE, -20), tag="body")
    m.step("A 2 x 3 plate behind them")
    m.place("3021", "white", (0, T1 - PLATE, 10), tag="body")

    m.step("The wings: a 2 x 2 plate on each side stud, studs out, centred on it: the stud goes "
           "up into the tube in the middle of the plate's underside")
    m.place("3022", "white", (38, T1 + 10, 0), axes(EY, -EX, EZ), tag="wings")
    m.place("3022", "white", (-38, T1 + 10, 0), axes(EY, EX, -EZ), tag="wings")

    # The head: on the headlight's stud, a brick with studs on two sides, its own top stud
    # forward and its side studs out to the sides
    HY = T1 - BRICK + 10                     # the headlight stud's height
    HZ = -50                                 # the lower head brick's top: its stud forward
    CUBE = axes(EY, EZ, EX)
    m.step("The head: a brick with studs on two sides on the headlight's stud, its top forward")
    m.place("47905", "white", (0, HY, HZ), CUBE, tag="head")
    m.step("A 2 x 2 plate on its left side stud, studs out: the side of the head")
    m.place("3022", "white", (-18, HY - 10, HZ), axes(-EY, EX, EZ), tag="head")
    # Pages 13 and 14: the upper brick, then two 1 x 1 plates behind it. With the brick on, the
    # plates have to slide in from the side and then press forward onto it (the headlight
    # brick's top stud is right behind them), a move the checks and the video cannot make.
    # Here the plates go on the brick first and the three go on together, from the right side
    # (plates and tiles stand upright, studs forward (FWD); a plate's back is 8 behind its top)
    top = model.submodel("head_top", "The upper head brick")
    top.step("A brick with studs on two sides, and two 1 x 1 plates on its bottom")
    top.place("47905", "white", (0, HY - 20, HZ - 20), CUBE, tag="head")
    for zb in (-46, -38):
        top.place("3024", "white", (0, HY - 20, zb), FWD, tag="head")
    m.step("The upper brick, top forward, in the plate's upper front hole: a stud higher and a "
           "stud further forward than the first, its plates reaching back to the headlight")
    m.use(top, tag="head", insert=(1, 0, 0))
    m.step("A 1 x 1 plate on the lower brick's stud")
    m.place("3024", "white", (0, HY, HZ - PLATE), FWD, tag="head")
    m.step("The wattle: a red bracket, its plate on the 1 x 1 plate's stud and its other plate "
           "flat underneath, reaching forward")
    m.place("36840", "red", (0, HY, HZ - 2 * PLATE), FWD, tag="wattle")
    m.step("A red 1 x 1 plate upside down on the bracket's stud underneath")
    m.place("3024", "red", (0, HY + 22, HZ - 2 * PLATE - 2), FLIP, tag="wattle")
    m.step("A white 1 x 1 plate on the red bracket's stud")
    m.place("3024", "white", (0, HY, HZ - 3 * PLATE), FWD, tag="head")
    m.step("A 2 x 2 plate on the right side studs of the two bricks: the other side of the head")
    m.place("3022", "white", (18, HY - 10, HZ), axes(EY, -EX, EZ), tag="head")
    m.step("The eyes: a 1 x 2 tile printed with two black squares on the upper brick's stud, by "
           "one end, reaching out to the right")
    m.place(EYES, "white", (EYE_X, HY - 20, HZ - 20 - PLATE), EYE_TURN, tag="eyes")
    m.step("The beak: an orange 1 x 2 jumper plate on the white 1 x 1 plate's stud")
    m.place("15573", "orange", (0, HY, HZ - 4 * PLATE), FWD, tag="beak")
    m.step("An orange 1 x 2 tile on the jumper's stud")
    m.place("3069b", "orange", (0, HY, HZ - 5 * PLATE), FWD, tag="beak")

