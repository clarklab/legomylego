"""Yoda PEZ: our own brick version of the sweet dispenser, as near its real size as bricks
allow (10.6 cm tall), on the stem all three of our PEZ models share
(brickkit/designs/pez.py: the foot, the stem, the hinge the head tips back on, the sweet).

The head is in its own frame: y = 0 is its underside, the face looks to -Z. Colours are
palette roles from model.toml."""
import numpy as np

from brickkit.designs.pez import (CORE, EY, FRONT, ROWS, RIGHT, build_cheek, build_stem,
                                  cheek_bricks, dome_slopes, dome_top, head_face_bricks,
                                  head_hinge, head_mount, mount_head, on_front, orient,
                                  place_cheeks, y)
from brickkit.ldraw.matrix import rot


def build(model):
    cheek = build_cheek(model)
    cheek.step("A cheek: two tall bricks side by side, studs to the same side, joined by a "
               "green 2 x 2 tile on their four studs. Make two")
    cheek_bricks(cheek)
    cheek.place("3068b", "head", (18, y(20), 0), RIGHT, tag="cheek")

    head = model.submodel("head", "Head")
    head.step("The face: three tall bricks side by side, studs forward, joined by a green "
              "1 x 3 plate across their lower studs")
    head_face_bricks(head)
    on_front(head, "3623", "head", 0, 10, tag="chin")
    head.step("On that plate: a round plate in the middle, the nose, and a tile either side")
    on_front(head, "6141", "head", 0, 10, out=8, tag="nose")
    for x in (-20, 20):
        on_front(head, "3070b", "head", x, 10, out=8, tag="chin")
    head.step("On the upper studs: the two eyes, their glints at the top, and a cheese slope "
              "between them, its high edge up: the brow")
    for x in (-20, 20):
        head.place("98138p2j", "eye", (x, y(30), ROWS[0] - 18), FRONT @ rot(y=45), tag="eyes")
    on_front(head, "54200", "head", 0, 30, slope=True, tag="brow")
    head.step("Stand a cheek each side behind the face, tiles out, and the last tall brick "
              "between them at the back, studs to the back. Press a 2 x 3 plate down on the "
              "front and middle rows, and a 1 x 3 plate on the back row")
    place_cheeks(head, cheek)
    head_mount(head)
    head.place("3021", "head", (0, y(CORE + 8), (ROWS[0] + ROWS[1]) / 2), tag="crown")
    head.place("3623", "head", (0, y(CORE + 8), ROWS[2]), tag="crown")
    head.step("The ears: a 1 x 3 plate each side of the middle row, two studs of it sticking "
              "out, and a 1 x 1 plate between them")
    for side in (-1, 1):
        head.place("3623", "head", (40 * side, y(CORE + 16), ROWS[1]), tag="ears")
    head.place("3024", "head", (0, y(CORE + 16), ROWS[1]), tag="crown")
    head.step("A 1 x 3 plate along the front and one along the back, and a curved slope on "
              "each ear, thin end out: the tip")
    for z in (ROWS[0], ROWS[2]):
        head.place("3623", "head", (0, y(CORE + 16), z), tag="crown")
    for side in (-1, 1):
        u = np.array([-side, 0.0, 0.0])                 # from the thin end to the thick one
        head.place("11477", "head", (50 * side, y(CORE + 16), ROWS[1]), orient(np.cross(EY, u), EY),
                   tag="ears")
    head.step("The top of the head: four curved slopes round the edge, each with its thick "
              "end at the middle of a side")
    dome_slopes(head, "head", CORE + 16)
    head.step("A plate and a tile in the middle")
    dome_top(head, CORE + 16)
    head.step("The head's hinge plate, the one with a single finger: upright on the two studs "
              "at the back, finger down")
    head_hinge(head)

    build_stem(model)
    mount_head(model, head)
