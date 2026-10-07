"""Geometry helpers for the hamburger: the octagon outline, rectangle packing, turned faces.

Frame: LDU, -Y up, front is -Z. Cells are stud positions (i, k) on a grid centred between four
studs: cell (i, k) spans x in [i, i + 1], z in [k, k + 1] studs. A plate or tile placed with its
top face at `y` has its bottom at y + 8; a brick's bottom is at y + 24.

The outline is an octagon: flats 7 studs from the axis on the four sides (14 studs across) and 45
degree flats at |x| + |z| = 10 between them. The four side flats are built on the stud grid. The
four diagonal flats are separate little "faces" turned 45 degrees: each stands on smooth tiles
and is pinned by a single stud (a round 1 x 1 plate among the tiles), and the on-grid parts on
either side hold it straight. That keeps every visible wall smooth: LEGO's 45 degree wedge plates
and bricks all have stud notches along their cut edges, which would show as rows of slots.
"""
from __future__ import annotations

import math

import numpy as np

from brickkit.ldraw.matrix import rot

S = 20                     # stud, LDU
PLATE, BRICK = 8, 24
QUADS = ((1, -1), (-1, -1), (-1, 1), (1, 1))
# rotation about Y that turns a 6106's cut corner (local +x, -z) toward quadrant (sx, sz)
CUT_TURN = {(1, -1): 0, (-1, -1): 90, (-1, 1): 180, (1, 1): -90}

PLATES = {(1, 1): "3024", (1, 2): "3023", (1, 3): "3623", (1, 4): "3710", (1, 6): "3666",
          (1, 8): "3460", (2, 2): "3022", (2, 3): "3021", (2, 4): "3020", (2, 6): "3795",
          (2, 8): "3034", (4, 4): "3031", (4, 6): "3032", (6, 6): "3958"}
TILES = {(1, 1): "3070b", (1, 2): "3069b", (1, 3): "63864", (1, 4): "2431", (1, 6): "6636",
         (2, 2): "3068b", (2, 4): "87079"}
BRICKS = {(1, 1): "3005", (1, 2): "3004", (1, 3): "3622", (1, 4): "3010", (1, 6): "3009",
          (2, 2): "3003", (2, 3): "3002", (2, 4): "3001", (2, 6): "2456"}

DIAG = math.sqrt(0.5)


def turn_toward(dx: float, dz: float) -> float:
    """Degrees about Y that turn a part's front (-z) toward the direction (dx, dz)."""
    return math.degrees(math.atan2(-dx, -dz))


def rect_cells(i0, k0, nx, nz):
    return {(i, k) for i in range(i0, i0 + nx) for k in range(k0, k0 + nz)}


def octagon_cells(flat: int, diag: int) -> set:
    """Cells wholly inside the octagon |x|, |z| <= flat, |x| + |z| <= diag (studs)."""
    out = set()
    for i in range(-flat, flat):
        for k in range(-flat, flat):
            fx, fz = max(abs(i), abs(i + 1)), max(abs(k), abs(k + 1))
            if fx <= flat and fz <= flat and fx + fz <= diag:
                out.add((i, k))
    return out


def mirror4(cells_q):
    """Cells given in the (+x, +z) quadrant's own coordinates (a, b >= 0), copied to all four
    quadrants: (a, b) -> (a or -a-1, b or -b-1)."""
    out = set()
    for a, b in cells_q:
        for sx, sz in QUADS:
            out.add((a if sx > 0 else -a - 1, b if sz > 0 else -b - 1))
    return out


def sym8(cells_q):
    """Like mirror4, and also swapping x and z (the octagon's eight-fold symmetry)."""
    return mirror4(set(cells_q) | {(b, a) for a, b in cells_q})


def place_rect(sub, table, color, i0, k0, nx, nz, y, tag=""):
    """A plate, tile or brick covering cells i0..i0+nx-1, k0..k0+nz-1, top face at y."""
    part = table[(min(nx, nz), max(nx, nz))]
    turn = 0 if nx >= nz else 90
    x, z = (i0 + nx / 2) * S, (k0 + nz / 2) * S
    return sub.place(part, color, (x, y, z), rot(y=turn) if turn else None, tag=tag)


