"""The midbody's sides: large tiled panels on clip-and-bar hinges, at the hull's real angles.

Over the constant midbody (naut_shape.WIDE) each side of the hull is four flat facets, two over
the side keels and two under them, a chain of hinges in the hull's cross-section:

    deck's edge (bar) - facet b - seam S - facet a - side keels (bar)
    side keels (bar)  - facet c - seam S' - facet d - keel strip's edge (bar)

Each facet is a panel four studs wide: a long 4 x N plate, 1 x 2 hinge plates under it at
its two edges (a clip, 63868, or a bar, 60478, ten LDU past the plate's edge), and tiles on top.
Two facets meet on one hinge line (one's bar in the other's clips); the chain's ends clip onto
bars set into the side keels, the deck strip and the keel strip. Given the two ends and the
facets' widths the chain closes in one way: that fixes the seam, so the hull's cross-section is
a lens of four flat faces, like the photo's plating (the seam over the side keels runs where its
line of vents does).

Geometry here is in the hull's cross-section, (w, y): w = |z| (outward), y down. A point at
distance t along a facet from its first hinge line P, s out from it (s: the panel's outward
normal), is P + t d + s n. Through a panel: hinge plates s -6..2, the plate 2..10, tiles 10..18.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

import naut_shape as shp
from brickkit.ldraw.matrix import rot, transform
from naut_kit import AV, PLATE, S, TILE, Batch, bbox, connected, ids_of, orient, pack, rect_part

CLIP, BAR = "63868", "60478"      # 1 x 2 plates with a clip / a bar on the end
S_HINGE, S_PLATE, S_TILE, S_TOP = -6.0, 2.0, 10.0, 18.0   # a panel's layers (s of their bottoms)
UP = (0, -1, 0)


# ------------------------------------------------------------------ the chains
def seam(spec) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(B, S, T): a chain's first hinge, its seam and its last hinge, (w, y). The seam is where
    two facets of the given widths (hinge to hinge: 20 n + 20) meet, bulging outward."""
    (bw, by), (n1, n2), (tw, ty) = spec
    B, T = np.array([bw, by], float), np.array([tw, ty], float)
    L1, L2 = S * (n1 + 1), S * (n2 + 1)
    d = float(np.linalg.norm(T - B))
    u = (T - B) / d
    a = (L1 ** 2 - L2 ** 2 + d ** 2) / (2 * d)
    h = float(np.sqrt(L1 ** 2 - a ** 2))
    p = np.array([-u[1], u[0]])
    if p[0] < 0:
        p = -p
    return B, B + a * u + h * p, T


@dataclass
class Facet:
    name: str
    P: np.ndarray           # first hinge line (w, y)
    Q: np.ndarray           # second hinge line
    n: int                  # width in studs (hinge to hinge: 20 n + 20)
    ends: tuple             # (at P, at Q): "clip" or "bar" on the panel

    @property
    def d(self) -> np.ndarray:
        v = self.Q - self.P
        return v / np.linalg.norm(v)

    @property
    def nrm(self) -> np.ndarray:
        """Outward normal (away from the hull's middle)."""
        d = self.d
        p = np.array([-d[1], d[0]])
        return p if p[0] > 0 else -p

    @property
    def L(self) -> float:
        return S * (self.n + 1)

    def at(self, t: float, s: float) -> np.ndarray:
        return self.P + t * self.d + s * self.nrm


def facets() -> dict[str, Facet]:
    B, Sa, T = seam(shp.CHAIN_UP)
    B2, Sc, K = seam(shp.CHAIN_LO)
    nu, nl = shp.CHAIN_UP[1], shp.CHAIN_LO[1]
    return {"a": Facet("a", B, Sa, nu[0], ("clip", "bar")),
            "b": Facet("b", Sa, T, nu[1], ("clip", "clip")),
            "c": Facet("c", B2, Sc, nl[0], ("clip", "bar")),
            "d": Facet("d", Sc, K, nl[1], ("clip", "clip"))}


FACETS = facets()
FACETS_N = {k: f.n for k, f in FACETS.items()}


def to_world(x: float, wy, side: int) -> np.ndarray:
    return np.array([x, wy[1], side * wy[0]], float)


def vec3(v, side: int) -> np.ndarray:
    return np.array([0.0, v[1], side * v[0]])


# ------------------------------------------------------------------ the section
def _profile(s: float, upper: bool) -> tuple[np.ndarray, np.ndarray]:
    """The section's outline at offset s from the hinge lines, as (y, w) points sorted by y:
    the two facets' ends, joined across the seam."""
    keys = ("a", "b") if upper else ("c", "d")
    pts = [FACETS[k].at(t, s) for k in keys for t in (0.0, FACETS[k].L)]
    pts.sort(key=lambda p: p[1])
    return np.array([p[1] for p in pts]), np.array([p[0] for p in pts])


