"""The Nautilus's bow: everything forward of the bow station (naut_shape.BOW_STATION, x = -800),
one sub-assembly in the hull frame, pushed onto the hull along +X.

`build_bow(model, parent)` builds it and places it in `parent` (hull frame: LDU, -Y up, bow toward
-X, port toward -Z, side keels centred on y = 0).

**Shape.** A cone converging on the ram, like the photo model's riveted plating: on each side two
big tiled panels over the side keels (A, nearly upright, and E, sloping up to the ridge) and one
under them (C, the bottom, sloping down to the keel), all running to the bow's point. Between
the upper panels the spine's ridge (curved slopes stepping down to the ram, a dorsal spine on
every second pair of columns, as the hull's crest: a 45 degree slope and a cheese slope on
jumpers); between the lower ones the saw keel's blade with its teeth; at the waterline the side
keels, two plates thick, narrowing 1:3 (wedge plates) with a tooth on each edge wedge; at the
point the ram (round bricks, a bar 6L with its stop ring, a cone) out of the spine's nose.

**How the panels hang.** Each panel is a flat sub-assembly (a carrier layer of plates, a skin
layer of plates and wedge plates, tiles) clipped on along its edges: a clip plate each side of a
hinge line, a bar through them. A hangs on the side keels (1 x 1 clip plates on round-plate
spacers, turned to the line, 1:3 in plan) and on the crease it shares with E; E on the crease
and on clip plates on the spine's side studs (the ridge line, 0.36); the crease is solved so
both panels meet it at their wedge plates' angle (1:4), so the side keels, A, E and the spine
close into one rigid ring. C hangs on clip plates on the spine's side studs under the side keels
(the keel line, 0.16); its other edge runs just under the side keels at its wedge plates' angle
(1:3) to the keel line.

**The join.** At the station a column of Technic bricks 1 x 1 (6541), their holes along X, take
the hull's twelve side studs (11211 at z = +-10, y = -142 .. 58); the spine (two studs wide) and
everything else grows forward from them. Nothing crosses x = -800.

The tail's stock (naut_tail_new) is this cone again, loaded a second time with the hooks below
set (FACETS, DETAILS, SPINE_PROFILE, SPINE_SKIP, EXTRA_WALL, FRAME, FLANGE_*), built as if it
were a bow and turned to point aft.
"""
from __future__ import annotations

import math
from functools import lru_cache

import numpy as np
from scipy.optimize import fsolve

import naut_shape as shp
from brickkit.ldraw.matrix import rot, transform

S = 20
XS = float(shp.BOW_STATION)                 # -800: the station plane
ROLE = "hull"
CORE = "core"
CLIP_ROLE = "hinge"                         # Black: clip plates (61252 has no Reddish Brown)
SPINE = "spine"
BAR = "87994"                               # bar 3L, the hinges' pins
CLIP1, CLIP2 = "61252", "63868"             # 1 x 1 clip (single stud, turns), 1 x 2 clip on end
RP = "6141"                                 # round plate 1 x 1: spacers under the clips

# ------------------------------------------------------------------ small geometry
def unit(v) -> np.ndarray:
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def angd(a, b) -> float:
    return math.degrees(math.acos(float(np.clip(abs(np.dot(unit(a), unit(b))), -1, 1))))


class Line:
    def __init__(self, p, d):
        self.p = np.asarray(p, float)
        self.d = unit(d)

    def at_x(self, x: float) -> np.ndarray:
        return self.p + (x - self.p[0]) / self.d[0] * self.d

    def pt(self, t: float) -> np.ndarray:
        return self.p + t * self.d

    def mirror(self) -> "Line":
        return Line(self.p * (1, 1, -1), self.d * (1, 1, -1))


def orient(ex, ey, ez=None) -> np.ndarray:
    ex, ey = np.asarray(ex, float), np.asarray(ey, float)
    ez = np.cross(ex, ey) if ez is None else np.asarray(ez, float)
    return np.column_stack([ex, ey, ez])


# ------------------------------------------------------------------ the hinge lines (port side)
# Side keels' clip lines (studs on a 20-grid at x, z = 10 + 20 n): a line through flange studs at
# slope p/q in plan; its 1 x 1 clips' bars run 20 LDU outside the studs (perpendicular).
CHINE_UP = dict(slope=(1, 3), stud=(-850.0, 90.0), y=-30.0, spacers=2)    # over the side keels
# under them (the quarters' lower facet c hangs on it; the bow's C ends under the side keels)
CHINE_LO = dict(slope=(2, 7), stud=(-530.0, 150.0), y=18.0, spacers=1)
# Spine side-stud clip lines (studs at x = 10 + 20 n, y = 2 + 8 n): slope dy/dx, a stud on it;
# the clips' bars run 20 LDU from the studs (up for the ridge, down for the keel), at |z| = W_SPINE.
# Both run on aft into the quarter (naut_quarters), where the core's side studs carry them.
RIDGE = dict(slope=0.36, stud=(-950.0, -70.0), up=True)
KEEL = dict(slope=0.4, stud=(-830.0, 18.0), up=False)
W_SPINE = 34.0                               # |z| of the spine's clip lines (a round plate on each side stud)
# Each facet: its grid edge and its diagonal edge (at 1:k to it), meeting at its apex.
#   A: grid on the side keels' line, diagonal on the crease AB (1:6)
#   E: grid on the crease, diagonal on the ridge (1:3)
#   c: grid on the line under the side keels, diagonal on the seam CD (1:3) (the quarters only)
#   C: grid on the seam, diagonal on the keel (1:6)
# The creases are solved so each facet meets its neighbours at those angles: the upper and lower
# cones close exactly, and their section where the midbody's panels end is theirs to within a
# few LDU (naut_quarters).
UPPER = "crease"                             # "crease" (A, E) or "rest" (E alone, resting)
LOWER = "seam"                               # "seam" (c, C) or "rest" (C alone, resting)
K = {"A": 6, "E": 3, "c": 3, "C": 6}         # each facet's wedge slope 1:k
FACETS = "AE"                                # the panels this module builds (the lower ones,
                                             # c and C: the quarters', naut_quarters)
# Hooks for reusing this module's cone for the tail's stock (naut_tail_new loads a second copy
# and sets these): what to build besides the spine, side keels and panels; the spine's own
# outline and cells left out of its wall; extra parts set into the wall.
DETAILS = {"ridge": True, "keel_teeth": True, "flange_teeth": True, "ram": True}
SPINE_PROFILE = None          # None, or a function -> ({column: top y}, {column: bottom y})
SPINE_SKIP = frozenset()      # (column, layer) cells kept out of the spine's wall
EXTRA_WALL = ()               # [(part, role, M)] set into the wall as it is built
FRAME = None                  # None, or a 4 x 4 turning everything built (see build_cone)
FLANGE_STRIP_TO = None        # None, or x: the side keels go on as a strip along the spine to x
SPINE_CLIP_EVERY = 1          # the spine's clip lines: a clip on every this many lattice steps
JOIN_CAPTION = "The spine on the hull's join, the side keels"
X_NEAR = (-1150.0, -900.0)                   # the creases' apexes (upper, lower): near here
STATION_JOINT = True          # the panels end on a grid line at the station (the quarters'
                              # panels on the same facets take over there)
PREFIX, TITLE = "bow", "The bow"             # sub-assembly names (the tail's stock reuses this)


def chine_line(c) -> Line:
    p, q = c["slope"]
    sl = p / q
    xs, zs = c["stud"]
    assert (xs - 10) % 20 == 0 and (zs - 10) % 20 == 0, f"chine stud {c['stud']} off the grid"
    off = 20 * math.sqrt(1 + sl * sl)
    # port: |z| grows aft at sl; the bar is `off` outboard of the studs' line (in z)
    z0 = zs + (XS - xs) * sl + off
    return Line((XS, c["y"], -z0), (-1.0, 0.0, sl))


def spine_line(c) -> Line:
    sl = c["slope"]
    xs, ys = c["stud"]
    assert (xs - 10) % 20 == 0 and (ys - 2) % 8 == 0, f"spine stud {c['stud']} off the lattice"
    off = 20 * math.sqrt(1 + sl * sl)
    if c["up"]:                 # the ridge: falls toward the bow (y grows as x falls)
        y0 = ys - sl * (XS - xs) - off
        return Line((XS, y0, -W_SPINE), (-1.0, sl, 0.0))
    y0 = ys + sl * (XS - xs) + off      # the keel: rises toward the bow
    return Line((XS, y0, -W_SPINE), (-1.0, -sl, 0.0))


def _crease(L1: Line, L2: Line, a1: float, a2: float, x_near: float, outward) -> tuple:
    """The line through a point P1 of L1 and a point P2 of L2 meeting L1 at a1 and L2 at a2
    degrees (the crease between two facets of given apex angles), the solution with both points
    nearest x_near whose crease bulges toward `outward` at the station."""
    def f(v):
        P1, P2 = L1.pt(v[0]), L2.pt(v[1])
        d = P2 - P1
        return [angd(d, L1.d) - a1, angd(d, L2.d) - a2]
    best = None
    for g1 in np.linspace(-200, 600, 9):
        for g2 in np.linspace(-200, 600, 9):
            v, info, ier, msg = fsolve(f, (g1, g2), full_output=True, xtol=1e-12)
            if ier != 1 or max(abs(np.array(f(v)))) > 1e-8:
                continue
            P1, P2 = L1.pt(v[0]), L2.pt(v[1])
            M = Line(P1, P2 - P1).at_x(XS)
            mid = (L1.at_x(XS) + L2.at_x(XS)) / 2
            if np.dot(M - mid, outward) <= 0:
                continue
            cost = abs(P1[0] - x_near) + abs(P2[0] - x_near)
            if best is None or cost < best[0]:
                best = (cost, P1, P2)
    if best is None:
        raise RuntimeError("crease did not solve")
    return best[1], best[2]


@lru_cache(maxsize=None)
def geometry() -> dict:
    """The port side's hinge lines and each facet's two lines and apex (world, hull frame):
    {facet: (grid line, diagonal line, apex, outward hint)}."""
    ri, ke = spine_line(RIDGE), spine_line(KEEL)
    deg = lambda k: math.degrees(math.atan(1 / k))
    out = {"ridge": ri, "keel": ke}
    if UPPER == "crease":
        cu = chine_line(CHINE_UP)
        # the crease AB: meets the side keels' line at A's angle, the ridge at E's
        PA, PE = _crease(cu, ri, deg(K["A"]), deg(K["E"]), X_NEAR[0], np.array([0.0, -0.6, -0.8]))
        ab = Line(PA, PE - PA)
        if ab.d[0] < 0:                          # the crease runs from its apex toward the station
            ab.d = -ab.d
        out["AB"] = ab
        out["A"] = (cu, ab, PA, np.array([0.0, -0.3, -1.0]))
        out["E"] = (ab, ri, PE, np.array([0.0, -1.0, -0.5]))
    else:
        # one panel a side over the side keels, hung on the ridge line, its diagonal edge
        # resting on them (as C's under them, below)
        cu, PE = _resting(ri, RIDGE["slope"], K["E"], CHINE_UP["y"])
        out["E"] = (ri, cu, PE, np.array([0.0, -1.0, -0.5]))
    out["chine_up"] = cu
    if LOWER == "seam":
        cl = chine_line(CHINE_LO)
        # the seam CD: meets the line under the side keels at c's angle, the keel at C's
        PC, PD = _crease(cl, ke, deg(K["c"]), deg(K["C"]), X_NEAR[1], np.array([0.0, 0.6, -0.8]))
        cd = Line(PC, PD - PC)
        if cd.d[0] < 0:
            cd.d = -cd.d
        out["CD"] = cd
        out["c"] = (cl, cd, PC, np.array([0.0, 0.3, -1.0]))
        out["C"] = (cd, ke, PD, np.array([0.0, 1.0, -0.5]))
    else:
        # under the side keels one panel a side, hung on the keel line: its diagonal edge runs
        # just under the side keels at the angle its 1:k wedge plates make with the keel line
        cl, PC = _resting(ke, KEEL["slope"], K["C"], CHINE_LO["y"])
        out["C"] = (ke, cl, PC, np.array([0.0, 1.0, -0.6]))
    out["chine_lo"] = cl
    return out