def pack(cells, table, *, along="x", reverse=False, strict=False):
    """Greedy cover of `cells` with the rectangles of `table`, largest first, each anchored at
    the first free cell in scan order (`reverse` scans from the other end, anchoring at the far
    corner). `strict` keeps every run's long side along `along`, so two layers packed strictly
    in crossing directions always bond. Returns [(i0, k0, nx, nz)]."""
    if reverse:
        flipped = {(-i - 1, -k - 1) for i, k in cells}
        return [(-i0 - nx, -k0 - nz, nx, nz)
                for i0, k0, nx, nz in pack(flipped, table, along=along, strict=strict)]
    free = set(cells)
    sizes = sorted(table, key=lambda s: (-s[0] * s[1], -s[1]))
    out = []
    key = (lambda c: (c[1], c[0])) if along == "x" else (lambda c: (c[0], c[1]))
    for c in sorted(cells, key=key):
        if c not in free:
            continue
        for w, l in sizes:
            dims = ((l, w), (w, l)) if along == "x" else ((w, l), (l, w))
            if strict and w != l:
                dims = dims[:1]
            hit = next(((nx, nz) for nx, nz in dims
                        if rect_cells(c[0], c[1], nx, nz) <= free), None)
            if hit:
                out.append((c[0], c[1], *hit))
                free -= rect_cells(c[0], c[1], *hit)
                break
    return out


def lay(sub, table, color, cells, y, *, along="x", reverse=False, tag=""):
    """Pack `cells` with plates, tiles or bricks (top face at y). Returns the placements."""
    return [place_rect(sub, table, color, *r, y, tag)
            for r in pack(cells, table, along=along, reverse=reverse)]


