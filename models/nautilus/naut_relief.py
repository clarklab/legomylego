"""The hull body at the bubble scale: a spine (the core, two studs wide) carrying the side
keels, deck and keel strips, and on each side, above and below the side keels, a shell of
plates turned studs-out (the "relief"), hollow inside.

* **Core**: a wall two studs wide from the keel strip up to the deck, through the side keels:
  courses of bricks (bricks with studs on their sides where a hull side hangs on it) and two
  plates between them, so the side studs come every two rows. It stops short of the salon,
  which is open from side to side.
* **Relief**: on each side, rows of studs-out plates 20 LDU tall (seven over the side keels,
  eight under them), each row as many layers deep (8 LDU each) as the hull is wide there: the
  cross-section is a lens from the side keels (two studs in from their edge) to the deck's
  edge above and the keel below; its plan follows the side keels' taper. Only the outer
  layers are built (a shell three plates thick), except at the bulkheads and where the hull is
  thin, which go all the way in to the core.

Hull frame (naut_shape): side keels centred on y = 0 (y -8..8), the bow toward -X, port toward
-Z. Cells: column i is x in [20 i, 20 i + 20]."""
from __future__ import annotations

import math
from collections import defaultdict

import numpy as np

import naut_panels as pn
import naut_shape as shp
from brickkit.ldraw.matrix import rot, transform
from naut_kit import (AV, BRICK, PLATE, S, TILE, Batch, cells_of, connected, ids_of, orient,
                      pack, rect_part, runs, side_R)

CORE_HW = 20              # the core: two studs wide
SHELL = 3                 # the hull sides' shell: this many plates thick
NL = 32
X0 = shp.BOW_TIP_X        # the core and hull sides run from the bow tip...
X1 = shp.STERN_X          # ...to where the tail stock starts
SIDE_STUD = {4: "30414", 2: "11211", 1: "87087"}
UP = (0, -1, 0)           # in a flat-built sub-assembly's own frame: pressed on from above


def xc(i: int) -> float:
    return S * i + S / 2


def in_bay(x: float) -> bool:
    return shp.SALON_BAY[0] <= x < shp.SALON_BAY[1]


def bulkhead(i: int) -> bool:
    """Walls across the hull: the bulkheads, and the two columns where the midbody's panels end."""
    x = xc(i)
    ends = (shp.WIDE[0] - 40, shp.WIDE[1])
    return any(b <= x < b + 40 for b in (*shp.BULKHEADS, *ends))


# ------------------------------------------------------------------ the hull's outline
def deck_at(x: float) -> bool:
    return shp.deck_hw(x) > 0


def n_up(x: float) -> int:
    """Rows over the side keels at x: under the deck, or under the traced top line."""
    if deck_at(x):
        return len(shp.UP_ROWS)
    t = shp.top(x)
    return sum(1 for k in range(len(shp.UP_ROWS)) if -32 - 20 * k >= t - 6)


def n_lo(x: float) -> int:
    b = max(shp.bot(x), 0.0)
    if b >= shp.KEEL_TOP:
        return len(shp.LO_ROWS)
    return sum(1 for k in range(len(shp.LO_ROWS)) if 28 + 20 * k <= b + 6)


def core_top(x: float) -> float:
    """The core's top: under the deck, or the plate level just over the highest row."""
    if deck_at(x):
        return shp.CORE_TOP
    n = n_up(x)
    if n == 0:
        return shp.FL_A
    return -8.0 * math.ceil((32 + 20 * (n - 1)) / 8)


def core_bot(x: float) -> float:
    n = n_lo(x)
    if n == 0:
        return shp.FL_B + 8
    return 8.0 * math.ceil((28 + 20 * (n - 1)) / 8)


def in_wide(x: float) -> bool:
    return shp.WIDE[0] <= x < shp.WIDE[1]


def _section_y(x: float, y: float) -> tuple[float, float, float]:
    """(y in the midbody's section that height y at x maps to, w1 here, w1 in the midbody):
    the section is scaled to each column's height, from the side keels to the deck (or the
    core's top) and to the keel strip (or the core's bottom)."""
    if y < 0:
        t, tW = core_top(x), shp.CORE_TOP
        w1 = shp.deck_hw(x) if deck_at(x) else CORE_HW
        eta = (shp.FL_A - y) / (shp.FL_A - t) if t < shp.FL_A else 1.0
        return shp.FL_A - min(max(eta, 0.0), 1.0) * (shp.FL_A - tW), w1, float(shp.DECK_HW)
    b, bW = core_bot(x), float(shp.KEEL_TOP)
    w1 = shp.KEEL_HW if b >= shp.KEEL_TOP else CORE_HW
    eta = (y - shp.FL_B - 8) / (b - shp.FL_B - 8) if b > shp.FL_B + 8 else 1.0
    return shp.FL_B + 8 + min(max(eta, 0.0), 1.0) * (bW - shp.FL_B - 8), w1, float(shp.KEEL_HW)


