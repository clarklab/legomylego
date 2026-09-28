"""Roofs: the deck over the walls with the red cornice, slate mansards with dormers and iron
cresting on the wings, gabled attics over the centre pavilions, and the corner pavilions'
towers (a stage with a round red oculus on each outer face, a red cornice and a slate cap
with red ribs).

Heights (y): wall top -344; deck -344..-360 (two plate layers over the whole building, the
outer ring tan then red); cornice: red inverted slopes -360..-384 on the outer ring, red
plates -384..-392 over it and the overhang, red tiles on the overhang -392..-400. The flat
roof inside is tiled slate grey at -360..-368."""
from __future__ import annotations

import numpy as np

from brickkit.ldraw.matrix import rot, transform, translate
from kit import (AV, BRICK, PLATE, PLATE1, TILE, TILE1, Batch, n_pieces, pack, rect_M,
                 segments, split_line, weave)
import base

DIRS = [(0, -1), (1, 0), (0, 1), (-1, 0)]
FACE_ROT = {(0, -1): 0, (1, 0): -90, (0, 1): 180, (-1, 0): 90}   # rot(y) turning -Z to d
Y_DECK = -360
Y_CORNICE = -392          # top of the cornice plates


def cx(i):
    return 20 * i + 10


def _R(d):
    return rot(y=FACE_ROT[d])


def turn_cells(cells, a):
    """Cells turned by rot(y=a) about the centre."""
    R = rot(y=a)
    out = set()
    for i, k in cells:
        p = R @ np.array([cx(i), 0.0, cx(k)])
        out.add((int(round((p[0] - 10) / 20)), int(round((p[2] - 10) / 20))))
    return out


OUTLINE = base.BUILDING


def exposures():
    """{cell: [outward directions]} for the building's outer cells."""
    out = {}
    for c in OUTLINE:
        ds = [d for d in DIRS if (c[0] + d[0], c[1] + d[1]) not in OUTLINE]
        if ds:
            out[c] = ds
    return out


def cornice_plan():
    """Inverted slopes (cell, direction) and the cells they overhang: straight runs first,
    then corners take a direction whose overhang is still free."""
    exp = exposures()
    slopes, over = [], set()
    for c, ds in sorted(exp.items(), key=lambda kv: len(kv[1])):
        for d in ds:
            o = (c[0] + d[0], c[1] + d[1])
            if o in over:
                continue
            slopes.append((c, d))
            over.add(o)
            break
    # the plates over the cornice also cover a corner's other side and the diagonal cell
    corners = set()
    for c, ds in exp.items():
        for d in ds:
            corners.add((c[0] + d[0], c[1] + d[1]))
        if len(ds) == 2:
            (a, b), (e, f) = ds
            corners.add((c[0] + a + e, c[1] + b + f))
    return slopes, over, (corners - over) - OUTLINE


# ------------------------------------------------------------------ zones on the roof
def _zone(cells_front_right):
    return set().union(*(turn_cells(cells_front_right, a) for a in (0, 90, 180, 270)))


PAVILION = _zone({(i, k) for i in range(6, 14) for k in range(-14, -6)})
PAV_TOWER = _zone({(i, k) for i in range(7, 13) for k in range(-13, -7)})
TOWER = {(i, k) for i in range(-5, 5) for k in range(-5, 5)}
WING_MANSARD = set().union(*(turn_cells({(i, k) for i in list(range(2, 7)) + list(range(-7, -2))
                                         for k in (-13, -12)}, a) for a in (0, 90, 180, 270)))
ATTIC = _zone({(i, k) for i in range(-2, 2) for k in range(-14, -11)})


def deck_batch() -> Batch:
    """The first layout (trying different plate packings) whose two deck layers are one
    piece on their own."""
    for v in range(40):
        b = _deck_batch(v)
        if n_pieces(b.parts({"deck1", "deck2"})) == 1:
            return b
    raise RuntimeError("no deck layout joins up")


