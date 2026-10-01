"""Nautilus: model-local helpers. Part tables, availability per palette role, orientation of
sideways (SNOT) parts, connectivity, and a Batch that turns world placements into small
connected build steps inside a sub-assembly.

Units: LDU (stud 20, plate 8, brick 24), -Y up, bow toward -X, port side toward -Z."""
from __future__ import annotations

import math
import tomllib
from collections import defaultdict
from pathlib import Path

import numpy as np

from brickkit.engine import Engine
from brickkit.ldraw.matrix import rot
from brickkit.snaps.match import find_connections

ENG = Engine()
HERE = Path(__file__).resolve().parent
S, PL, BR = 20, 8, 24

PLATE = {(1, 1): "3024", (1, 2): "3023", (1, 3): "3623", (1, 4): "3710", (1, 6): "3666",
         (1, 8): "3460", (1, 10): "4477", (1, 12): "60479", (2, 2): "3022", (2, 3): "3021",
         (2, 4): "3020", (2, 6): "3795", (2, 8): "3034", (2, 10): "3832", (2, 12): "2445",
         (2, 14): "91988", (4, 4): "3031", (4, 6): "3032", (4, 8): "3035", (4, 10): "3030",
         (4, 12): "3029", (6, 6): "3958",
         (6, 8): "3036", (6, 10): "3033", (6, 12): "3028"}
BRICK = {(1, 1): "3005", (1, 2): "3004", (1, 3): "3622", (1, 4): "3010", (1, 6): "3009",
         (1, 8): "3008", (1, 12): "6112", (2, 2): "3003", (2, 3): "3002", (2, 4): "3001",
         (2, 6): "2456", (2, 8): "3007"}
TILE = {(1, 1): "3070b", (1, 2): "3069b", (1, 3): "63864", (1, 4): "2431", (1, 6): "6636",
        (1, 8): "4162", (2, 2): "3068b", (2, 4): "87079"}


def canon(part: str) -> str:
    return ENG.catalog.canonical(part)


# ------------------------------------------------------------------ colours and availability
def role_colours() -> dict[str, set[str]]:
    cfg = tomllib.loads((HERE / "model.toml").read_text())
    out = {r: {c} for r, c in cfg.get("palette", {}).items()}
    for v in cfg.get("variants", {}).values():
        for r, c in v.items():
            if r != "title":
                out.setdefault(r, set()).add(c)
    return out


class Avail:
    """part/role pairs that exist in every colour the role takes (>= 3 sets, in a set in 2016
    or later), so packers only use sizes that are real in every colourway."""

    def __init__(self):
        self.cols = role_colours()
        self.cache: dict = {}

    def ok(self, part: str, role: str) -> bool:
        key = (part, role)
        if key not in self.cache:
            good = True
            for c in self.cols.get(role, {role}):
                e = ENG.catalog.element(canon(part), c)
                if e is None or e.set_count < 3 or e.last_year < 2016:
                    good = False
                    break
            self.cache[key] = good
        return self.cache[key]

    def sizes(self, table: dict, role: str) -> list[tuple[int, int]]:
        return [k for k, p in table.items() if self.ok(p, role)]


AV = Avail()


# ------------------------------------------------------------------ geometry helpers
def bbox(part: str):
    return ENG.geom.mesh(canon(part)).bbox


def orient(ex, ey, ez=None) -> np.ndarray:
    """3x3 rotation whose columns are where the part's local X, Y and Z axes point."""
    ex, ey = np.asarray(ex, float), np.asarray(ey, float)
    ez = np.cross(ex, ey) if ez is None else np.asarray(ez, float)
    return np.column_stack([ex, ey, ez])


def side_R(side: int) -> np.ndarray:
    """Rotation for a sideways plate on a hull side: studs (local -Y) face outward (side -1 =
    port = -Z), local X along the hull (world X), local Z along world -Y (port) / +Y
    (starboard)."""
    return orient((1, 0, 0), (0, 0, -side))


def rect_part(table: dict, w: int, d: int):
    """(part, R) for a w (local X) by d (local Z) rectangle from a table keyed (short, long)."""
    part = table[(min(w, d), max(w, d))]
    lo, hi = bbox(part)
    along_x = abs((hi[0] - lo[0]) - S * w) < 1 and abs((hi[2] - lo[2]) - S * d) < 1
    return part, (np.eye(3) if along_x else rot(y=90))


