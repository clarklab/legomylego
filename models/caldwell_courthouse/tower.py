"""The central tower and the four bell domes round it.

The tower: four hidden columns from the base to the roof deck, the belfry (10 x 10, as wide
as the clock stage's core, with two tall arched openings under red hoods on each side, red
corner pilasters and a red band at the top), the clock stage (clock.py) and the lift-off
top: a red cornice, the bell-shaped slate dome with red corner ribs, a Texas star medallion
on each face, a finial and an arrow weather vane.

The four bell domes stand on the front and back facades' dome pavilions, two flanking the
tower on each, flush with the facade. Each has a storey-tall 10 x 10 cream stage with red
corner pilasters, a big round red-framed window on its front and sides and red bands at the
top, a red cornice a stud wider, and a slate bell about as tall as it is wide: a 45-degree
flared foot, a steep 75-degree body, two 45-degree stages swelling to a short 75-degree
point, red ribs up every corner and a red finial, its tip level with the belfry's openings
and below the clock stage.

World heights: the belfry stands on the roof deck (-512) up to -1024, the clock stage's
floor (YC + 120); the clocks' centre is YC; the lift-off top sits on the clock stage at
YC - 120. The domes stand on the cornice (-544): stage to -728, cornice to -744, the bell's
point to -928 and the finial to -984."""
from __future__ import annotations

import numpy as np

from brickkit.ldraw.matrix import rot, transform, translate
from kit import AV, BRICK, PLATE, PLATE1, TILE, TILE1, Batch, orient, pack, rect_M, weave
from roofs import FLAT_OCULUS, ring_course

YC = -1144                    # the clocks' centre (world)
DECK = -512
BELFRY_TOP = YC + 120         # -1024: the clock stage stands on the belfry
TOP_Y = YC - 120              # -1264: the lift-off top sits here


def cx(i):
    return 20 * i + 10


def cells_turned(cells, a):
    R = rot(y=a)
    out = set()
    for i, k in cells:
        p = R @ np.array([cx(i), 0.0, cx(k)])
        out.add((int(round((p[0] - 10) / 20)), int(round((p[2] - 10) / 20))))
    return out


# ------------------------------------------------------------------ hidden columns
def column(model):
    """A 2 x 2 column of grey bricks from the base to the underside of the roof deck."""
    s = model.submodel("column", "Column")
    y = 0
    for n in range(20):
        y -= 24
        s.place("3003", "core", (0, y, 0))
        if n in (6, 13):
            s.step()
    s.place("3022", "core", (0, y - 8, 0))
    s.place("3022", "core", (0, y - 16, 0))
    return s


COLUMNS = [(sx * 80, sz * 80) for sx in (1, -1) for sz in (1, -1)] + \
    [(sx * 160, sz * 400) for sx in (1, -1) for sz in (1, -1)]


# ------------------------------------------------------------------ belfry
BELFRY = (-5, 4, -5, 4)
B_COURSES = [(t, "brick", "wall") for t in range(-536, -801, -24)] + \
    [(-808, "plate", "trim")] + \
    [(t, "brick", "wall") for t in range(-832, -1001, -24)] + [(-1024, "brick", "trim")]
B_BAND = -808                                  # the red band between the two parts
OPEN_CELLS = ((-3, -2), (1, 2))                # two openings per side
OPEN = (-976, -832)                            # two 1 x 2 x 3 windows stacked, dark
HOOD = (-1000, -976)                           # red 1 x 4 arches over them
CORNER_ROT = {(1, -1): 0, (-1, -1): 90, (-1, 1): 180, (1, 1): -90}   # 2 x 2 corner parts
SIDE_ROT = {(0, -1): 0, (1, 0): -90, (0, 1): 180, (-1, 0): 90}


