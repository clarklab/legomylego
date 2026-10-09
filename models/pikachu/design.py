"""Surprised Pikachu: the head from the "surprised Pikachu" picture, 50 pieces, 7 studs wide.
Wide eyes, red cheeks, a small black nose over an open pink mouth, and two pointed ears with
black tips that swing on clips.

Built from a designer's 9-page instructions (not ours; NOTES.md has the credit, the page-by-page
parts list and what had to be worked out). One step here per page, with one change: page 7
clips the ears' bare clip plates on and page 8 puts a plate under each; here each clip plate
gets that plate first (`ear_base`) and is clipped on in step 8.

Frame: LDU (stud 20, plate 8, brick 24), -Y up, the front faces -Z. x runs to the right as you
face him. The head stands on y = 0; the top of the bracket it is built round is y = TOP.

Almost nothing here is stacked. The face is built forward off a bracket whose 2 x 4 side stands
upright, so the face's studs point at you, in layers one plate (8) apart:

    z = BACK   (-14)  the bracket's studs start here; the backs of the face's plates
    z = PLATES (-22)  the fronts of those plates; the eyes sit this deep
    z = FACE   (-30)  the fronts of the tiles and slopes on them: the skin
    z = NOSE   (-38)  the nose, on the stud of a jumper plate

Behind the bracket the plates face the same way and plug in from behind (their studs go
forward into the backs of the face), out to z = 26.

The small curved slopes (11477, 15068, 29119, 50950) have a step underneath: the thick end sits
one plate higher than the thin end. So each one straddles an edge: its thick end on a plate's
studs, its thin end hanging over that plate's edge, flush with the plate's own underside. The
upside-down one under each ear's tip (24201) is the same shape the other way up: its two studs
are a plate apart in height."""
import math

import numpy as np

PLATE, BRICK = 8, 24

TOP = -80                         # the top of the bracket (its 1 x 2 part); the head's base is 0
BACK, PLATES, FACE, NOSE = -14, -22, -30, -38
REAR = -6                         # the backs of the plates that plug in behind the face
SHELF = 18                        # the backs of the bricks behind those: the last layer goes here

EAR_ANGLE = 36.0                  # degrees the ears rise above level (read off pages 7 to 9)
BAR = (30, 2, 20)                 # an ear's bar: out from the middle, below TOP, back
GLINT = (-1.66, -2.46)            # where the eye tile's white spot is, off its middle (x, z)


def orient(ex, ey) -> np.ndarray:
    """3x3 rotation whose columns are where the part's local X, Y and Z axes point."""
    ex, ey = np.asarray(ex, float), np.asarray(ey, float)
    return np.column_stack([ex, ey, np.cross(ex, ey)])


def front(turn: float = 0.0) -> np.ndarray:
    """A part whose studs point at you (-Z), turned `turn` degrees clockwise as you face it.
    At 0 its own X runs to your right and its own +Z points up."""
    a = math.radians(turn)
    return orient((math.cos(a), math.sin(a), 0.0), (0.0, 0.0, 1.0))


def at(x, y, z):
    """A place in the head: x right, y down from the top of the bracket, z back."""
    return (x, TOP + y, z)


def ear_frame(side: int):
    """Where an ear's clip plate goes (its position and rotation), `side` +1 for the ear on
    your right and -1 for the one on your left: it swings on its bar, up and out, its studs
    facing up and in."""
    a = math.radians(EAR_ANGLE)
    R = orient((-side * math.cos(a), math.sin(a), 0.0), (side * math.sin(a), math.cos(a), 0.0))
    bar = np.array([side * BAR[0], TOP + BAR[1], BAR[2]], float)
    return bar - R @ np.array([30.0, 2.0, 0.0]), R          # the clip is at (30, 2, 0) on the plate


# an ear's pieces in its clip plate's own frame: x runs from the tip (-) to the clip (+),
# -y is the stud side. The plate's own studs are at x = -10 and 10.
ALONG = orient((0, 0, 1), (0, 1, 0))            # a slope with its thick end towards the tip
BACK_ALONG = orient((0, 0, -1), (0, 1, 0))      # and with its thick end towards the clip