# ------------------------------------------------------------------ connectivity
def links(parts: list[tuple]) -> dict:
    conns = [[c.transformed(M) for c in ENG.shadow.connectors(canon(p))] for p, M in parts]
    adj = defaultdict(set)
    for c in find_connections(conns):
        adj[c.a].add(c.b)
        adj[c.b].add(c.a)
    return adj


def components(parts: list[tuple]) -> list[list[int]]:
    adj = links(parts)
    seen, out = set(), []
    for s in range(len(parts)):
        if s in seen:
            continue
        comp, stack = [], [s]
        while stack:
            x = stack.pop()
            if x not in seen:
                seen.add(x)
                comp.append(x)
                stack += list(adj[x] - seen)
        out.append(comp)
    return out


class Batch:
    """Collect world placements (part, colour, M, category), then emit them into a submodel
    as build steps. `frame` is the submodel's placement in the world: parts are stored in its
    local frame. Within each phase (a list of categories) a step takes up to `per_step` parts
    that join onto what is built, grown outward from the step's first part, lowest first (in
    the submodel's own frame, so a side panel built flat goes up layer by layer)."""

    def __init__(self, frame=None):
        self.items = []
        self.lows = {}
        self.frame = np.eye(4) if frame is None else np.asarray(frame, float)
        self.inv = np.linalg.inv(self.frame)

    def add(self, part, color, M, cat="", tag="", insert=None, low=None):
        """`low`: build this part as if its lowest point were at this y (local frame)."""
        self.items.append((canon(part), color, self.inv @ np.asarray(M, float), cat, tag, insert))
        if low is not None:
            self.lows[len(self.items) - 1] = low

    def parts(self, cats=None):
        return [(p, M) for p, _, M, cat, *_ in self.items if cats is None or cat in cats]

    def emit(self, sub, phases=None, captions=None, per_step: int = 6, reach: float = 140,
             order=None, hanging=()):
        """`hanging`: categories built downward from what is already there (plates pushed up
        one under another, the highest first), not upward from the table."""
        captions = captions or {}
        if phases is None:
            phases = [sorted({it[3] for it in self.items}, key=lambda c: list(captions).index(c)
                             if c in captions else 99)]
            phases = [[c] for c in phases[0]]
        prior = []
        for it in sub.items:
            if hasattr(it, "part"):
                prior.append((it.part, it.M))
            else:
                prior += [(p, it.M @ M) for p, _, M in it.sub.flatten_local()]
        adj = links(prior + self.parts())
        n0 = len(prior)
        built = set(range(n0))
        told = set()
        pos = {j: it[2][:3, 3] for j, it in enumerate(self.items)}
        low_of, box = {}, {}
        for j, it in enumerate(self.items):
            lo, hi = bbox(it[0])
            corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1])
                                for z in (lo[2], hi[2])]) @ it[2][:3, :3].T + it[2][:3, 3]
            low_of[j] = round(self.lows.get(j, corners[:, 1].max()) / 4)   # lowest point, 4 LDU bands
            box[j] = (corners.min(0) + 0.6, corners.max(0) - 0.6)
        placed: list[int] = []

        # parts each part sits on (directly below it, overlapping its footprint)
        under = defaultdict(set)
        for j in box:
            a0, a1 = box[j]
            for k in box:
                if k == j:
                    continue
                b0, b1 = box[k]
                if a0[0] < b1[0] and b0[0] < a1[0] and a0[2] < b1[2] and b0[2] < a1[2] \
                        and abs(b0[1] - a1[1]) < 6.0 and b1[1] > a1[1]:
                    under[j].add(k)
        placed_set = set()

        def sandwiched(j):
            """Would j go in between parts already built above and below it?"""
            a0, a1 = box[j]
            above = below = False
            for k in placed:
                b0, b1 = box[k]
                if a0[0] < b1[0] and b0[0] < a1[0] and a0[2] < b1[2] and b0[2] < a1[2]:
                    if b1[1] <= a0[1] + 4.6:
                        above = True
                    elif b0[1] >= a1[1] - 4.6:
                        below = True
            return above and below
        for cats in phases:
            todo = [j for j, it in enumerate(self.items) if it[3] in cats]
            if set(cats) & set(hanging):
                self._hang(sub, todo, adj, n0, built, placed, placed_set, box, pos, captions,
                           told, per_step, reach)
                continue
            key = order or (lambda j: (-low_of[j], pos[j][0], pos[j][2]))
            todo.sort(key=key)
            phase = set(todo)
            table = max((low_of[j] for j in todo), default=0)   # parts down here lie on the table
            # parts that stand on the table, directly or through parts under them; the others
            # hang (from what is built above them) and go in afterwards, from below
            stands = {j for j in todo if low_of[j] == table}
            grew = True
            while grew:
                grew = False
                for j in todo:
                    if j not in stands and under[j] & stands:
                        stands.add(j)
                        grew = True
            # a standing part waits for the standing parts under it; a hanging part waits for
            # everything over it (it is pushed up from below once that is built)
            supports = {j: (under[j] & stands) if j in stands
                        else {k for k in phase if j in under[k]} for j in todo}
            while todo:
                step, anchor = [], None
                while todo and len(step) < per_step:
                    ready = [j for j in todo
                             if (adj[n0 + j] & built or not built or low_of[j] == table)
                             and supports[j] <= placed_set and not sandwiched(j)]
                    if not ready:     # nothing sits on finished supports: relax that rule
                        ready = [j for j in todo if (adj[n0 + j] & built or not built)
                                 and not sandwiched(j)]
                    if not ready:
                        if step:
                            break
                        ready = todo[:1]
                    low = max(low_of[j] for j in ready)
                    ready = [j for j in ready if low_of[j] == low]
                    if step and low > min(low_of[k] for k in step):
                        break       # never a lower part after a higher one in a step
                    if step and any(under[j] & set(step) for j in ready):
                        ready = [j for j in ready if not under[j] & set(step)]
                        if not ready:
                            break   # nor a part on one placed in this same step
                    if anchor is None:
                        j = ready[0]
                        anchor = pos[j]
                    else:
                        j = min(ready, key=lambda j: np.linalg.norm(pos[j] - anchor))
                        if np.linalg.norm(pos[j] - anchor) > reach and len(step) >= 2:
                            break
                    step.append(j)
                    built.add(n0 + j)
                    placed.append(j)
                    placed_set.add(j)
                    todo.remove(j)
                new = [c for c in captions if c not in told and
                       any(self.items[j][3] == c for j in step)]
                told.update(self.items[j][3] for j in step)
                sub.step(captions[new[0]] if new else "")
                for j in step:
                    part, color, M, cat, tag, insert = self.items[j]
                    p = sub.place(part, color, (0, 0, 0), tag=tag, insert=insert)
                    p.M = M
        self.items = []
        self.lows = {}

    def _hang(self, sub, todo, adj, n0, built, placed, placed_set, box, pos, captions, told,
              per_step, reach):
        """Build hanging parts top down: each step takes parts that join what is built,
        highest first, near the step's first part."""
        top_of = {j: round(box[j][0][1] / 4) for j in todo}
        todo = sorted(todo, key=lambda j: (top_of[j], pos[j][0], pos[j][2]))
        while todo:
            step, anchor = [], None
            while todo and len(step) < per_step:
                ready = [j for j in todo if adj[n0 + j] & built] or todo[:1]
                hi = min(top_of[j] for j in ready)
                ready = [j for j in ready if top_of[j] == hi]
                if step and hi < max(top_of[k] for k in step):
                    break
                if anchor is None:
                    j = ready[0]
                    anchor = pos[j]
                else:
                    j = min(ready, key=lambda j: np.linalg.norm(pos[j] - anchor))
                    if np.linalg.norm(pos[j] - anchor) > reach and len(step) >= 2:
                        break
                step.append(j)
                built.add(n0 + j)
                placed.append(j)
                placed_set.add(j)
                todo.remove(j)
            new = [c for c in captions if c not in told and
                   any(self.items[j][3] == c for j in step)]
            told.update(self.items[j][3] for j in step)
            sub.step(captions[new[0]] if new else "")
            for j in step:
                part, color, M, cat, tag, insert = self.items[j]
                p = sub.place(part, color, (0, 0, 0), tag=tag, insert=insert)
                p.M = M


