"""Chainsaw Face: model-local helpers. Part tables, a course packer that bonds each course to
the one below, mirrored (left/right) placement and small matrix helpers.

Units: LDU (stud 20, plate 8, brick 24), -Y up, the figure faces -Z. Cell (i, k) of a grid is
the stud square x in [ox + 20 i, ox + 20 i + 20], z in [oz + 20 k, oz + 20 k + 20]."""
from __future__ import annotations

import tomllib
from pathlib import Path

import numpy as np

from brickkit.engine import Engine
from brickkit.ldraw.matrix import rot, transform, translate

ENG = Engine()
HERE = Path(__file__).resolve().parent
S, PL, BR = 20, 8, 24

BRICK = {(1, 1): "3005", (1, 2): "3004", (1, 3): "3622", (1, 4): "3010", (1, 6): "3009",
         (1, 8): "3008", (2, 2): "3003", (2, 3): "3002", (2, 4): "3001", (2, 6): "2456",
         (2, 8): "3007"}
PLATE = {(1, 1): "3024", (1, 2): "3023", (1, 3): "3623", (1, 4): "3710", (1, 6): "3666",
         (1, 8): "3460", (1, 10): "4477", (1, 12): "60479", (2, 2): "3022", (2, 3): "3021",
         (2, 4): "3020", (2, 6): "3795", (2, 8): "3034", (2, 10): "3832", (2, 12): "2445",
         (2, 16): "4282", (4, 4): "3031", (4, 6): "3032", (4, 8): "3035", (4, 10): "3030",
         (4, 12): "3029", (6, 6): "3958", (6, 8): "3036", (6, 10): "3033", (6, 12): "3028",
         (6, 14): "3456", (6, 16): "3027", (8, 8): "41539", (8, 16): "92438"}
TILE = {(1, 1): "3070b", (1, 2): "3069b", (1, 3): "63864", (1, 4): "2431", (1, 6): "6636",
        (1, 8): "4162", (2, 2): "3068b", (2, 3): "26603", (2, 4): "87079", (2, 6): "69729"}
TABLES = {"brick": BRICK, "plate": PLATE, "tile": TILE}
HEIGHT = {"brick": BR, "plate": PL, "tile": PL}


def canon(part: str) -> str:
    return ENG.catalog.canonical(part)


# ------------------------------------------------------------------ colours and availability
def role_colours() -> dict[str, set[str]]:
    """Every colour a palette role takes in the default palette and the colourways."""
    cfg = tomllib.loads((HERE / "model.toml").read_text())
    out = {r: {c} for r, c in cfg.get("palette", {}).items()}
    for v in cfg.get("variants", {}).values():
        for r, c in v.items():
            if r != "title":
                out.setdefault(r, set()).add(c)
    return out


class Avail:
    """part/role pairs that exist in every colour the role takes (>= 3 sets, still sold in
    2016 or later), so the packer only uses sizes that are real in every colourway."""

    def __init__(self):
        self.cols = role_colours()
        self.cache: dict = {}

    def ok(self, part: str, role: str) -> bool:
        key = (part, role)
        if key not in self.cache:
            good = True
            for c in self.cols.get(role, {role}):
                e = ENG.catalog.element(part, c)
                if e is None or e.set_count < 3 or e.last_year < 2016:
                    good = False
                    break
            self.cache[key] = good
        return self.cache[key]

    def sizes(self, kind: str, role: str) -> list[tuple[int, int]]:
        return [s for s, p in TABLES[kind].items() if self.ok(p, role)]


AV = Avail()


# ------------------------------------------------------------------ geometry helpers
def bbox(part: str):
    return ENG.geom.mesh(canon(part)).bbox


MIRROR = np.diag([-1.0, 1.0, 1.0])


def mirror_R(part: str, R) -> np.ndarray:
    """Rotation that places `part` as the mirror image (x -> -x) of the part placed with R.
    LEGO parts can't be mirrored, but a part that is symmetric about one of its own planes
    (x = 0 or z = 0) can be turned to look like its mirror image."""
    R = np.eye(3) if R is None else np.asarray(R, float)
    lo, hi = bbox(part)
    if abs(lo[0] + hi[0]) < 0.6:
        own = np.diag([-1.0, 1.0, 1.0])
    elif abs(lo[2] + hi[2]) < 0.6:
        own = np.diag([1.0, 1.0, -1.0])
    else:
        raise ValueError(f"{part} has no mirror plane through its origin")
    return MIRROR @ R @ own


