"""Moby Dick: a Quick Bricks model, d.e.n.n.i.s's design, built as d.e.n.n.i.s's instructions
build it (reference/: the app's parts list and its 11 pages, as screenshots, and the app's
picture of the model). Each step here is a page there. Every page was checked by laying a render
from the app's camera over it (ortho, 45 degrees round, 30 up).

Frame: LDU (stud 20, plate 8, brick 24), -Y up, the front faces -Z. The sea (the blue 4 x 12
plate) lies front to back, its top at y = 0, centred on x = 0 and z = 0. The whale swims to the
front (-Z), two studs wide (x = -20 .. 20) and eight long (z = -100 .. 60), with its tail on the
plate behind it. Colours are palette roles from model.toml.

How it goes together: a 2 x 4 brick is the body. A 1 x 1 brick with a stud on its side in front
of it on each side carries an eye, and two 1 x 2 plates stacked in front of those are the snout.
At the back, two more stacked plates and a 1 x 2 slope taper it. A curved slope goes over each
end: its high end's underside is a plate higher than its low end's, so it sits on the bricks
and the plates at once, low end out (the nose; the back). Between them on top, a jumper (the
blowhole) and a 2 x 2 tile. Behind the whale, two cheese slopes sloping towards each other are
the flukes of its tail, coming up out of the sea."""
import numpy as np

from brickkit.ldraw.matrix import rot

PLATE, BRICK = 8, 24
EX, EY, EZ = np.eye(3)


def axes(x, y, z):
    """A rotation given by where a part's own X, Y and Z axes point."""
    return np.column_stack((x, y, z)).astype(float)


LENGTH = rot(y=90)          # a part whose length is along its own X, turned to run front to back
TOP = -BRICK                # the top of the bricks
SNOUT = 2 * PLATE           # how high the stacked plates are
EYE_Z = -70                 # the row of the 1 x 1 bricks with a side stud
SIDE_STUD = TOP + 10        # their side studs' height (10 below a brick's top)
EYE_X = 20 + PLATE          # an eye's face: a plate out from the side of the body


def eye_turn(side):
    """An eye on the side stud facing `side` (-1 left, 1 right): the tile's face out, and its
    print turned with the eyelid's line along the bottom and the eye's dome up, as in the app's
    picture (the print's dome is along the tile's own +Z)."""
    return axes(side * EZ, -side * EX, -EY)


def build(model):
    m = model.main

    m.step("The sea: a blue 4 x 12 plate, lying front to back")                     # page 1
    m.place("3029", "sea", (0, 0, 0), LENGTH, tag="sea")

    m.step("The body: a 2 x 4 brick down the middle, a stud in from the front")     # page 2
    m.place("3001", "whale", (0, TOP, -20), LENGTH, tag="body")

    m.step("In front of it a 1 x 1 brick with a stud on its side on each side, "     # page 3
           "the side studs out")
    m.place("87087", "whale", (-10, TOP, EYE_Z), rot(y=90), tag="body")
    m.place("87087", "whale", (10, TOP, EYE_Z), rot(y=-90), tag="body")

    m.step("The snout: two 1 x 2 plates, one on the other, in front of them")       # page 4
    for k in (1, 2):
        m.place("3023", "whale", (0, -k * PLATE, -90), tag="body")

    m.step("Two 1 x 2 plates, one on the other, behind the body")                   # page 5
    for k in (1, 2):
        m.place("3023", "whale", (0, -k * PLATE, 30), tag="body")

    m.step("A 1 x 2 slope behind them, sloping down to the back")                   # page 6
    m.place("85984", "whale", (0, 0, 50), rot(y=180), tag="body")

    m.step("The head: a curved slope over the snout and the side-stud bricks, "     # page 7
           "low end to the front")
    m.place("15068", "whale", (0, -SNOUT, -80), tag="head")

    m.step("On top: a jumper (the blowhole) and a 2 x 2 tile behind it")            # page 8
    m.place("15573", "whale", (0, TOP - PLATE, -50), tag="blowhole")
    m.place("3068b", "whale", (0, TOP - PLATE, -20), tag="back")

    m.step("A curved slope over the back of the body, low end to the back")         # page 9
    m.place("15068", "whale", (0, -SNOUT, 20), rot(y=180), tag="back")

    m.step("The tail: two cheese slopes on the sea behind it, sloping towards "     # page 10
           "each other")
    m.place("54200", "whale", (-10, 0, 90), rot(y=-90), tag="tail")
    m.place("54200", "whale", (10, 0, 90), rot(y=90), tag="tail")

    m.step("The eyes, on the side studs")                                           # page 11
    m.place("98138p2g", "eye", (-EYE_X, SIDE_STUD, EYE_Z), eye_turn(-1), tag="eyes")
    m.place("98138p2g", "eye", (EYE_X, SIDE_STUD, EYE_Z), eye_turn(1), tag="eyes")