def use_M(sub, child, M, tag="", insert=None):
    M = np.asarray(M, float)
    return sub.use(child, tuple(M[:3, 3]), M[:3, :3], tag=tag, insert=insert)


# ------------------------------------------------------------------ packing
def pack(cells, sizes, below=None, prefer="x", shift=0, above=None) -> list[tuple]:
    """Cover cells with rectangles (both orientations); with `below` ({cell: group}) each
    rectangle is chosen to join as many still separate groups as it can, then (with `above`,
    the cells of the layer to come) to reach under that layer, then by area.
    Returns (i0, i1, j0, j1)."""
    parent: dict = {}

    def root(a):
        parent.setdefault(a, a)
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    free = set(cells)
    cand = set()
    for a, b in sizes:
        cand |= {(a, b), (b, a)}
    cand = sorted(cand, key=lambda s: (-s[0] * s[1], -(s[0] if prefer == "x" else s[1])))
    seq = sorted(free, key=lambda c: (c[0], c[1]) if prefer == "x" else (c[1], c[0]))
    if shift and seq:
        seq = seq[shift % len(seq):] + seq[:shift % len(seq)]
    if above:       # cells nothing will cover first, while their neighbours are still free
        seq = [c for c in seq if c not in above] + [c for c in seq if c in above]
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
                    groups = {root(below[x]) for x in box if below and x in below}
                    reach = bool(above) and not box.isdisjoint(above)
                    score = (len(groups), reach, w * d, w if prefer == "x" else d)
                    if best is None or score > best[0]:
                        best = (score, box, (i0, i0 + w - 1, j0, j0 + d - 1))
        if best is None:
            raise ValueError(f"cannot cover cell {c}")
        free -= best[1]
        out.append(best[2])
        if below:
            ids = [root(below[x]) for x in best[1] if x in below]
            for a in ids[1:]:
                parent[root(a)] = root(ids[0])
    return out


