"""Garfield: a Quick Bricks model, zeldar's design, built as zeldar's instructions build it
(reference/: the app's picture, its parts list and its 18 pages, as screenshots). Each step
here is a page there, with one change of order: page 6 puts a 1 x 1 brick with a side stud on
its side under each end of the face, but nothing holds them until the curved slopes go on at
page 12, so here each goes onto its curved slope first (a small sub-assembly, one a side) and
the pair goes on at page 12 (NOTES.md). Every page was checked by laying a render from the
app's camera over it (orthographic, 45 degrees round, 30 up).

Frame: LDU (stud 20, plate 8, brick 24), -Y up, the front faces -Z. The table is y = 0, under
the two 1 x 1 plates the head stands on; the head is centred on x = 0. Colours are palette
roles from model.toml.

How it goes together: a one-stud column (two 1 x 1 plates and a brick with a side stud: the
nose's stud) carries a 1 x 3 plate. Under its ends hang two brackets whose plates stand up in
front, two studs each: the eyelids and the eyes. Small brackets on the 1 x 3's ends hold
brackets facing out to the sides; on their studs and on bricks on their sides go the curved
slopes (the jowls) and cheese slopes (the temples). The ears hang on studs at the back; the
cheeks each turn on one stud, tipped in towards the nose."""
import numpy as np

from brickkit.ldraw.matrix import rot

PLATE, BRICK = 8, 24
EX, EY, EZ = np.eye(3)


def axes(x, y, z):
    """A rotation given by where a part's own X, Y and Z axes point."""
    return np.column_stack((x, y, z)).astype(float)


TOP_OUT = {1: axes(EY, -EX, EZ),     # on its side, its top (and top stud) out to the right
           -1: axes(-EY, EX, EZ)}    # (+X) or to the left (-X)
OUT = {1: axes(EZ, EY, -EX),         # a 79389 bracket, its plate hanging down the right side,
       -1: axes(-EZ, EY, EX)}        # studs out; and the left one
JOWL = {1: axes(EZ, -EX, -EY),       # a curved slope on its side, underside in, thick end up:
        -1: axes(-EZ, EX, -EY)}      # its two holes (one a plate deeper) on two side studs
TEMPLE = {1: axes(-EZ, -EX, EY),     # a cheese slope on a side stud, its thin end down
          -1: axes(EZ, EX, EY)}
FRONT = axes(EX, EZ, -EY)            # a tile on a front stud, top to the front: the eyes'
#                                      print upright, the cheeks' flat edge up
LID = axes(-EX, EZ, EY)              # a 1 x 1 tile with a round end on a front stud, round end up
EAR = axes(EX, -EZ, EY)              # a 1 x 1 plate with a tooth on a back stud, the tooth up
CHEEK_TURN = 15                      # each cheek turned on its stud, its inner end down

SIDE = 34                            # the outer faces of the side bricks and brackets
COL = -40                            # the top of the middle brick; the 1 x 3 plate sits on it
TOP = COL - PLATE                    # the top of the 1 x 3 plate


def build(model):
    m = model.main

    # Pages 1-3: the column and the plate across it
    m.step("Two 1 x 1 plates, one on the other")
    m.place("3024", "orange", (0, -PLATE, 0), tag="column")
    m.place("3024", "orange", (0, -2 * PLATE, 0), tag="column")
    m.step("A 1 x 1 brick with a stud on its side, the stud to the front")
    m.place("87087", "orange", (0, COL, 0), tag="column")
    m.step("A 1 x 3 plate across it")
    m.place("3623", "orange", (0, TOP, 0), tag="column")

    # Pages 4-5: the face brackets under the plate's ends
    m.step("Under each end of the 1 x 3 a bracket, its plate standing up in front, studs to "
           "the front")
    for x in (-20, 20):
        m.place("73825", "orange", (x, COL, 0), tag="face")
    m.step("A 1 x 1 plate under each bracket")
    for x in (-20, 20):
        m.place("3024", "orange", (x, COL + PLATE, 0), tag="face")

    # Pages 7-8: small brackets facing back on the 1 x 3's ends, and the middle
    m.step("On each end of the 1 x 3 a small bracket, its plate at the back, stud to the back")
    for x in (-20, 20):
        m.place("36840", "orange", (x, TOP - PLATE, 0), rot(y=180), tag="back")
    m.step("Two 1 x 1 plates on the middle of the 1 x 3")
    m.place("3024", "orange", (0, TOP - PLATE, 0), tag="column")
    m.place("3024", "orange", (0, TOP - 2 * PLATE, 0), tag="column")

    # Pages 9-11: the sides and the ears
    m.step("On each small bracket a bracket whose plate hangs down the side, studs out")
    for s in (-1, 1):
        m.place("79389", "orange", (20 * s, TOP - 2 * PLATE, 0), OUT[s], tag="side")
    m.step("The ears: a 1 x 1 plate with a tooth on each back stud, the tooth up")
    for s in (-1, 1):
        m.place("49668", "ear", (20 * s, TOP - 10, 22), EAR, tag="ears")
    m.step("A 1 x 1 plate on each side bracket's lower stud")
    for s in (-1, 1):
        m.place("3024", "orange", (s * (SIDE + PLATE), COL + 6, 0), TOP_OUT[s], tag="side")

    # Page 12 (and page 6): the jowls. zeldar's page 6 puts the two bricks on their sides
    # under the face brackets' plates, but nothing holds them until the curved slopes go on
    # at page 12: here each brick goes onto its curved slope first, and the two on together
    for s, side in ((-1, "left"), (1, "right")):
        jowl = model.submodel(f"jowl_{side}", f"The {side} jowl")
        jowl.step("A curved slope, and a 1 x 1 brick with a side stud on its lower hole, the "
                  "brick's side stud to the front")
        jowl.place("11477", "orange", (SIDE * s, COL + 16, 0), JOWL[s], tag="jowls")
        jowl.place("87087", "orange", (SIDE * s, COL + 26, 0), TOP_OUT[s], tag="side")
        if s < 0:
            m.step("The jowls: each on the side, its upper hole on the plate's stud, the brick "
                   "tucked under the face bracket's plate")
        m.use(jowl, tag="jowls", insert=(s, 0, 0))

    # Pages 13-14: the temples and the top
    m.step("A cheese slope on each side bracket's upper stud")
    for s in (-1, 1):
        m.place("54200", "orange", (SIDE * s, TOP - 6, 0), TEMPLE[s], tag="temples")
    m.step("A 1 x 3 tile on top")
    m.place("63864", "orange", (0, TOP - 3 * PLATE, 0), tag="top")

    # Pages 15-18: the face
    m.step("The eyelids: a 1 x 1 tile with a round end on each upper stud, round end up")
    for s in (-1, 1):
        m.place("24246", "orange", (20 * s, COL - 22, -22), LID, tag="eyelids")
    m.step("The nose: a pink round tile on the middle brick's stud")
    m.place("98138", "nose", (0, COL + 10, -18), FRONT, tag="nose")
    m.step("The eyes, under the eyelids")
    for s in (-1, 1):
        m.place("98138p2l", "white", (20 * s, COL - 2, -22), FRONT, tag="eyes")
    m.step("The cheeks: a half round tile on each side brick's stud, flat edge up, turned "
           "so its inner end dips under the nose")
    for s in (-1, 1):
        m.place("1748", "cheek", (24 * s, COL + 26, -18), rot(z=-s * CHEEK_TURN) @ FRONT,
                tag="cheeks")
