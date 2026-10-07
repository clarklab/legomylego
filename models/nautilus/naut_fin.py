"""Thin fins built sideways (SNOT), as LEGO's own sets build fins and wings: the fin's outline is
the diagonals of wedge plates, its faces are tiles.

A fin stands in the hull's x-y plane, centred on z = 0:

* a **core** one stud thick (z -10 .. 10) of plates and bricks, with bricks with studs on two
  sides (47905) where a face needs a stud: every other row of the face's stud grid (a brick and
  two plates make 40 LDU, two rows);
* on each side a **face** of plates and wedge plates lying on the core's side studs (studs out,
  z +-10 .. +-18), their outline the fin's (the wedge plates' diagonals make its swept edges);
* **tiles** on the faces' studs (z +-18 .. +-26) and on the core's top, so the fin is smooth.
  Tiles bridge the face's parts where they span two of them (a wedge plate on a row without
  core studs is held by the tiles over it and its neighbour).

The fin is 52 LDU thick. The port face is laid out here (in face coordinates u = x, v = -y, up);
the starboard face is its mirror image (mirror wedge plates, the same plates).

The core is built up from a base (`upright`, its first layer's underside at the base's top: the
face's first row starts 4 LDU over it) or down from it (`hanging`: the face's first row starts
flush with the base's underside), course by course: a row of 47905s (three plates) whose side
studs carry the face's rows 0, 2, 4, ..., then two layers of plates bonding them.

Hull frame (naut_shape): LDU, -Y up, bow toward -X, port toward -Z.
"""
from __future__ import annotations

from collections import defaultdict
from functools import lru_cache

import numpy as np

from brickkit.ldraw.matrix import rot
from naut_kit import ENG, PLATE, TILE, S, Batch, canon, connectors, ids_of, pack, rect_part

FACE_IN = 10.0                     # |z| of the core's faces: the side studs' base
Z_PLATE = -(FACE_IN + 8.0)         # the port face's plates' top face (their studs outward)
Z_TILE = Z_PLATE - 8.0             # its tiles' top face
SIDE_BRICK = "47905"               # brick 1 x 1 with studs on two (opposite) sides
# port face: local x -> world x (u), local y (into the part) -> +z, local z -> -y (up, v)
R_PORT = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 1.0, 0.0]])
SZ = np.diag([1.0, 1.0, -1.0])
SX = np.diag([-1.0, 1.0, 1.0])
# wedge plates and their mirror images (the outline mirrored across the part's local x = 0)
PAIRS = {"41769": "41770", "43722": "43723", "24299": "24307", "54383": "54384",
         "78443": "78444", "47397": "47398", "50304": "50305"}
PAIRS.update({b: a for a, b in list(PAIRS.items())})
REFLECT = (SX, np.diag([1.0, 1.0, -1.0]),
           np.array([[0.0, 0.0, 1.0], [0.0, 1.0, 0.0], [1.0, 0.0, 0.0]]),
           np.array([[0.0, 0.0, -1.0], [0.0, 1.0, 0.0], [-1.0, 0.0, 0.0]]))
TILE_SIZES = [(1, 1), (1, 2), (1, 3), (1, 4), (1, 6), (1, 8), (2, 2), (2, 4)]
CORE_PLATES = [(1, 1), (1, 2), (1, 3), (1, 4), (1, 6), (1, 8)]


def short(part: str) -> str:
    return canon(part).replace(".dat", "").rstrip("abc") if canon(part)[:5].isdigit() else part


def _rq(q: int) -> np.ndarray:
    return R_PORT @ np.asarray(rot(y=90 * q), float)[:3, :3]


@lru_cache(maxsize=None)
def outline(part: str) -> np.ndarray:
    """The part's top face outline in its own x-z plane (convex hull of its top vertices)."""
    from scipy.spatial import ConvexHull
    t = ENG.geom.mesh(canon(part)).tris.reshape(-1, 3)
    top = t[t[:, 1] < 0.5][:, [0, 2]]
    return top[ConvexHull(top).vertices]


def face_poly(part: str, q: int = 0) -> np.ndarray:
    """The part's outline on the port face (u, v) with turn q (quarter turns about its studs),
    relative to its origin."""
    o = outline(part)
    P = np.column_stack([o[:, 0], np.zeros(len(o)), o[:, 1]]) @ _rq(q).T
    return np.column_stack([P[:, 0], -P[:, 1]])