def body_hw(x: float, y: float) -> float:
    """Half-width of the hull body at (x, y) in the tapers toward the ram and the tail. Its
    width at the side keels follows their plan; its section runs from the midbody's (two flat
    facets over the side keels, two under them, scaled to the hull's height here) at the
    midbody's ends to a rounded lens (a superellipse) a little way along, so toward the ends
    the hull narrows to its top and bottom like a cone instead of keeping straight sides."""
    yW, w1, w1W = _section_y(x, y)
    w0W = W0_MID
    g_mid = min(max((pn.outer_w(yW) - w1W) / (w0W - w1W), 0.0), 1.0)
    w0 = shp.flange_hw(x) * w0W / shp.FLANGE_HW
    if w0 <= w1:
        return w0
    eta = _eta(x, y)
    g_cone = (1.0 - min(eta, 1.0) ** CONE_P) ** (1.0 / CONE_P)
    s = min(_from_wide(x) / CONE_RUN, 1.0) ** 0.5
    return w1 + (w0 - w1) * ((1 - s) * g_mid + s * g_cone)


CONE_P = 1.6              # the tapers' section: |w|^p + |y|^p = 1 (2 is an ellipse)
W0_MID = 207.9            # the midbody's half-width just over the side keels (its panels' face;
                          # fixed, so the tapers and the modules' stations keep their section)
CONE_RUN = 200.0          # ...reached this far along from the midbody's ends


def _from_wide(x: float) -> float:
    return max(shp.WIDE[0] - x, x - shp.WIDE[1], 0.0)


def _eta(x: float, y: float) -> float:
    """How far up (or down) the hull's side height y is at x: 0 at the side keels, 1 at the
    top (the deck, or the traced top line) or the bottom (the keel strip, or the traced
    bottom)."""
    if y < 0:
        top = shp.CORE_TOP if deck_at(x) else min(max(shp.top(x), shp.CORE_TOP), shp.FL_A - 1)
        return (shp.FL_A - y) / (shp.FL_A - top)
    b = shp.bot(x)
    bot = shp.KEEL_TOP if b >= shp.KEEL_TOP else max(b, shp.FL_B + 9)
    return (y - shp.FL_B - 8) / (bot - shp.FL_B - 8)


def wall_hw(y0: float, y1: float) -> float:
    """How far out a bulkhead's wall may reach in the midbody between heights y0 and y1 (inside
    the panels and their hinges)."""
    return min(pn.inner_w(y) for y in np.linspace(y0, y1, 9))


# ------------------------------------------------------------------ the relief plan
# The tapers' rows: curved slopes along the hull (name, depths from the midbody's end outward
# relative to the last base A, the next base relative to A, a small cost per column so curves
# beat flat tiles where they fit the shape as well).
RAMPS = (("tile", (0,), 0, 0.10), ("54200", (-1,), -1, 0.15), ("11477", (0, -1), -1, 0.0),
         ("50950", (-1, -2, -2), -2, 0.0))
RAMP_OFFS = {name: offs for name, offs, _, _ in RAMPS}


def fit_chain(t: list, lb: list, pieces, levels, forced=None, end_w: float = 0.6):
    """A run of columns (from its high end outward) capped by a chain of curved slopes: each
    piece sits on the steps it covers, its high end under the last one's low end. `t`: each
    column's target level (float), `lb` its least; `pieces`: (name, levels outward relative to
    the last piece's base A, the next base relative to A, a cost per column); `forced`
    {column index: piece}: that piece starts there (and nothing else covers it). A dynamic
    programme picks the chain nearest the targets, its last column low (end_w). Returns
    (levels, [(piece, first index, columns)])."""
    forced = forced or {}
    n = len(t)
    dp = [dict() for _ in range(n + 1)]
    for A in levels:
        dp[0][A] = (0.0, None)
    hi = max(levels)
    for k in range(n):
        for A, (c0, _) in dp[k].items():
            for pi, (name, offs, dA, pen) in enumerate(pieces):
                m = len(offs)
                if k + m > n or forced.get(k, name) != name:
                    continue
                if k not in forced and name in forced.values():
                    continue
                if any(k < f < k + m for f in forced):
                    continue
                lv = [A + o for o in offs]
                if any(l < lb[k + j] or l > hi for j, l in enumerate(lv)):
                    continue
                c = c0 + pen * m + sum((l - t[k + j]) ** 2 for j, l in enumerate(lv))
                A2 = A + dA
                if A2 not in dp[k + m] or c < dp[k + m][A2][0]:
                    dp[k + m][A2] = (c, (k, A, pi))
    A = min(dp[n], key=lambda a: dp[n][a][0] + end_w * a * a)
    out, lev, k = [], [0] * n, n
    while k > 0:
        _, (k0, A0, pi) = dp[k][A]
        name, offs = pieces[pi][0], pieces[pi][1]
        for j, o in enumerate(offs):
            lev[k0 + j] = A0 + o
        out.append((name, k0, len(offs)))
        k, A = k0, A0
    return lev, out[::-1]


