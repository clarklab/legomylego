"""Roofs: the deck over the walls with the red cornice; a steep slate mansard along each
facade with an arched dormer over each wing (and, on the sides, over each dome pavilion) and
a gabled attic over each entrance; tall cream chimneys rising above it; the four corner
pavilions' mansards (a pedimented dormer on each outer face, a flat top crowned with iron
cresting); slate grey tiles on the flat roof.

Heights (y): wall top -496; deck -496..-512 (two plate layers over the whole building, the
outer ring tan then red); cornice: red inverted slopes -512..-536 on the outer ring, red
plates -536..-544 over it and the overhang, red tiles on the overhang -544..-552. The flat
roof inside is tiled slate grey at -512..-520."""
from __future__ import annotations

import numpy as np

from brickkit.ldraw.matrix import rot, transform, translate
from kit import (AV, BRICK, PLATE, PLATE1, TILE, TILE1, Batch, n_pieces, pack, rect_M,
                 segments, split_line, weave)
import base

DIRS = [(0, -1), (1, 0), (0, 1), (-1, 0)]
FACE_ROT = {(0, -1): 0, (1, 0): -90, (0, 1): 180, (-1, 0): 90}   # rot(y) turning -Z to d
Y_DECK = -512
Y_CORNICE = -544          # top of the cornice plates


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
TOWER = {(i, k) for i in range(-5, 5) for k in range(-5, 5)}            # the belfry
DOME0 = {(i, k) for i in range(3, 13) for k in range(-24, -14)}         # front-right dome
DOME_DX = -320                                                          # to the front-left
DOME_RING0 = {(i, k) for i, k in DOME0 if i in (3, 12) or k in (-24, -15)}
DOMES = set()
for _a in (0, 180):
    DOMES |= base.turn(DOME0 | {(i - 16, k) for i, k in DOME0}, _a)
ON_CORNICE = DOMES - base.BUILDING        # stage cells standing on the cornice's overhang
CP0 = {(i, k) for i in range(16, 24) for k in range(-24, -16)}          # front-right pavilion
CORNER_ROOFS = base.all_sides(CP0)
ATTIC_I = (-2, -1, 0, 1)                    # over the entrance
ROW = -23                                   # the set-back facade row (wings, entrance)
CHIMNEYS0 = [((-16, -15), -20), ((14, 15), -20)]
YC0 = Y_CORNICE                             # upper roofs start on the cornice's top


def mansard_plan(domes: bool):
    """(steep slope cells, low slope cells, dormer pairs) of one facade's mansard. Front and
    back: over the wings only (the domes stand on the dome pavilions and the entrance keeps
    its attic), an arched dormer on the outer two cells and a low 45-degree slope next to
    the dome's stage (clear of its side window); the sides: steep slopes all along, with
    dormers over the wings and the dome pavilions."""
    if domes:
        return [], [-14, 13], [(-16, -15), (14, 15)]
    slopes = [i for i in range(-16, 16) if i not in ATTIC_I
              and i not in (-15, -14, 13, 14, -9, -8, 7, 8)]
    return slopes, [], [(-15, -14), (-9, -8), (7, 8), (13, 14)]


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
        p, M = rect_M(PLATE, r, Y_DECK + 8)
        b.add(p, "wall", M, "deck1")
    for r in pack(inner, ok, shift=3 + 7 * v):
        p, M = rect_M(PLATE, r, Y_DECK + 8)
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
    edge = (over | corners) - ON_CORNICE          # (the domes' stages stand on those plates)
    for r in weave(edge, "x", AV.lengths(TILE1, "trim"), 1):
        p, M = rect_M(TILE, r, Y_CORNICE - 8)
        b.add(p, "trim", M, "cornice3")
    return b


DECK_PHASES = [["deck1", "deck2"], ["cornice"], ["cornice2"], ["cornice3"]]


# ------------------------------------------------------------------ upper roofs
def _backfill(b: Batch, cells, cat="backfill", colour="core"):
    """A brick and a plate on the deck (Y_DECK) so a roof piece can start at the cornice's
    top (Y_CORNICE)."""
    ring = set(exposures())
    for i, k in cells:
        if (i, k) in ring or (i, k) not in OUTLINE:     # the cornice's plates are there
            continue
        b.add("3005", colour, transform((cx(i), Y_DECK - 24, cx(k))), cat)
        b.add("3024", colour, transform((cx(i), Y_CORNICE, cx(k))), cat)


