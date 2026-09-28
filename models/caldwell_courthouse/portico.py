"""The entrance portico in front of the front centre pavilion: a stone platform with a step,
two pairs of tan columns with red capitals, a red and tan entablature at the height of the
belt course and a white balustrade on top. It stands on the base (x -60..60, z -320..-280;
the step at z -340..-320) against the front wall."""
from __future__ import annotations

from brickkit.ldraw.matrix import rot, transform
from kit import Batch, PLATE, TILE, rect_M

COLUMNS = [-50, -30, 30, 50]
Z_COL = -310
TOP = -168                     # columns' top (six round bricks from the platform at -24)


def portico_batch() -> Batch:
    b = Batch()
    for y in (0, -8):                                       # platform, two plate layers
        for r in ((-3, 2, -16, -16), (-3, 2, -15, -15)) if y == 0 else ((-3, 2, -16, -15),):
            p, M = rect_M(PLATE, r, y - 8)
            b.add(p, "walk", M, "platform")
    cols = {((x - 10) // 20, -16) for x in COLUMNS}
    floor = {(i, k) for i in range(-3, 3) for k in (-16, -15)} - cols
    for r in ((-2, 1, -16, -16), (-3, 2, -15, -15)):
        cells = {(i, k) for i in range(r[0], r[1] + 1) for k in range(r[2], r[3] + 1)}
        if cells <= floor:
            p, M = rect_M(TILE, r, -24)
            b.add(p, "walk", M, "floor")
    b.add("3666", "walk", transform((0, -8, -330)), "step")         # the step
    b.add("6636", "walk", transform((0, -16, -330)), "step")
    for x in COLUMNS:
        b.add("4073", "trim", transform((x, -24, Z_COL)), "floor")    # bases
        for n in range(6):
            b.add("3062b", "wall", transform((x, -48 - 24 * n, Z_COL)), f"col{n}")
        b.add("4073", "trim", transform((x, TOP - 8, Z_COL)), "caps")
    b.add("3795", "trim", transform((0, TOP - 16, -300)), "entablature")
    b.add("3795", "wall", transform((0, TOP - 24, -300)), "entablature")
    b.add("15332", "balustrade", transform((0, TOP - 72, Z_COL)), "balustrade")
    for x in (-50, 50):
        b.add("3062b", "balustrade", transform((x, TOP - 48, Z_COL)), "balustrade")
        b.add("3062b", "balustrade", transform((x, TOP - 72, Z_COL)), "balustrade")
    return b


PHASES = [["platform"], ["floor", "step"]] + [[f"col{n}"] for n in range(6)] + \
    [["caps"], ["entablature"], ["balustrade"]]
CAPTIONS = {"platform": "The portico: a stone platform in front of the door",
            "floor": "Tiles on it, round plates for the columns, and a step",
            "col0": "Two pairs of columns", "caps": "Red capitals",
            "entablature": "The entablature, red under tan",
            "balustrade": "A white balustrade on top"}


def build(model, main):
    portico_batch().emit(main, PHASES, CAPTIONS, per_step=8)