def orient(ex, ey, ez) -> np.ndarray:
    """3x3 rotation whose columns are where the part's local X, Y and Z axes point."""
    return np.column_stack([np.asarray(v, float) for v in (ex, ey, ez)])


def rect_part(kind: str, w: int, d: int) -> tuple[str, bool]:
    """(part, turned) for a w (x) by d (z) rectangle: turned = part's long side along z."""
    table = TABLES[kind]
    part = table[(min(w, d), max(w, d))]
    lo, hi = bbox(part)
    along_x = abs((hi[0] - lo[0]) - S * w) < 1 and abs((hi[2] - lo[2]) - S * d) < 1
    return part, not along_x


class Grid:
    def __init__(self, ox: float = 0.0, oz: float = 0.0):
        self.ox, self.oz = ox, oz

    def centre(self, i0, i1, k0, k1) -> tuple[float, float]:
        return (self.ox + S * (i0 + i1 + 1) / 2, self.oz + S * (k0 + k1 + 1) / 2)

    def cell_xz(self, i, k) -> tuple[float, float]:
        return self.ox + S * i + 10, self.oz + S * k + 10


def rects_of(cells) -> list[tuple]:
    return [(i, i, k, k) for i, k in cells]


def cells_of(rect) -> set:
    i0, i1, k0, k1 = rect
    return {(i, k) for i in range(i0, i1 + 1) for k in range(k0, k1 + 1)}