def turned(b: Batch, a: float) -> Batch:
    """The batch's placements turned by rot(y=a) about the building's centre."""
    out = Batch()
    T = transform((0, 0, 0), rot(y=a))
    for part, colour, M, cat, tag, insert in b.items:
        ins = None if insert is None else tuple(T[:3, :3] @ np.asarray(insert, float))
        out.items.append((part, colour, T @ M, cat, tag, ins))
    return out


def dormer(b: Batch, x: float, z_face: float, colour_face="trim", tall=False, arched=False):
    """A dormer on a slope whose low cell is at z_face (the front, -Z), standing on the
    cornice's top. `arched`: a round-topped window (1 x 2 x 2 2/3) with a dark lattice pane,
    slate cheeks and a slate tile behind it, as tall as the steep mansard. Otherwise a
    window (1 x 2 x 2, or 1 x 2 x 3 when `tall`) with tan cheeks behind it and a little
    gable of two cheese slopes, red in front."""
    zf, zb = z_face, z_face + 20
    if arched:
        M = transform((x, YC0 - 64, zf))
        b.add("30044", "window", M, "dormer")
        b.add("30046", "glass_dark", M @ translate(0, 24, 4), "dormer", insert=(0, 0, 1))
        for n in range(2):                      # after the pane, which goes in from behind
            b.add("3004", "roof", transform((x, YC0 - 24 * (n + 1), zb)), "dormer_back")
        for n in range(2):
            b.add("3023", "roof", transform((x, YC0 - 56 - 8 * n, zb)), "dormer_back")
        b.add("3069b", "roof", transform((x, YC0 - 72, zb)), "dormer_roof")
        return
    h = 72 if tall else 48
    win, glass = ("60593", "60602") if tall else ("60592", "60601")
    b.add(win, "window", transform((x, YC0 - h, zf)), "dormer")
    b.add(glass, "glass", transform((x, YC0 - h, zf)), "dormer", insert=(0, 0, 1))
    for n in range(h // 24):
        b.add("3004", "wall", transform((x, YC0 - 24 * (n + 1), zb)), "dormer")
    for z, colour in ((zf, colour_face), (zb, "roof"))[:1 if tall else 2]:
        b.add("54200", colour, transform((x - 10, YC0 - h, z), rot(y=90)), "dormer_roof")
        b.add("54200", colour, transform((x + 10, YC0 - h, z), rot(y=-90)), "dormer_roof")


def attic(b: Batch):
    """The gabled attic over the entrance bay (x -40..40, its face on the wall row): a window
    under a red arch, a red pediment, a slate roof behind it and a finial."""
    zf = cx(ROW)
    _backfill(b, [(i, k) for i in (-2, 1) for k in (ROW + 1, ROW + 2)])
    for y in (YC0 - 24, YC0 - 48):
        for i in (-2, 1):
            b.add("3005", "wall", transform((cx(i), y, zf)), "walls")
            b.add("3004", "wall", transform((cx(i), y, zf + 30), rot(y=90)), "walls")
    b.add("60592", "window", transform((0, YC0 - 48, zf)), "window")
    b.add("60601", "glass", transform((0, YC0 - 48, zf)), "window", insert=(0, 0, 1))
    b.add("3659", "trim", transform((0, YC0 - 72, zf)), "arch")
    for i in (-2, 1):
        b.add("3004", "wall", transform((cx(i), YC0 - 72, zf + 30), rot(y=90)), "arch")
    for dz, colour in ((0, "trim"), (20, "roof"), (40, "roof")):
        b.add("3040b", colour, transform((-10, YC0 - 96, zf + dz), rot(y=90)), "gable")
        b.add("3040b", colour, transform((10, YC0 - 96, zf + dz), rot(y=-90)), "gable")
    b.add("15573", "trim", transform((0, YC0 - 104, zf)), "finial")
    b.add("59900", "trim", transform((0, YC0 - 128, zf)), "finial")


def main_mansard(b: Batch, domes: bool):
    """One facade's mansard: steep (75-degree) slate slopes whose low cells stand on the
    cornice (or on backfill behind the projecting bays) along the set-back row, arched
    dormers, the attic over the entrance and two chimneys behind, rising above it. With
    `domes` (front and back), the rings of the domes' stages are backfilled up to the
    cornice's top for the stages to stand on."""
    slopes, low, dormers = mansard_plan(domes)
    cells = slopes + low + [i for pair in dormers for i in pair]
    _backfill(b, [(i, k) for i in cells for k in (ROW, ROW + 1)])
    for i in slopes:
        b.add("4460b", "roof", transform((cx(i), YC0 - 72, cx(ROW + 1))), "slopes")
    for i in low:
        b.add("3040b", "roof", transform((cx(i), YC0 - 24, cx(ROW + 1))), "slopes")
    for i0, i1 in dormers:
        dormer(b, (cx(i0) + cx(i1)) / 2, cx(ROW), arched=True)
    attic(b)
    if domes:
        _backfill(b, sorted(DOME_RING0 | {(i - 16, k) for i, k in DOME_RING0}),
                  cat="dome_base")
    for (i0, i1), k in CHIMNEYS0:                       # chimneys: tan, red caps
        x = (cx(i0) + cx(i1)) / 2
        for n in range(8):
            b.add("98283", "wall", transform((x, Y_DECK - 24 - 24 * n, cx(k))), "chimney")
        b.add("3023", "trim", transform((x, Y_DECK - 200, cx(k))), "chimney_cap")
        b.add("3069b", "trim", transform((x, Y_DECK - 208, cx(k))), "chimney_cap")


def roof_cells_front(domes: bool) -> set:
    """Deck cells one facade's upper roofs stand on (for the flat roof's tiles)."""
    slopes, low, dormers = mansard_plan(domes)
    cells = {(i, k) for i in slopes + low + [i for p in dormers for i in p]
             for k in (ROW, ROW + 1)}
    cells |= {(i, k) for i in ATTIC_I for k in (ROW, ROW + 1, ROW + 2)}
    cells |= {(i, k) for (pair, k) in CHIMNEYS0 for i in pair}
    return cells


def upper_roofs() -> Batch:
    """Mansards, dormers, attics and chimneys on all four sides (the domes' bases on the
    front and back), and slate tiles on the flat roof."""
    out = Batch()
    busy = TOWER | DOMES | CORNER_ROOFS
    for a in (0, 90, 180, 270):
        domes = a in (0, 180)
        one = Batch()
        main_mansard(one, domes)
        out.items += turned(one, a).items
        busy |= base.turn(roof_cells_front(domes), a)
    flat_roof(out, busy)
    return out


def flat_roof(b: Batch, busy: set):
    """Slate tiles on the flat parts of the roof deck."""
    free = OUTLINE - set(exposures()) - busy
    sizes = [(2, 6), (2, 4), (2, 2), (1, 6), (1, 4), (1, 3), (1, 2), (1, 1)]
    for r in pack(free, [s for s in sizes if s in TILE and AV.ok(TILE[s], "roof")]):
        p, M = rect_M(TILE, r, Y_DECK - 8)
        b.add(p, "roof", M, "flat")


UPPER_PHASES = [["backfill", "dome_base"], ["walls", "slopes", "dormer", "window", "chimney"],
                ["arch", "dormer_back", "dormer_roof", "chimney_cap"], ["gable"], ["finial"],
                ["flat"]]
UPPER_CAPTIONS = {
    "backfill": "Bricks and plates on the deck behind the cornice (and where the domes' "
                "stages will stand)",
    "slopes": "The steep slate mansard along each facade, with arched dormers",
    "walls": "Attics over the entrances: walls round a window",
    "chimney": "Tall chimneys of rough-faced bricks",
    "arch": "Red arches over the attic windows",
    "dormer_back": "Slate cheeks behind the dormers' windows",
    "dormer_roof": "Tiles on top",
    "chimney_cap": "Red chimney caps",
    "gable": "Pediments: red slopes in front, slate slopes behind",
    "finial": "Finials on the pediments", "flat": "Slate grey tiles on the flat roof"}


# ------------------------------------------------------------------ corner pavilion roofs
def corner_roof() -> Batch:
    """The front-right corner pavilion's mansard (cells 16..23 x -24..-17), covering the
    whole pavilion: one ring of steep (75-degree) slate slopes on the cornice with a tall
    dormer on each outer face, rising to a flat 6 x 6 top crowned with iron cresting."""
    b = Batch()
    i0, i1, k0, k1 = 16, 23, -24, -17
    xc, zc = (cx(i0) + cx(i1)) / 2, (cx(k0) + cx(k1)) / 2           # 400, -400
    box = {(i, k) for i in range(i0, i1 + 1) for k in range(k0, k1 + 1)}
    _backfill(b, sorted(box))
    inner = {(i, k) for i in range(i0 + 2, i1 - 1) for k in range(k0 + 2, k1 - 1)}   # 4 x 4
    for i, k in sorted(inner):
        for n in range(3):
            b.add("3005", "core", transform((cx(i), YC0 - 24 - 24 * n, cx(k))), "core")
    for (ci, ck), a in (((i1 - 1, k0 + 1), 0), ((i0 + 1, k0 + 1), 90), ((i0 + 1, k1 - 1), 180),
                        ((i1 - 1, k1 - 1), -90)):
        b.add("3685", "roof", transform((cx(ci), YC0 - 72, cx(ck)), rot(y=a)), "slopes")
    for i in range(i0 + 2, i1 - 1):
        if i not in (19, 20):
            b.add("4460b", "roof", transform((cx(i), YC0 - 72, cx(k0 + 1))), "slopes")
        b.add("4460b", "roof", transform((cx(i), YC0 - 72, cx(k1 - 1)), rot(y=180)), "slopes")
    for k in range(k0 + 2, k1 - 1):
        b.add("4460b", "roof", transform((cx(i0 + 1), YC0 - 72, cx(k)), rot(y=90)), "slopes")
        if k not in (-21, -20):
            b.add("4460b", "roof", transform((cx(i1 - 1), YC0 - 72, cx(k)), rot(y=-90)),
                  "slopes")
    dormer(b, xc, cx(k0), tall=True)                                 # front face
    side = Batch()
    dormer(side, 0, cx(k0), tall=True)                               # right face
    T = transform((0, 0, zc), rot(y=-90))
    for part, colour, M, cat, tag, insert in side.items:
        ins = None if insert is None else tuple(T[:3, :3] @ np.asarray(insert, float))
        b.items.append((part, colour, T @ M, cat, tag, ins))
    top = YC0 - 80                                                   # the flat top
    b.add("3958", "roof", transform((xc, top, zc)), "top")
    for dx in (-20, 20):
        for dz in (-20, 20):
            b.add("3068b", "roof", transform((xc + dx, top - 8, zc + dz)), "top2")
    for (x, z) in ((xc - 50, zc - 50), (xc + 50, zc - 50), (xc - 50, zc + 50),
                   (xc + 50, zc + 50)):
        b.add("3062b", "crest", transform((x, top - 24, z)), "crest")
        b.add("59900", "crest", transform((x, top - 48, z)), "crest")
    for x, z, a in ((xc, zc - 50, 0), (xc, zc + 50, 0), (xc - 50, zc, 90), (xc + 50, zc, 90)):
        b.add("4083", "crest", transform((x, top - 48, z), rot(y=a)), "crest")
    return b


def corner_roofs() -> Batch:
    one = corner_roof()
    out = Batch()
    for a in (0, 90, 180, 270):
        out.items += turned(one, a).items
    return out


CORNER_PHASES = [["backfill", "core"], ["slopes", "dormer"], ["dormer_roof"],
                 ["top"], ["top2", "crest"]]
CORNER_CAPTIONS = {
    "backfill": "The corner pavilions' roofs: bricks and plates on the deck",

    "slopes": "Mansards over the whole pavilion: steep slate slopes and a tall dormer on "
              "each outer face", "dormer_roof": "Little red pediments over the dormers",
    "top": "Flat tops", "crest": "Iron cresting: railings and corner posts"}




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
    """A round window, 6 x 6: a round red plate, a red frame of four quarter-ring plates on
    it and dark glass of macaroni and quarter tiles inside the frame. Built lying flat, then
    pressed onto the side studs of a dome's stage."""
    s = model.submodel("oculus", "Round window")
    s.place("11213", "trim", (0, 0, 0))
    s.step("The red frame and the dark glass")
    up = translate(0, -8, 0)
    for q in range(4):
        R = transform((0, 0, 0), rot(y=90 * q))
        s.place("68568", "trim").M = up @ R @ translate(10, 0, 10)
        s.place("27925", "glass_dark").M = up @ R @ translate(10, 0, -10)
        s.place("25269", "glass_dark").M = up @ R @ translate(10, 0, -10)
    return s