def belfry(model):
    s = model.submodel("belfry", "Belfry")
    b = Batch()
    open_cells, hood_cells = set(), set()
    for a in (0, 90, 180, 270):
        for c0, c1 in OPEN_CELLS:
            open_cells |= cells_turned({(c0, -5), (c1, -5)}, a)
            hood_cells |= cells_turned({(i, -5) for i in range(c0 - 1, c1 + 2)}, a)
    corners = {(i, k) for i in (BELFRY[0], BELFRY[1]) for k in (BELFRY[2], BELFRY[3])}
    for n, (top, kind, colour) in enumerate(B_COURSES):
        h = 24 if kind == "brick" else 8
        skip = set()
        if OPEN[0] <= top and top + h <= OPEN[1]:
            skip = set(open_cells)
        if HOOD[0] <= top and top + h <= HOOD[1]:
            skip = set(hood_cells)
        if kind == "brick" and colour == "wall":             # red corner pilasters
            skip |= corners
            for i, k in corners:
                b.add("3005", "trim", transform((cx(i), top, cx(k))), f"b{n:02d}")
        ring_course(b, BELFRY, top, kind, colour, f"b{n:02d}", n, skip)
    for a in (0, 90, 180, 270):
        R = rot(y=a)
        back = tuple(R @ np.array([0, 0, 1.0]))
        for c0, c1 in OPEN_CELLS:
            c = R @ np.array([(cx(c0) + cx(c1)) / 2, 0.0, cx(-5)])
            for y, cat in ((OPEN[1] - 72, "win"), (OPEN[0], "win2")):
                b.add("60593", "window", transform(c + (0, y, 0), R), cat)
                b.add("60602", "glass_dark", transform(c + (0, y, 0), R), cat, insert=back)
            b.add("3659", "trim", transform(c + (0, HOOD[0], 0), R), "hood")
    phases = []
    for n, (top, _, _) in enumerate(B_COURSES):
        if top == HOOD[0]:
            phases.append(["hood"])
        phases.append([f"b{n:02d}"])
        if top == OPEN[1]:
            phases.append(["win"])
        if top == OPEN[1] - 72:
            phases.append(["win2"])
    band = next(n for n, c in enumerate(B_COURSES) if c[0] == B_BAND)
    b.emit(s, phases, {"b00": "The belfry stands on the roof deck, over the columns",
                       f"b{band:02d}": "A red band",
                       "win": "Two tall dark openings on each side",
                       "hood": "Red hoods over them",
                       f"b{len(B_COURSES) - 1:02d}": "A red band at the top: the clock stage "
                                                     "sits on it"},
           per_step=8)
    return s


def corbel_ring(b: Batch, lo: int, hi: int, top: float, cat: str, colour="wall"):
    """A ring of inverted slopes stepping out one stud: their backs on the ring of cells
    lo..hi's edge, overhanging one cell outward; inverted double-convex corners."""
    for (sx, sz), a in CORNER_ROT.items():
        i = hi if sx > 0 else lo
        k = hi if sz > 0 else lo
        b.add("3676", colour, transform((cx(i), top, cx(k)), rot(y=a)), cat)
    for d, a in SIDE_ROT.items():
        for t in range(lo + 1, hi):
            if d[0] == 0:
                i, k = t, (hi if d[1] > 0 else lo)
            else:
                i, k = (hi if d[0] > 0 else lo), t
            b.add("3665b", colour, transform((cx(i), top, cx(k)), rot(y=a)), cat)


# ------------------------------------------------------------------ bell domes
DOME = (3, 12, -24, -15)                     # the front-right dome's stage (cells)
DOME_C = (160.0, -380.0)
D_BASE = -544                                # it stands on the cornice's top
D_COURSES = [(-568, "brick", "wall"), (-576, "plate", "wall"), (-600, "brick", "wall"),
             (-608, "plate", "wall"), (-616, "plate", "wall"), (-640, "brick", "wall"),
             (-664, "brick", "wall"), (-688, "brick", "wall"), (-712, "brick", "wall"),
             (-720, "plate", "trim"), (-728, "plate", "trim")]