def _deck_batch(v: int) -> Batch:
    b = Batch()
    slopes, over, corners = cornice_plan()
    ring = set(exposures())
    inner = OUTLINE - ring
    sizes = [(16, 16), (8, 16), (6, 16), (8, 8), (6, 10), (6, 8), (4, 8), (6, 6), (4, 6),
             (4, 4), (2, 8), (2, 6), (2, 4), (2, 3), (2, 2), (1, 4), (1, 3), (1, 2), (1, 1)]
    ok = [s for s in sizes if s in PLATE and AV.ok(PLATE[s], "core")]
    # layer 1: a tan ring over the walls, big grey plates inside
    runs = [(1, 8), (1, 6), (1, 4), (1, 3), (1, 2), (1, 1)]
    for r in pack(ring, [s for s in runs if AV.ok(PLATE[s], "wall")]):
        p, M = rect_M(PLATE, r, -352)
        b.add(p, "wall", M, "deck1")
    for r in pack(inner, ok, shift=3 + 7 * v):
        p, M = rect_M(PLATE, r, -352)
        b.add(p, "core", M, "deck1")
    # layer 2: a red ring two studs wide (it bonds the ring to the inside), grey inside
    ring2 = ring | {c for c in inner if any((c[0] + a, c[1] + e) in ring
                                            for a, e in DIRS + [(1, 1), (1, -1), (-1, 1), (-1, -1)])}
    left = set(ring2)
    exp = exposures()
    for d in DIRS:                   # 2-wide strips along each straight edge, over the ring
        edge = sorted(c for c, ds in exp.items() if ds == [d])
        lines = {}
        for c in edge:
            lines.setdefault(c[1] if d[1] else c[0], []).append(c[0] if d[1] else c[1])
        lens = [n for n in (8, 6, 4, 3, 2) if AV.ok(PLATE[(2, n)], "trim")]
        for key, vals in lines.items():
            for seg in segments(vals):
                pos = seg[0]
                while pos <= seg[-1]:
                    for L in lens:
                        run = range(pos, pos + L)
                        cells = ({(u, key) for u in run} | {(u, key - d[1]) for u in run}) \
                            if d[1] else ({(key, u) for u in run} | {(key - d[0], u) for u in run})
                        if pos + L - 1 <= seg[-1] and cells <= left:
                            i0 = min(c[0] for c in cells); i1 = max(c[0] for c in cells)
                            k0 = min(c[1] for c in cells); k1 = max(c[1] for c in cells)
                            p, M = rect_M(PLATE, (i0, i1, k0, k1), Y_DECK)
                            b.add(p, "trim", M, "deck2")
                            left -= cells
                            pos += L
                            break
                    else:
                        pos += 1
    strips = [(2, 4), (2, 3), (2, 2), (1, 4), (1, 3), (1, 2), (1, 1)]
    for r in pack(left, [s for s in strips if AV.ok(PLATE[s], "trim")], shift=1):
        p, M = rect_M(PLATE, r, Y_DECK)
        b.add(p, "trim", M, "deck2")
    for r in pack(OUTLINE - ring2, ok, shift=11 + 13 * v, prefer="xz"[v % 2]):
        p, M = rect_M(PLATE, r, Y_DECK)
        b.add(p, "core", M, "deck2")
    # cornice: inverted slopes out over the walls, plates over them, tiles on the overhang
    for c, d in slopes:
        b.add("3665b", "trim", transform((cx(c[0]), Y_DECK - 24, cx(c[1])), _R(d)), "cornice")
    top = ring | over | corners
    for r in weave(top, "x", AV.lengths(PLATE1, "trim"), 2):
        p, M = rect_M(PLATE, r, Y_CORNICE)
        b.add(p, "trim", M, "cornice2")
    edge = (over | corners)
    for r in weave(edge, "x", AV.lengths(TILE1, "trim"), 1):
        p, M = rect_M(TILE, r, Y_CORNICE - 8)
        b.add(p, "trim", M, "cornice3")
    return b