def _M(R, t) -> np.ndarray:
    M = np.eye(4)
    M[:3, :3] = R
    M[:3, 3] = t
    return M


@lru_cache(maxsize=None)
def mirror_of(part: str):
    """(mirror part, local reflection S): the part mirrored across its local x-z plane's
    reflection S is the mirror part."""
    p = short(part)
    if p in PAIRS:
        return PAIRS[p], SX
    o = outline(part)
    key = {(round(a), round(b)) for a, b in o}
    for Sm in REFLECT:
        q = np.column_stack([o[:, 0], np.zeros(len(o)), o[:, 1]]) @ Sm.T
        m = {(round(a), round(b)) for a, b in q[:, [0, 2]]}
        if m == key:
            return part, Sm
    raise ValueError(f"no mirror for {part}")


def starboard(part: str, M):
    """The starboard face's part for a port face part: its mirror image through z = 0."""
    p2, Sm = mirror_of(part)
    S4 = np.eye(4)
    S4[:3, :3] = Sm
    Z4 = np.eye(4)
    Z4[:3, :3] = SZ
    return p2, Z4 @ np.asarray(M, float) @ S4


def inside_convex(poly: np.ndarray, pts: np.ndarray, eps: float = 0.01) -> np.ndarray:
    """Which points (N x 2) are inside the convex polygon (either winding)?"""
    n = len(poly)
    signs = []
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        cr = (b[0] - a[0]) * (pts[:, 1] - a[1]) - (b[1] - a[1]) * (pts[:, 0] - a[0])
        signs.append(cr)
    signs = np.array(signs)
    return np.all(signs >= -eps, axis=0) | np.all(signs <= eps, axis=0)


