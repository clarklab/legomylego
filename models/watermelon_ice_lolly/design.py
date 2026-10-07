"""LEGO 11039 watermelon ice lolly, official PDF 6555451, pages 14–19.

23 pieces, retaining all eleven numbered steps. The three seeds and the stick
are genuine subassemblies shown in the official yellow instruction insets.
The four-stud-wide face points toward -Z; -Y is up. Units are LDraw units.
"""
from brickkit.ldraw.matrix import rot

FRONT = rot(x=90)
# The large white highlight is upper left; the smaller highlight is lower right.
EYE = FRONT @ rot(y=45)


def build(model):
    seed = model.submodel("seed", "A watermelon seed")
    seed.step("Press the black round tile onto the coral side stud")
    seed.place("86876", "flesh", tag="seed_brick")
    seed.place("98138", "seed", (0, 10, -18), FRONT, tag="seed_tile")

    stick = model.submodel("stick", "The lolly stick")
    stick.step("Stack the two tan round bricks")
    stick.place("3941", "stick", tag="stick_top")
    stick.place("3941", "stick", (0, 24, 0), tag="stick_bottom")

    m = model.main
    m.step("1 · The rind: white plate on the lime brick")
    m.place("3001", "rind", tag="rind")
    m.place("3020", "pith", (0, -8, 0), tag="pith")

    m.step("2 · The back of the first coral row")
    m.place("3010", "flesh", (0, -32, 10), tag="lower_back")

    m.step("3 · Build two seeds and place them across the front")
    m.use(seed, (-20, -32, -10), tag="seed_left")
    m.use(seed, (20, -32, -10), tag="seed_right")

    m.step("4 · Build the third seed and centre it above the first two")
    m.use(seed, (0, -56, -10), tag="seed_middle")

    m.step("5 · Complete the second coral row with three bricks")
    m.place("3004", "flesh", (-30, -56, 0), rot(y=90), tag="middle_left")
    m.place("3004", "flesh", (30, -56, 0), rot(y=90), tag="middle_right")
    m.place("3004", "flesh", (0, -56, 10), tag="middle_back")

    m.step("6 · Add the smiling brick and the long brick behind it")
    m.place("3010", "flesh", (0, -80, 10), tag="upper_back")
    m.place("3004p0g", "flesh", (0, -80, -10), tag="smile")

    m.step("7 · Add the two bricks with studs facing forward")
    for x, side in ((-30, "left"), (30, "right")):
        m.place("87087", "flesh", (x, -80, -10), tag=f"eye_brick_{side}")

    m.step("8 · Press the printed eyes onto the front studs")
    for x, side in ((-30, "left"), (30, "right")):
        m.place("98138p2j", "eye", (x, -70, -28), EYE, tag=f"eye_{side}")

    m.step("9 · Centre the square brick on top")
    m.place("3003", "flesh", (0, -104, 0), tag="crown")

    m.step("10 · Round off the two top corners")
    m.place("37352", "flesh", (-30, -104, 0), rot(y=90), tag="curve_left")
    m.place("37352", "flesh", (30, -104, 0), rot(y=-90), tag="curve_right")

    m.step("11 · Stack the tan round bricks and attach the stick underneath", view="below")
    m.use(stick, (0, 24, 0), tag="stick", insert=(0, 1, 0))