DECK_PHASES = [["deck1", "deck2"], ["cornice"], ["cornice2"], ["cornice3"]]


# ------------------------------------------------------------------ wing mansards
def _backfill(b: Batch, cells, cat="backfill"):
    """A brick and a plate on the deck (-360) so a roof piece can start at the cornice's
    top (-392)."""
    for i, k in cells:
        b.add("3005", "core", transform((cx(i), -384, cx(k))), cat)
        b.add("3024", "core", transform((cx(i), -392, cx(k))), cat)


def wing_mansard(b: Batch, side: int):
    """The slate mansard over a front wing (side +1: x 40..140, -1: x -140..-40): 75-degree
    slopes from the cornice up to -464, a dormer over the wing's window, iron cresting."""
    cells = list(range(2, 7)) if side > 0 else list(range(-7, -2))
    end = 6 if side > 0 else -7                 # the cell against the pavilion tower
    dormer = (3, 4) if side > 0 else (-5, -4)
    _backfill(b, [(i, -12) for i in cells] + [(end, -13)])
    for i in cells:
        if i in dormer:
            continue
        b.add("4460b", "roof", transform((cx(i), -464, cx(-12))), "slopes")
    x = (cx(dormer[0]) + cx(dormer[1])) / 2
    b.add("60592", "window", transform((x, -440, cx(-13))), "dormer")
    b.add("60601", "glass", transform((x, -440, cx(-13))), "dormer", insert=(0, 0, 1))
    b.add("3004", "wall", transform((x, -416, cx(-12))), "dormer")
    b.add("3004", "wall", transform((x, -440, cx(-12))), "dormer")
    b.add("3039", "roof", transform((x, -464, cx(-12))), "dormer_roof")
    rail = [i for i in cells if i != end]
    b.add("19121", "crest", transform(((cx(rail[0]) + cx(rail[-1])) / 2, -512, cx(-12))),
          "crest")
    return b


# ------------------------------------------------------------------ centre attics
def attic(b: Batch):
    """The gabled attic over a centre pavilion (x -40..40, z -280..-220): a window under a
    red arch, a red pediment, a slate roof behind it and a small finial."""
    _backfill(b, [(i, k) for i in (-2, 1) for k in (-13, -12)])
    for y in (-416, -440):
        for i in (-2, 1):
            b.add("3005", "wall", transform((cx(i), y, cx(-14))), "walls")
            b.add("3004", "wall", transform((cx(i), y, -240), rot(y=90)), "walls")
    b.add("60592", "window", transform((0, -440, cx(-14))), "window")
    b.add("60601", "glass", transform((0, -440, cx(-14))), "window", insert=(0, 0, 1))
    b.add("3659", "trim", transform((0, -464, cx(-14))), "arch")
    for i in (-2, 1):
        b.add("3004", "wall", transform((cx(i), -464, -240), rot(y=90)), "arch")
    for k, colour in ((-14, "trim"), (-13, "roof"), (-12, "roof")):
        b.add("3040b", colour, transform((-10, -488, cx(k)), rot(y=90)), "gable")
        b.add("3040b", colour, transform((10, -488, cx(k)), rot(y=-90)), "gable")
    b.add("15573", "trim", transform((0, -496, cx(-14))), "finial")
    b.add("59900", "trim", transform((0, -520, cx(-14))), "finial")
    return b


def turned(b: Batch, a: float) -> Batch:
    """The batch's placements turned by rot(y=a) about the building's centre."""
    out = Batch()
    T = transform((0, 0, 0), rot(y=a))
    for part, colour, M, cat, tag, insert in b.items:
        ins = None if insert is None else tuple(T[:3, :3] @ np.asarray(insert, float))
        out.items.append((part, colour, T @ M, cat, tag, ins))
    return out


def upper_roofs() -> Batch:
    """Wing mansards and centre attics on all four sides."""
    one = Batch()
    wing_mansard(one, 1)
    wing_mansard(one, -1)
    attic(one)
    out = Batch()
    for a in (0, 90, 180, 270):
        out.items += turned(one, a).items
    flat_roof(out)
    return out