SNOT_TOPS = (-600, -640)      # side-stud courses (studs at -590 and -630) for the windows
OCULUS_Y = -640               # the round windows' centre (6 x 6: -580..-700)
D_TOP = -728                  # the stage's top
D_CORNICE = D_TOP - 8         # the cornice plates' top
D_BELL = [(10, D_CORNICE - 24, "3045", "3040b", "flare"),      # outer size, top, parts
          (8, D_CORNICE - 96, "3685", "4460b", "body"),
          (6, D_CORNICE - 120, "3045", "3040b", "swell"),
          (4, D_CORNICE - 144, "3045", "3040b", "swell2")]
D_POINT = D_CORNICE - 192     # the point's top (-928)
D_TIP = D_POINT - 28          # the finial's red cone (to -956) on a black rod (to -984),
                              # below the clock stage (BELFRY_TOP, -1024)


def _ring(top: Batch, size: int, y: float, corner: str, side: str, colour_c: str,
          colour_s: str, cat: str):
    """A ring of 2 x 2 corner slopes and 2 x 1 side slopes whose outer edge is the
    size x size square centred on the dome (their low sides outward)."""
    x0, z0 = DOME_C
    h = size // 2
    for (sx, sz), a in CORNER_ROT.items():
        top.add(corner, colour_c, transform((x0 + sx * (20 * h - 30), y,
                                             z0 + sz * (20 * h - 30)), rot(y=a)), cat)
    for d, a in SIDE_ROT.items():
        for t in range(-(h - 2), h - 2):
            u = 20 * t + 10
            if d[0] == 0:
                x, z = x0 + u, z0 + d[1] * (20 * h - 30)
            else:
                x, z = x0 + d[0] * (20 * h - 30), z0 + u
            top.add(side, colour_s, transform((x, y, z), rot(y=a)), cat)