def components(rects_by_layer, fixed=()):
    """How many separate pieces stacked layers of rectangles make: two rectangles in adjacent
    layers are joined when they share a cell. `fixed` adds extra cell groups (parts placed by
    hand) to the lowest layer. Returns the count."""
    nodes = []
    for layer, rects in enumerate(rects_by_layer):
        for r in rects:
            nodes.append((layer, rect_cells(*r)))
    for cells in fixed:
        nodes.append((0, set(cells)))
    parent = list(range(len(nodes)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for a in range(len(nodes)):
        for b in range(a + 1, len(nodes)):
            if abs(nodes[a][0] - nodes[b][0]) == 1 and nodes[a][1] & nodes[b][1]:
                parent[find(a)] = find(b)
    return len({find(a) for a in range(len(nodes))})


def bonded_pair(cells_a, table_a, cells_b, table_b, fixed_a=(), fixed_b=()):
    """Packings for two stacked layers (a below b) that join into one piece: runs strictly
    across each other, from either scan end, with the full tables or only 1-wide parts (which
    keep whole rows and columns together), fewest pieces first and then fewest parts.
    `fixed_*` are cell groups of parts placed by hand in that layer. Returns (rects_a, rects_b)."""
    def narrow(t):
        return {d: p for d, p in t.items() if d[0] == 1}

    best = None
    for ta in (table_a, narrow(table_a)):
        for tb in (table_b, narrow(table_b)):
            for along_a, along_b in (("x", "z"), ("z", "x")):
                for rev_a in (False, True):
                    ra = pack(cells_a, ta, along=along_a, reverse=rev_a, strict=True)
                    for rev_b in (False, True):
                        rb = pack(cells_b, tb, along=along_b, reverse=rev_b, strict=True)
                        layers = [ra + [rect_of(c) for c in fixed_a if c],
                                  rb + [rect_of(c) for c in fixed_b if c]]
                        score = (components(layers), len(ra) + len(rb))
                        if best is None or score < best[0]:
                            best = (score, ra, rb)
    if best[0][0] != 1:
        raise ValueError(f"layers fall into {best[0][0]} pieces")
    return best[1], best[2]


def rect_of(cells):
    i0, k0 = min(c[0] for c in cells), min(c[1] for c in cells)
    return i0, k0, max(c[0] for c in cells) - i0 + 1, max(c[1] for c in cells) - k0 + 1


def octagon7(sub, color, y, tag="", arms="3795", center="3022"):
    """One plate layer of the 14-stud octagon (top face at y): a 6106 in each quadrant
    (cells 1..6), 2 x 6 arms along the axes and a 2 x 2 in the middle. Only ever used as a
    bottom layer: the wedge plates' notched cut edges sit low, against the table or the layer
    below."""
    for q in QUADS:
        sub.place("6106", color, (q[0] * 80, y, q[1] * 80), rot(y=CUT_TURN[q]), tag=tag)
    reach = {"3795": 80, "3020": 60}[arms]        # arm centre: a 2 x 6 runs out to 7, a 2 x 4 to 5
    for sx in (-1, 1):
        sub.place(arms, color, (sx * reach, y, 0), tag=tag)
        sub.place(arms, color, (0, y, sx * reach), rot(y=90), tag=tag)
    sub.place(center, color, (0, y, 0), tag=tag)


def octagon6(sub, color, y, tag=""):
    """One plate layer of the 12-stud octagon (flats at 6, |x| + |z| <= 8): four 6106 wedge
    plates, cut corners outward. Used inset under the layers it holds together."""
    for q in QUADS:
        sub.place("6106", color, (q[0] * 60, y, q[1] * 60), rot(y=CUT_TURN[q]), tag=tag)


OCT6 = octagon_cells(6, 8)
OCT7 = octagon_cells(7, 10)
CENTER = rect_cells(-2, -2, 4, 4)   # the shared 4 x 4 stud zone


# ---- turned faces ----------------------------------------------------------------------------

class Face:
    """A sub-assembly built facing -z in its own frame (x along the face, -z outward), placed so
    that its outward direction points at `angle` degrees (0 = -z, 90 = -x ... as rot(y=)).
    `items` are (part, colour, (x, y, z), local rotation or None); the first item is the base,
    pinned through one of its anti-studs `pins` (local x, z)."""

    def __init__(self, angle, items, pins, center_n, y_base):
        self.angle = angle
        self.items = items
        self.pins = pins
        self.center_n = center_n     # LDU from the axis to the face frame's origin
        self.y_base = y_base
        self.R = rot(y=angle)
        self.origin = self.R @ np.array([0.0, 0.0, -center_n])
        self.pin = None

    def world(self, local):
        return self.origin + self.R @ np.asarray(local, float)

    def solve_pin(self, allow=lambda g: True, max_shift=6.0, max_side=2.0):
        """Shift the face (by a few LDU at most) so that one of its base's anti-studs sits on
        a pin: a stud on the grid (odd multiples of 10 LDU, a round 1 x 1 plate) or on a grid
        corner (multiples of 20 LDU, a 2 x 2 jumper plate). `allow(g)` says which positions
        can carry a pin. Prefers small sideways shifts and shifts outward over inward."""
        best = None
        for ax, az in self.pins:
            w = self.world((ax, 0, az))
            cands = [(math.floor(w[0] / 20) * 20 + 10 + dx, math.floor(w[2] / 20) * 20 + 10 + dz)
                     for dx in (-20, 0, 20) for dz in (-20, 0, 20)]
            cands += [(round(w[0] / 20) * 20 + dx, round(w[2] / 20) * 20 + dz)
                      for dx in (-20, 0, 20) for dz in (-20, 0, 20)]
            for gx, gz in cands:
                if not allow((gx, gz)):
                    continue
                shift = np.array([gx - w[0], 0, gz - w[2]])
                out = float(shift @ (self.R @ [0, 0, -1]))
                side = abs(float(shift @ (self.R @ [1, 0, 0])))
                if math.hypot(out, side) > max_shift or side > max_side:
                    continue
                score = side + (out if out > 0 else -2 * out)
                if best is None or score < best[0]:
                    best = (score, shift, (gx, gz))
        if best is None:
            raise ValueError(f"no pin for the face at {self.angle} degrees")
        self.origin = self.origin + best[1]
        self.pin = best[2]
        return self.pin

    def place(self, sub, tag=""):
        for part, color, local, lrot in self.items:
            M = self.R if lrot is None else self.R @ lrot
            sub.place(part, color, tuple(self.world(local)), M, tag=tag)

    def footprint(self, x0, x1, z0, z1):
        """World (x, z) corners of a local rectangle."""
        return [self.world((x, 0, z))[[0, 2]] for x, z in ((x0, z0), (x1, z0), (x1, z1), (x0, z1))]


def cells_under(polys, margin=0.3):
    """Cells whose square overlaps any of the convex polygons (lists of (x, z) LDU)."""
    out = set()
    for poly in polys:
        P = np.array(poly)
        lo, hi = P.min(axis=0), P.max(axis=0)
        for i in range(int(math.floor(lo[0] / S)) - 1, int(math.ceil(hi[0] / S)) + 1):
            for k in range(int(math.floor(lo[1] / S)) - 1, int(math.ceil(hi[1] / S)) + 1):
                sq = np.array([[i * S, k * S], [(i + 1) * S, k * S],
                               [(i + 1) * S, (k + 1) * S], [i * S, (k + 1) * S]])
                if _overlap(P, sq, margin):
                    out.add((i, k))
    return out


def _overlap(A, B, margin):
    """Separating-axis test for two convex polygons, shrunk by `margin` LDU."""
    for poly in (A, B):
        n = len(poly)
        for j in range(n):
            e = poly[(j + 1) % n] - poly[j]
            axis = np.array([-e[1], e[0]]) / np.linalg.norm(e)
            pa, pb = A @ axis, B @ axis
            if pa.max() - margin <= pb.min() or pb.max() - margin <= pa.min():
                return False
    return True