def pack(cells: dict, kind: str, below: dict | None = None, prefer: str = "x",
         max_len: int = 8, sizes: dict | None = None) -> list[tuple[str, tuple]]:
    """Cover a course's cells {(i, k): role} with rectangles of one role each. With `below`
    ({cell: id of the part under it}) each rectangle joins as many still separate groups of
    parts below as it can (union-find), then covers as much as it can. Returns
    [(role, (i0, i1, k0, k1))]."""
    parent: dict = {}

    def root(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    free = dict(cells)
    out = []
    order = sorted(free, key=(lambda c: (c[1], c[0])) if prefer == "x" else (lambda c: c))
    for c in order:
        if c not in free:
            continue
        role = free[c]
        opts = (sizes or {}).get(role) or AV.sizes(kind, role)
        cand = set()
        for a, b in opts:
            if max(a, b) <= max_len:
                cand |= {(a, b), (b, a)}
        best = None
        for w, d in cand:
            for oa in range(w):
                for ob in range(d):
                    i0, k0 = c[0] - oa, c[1] - ob
                    box = {(i0 + a, k0 + b) for a in range(w) for b in range(d)}
                    if any(free.get(x) != role for x in box):
                        continue
                    groups = {root(below[x]) for x in box if below and x in below}
                    along = w >= d if prefer == "x" else d >= w
                    score = (len(groups), w * d, along)
                    if best is None or score > best[0]:
                        best = (score, box, (i0, i0 + w - 1, k0, k0 + d - 1))
        if best is None:
            raise ValueError(f"cannot cover cell {c} ({role}) with {kind}s")
        for x in best[1]:
            del free[x]
        out.append((role, best[2]))
        if below:
            ids = [root(below[x]) for x in best[1] if x in below]
            for a in ids[1:]:
                parent[root(a)] = root(ids[0])
    return out


def ids_of(rects, start: int = 0) -> dict:
    return {x: n for n, (_, r) in enumerate(rects, start) for x in cells_of(r)}


class Seg:
    """A submodel plus a grid: places bricks/plates/tiles by cells, remembers the course
    below for bonding, and mirrors x for the right-hand side (side = -1)."""

    def __init__(self, sub, grid: Grid | None = None, side: int = 1):
        self.sub = sub
        self.g = grid or Grid()
        self.side = side
        self.below: dict = {}

    def step(self, caption: str = "", view: str | None = None):
        self.sub.step(caption, view)

    def put(self, part: str, role, pos, R=None, tag: str = "", insert=None, note: str = ""):
        x, y, z = pos
        if self.side < 0:
            R = mirror_R(part, R)
            x = -x
            if insert is not None:
                insert = (-insert[0], insert[1], insert[2])
        p = self.sub.place(part, role, (x, y, z), R, tag=tag, insert=insert, note=note)
        return p

    def put_M(self, part: str, role, M, tag: str = "", insert=None):
        M = np.asarray(M, float)
        return self.put(part, role, tuple(M[:3, 3]), M[:3, :3], tag=tag, insert=insert)

    def rect(self, kind: str, role, rect, ytop: float, R_extra=None, tag: str = ""):
        i0, i1, k0, k1 = rect
        w, d = i1 - i0 + 1, k1 - k0 + 1
        part, turned = rect_part(kind, w, d)
        x, z = self.g.centre(i0, i1, k0, k1)
        R = rot(y=90) if turned else None
        return self.put(part, role, (x, ytop, z), R, tag=tag)

    def course(self, kind: str, cells: dict, ytop: float, prefer: str = "x",
               max_len: int = 8, bond: bool = True, sizes=None) -> list:
        """Pack and place one course (top face at ytop). Returns the rectangles."""
        rects = pack(cells, kind, self.below if bond else None, prefer, max_len, sizes)
        for role, r in rects:
            self.rect(kind, role, r, ytop)
        self.below = ids_of(rects, start=len(self.sub.items) * 1000)
        return rects


def box_cells(i0, i1, k0, k1, role) -> dict:
    return {(i, k): role for i in range(i0, i1 + 1) for k in range(k0, k1 + 1)}


def Mrot(axis: str, deg: float) -> np.ndarray:
    return transform((0, 0, 0), rot(**{axis: deg}))


def about(point, R3) -> np.ndarray:
    """4x4 rotation R3 about a point."""
    P = np.asarray(point, float)
    return translate(*P) @ transform((0, 0, 0), R3) @ translate(*(-P))


# ------------------------------------------------------------------ bonded flat panels
def _connected(parts) -> bool:
    from brickkit.snaps.match import find_connections
    conns = [[c.transformed(M) for c in ENG.shadow.connectors(canon(p))] for p, _, M in parts]
    n = len(parts)
    parent = list(range(n))

    def root(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for c in find_connections(conns):
        parent[root(c.a)] = root(c.b)
    return len({root(i) for i in range(n)}) == 1


def panel_parts(g: Grid, plates: dict, tiles: dict, specials=(), y_plate=-PL, y_tile=-2 * PL,
                name: str = "panel"):
    """Lay out a flat panel (plates under tiles) so that it holds together as one piece: tries
    plate/tile directions and lengths until the tiles bridge every plate. `specials`: extra
    (part, role, M) placed as they are (round tiles, slopes). Returns [(part, role, M)]."""
    tried = []
    for pp, tp, mp, mt in (("x", "z", 8, 6), ("z", "x", 8, 6), ("x", "z", 6, 4),
                           ("z", "x", 6, 4), ("x", "z", 4, 3), ("z", "x", 4, 3),
                           ("x", "z", 12, 8), ("z", "x", 12, 8)):
        rects_p = pack(plates, "plate", None, pp, mp)
        rects_t = pack(tiles, "tile", ids_of(rects_p), tp, mt) if tiles else []
        parts = []
        for kind, rects, y in (("plate", rects_p, y_plate), ("tile", rects_t, y_tile)):
            for role, (i0, i1, k0, k1) in rects:
                part, turned = rect_part(kind, i1 - i0 + 1, k1 - k0 + 1)
                x, z = g.centre(i0, i1, k0, k1)
                parts.append((part, role, transform((x, y, z), rot(y=90) if turned else None)))
        parts += list(specials)
        if _connected(parts):
            return parts
        tried.append((pp, mp, mt))
    raise ValueError(f"{name}: no bonded panel layout (tried {tried})")


def local_M(part: str, pos, R=None, side: int = 1) -> np.ndarray:
    """4x4 placement of a part given in left-hand coordinates, mirrored for side = -1."""
    x, y, z = pos
    if side < 0:
        return transform((-x, y, z), mirror_R(part, R))
    return transform((x, y, z), R)
