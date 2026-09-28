"""The base: a 38 x 38 stud lawn with a sidewalk round the edge and paths to the doors, two
live oaks at the corners and three flagpoles in front. Two layers of plates (the top one
green lawn and grey walks), tiles on the walks. Its top is at y = 0.

The building's footprint (studs, from the centre): pavilions and the centre pavilions reach
14, the wings 13; the portico stands in front of the front centre pavilion (x -3..3,
z -16..-14) with its steps down to the path (z -17..-16)."""
from __future__ import annotations

import numpy as np

from brickkit.ldraw.matrix import rot, transform
from kit import AV, PLATE, TILE, Batch, pack, rect_M

N = 19                                         # cells -19..18: 38 x 38 studs
CELLS = {(i, k) for i in range(-N, N) for k in range(-N, N)}
RING = {(i, k) for i, k in CELLS if i in (-N, N - 1) or k in (-N, N - 1)}
PORTICO = {(i, k) for i in range(-3, 3) for k in range(-16, -14)}   # its platform
STEPS = {(i, k) for i in range(-3, 3) for k in (-17,)}
FRONT_PATH = {(i, -18) for i in range(-3, 3)}


def _side_paths():
    """Paths 4 studs wide from the other three doors to the ring."""
    out = set()
    for i in range(-2, 2):
        for k in range(14, N - 1):
            out |= {(i, k), (k, i), (-k - 1, i)}
    return out


WALK = RING | FRONT_PATH | STEPS | PORTICO | _side_paths()


def _building() -> set:
    cells = {(i, k) for i in range(-13, 13) for k in range(-13, 13)}
    for sx in (1, -1):
        for sz in (1, -1):
            cells |= {(i if sx > 0 else -i - 1, k if sz > 0 else -k - 1)
                      for i in range(6, 14) for k in range(6, 14)}
    for i in range(-2, 2):
        cells |= {(i, -14), (i, 13), (-14, i), (13, i)}
    return cells


BUILDING = _building()
TREES = [(-330.0, -190.0), (330.0, 190.0)]
FLAGS = [(90.0, -330.0, "Red", "flag_us"), (170.0, -330.0, "Blue", "flag_tx"),
         (250.0, -330.0, "Dark Blue", "flag_county")]


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
    walk_tiles = WALK - PORTICO - STEPS - BUILDING
    for r in pack(walk_tiles, [s for s in tiles if s in TILE and AV.ok(TILE[s], "walk")]):
        p, M = rect_M(TILE, r, -8)
        b.add(p, "walk", M, "walks")
    return b


def shrubs() -> Batch:
    """Leafy round plates on the lawn, one stud out from the walls, every other stud."""
    b = Batch()
    near = lambda c, cells, r: any((c[0] + a, c[1] + e) in cells
                                   for a in range(-r, r + 1) for e in range(-r, r + 1))
    ring = {(i + 2 * d[0], k + 2 * d[1]) for i, k in BUILDING
            for d in ((1, 0), (-1, 0), (0, 1), (0, -1))}
    ring = {c for c in ring if c in CELLS and not near(c, BUILDING, 1) and not near(c, WALK, 1)}
    busy = {((int(x) - 10) // 20, (int(z) - 10) // 20) for x, z in TREES} | \
        {((int(x) - 10) // 20, (int(z) - 10) // 20) for x, z, *_ in FLAGS}
    for i, k in sorted(ring):
        if (i + k) % 2 or near((i, k), busy, 2):
            continue
        b.add("32607", "leaves" if (i // 2 + k // 2) % 2 else "leaves2",
              transform((20 * i + 10, -8, 20 * k + 10)), "shrubs")
    return b


def tree(model):
    """A live oak on a side lawn: a round trunk and leaves in three tiers, fanned along the
    lawn (their long side runs along Z, so they clear the walls and the base's edge)."""
    s = model.submodel("tree", "Live oak")
    for n in range(3):
        s.place("3062b", "trunk", (0, -24 * (n + 1), 0))
    y = -72
    tiers = [("2417", "leaves", 0), ("2417", "leaves2", 180), ("2417", "leaves", 180),
             ("2417", "leaves2", 0), ("2423", "leaves", 0), ("2423", "leaves", 180)]
    for n, (part, colour, a) in enumerate(tiers):
        s.step("The crown: leaves on round plates" if n == 0 else "")
        if n:
            s.place("6141", "trunk", (0, y - 8, 0))
            s.place("6141", "trunk", (0, y - 16, 0))
            y -= 16
        y -= 8
        s.place(part, colour, (0, y, 0), rot(y=a))
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