def _resting(L: Line, b: float, k: int, y_c: float) -> tuple:
    """A panel hung on spine line L (slope b, at |z| = W_SPINE) whose other edge is free, at
    height y_c along the side keels: the line there at the angle a 1:k wedge plate makes with
    L, meeting it (port side). Returns (that line, the apex)."""
    t = 1.0 / k
    a = math.sqrt((1 + t * t) / (1 + b * b) - 1)
    d = (y_c - L.at_x(XS)[1]) / (L.d[1] / -L.d[0])      # where L reaches y_c
    edge = Line((XS, y_c, -(W_SPINE + a * d)), (-1.0, 0.0, a))
    P = L.at_x(XS - d)
    assert abs(angd(L.d, edge.d) - math.degrees(math.atan(t))) < 1e-9
    assert np.linalg.norm(edge.at_x(XS - d) - P) < 1e-6
    return edge, P


# ------------------------------------------------------------------ parts' shapes
@lru_cache(maxsize=None)
def _engine():
    from brickkit.engine import Engine
    return Engine()


def canon(part: str) -> str:
    return _engine().catalog.canonical(part)


@lru_cache(maxsize=None)
def top_outline(part: str) -> np.ndarray:
    """A plate's top face outline in its own x-z plane (convex hull of its top vertices)."""
    from scipy.spatial import ConvexHull
    t = _engine().geom.mesh(canon(part)).tris.reshape(-1, 3)
    top = t[t[:, 1] < 0.5][:, [0, 2]]
    h = ConvexHull(top)
    return top[h.vertices]


@lru_cache(maxsize=None)
def studs_of(part: str) -> tuple:
    """(x, z) of a part's studs on its top (connectors pointing up at y = 0)."""
    out = []
    for c in _engine().shadow.connectors(canon(part)):
        if c.kind == "cyl" and c.gender == "M" and c.axis[1] < -0.99 and abs(c.origin[1]) < 0.5:
            out.append((round(float(c.origin[0]), 3), round(float(c.origin[2]), 3)))
    return tuple(sorted(set(out)))


def inside(poly: np.ndarray, p, eps: float = 0.5) -> bool:
    """Is point p inside convex polygon poly (counter- or clockwise), by eps?"""
    n = len(poly)
    sgn = 0
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        cr = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
        ln = math.hypot(b[0] - a[0], b[1] - a[1])
        d = cr / ln
        if abs(d) < eps:
            continue
        s = 1 if d > 0 else -1
        if sgn == 0:
            sgn = s
        elif s != sgn:
            return False
    return True


def Ry(deg: float) -> np.ndarray:
    return rot(y=deg)


# wedge plates by slope: (part with its full column at +x, part with it at -x)
WEDGES = {4: ("41769", "41770"), 6: ("78444", "78443"), 3: ("43722", "43723"), 2: ("24299", "24307")}
PLATE = {(1, 1): "3024", (1, 2): "3023", (1, 3): "3623", (1, 4): "3710", (1, 6): "3666",
         (1, 8): "3460", (1, 10): "4477", (1, 12): "60479", (2, 2): "3022", (2, 3): "3021",
         (2, 4): "3020", (2, 6): "3795", (2, 8): "3034", (2, 10): "3832", (2, 12): "2445",
         (4, 4): "3031", (4, 6): "3032", (4, 8): "3035", (4, 10): "3030", (4, 12): "3029",
         (6, 6): "3958", (6, 8): "3036", (6, 10): "3033", (6, 12): "3028"}
TILE = {(1, 1): "3070b", (1, 2): "3069b", (1, 3): "63864", (1, 4): "2431", (1, 6): "6636",
        (1, 8): "4162", (2, 2): "3068b", (2, 4): "87079"}
BRICK = {(1, 1): "3005", (1, 2): "3004", (1, 3): "3622", (1, 4): "3010", (1, 6): "3009",
         (1, 8): "3008", (2, 2): "3003", (2, 3): "3002", (2, 4): "3001", (2, 6): "2456",
         (2, 8): "3007"}


def rect_part(table: dict, w: int, d: int):
    """(part, R) for a rectangle w cells along local x by d along local z."""
    part = table[(min(w, d), max(w, d))]
    from brickkit.engine import Engine  # noqa: F401  (engine cached in _engine)
    lo, hi = _engine().geom.mesh(canon(part)).bbox
    along_x = abs((hi[0] - lo[0]) - S * w) < 1 and abs((hi[2] - lo[2]) - S * d) < 1
    return part, (np.eye(3) if along_x else rot(y=90))


def pack(cells: set, sizes, prefer_rows=None, shift: int = 0, groups=None) -> list:
    """Cover cells (i, j) with rectangles (i0, i1, j0, j1), biggest first; `prefer_rows`: tuple of
    rows a rectangle should span together if it can (e.g. (0, 1): the overhang row with the row
    over the carrier); `groups` {cell: piece}: prefer rectangles joining pieces not yet joined."""
    free = set(cells)
    cand = set()
    for a, b in sizes:
        cand |= {(a, b), (b, a)}
    cand = sorted(cand, key=lambda s: (-s[0] * s[1], -s[0]))
    seq = sorted(free, key=lambda c: (c[1], c[0]))
    if shift and seq:
        seq = seq[shift % len(seq):] + seq[:shift % len(seq)]
    parent = {}

    def root(a):
        parent.setdefault(a, a)
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    out = []
    for c in seq:
        if c not in free:
            continue
        best = None
        for w, d in cand:
            for oa in range(w):
                for ob in range(d):
                    i0, j0 = c[0] - oa, c[1] - ob
                    box = {(i0 + a, j0 + b) for a in range(w) for b in range(d)}
                    if not box <= free:
                        continue
                    rows = {j0 + b for b in range(d)}
                    joins = bool(prefer_rows) and set(prefer_rows) <= rows
                    links = len({root(groups[x]) for x in box if groups and x in groups})
                    score = (links, joins, w * d, w)
                    if best is None or score > best[0]:
                        best = (score, box, (i0, i0 + w - 1, j0, j0 + d - 1))
        if best is None:
            raise ValueError(f"cannot cover cell {c}")
        free -= best[1]
        out.append(best[2])
        if groups:
            ids = [root(groups[x]) for x in best[1] if x in groups]
            for a in ids[1:]:
                parent[root(a)] = root(ids[0])
    return out


# ------------------------------------------------------------------ the panels
SKIN_DIAG = {"crease": 4.0, "chine": -11.5, "rest": -4.0, "ridge": -14.0, "seam": 8.0}     # the skin's diagonal edge: this far inside its
                                                 # hinge (+) or past it (-), on a grid corner line
GRID_LIP = {"E": True, "C": True}               # panels whose grid edge (a crease) has a lip
LIP_UNDER = {"E": "A", "C": "c"}                 # ... over this panel's diagonal edge
LIP_OVER = {v: k for k, v in LIP_UNDER.items()}
RING = 9.6                                       # carrier keeps this far from a clip's bar...
RING_AX = 5.5                                    # ...within this of the clip along it