# where each sits: (its base's offset from the low end's depth, origin at its top or bottom)
RAMP_PART = {"54200": 0, "11477": 0, "50950": 24}


class Relief:
    """Layer counts L[(i, r)] for the rows over (kind 'up') or under ('lo') the side keels."""

    def __init__(self, kind: str):
        self.kind = kind
        self.rows = shp.UP_ROWS if kind == "up" else shp.LO_ROWS
        self.L: dict = {}
        self.extra: dict = {}           # cells thickened so every plate stands (relief_rects)
        target: dict = {}
        for i in range(int(X0 // S), int(X1 // S)):
            x = xc(i)
            nr = n_up(x) if kind == "up" else n_lo(x)
            if in_wide(x):              # the midbody: panels outside; only the bulkheads' walls
                if not bulkhead(i):
                    continue
                for r in range(nr):
                    yr = self.rows[r]
                    n = int((wall_hw(yr - 10, yr + 10) - CORE_HW) // 8)
                    if n > 0:
                        self.L[(i, r)] = min(n, NL)
                continue
            for r in range(nr):
                t = (body_hw(x, self.rows[r]) - CORE_HW) / 8
                lb = 1
                if kind == "up" and r == nr - 1 and deck_at(x):
                    # the row under the deck reaches out past the deck's edge
                    lb = -(-int(shp.deck_hw(x) - CORE_HW) // 8)
                target[(i, r)] = (min(t, NL), lb)
        self.xcaps: dict = {}
        self.fitted = set(target)
        for r in range(len(self.rows)):
            cols = sorted(i for (i, rr) in target if rr == r)
            for run, d in (([i for i in reversed(cols) if xc(i) < 0], 1),
                           ([i for i in cols if xc(i) > 0], -1)):
                if run:
                    self._fit(run, r, target, d)
        # the bow and tail modules' stations: the hull here stops there (laid out whole first,
        # so its section at the station doesn't depend on whether a module is there)
        keep = lambda c: shp.in_hull(xc(c[0])) and not shp.in_quarter(xc(c[0]))
        self.L = {c: l for c, l in self.L.items() if keep(c)}
        self.xcaps = {c: v for c, v in self.xcaps.items() if all(keep(k) for k in v[2])}

    def _fit(self, run: list, r: int, target: dict, d: int):
        """Lay out one row of a taper, from the midbody's end out to the row's end (`run`, its
        columns in that order; d: +1 if amidships is toward +x): its depth in layers column by
        column, as a chain of curved slopes along the hull (fit_chain), the row's end kept
        shallow (its end face shows)."""
        levels, pieces = fit_chain([target[(i, r)][0] for i in run],
                                   [max(1, target[(i, r)][1]) for i in run], RAMPS,
                                   levels=range(1, NL + 1))
        for k, l in enumerate(levels):
            self.L[(run[k], r)] = l
        for name, k0, m in pieces:
            if name != "tile":
                cells = tuple((run[k0 + j], r) for j in range(m))
                self.xcaps[cells[0]] = (name, d, cells)

    def y(self, r: float) -> float:
        return float(np.interp(r, range(len(self.rows)), self.rows))

    def solid(self, i: int, r: int) -> bool:
        """Built all the way in to the core: at the bulkheads and where the hull is thin."""
        return bulkhead(i) or self.L[(i, r)] <= SHELL + 2

    def thick(self, i: int, r: int) -> int:
        """The shell's thickness at a cell: SHELL plates, more where a neighbour is much
        shallower, so neighbouring cells always share a layer (and the shell holds together);
        all the way in where there is no neighbour (the hull's top and bottom rows, its ends),
        so the hollow inside never shows."""
        l = self.L[(i, r)]
        nb = [self.L.get(c, 0) for c in ((i - 1, r), (i + 1, r), (i, r + 1))]
        if r > 0:
            nb.append(self.L.get((i, r - 1), 0))
        return min(l, max(SHELL, l - min(nb) + 1) + self.extra.get((i, r), 0))

    def layer(self, n: int) -> set:
        return {c for c, l in self.L.items()
                if l > n and (n >= l - self.thick(*c) or self.solid(*c))}

    def toward_keel(self) -> int:
        """+1 if the side keels are toward +y from the rows (over them), else -1."""
        return 1 if self.kind == "up" else -1

    def caps(self) -> dict:
        """How each outer face is finished: {cell: (kind, d, cells)} with kind "curved" (a
        curved slope over this cell and the next one toward d, a layer higher, rising to the
        one after, a layer higher again), "cheese" (rising to the next cell toward d, two layers
        higher) or "tile"; d = (columns, rows) toward the side keels first, then along the hull
        toward amidships. The bulkheads' walls in the midbody (seen when the salon is open):
        tiles."""
        H = self.L
        out, done = {}, set()
        for c, (name, d, cells) in self.xcaps.items():
            for k in cells:
                out[k] = ("x" + name, (d, 0), cells)
                done.add(k)
        for c in sorted(H, key=lambda c: (H[c], c)):
            i, r = c
            if c in done:
                continue
            if c in self.fitted:                 # a flat stretch of a taper's row: tiles
                out[c] = ("tile", None, (c,))
                done.add(c)
                continue
            if in_wide(xc(i)):               # a bulkhead's wall in the salon: tiles
                out[c] = ("tile", None, (c,))
                done.add(c)
                continue
            mid = 1 if xc(i) < 0 else -1
            for d in ((0, -1), (mid, 0)):
                n1 = (i + d[0], r + d[1])
                n2 = (i + 2 * d[0], r + 2 * d[1])
                h1 = H.get(n1, 0) if (r + d[1]) >= 0 else H[c]
                h2 = H.get(n2, 0) if (r + 2 * d[1]) >= 0 else H[c]
                if d[1] and h1 == H[c] + 1 and h2 == H[c] + 2 and n1 not in done:
                    out[c] = ("curved", d, (c, n1))
                    done |= {c, n1}
                    break
                if h1 == H[c] + 2:
                    out[c] = ("cheese", d, (c,))
                    done.add(c)
                    break
            else:
                out[c] = ("tile", None, (c,))
                done.add(c)
        return out

    def face(self, i: int, r: int) -> float:
        """|z| of a cell's outer face."""
        return CORE_HW + 8 * self.L[(i, r)]

    def anchors(self) -> set:
        """(i, r): the core's side-stud bricks for this relief, on every other row where the
        relief reaches in to the core (none in the salon)."""
        return {(i, r) for (i, r) in self.layer(0) if r % 2 == 0 and not in_bay(xc(i))}


# ------------------------------------------------------------------ the core
CORE_END = 1180.0          # the core runs on past the stern as the tail stock, to here


def joint_cols() -> dict:
    """{core column: -1 / +1}: the core's last column at a module's station, its brick courses
    1 x 2 bricks with two side studs facing out of the station (-X at the bow, +X at the tail),
    which the module pushes onto (naut_shape.BOW_STATION)."""
    out = {}
    if shp.BOW_MODULE:
        out[int(shp.BOW_STATION // S)] = -1
    if shp.TAIL_MODULE:
        out[int(shp.TAIL_STATION // S) - 1] = 1
    return out


def core_batch(up: Relief, lo: Relief, gap=(), shaft=()) -> Batch:
    """The core, built on the side keels: a wall two studs wide up to the deck and hanging
    under them down to the keel strip, in 8 LDU slots outward from the side keels: every five
    slots a brick course (bricks with side studs where a hull side hangs on it), plates in the
    other two; plates where a brick would stand past the column's end. Past the stern it is
    the tail stock. `gap`: columns whose first brick over the side keels the caller places
    (the propeller's bearing); `shaft`: columns left open under the side keels (the lights'
    lead runs down there to the stand's post)."""
    bt = Batch()
    anchors = {"up": up.anchors(), "lo": lo.anchors()}
    joints = joint_cols()
    cols = [i for i in range(int(X0 // S), int(CORE_END // S))
            if not in_bay(xc(i)) and shp.in_hull(xc(i))]
    bsizes = [s for s in AV.sizes(BRICK, "core") if s[0] <= 2 and s[1] <= 8]
    psizes = [s for s in AV.sizes(PLATE, "core") if s[0] <= 2 and s[1] <= 12]
    for kind in ("up", "lo"):
        sgn = -1 if kind == "up" else 1
        base = shp.FL_A if kind == "up" else shp.FL_B + 8      # the side keels' face
        extent = {i: (0 if kind == "lo" and i in shaft else
                      int(round(abs((core_top(xc(i)) if kind == "up" else core_bot(xc(i)))
                                    - base) / 8))) for i in cols}
        ins = None if kind == "up" else (0, 1, 0)
        cat = "core" if kind == "up" else "core_lo"
        below = None
        nslots = max(extent.values(), default=0)
        s = 0
        while s < nslots:
            course = s % 5 == 0 and s + 3 <= nslots + 3
            bricks, plates = set(), set()
            skip = set(gap) if (kind == "up" and s == 0) else set()
            if course:
                for i in cols:
                    if extent[i] >= s + 3 and i not in skip:
                        bricks.add(i)
            # the slot's outer face (a part's top for 'up', its bottom for 'lo')
            def top_of(n_slots):
                return base - 8 * (s + n_slots) if kind == "up" else base + 8 * s
            if bricks:
                band = s // 5
                jts = {i for i in bricks if i in joints}
                anc = {i for i in bricks if (i, 2 * band) in anchors[kind]
                       or shp.in_quarter(xc(i))} - jts
                for i in jts:                 # the modules' joints
                    R = orient((0, 0, joints[i]), (0, 1, 0))
                    bt.add("11211", "core", transform((xc(i), top_of(3), 0), R),
                           "anchor" if kind == "up" else "anchor_lo", insert=ins)
                for side, k in ((-1, -1), (1, 0)):
                    for i0, i1, _, _ in runs({(i, 0) for i in anc}, (4, 2, 1)):
                        R = None if side < 0 else rot(y=180)
                        bt.add(SIDE_STUD[i1 - i0 + 1], "core",
                               transform((S * (i0 + i1 + 1) / 2, top_of(3), S * k + 10), R),
                               "anchor" if kind == "up" else "anchor_lo", insert=ins)
                cells = {(i, k) for i in bricks - anc - jts for k in (-1, 0)}
                rects = pack(cells, bsizes, below, prefer="x", shift=s) if cells else []
                for i0, i1, k0, k1 in rects:
                    part, R = rect_part(BRICK, i1 - i0 + 1, k1 - k0 + 1)
                    bt.add(part, "core", transform((S * (i0 + i1 + 1) / 2, top_of(3),
                                                    S * (k0 + k1 + 1) / 2), R), cat, insert=ins)
                below = ids_of(rects)
                for i in anc:
                    below[(i, -1)] = below[(i, 0)] = ("anc", i // 4)
                for i in jts:
                    below[(i, -1)] = below[(i, 0)] = ("joint", i)
            # plates for the columns without a brick here, slot by slot
            for t in range(3 if course else 1):
                cells = {(i, k) for i in cols if i not in bricks and extent[i] >= s + t + 1
                         and i not in skip for k in (-1, 0)}
                if not cells:
                    continue
                y_top = base - 8 * (s + t + 1) if kind == "up" else base + 8 * (s + t)
                rects = pack(cells, psizes, below, prefer="x", shift=s + t)
                for i0, i1, k0, k1 in rects:
                    part, R = rect_part(PLATE, i1 - i0 + 1, k1 - k0 + 1)
                    bt.add(part, "core", transform((S * (i0 + i1 + 1) / 2, y_top,
                                                    S * (k0 + k1 + 1) / 2), R), cat, insert=ins)
                below = {**(below or {}), **ids_of(rects, start=10000 * (s + t + 1))}
            s += 3 if course else 1
    return bt


CORE_PHASES = [["anchor", "core"], ["anchor_lo", "core_lo"]]
CORE_HANGING = ("anchor_lo", "core_lo")
CORE_CAPTIONS = {"core": "The core: a wall two studs wide on the side keels",
                 "anchor": "Bricks with side studs: the hull sides hang on them",
                 "core_lo": "The core under the side keels, pushed up one level at a time"}


# ------------------------------------------------------------------ the relief
def relief_frame(side: int) -> np.ndarray:
    """Where a hull side's sub-assembly sits: its local frame has the core's side face as the
    table (y = 0) and its layers stacked up (-y) outward."""
    return transform((0.0, 0.0, side * CORE_HW), side_R(side))


def relief_rects(rel: Relief, xr) -> list[list]:
    """Plates for each layer of the columns with x in xr (see _pack_relief). Built flat, a plate
    stands on the layer under it, down to the core's face, or hangs over the hollow inside from
    the layers over it (pushed up under them): where one would do neither (held only by the
    slopes and tiles on top), the shell under it is thickened a layer and it is all packed
    again."""
    for _ in range(NL):
        layers = _pack_relief(rel, xr)
        loose = {c for n, k in _unheld(layers) for c in cells_of(layers[n][k])
                 if not rel.solid(*c) and rel.L[c] - rel.thick(*c) > 0}
        if not loose:
            break
        for c in loose:
            rel.extra[c] = rel.extra.get(c, 0) + 1
    return layers


def _unheld(layers) -> list:
    """The hanging plates (see _hanging) not held from above either: by no standing or held
    plate of the layer over them."""
    hang = set(_hanging(layers))
    held = set()
    for n in range(len(layers) - 1, -1, -1):
        for k, r in enumerate(layers[n]):
            if (n, k) not in hang:
                continue
            if n + 1 < len(layers) and any(
                    cells_of(r) & cells_of(q) and ((n + 1, j) not in hang or (n + 1, j) in held)
                    for j, q in enumerate(layers[n + 1])):
                held.add((n, k))
    return [p for p in hang if p not in held]


def _hanging(layers) -> list:
    """(layer, index) of the plates that stand on no standing plate of the layer under them."""
    standing, out = set(), []
    for n, rs in enumerate(layers):
        under = set().union(*[cells_of(r) for k, r in enumerate(layers[n - 1])
                              if (n - 1, k) in standing]) if n else set()
        for k, r in enumerate(rs):
            if n == 0 or cells_of(r) & under:
                standing.add((n, k))
            else:
                out.append((n, k))
    return out


def _pack_relief(rel: Relief, xr) -> list[list]:
    """Plates for each layer of the columns with x in xr, bonded to the layer under them;
    tries a few packings until the piece holds together by itself."""
    sizes = [s for s in AV.sizes(PLATE, "hull") if s[0] <= 4 and s[1] <= 12]
    keep = lambda c: xr[0] <= xc(c[0]) < xr[1]
    best = None
    for shift in range(0, 120, 3):
        out = []
        below = {}
        for n in range(NL):
            cells = {c for c in rel.layer(n) if keep(c)}
            if not cells:
                out.append([])
                continue
            above = {c for c in rel.layer(n + 1) if keep(c)}
            rects = pack(cells, sizes, below, prefer="x", shift=shift + n * 5, above=above)
            out.append(rects)
            below = ids_of(rects, start=1000 * (n + 1))
        pieces = connected(out)
        if best is None or pieces < best[0]:
            best = (pieces, out)
        if pieces == 1:
            break
    return best[1]


def build_relief(model, rel: Relief, side: int, xr=(-1e9, 1e9), name=None, title=None):
    sname = "port" if side < 0 else "stbd"
    where = "upper" if rel.kind == "up" else "lower"
    sub = model.submodel(name or f"{where}_{sname}", title or f"Hull side, {where}, {sname}")
    R = side_R(side)
    bt = Batch(relief_frame(side))                     # built flat, layer 0 on the table
    layers = relief_rects(rel, xr)
    # (any plate left over the hollow inside, held by the layer over it, goes in from below,
    # pushed up under it once that is built)
    hanging = set(_hanging(layers))
    for n, rs in enumerate(layers):
        z = side * (CORE_HW + 8 + 8 * n)
        for k, r in enumerate(rs):
            i0, i1, r0, r1 = r
            part, Rl = rect_part(PLATE, i1 - i0 + 1, r1 - r0 + 1)
            pos = (S * (i0 + i1 + 1) / 2, (rel.y(r0) + rel.y(r1)) / 2, z)
            if (n, k) not in hanging:
                bt.add(part, "hull", transform(pos, R @ Rl), f"layer{n}", insert=UP)
            else:
                bt.add(part, "hull", transform(pos, R @ Rl), "hanging", insert=(0, 1, 0))
    _caps(bt, rel, side, xr)
    captions = {f"layer{n}": f"Layer {n + 1}" for n in range(NL)}
    captions["layer0"] = f"The {where} hull side: plates on the core's side studs"
    captions["caps"] = "Curved slopes and tiles: the steps join into a smooth side"
    captions["hanging"] = "Plates pushed up under the outer layers, over the hollow inside"
    bt.emit(sub, phases=[[f"layer{n}" for n in range(NL)], ["hanging"], ["caps"]],
            captions=captions, per_step=10, reach=240, hanging=("hanging",))
    return sub


def cap_R(side: int, toward) -> np.ndarray:
    """A slope on a hull side: its bottom on the relief (local -Y outward), its high side
    (local +Z) toward (dx, dy) in the hull's x-y plane."""
    ey = np.array([0, 0, -side], float)
    ez = np.array([toward[0], toward[1], 0], float)
    return orient(np.cross(ey, ez), ey, ez)


def _caps(bt, rel: Relief, side: int, xr):
    """Curved slopes, cheese slopes and tiles over the relief's outer faces (rows run along y:
    a step toward the side keels is toward (0, rel.toward_keel()) in world x-y)."""
    R = side_R(side)
    keep = lambda c: xr[0] <= xc(c[0]) < xr[1]
    caps = {c: v for c, v in rel.caps().items() if all(keep(k) for k in v[2])}
    tk = rel.toward_keel()

    def zf(c):
        return side * (CORE_HW + 8 * rel.L[c])

    def cy(r):
        return rel.y(r)
    # curved slopes: two columns side by side with the same cap make one 2 x 2 curved slope
    curved = {c: v for c, v in caps.items() if v[0] == "curved"}
    used = set()
    for c in sorted(curved):
        if c in used:
            continue
        kind, d, cells = curved[c]
        (i, r), (i1, r1) = cells
        wd = (d[0], -tk * d[1]) if d[1] else (d[0], 0)     # world (dx, dy)
        pos_x = (xc(i) + xc(i1)) / 2
        pos_y = (cy(r) + cy(r1)) / 2
        nb = (i + 1, r)
        if d[1] and nb in curved and nb not in used and curved[nb][1] == d and \
                rel.L[nb] == rel.L[c] and keep(nb):
            used |= {c, nb}
            bt.add("15068", "hull", transform((pos_x + S / 2, pos_y, zf(c)), cap_R(side, wd)),
                   "caps", insert=UP)
            continue
        used.add(c)
        bt.add("11477", "hull", transform((pos_x, pos_y, zf(c)), cap_R(side, wd)), "caps",
               insert=UP)
    # curved slopes along the hull in the tapers (each on the steps it covers, low end out)
    for c, (kind, d, cells) in caps.items():
        if not kind.startswith("x") or c != cells[0]:
            continue
        part = kind[1:]
        low = cells[-1]                                  # the outer end: the lowest step
        xm = (xc(cells[0][0]) + xc(cells[-1][0])) / 2
        z = side * (CORE_HW + 8 * rel.L[low] + RAMP_PART[part])
        bt.add(part, "hull", transform((xm, cy(low[1]), z), cap_R(side, d)), "caps",
               insert=UP)
    # cheese slopes: in pairs along the hull where they can
    cheese = defaultdict(set)
    for c, (kind, d, _) in caps.items():
        if kind == "cheese":
            cheese[(d, rel.L[c])].add(c)
    for (d, l), cells in cheese.items():
        wd = (d[0], -tk * d[1]) if d[1] else (d[0], 0)
        for i0, i1, r, _ in runs(cells, (2, 1) if d[1] else (1,)):
            part = {2: "85984", 1: "54200"}[i1 - i0 + 1]
            bt.add(part, "hull", transform((S * (i0 + i1 + 1) / 2, cy(r), zf((i0, r))),
                                           cap_R(side, wd)), "caps", insert=UP)
    # tiles
    tiles = defaultdict(set)
    for c, (kind, _, _) in caps.items():
        if kind == "tile":
            tiles[rel.L[c]].add(c)
    lengths = sorted({k[1] for k in AV.sizes(TILE, "hull") if k[0] == 1})
    for l, cells in tiles.items():
        for i0, i1, r, _ in runs(cells, lengths):
            part, Rl = rect_part(TILE, i1 - i0 + 1, 1)
            bt.add(part, "hull", transform((S * (i0 + i1 + 1) / 2, cy(r),
                                            zf((i0, r)) + side * 8), R @ Rl), "caps", insert=UP)


# ------------------------------------------------------------------ the joins' sections
def station_section(which: str) -> dict:
    """The hull's section at a module's station (naut_shape.BOW_STATION / TAIL_STATION), as the
    hull here ends there: {"x", "rows_up" / "rows_lo": [(y0, y1, |z| of the plates' outer face)],
    "core": (z0, z1, y_top, y_bottom), "deck": (half-width, y of its plates' top, y of its
    tiles' top) or None, "flange": (half-width, y top, y bottom), "keel": y of the keel under
    the core's underside}. The hull sides' faces carry curved slopes or tiles 8 to 24 LDU
    further out."""
    import naut_keel as keel
    x0 = shp.BOW_STATION if which == "bow" else shp.TAIL_STATION
    i = int(x0 // S) if which == "bow" else int(x0 // S) - 1        # the wall's outer column
    x = xc(i)
    out = {"x": x0}
    for kind in ("up", "lo"):
        rel = Relief(kind)
        out["rows_" + kind] = [(y - 10, y + 10, float(CORE_HW + 8 * rel.L[(i, r)]))
                               for r, y in enumerate(rel.rows) if (i, r) in rel.L]
    out["core"] = (-CORE_HW, CORE_HW, core_top(x), core_bot(x))
    out["deck"] = ((shp.deck_hw(x), shp.DECK_STRIP - 8, shp.DECK_STRIP - 16)
                   if deck_at(x) else None)
    out["flange"] = (shp.flange_hw(x0), shp.FL_A - 8 + 8, shp.FL_B + 8)
    plan = keel.saw_plan() if which == "bow" else keel.stern_keel_plan()
    out["keel"] = float(8 * dict(zip(plan[0], plan[1]))[i])
    return out


# ------------------------------------------------------------------ the quarters' interface
def course_studs(x: float) -> list:
    """y of the side studs on the core's faces at x: one row in each of its brick courses (four
    courses of five slots over the side keels, as many under them as the core reaches)."""
    out = []
    for kind, base in (("up", shp.FL_A), ("lo", shp.FL_B + 8)):
        sgn = -1 if kind == "up" else 1
        end = core_top(x) if kind == "up" else core_bot(x)
        extent = int(round(abs(end - base) / 8))
        for s in range(0, extent, 5):
            if s + 3 <= extent:
                top = base - 8 * (s + 3) if kind == "up" else base + 8 * s
                out.append(top + 10)
    return sorted(out)


def quarter_interface() -> dict:
    """What the quarters module (naut_shape.QUARTERS) hangs its skins on and must meet, all in
    the hull frame. Per column of each quarter (its middle x):

    * "studs": [(x, y, z)] the core's side studs, facing out of its faces (z = -20 port, +20
      starboard; the studs stand 4 LDU out): every column, every brick course (course_studs).
    * "core": {x: (y top, y bottom)}: the core, two studs wide (z -20 .. 20), from the deck (or
      the stern's ridge) down to the keel strip (or the keels).
    * "deck": {x: (half-width, y of its tiles' top, y of its underside)} or nothing where there
      is no deck (aft of x 780 the stern's ridge, two studs wide, is on the core).
    * "flange": {x: (upper layer's half-width, lower layer's half-width)}: the side keels, y -8
      .. 8; wedge plates make the upper layer's edge. Their top studs and underside in the
      quarters are left bare for the skins (the last tiles cover what the skins leave).
    * "keel": {x: y of the underside of what hangs under the core}: the keel strip (6 studs
      wide, at x -520 .. 520), the saw keel and the stern's keel (2 studs wide).
    * "panels_end": the midbody's panels' section where they end (x -480 and 360): for each
      facet (a, b over the side keels; c, d under them) its outer face (tiles' top) as
      [(|z|, y), ...] from its first hinge line to its second, lips included.
    """
    import naut_frame as frame
    import naut_keel as keel
    import naut_panels as pn
    out = {"quarters": shp.QUARTERS, "studs": [], "core": {}, "deck": {}, "flange": {},
           "keel": {}}
    _, lower_w = {}, {}
    cells_b, _ = frame.keel_plan(lower=True)
    for i, k in cells_b:
        lower_w[i] = max(lower_w.get(i, 0), abs(S * k + (S if k >= 0 else 0)))
    plans = [keel.clip_plan(*keel.saw_plan()), keel.clip_plan(*keel.stern_keel_plan())]
    deep = {c: 8 * d for cols, depths, _, _ in plans for c, d in zip(cols, depths)}
    for x0, x1 in shp.QUARTERS:
        for i in range(int(x0 // S), int(x1 // S)):
            x = xc(i)
            if not shp.in_hull(x):
                continue
            for y in course_studs(x):
                if i in joint_cols():
                    continue
                out["studs"] += [(x, y, -CORE_HW), (x, y, CORE_HW)]
            out["core"][x] = (core_top(x), core_bot(x))
            if deck_at(x):
                out["deck"][x] = (shp.deck_hw(x), shp.DECK_STRIP - 16, shp.DECK_STRIP + 8)
            out["flange"][x] = (shp.flange_hw(x), float(lower_w.get(i, 0)))
            if -520 <= x < 520:
                out["keel"][x] = float(keel.BELLY)
            elif i in deep:
                out["keel"][x] = float(deep[i])
    out["panels_end"] = pn.end_section()
    return out