def cells_of(r) -> set:
    i0, i1, j0, j1 = r
    return {(i, j) for i in range(i0, i1 + 1) for j in range(j0, j1 + 1)}


def ids_of(rects, start=0) -> dict:
    return {c: n for n, r in enumerate(rects, start) for c in cells_of(r)}


def runs(cells, lengths) -> list[tuple]:
    """1-row runs along x (i0, i1, j, j) covering cells, as few parts as possible."""
    out = []
    by_j = defaultdict(list)
    for i, j in cells:
        by_j[j].append(i)
    for j, iis in by_j.items():
        iis.sort()
        seg = [iis[0]]
        for i in iis[1:] + [None]:
            if i is not None and i == seg[-1] + 1:
                seg.append(i)
                continue
            n, pos = len(seg), seg[0]
            while n > 0:
                L = max(l for l in lengths if l <= n)
                out.append((pos, pos + L - 1, j, j))
                pos += L
                n -= L
            if i is not None:
                seg = [i]
    return out


def connected(layers: list[list]) -> int:
    """Pieces formed by stacked layers of rectangles (each joins those under it)."""
    parent = {}

    def root(a):
        parent.setdefault(a, a)
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    prev = {}
    for n, rects in enumerate(layers):
        cur = {}
        for k, r in enumerate(rects):
            root((n, k))
            for c in cells_of(r):
                cur[c] = (n, k)
                if c in prev:
                    parent[root(prev[c])] = root((n, k))
        prev = cur
    return len({root(a) for a in list(parent)})


# ------------------------------------------------------------------ placing by connectors
def about(point, R) -> np.ndarray:
    """4x4 rotation R about a line (or point) through `point`."""
    p = np.asarray(point, float)
    M = np.eye(4)
    M[:3, :3] = R
    M[:3, 3] = p - np.asarray(R, float) @ p
    return M


def connectors(part, M=None):
    cs = ENG.shadow.connectors(canon(part))
    return cs if M is None else [c.transformed(np.asarray(M, float)) for c in cs]


# ------------------------------------------------------------------ tiling exposed studs
def exposed_studs(parts, keep=None, tol=1.5):
    """Studs on top of placed parts [(part, M)] (vertical, upward) that nothing sits on: no
    anti-stud of another part at the stud and no part's box over it. `keep(x, y, z)` limits
    which to consider. Returns [(x, y, z)] (y: the top the stud stands on)."""
    holes, boxes = [], []
    for j, (part, M) in enumerate(parts):
        M = np.asarray(M, float)
        for c in connectors(part, M):
            if c.kind == "cyl" and c.gender == "F" and abs(abs(c.axis[1]) - 1) < 1e-6:
                holes.append((j, np.asarray(c.origin, float)))
        lo, hi = bbox(part)
        corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1])
                            for z in (lo[2], hi[2])]) @ M[:3, :3].T + M[:3, 3]
        boxes.append((corners.min(0) + 0.6, corners.max(0) - 0.6))
    hole_pts = np.array([h for _, h in holes]) if holes else np.zeros((0, 3))
    hole_own = np.array([j for j, _ in holes]) if holes else np.zeros(0, int)
    out = []
    for j, (part, M) in enumerate(parts):
        for c in connectors(part, np.asarray(M, float)):
            if c.kind != "cyl" or c.gender != "M" or c.axis[1] > -1 + 1e-6 or not c.secs:
                continue
            if abs(c.secs[0][1] - 6) > 0.7:
                continue
            p = np.asarray(c.origin, float)
            if any(abs((v - 10) / S - round((v - 10) / S)) > 1e-3 for v in (p[0], p[2])):
                continue                     # off the stud grid (a turned part): no tiles
            if keep is not None and not keep(*p):
                continue
            if len(hole_pts):
                d = np.linalg.norm(hole_pts - p, axis=1)
                if np.any((d < tol) & (hole_own != j)):
                    continue
            lo = p + np.array([-10.5, -10.0, -10.5])   # the tile, and a little room round it
            hi = p + np.array([10.5, -0.5, 10.5])
            if any(k != j and np.all(lo < b1) and np.all(b0 < hi) for k, (b0, b1) in
                   enumerate(boxes)):
                continue
            out.append(tuple(np.round(p, 3)))
    return sorted(set(out))


