"""The 23-piece avocado in LEGO Classic 11039, PDF 6555451 pp. 22–31.

One main step per numbered LEGO step. Steps 6 and 7 each include the separate
inverted-slope/brick cheek callout shown in the PDF. -Y is up; the face is -Z.
The source inventory and exact printed element IDs are in reference/inventory.json.
"""
from brickkit.ldraw.matrix import rot


def build(model):
    m = model.main
    m.step("1 · The lime base")
    m.place("3020", "flesh", tag="base")

    m.step("2 · The centre of the avocado")
    m.place("3003", "flesh", (0, -24, 0), tag="lower_centre")

    m.step("3 · The two back corners slope inward")
    m.place("3665b", "flesh", (-30, -24, 10), rot(y=90), tag="back_left_corner")
    m.place("3665b", "flesh", (30, -24, 10), rot(y=-90), tag="back_right_corner")

    m.step("4 · Join the back with a six-stud brick")
    m.place("3009", "flesh", (0, -48, 10), tag="back")

    m.step("5 · The stud for the stone")
    m.place("86876", "flesh", (0, -48, -10), tag="stone_mount")

    for number, side, angle in ((6, 1, -90), (7, -1, 90)):
        cheek = model.submodel(f"cheek_{number}", f"Step {number}: build the {'right' if side == 1 else 'left'} cheek")
        cheek.step("Stack the brick on the inverted slope")
        cheek.place("3665b", "flesh", (0, 0, 0), rot(y=angle), tag="corner")
        cheek.place("3004", "flesh", (side * 10, -24, 0), tag="brick")
        m.step(f"{number} · Attach the {'right' if side == 1 else 'left'} cheek")
        m.use(cheek, (side * 30, -24, -10), tag=f"cheek_{number}")

    m.step("8 · A square brick above the stone")
    m.place("3003", "flesh", (0, -72, 0), tag="upper_centre")

    m.step("9 · Round off both shoulders")
    m.place("3039", "flesh", (-30, -72, 0), rot(y=90), tag="left_shoulder")
    m.place("3039", "flesh", (30, -72, 0), rot(y=-90), tag="right_shoulder")

    m.step("10 · The round brown stone")
    m.place("67095", "stone", (0, -38, -28), rot(x=90), tag="stone")

    m.step("11 · Build the back of the head")
    m.place("3010", "flesh", (0, -96, 10), tag="head_back")

    m.step("12 · A smile between the eye studs")
    m.place("87087", "flesh", (-30, -96, -10), tag="left_eye_mount")
    m.place("87087", "flesh", (30, -96, -10), tag="right_eye_mount")
    m.place("3004p0g", "flesh", (0, -96, -10), tag="smile")

    m.step("13 · Two squeezed-shut eyes")
    m.place("98138p2o", "eyes", (-30, -86, -28), rot(x=90) @ rot(y=180), tag="left_eye")
    m.place("98138p2o", "eyes", (30, -86, -28), rot(x=90), tag="right_eye")

    m.step("14 · The tapered top")
    m.place("3039", "flesh", (-10, -120, 0), rot(y=90), tag="left_crown")
    m.place("3039", "flesh", (10, -120, 0), rot(y=-90), tag="right_crown")

    m.step("15 · Finish with the green stem cap")
    m.place("18674", "stem", (0, -128, 0), tag="stem")