class Panel:
    """A facet's panel in its own frame: x along its grid-edge hinge, z across (in), y inward.
    Hinge plane y = 0; layers: clips y -2..6 (under), carrier -10..-2, skin -18..-10, tiles
    -26..-18. The grid hinge runs at z = 10; the diagonal one leaves the apex (x_P, 10) at 1:k."""

    def __init__(self, name: str, side: int, cut=None):
        """`cut`: which part of the facet this panel is: {"x_max": world x its cells stay
        behind (default the station), "x_min", "y_min": world y they stay under, "joint":
        ("fore" | "aft", x): the side of the grid column line nearest x (wholly forward of x)
        it keeps, "forbid": f(world corners) -> True to leave a cell out}."""
        self.name, self.side = name, side
        self.cut = dict(x_max=XS) if cut is None else dict(cut)
        G, D, P, hint = geometry()[name]
        if side > 0:
            G, D = G.mirror(), D.mirror()
            P, hint = P * (1, 1, -1), hint * (1, 1, -1)
        self.G, self.D, self.P = G, D, P
        self.k = K[name]
        n = unit(np.cross(G.d, D.d))
        n = -n if n @ hint < 0 else n
        self.n = n
        ey = -n
        ex = unit(G.d)
        dD = D.d if D.d[0] > 0 else -D.d            # the diagonal from the apex toward the station
        if np.dot(np.cross(ex, ey), dD) < 0:
            ex = -ex
        ez = np.cross(ex, ey)
        self.R = orient(ex, ey, ez)
        self.sig = 1 if ex[0] > 0 else -1            # local +x toward the station?
        th = math.atan(1 / self.k)
        self.th = th
        self.u = np.array([self.sig * math.cos(th), math.sin(th)])      # diag direction (x, z)
        self.nu = np.array([self.sig * math.sin(th), -math.cos(th)])    # its inward normal
        r = math.sqrt(self.k ** 2 + 1)
        self.xP = (10 - self.sig * 20 * r) % 20
        self.O = P - self.R @ np.array([self.xP, 0.0, 10.0])
        self.M = np.eye(4)
        self.M[:3, :3], self.M[:3, 3] = self.R, self.O
        if name == "E" and UPPER == "rest":
            kind = "rest"                               # a free edge resting on the side keels
        elif name == "C" and LOWER == "rest":
            kind = "chine"
        else:
            kind = {"A": "crease", "c": "seam", "E": "ridge", "C": "ridge"}[name]
        self.kind = kind
        self.c_diag = self._corner_offset(SKIN_DIAG[kind])
        self.diag_hinged = not ((name == "E" and UPPER == "rest") or
                                (name == "C" and LOWER == "rest"))   # clips along its diagonal
        self.cols = None
        for key in ("joint", "joint2"):          # a grid column line at each end, if any
            if key in self.cut:
                lo, hi = self._joint_cols(*self.cut[key])
                if self.cols is not None:
                    lo, hi = max(lo, self.cols[0]), min(hi, self.cols[1])
                self.cols = (lo, hi)

    # -- coordinates
    def world(self, x, y, z) -> np.ndarray:
        return self.O + self.R @ np.array([x, y, z], float)

    def d_diag(self, x, z) -> float:
        """Signed distance inside the diagonal hinge (toward the grid edge)."""
        return float((np.array([x, z]) - (self.xP, 10.0)) @ self.nu)

    def a_diag(self, x, z) -> float:
        return float((np.array([x, z]) - (self.xP, 10.0)) @ self.u)

    def a_grid(self, x) -> float:
        return self.sig * (x - self.xP)

    def _corner_offset(self, target: float) -> float:
        """The grid-corner line parallel to the diagonal nearest `target` inside it."""
        best = None
        for i in range(-30, 30):
            for j in range(-3, 4):
                d = self.d_diag(20 * i, 20 * j)
                if best is None or abs(d - target) < abs(best - target):
                    best = d
        return best

    def station_ok(self, x0, x1, z0, z1, y0, y1) -> bool:
        """Is the box (local x0..x1, z0..z1, y0..y1) within this panel's part of its facet?"""
        c = self.cut
        if self.cols is not None:
            lo, hi = self.cols
            if min(x0, x1) < lo - 0.01 or max(x0, x1) > hi + 0.01:
                return False
        pts = [self.world(x, y, z) for x in (x0, x1) for z in (z0, z1) for y in (y0, y1)]
        for w in pts:
            if w[0] > c.get("x_max", 1e9) + 0.01 or w[0] < c.get("x_min", -1e9) - 0.01:
                return False
            if w[1] < c.get("y_min", -1e9) - 0.01:
                return False
        if c.get("forbid") is not None and c["forbid"](pts):
            return False
        return True

    def _joint_cols(self, keep: str, x: float) -> tuple:
        """The local x range of the columns on one side ("fore": toward the apex; "aft") of the
        grid column line nearest the plane x whose whole length is forward of it."""
        th = self.th

        def span(u):                  # the column line at local x = u, across the panel
            zd = 10 + self.sig * (u - self.xP) * math.tan(th) + 30
            return [self.world(u, y, z)[0] for y in (-26.0, 6.0)
                    for z in np.linspace(-10.0, max(zd, 0.0), 12)]

        def max_x(u):
            return max(span(u))

        def min_x(u):
            return min(span(u))
        us = [20 * i for i in range(-80, 80)]
        if keep == "aft" and self.cut.get("joint_last", False):
            # the aft part's end: the first column line wholly aft of x
            cand = [u for u in us if min_x(u) >= x - 0.01]
            u = min(cand) if self.sig > 0 else max(cand)
        else:
            cand = [u for u in us if max_x(u) <= x + 0.01]
            u = max(cand) if self.sig > 0 else min(cand)       # the last one before x
        if keep == "fore":
            return (-1e9, u) if self.sig > 0 else (u, 1e9)
        return (u, 1e9) if self.sig > 0 else (-1e9, u)

    def diag_studs(self) -> list:
        """Stud centres (x, z) of the 1 x 1 clips along the diagonal: 20 inside its hinge."""
        out = []
        for j in range(0, 40):
            t = 20 * (j + math.cos(self.th)) / math.sin(self.th)
            q = np.array([self.xP, 10.0]) + t * self.u + 20 * self.nu
            if abs((q[0] - 10) / 20 - round((q[0] - 10) / 20)) > 1e-6 or \
                    abs((q[1] - 10) / 20 - round((q[1] - 10) / 20)) > 1e-6:
                raise AssertionError(f"{self.name}: diagonal studs off the grid {q}")
            out.append((float(round(q[0], 6)), float(round(q[1], 6))))
        return out

    # -- the cells of each layer
    def layout(self):
        """Skin: rectangles' cells and the wedge slots along the diagonal; carrier cells."""
        k, sig = self.k, self.sig
        nx, nz = self.nu
        c = self.c_diag
        # the skin's corner line crosses row boundary z = 20 m at x_m
        xm = {}
        for m in range(0, 12):
            x = self.xP + (c - (20 * m - 10) * nz) / nx
            if abs(x / 20 - round(x / 20)) > 1e-6:
                raise AssertionError(f"{self.name}: corner line off the grid at z={20 * m}: {x}")
            xm[m] = round(x)
        skin_lv, car_lv = (-18.0, -10.0), (-10.0, -2.0)
        wedges, cells = [], set()
        col_seg = {}
        for m in range(1, 11):
            xa, xb = xm[m], xm[m + 1]
            lo, hi = min(xa, xb), max(xa, xb)
            for i in range(lo // 20, hi // 20):
                col_seg[i] = m
            if not self.station_ok(lo, hi, 20 * (m - 1), 20 * (m + 1), *skin_lv):
                continue
            wedges.append(dict(m=m, x0=lo, x1=hi, wide=xb))
        wcols = {(i, j) for w in wedges for i in range(w["x0"] // 20, w["x1"] // 20)
                 for j in (w["m"] - 1, w["m"])}
        for i, m in col_seg.items():
            for j in range(0, m + 1):
                if (i, j) in wcols:
                    continue
                x0, x1 = 20 * i, 20 * i + 20
                z0, z1 = 20 * j, 20 * j + 20
                if min(self.d_diag(x, z) for x in (x0, x1) for z in (z0, z1)) < c - 0.01:
                    continue
                if self.station_ok(x0, x1, z0, z1, *skin_lv):
                    cells.add((i, j))
        full = cells | {(i, w["m"] - 1) for w in wedges for i in range(w["x0"] // 20, w["x1"] // 20)}
        studs = {(int(math.floor(x / 20)), int(math.floor(z / 20))) for x, z in self.diag_studs()}
        carrier = set()
        for (i, j) in full:
            if j < 1:
                continue
            x0, x1, z0, z1 = 20 * i, 20 * i + 20, 20 * j, 20 * j + 20
            dmin = min(self.d_diag(x, z) for x in (x0, x1) for z in (z0, z1))
            if dmin < (0.5 if (i, j) in studs or not self.diag_hinged else RING):
                continue
            if self.station_ok(x0, x1, z0, z1, *car_lv) and \
                    self.station_ok(x0, x1, z0, z1, 6.0, 6.0):
                carrier.add((i, j))
        return dict(skin=cells, wedges=wedges, carrier=carrier, full=full)

    # -- parts
    def wedge_part(self, w) -> tuple:
        """(part, local 4x4) of the wedge plate for a slot: its full row m-1, its triangle row m
        wide at x = wide, k cells along x."""
        k, m = self.k, w["m"]
        xc = (w["x0"] + w["x1"]) / 2
        zc = 20.0 * m                          # between the full row and the triangle row
        full_pt = (xc, zc - 10)
        wide_pt = (w["wide"] - self.sig * 5, zc + 10 - 3)     # in the triangle near its wide end
        narrow_pt = (w["wide"] - self.sig * (20 * k - 5), zc + 10 + 6)   # outside, narrow end
        for part in WEDGES[k]:
            poly0 = top_outline(part)
            for deg in (90, -90):
                R = Ry(deg)
                poly = np.array([(R @ np.array([p[0], 0, p[1]]))[[0, 2]] for p in poly0]) + (xc, zc)
                if inside(poly, full_pt) and inside(poly, wide_pt) and not inside(poly, narrow_pt):
                    M = np.eye(4)
                    M[:3, :3], M[:3, 3] = R, (xc, -18.0, zc)
                    return part, M
        raise AssertionError(f"{self.name}: no wedge fits slot {w}")


class FlatPanel:
    """A flat panel on a facet hung on one hinge line, its grid along that line (the hinge at
    local z = 10, the panel toward +z), its other edges where `inside` (a test on points of the
    facet's plane, world) and its `cut` (as Panel's) allow, stepped by whole cells: Panel's layers
    and parts, without wedge plates. Duck-types Panel for the clip pairing and panel_parts."""

    def __init__(self, name: str, side: int, hinge: Line, normal, toward, inside,
                 cut=None, cols=None, rows=14, x0: float = 0.0, thin: bool = False):
        """`hinge`: the hinge line (world); `normal`: the facet's outward normal; `toward`: a
        point inside the facet (the panel's side of the hinge); `x0`: the world x of a grid
        column line (the grid's phase along the hinge)."""
        self.name, self.side = name, side
        self.cut = dict(cut or {})
        self.inside = inside
        self.thin = thin                 # the midbody's thickness: carrier and tiles (18 out)
        self.cols_range, self.rows = cols, rows
        n = unit(normal)
        self.n = n
        ex = unit(hinge.d if hinge.d[0] >= 0 else -hinge.d)
        ey = -n
        ez = np.cross(ex, ey)
        P0 = hinge.at_x(x0)
        if (np.asarray(toward, float) - P0) @ ez < 0:
            ex = -ex
            ez = np.cross(ex, ey)
        self.R = orient(ex, ey, ez)
        self.sig = 1 if ex[0] > 0 else -1
        self.O = P0 - self.R @ np.array([0.0, 0.0, 10.0])
        self.M = np.eye(4)
        self.M[:3, :3], self.M[:3, 3] = self.R, self.O
        self.k = None
        self.cols = None
        self.diag_hinged = False
        if cols is None:                         # the columns over the cut's x range
            xa, xb = self.cut.get("x_min", -1000.0), self.cut.get("x_max", 1000.0)
            us = [(hinge.at_x(x) - self.O) @ ex for x in (xa, xb)]
            self.cols_range = (int(math.floor(min(us) / 20)) - 2, int(math.ceil(max(us) / 20)) + 2)

    def world(self, x, y, z) -> np.ndarray:
        return self.O + self.R @ np.array([x, y, z], float)

    def station_ok(self, x0, x1, z0, z1, y0, y1) -> bool:
        c = self.cut
        pts = [self.world(x, y, z) for x in (x0, x1) for z in (z0, z1) for y in (y0, y1)]
        for w in pts:
            if w[0] > c.get("x_max", 1e9) + 0.01 or w[0] < c.get("x_min", -1e9) - 0.01:
                return False
            if w[1] < c.get("y_min", -1e9) - 0.01 or w[1] > c.get("y_max", 1e9) + 0.01:
                return False
        if c.get("forbid") is not None and c["forbid"](pts):
            return False
        return True

    def _in(self, x0, x1, z0, z1) -> bool:
        return all(self.inside(self.world(x, 0.0, z)) for x in (x0, x1) for z in (z0, z1))

    def diag_studs(self) -> list:
        return []

    @lru_cache(maxsize=None)
    def layout(self):
        skin, carrier = set(), set()
        top = -18.0 if self.thin else -26.0
        for i in range(*self.cols_range):
            for j in range(0, self.rows):
                x0, x1, z0, z1 = 20 * i, 20 * i + 20, 20 * j, 20 * j + 20
                if not self._in(x0, x1, z0, z1) or not self.station_ok(x0, x1, z0, z1,
                                                                        top, -10.0):
                    continue
                skin.add((i, j))
                if j >= 1 and self.station_ok(x0, x1, z0, z1, -10.0, -2.0) and \
                        self.station_ok(x0, x1, z0, z1, 6.0, 6.0):
                    carrier.add((i, j))
        return dict(skin=skin, wedges=[], carrier=carrier, full=set(skin))

    def __hash__(self):
        return id(self)

    def thin_parts(self, grid_cols, shift: int = 0) -> list:
        """The thin panel's parts in its frame: plates over the carrier's cells (-10 .. -2),
        tiles over them (-18 .. -10); the skin's cells with no carrier under them (row 0 along
        the hinge, the cut edges' last cells) under tiles two rows deep, resting on the row
        next to them; the grid edge's clips under row 1: [(part, role, M, cat, insert)]."""
        lay = self.layout()
        car = lay["carrier"]
        out = []
        rects = pack(car, PANEL_PLATES, prefer_rows=None, shift=shift)
        piece = {}
        for n, (i0, i1, j0, j1) in enumerate(rects):
            part, R = rect_part(PLATE, i1 - i0 + 1, j1 - j0 + 1)
            out.append((part, ROLE, _M(R, (20 * (i0 + i1 + 1) / 2, -10.0, 20 * (j0 + j1 + 1) / 2)),
                        "carrier", None))
            for i in range(i0, i1 + 1):
                for j in range(j0, j1 + 1):
                    piece[(i, j)] = n
        done = set()
        # each bare skin cell with its neighbour across the rows (the one toward the carrier)
        pairs = {}
        for i, j in sorted(lay["skin"] - car):
            for dj in (1, -1):
                if (i, j + dj) in car and (i, j + dj) not in done:
                    pairs.setdefault((j, dj), []).append(i)
                    done |= {(i, j), (i, j + dj)}
                    break
        for (j, dj), cols in sorted(pairs.items()):
            jl = min(j, j + dj)
            k = 0
            while k < len(cols):
                run = [cols[k]]
                while k + 1 < len(cols) and cols[k + 1] == run[-1] + 1 and len(run) < 4:
                    k += 1
                    run.append(cols[k])
                k += 1
                start = run[0]
                left = len(run)
                while left > 0:
                    ln = 4 if left >= 4 else (2 if left >= 2 else 1)
                    if ln == 1:
                        out.append(("3069b", ROLE, _M(rot(y=90), (20 * start + 10, -18.0,
                                                                   20.0 * jl + 20)), "tiles", None))
                    else:
                        part, R = rect_part(TILE, ln, 2)
                        out.append((part, ROLE, _M(R, (20 * start + 10 * ln, -18.0, 20.0 * jl + 20)),
                                    "tiles", None))
                    start += ln
                    left -= ln
        rest = {c for c in car if c not in done}
        for i0, i1, j0, j1 in pack(rest, PANEL_TILES, shift=shift, groups=piece):
            part, R = rect_part(TILE, i1 - i0 + 1, j1 - j0 + 1)
            out.append((part, ROLE, _M(R, (20 * (i0 + i1 + 1) / 2, -18.0, 20 * (j0 + j1 + 1) / 2)),
                        "tiles", None))
        for i in grid_cols:
            out.append((CLIP1, CLIP_ROLE, _M(np.eye(3), (20 * i + 10, -2.0, 30.0)), "clips",
                        (0, 1, 0)))
        return out


def half_spaces(planes, margins) -> callable:
    """A test for points: inside every plane (point, outward normal) within its margin (+ out
    past it, - short of it)."""
    def inside(w):
        return all((w - p) @ n <= m for (p, n), m in zip(planes, margins))
    return inside


def _M(R, pos) -> np.ndarray:
    M = np.eye(4)
    M[:3, :3] = np.asarray(R, float)
    M[:3, 3] = pos
    return M


def components(parts) -> list:
    """Connected groups of [(part, M)] (by real connections)."""
    from brickkit.snaps.match import find_connections
    eng = _engine()
    conns = [[c.transformed(np.asarray(M, float)) for c in eng.shadow.connectors(canon(p))]
             for p, M in parts]
    parent = list(range(len(parts)))

    def root(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for c in find_connections(conns):
        parent[root(c.a)] = root(c.b)
    groups = {}
    for i in range(len(parts)):
        groups.setdefault(root(i), []).append(i)
    return list(groups.values())


PANEL_PLATES = [s for s in PLATE if s[0] <= 2 and s[1] <= 8]
PANEL_TILES = [(1, 1), (1, 2), (1, 3), (1, 4), (1, 6), (1, 8), (2, 2), (2, 4)]


def _panel_parts(p: Panel, grid_cols, diag_studs, shift: int = 0):
    L = p.layout()
    out = []                       # (part, role, M, cat, insert)
    # carrier
    for i0, i1, j0, j1 in pack(L["carrier"], PANEL_PLATES, shift=shift):
        part, R = rect_part(PLATE, i1 - i0 + 1, j1 - j0 + 1)
        out.append((part, ROLE, _M(R, (20 * (i0 + i1 + 1) / 2, -10.0, 20 * (j0 + j1 + 1) / 2)),
                    "carrier", None))
    # skin: wedges, then rectangles (the overhang row with the one over the carrier)
    studs, piece = set(), {}
    for n, w in enumerate(L["wedges"]):
        part, M = p.wedge_part(w)
        out.append((part, ROLE, M, "skin", None))
        for sx, sz in studs_of(canon(part)):
            q = M[:3, :3] @ np.array([sx, 0, sz]) + M[:3, 3]
            c = (int(math.floor(q[0] / 20)), int(math.floor(q[2] / 20)))
            studs.add(c)
            piece[c] = ("w", n)
    for n, (i0, i1, j0, j1) in enumerate(pack(L["skin"], PANEL_PLATES, prefer_rows=(0, 1),
                                               shift=shift)):
        part, R = rect_part(PLATE, i1 - i0 + 1, j1 - j0 + 1)
        out.append((part, ROLE, _M(R, (20 * (i0 + i1 + 1) / 2, -18.0, 20 * (j0 + j1 + 1) / 2)),
                    "skin", None))
        for i in range(i0, i1 + 1):
            for j in range(j0, j1 + 1):
                studs.add((i, j))
                piece[(i, j)] = ("r", n)
    # a lip of tiles a row past the grid edge where it is a crease (GRID_LIP): over the
    # neighbouring panel's stepped edge, it closes the seam; tiles two rows deep, on row 0
    lip = [i for i in sorted({i for i, j in studs if j == 0})
           if GRID_LIP.get(p.name) and p.station_ok(20 * i, 20 * i + 20, -20.0, 0.0, -26.0, -18.0)]
    if set(lip) & _lip_banned(p):
        lip = []                       # all along the edge or not at all (no ragged edge)
    run = []
    for i in lip + [None]:
        if run and (i is None or i != run[-1] + 1 or len(run) == 4):
            k = 0
            while k < len(run):
                ln = 4 if len(run) - k >= 4 else (2 if len(run) - k >= 2 else 1)
                part, R = rect_part(TILE, ln, 2)
                out.append((part, ROLE, _M(R, (20 * run[k] + 10 * ln, -26.0, 0.0)), "skin", None))
                studs -= {(run[k] + m, 0) for m in range(ln)}
                k += ln
            run = []
        if i is not None:
            run.append(i)
    studs -= getattr(p, "no_tile", set())  # (under the neighbouring panel's lip: bare studs)
    for i0, i1, j0, j1 in pack(studs, PANEL_TILES, shift=shift, groups=piece):
        part, R = rect_part(TILE, i1 - i0 + 1, j1 - j0 + 1)
        out.append((part, ROLE, _M(R, (20 * (i0 + i1 + 1) / 2, -26.0, 20 * (j0 + j1 + 1) / 2)),
                    "skin", None))
    # clips under the carrier
    for i in grid_cols:              # a 1 x 1 clip on the first row over the carrier
        assert (i, 1) in L["carrier"], f"{p.name}: grid clip off the carrier"
        out.append((CLIP1, CLIP_ROLE, _M(np.eye(3), (20 * i + 10, -2.0, 30.0)), "clips",
                    (0, 1, 0)))
    for xs, zs in diag_studs:
        ex = np.array([p.u[0], 0, p.u[1]])
        if np.dot(np.cross(ex, (0, 1, 0))[[0, 2]], p.nu) < 0:
            ex = -ex
        R = orient(ex, (0, 1, 0))
        out.append((CLIP1, CLIP_ROLE, _M(R, (xs, -2.0, zs)), "clips", (0, 1, 0)))
    return out


def prepare_lip(lower, upper) -> None:
    """Before the lower panel's parts are made: leave bare (no tile) its studs that a tile of
    the upper panel's lip (GRID_LIP, over the lower panel's diagonal edge) would sit on: the lip
    covers them. Sets lower.no_tile (cells in its frame)."""
    if not GRID_LIP.get(upper.name):
        return
    rows0 = sorted({i for i, j in upper.layout()["skin"] if j == 0})
    lips = [upper.M @ _M(Ry(90), (20 * i + 10, -26.0, 0.0)) for i in rows0
            if upper.station_ok(20 * i, 20 * i + 20, -20.0, 0.0, -26.0, -18.0)]
    lay = lower.layout()
    cells = set(lay["skin"]) | {(i, j) for w in lay["wedges"]
                                for i in range(w["x0"] // 20, w["x1"] // 20)
                                for j in (w["m"] - 1, w["m"])}
    no = set()
    for i, j in cells:
        Mt = lower.M @ _M(np.eye(3), (20 * i + 10, -26.0, 20 * j + 10))
        if any(np.linalg.norm(Mt[:3, 3] - Ml[:3, 3]) < 100 and _clash("3070b", Mt, "3069b", Ml)
               for Ml in lips):
            no.add((i, j))
    lower.no_tile = no


def _lip_banned(p) -> set:
    """Columns where the grid edge's lip would hit the neighbouring panel's parts
    (p.lip_avoid: [(part, M)] in the panel's parent frame)."""
    if getattr(p, "_lip_ban", None) is None:
        ban = set()
        for i in range(-80, 80):
            Mt = p.M @ _M(Ry(90), (20 * i + 10, -26.0, 0.0))     # a 1 x 2 tile across the lip
            if any(_clash("3069b", Mt, q, Mq) for q, Mq in getattr(p, "lip_avoid", ())
                   if np.linalg.norm(np.asarray(Mq)[:3, 3] - Mt[:3, 3]) < 120):
                ban.add(i)
        p._lip_ban = ban
    return p._lip_ban


def panel_parts(p: Panel, grid_cols, diag_studs):
    """The panel's parts, packed so they hold together as one piece."""
    best = None
    thin = getattr(p, "thin", False)
    for shift in (range(0, 240) if thin else range(0, 40, 3)):
        if thin:
            out = p.thin_parts(grid_cols, shift)
        else:
            out = _panel_parts(p, grid_cols, diag_studs, shift)
        n = len(components([(q[0], q[2]) for q in out]))
        if best is None or n < best[0]:
            best = (n, out)
        if n == 1:
            break
    if best[0] > 1:                          # drop stray bits (by the station's cut)
        out = best[1]
        comps = sorted(components([(q[0], q[2]) for q in out]), key=len)
        keep = set(comps[-1])
        if len(keep) < len(out) - 4:
            print(f"warning: panel {p.name}{p.side}: {best[0]} pieces")
        return [q for k, q in enumerate(out) if k in keep]
    return best[1]


# ------------------------------------------------------------------ emitting
def emit(sub, items, per_step: int = 8, caption: str = "", connected: bool = False):
    """Place [(part, role, M, cat, insert)] into `sub` in order, a few per step, a new step
    whenever the category changes. `connected`: a step only ends once what is built of these
    items holds together (so no step leaves loose pieces)."""
    cat_prev, n = None, 0
    built = []
    for k, (part, role, M, cat, ins) in enumerate(items):
        cut = cat != cat_prev or n >= per_step
        if cut and connected and built and cat == cat_prev:
            cut = len(components(built)) == 1
        if cut:
            sub.step(caption if cat_prev is None else "")
            cat_prev, n = cat, 0
        pl = sub.place(part, role, (0, 0, 0), tag="", insert=ins)
        pl.M = np.asarray(M, float)
        built.append((part, np.asarray(M, float)))
        n += 1


def use_M(parent, child, M, tag: str = "", insert=None):
    M = np.asarray(M, float)
    return parent.use(child, tuple(M[:3, 3]), M[:3, :3], tag=tag, insert=insert)


# ------------------------------------------------------------------ the fixed clips
def _clip_R(axis, ey, offset_dir) -> np.ndarray:
    """A 1 x 1 clip (61252) with its local y along ey, its clip's bar along `axis` and its clip
    reaching out (local -z) toward `offset_dir`."""
    for ex in (unit(axis), -unit(axis)):
        ez = np.cross(ex, ey)
        if np.dot(-ez, offset_dir) > 0:
            return orient(ex, ey, ez)
    raise AssertionError("clip orientation")


def chine_clips(side: int, which: str, xr=None) -> list:
    """The side keels' clip stacks for one hinge line, studs within x range `xr` (default: the
    bow's side keels): [(parts [(part, role, M)], clip point)]."""
    xr = (FLANGE_TIP, XS - 14) if xr is None else xr
    c = CHINE_UP if which == "up" else CHINE_LO
    L = chine_line(c)
    if side > 0:
        L = L.mirror()
    p, q = c["slope"]
    xs, zs = c["stud"]
    out = []
    for m in range(-3, 12):
        x = xs - 20 * q * m
        z = (zs - 20 * p * m) * side
        if z * side < 34 or not xr[0] <= x <= xr[1]:
            continue                          # inside the spine, or out of range
        stud = np.array([x, 0.0, z])
        perp = unit(np.array([-L.d[2], 0.0, L.d[0]]))
        if perp[2] * side < 0:
            perp = -perp                      # outboard
        R = _clip_R(L.d, (0, 1, 0), perp)
        parts = []
        if which == "up":
            for n in range(c["spacers"]):
                parts.append((RP, CORE, _M(np.eye(3), (x, -16.0 - 8 * n, z))))
            y = -16.0 - 8 * c["spacers"]
        else:
            for n in range(c["spacers"]):
                parts.append((RP, CORE, _M(np.eye(3), (x, 8.0 + 8 * n, z))))
            y = 8.0 + 8 * c["spacers"]
        parts.append((CLIP1, CLIP_ROLE, _M(R, (x, y, z))))
        pt = stud + 20 * perp
        pt[1] = c["y"]
        assert np.linalg.norm(np.cross(pt - L.p, L.d)) < 1e-6, "chine clip off its line"
        out.append((parts, pt))
    return out


def spine_clips(side: int, which: str, xr=None, avail=None, every=None) -> list:
    """Clip plates on side studs for the ridge ('up') or keel line, studs within x range `xr`
    (default: the bow's spine) where `avail(x, y)` (default: anywhere, the spine's own side-stud
    bricks): [(parts, point, (column, top y of the side-stud brick))]."""
    xr = (S * I_NOSE, XS - 30) if xr is None else xr
    c = RIDGE if which == "up" else KEEL
    L = spine_line(c)
    if side > 0:
        L = L.mirror()
    xs, ys = c["stud"]
    sl = c["slope"]
    n_step = next(n for n in range(1, 41) if abs(sl * 20 * n / 8 - round(sl * 20 * n / 8)) < 1e-9)
    out = []
    for m in range(-60, 60):
        x = xs - 20 * n_step * m
        dy = sl * 20 * n_step * m
        y = ys + dy if c["up"] else ys - dy
        if not xr[0] <= x <= xr[1] or m % (every or SPINE_CLIP_EVERY):
            continue                          # out of range
        if avail is not None:
            if not avail(x, y):
                continue
        elif (c["up"] and y - 10 + 24 > -8) or (not c["up"] and y - 10 < 8):
            continue                          # its side-stud brick would cut the side keels
        stud = np.array([x, y, side * 20.0])
        up = c["up"]
        perp = unit(np.array([-L.d[1], L.d[0], 0.0]))
        if (perp[1] < 0) != up:
            perp = -perp
        ey = np.array([0.0, 0.0, -side])     # underside toward the spine, onto the side stud
        R = _clip_R(L.d, ey, perp)
        M = _M(R, (x, y, side * 36.0))
        Rs = orient((1.0, 0.0, 0.0), ey)
        spacer = (RP, CORE, _M(Rs, (x, y, side * 28.0)))
        pt = stud + 20 * perp
        pt[2] = side * W_SPINE
        assert np.linalg.norm(np.cross(pt - L.p, L.d)) < 1e-6, "spine clip off its line"
        out.append(([spacer, (CLIP1, CLIP_ROLE, M)], pt, (int(math.floor(x / 20)), y - 10)))
    return out


# ------------------------------------------------------------------ pairing clips into hinges
BARS = {60: "87994", 80: "30374"}            # bar 3L, bar 4L (their origin at one end, along +y)


def _axial(L: Line, pt) -> float:
    return float((np.asarray(pt, float) - L.p) @ L.d)


def _bar(L: Line, a, b, role=CORE):
    """A bar on line L spanning clip points a and b (world): (part, role, M). Up to 80 apart a
    plain bar (3L, 4L); further, the long end of a bar 6L with a stop ring (63965: the ring 18
    from its end, then 95 of bar), the ring beyond clip a."""
    ta, tb = _axial(L, a), _axial(L, b)
    span = abs(ta - tb) + 16
    d = L.d
    ex = unit(np.cross(d, (0.0, 0.0, 1.0)) if abs(d[2]) < 0.9 else np.cross(d, (1.0, 0, 0)))
    if span <= max(BARS):
        length = next(n for n in sorted(BARS) if n >= span)
        mid = L.p + (ta + tb) / 2 * d
        return (BARS[length], role, _M(orient(ex, d, np.cross(ex, d)), mid - d * length / 2))
    if span > 95 + 2:
        raise AssertionError(f"clips {span - 16:.1f} apart: no bar long enough")
    # 63965: its connector runs from y = 18 (one end) toward -y: 18 of bar, the ring, 95 of bar
    s = 1.0 if tb > ta else -1.0
    start = ta - s * 6.0                     # the long part's end, just beyond clip a
    e = d * s                                # local -y runs from the ring along the long part
    ey = -e
    R = orient(unit(np.cross(ey, (0.0, 0.0, 1.0)) if abs(ey[2]) < 0.9 else np.cross(ey, (1.0, 0, 0))), ey)
    R = orient(R[:, 0], ey, np.cross(R[:, 0], ey))
    origin = L.p + start * d - ey * (-7.5)   # local y = -7.5 (the long part's start) at `start`
    return ("63965", role, _M(R, origin))


def _diag_clips(p: Panel, L: Line) -> list:
    """The panel's possible clips along its diagonal: [(local stud (x, z), world clip point)]."""
    lay = p.layout()
    out = []
    for xs, zs in p.diag_studs():
        cell = (int(math.floor(xs / 20)), int(math.floor(zs / 20)))
        if zs < 30 or cell not in lay["carrier"]:
            continue
        # the clip plate's body (a square turned to the diagonal) stays within the panel's part
        if not p.station_ok(xs - 15, xs + 15, zs - 15, zs + 15, -2.0, 6.0):
            continue
        q = np.array([xs, zs]) - 20 * p.nu
        pt = p.world(q[0], 0.0, q[1])
        assert np.linalg.norm(np.cross(pt - L.p, L.d)) < 1e-6, "diag clip off its line"
        out.append(((xs, zs), pt))
    return out


def _clash(part_a: str, Ma, part_b: str, Mb) -> bool:
    return bool(_engine().collide.collide_pair(canon(part_a), np.asarray(Ma, float),
                                                  canon(part_b), np.asarray(Mb, float)))


def _grid_clip_M(p: Panel, i: int) -> np.ndarray:
    return p.M @ _M(np.eye(3), (20 * i + 10, -2.0, 30.0))


def _grid_cols(p: Panel, partners: list, avoid=(), ok=None, commit=None) -> list:
    """For each partner clip [(point on the panel's grid hinge, world M of its clip plate)], a
    column for the panel's own clip (a 1 x 1 clip plate on the carrier's first row) at least 8
    and at most 64 LDU from it along the hinge, the nearest that clears it: [(column, partner
    point, own clip point)]."""
    lay = p.layout()
    inv = np.linalg.inv(p.M)
    used, out = set(), []
    for pt, Mpart in partners:
        xl = (inv @ np.append(pt, 1.0))[0]
        best = None
        for i in range(-40, 40):
            if {i - 1, i, i + 1} & used:
                continue
            x = 20 * i + 10
            dx = abs(x - xl)
            if not 8 <= dx <= 64:
                continue
            if (i, 1) not in lay["carrier"]:
                continue
            if not p.station_ok(20 * i, 20 * i + 20, 20.0, 40.0, -2.0, 6.0):
                continue
            Mi = _grid_clip_M(p, i)
            if _clash(CLIP1, Mi, CLIP1, Mpart) or any(_clash(CLIP1, Mi, q, Mq) for q, Mq in avoid):
                continue
            if ok is not None and not ok(pt, p.world(20 * i + 10, 0.0, 10.0)):
                continue
            if best is None or dx < best[0]:
                best = (dx, i)
        if best is None:
            continue
        i = best[1]
        used.add(i)
        avoid = list(avoid) + [(CLIP1, _grid_clip_M(p, i))]
        out.append((i, pt, p.world(20 * i + 10, 0.0, 10.0)))
        if commit is not None:
            commit(pt, p.world(20 * i + 10, 0.0, 10.0))
    return out


def _diag_clip_M(p: Panel, stud) -> np.ndarray:
    xs, zs = stud
    ex = np.array([p.u[0], 0, p.u[1]])
    if np.dot(np.cross(ex, (0, 1, 0))[[0, 2]], p.nu) < 0:
        ex = -ex
    return p.M @ _M(orient(ex, (0, 1, 0)), (xs, -2.0, zs))


def pairings() -> list:
    """The hinge lines and how they are held: [(line, kind, first, second)] with kind
    "fixed-grid" (clips on the hull's frame + a panel's grid clips), "diag-grid" (one panel's
    diagonal clips + the other's grid clips) or "fixed-diag"."""
    out = []
    if UPPER == "crease":
        out += [("chine_up", "fixed-grid", "chine_up", "A"), ("AB", "diag-grid", "A", "E"),
                ("ridge", "fixed-diag", "ridge", "E")]
    else:
        out += [("ridge", "fixed-grid", "ridge", "E")]
    if LOWER == "seam":
        out += [("chine_lo", "fixed-grid", "chine_lo", "c"), ("CD", "diag-grid", "c", "C"),
                ("keel", "fixed-diag", "keel", "C")]
    else:
        out += [("keel", "fixed-grid", "keel", "C")]
    return out


def bow_cut(name: str) -> dict:
    """The bow's part of a facet: forward of the station's joint line (and C under the side
    keels)."""
    cut = dict(x_max=XS)
    if STATION_JOINT:
        cut["joint"] = ("fore", XS)
    if name == "C" and LOWER == "seam":
        cut["y_min"] = 9.0
    return cut


@lru_cache(maxsize=None)
def plan(side: int) -> dict:
    """The bow's panels on one side, the clips on every hinge line and the bars through them."""
    P = {f: Panel(f, side, bow_cut(f)) for f in FACETS}
    fixed = {"chine_up": chine_clips(side, "up") if UPPER == "crease" else [],
             "chine_lo": [],
             "ridge": spine_clips(side, "up"), "keel": spine_clips(side, "lo")}
    return pair_up(side, P, fixed)


def pair_up(side: int, P: dict, fixed: dict) -> dict:
    """Pair clips into hinges: each pair of clips (one each side of a hinge line) shares a bar;
    the clips must clear each other and the panel's other clips, the bars each other. `P`:
    {facet: Panel}, `fixed`: {line: the frame's clips [(parts, point, ...)]}."""
    g = geometry()
    lines = {k: (g[k] if side < 0 else g[k].mirror())
             for k in ("chine_up", "chine_lo", "ridge", "keel", "AB", "CD") if k in g}
    bars = {"main": [], **{f: [] for f in P}}   # bars held first by the frame, by a panel
    grid = {f: [] for f in P}
    diag = {f: [] for f in P}
    used_fixed = {k: [] for k in fixed}
    own = {f: [] for f in P}                    # each panel's clip plates placed (part, world M)
    spans = {k: [] for k in lines}              # each line's bars (axial intervals)

    def bar_ok(line):
        def ok(a, b):
            L = lines[line]
            ta, tb = _axial(L, a), _axial(L, b)
            lo, hi = min(ta, tb) - 8, max(ta, tb) + 8
            if hi - lo > max(BARS):
                return False
            n = next(n for n in sorted(BARS) if n >= hi - lo)       # the bar it would take
            mid = (ta + tb) / 2
            lo, hi = mid - n / 2, mid + n / 2
            return all(hi < s0 - 1 or lo > s1 + 1 for s0, s1 in spans[line])
        return ok

    def add_bar(line, a, b, who):
        L = lines[line]
        ta, tb = _axial(L, a), _axial(L, b)
        part = _bar(L, a, b)
        n = next(n for n, q in BARS.items() if q == part[0])
        mid = (ta + tb) / 2
        spans[line].append((mid - n / 2, mid + n / 2))
        bars[who].append(part)

    for line, kind, first, second in pairings():
        if kind != "diag-grid" and (first not in fixed or second not in P):
            continue
        if kind == "diag-grid" and (first not in P or second not in P):
            continue
        if kind == "fixed-grid":           # the frame's clips and a panel's grid clips
            f = second
            pts = [(q[1], q[0][-1][2]) for q in fixed[line]]
            for i, partner, own_pt in _grid_cols(P[f], pts, own[f], bar_ok(line),
                                                 lambda a, b, l=line: add_bar(l, a, b, "main")):
                grid[f].append(i)
                own[f].append((CLIP1, _grid_clip_M(P[f], i)))
                used_fixed[line].append(next(k for k, q in enumerate(fixed[line])
                                             if np.allclose(q[1], partner)))
        elif kind == "diag-grid":          # the diagonal panel goes on first: it carries the bars
            fd, fg = first, second
            cands = [(st, pt) for st, pt in _diag_clips(P[fd], lines[line])
                     if not any(_clash(CLIP1, _diag_clip_M(P[fd], st), q, Mq) for q, Mq in own[fd])]
            for i, partner, own_pt in _grid_cols(P[fg], [(pt, _diag_clip_M(P[fd], st))
                                                         for st, pt in cands], own[fg],
                                                 bar_ok(line),
                                                 lambda a, b, l=line, w=fd: add_bar(l, a, b, w)):
                stud = next(st for st, pt in cands if np.allclose(pt, partner))
                diag[fd].append(stud)
                own[fd].append((CLIP1, _diag_clip_M(P[fd], stud)))
                grid[fg].append(i)
                own[fg].append((CLIP1, _grid_clip_M(P[fg], i)))
        else:                              # the frame's clips and a panel's diagonal clips
            f = second
            cands = _diag_clips(P[f], lines[line])
            L = lines[line]
            for k, q in enumerate(fixed[line]):
                pt = q[1]
                best = None
                Mpart = q[0][-1][2]
                for stud, own_pt in cands:
                    dx = abs(_axial(L, pt) - _axial(L, own_pt))
                    if not 8 <= dx <= 64 or stud in diag[f] or (best and dx >= best[0]):
                        continue
                    Ms = _diag_clip_M(P[f], stud)
                    if _clash(CLIP1, Ms, CLIP1, Mpart) or any(_clash(CLIP1, Ms, q2, Mq)
                                                              for q2, Mq in own[f]):
                        continue
                    if not bar_ok(line)(pt, own_pt):
                        continue
                    best = (dx, stud, own_pt)
                if best:
                    diag[f].append(best[1])
                    own[f].append((CLIP1, _diag_clip_M(P[f], best[1])))
                    add_bar(line, pt, best[2], "main")
                    used_fixed[line].append(k)
    return dict(P=P, fixed=fixed, used=used_fixed, bars=bars, grid=grid, diag=diag, lines=lines)


# ------------------------------------------------------------------ the skeleton
JOIN_Y = tuple(float(y) for y in shp.JOIN_STUD_Y["bow"])     # -142 .. 58
TECHNIC = "6541"                        # Technic brick 1 x 1: the hull's side studs go in its hole
I_STATION = int(math.floor((XS - 20) / S))      # -41: the spine's first column (x -820..-800)
I_NOSE = -58                                     # its last (x -1160..-1140)
FLANGE_TIP = -1180.0
FLANGE_HW = 180.0                                # the side keels' half-width at the station
FLANGE_K = 3                                     # ... narrowing 1:3 (wedge plates 2 x 3)


def flange_edge(x: float) -> float:
    """|z| of the side keels' edge: FLANGE_HW at the station, narrowing 1:FLANGE_K."""
    return FLANGE_HW - (XS - x) / FLANGE_K


def _surf_y(p: Panel, x: float, z: float, off: float = -26.0) -> float:
    """y of a panel's outer surface (local y = off) over world (x, z)."""
    R, O = p.R, p.O
    A = np.array([[R[0, 0], R[0, 2]], [R[2, 0], R[2, 2]]])
    lx, lz = np.linalg.solve(A, np.array([x, z]) - O[[0, 2]] - R[[0, 2], 1] * off)
    return float(p.world(lx, off, lz)[1])


def blade(x: float) -> float:
    """The saw keel's blade under the spine: its underside, from the hull's saw keel at the
    station rising to the side keels at the ram."""
    return 16.0 + max(0.0, BLADE_SLOPE * (x - BLADE_TIP))


BLADE_SLOPE, BLADE_TIP = 0.35, -1060.0


@lru_cache(maxsize=None)
def spine_plan() -> dict:
    """The spine's columns: top y (under the ridge's curved slopes) and bottom y (the keel
    blade's underside), the join's Technic bricks and the side-stud bricks' cells (reserved)."""
    E, C = Panel("E", -1), Panel("C", -1)
    top, bot = {}, {}
    if SPINE_PROFILE is not None:
        top, bot = SPINE_PROFILE()
    # the ridge: curved slopes 2 x 2 in pairs of columns, the fore column a plate lower; the aft
    # column's top 6 under E's outer surface beside it (its curve then rises 2 over it)
    i = I_STATION
    while i - 1 >= I_NOSE and SPINE_PROFILE is None:
        a, f = i, i - 1
        xa = S * a + S / 2
        ya = 8 * round((_surf_y(E, xa, -22.0) + 6) / 8)
        top[a], top[f] = ya, ya + 8
        i -= 2
    for i in range(I_NOSE, I_STATION + 1) if SPINE_PROFILE is None else ():
        xc = S * i + S / 2
        bot[i] = 8 * round(max(_surf_y(C, xc, -22.0) + 12, blade(xc)) / 8)
    technic = {(I_STATION, int((y - 10) // 8) + d) for y in JOIN_Y for d in range(3)}
    if DETAILS["ram"]:
        technic |= {(I_NOSE, int((RAM_Y - 10) // 8) + d) for d in range(3)}    # the ram's brick
    technic |= set(SPINE_SKIP)
    side = {}
    for which in ("up", "lo"):
        for parts, pt, (col, ytop) in spine_clips(-1, which):
            side.setdefault(which, []).append((col, ytop))
    return dict(top=top, bot=bot, technic=technic, side=side)


def spine_cells(used_side) -> dict:
    """(column, layer n: y in [8n, 8n + 8]) -> filled by packing, for the spine's 2-wide wall,
    leaving the flange's two layers (n = -1, 0), the join's Technic bricks and the side-stud
    bricks."""
    sp = spine_plan()
    cells = set()
    for i in range(I_NOSE, I_STATION + 1):
        n0, n1 = int(sp["top"][i] // 8), int(sp["bot"][i] // 8)
        covered = S * i >= min(FLANGE_TIP, FLANGE_STRIP_TO or FLANGE_TIP) - 0.5   # side keels
        for n in range(n0, n1):
            if n in (-1, 0) and covered:
                continue
            if (i, n) in sp["technic"]:
                continue
            cells.add((i, n))
    for col, ytop in used_side:
        for n in range(int(ytop // 8), int(ytop // 8) + 3):
            cells.discard((col, n))
    return cells


def pack_wall(cells: set) -> list:
    """Pack a 2-wide wall's cells (column, layer) into bricks (three layers) and plates, bonded:
    [(part, R, (x centre, y top))] (2 studs across z)."""
    out = []
    left = set(cells)
    layers = sorted({n for _, n in left}, reverse=True)       # bottom (largest y) first
    # bricks where three layers run together; joints offset course by course
    course = 0
    for n in layers:
        trio = {i for i, m in left if m == n and (i, n - 1) in left and (i, n - 2) in left}
        if not trio:
            continue
        runs, cur = [], []
        for i in sorted(trio):
            if cur and i != cur[-1] + 1:
                runs.append(cur)
                cur = []
            cur.append(i)
        if cur:
            runs.append(cur)
        for r in runs:
            pieces = _split(len(r), (8, 6, 4, 3, 2), course % 2)
            i0 = r[0]
            for ln in pieces:
                part, R = rect_part(BRICK, ln, 2)
                out.append((part, R, (S * i0 + S * ln / 2, 8.0 * (n - 2))))
                for i in range(i0, i0 + ln):
                    for m in (n, n - 1, n - 2):
                        left.discard((i, m))
                i0 += ln
        course += 1
    # plates for what is left, layer by layer
    for k, n in enumerate(sorted({n for _, n in left}, reverse=True)):
        row = sorted(i for i, m in left if m == n)
        runs, cur = [], []
        for i in row:
            if cur and i != cur[-1] + 1:
                runs.append(cur)
                cur = []
            cur.append(i)
        if cur:
            runs.append(cur)
        for r in runs:
            i0 = r[0]
            for ln in _split(len(r), (12, 10, 8, 6, 4, 3, 2), k % 2):
                part, R = rect_part(PLATE, ln, 2)
                out.append((part, R, (S * i0 + S * ln / 2, 8.0 * n)))
                i0 += ln
    return out


def _split(n: int, sizes, odd: int) -> list:
    """Lengths (from `sizes`, 1 allowed only as a last resort) summing to n, the first one
    shorter on odd courses so joints don't line up."""
    if n == 1:
        return [1]
    out = []
    if odd and n > 3:
        first = next((s for s in sizes if s <= n - 2 and s < n // 2 + 1 and s >= 2), None)
        if first:
            out.append(first)
            n -= first
    while n > 0:
        s = next((s for s in sizes if s <= n and (n - s) != 1), None)
        if s is None:
            s = 1
        out.append(s)
        n -= s
    return out


@lru_cache(maxsize=None)
def flange_layout() -> dict:
    """The side keels forward of the station: two layers of plates, wedge plates along the upper
    one's edge (1:FLANGE_K), their triangles overhanging the lower one."""
    i_tip = int(math.floor(FLANGE_TIP / S))
    wedges, top, bot = [], set(), set()
    for m in range(0, 20):
        x1 = XS - 20 * FLANGE_K * m
        x0 = x1 - 20 * FLANGE_K
        if x0 < FLANGE_TIP - 0.5:
            break
        for side in (-1, 1):
            wedges.append(dict(x0=x0, x1=x1, side=side, z_full=(FLANGE_HW - 20 * (m + 2)),
                               z_tri=(FLANGE_HW - 20 * (m + 1))))
    wcells = {(int(w["x0"] // S) + a, (int(w["z_full"] // S) + b) if w["side"] > 0
               else (-int(w["z_full"] // S) - 1 - b))
              for w in wedges for a in range(FLANGE_K) for b in range(2)}
    full_rows = {(int(w["x0"] // S) + a, (int(w["z_full"] // S)) if w["side"] > 0
                  else (-int(w["z_full"] // S) - 1)) for w in wedges for a in range(FLANGE_K)}
    for i in range(i_tip, int(XS // S)):
        x0 = S * i
        e = flange_edge(x0)
        for k in range(-12, 12):
            z0, z1 = S * k, S * k + S
            if max(abs(z0), abs(z1)) <= e + 0.01 and (i, k) not in wcells:
                top.add((i, k))
    if FLANGE_STRIP_TO is not None:             # a strip two studs wide on along the spine
        for i in range(int(math.floor(FLANGE_STRIP_TO / S)), i_tip):
            top |= {(i, -1), (i, 0)}
    bot = top | full_rows               # under the edge's wedges only their triangles overhang
    return dict(wedges=wedges, top=top, bot=bot)


def flange_wedge(w) -> tuple:
    """(part, M) of a side keel's edge wedge (43722/43723), its wide end aft."""
    s = w["side"]
    xc = (w["x0"] + w["x1"]) / 2
    zc = s * (w["z_full"] + 20)                 # between the full row and the triangle row
    full_pt = (xc, zc - s * 10)
    wide_pt = (w["x1"] - 5, zc + s * 7)
    narrow_pt = (w["x0"] + 5, zc + s * 16)
    for part in WEDGES[FLANGE_K]:
        poly0 = top_outline(part)
        for deg in (90, -90):
            R = Ry(deg)
            poly = np.array([(R @ np.array([q[0], 0, q[1]]))[[0, 2]] for q in poly0]) + (xc, zc)
            if inside(poly, full_pt) and inside(poly, wide_pt) and not inside(poly, narrow_pt):
                return part, _M(R, (xc, -8.0, zc))
    raise AssertionError(f"no flange wedge for {w}")


def _grid_rects(cells, sizes, layer_y, role, cat, along: str, shift: int = 0) -> list:
    out = []
    srt = sorted(cells, key=(lambda c: (c[1], c[0])) if along == "x" else (lambda c: (c[0], c[1])))
    free = set(cells)
    if shift and srt:
        srt = srt[shift % len(srt):] + srt[:shift % len(srt)]
    cand = set()
    for a, b in sizes:
        cand |= {(a, b), (b, a)}
    cand = sorted(cand, key=lambda q: (-q[0] * q[1], -(q[0] if along == "x" else q[1])))
    for c in srt:
        if c not in free:
            continue
        for w, d in cand:
            done = False
            for oa in range(w):
                for ob in range(d):
                    i0, k0 = c[0] - oa, c[1] - ob
                    box = {(i0 + a, k0 + b) for a in range(w) for b in range(d)}
                    if box <= free:
                        free -= box
                        part, R = rect_part(PLATE, w, d)
                        out.append((part, role, _M(R, (S * i0 + S * w / 2, layer_y,
                                                        S * k0 + S * d / 2)), cat, None))
                        done = True
                        break
                if done:
                    break
            if done:
                break
    return out


def skeleton(used_side, top_clip_studs) -> list:
    """The spine, the Technic join at the station, the side keels: [(part, role, M, cat, insert)]
    in building order (bottom up)."""
    sp = spine_plan()
    items = []
    # the join: Technic bricks 1 x 1, their holes along X on the hull's side studs
    for y in JOIN_Y:
        for z in (-10.0, 10.0):
            items.append((TECHNIC, CORE, _M(rot(y=90), (XS - 10, y - 10, z)), "spine", None))
    # side-stud bricks for the ridge's and keel's clips (a pair back to back)
    for col, ytop in used_side:
        x = S * col + S / 2
        items.append(("87087", CORE, _M(np.eye(3), (x, ytop, -10.0)), "spine", None))
        items.append(("87087", CORE, _M(rot(y=180), (x, ytop, 10.0)), "spine", None))
    # the ram's footing: a brick with two side studs in the spine's nose, its studs forward
    if DETAILS["ram"]:
        items.append(("11211", CORE, _M(orient((0, 0, -1), (0, 1, 0), (1, 0, 0)),
                                        (S * I_NOSE + S / 2, RAM_Y - 10, 0.0)), "spine", None))
    items += [(part, role, M, "spine", None) for part, role, M in EXTRA_WALL]
    for part, R, (x, ytop) in pack_wall(spine_cells(used_side)):
        items.append((part, CORE, _M(R, (x, ytop, 0.0)), "spine", None))
    fl = flange_layout()
    wed = [(*flange_wedge(w), ) for w in fl["wedges"]]
    sizes = [s for s in PLATE if s[1] <= 12]
    # under each edge wedge a 2 x 3 plate across its full row and the row inside it
    seeds, seeded = [], set()
    for w in fl["wedges"]:
        i0 = int(w["x0"] // S)
        k_full = int(w["z_full"] // S) if w["side"] > 0 else -int(w["z_full"] // S) - 1
        k_in = k_full - w["side"]
        box = {(i0 + a, k) for a in range(FLANGE_K) for k in (k_full, k_in)}
        if box <= fl["bot"] and not box & seeded:
            seeded |= box
            part, R = rect_part(PLATE, FLANGE_K, 2)
            seeds.append((part, ROLE, _M(R, (w["x0"] + 10 * FLANGE_K, 0.0,
                                                S * min(k_full, k_in) + S)),
                          "spine", None))
    best = None
    for shift in range(0, 60, 3):          # the two layers bonded into one piece
        lay = (seeds + _grid_rects(fl["bot"] - seeded, sizes, 0.0, ROLE, "spine", "z", shift)
               + _grid_rects(fl["top"], sizes, -8.0, ROLE, "spine", "x", shift // 3)
               + [(part, ROLE, M, "spine", None) for part, M in wed])
        n = len(components([(q[0], q[2]) for q in lay]))
        if best is None or n < best[0]:
            best = (n, lay)
        if n == 1:
            break
    items += best[1]
    # building order: the side keels (lying on the table), the spine over them bottom up, the
    # spine under them top down (each part pushed up under the one over it)
    def box(it):
        lo, hi = _engine().geom.mesh(canon(it[0])).bbox
        c = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1])
                      for z in (lo[2], hi[2])]) @ it[2][:3, :3].T + it[2][:3, 3]
        return c[:, 1].min(), c[:, 1].max()
    flange, upper, lower = [], [], []
    for it in items:
        y = it[2][1, 3]                      # a part's top face
        if abs(y + 8) < 0.5 or abs(y) < 0.5:
            flange.append(it)
        elif y < -8:
            upper.append(it)
        else:
            lower.append((it[0], it[1], it[2], it[3], (0, 1, 0)))
    flange.sort(key=lambda it: -it[2][1, 3])
    upper.sort(key=lambda it: (-box(it)[1], it[2][0, 3]))
    lower.sort(key=lambda it: (it[2][1, 3], it[2][0, 3]))
    return flange + upper + lower


def _stud_cells(items, y_top: float) -> set:
    """Cells (i, k) of the studs on top of parts whose top is at y_top."""
    out = set()
    for part, role, M, *_ in items:
        if abs(M[1, 3] - y_top) > 0.01:
            continue
        for sx, sz in studs_of(canon(part)):
            q = M[:3, :3] @ np.array([sx, 0.0, sz]) + M[:3, 3]
            out.add((int(math.floor(q[0] / S)), int(math.floor(q[2] / S))))
    return out


def flange_tiles(items, keep_bare: set) -> list:
    cells = _stud_cells([it for it in items if it[0] != TECHNIC], -8.0)
    cells = {c for c in cells if c not in keep_bare}
    out = []
    for i0, i1, k0, k1 in pack(cells, [(1, 1), (1, 2), (1, 3), (1, 4), (1, 6), (1, 8), (2, 2),
                                       (2, 4)]):
        part, R = rect_part(TILE, i1 - i0 + 1, k1 - k0 + 1)
        out.append((part, ROLE, _M(R, (S * (i0 + i1 + 1) / 2, -16.0, S * (k0 + k1 + 1) / 2)),
                    "tiles", None))
    return out


SPINE_EVERY = 2          # a dorsal spine on every second pair of the ridge's columns


RIDGE_WIDE = True        # the ridge's cap four studs wide, over the E panels' edges


def ridge_cap() -> list:
    """The ridge over the spine: curved slopes 2 x 2 down to the ram, a pair of columns each,
    and on every SPINE_EVERY-th pair a dorsal spine instead, as the hull's crest's (a plate
    levelling the fore column, a jumper on each column, a 45 degree slope 2 x 1 facing the bow
    on them and a cheese slope on its back), continuing the crest's rhythm down to the ram.
    With RIDGE_WIDE each pair stands on a plate four studs wide (on a riser where the E
    panels' faces beside the spine are too high for it), its edges over the panels' edges."""
    sp = spine_plan()
    E = Panel("E", -1)
    out = []
    down = orient((0.0, 0.0, -1.0), (0.0, 1.0, 0.0), (1.0, 0.0, 0.0))     # slopes down to -X
    for n, a in enumerate(range(I_STATION, I_NOSE, -2)):
        f = a - 1
        xa, xf = S * a + S / 2, S * f + S / 2
        if RIDGE_WIDE:
            ya = sp["top"][a]
            xm = S * a
            out.append(("3023", ROLE, _M(rot(y=90), (xf, sp["top"][f] - 8, 0.0)), "ridge", None))
            yb = ya                                     # the wide plate's underside
            if any(_surf_y(E, x, -26.0) < yb + 0.5 for x in (xa - 10, xa + 10, xf - 10, xf + 10)):
                out.append(("3022", ROLE, _M(np.eye(3), (xm, ya - 8, 0.0)), "ridge", None))
                yb = ya - 8
            out.append(("3020", ROLE, _M(rot(y=90), (xm, yb - 8, 0.0)), "ridge", None))
            yt = yb - 8                                 # its top
            if n % SPINE_EVERY == 1:
                for x in (xa, xf):
                    out.append(("15573", SPINE, _M(rot(y=90), (x, yt - 8, 0.0)), "ridge", None))
                out.append(("3040", SPINE, _M(down, (xa, yt - 32, 0.0)), "ridge", None))
                out.append(("54200", SPINE, _M(_R_up(1), (xa, yt - 32, 0.0)), "ridge", None))
                for z in (-30.0, 30.0):
                    out.append(("3069b", ROLE, _M(np.eye(3), (xm, yt - 8, z)), "ridge", None))
            else:
                for z in (-20.0, 20.0):
                    out.append(("15068", ROLE, _M(rot(y=90), (xm, yt, z)), "ridge", None))
            continue
        if n % SPINE_EVERY == 1:
            yt = sp["top"][a]
            out.append(("3023", ROLE, _M(rot(y=90), (xf, sp["top"][f] - 8, 0.0)), "ridge", None))
            for x in (xa, xf):
                out.append(("15573", SPINE, _M(rot(y=90), (x, yt - 8, 0.0)), "ridge", None))
            out.append(("3040", SPINE, _M(down, (xa, yt - 32, 0.0)), "ridge", None))
            out.append(("54200", SPINE, _M(_R_up(1), (xa, yt - 32, 0.0)), "ridge", None))
        else:
            out.append(("15068", ROLE, _M(rot(y=90), (S * f + S, sp["top"][f], 0.0)), "ridge",
                        None))
    return out


def _R_up(sx: int) -> np.ndarray:
    """A slope rising toward +X (sx = 1) or -X: its high side (local +Z) that way."""
    ez = np.array([sx, 0.0, 0.0])
    ey = np.array([0.0, 1.0, 0.0])
    return orient(np.cross(ey, ez), ey, ez)


TOOTH_EVERY = 3          # a saw tooth under every third column of the keel's blade


def keel_teeth() -> list:
    """The saw keel: plates with a vertical tooth (15070) hanging under the blade, each tooth
    on its fore side (the blade steps up toward the bow, so it clears it)."""
    sp = spine_plan()
    out = []
    for i in range(I_STATION - 1, I_NOSE - 1, -TOOTH_EVERY):
        for z in (-10.0, 10.0):
            out.append(("15070", SPINE, _M(rot(y=90), (S * i + S / 2, sp["bot"][i], z)),
                        "teeth", (0, 1, 0)))
    return out


def flange_teeth(items) -> tuple:
    """Teeth along the side keels' edges (49668), as the hull's: a plate with a tooth on the
    side keels' top, on the outermost stud of each edge wedge (at its narrow, fore end), the tooth
    pointing straight out. Returns (parts, their cells)."""
    fl = flange_layout()
    out, cells = [], set()
    for w in fl["wedges"]:
        sd = w["side"]
        x = w["x0"] + 10                     # the wedge's narrow end: its full row's last stud
        z = sd * (w["z_full"] + 10)
        R = np.eye(3) if sd < 0 else rot(y=180)          # the tooth straight out
        out.append(("49668", SPINE, _M(R, (x, -16.0, z)), "teeth", (0, -1, 0)))
        cells.add((int(math.floor(x / S)), int(math.floor(z / S))))
    return out, cells


RAM_Y = -30.0            # the ram's axis: just over the side keels' tiles


def ram() -> list:
    """The ram, out of the spine's nose along -X: a jumper plate on the footing's two side
    studs, two round bricks, a bar 6L with its stop ring near the point, a cone on its end."""
    x = S * I_NOSE                            # the spine's nose face
    R = orient((0, 0, 1), (1, 0, 0), (0, 1, 0))          # local +y (into a part) -> +X
    Rf = orient((0, 0, -1), (-1, 0, 0), (0, 1, 0))       # the bar: its long end aft
    ins = (-1, 0, 0)
    out = [("15573", ROLE, _M(R, (x - 8, RAM_Y, 0.0)), "ram", ins),
           ("3062b", ROLE, _M(R, (x - 32, RAM_Y, 0.0)), "ram", ins),
           ("3062b", ROLE, _M(R, (x - 56, RAM_Y, 0.0)), "ram", ins)]
    end = x - 60 + 8                          # the bar's long end, 8 into the round brick
    out.append(("63965", ROLE, _M(Rf, (end - 102.5, RAM_Y, 0.0)), "ram", ins))
    tip = end - 102.5 - 18                    # its short end, the cone over it to the ring
    out.append(("59900", ROLE, _M(R, (tip, RAM_Y, 0.0)), "ram", ins))
    return out


def _to_local(M_panel, items) -> list:
    inv = np.linalg.inv(M_panel)
    return [(p, r, inv @ M, c, i) for p, r, M, c, i in items]


def build_bow(model, parent):
    """Build the bow as one sub-assembly in the hull frame and place it in `parent`, pushed on
    from the bow (along +X). Returns the sub-assembly."""
    bow = build_cone(model)
    parent.step("The bow, pushed onto the hull's station studs")
    parent.use(bow, (0, 0, 0), tag="bow", insert=(-1, 0, 0))
    return bow


def build_cone(model):
    """The cone (spine, side keels, panels) as one sub-assembly in the hull frame, not placed.
    (With FRAME set, everything goes in turned by it: the tail's stock is this cone, built as if
    it were a bow and turned to point aft.)"""
    F = np.eye(4) if FRAME is None else np.asarray(FRAME, float)

    def put(items):
        return [(p, r, F @ np.asarray(M, float), c,
                 None if i is None else tuple(np.round(F[:3, :3] @ np.asarray(i, float), 6)))
                for p, r, M, c, i in items]

    bow = model.submodel(PREFIX, TITLE)
    plans = {s: plan(s) for s in (-1, 1)}
    used_side = set()
    for s in (-1, 1):
        for line in ("ridge", "keel"):
            for k in plans[s]["used"][line]:
                used_side.add(plans[s]["fixed"][line][k][2])
    items = skeleton(sorted(used_side), [])
    # under a side stud low over the side keels the tiles go on early, before the wall it
    # stands in (they could not go in past it)
    low = set()
    for col, ytop in used_side:
        if ytop + 10 > -44:
            low |= {(col, -2), (col, 1)}
    n_fl = next((k for k, it in enumerate(items)
                 if not (abs(it[2][1, 3] + 8) < 0.5 or abs(it[2][1, 3]) < 0.5)), len(items))
    studs = _stud_cells([it for it in items if it[0] != TECHNIC], -8.0)
    early = [("3070b", ROLE, _M(np.eye(3), (S * i + S / 2, -16.0, S * k + S / 2)), "tiles", None)
             for i, k in sorted(low & studs)]
    emit(bow, put(items[:n_fl] + early + items[n_fl:]), per_step=8, caption=JOIN_CAPTION)
    bare = set()
    for s in (-1, 1):
        for k in plans[s]["used"]["chine_up"]:
            parts = plans[s]["fixed"]["chine_up"][k][0]
            x, z = parts[0][2][0, 3], parts[0][2][2, 3]
            bare.add((int(math.floor(x / S)), int(math.floor(z / S))))
    for i in range(I_NOSE, I_STATION + 1):
        bare |= {(i, -1), (i, 0)}             # the spine stands on the side keels here
    bare |= {(int(math.floor(t[2][0, 3] / S)), int(math.floor(t[2][2, 3] / S))) for t in early}
    fteeth, fcells = flange_teeth(items) if DETAILS["flange_teeth"] else ([], set())
    bare |= fcells
    if DETAILS["ram"]:
        bare |= {(I_NOSE - 1, -1), (I_NOSE - 1, 0)}      # under the ram's footing's studs
    emit(bow, put(flange_tiles(items, bare)), per_step=12, caption="Tiles on the side keels")
    emit(bow, put(fteeth), per_step=8, caption="Teeth along the side keels' edges")
    # the clips on the side keels and the spine
    for s in (-1, 1):
        pl = plans[s]
        for k in pl["used"]["chine_up"]:
            parts = pl["fixed"]["chine_up"][k][0]
            emit(bow, put([(p, r, M, "chine_up", None) for p, r, M in parts]), per_step=8,
                 caption="Clips on the side keels for the hull's panels")
        for line in ("ridge", "keel"):
            for k in pl["used"][line]:
                parts = pl["fixed"][line][k][0]
                side = 1 if parts[0][2][2, 3] > 0 else -1
                emit(bow, put([(p, r, M, line, (0, 0, side)) for p, r, M in parts]),
                     caption="Clips on the spine's side studs")
    if DETAILS["ridge"]:
        emit(bow, put(ridge_cap()),
             caption="The ridge: curved slopes stepping down to the ram, spines")
    if DETAILS["keel_teeth"]:
        emit(bow, put(keel_teeth()), caption="The saw keel's teeth under its blade")
    if DETAILS["ram"]:
        emit(bow, put(ram()), caption="The ram")

    # the bars through the side keels' and the spine's clips
    for s in (-1, 1):
        bars = plans[s]["bars"]["main"]
        emit(bow, put([(p, r, M, "bars", None) for p, r, M in bars]),
             caption="Bars in the clips: the panels' hinges")
    # the panels, each built flat and clipped on: under the side keels first, then over them
    made = {}
    for name in [f for f in "cCEA" if f in FACETS] if UPPER == "rest" else \
            [f for f in "cCAE" if f in FACETS]:
        for side in (-1, 1):
            pl = plans[side]
            p = pl["P"][name]
            sname = "port" if side < 0 else "stbd"
            if FRAME is not None:              # turned: port and starboard swap
                sname = "stbd" if side < 0 else "port"
            sub = model.submodel(f"{PREFIX}_panel_{name}_{sname}",
                                 f"{TITLE}: panel {name}, {sname}")
            if name in LIP_UNDER:                  # its lip clears the panel under it
                p.lip_avoid = made.get((LIP_UNDER[name], side), [])
            elif name in LIP_OVER and LIP_OVER[name] in pl["P"]:
                prepare_lip(p, pl["P"][LIP_OVER[name]])
            items_p = panel_parts(p, pl["grid"][name], pl["diag"][name])
            made[(name, side)] = [(q[0], p.M @ q[2]) for q in items_p]
            if name in pl["bars"]:
                items_p += _to_local(p.M, [(q[0], q[1], q[2], "bars", None)
                                           for q in pl["bars"][name]])
            emit(sub, items_p, caption=f"Panel {name}: plates, wedge plates, tiles",
                 connected=True)
            bow.step(f"Clip panel {name} on" if side < 0 else "")
            use_M(bow, sub, F @ p.M, tag=f"{PREFIX}_{name}_{sname}",
                  insert=tuple(np.round(F[:3, :3] @ p.n, 6)))
    return bow