def tile_studs(sub, studs, role="hull", caption="Tiles over the bare studs", grille=None,
               sizes=((1, 1), (1, 2), (1, 4), (2, 2))):
    """Cover studs [(x, y, z)] (on the stud grid) with tiles. `grille(x, z)`: where 1 x 2
    runs along X are grille tiles instead (a grated deck)."""
    by_y = defaultdict(set)
    for x, y, z in studs:
        by_y[y].add((int(math.floor(x / S)), int(math.floor(z / S))))
    first = True
    for y, cells in sorted(by_y.items()):
        grid = {c for c in cells if grille and grille(S * c[0] + 10, S * c[1] + 10)}
        plain = cells - grid
        rects = [(r, False) for r in pack(plain, list(sizes), prefer="x")] if plain else []
        rects += [(r, True) for r in pack(grid, [(1, 1), (1, 2)], prefer="x")] if grid else []
        for (i0, i1, k0, k1), gr in rects:
            w, d = i1 - i0 + 1, k1 - k0 + 1
            if gr and w == 2 and d == 1:
                part, R = "2412b", np.eye(3)
            else:
                part, R = rect_part(TILE, w, d)
            if first:
                sub.step(caption)
                first = False
            sub.place(part, role, (S * (i0 + i1 + 1) / 2, y - 8, S * (k0 + k1 + 1) / 2), R)


def free_sockets(parts, keep=None, room=((-10.5, 0.5, -10.5), (10.5, 24.0, 10.5)), tol=1.5):
    """Anti-studs on the underside of placed parts [(part, M)] that nothing plugs into and
    with nothing in `room` (a box relative to the socket, +y down) under them, for hanging
    something there. `keep(x, y, z)` limits which to consider. Returns [(x, y, z)] (y: the
    underside)."""
    studs, boxes = [], []
    for j, (part, M) in enumerate(parts):
        M = np.asarray(M, float)
        for c in connectors(part, M):
            if c.kind == "cyl" and c.gender == "M" and abs(abs(c.axis[1]) - 1) < 1e-6:
                studs.append((j, np.asarray(c.origin, float)))
        lo, hi = bbox(part)
        corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1])
                            for z in (lo[2], hi[2])]) @ M[:3, :3].T + M[:3, 3]
        boxes.append((corners.min(0) + 0.6, corners.max(0) - 0.6))
    stud_pts = np.array([s for _, s in studs]) if studs else np.zeros((0, 3))
    stud_own = np.array([j for j, _ in studs]) if studs else np.zeros(0, int)
    r0, r1 = np.asarray(room[0], float), np.asarray(room[1], float)
    out = []
    for j, (part, M) in enumerate(parts):
        for c in connectors(part, np.asarray(M, float)):
            if c.kind != "cyl" or c.gender != "F" or c.axis[1] > -1 + 1e-6 or not c.secs:
                continue
            if abs(c.secs[0][1] - 6) > 0.7:
                continue
            p = np.asarray(c.origin, float)
            if any(abs((v - 10) / S - round((v - 10) / S)) > 1e-3 for v in (p[0], p[2])):
                continue
            if keep is not None and not keep(*p):
                continue
            if len(stud_pts):
                d = np.linalg.norm(stud_pts - p, axis=1)
                if np.any((d < tol) & (stud_own != j)):
                    continue
            lo, hi = p + r0, p + r1
            if any(k != j and np.all(lo < b1) and np.all(b0 < hi) for k, (b0, b1) in
                   enumerate(boxes)):
                continue
            out.append(tuple(np.round(p, 3)))
    return sorted(set(out))
