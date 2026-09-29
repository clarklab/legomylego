"""The base: a 56 x 56 stud lawn with a sidewalk round the edge, paths to the front and back
doors, porches on the two sides, four live oaks and three flagpoles in front. Two layers of
plates (the top one green lawn and grey walks), tiles on the walks. Its top is at y = 0.

The building's footprint (studs from the centre): 46 x 46 with the corner pavilions and the
dome pavilions projecting one stud more on every side (48 x 48 over them); the entrance bays
between the dome pavilions are set back. The side porches stand in front of the entrance
bays on the two sides (x 460..500, z -80..80), with a step down to the walk."""
from __future__ import annotations

import numpy as np

from brickkit.ldraw.matrix import rot, transform
from kit import AV, PLATE, TILE, Batch, pack, rect_M

N = 28                                         # cells -28..27: 56 x 56 studs
CELLS = {(i, k) for i in range(-N, N) for k in range(-N, N)}
RING = {(i, k) for i, k in CELLS if i in (-N, N - 1) or k in (-N, N - 1)}


def turn(cells, a):
    """Cells turned by rot(y=a) about the centre."""
    R = rot(y=a)
    out = set()
    for i, k in cells:
        p = R @ np.array([20 * i + 10, 0.0, 20 * k + 10])
        out.add((int(round((p[0] - 10) / 20)), int(round((p[2] - 10) / 20))))
    return out


def all_sides(cells, angles=(0, 90, 180, 270)):
    return set().union(*(turn(cells, a) for a in angles))


# the front (-Z) side's projecting bays: corner pavilions and dome pavilions
PROJECT = {(i, -24) for i in list(range(-24, -16)) + list(range(-12, -4)) + list(range(4, 12))
           + list(range(16, 24))}
BUILDING = {(i, k) for i in range(-23, 23) for k in range(-23, 23)} | all_sides(PROJECT)
# porches on the sides (+X and -X), built in the front frame and turned
PORCH0 = {(i, k) for i in range(-4, 4) for k in (-25, -24)}
STEP0 = {(i, -26) for i in range(-4, 4)}
PORCH = turn(PORCH0, 90) | turn(PORCH0, 270)
STEPS = turn(STEP0, 90) | turn(STEP0, 270)
SIDE_WALKS = turn({(i, -27) for i in range(-4, 4)}, 90) | turn({(i, -27) for i in range(-4, 4)}, 270)
DOORWAYS = turn({(i, -24) for i in range(-4, 4)}, 0) | turn({(i, -24) for i in range(-4, 4)}, 180)
PATHS = {(i, k) for i in range(-2, 2) for k in range(-27, -24)}
PATHS |= turn(PATHS, 180)
WALK = RING | PORCH | STEPS | SIDE_WALKS | DOORWAYS | PATHS
TREES = [(-250.0, -510.0), (-430.0, -510.0), (250.0, 510.0), (430.0, 510.0)]
FLAGS = [(90.0, -510.0, "Red", "flag_us"), (170.0, -510.0, "Blue", "flag_tx"),
         (250.0, -510.0, "Dark Blue", "flag_county")]


def base_batch() -> Batch:
    b = Batch()
    big = [(16, 16), (8, 16), (6, 16), (8, 8), (6, 10), (6, 8), (4, 8), (6, 6), (4, 6),
           (4, 4), (2, 8), (2, 6), (2, 4), (2, 2), (1, 4), (1, 2), (1, 1)]
    ok = lambda sizes, c: [s for s in sizes if s in PLATE and AV.ok(PLATE[s], c)]
    for r in pack(CELLS, ok(big, "base"), shift=5):                      # bottom layer
        p, M = rect_M(PLATE, r, 8)
        b.add(p, "base", M, "bottom")
    for colour, cells in (("walk", WALK), ("lawn", CELLS - WALK)):          # top layer
        for r in pack(cells, ok(big, colour), prefer="z"):
            p, M = rect_M(PLATE, r, 0)
            b.add(p, colour, M, "top")
    tiles = [(2, 6), (2, 4), (1, 6), (1, 4), (2, 2), (1, 3), (1, 2), (1, 1)]
    walk_tiles = WALK - PORCH - STEPS - BUILDING
    for r in pack(walk_tiles, [s for s in tiles if s in TILE and AV.ok(TILE[s], "walk")]):
        p, M = rect_M(TILE, r, -8)
        b.add(p, "walk", M, "walks")
    return b


def shrubs() -> Batch:
    """Leafy round plates on the lawn, one stud out from the walls, every other stud."""
    b = Batch()
    near = lambda c, cells, r: any((c[0] + a, c[1] + e) in cells
                                   for a in range(-r, r + 1) for e in range(-r, r + 1))
    ring = {(i + 3 * d[0], k + 3 * d[1]) for i, k in BUILDING
            for d in ((1, 0), (-1, 0), (0, 1), (0, -1))}
    ring = {c for c in ring if c in CELLS and not near(c, BUILDING, 2) and not near(c, WALK, 1)}
    busy = {((int(x) - 10) // 20, (int(z) - 10) // 20) for x, z in TREES} | \
        {((int(x) - 10) // 20, (int(z) - 10) // 20) for x, z, *_ in FLAGS}
    for i, k in sorted(ring):
        if (i + k) % 2 or near((i, k), busy, 2):
            continue
        b.add("32607", "leaves" if (i // 2 + k // 2) % 2 else "leaves2",
              transform((20 * i + 10, -8, 20 * k + 10)), "shrubs")
    return b


def tree(model):
    """A live oak on the front or back lawn: a round trunk and a wide, low crown that
    spreads along the facade (the lawn is only three studs deep): on each tier a round
    2 x 2 plate carries two leaves pointing left and right, on its outer side."""
    s = model.submodel("tree", "Live oak")
    for n in range(3):
        s.place("3062b", "trunk", (0, -24 * (n + 1), 0))
    y = -72
    for n in range(3):
        s.step("The crown: two leaves on a round plate, three times" if n == 0 else "")
        s.place("4032a", "trunk", (0, y - 8, 0))
        s.place("2423", "leaves", (-10, y - 16, -10), rot(y=90))
        s.place("2423", "leaves2" if n % 2 else "leaves", (10, y - 16, -10), rot(y=-90))
        y -= 16
    s.step("The top")
    s.place("4032a", "trunk", (0, y - 8, 0))
    s.place("32607", "leaves2", (-10, y - 16, -10))
    return s


def flagpole(model):
    """Two round bricks and a white bar 6L standing in the top one."""
    s = model.submodel("flagpole", "Flagpole")
    s.place("3062b", "pole", (0, -24, 0))
    s.place("3062b", "pole", (0, -48, 0))
    s.step("A white bar for the pole")
    s.place("63965", "pole", (0, -52, 0))
    return s


FLAG_Y = -146               # the wavy flag slides down the bar to here
