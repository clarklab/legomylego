"""The 23-piece taco in LEGO Classic 11039, PDF 6555451 pp. 34–41.

All 12 source steps, including both hidden white plates and the hidden Coral
brick. The source builds the taco flat and stands it up on p. 41. Coordinates
below follow that flat build; place() turns everything upright for the repo's
finished model, with the eye-covered shell facing -Z and its straight edge down.
"""
import numpy as np
from brickkit.ldraw.matrix import rot

UPRIGHT = rot(x=90)
OFFSET = np.array((0, -40, 12))


def build(model):
    m = model.main

    def place(part, color, pos, rotation=None, tag=""):
        R = np.eye(3) if rotation is None else rotation
        return m.place(part, color, tuple(UPRIGHT @ np.asarray(pos) + OFFSET), UPRIGHT @ R, tag=tag)

    m.step("1 · The first curved shell corner")
    place("30565", "shell", (-40, 0, 0), rot(y=180), "back_left_shell")

    m.step("2 · The eight-stud folded edge")
    place("3008", "shell", (0, -24, -30), tag="fold")

    m.step("3 · Complete the back shell")
    place("30565", "shell", (40, 0, 0), rot(y=-90), "back_right_shell")

    m.step("4 · Lettuce filling and two red round plates")
    place("3010", "filling", (0, -24, -10), tag="inner_lettuce")
    for side in (-1, 1):
        place("85861", "tomato", (side * 50, -8, -10), tag=f"red_plate_{side}")

    m.step("5 · The hidden coral brick and two white side-stud bricks")
    for side in (-1, 1):
        place("87087", "white", (side * 30, -24, 10), rot(y=180), f"filling_mount_{side}")
    place("3004", "inner", (0, -24, 10), tag="hidden_coral_brick")

    m.step("6 · Curved green and brown fillings")
    place("49307", "filling", (30, -14, 20), rot(x=-90), "green_filling")
    place("49307", "meat", (-30, -14, 20), rot(x=-90), "brown_filling")

    m.step("7 · A curved tomato slice")
    place("37352", "tomato", (0, -24, 30), rot(y=180), "tomato_slice")

    m.step("8 · Two lettuce leaves at the edges")
    place("32607", "leaf", (-50, -8, 10), rot(y=180), "lower_left_leaf")
    place("32607", "leaf", (50, -8, 10), rot(y=-90), "lower_right_leaf")

    m.step("9 · White round plates between the leaves")
    for side in (-1, 1):
        place("85861", "white", (side * 50, -16, 10), tag=f"white_plate_{side}")

    m.step("10 · A second pair of lettuce leaves")
    place("32607", "leaf", (-50, -24, 10), rot(y=180), "upper_left_leaf")
    place("32607", "leaf", (50, -24, 10), rot(y=-90), "upper_right_leaf")

    m.step("11 · Close the front shell")
    place("30565", "shell", (-40, -32, 0), rot(y=180), "front_left_shell")
    place("30565", "shell", (40, -32, 0), rot(y=-90), "front_right_shell")

    m.step("12 · The nose and happy closed eyes")
    place("15573", "shell", (0, -40, -30), tag="nose")
    for side in (-1, 1):
        place("98138p2n", "white", (side * 30, -40, -10), tag=f"eye_{side}")