def flat_roof(b: Batch):
    """Slate grey tiles on the flat parts of the roof deck."""
    ring = set(exposures())
    free = OUTLINE - ring - WING_MANSARD - ATTIC - PAV_TOWER - TOWER
    sizes = [(2, 6), (2, 4), (2, 2), (1, 6), (1, 4), (1, 3), (1, 2), (1, 1)]
    for r in pack(free, [s for s in sizes if s in TILE and AV.ok(TILE[s], "roof")]):
        p, M = rect_M(TILE, r, Y_DECK - 8)
        b.add(p, "roof", M, "flat")


UPPER_PHASES = [["backfill"], ["walls", "slopes", "dormer", "window"], ["arch", "dormer_roof"],
                ["gable"], ["finial", "crest"], ["flat"]]
UPPER_CAPTIONS = {
    "backfill": "Bricks and plates on the deck behind the cornice",
    "slopes": "Steep slate mansards over the wings, each with a dormer window",
    "walls": "Attics over the centre pavilions: walls round a window",
    "arch": "Red arches over the attic windows", "dormer_roof": "Dormer roofs",
    "gable": "Pediments: red slopes in front, slate slopes behind",
    "finial": "Finials on the pediments", "crest": "Iron cresting along the mansards",
    "flat": "Slate grey tiles on the flat roof"}


# ------------------------------------------------------------------ corner pavilion towers
def ring_cells(i0, i1, k0, k1):
    return [(i, k) for i in range(i0, i1 + 1) for k in range(k0, k1 + 1)
            if i in (i0, i1) or k in (k0, k1)]


def ring_course(b: Batch, box, top, kind, colour, cat, n, skip=()):
    """One course of a rectangular ring wall (box = i0, i1, k0, k1), corners alternating
    between the rows and the columns course by course; `skip` cells are left out."""
    i0, i1, k0, k1 = box
    table = BRICK if kind == "brick" else PLATE1
    lengths = AV.lengths(table, colour)
    rows_own = n % 2 == 0
    lines = []
    for k in (k0, k1):
        cells = [i for i in range(i0, i1 + 1) if (i, k) not in skip and
                 (rows_own or i not in (i0, i1))]
        lines.append(("x", k, cells))
    for i in (i0, i1):
        cells = [k for k in range(k0, k1 + 1) if (i, k) not in skip and
                 (not rows_own or k not in (k0, k1))]
        lines.append(("z", i, cells))
    for axis, key, vals in lines:
        if not vals:
            continue
        for seg in segments(vals):
            pos = seg[0]
            first = (0, 3, 2, 4)[(n + key) % 4]
            for L in split_line(len(seg), lengths, first):
                a, e = pos, pos + L - 1
                r = (a, e, key, key) if axis == "x" else (key, key, a, e)
                p, M = rect_M(PLATE if kind == "plate" else
                              {(1, n): BRICK[n] for n in BRICK}, r, top)
                b.add(p, colour, M, cat)
                pos += L


FLAT_OCULUS = transform((0, 0, 0), rot(x=90))       # the oculus is built lying flat


def oculus(model):
    """A round window: a cross of red plates, a red ring of four 2 x 2 macaroni tiles and
    four black quarter tiles for the glass. Built lying flat, then pressed onto the side
    studs of a pavilion tower's wall."""
    s = model.submodel("oculus", "Oculus")
    for r in ((-1, 0, -2, 1), (1, 1, -1, 0), (-2, -2, -1, 0)):
        p, M = rect_M(PLATE, r, 0)
        s.place(p, "trim").M = M
    s.step("The red ring and the dark glass")
    for q in range(4):
        R = transform((0, 0, 0), rot(y=90 * q))
        s.place("27925", "trim").M = translate(0, -8, 0) @ R @ translate(10, 0, -10)
        s.place("25269", "glass_dark").M = translate(0, -8, 0) @ R @ translate(10, 0, -10)
    return s