def outer_w(y: float) -> float:
    """The hull's half-width at height y in the midbody (the panels' tiles): the upper facets
    over the side keels, the lower ones under them (straight across their seam)."""
    ys, ws = _profile(S_TOP, y < 0)
    return float(np.interp(y, ys, ws))


def inner_w(y: float, clear: float = 4.0) -> float:
    """How far out structure inside the midbody may reach at height y (the hinge plates' inner
    faces, less a little room)."""
    ys, ws = _profile(S_HINGE, y < 0)
    return float(np.interp(y, ys, ws)) - clear


# ------------------------------------------------------------------ the layout
# The midbody's panels along the hull: three lengths (ahead of the salon, the salon, aft of it);
# the facets next to the side keels (a, c) leave a gap for each window's boss. The salon's
# upper panels on the port side are one piece, hinged at the deck's edge (the gull wing).
SEGMENTS = ((-480.0, -280.0), (-280.0, 200.0), (200.0, 360.0))
BAY = SEGMENTS[1]
# the hinges along each length (x of their columns): clear of the bulkheads' walls
HINGES = {(-480.0, -280.0): (-450.0, -390.0, -330.0), (200.0, 360.0): (230.0, 330.0),
          (-280.0, shp.BOSS_X[0]): (-250.0, -230.0), (shp.BOSS_X[1], 200.0): (110.0, 170.0),
          BAY: (-250.0, -30.0, 170.0)}


def pieces(key: str) -> list[tuple[float, float]]:
    """The panels of facet `key` along the hull (x0, x1)."""
    if key in "ac":
        return [SEGMENTS[0], (BAY[0], shp.BOSS_X[0]), (shp.BOSS_X[1], BAY[1]), SEGMENTS[2]]
    return list(SEGMENTS)


def hinge_x(key: str, x0: float, x1: float) -> tuple[list, list]:
    """(hinges on the panel's first edge, on its second edge). Facets b and d meet a and c at
    the seam: there their hinges are a's and c's. A facet three studs wide has the hinge plates
    of its two edges a column apart (they would overlap in one)."""
    own = list(HINGES[(x0, x1)])
    if key in "ac":
        return own, own
    seam = sorted(x for p in pieces("a") for x in HINGES[p] if x0 <= x < x1)
    if FACETS_N[key] < 4:
        own = [x + S if x + S not in seam else x - S for x in own]
    return seam, own


def frame_stations(key: str) -> list[float]:
    """x of the bars on the hull's frame that facet `key`'s panels clip onto (a: the side keels,
    over them; b: the deck; c: the side keels, under them; d: the keel strip)."""
    i = 0 if key in "ac" else 1
    return sorted(x for p in pieces(key) for x in hinge_x(key, *p)[i])


# ------------------------------------------------------------------ a panel
def facet_R(f: Facet, side: int) -> np.ndarray:
    """A plate's rotation on facet f: its length along the hull (local X), studs outward."""
    return orient((1.0, 0.0, 0.0), -vec3(f.nrm, side))


def panel_frame(f: Facet, side: int, x0: float) -> np.ndarray:
    """A panel's own frame: built flat, the table its plate's underside (s = 2), x from x0."""
    M = np.eye(4)
    M[:3, :3] = facet_R(f, side)
    M[:3, 3] = to_world(x0, f.at(0, S_PLATE), side)
    return M


def hinge_R(f: Facet, side: int, at_q: bool) -> np.ndarray:
    """A hinge plate under a panel: its clip / bar end (local +X) toward the edge."""
    ex = vec3(f.d, side) * (1 if at_q else -1)
    return orient(ex, -vec3(f.nrm, side))