# ------------------------------------------------------------------ the fin
class Fin:
    """A SNOT fin (see the module's docstring). Lay out its port face with `plate`, `wedge`
    (face grid cells: column c spans u in [U0 + 20 c, U0 + 20 c + 20], row r spans v in
    [V0 + 20 r, V0 + 20 r + 20]), then `build` it into a Batch."""

    def __init__(self, U0: float, base_y: float, hanging: bool = False, role: str = "hull",
                 core_role: str = "core"):
        self.U0 = float(U0)
        self.hanging = hanging
        self.base_y = float(base_y)
        # upright: the face's row 0 starts 4 over the base (a 47905 on it carries it);
        # hanging: row 0 ends flush with the base's underside, the rows going down
        self.V0 = -(base_y - 4.0) if not hanging else -(base_y + 20.0)
        self.role, self.core_role = role, core_role
        self.parts: list = []            # (part, M port)

    # -- the port face's parts
    def cell(self, c: float, r: float) -> tuple:
        """(u, v) of the lower-left corner of face cell (c, r) (hanging: rows count down)."""
        return self.U0 + S * c, self.V0 - S * r if self.hanging else self.V0 + S * r

    def plate(self, c0: int, r0: int, w: int, h: int, table=PLATE):
        """A plate w columns by h rows, its lower-left cell (c0, r0) (hanging: its upper-left,
        rows down)."""
        part, R = rect_part(table, w, h)
        u, v = self.cell(c0, r0)
        vc = v + S * h / 2 if not self.hanging else v + S - S * h / 2
        self.parts.append((part, _M(R_PORT @ np.asarray(R, float)[:3, :3],
                                    (u + S * w / 2, -vc, Z_PLATE))))

    def wedge(self, part: str, q: int, c0: float, r0: float, top: bool = False):
        """A wedge plate turned q, its outline's bounding box's lower-left at cell (c0, r0)'s
        corner (hanging, or `top`: its upper-left at that cell's upper-left)."""
        poly = face_poly(part, q)
        u, v = self.cell(c0, r0)
        if self.hanging or top:
            v = v + S - (poly[:, 1].max() - poly[:, 1].min())
        t = (u - poly[:, 0].min(), -(v - poly[:, 1].min()), Z_PLATE)
        self.parts.append((part, _M(_rq(q), t)))

    def fill(self, cells, role: str = "hull"):
        """Cover face cells {(c, r)} with plates, each on a row of the core's side studs (even r):
        an odd row's cells paired with the even row beside them in plates two rows tall, the
        even rows' leftovers in plates one row tall. Returns the cells it could not cover."""
        from naut_kit import AV
        left = set(cells)
        two = sorted({b for a, b in AV.sizes(PLATE, role) if a == 2} | {1}, reverse=True)
        one = sorted({b for a, b in AV.sizes(PLATE, role) if a == 1}, reverse=True)

        def split(n, sizes):
            out = []
            while n > 0:
                s = next((s for s in sizes if s <= n and n - s != 1 or s == n), None) or \
                    max(s for s in sizes if s <= n)
                out.append(s)
                n -= s
            return out

        def runs(cs):
            out, cur = [], []
            for c in sorted(cs):
                if cur and c != cur[-1] + 1:
                    out.append(cur)
                    cur = []
                cur.append(c)
            return out + ([cur] if cur else [])
        for r in sorted({r for _, r in left if r % 2}):
            for partner in (r - 1, r + 1):
                cs = [c for c, rr in left if rr == r and (c, partner) in left]
                for run in runs(cs):
                    c0 = run[0]
                    for n in split(len(run), two):
                        self.plate(c0, min(r, partner), n, 2)
                        left -= {(c, rr) for c in range(c0, c0 + n) for rr in (r, partner)}
                        c0 += n
        for r in sorted({r for _, r in left}):
            for run in runs([c for c, rr in left if rr == r]):
                c0 = run[0]
                for n in split(len(run), one):
                    self.plate(c0, r, n, 1)
                    left -= {(c, r) for c in range(c0, c0 + n)}
                    c0 += n
        if left:
            print(f"warning: fin face cells not covered: {sorted(left)}")
        return left

    def polys(self) -> list:
        out = []
        for part, M in self.parts:
            o = outline(part)
            P = np.column_stack([o[:, 0], np.zeros(len(o)), o[:, 1]]) @ M[:3, :3].T + M[:3, 3]
            out.append(np.column_stack([P[:, 0], -P[:, 1]]))
        return out

    def covered(self, pts: np.ndarray) -> np.ndarray:
        ok = np.zeros(len(pts), bool)
        for poly in self.polys():
            ok |= inside_convex(poly, pts, eps=0.6)
        return ok

    # -- the core
    def _layer_rect(self, c: int, k: int) -> np.ndarray:
        """Sample points over core cell (column c, layer k)."""
        u0 = self.U0 + S * c
        y0 = self.base_y - 8.0 * (k + 1) if not self.hanging else self.base_y + 8.0 * k
        # upright, the face starts 4 over the base: the first layer counts from there
        dys = (1.0, 2.5, 3.5) if (k == 0 and not self.hanging) else (1.0, 4.0, 7.0)
        return np.array([(u, -(y0 + dy)) for u in np.arange(u0 + 1.0, u0 + S, 3.0)
                         for dy in dys])

    def covered_layers(self, c: int, kmax: int = 60) -> list:
        return [k for k in range(kmax) if self.covered(self._layer_rect(c, k)).all()]

    def reach_from(self, u: float, v0: float) -> float | None:
        """Upright: the highest v the face covers going up from v0 (None if not at v0 + 0.5)."""
        vs = np.arange(v0 + 0.5, v0 + 400.0, 1.0)
        ok = self.covered(np.column_stack([np.full(len(vs), u), vs]))
        if not ok[0]:
            return None
        k = int(np.argmin(ok)) if not ok.all() else len(vs)
        return float(vs[k - 1])

    def cap(self, c: int, k0: int):
        """Upright: how many layers of a column's top run (from layer k0 up) to build, and the
        cap on them, as close under the face's edge as it goes: (n, "tile") or (n, ("cheese",
        +1 / -1: rising toward +u or -u)); the cheese slope (54200) rises 16 over its stud."""
        base_v = -self.base_y + 8.0 * k0
        u0 = self.U0 + S * c
        us = np.arange(1.0, S, 2.0)
        start = base_v + (4.0 if k0 == 0 else 0.0)
        r = [self.reach_from(u0 + u, start) for u in us]
        if any(x is None for x in r):
            return None
        vmin = min(r)
        n_t = int(np.floor((vmin - base_v - 8.0 + 0.6) / 8.0))
        best = (n_t, "tile", base_v + 8 * n_t + 8)
        for sx in (1, -1):
            rs = [self.reach_from(u0 + (u if sx > 0 else S - u), start) for u in us]
            if rs[-1] - rs[0] < 4:
                continue
            n = int(np.floor(min(rr - 16.0 * (u / S) - base_v for u, rr in zip(us, rs))
                             / 8.0 + 0.075))
            if n >= 0 and base_v + 8 * n + 16 > best[2] + 2:
                best = (n, ("cheese", sx), base_v + 8 * n + 16)
        return best[:2] if best[0] >= 0 else None

    def build(self, ncols: range, cat: str = "fin", core_top_tiles: bool = True,
              core_skip=(), extra_core=(), core_to=None, spikes=(),
              spike_role: str = "spine") -> Batch:
        """The fin's parts: the core over columns `ncols` (as far as the face covers each, less
        room for the cap on its top), its 47905s, both faces, the tiles. Categories
        cat + "_core", "_core_tiles", "_spikes", "_port", "_stbd", "_tiles" (or place the faces
        and tiles with emit_faces). `core_skip`: (column, layer) cells kept out of the core.
        `extra_core`: [(part, role, M)] set in the core. Hanging: `core_to` (y) the core runs
        down to (past the face's last row). `spikes`: upright, columns whose cap is a spike
        instead (a claw in a round plate with an open stud), curving aft."""
        bt = Batch()
        # layers: upright, layer n spans y [base - 8 (n + 1), base - 8 n]; hanging, [base + 8 n,
        # base + 8 (n + 1)]
        cells = set()
        no_brick = set()
        if not self.hanging:
            caps = {}               # {column: (layer under the cap, cap)}
            for c in ncols:
                ks = self.covered_layers(c)
                if not ks:
                    continue
                k0 = ks[-1]
                while k0 - 1 in ks:
                    k0 -= 1                      # the top run: k0 .. ks[-1]
                keep = set(ks)
                if core_top_tiles:
                    cp = self.cap(c, k0)
                    keep = {k for k in ks if k < k0}
                    if cp is not None:
                        n, kind = cp
                        keep |= set(range(k0, k0 + n))
                        if n > 0:
                            caps[c] = (k0 + n, kind)
                for k in keep:
                    if (c, k) not in core_skip:
                        cells.add((c, k))
        else:
            caps = {}
            # every layer cell the face covers, wherever it starts; down to core_to where the
            # face reaches its last row
            for c in ncols:
                u0 = self.U0 + S * c
                us = np.arange(u0 + 1.0, u0 + S, 3.0)
                last = None
                for k in range(60):
                    y0 = self.base_y + 8 * k
                    if core_to is not None and y0 >= core_to:
                        break
                    pts = np.array([(u, -(y0 + dy)) for u in us for dy in (1.0, 4.0, 7.0)])
                    if self.covered(pts).all():
                        if (c, k) not in core_skip:
                            cells.add((c, k))
                        last = k
                    elif core_to is not None and last == k - 1 and \
                            self.base_y + 8 * k + 8 <= core_to and \
                            self.covered(np.array([(u, -(y0 + 1.0)) for u in us])).all():
                        cells.add((c, k))        # the last layer, past the face's foot
                        last = k
            # a column too short for the plates under its first course: its layers bond to a
            # longer neighbour's (no side bricks in either's first course), else it is left out
            depth = {c: max(k for cc, k in cells if cc == c) for c, _ in cells}
            for c, d in sorted(depth.items()):
                if d >= 3:
                    continue
                nb = [n for n in (c - 1, c + 1) if depth.get(n, -1) >= 3
                      and all((n, k) in cells for k in range(d + 1))]
                if nb and all((c, k) in cells for k in range(d + 1)):
                    no_brick |= {(c, 0), (nb[0], 0)}
                else:
                    cells -= {(c, k) for k in range(60)}
        self.core_cells = cells
        # side bricks: course j's layers 5 j .. 5 j + 2 (upright: from the base; hanging: from the
        # top), in every column holding all three
        bricks = set()
        for c, k in cells:
            if k % 5 == 0 and (c, k + 1) in cells and (c, k + 2) in cells \
                    and (c, k) not in no_brick:
                bricks.add((c, k))
        left = set(cells)
        for c, k in bricks:
            left -= {(c, k), (c, k + 1), (c, k + 2)}
        xc = lambda c: self.U0 + S * c + S / 2
        ytop = (lambda k: self.base_y - 8.0 * (k + 1)) if not self.hanging else \
            (lambda k: self.base_y + 8.0 * k)
        for c, k in sorted(bricks):
            yt = ytop(k + 2) if not self.hanging else ytop(k)
            bt.add(SIDE_BRICK, self.core_role, _M(np.eye(3), (xc(c), yt, 0.0)), cat + "_core")
        for part, role, M in extra_core:
            bt.add(part, role, M, cat + "_core")
        # plates, layer by layer, bonded to the layer before
        layers = sorted({k for _, k in left})
        prev = None
        for k in layers:
            lc = {(c, 0) for c, kk in left if kk == k}
            # the bricks in this layer count as groups to bond
            rects = pack(lc, CORE_PLATES, prev, prefer="x", shift=k) if lc else []
            cur = ids_of(rects, start=1000 * k)
            for c, kk in bricks:
                if kk <= k <= kk + 2:
                    cur[(c, 0)] = ("b", c, kk)
            for i0, i1, _, _ in rects:
                part, R = rect_part(PLATE, i1 - i0 + 1, 1)
                bt.add(part, self.core_role,
                       _M(np.asarray(R, float)[:3, :3], ((xc(i0) + xc(i1)) / 2, ytop(k), 0.0)),
                       cat + "_core")
            prev = cur
        # caps on the core's top (upright): tiles, or cheese slopes up under a swept edge
        if core_top_tiles and not self.hanging:
            by_k = defaultdict(set)
            for c, (n, cap) in caps.items():
                if n <= 0 or (c, n - 1) not in cells:
                    continue
                if c in spikes:
                    Rs = (np.asarray(rot(y=-90), float)[:3, :3]
                          @ np.asarray(rot(x=90), float)[:3, :3])
                    bt.add("85861", spike_role, _M(np.eye(3), (xc(c), ytop(n - 1) - 8.0, 0.0)),
                           cat + "_spikes")
                    bt.add("53451", spike_role, _M(Rs, (xc(c), ytop(n - 1) - 12.0, 0.0)),
                           cat + "_spikes")
                    continue
                if cap == "tile":
                    by_k[n].add((c, 0))
                else:
                    sx = cap[1]
                    ez = np.array([sx, 0.0, 0.0])
                    ey = np.array([0.0, 1.0, 0.0])
                    R = np.column_stack([np.cross(ey, ez), ey, ez])
                    bt.add("54200", self.role, _M(R, (xc(c), ytop(n - 1), 0.0)),
                           cat + "_core_tiles")
            for n, cs in by_k.items():
                for i0, i1, _, _ in pack(cs, [(1, 1), (1, 2), (1, 3), (1, 4), (1, 6)],
                                         prefer="x"):
                    part, R = rect_part(TILE, i1 - i0 + 1, 1)
                    bt.add(part, self.role, _M(np.asarray(R, float)[:3, :3],
                                               ((xc(i0) + xc(i1)) / 2, ytop(n - 1) - 8.0, 0.0)),
                           cat + "_core_tiles")
        # the faces
        held = self._held(bt)
        for part, M in self.parts:
            bt.add(part, self.role, M, cat + "_port", insert=(0, 0, -1))
        for part, M in self.parts:
            p2, M2 = starboard(part, M)
            bt.add(p2, self.role, M2, cat + "_stbd", insert=(0, 0, 1))
        self._tiles = self.tiles(held)
        for part, M in self._tiles:
            bt.add(part, self.role, M, cat + "_tiles", insert=(0, 0, -1))
            p2, M2 = starboard(part, M)
            bt.add(p2, self.role, M2, cat + "_tiles", insert=(0, 0, 1))
        return bt

    def _held(self, bt) -> set:
        """Indices of the port face's parts held by a core stud."""
        studs = []
        for part, _, M, *_ in bt.items:
            for cn in connectors(part, M):
                if cn.kind == "cyl" and cn.gender == "M" and cn.axis[2] < -0.99:
                    studs.append(np.asarray(cn.origin, float))
        studs = np.array(studs) if studs else np.zeros((0, 3))
        out = set()
        for j, (part, M) in enumerate(self.parts):
            for cn in connectors(part, M):
                if cn.kind == "cyl" and cn.gender == "F" and cn.axis[2] < -0.99 and len(studs):
                    if np.min(np.linalg.norm(studs - np.asarray(cn.origin, float), axis=1)) < 1:
                        out.add(j)
        self.held = out
        return out

    def face_studs(self) -> dict:
        """{(column, row) of a stud on the port face: index of its part}."""
        out = {}
        for j, (part, M) in enumerate(self.parts):
            for cn in connectors(part, M):
                if cn.kind == "cyl" and cn.gender == "M" and cn.axis[2] < -0.99:
                    u, v = cn.origin[0], -cn.origin[1]
                    c = int(round((u - self.U0 - 10) / S))
                    r = (v - self.V0 - 10) / S
                    out[(c, int(round(r)))] = j
        return out

    def tiles(self, held: set) -> list:
        """Tiles over the port face's studs: [(part, M)], laid to bridge parts not held by
        the core to ones that are."""
        studs = self.face_studs()
        below = {cell: (0 if j in held else j + 1) for cell, j in studs.items()}
        out = []
        for c0, c1, r0, r1 in pack(set(studs), TILE_SIZES, below, prefer="x"):
            w, h = c1 - c0 + 1, r1 - r0 + 1
            part, R = rect_part(TILE, w, h)
            uc = self.U0 + S * (c0 + c1 + 1) / 2
            vc = self.V0 + S * (r0 + r1 + 1) / 2
            out.append((part, _M(R_PORT @ np.asarray(R, float)[:3, :3], (uc, -vc, Z_TILE))))
        self.unheld = self._unheld(out, held)
        return out

    def _unheld(self, tiles, held) -> list:
        """Port face parts neither held by the core nor joined to one by a tile (should be
        none)."""
        studs = self.face_studs()
        parent = list(range(len(self.parts)))

        def root(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a
        covers = []
        self._covers = covers
        for part, M in tiles:
            o = outline(part)
            P = np.column_stack([o[:, 0], np.zeros(len(o)), o[:, 1]]) @ M[:3, :3].T + M[:3, 3]
            poly = np.column_stack([P[:, 0], -P[:, 1]])
            js = set()
            for (c, r), j in studs.items():
                p = np.array([[self.U0 + S * c + 10, self.V0 + S * r + 10]])
                if inside_convex(poly, p, eps=0.5)[0]:
                    js.add(j)
            covers.append(set(js))
            js = sorted(js)
            for j in js[1:]:
                parent[root(j)] = root(js[0])
        good = {root(j) for j in held}
        return [j for j in range(len(self.parts)) if root(j) not in good]


def _emit_faces(fin: "Fin", sub, caption: str = "", per_step: int = 8):
    """Place both faces and their tiles in `sub` (after the core): each face's parts held by
    the core's side studs first; then each part held only through a tile, in the same step as
    that tile (pressed on over it and a part already on); then the other tiles."""
    tiles, covers = fin._tiles, fin._covers
    first = True
    for side in (-1, 1):
        parts = list(fin.parts) if side < 0 else [starboard(p, M) for p, M in fin.parts]
        tl = list(tiles) if side < 0 else [starboard(p, M) for p, M in tiles]
        ins = (0, 0, side)
        steps = []
        held = sorted(fin.held, key=lambda j: (-parts[j][1][1, 3], parts[j][1][0, 3]))
        for k in range(0, len(held), per_step):
            steps.append([parts[j] for j in held[k:k + per_step]])
        placed, used = set(fin.held), set()
        while True:
            t = next((t for t in range(len(tl)) if t not in used and covers[t] & placed
                      and covers[t] - placed), None)
            if t is None:
                break
            steps.append([parts[j] for j in sorted(covers[t] - placed)] + [tl[t]])
            placed |= covers[t]
            used.add(t)
        rest = [tl[t] for t in range(len(tl)) if t not in used]
        for k in range(0, len(rest), per_step + 2):
            steps.append(rest[k:k + per_step + 2])
        for st in steps:
            sub.step(caption if first else "")
            first = False
            for part, M in st:
                pl = sub.place(part, fin.role, (0, 0, 0), insert=ins)
                pl.M = np.asarray(M, float)


Fin.emit_faces = _emit_faces
