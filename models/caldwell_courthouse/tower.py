"""The central tower: four hidden columns from the base to the roof deck, the belfry stage
(10 x 10, a pair of arched windows under a red arch on each side), the clock stage
(clock.py) and the lift-off top: a red cornice with a pediment on each side and the
bell-shaped slate dome with red corner ribs, a Texas star medallion on each face, a finial
and an arrow weather vane.

World heights: the belfry stands on the roof deck (-360) up to the clock stage's floor at
YC + 120; the clocks' centre is YC; the lift-off top sits on the clock stage at YC - 120."""
from __future__ import annotations

import numpy as np

from brickkit.ldraw.matrix import rot, transform, translate
from kit import AV, BRICK, PLATE, PLATE1, TILE, TILE1, Batch, orient, pack, rect_M, weave
from roofs import ring_course

YC = -656                     # the clocks' centre (world)
BELFRY_TOP = YC + 120         # -536: the clock stage stands on it
TOP_Y = YC - 120              # -776: the lift-off top sits here


def cx(i):
    return 20 * i + 10


# ------------------------------------------------------------------ hidden columns
def column(model):
    """A 2 x 2 column of grey bricks from the base to the underside of the roof deck."""
    s = model.submodel("column", "Tower column")
    y = 0
    for n in range(14):
        y -= 24
        s.place("3003", "core", (0, y, 0))
        if n in (4, 9):
            s.step()
    s.place("3022", "core", (0, y - 8, 0))
    return s


COLUMNS = [(sx * 80, sz * 80) for sx in (1, -1) for sz in (1, -1)]


# ------------------------------------------------------------------ belfry
BELFRY = (-5, 4, -5, 4)
B_COURSES = [(-384, "brick", "wall"), (-408, "brick", "wall"), (-416, "plate", "trim"),
             (-440, "brick", "wall"), (-464, "brick", "wall"), (-488, "brick", "wall"),
             (-512, "brick", "wall"), (-536, "brick", "wall")]
WIN = (-488, -416)             # a pair of 1 x 2 x 3 windows
ARCH = (-536, -488)            # a 1 x 6 x 2 arch over them


def belfry(model):
    s = model.submodel("belfry", "Belfry")
    b = Batch()
    win_cells = set()
    arch_cells = set()
    for a in (0, 90, 180, 270):          # windows in the middle of each side
        R = rot(y=a)
        for i in range(-2, 2):
            p = R @ np.array([cx(i), 0.0, cx(-5)])
            win_cells.add((int(round((p[0] - 10) / 20)), int(round((p[2] - 10) / 20))))
        for i in range(-3, 3):
            p = R @ np.array([cx(i), 0.0, cx(-5)])
            arch_cells.add((int(round((p[0] - 10) / 20)), int(round((p[2] - 10) / 20))))
    for n, (top, kind, colour) in enumerate(B_COURSES):
        skip = set()
        if WIN[0] <= top and top + (24 if kind == "brick" else 8) <= WIN[1]:
            skip = win_cells
        if ARCH[0] <= top and top + 24 <= ARCH[1]:
            skip = arch_cells
        ring_course(b, BELFRY, top, kind, colour, f"b{n:02d}", n, skip)
    for a in (0, 90, 180, 270):
        R = rot(y=a)
        for x in (-20, 20):
            c = R @ np.array([x, 0.0, cx(-5)])
            b.add("60593", "window", transform(c + (0, WIN[0], 0), R), "win")
            b.add("60602", "glass", transform(c + (0, WIN[0], 0), R), "win",
                  insert=tuple(R @ np.array([0, 0, 1.0])))
        c = R @ np.array([0.0, 0.0, cx(-5)])
        b.add("15254", "trim", transform(c + (0, ARCH[0], 0), R), "arch")
    phases = []
    for n, (top, _, _) in enumerate(B_COURSES):
        phases.append([f"b{n:02d}"])
        if top == WIN[1]:
            phases.append(["win"])
        if top == ARCH[1]:
            phases.append(["arch"])
    b.emit(s, phases, {"b00": "The belfry stands on the roof deck, over the columns",
                       "b02": "A red band", "win": "Two windows side by side on each side",
                       "arch": "Red arches over them"}, per_step=8)
    return s


# ------------------------------------------------------------------ lift-off top
def medallion(model):
    """A Texas star medallion: a tan dish on a red jumper plate, a red star on the dish.
    Built flat; it goes onto two side studs in the middle of a dome face."""
    s = model.submodel("medallion", "Star medallion")
    s.place("15573", "trim", (0, 0, 0))
    s.step("A tan dish and a red star")
    s.place("4740", "wall", (0, -8, 0))
    s.place("11609", "star", (0, -8, 0))
    return s