def _plates(b: Batch, rect, y, colour, cat):
    """A rectangle of cells as plates that exist in the colour (2 x N, else 1 x N runs)."""
    i0, i1, k0, k1 = rect
    w, d = i1 - i0 + 1, k1 - k0 + 1
    if AV.ok(PLATE[(min(w, d), max(w, d))], colour):
        p, M = rect_M(PLATE, rect, y)
        b.add(p, colour, M, cat)
        return
    n = max(w, d)
    for L in {8: [4, 4], 6: [4, 2], 10: [6, 4], 12: [6, 6]}.get(n, [n // 2, n - n // 2]):
        if w >= d:
            _plates(b, (i0, i0 + L - 1, k0, k1), y, colour, cat)
            i0 += L
        else:
            _plates(b, (i0, i1, k0, k0 + L - 1), y, colour, cat)
            k0 += L


def dome(model, ocu):
    """The front-right bell dome, built on its dome pavilion flush with the facade: a
    storey-tall 10 x 10 cream stage with red corner pilasters and a big round red-framed
    window on its front and both sides, red bands, a red cornice one stud wider, then the
    bell: a 45-degree flared foot, a steep 75-degree body, two 45-degree stages and a short
    75-degree point (red ribs up every corner), and a red finial."""
    s = model.submodel("dome", "Bell dome")
    b = Batch()
    i0, i1, k0, k1 = DOME
    x0, z0 = DOME_C
    mid_i = [i for i in range(i0, i1 + 1) if abs(cx(i) - x0) <= 30]     # 4 cells across
    mid_k = [k for k in range(k0, k1 + 1) if abs(cx(k) - z0) <= 30]
    snot = {(i, k0) for i in mid_i} | {(i, k) for i in (i0, i1) for k in mid_k}
    corners = {(i0, k0), (i0, k1), (i1, k0), (i1, k1)}
    for n, (top, kind, colour) in enumerate(D_COURSES):
        skip = set(snot) if top in SNOT_TOPS else set()
        if colour == "wall":                            # red corner pilasters
            skip |= corners
            for i, k in corners:
                b.add("3005" if kind == "brick" else "3024", "trim",
                      transform((cx(i), top, cx(k))), f"t{n:02d}")
        ring_course(b, DOME, top, kind, colour, f"t{n:02d}", n, skip)
        if top in SNOT_TOPS:
            b.add("30414", "wall", transform((x0, top, cx(k0))), f"t{n:02d}")
            b.add("30414", "wall", transform((cx(i1), top, z0), rot(y=-90)), f"t{n:02d}")
            b.add("30414", "wall", transform((cx(i0), top, z0), rot(y=90)), f"t{n:02d}")
    top = Batch()
    for r in ((i0 - 1, i0 + 4, k0 - 1, k0), (i0 + 5, i1 + 1, k0 - 1, k0),
              (i0 - 1, i0 + 4, k1, k1 + 1), (i0 + 5, i1 + 1, k1, k1 + 1),
              (i0 - 1, i0, k0 + 1, k1 - 1), (i1, i1 + 1, k0 + 1, k1 - 1)):
        _plates(top, r, D_CORNICE, "trim", "cornice")
    edge = {(i, k) for i in range(i0 - 1, i1 + 2) for k in range(k0 - 1, k1 + 2)
            if i in (i0 - 1, i1 + 1) or k in (k0 - 1, k1 + 1)}
    # little red pediments over the three windows (4 wide: two 45-degree slopes back to back)
    peds = [((x0, cx(k0 - 1)), 0), ((cx(i1 + 1), z0), -90), ((cx(i0 - 1), z0), 90)]
    for (px, pz), a in peds:
        R = rot(y=a)
        for u, turn in ((-10, 90), (10, -90)):
            p = np.array([px, D_CORNICE - 24, pz]) + R @ np.array([u, 0.0, 0.0])
            top.add("3040b", "trim", transform(p, R @ rot(y=turn)), "pediment")
        edge -= {(i, k) for i, k in edge
                 if abs(cx(i) - px) <= (40 if a == 0 else 10)
                 and abs(cx(k) - pz) <= (10 if a == 0 else 40)}
    for r in pack(edge, [(1, n) for n in (6, 4, 3, 2, 1) if AV.ok(TILE[(1, n)], "trim")]):
        p, M = rect_M(TILE, r, D_CORNICE - 8)
        top.add(p, "trim", M, "cornice2")
    for size, y, corner, side, cat in D_BELL:
        _ring(top, size, y, corner, side, "trim", "roof", cat)
    top.add("3688", "roof", transform((x0, D_POINT, z0)), "point")
    top.add("59900", "trim", transform((x0, D_TIP, z0)), "finial")
    top.add("87994", "crest", transform((x0, D_TIP - 28, z0)), "finial")
    phases = [[f"t{n:02d}"] for n in range(len(D_COURSES))]
    b.emit(s, phases, {"t00": "A bell dome: a cream stage with red corner pilasters, on the "
                              "cornice over a dome pavilion",
                       "t02": "Bricks with side studs for the round windows",
                       "t09": "Red bands at the top"}, per_step=8)
    s.step("Press a round window onto the front and both sides")
    for M in (translate(x0, OCULUS_Y, cx(k0) - 18) @ FLAT_OCULUS,
              translate(cx(i1) + 18, OCULUS_Y, z0) @ transform((0, 0, 0), rot(y=-90))
              @ FLAT_OCULUS,
              translate(cx(i0) - 18, OCULUS_Y, z0) @ transform((0, 0, 0), rot(y=90))
              @ FLAT_OCULUS):
        out = M[:3, :3] @ np.array([0.0, -1.0, 0.0])
        s.use(ocu, tuple(M[:3, 3]), M[:3, :3], insert=tuple(out))
    top.emit(s, [["cornice"], ["cornice2", "pediment"], ["flare"], ["body"], ["swell"],
                 ["swell2"], ["point"], ["finial"]], {
        "cornice": "A red cornice, one stud wider all round",
        "cornice2": "Red tiles on its edge and a little pediment over each window",
        "flare": "The bell's flared foot: slate slopes, red corners",
        "body": "The steep body, with red ribs at the corners",
        "swell": "Two gentler stages: the bell swells towards the top",
        "point": "A short point", "finial": "A red finial on a black rod"}, per_step=8)
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
