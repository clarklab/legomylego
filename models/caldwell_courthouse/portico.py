"""The side porches: a stone platform in front of each side entrance, a step, four tan
columns with red capitals across the front, a red and tan entablature and a white
balustrade on top. Built in the front (-Z) frame in front of the set-back entrance bay
(x -80..80, z -500..-460, the step at z -520..-500), and turned to the +X and -X sides;
a pedimented attic stands over each on the roof."""
from __future__ import annotations

from brickkit.ldraw.matrix import rot, transform
from kit import Batch, PLATE, TILE, rect_M

COLUMNS = [-70, -30, 30, 70]
Z_COL = -490
TOP = -168                     # columns' top (six round bricks from the platform at -24)


def porch_batch() -> Batch:
    b = Batch()
    for k in (-25, -24):                                   # platform: 1 x 8s, then 2 x 4s
        p, M = rect_M(PLATE, (-4, 3, k, k), -8)
        b.add(p, "walk", M, "platform")
    for i0 in (-4, 0):
        p, M = rect_M(PLATE, (i0, i0 + 3, -25, -24), -16)
        b.add(p, "walk", M, "platform")
    for r in ((-3, -3, -25, -25), (-1, 0, -25, -25), (2, 2, -25, -25), (-4, 3, -24, -24)):
        p, M = rect_M(TILE, r, -24)
        b.add(p, "walk", M, "floor")
    b.add("3460", "walk", transform((0, -8, -510)), "step")          # the step
    b.add("4162", "walk", transform((0, -16, -510)), "step")
    for x in COLUMNS:
        b.add("4073", "trim", transform((x, -24, Z_COL)), "floor")      # bases
        for n in range(6):
            b.add("3062b", "wall", transform((x, -48 - 24 * n, Z_COL)), f"col{n}")
        b.add("4073", "trim", transform((x, TOP - 8, Z_COL)), "caps")
    for x in (-40, 40):                                    # entablature: red, then tan
        p, M = rect_M(PLATE, (-4, -1, -25, -24) if x < 0 else (0, 3, -25, -24), TOP - 16)
        b.add(p, "trim", M, "entablature")
    p, M = rect_M(PLATE, (-3, 2, -25, -24), TOP - 24)
    b.add(p, "wall", M, "entablature")
    for x in (-40, 40):
        b.add("15332", "balustrade", transform((x, TOP - 72, Z_COL)), "balustrade")
    return b


def turned(b: Batch, a: float) -> Batch:
    out = Batch()
    T = transform((0, 0, 0), rot(y=a))
    for part, colour, M, cat, tag, insert in b.items:
        out.items.append((part, colour, T @ M, cat, tag, insert))
    return out


PHASES = [["platform"], ["floor", "step"]] + [[f"col{n}"] for n in range(6)] + \
    [["caps"], ["entablature"], ["balustrade"]]
CAPTIONS = {"platform": "A side porch: a stone platform in front of the door",
            "floor": "Tiles on it, round plates for the columns, and a step",
            "col0": "Four columns", "caps": "Red capitals",
            "entablature": "The entablature, red under tan",
            "balustrade": "A white balustrade on top"}


def build(model, main):
    for a in (90, 270):
        turned(porch_batch(), a).emit(main, PHASES, CAPTIONS, per_step=8)
