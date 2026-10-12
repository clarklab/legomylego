"""Darth Vader PEZ: our own brick version of the sweet dispenser, as near its real size as
bricks allow (10.6 cm tall), on the stem all three of our PEZ models share
(brickkit/designs/pez.py: the foot, the stem, the hinge the head tips back on, the sweet).

The head is in its own frame: y = 0 is its underside, the face looks to -Z. Colours are
palette roles from model.toml."""
from brickkit.designs.pez import (CORE, ROWS, RIGHT, build_cheek, build_stem, cheek_bricks,
                                  dome_slopes, dome_top, head_face_bricks, head_hinge,
                                  head_mount, mount_head, on_front, place_cheeks, y)
from brickkit.ldraw.matrix import rot


def build(model):
    cheek = build_cheek(model)
    cheek.step("A cheek: two tall bricks side by side, studs to the same side, joined by a "
               "black curved 2 x 2 slope over their four studs, its thick end down (it grips "
               "the upper two): the flare of the helmet. Make two")
    cheek_bricks(cheek)
    cheek.place("15068", "head", (10, y(20), 0), RIGHT @ rot(y=90), tag="flare")

    head = model.submodel("head", "Head")
    head.step("The mask: three tall bricks side by side, studs forward, joined by a dark grey "
              "1 x 3 plate across their lower studs")
    head_face_bricks(head)
    on_front(head, "3623", "mask", 0, 10, tag="snout")
    head.step("On that plate: the silver plate with a tooth in the middle, tooth down, and a "
              "black tile either side")
    on_front(head, "49668", "silver", 0, 10, out=8, tag="mouth")
    for x in (-20, 20):
        on_front(head, "3070b", "head", x, 10, out=8, tag="snout")
    head.step("On the upper studs: the eyes, two black round tiles, and between them a dark "
              "grey cheese slope, its high edge up")
    for x in (-20, 20):
        on_front(head, "98138", "head", x, 30, tag="eyes")
    on_front(head, "54200", "mask", 0, 30, slope=True, tag="nose")
    head.step("Stand a cheek each side behind the mask, flares out, and the last tall brick "
              "between them at the back, studs to the back. Press a 3 x 3 plate down on all "
              "of them")
    place_cheeks(head, cheek)
    head_mount(head)
    head.place("11212", "head", (0, y(CORE + 8), ROWS[1]), tag="crown")
    head.step("A second 3 x 3 plate: the helmet's brim")
    head.place("11212", "head", (0, y(CORE + 16), ROWS[1]), tag="crown")
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
