"""Stormtrooper PEZ: our own brick version of the sweet dispenser, as near its real size as
bricks allow (10.6 cm tall), on the stem all three of our PEZ models share
(brickkit/designs/pez.py: the foot, the stem, the hinge the head tips back on, the sweet).

The head is in its own frame: y = 0 is its underside, the face looks to -Z. Colours are
palette roles from model.toml."""
from brickkit.designs.pez import (CORE, ROWS, RIGHT, build_cheek, build_stem, cheek_bricks,
                                  dome_slopes, dome_top, head_face_bricks, head_hinge,
                                  head_mount, mount_head, on_front, place_cheeks, y)
from brickkit.ldraw.matrix import rot

ALONG = RIGHT @ rot(y=90)         # a 1 x 2 tile on a cheek's studs, running front to back


def build(model):
    cheek = build_cheek(model)
    cheek.step("A cheek: two tall bricks side by side, studs to the same side. Join them with "
               "a white 1 x 2 tile on the upper studs and a grey grille tile on the lower. "
               "Make two")
    cheek_bricks(cheek)
    cheek.place("3069b", "head", (18, y(30), 0), ALONG, tag="cheek")
    cheek.place("2412b", "grey", (18, y(10), 0), ALONG, tag="vents")

    head = model.submodel("head", "Head")
    head.step("The face: three tall bricks side by side, studs forward, joined by a white "
              "1 x 3 plate across their lower studs")
    head_face_bricks(head)
    on_front(head, "3623", "head", 0, 10, tag="snout")
    head.step("On that plate: the black frown in the middle, its round side up, and a grey "
              "round tile either side")
    on_front(head, "24246", "black", 0, 10, turn=180, out=8, tag="frown")
    for x in (-20, 20):
        on_front(head, "98138", "grey", x, 10, out=8, tag="vents")
    head.step("On the upper studs: the eyes, two black quarter-round tiles with their round "
              "corners down and out, and a white tile between them")
    on_front(head, "25269", "black", 20, 30, tag="eyes")
    on_front(head, "25269", "black", -20, 30, turn=90, tag="eyes")
    on_front(head, "3070b", "head", 0, 30)
    head.step("Stand a cheek each side behind the face, grilles out, and the last tall brick "
              "between them at the back, studs to the back. Press the 3 x 3 plate down on "
              "all of them")
    place_cheeks(head, cheek)
    head_mount(head)
    head.place("11212", "head", (0, y(CORE + 8), ROWS[1]), tag="crown")
    head.step("The brow: a black 1 x 3 plate along the front, a white 2 x 3 plate behind it")
    head.place("3623", "black", (0, y(CORE + 16), ROWS[0]), tag="brow")
    head.place("3021", "head", (0, y(CORE + 16), (ROWS[1] + ROWS[2]) / 2), tag="crown")
    head.step("The dome: four curved slopes round the edge, each with its thick end at the "
              "middle of a side")
    dome_slopes(head, "head", CORE + 16)
    head.step("A plate and a tile in the middle of the dome")
    dome_top(head, CORE + 16)
    head.step("The head's hinge plate, the one with a single finger: upright on the two studs "
              "at the back, finger down")
    head_hinge(head)

    build_stem(model)
    mount_head(model, head)