def _top_batch() -> Batch:
    """Parts of the lift-off top in its own frame: y = 0 is the clock stage's top."""
    b = Batch()
    ring12 = {(i, k) for i in range(-6, 6) for k in range(-6, 6)}
    for r in weave(ring12, "x", AV.lengths(PLATE1, "wall"), 0):
        p, M = rect_M(PLATE, r, -8)
        b.add(p, "wall", M, "base")
    for r in weave(ring12, "z", AV.lengths(PLATE1, "wall"), 1):
        p, M = rect_M(PLATE, r, -16)
        b.add(p, "wall", M, "base")
    # cornice: red plates one stud wider all round, tiles on the overhang
    ring14 = {(i, k) for i in range(-7, 7) for k in range(-7, 7)} - \
        {(i, k) for i in range(-5, 5) for k in range(-5, 5)}
    for r in ((-7, 6, -7, -6), (-7, 6, 5, 6), (-7, -6, -5, 4), (5, 6, -5, 4)):
        for part_r in _split_rect(r):
            p, M = rect_M(PLATE, part_r, -24)
            b.add(p, "trim", M, "cornice")
    for r in ((-5, 4, -5, -5), (-5, 4, 4, 4), (-5, -5, -4, 3), (4, 4, -4, 3)):
        for part_r in _split_rect(r):
            p, M = rect_M(PLATE, part_r, -24)
            b.add(p, "trim", M, "cornice")
    edge = {(i, k) for i, k in ring14 if i in (-7, 6) or k in (-7, 6)}
    for r in pack(edge, [(1, 6), (1, 4), (1, 3), (1, 2), (1, 1)]):
        p, M = rect_M(TILE, r, -32)
        b.add(p, "trim", M, "cornice2")
    # the bell dome: each stage steps in one stud all round, so its toe sits on the last
    # stage's back row and the slopes run on without ledges. A 45-degree flare at the
    # foot, two 75-degree stages (the upper one with a star medallion in each face), two
    # 45-degree stages and a 75-degree point: concave at the foot, swelling to the point.
    # Red ribs up every corner.
    for a in (0, 90, 180, 270):
        R = rot(y=a)

        def add(part, colour, x, y, z, Rl=None, cat="flare"):
            b.add(part, colour, transform(R @ np.array([x, y, z], float),
                                          R @ (np.eye(3) if Rl is None else Rl)), cat)
        add("3045", "trim", cx(4), -48, cx(-5))
        for i in range(-4, 4):
            add("3040b", "roof", cx(i), -48, cx(-5))
        add("3685", "trim", cx(3), -120, cx(-4), cat="dome1")
        for i in range(-3, 3):
            add("4460b", "roof", cx(i), -120, cx(-4), cat="dome1")
        add("3685", "trim", cx(2), -192, cx(-3), cat="dome2")
        for i in (-2, 1):
            add("4460b", "roof", cx(i), -192, cx(-3), cat="dome2")
        add("3003", "roof", 0, -144, -60, cat="dome2")          # the medallion's column
        add("11211", "roof", 0, -168, cx(-4), cat="dome2")
        add("3004", "roof", 0, -168, cx(-3), cat="dome2")
        add("3003", "roof", 0, -192, -60, cat="dome2")
        add("3069b", "roof", 0, -200, cx(-4), cat="dome3")
        add("3045", "trim", cx(1), -216, cx(-2), cat="dome3")
        for i in (-1, 0):
            add("3040b", "roof", cx(i), -216, cx(-2), cat="dome3")
        add("3045", "trim", cx(0), -240, cx(-1), cat="dome4")
    b.add("3688", "roof", transform((0, -288, 0)), "point")
    b.add("59900", "trim", transform((0, -316, 0)), "vane")
    b.add("87994", "crest", transform((0, -344, 0)), "vane")
    b.add("60897", "crest", transform((0, -342, 20)), "vane")
    b.add("61252", "crest", transform((0, -350, 20), rot(y=180)), "vane")
    b.add("18041", "crest", transform((-20, -348, 40), rot(z=90)), "vane")
    return b


TOP_PHASES = [["base"], ["cornice"], ["cornice2"], ["flare"], ["dome1"],
              ["dome2"], ["dome3"], ["dome4"], ["point"], ["vane"]]


def _split_rect(r):
    """A rectangle of cells as plates that exist (2 x N up to 2 x 12, else 1 x N)."""
    i0, i1, k0, k1 = r
    w, d = i1 - i0 + 1, k1 - k0 + 1
    along_x = w >= d
    n = w if along_x else d
    out, pos = [], 0
    for L in {14: [8, 6], 10: [6, 4]}.get(n, [n]):
        a = pos
        if along_x:
            out.append((i0 + a, i0 + a + L - 1, k0, k1))
        else:
            out.append((i0, i1, k0 + a, k0 + a + L - 1))
        pos += L
    return out


def tower_top(model):
    """The lift-off top, in its own frame (y = 0 is the clock stage's top)."""
    s = model.submodel("tower_top", "Lift-off top: cornice and dome")
    b = _top_batch()
    later = Batch()
    later.items = [it for it in b.items if it[3] in ("dome3", "dome4", "point", "vane")]
    b.items = [it for it in b.items if it[3] not in ("dome3", "dome4", "point", "vane")]
    b.emit(s, TOP_PHASES[:6], {
        "base": "The lift-off top: two layers of tan plates",
        "cornice": "The red cornice: plates one stud wider all round",
        "cornice2": "Red tiles on its edge",
        "flare": "The bell dome: a flared foot of 45-degree slopes, red corner ribs",
        "dome1": "Steep slate slopes",
        "dome2": "Second steep stage, with a column in each face for a star medallion"},
        per_step=8)
    med = medallion(model)
    s.step("A star medallion on each face")
    for a in (0, 90, 180, 270):
        R = rot(y=a)
        M = transform(R @ np.array([0.0, -158, -88]), R @ rot(x=90))
        s.use(med, tuple(M[:3, 3]), M[:3, :3], insert=tuple(R @ np.array([0, 0, -1.0])))
    later.emit(s, TOP_PHASES[5:], {
        "dome3": "Gentler slopes towards the top", "point": "The point",
        "vane": "The weather vane: an arrow on a black bar"}, per_step=8)
    return s