PT = (7, 12, -13, -8)                        # the pavilion tower's walls (cells)
PT_COURSES = [(-384, "brick"), (-408, "brick"), (-416, "plate"), (-440, "brick"),
              (-448, "plate"), (-456, "plate"), (-480, "brick")]
OCULUS_Y = -440


def pavilion_tower(model, ocu):
    """A corner pavilion's tower over the front-right pavilion: a 6 x 6 tan stage with an
    oculus on its two outer faces, a red cornice, and a two-stage slate cap with red corner
    ribs, a red band and a finial."""
    s = model.submodel("pavilion_tower", "Pavilion tower")
    b = Batch()
    i0, i1, k0, k1 = PT
    snot = {(i, k0) for i in range(8, 12)} | {(i1, k) for k in range(-12, -8)}
    for n, (top, kind) in enumerate(PT_COURSES):
        skip = snot if top in (-440, -480) else ()
        ring_course(b, PT, top, kind, "wall", f"t{n}", n, skip)
        if skip:
            b.add("30414", "wall", transform((200, top, cx(k0))), f"t{n}")
            b.add("30414", "wall", transform((cx(i1), top, -200), rot(y=-90)), f"t{n}")
    for r in ((6, 13, -14, -13), (6, 13, -8, -7), (6, 7, -12, -9), (12, 13, -12, -9)):
        p, M = rect_M(PLATE, r, -488)
        b.add(p, "trim", M, "cornice")
    for (ci, ck), a in (((12, -13), 0), ((7, -13), 90), ((7, -8), 180), ((12, -8), -90)):
        b.add("3685", "trim", transform((cx(ci), -560, cx(ck)), rot(y=a)), "cap1")
    for i in range(8, 12):
        b.add("4460b", "roof", transform((cx(i), -560, cx(-13))), "cap1")
        b.add("4460b", "roof", transform((cx(i), -560, cx(-8)), rot(y=180)), "cap1")
    for k in range(-12, -8):
        b.add("4460b", "roof", transform((cx(7), -560, cx(k)), rot(y=90)), "cap1")
        b.add("4460b", "roof", transform((cx(12), -560, cx(k)), rot(y=-90)), "cap1")
    b.add("3958", "roof", transform((200, -568, -200)), "flat")
    for r in ((8, 11, -12, -11), (8, 11, -10, -9)):
        p, M = rect_M(TILE, r, -576)
        b.add(p, "roof", M, "flat")
    for x, z, a in ((200, -250, 0), (200, -150, 0), (150, -200, 90), (250, -200, 90)):
        b.add("4083", "crest", transform((x, -616, z), rot(y=a)), "crest")
    for x in (150, 250):
        for z in (-250, -150):
            b.add("3062b", "crest", transform((x, -592, z)), "crest")
            b.add("59900", "crest", transform((x, -616, z)), "crest")
    top = Batch()
    top.items = [it for it in b.items if not it[3].startswith("t")]
    b.items = [it for it in b.items if it[3].startswith("t")]
    phases = [[f"t{n}"] for n in range(len(PT_COURSES))]
    b.emit(s, phases, {"t0": "Pavilion tower: tan walls standing on the roof deck",
                       "t3": "Bricks with side studs for the round windows"}, per_step=8)
    s.step("Press a round window onto each outer face")
    for M in (translate(200, OCULUS_Y, -268) @ FLAT_OCULUS,
              translate(268, OCULUS_Y, -200) @ transform((0, 0, 0), rot(y=-90)) @ FLAT_OCULUS):
        out = M[:3, :3] @ np.array([0.0, -1.0, 0.0])
        s.use(ocu, tuple(M[:3, 3]), M[:3, :3], insert=tuple(out))
    top.emit(s, [["cornice"], ["cap1"], ["flat"], ["crest"]], {
        "cornice": "A red cornice",
        "cap1": "The mansard: steep slate slopes with red corners",
        "flat": "Its flat top", "crest": "Iron cresting: railings and corner posts"},
        per_step=8)
    return s