def stations(x0: float, x1: float, avoid=()) -> list[float]:
    """Where a panel from x0 to x1 has its hinges: its second and last-but-one columns, and
    one in between when it is long; none in the x ranges `avoid`."""
    n = int(round((x1 - x0) / S))
    cols = [1, n - 2] if n >= 4 else [n // 2]
    if n >= 10:
        cols.append(n // 2)
    xs = sorted({x0 + S * c + S / 2 for c in cols})
    return [x for x in xs if not any(a <= x < b for a, b in avoid)]


PANEL_TILES = ((2, 6), (2, 4), (2, 2), (1, 8), (1, 6), (1, 4), (1, 2), (1, 1))


def build_panel(model, name: str, title: str, f: Facet, side: int, x0: float, x1: float,
                hinges=None, ends=None, ext=None, lips=(False, False), role: str = "hull",
                ribs=(False, False)):
    """A facet's panel from x0 to x1: its plates, hinge plates on its two edges (`hinges`:
    (x list on its first edge, x list on its second); `ends`: (P end, Q end), each "clip",
    "bar" or None) and tiles. `ext` (xa, xb, n): n more studs of panel past its first edge
    between xa and xb. `lips` (at P, at Q): a stud more past that edge, over the hinge line,
    closing the seam (at each hinge only its tiles, bridging over the hinge from the lip's plates
    either side; on the seam's side of a and c returned as `late` [(part, world M)], to go on
    after the facet hinged there). `ribs` (at x0, at x1): over the end column, plates in the
    tiles' layer and on them tiles two studs wide reaching a stud past the end: a rib a plate
    proud, over the joint with a panel on another grid (the slot two grids leave there); those
    tiles go on after that panel (RIB_TILES, hull frame). Built flat in its own frame
    (panel_frame); returns (sub, M, late)."""
    ends = f.ends if ends is None else ends
    hp, hq = hinge_x(f.name, x0, x1) if hinges is None else hinges
    sub = model.submodel(name, title)
    M = panel_frame(f, side, x0)
    bt = Batch(M)
    R = facet_R(f, side)
    ncol = int(round((x1 - x0) / S))
    col = lambda x: int(round((x - S / 2 - x0) / S))
    main = {(i, j) for i in range(ncol) for j in range(f.n)}
    rib_cols = {i: d for i, d, on in ((0, -1, ribs[0]), (ncol - 1, 1, ribs[1])) if on}
    extra = set()
    if ext:
        xa, xb, ne = ext
        extra |= {(i, j) for i in range(int(round((xa - x0) / S)), int(round((xb - x0) / S)))
                  for j in range(-ne, 0)}
    # the lips' notches round the hinges: tiles bridge them (no plate: the hinge is there). On
    # the seam's side of a and c the facet hinged there (b, d) still has to clip on through the
    # notch: those tiles go on afterwards (returned as `late`), each a 2 x 2 reaching out over
    # it from the panel's last row.
    over, late_cells, late = set(), set(), []
    for at_q, on, xs in ((False, lips[0], hp), (True, lips[1], hq)):
        if on:
            j = f.n if at_q else -1
            notch = {col(x) for x in xs}
            if at_q and f.name in "ac":
                # a 2 x 2 tile over the hinge's column and the next, on the panel's last row
                # (the lip there left out): it reaches out over the hinge
                for i in sorted(notch):
                    if late and i <= late[-1] + 1:
                        continue                 # (two hinges side by side: one tile)
                    i0 = next(k for k in (i, i - 1, i + 1) if 0 <= k and k + 1 < ncol
                              and not {k, k + 1} & set(rib_cols))
                    notch = notch | {i0, i0 + 1}
                    late_cells |= {(i0, j - 1), (i0 + 1, j - 1)}
                    late.append(i0)
            extra |= {(i, j) for i in range(ncol) if i not in notch}
            if not (at_q and f.name in "ac"):
                over |= {(i, j) for i in notch if 0 < i < ncol - 1}
    # the plates: one long 4-wide plate where it fits (several on a long panel), then the
    # extra rows; the tiles bind them all
    sizes = [s for s in AV.sizes(PLATE, role) if s[0] <= 4 and s[1] <= 12]
    rects = pack(main, sizes, prefer="x") + (pack(extra, sizes, prefer="x") if extra else [])
    for i0, i1, j0, j1 in rects:
        part, Rl = rect_part(PLATE, i1 - i0 + 1, j1 - j0 + 1)
        t = 10 + S * (j0 + j1 + 1) / 2
        pos = to_world(x0 + S * (i0 + i1 + 1) / 2, f.at(t, S_TILE), side)
        bt.add(part, role, transform(pos, R @ Rl), "plate", insert=UP)
    # hinge plates under it
    for at_q, kind, xs in ((False, ends[0], hp), (True, ends[1], hq)):
        if not kind:
            continue
        for xh in xs:
            t = f.L - 30 if at_q else 30
            pos = to_world(xh, f.at(t, S_PLATE), side)
            bt.add(CLIP if kind == "clip" else BAR, role,
                   transform(pos, hinge_R(f, side, at_q)), "hinge", insert=(0, 1, 0))
    # tiles: long ones along the hull, laid to bind every plate to its neighbours
    tsizes = [s for s in PANEL_TILES if s in AV.sizes(TILE, role) or s == (2, 6)]
    rib_cells = {(i, j) for i, j in main | extra if i in rib_cols}
    late_ribs = RIB_TILES.setdefault(name, [])
    late_ribs.clear()
    for rc, d in rib_cols.items():
        rows = sorted(j for i, j in rib_cells if i == rc)
        for j0, n in _rib_runs(rows, (8, 6, 4, 3, 2, 1)):      # plates in the tiles' layer
            part, Rl = rect_part(PLATE, 1, n)
            pos = to_world(x0 + S * rc + S / 2, f.at(10 + S * j0 + S * n / 2, S_TOP), side)
            bt.add(part, role, transform(pos, R @ Rl), "tile", insert=UP)
        # (the rows by the seam where the quarters' lapping panel meets the facet: a stud
        # wide there, the slot narrows to nothing)
        inner = [j for j in rows if 0 <= j < f.n and not
                 (j == (f.n - 1 if f.name in "ac" else 0) and f.name in "acd")]
        for j0, n in _rib_runs(inner, (4, 2, 1)):     # the rib's tiles: they go on last
            part = _tile(2, n) if n > 1 else "3069b"
            xm = x0 + S * (rc + (1 if d > 0 else 0))
            pos = to_world(xm, f.at(10 + S * j0 + S * n / 2, S_TOP + 8), side)
            late_ribs.append((part, transform(pos, R @ _along_x(part, 2)),
                              tuple(np.round(vec3(f.nrm, side), 6))))
        for j in rows:                                          # over the rest: a stud wide
            if j not in inner:
                pos = to_world(x0 + S * rc + S / 2, f.at(10 + S * j + S / 2, S_TOP + 8), side)
                bt.add("3070b", role, transform(pos, R), "tile", insert=UP)
    cells = (main | extra | over) - late_cells - rib_cells
    best = None
    for shift in range(0, 40, 4):
        tiles = pack(cells, tsizes, ids_of(rects), prefer="x", shift=shift, bridge=True)
        n = connected([rects, tiles])
        if best is None or n < best[0]:
            best = (n, tiles)
        if n == 1:
            break
    for i0, i1, j0, j1 in best[1]:
        w, d = i1 - i0 + 1, j1 - j0 + 1
        part = _tile(w, d)
        t = 10 + S * (j0 + j1 + 1) / 2
        pos = to_world(x0 + S * (i0 + i1 + 1) / 2, f.at(t, S_TOP), side)
        bt.add(part, role, transform(pos, R @ _along_x(part, w)), "tile", insert=UP)
    bt.emit(sub, phases=[["plate"], ["tile"], ["hinge"]], hanging=("hinge",),
            captions={"plate": title, "hinge": "Hinge plates underneath: clips and bars",
                      "tile": "Tiles: the plating"}, per_step=10, reach=400)
    late_tiles = []
    for i0 in late:
        pos = to_world(x0 + S * (i0 + 1), f.at(10 + S * f.n, S_TOP), side)
        late_tiles.append(("3068b", transform(pos, R)))
    return sub, M, late_tiles


RIB_TILES = {}      # {panel: [(part, hull-frame M, insert)]}: ribs' tiles, put on after the
                    # panels they reach over (naut_quarters.build_quarters places them)


def _rib_runs(rows, lengths) -> list:
    """(first row, length) pieces covering consecutive runs of rows."""
    out, runs = [], []
    for j in rows:
        if runs and runs[-1][-1] == j - 1:
            runs[-1].append(j)
        else:
            runs.append([j])
    for run in runs:
        j0, left = run[0], len(run)
        while left:                          # (no piece of one where it can be helped)
            n = next((n for n in lengths if n <= left and left - n != 1), None) or \
                next(n for n in lengths if n <= left)
            out.append((j0, n))
            j0, left = j0 + n, left - n
    return out


def _tile(w: int, d: int) -> str:
    a, b = min(w, d), max(w, d)
    return {(2, 6): "69729"}.get((a, b)) or TILE[(a, b)]


def _along_x(part: str, ln: int) -> np.ndarray:
    """Local rotation turning a tile ln studs long to lie along X."""
    lo, hi = bbox(part)
    return np.eye(3) if abs((hi[0] - lo[0]) - S * ln) < 1 else rot(y=90)


LIPS = {"a": (True, True), "b": (False, True), "c": (True, True), "d": (False, True)}


def end_section() -> dict:
    """The midbody's panels' outer faces (tiles' top) in the cross-section, (|z|, y), each facet
    from its first hinge line to its second, with its lips (a stud past a hinge line)."""
    out = {}
    for key, f in FACETS.items():
        t0 = -S if LIPS[key][0] else 10.0
        t1 = f.L + S if LIPS[key][1] else f.L - 10.0
        out[key] = [tuple(round(float(v), 1) for v in f.at(t, S_TOP)) for t in (t0, t1)]
    return out


def ribs(key: str, x0: float, x1: float) -> tuple:
    """(rib at x0, rib at x1) of a midbody panel: where it meets the quarters' panels on
    another grid (naut_shape.QUARTERS_MODULE): forward, under the side keels (the forebody's
    cone), and aft except on the deck's facet (b: the afterbody's b is on its grid)."""
    if not shp.QUARTERS_MODULE:
        return (False, False)
    return (x0 == shp.WIDE[0] and key in "cd", x1 == shp.WIDE[1] and key in "acd")