def build(model):
    m = model.main

    def ear_piece(side, part, role, pos, R=np.eye(3), **kw):
        O, E = ear_frame(side)
        m.place(part, role, tuple(O + E @ np.asarray(pos, float)), E @ R, **kw)

    # an ear's base, made twice and clipped on in step 8. The plans clip the bare plate on
    # (page 7) and add the plate under it on the next page; by then there is too little room
    # under the ear for the checks (NOTES.md), so here the two go on together
    base = model.submodel("ear_base", "Ear base")
    base.step("An ear's base: a clip plate with a plate under it. Make two")
    base.place("63868", "body", (0, 0, 0))
    base.place("3023", "body", (0, PLATE, 0))

    m.step("A bracket with three 2 x 2 plates on its upright side, and the top of the head")
    m.place("93274", "body", at(0, 0, 0))
    m.place("3023", "body", at(0, -PLATE, 0))                      # lifts the slopes' thick ends
    m.place("50950", "body", at(30, -BRICK, 0), orient((0, 0, 1), (0, 1, 0)))     # falls right
    m.place("50950", "body", at(-30, -BRICK, 0), orient((0, 0, -1), (0, 1, 0)))   # falls left
    m.place("3022", "body", at(0, 20, PLATES), front())            # the middle of the face
    for x in (-40, 40):                                            # a stud lower and further out
        m.place("3022", "body", at(x, 40, PLATES), front())

    m.step("The eyes, the bridge of the nose and the nose")
    glint = math.degrees(math.atan2(-GLINT[1], -GLINT[0]))         # the white spot to your left
    for x in (-30, 30):
        m.place("98138px6", "eye", at(x, 10, PLATES), front(glint), tag="eyes")
    m.place("15068", "body", at(0, 0, BACK), front(180),           # thin end up, over the edge
            insert=(0, 0, -1))                                     # (on before the nose)
    m.place("15573", "body", at(0, 30, FACE), front())
    m.place("25269", "nose", at(0, 30, NOSE), front(45), tag="nose")    # its square corner up

    m.step("Red cheeks, and the curve under each one")
    for x in (-30, 30):
        m.place("3070b", "body", at(x, 30, FACE), front())
    for x in (-50, 50):
        m.place("98138", "cheek", at(x, 30, FACE), front(), tag="cheek")
    m.place("29119", "body", at(-50, 60, BACK), front())           # its cut corner out and down
    m.place("11477", "body", at(-30, 60, BACK), front())
    m.place("15068", "body", at(40, 60, BACK), front())

    m.step("Turn it round: plates behind the face, and the sloping side of the head")
    m.place("3623", "body", at(-50, 30, BACK), front(90))
    m.place("3020", "body", at(0, 60, BACK), front())
    m.place("43720", "body", at(60, 40, BACK), front(180))         # studs forward, wide end down

    m.step("Bricks behind those, and two round corner plates across them all: the jaw")
    m.place("3023", "body", at(50, 40, 10), front(90))             # on the back of the wedge
    m.place("3004", "body", at(-50, 40, REAR), front(90))
    m.place("3701", "body", at(0, 70, REAR), front())
    m.place("68568", "body", at(10, 30, SHELF), front(90))
    m.place("68568", "body", at(-10, 30, SHELF), front(180))

    m.step("Turn it back: a rounded corner beside each eye, and the open mouth")
    m.place("25269", "body", at(-50, 10, PLATES), front(180))      # round corner up and out
    m.place("25269", "body", at(50, 10, PLATES), front(270))
    m.place("3022", "body", at(0, 60, PLATES), front(), insert=(0, 0, -1))   # before its tiles
    m.place("25269", "mouth", at(-10, 50, FACE), front(180), tag="mouth")
    m.place("25269", "mouth", at(-10, 70, FACE), front(90), tag="mouth")
    m.place("3069b", "mouth", at(10, 60, FACE), front(90), tag="mouth")

    m.step("The ears' hinges: a plate pressed up under the top of the head, and two handles")
    m.place("3022", "body", at(0, PLATE, 10), insert=(0, 1, 0))
    for side in (1, -1):
        m.place("26047", "hinge", at(10 * side, 0, 20), orient((0, 0, side), (0, 1, 0)))

    m.step("Clip an ear's base to each handle; add a plate over its end and a curved slope")
    for side in (1, -1):
        O, E = ear_frame(side)
        m.use(base, tuple(O), E, tag="ear")
    for side in (1, -1):
        ear_piece(side, "3023", "body", (-20, -PLATE, 0), tag="ear")        # a stud further out
        ear_piece(side, "11477", "body", (0, 0, 0), ALONG, tag="ear")

    m.step("The black tips: a plate, a curved slope over it and an upside-down one under it")
    for side in (1, -1):
        ear_piece(side, "3024", "tip", (-30, 0, 0), tag="ear_tip")
        ear_piece(side, "11477", "tip", (-40, 0, 0), BACK_ALONG, tag="ear_tip")
        ear_piece(side, "24201", "tip", (-50, 0, 0), BACK_ALONG, tag="ear_tip")
