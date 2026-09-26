"""Layout helpers for the VHS cassette: stud-grid packing of plate/tile layers (bonded to the
layer underneath), quarter-circle parts, connectivity, and build-step ordering."""
from __future__ import annotations

from collections import defaultdict

import numpy as np

from brickkit.engine import Engine
from brickkit.ldraw.matrix import rot, transform, translate
from brickkit.snaps.match import find_connections

ENG = Engine()
S = 20   # one stud in LDU

PLATE = {(1, 1): "3024", (1, 2): "3023", (1, 3): "3623", (1, 4): "3710", (1, 6): "3666",
         (1, 8): "3460", (1, 10): "4477", (1, 12): "60479", (2, 2): "3022", (2, 3): "3021",
         (2, 4): "3020", (2, 6): "3795", (2, 8): "3034", (2, 10): "3832", (2, 12): "2445",
         (2, 14): "91988", (2, 16): "4282", (4, 4): "3031", (4, 6): "3032", (4, 8): "3035",
         (4, 10): "3030", (4, 12): "3029", (6, 6): "3958", (6, 8): "3036", (6, 10): "3033",
         (6, 12): "3028", (6, 14): "3456", (6, 16): "3027", (8, 8): "41539", (8, 16): "92438"}
TILE = {(1, 1): "3070b", (1, 2): "3069b", (1, 3): "63864", (1, 4): "2431", (1, 6): "6636",
        (1, 8): "4162", (2, 2): "3068b", (2, 3): "26603", (2, 4): "87079", (2, 6): "69729"}
BRICK = {(1, 1): "3005", (1, 2): "3004", (1, 3): "3622", (1, 4): "3010", (1, 6): "3009",
         (1, 8): "3008"}
BIG_PLATES = [(8, 16), (6, 16), (6, 14), (6, 12), (8, 8), (6, 10), (6, 8), (4, 12), (4, 10),
              (4, 8), (6, 6), (4, 6), (4, 4), (2, 16), (2, 14), (2, 12), (2, 10), (2, 8), (2, 6),
              (2, 4), (2, 3), (2, 2), (1, 8), (1, 6), (1, 4), (1, 3), (1, 2), (1, 1)]
MID_PLATES = [(2, 12), (2, 10), (2, 8), (2, 6), (2, 4), (2, 3), (2, 2), (1, 8), (1, 6), (1, 4),
              (1, 3), (1, 2), (1, 1)]
TILES = [(2, 6), (2, 4), (2, 3), (2, 2), (1, 8), (1, 6), (1, 4), (1, 3), (1, 2), (1, 1)]
# 1 x N runs (plates, tiles, bricks) by length
PLATE1 = {n: PLATE[(1, n)] for n in (1, 2, 3, 4, 6, 8, 10, 12)}
PLATE2 = {n: PLATE[(2, n)] for n in (2, 3, 4, 6, 8, 10, 12, 14, 16)}
PLATE2[1] = "3023"            # a 1 x 2 plate turned across the run
TILE1 = {n: TILE[(1, n)] for n in (1, 2, 3, 4, 6, 8)}
TILE2 = {n: TILE[(2, n)] for n in (2, 3, 4, 6)}

# quarter-circle parts: arc centre in the part's own frame (any quadrant; quarter_M turns them)
ARC = {"30565": (-40, 40), "79393": (0, 0), "27507": (0, 0), "27925": (-10, 10),
       "68568": (-10, -10)}


def orient(ex, ey, ez) -> np.ndarray:
    """3x3 rotation whose columns are where the part's local X, Y and Z axes point."""
    return np.column_stack([np.asarray(v, float) for v in (ex, ey, ez)])


def canon(part: str) -> str:
    return ENG.catalog.canonical(part)


def dims(part: str) -> tuple[float, float]:
    lo, hi = ENG.geom.mesh(canon(part)).bbox
    return hi[0] - lo[0], hi[2] - lo[2]


def rect_M(table: dict, rect: tuple, y: float):
    """(part, M) for a rectangle (i0, i1, k0, k1) of stud cells with its top at y."""
    i0, i1, k0, k1 = rect
    w, d = i1 - i0 + 1, k1 - k0 + 1
    part = table[(min(w, d), max(w, d))]
    bx, bz = dims(part)
    R = np.eye(3) if abs(bx - S * w) < 1 and abs(bz - S * d) < 1 else rot(y=90)
    return part, transform((S * (i0 + i1) / 2, y, S * (k0 + k1) / 2), R)


def pack(cells, sizes, order="row", prefer="x", below=None, shift=0, uf=None) -> list[tuple]:
    """Greedy cover of stud cells by rectangles (both orientations). With `below`
    (cell -> id of the part underneath) each rectangle is chosen to join as many still
    separate groups of parts below as possible (union-find), then by area; otherwise by area.
    `shift` rotates the scan start so alternative layouts can be tried; pass the same `uf`
    dict to several calls that cover one layer so they share what is already joined.
    Returns (i0, i1, k0, k1) tuples."""
    parent = {} if uf is None else uf

    def root(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    free = set(cells)
    cand = set()
    for a, b in sizes:
        cand |= {(a, b), (b, a)}
    cand = sorted(cand, key=lambda s: (-s[0] * s[1], -(s[0] if prefer == "x" else s[1])))
    keyf = (lambda c: (c[1], c[0])) if order == "row" else (lambda c: (c[0], c[1]))
    seq = sorted(free, key=keyf)
    if shift and seq:
        seq = seq[shift % len(seq):] + seq[:shift % len(seq)]
    out = []
    for i, k in seq:
        if (i, k) not in free:
            continue
        best = None
        for w, d in cand:
            # every placement of a w x d rectangle that covers this cell (min corner first)
            offs = [(0, 0)] + ([(oa, ob) for oa in range(w) for ob in range(d)
                                if (oa, ob) != (0, 0)] if below else [])
            for oa, ob in offs:
                i0, k0 = i - oa, k - ob
                box = {(i0 + a, k0 + b) for a in range(w) for b in range(d)}
                if not box <= free:
                    continue
                groups = {root(below[x]) for x in box if x in below} if below else set()
                score = (len(groups), w * d)
                if best is None or score > best[0]:
                    best = (score, box, (i0, i0 + w - 1, k0, k0 + d - 1))
            if not below and best:
                break
        if best:
            free -= best[1]
            out.append(best[2])
            if below:
                ids = [root(below[x]) for x in best[1] if x in below]
                for a in ids[1:]:
                    parent[root(a)] = root(ids[0])
    return out


def split_line(n: int, lengths, first=0) -> list[int]:
    """n studs as runs of the given lengths: a first run of `first` when it fits, then as
    few runs as possible with no 1-stud run (a 1 x 1 at the end of a line in one layer over
    another 1 x 1 would be an island)."""
    lengths = sorted(set(lengths), reverse=True)
    best = {0: (0, 0, [])}
    for m in range(1, n + 1):
        cand = [(best[m - L][0] + (L == 1), best[m - L][1] + 1, best[m - L][2] + [L])
                for L in lengths if L <= m and m - L in best]
        if cand:
            best[m] = min(cand, key=lambda c: (c[0], c[1]))
    if first and first in lengths and n - first > 1 and n - first in best \
            and best[n - first][0] == 0:
        return [first] + sorted(best[n - first][2], reverse=True)
    return sorted(best[n][2], reverse=True)


def weave(cells, along: str, lengths=(12, 10, 8, 6, 4, 3, 2, 1), phase=0) -> list[tuple]:
    """Cover stud cells with 1 x N runs along X (rows) or Z (columns): each line's
    contiguous segments split into the given lengths. Successive lines start with a different
    first run so the joints stagger. Two layers woven crosswise (rows over columns) join
    every part to its neighbours, whatever the outline."""
    lines = defaultdict(list)
    for i, k in cells:
        lines[k if along == "x" else i].append(i if along == "x" else k)
    out = []
    for n, key in enumerate(sorted(lines)):
        vals = sorted(lines[key])
        segs, cur = [], [vals[0]]
        for v in vals[1:]:
            if v == cur[-1] + 1:
                cur.append(v)
            else:
                segs.append(cur)
                cur = [v]
        segs.append(cur)
        for seg in segs:
            first = (0, 4, 6, 3)[(n + phase) % 4]
            pos = seg[0]
            for L in split_line(len(seg), lengths, first):
                a, b = pos, pos + L - 1
                out.append((a, b, key, key) if along == "x" else (key, key, a, b))
                pos += L
    return out


def cell_ids(rects, start=0) -> dict:
    """cell -> id of the rectangle covering it (for bonding the next layer)."""
    return {(i, k): n for n, (i0, i1, k0, k1) in enumerate(rects, start)
            for i in range(i0, i1 + 1) for k in range(k0, k1 + 1)}


def runs(n: int, lengths=(8, 6, 4, 3, 2, 1), phase=0) -> list[int]:
    """Split n studs into available lengths; `phase` fixes the first run to move the joints."""
    out, left = [], n
    phase = max((L for L in lengths if L <= phase), default=0)
    if phase and n > phase:
        out.append(phase)
        left -= phase
    while left:
        L = next(L for L in lengths if L <= left)
        out.append(L)
        left -= L
    return out


def line_rects(cells: list, lengths=(8, 6, 4, 3, 2, 1), phase=0) -> list[tuple]:
    """Rectangles covering an ordered straight line of cells in runs."""
    out, pos = [], 0
    for L in runs(len(cells), lengths, phase):
        seg = cells[pos:pos + L]
        pos += L
        out.append((min(c[0] for c in seg), max(c[0] for c in seg),
                    min(c[1] for c in seg), max(c[1] for c in seg)))
    return out


def quarter_M(part: str, q: int, y: float, centre=(0, 0)):
    """Quarter-circle part with its arc centre on `centre` (x, z), turned q * 90 degrees."""
    cx, cz = ARC[part]
    return (translate(centre[0], y, centre[1]) @ transform((0, 0, 0), rot(y=90 * q))
            @ translate(-cx, 0, -cz))


def links(parts: list[tuple]) -> dict:
    """Adjacency (index -> set of indices) of stud/pin/... connections among (part, M)."""
    conns = [[c.transformed(M) for c in ENG.shadow.connectors(canon(p))] for p, M in parts]
    adj = defaultdict(set)
    for c in find_connections(conns):
        adj[c.a].add(c.b)
        adj[c.b].add(c.a)
    return adj


def n_pieces(parts: list[tuple]) -> int:
    adj = links(parts)
    seen, n = set(), 0
    for s in range(len(parts)):
        if s in seen:
            continue
        n += 1
        stack = [s]
        while stack:
            x = stack.pop()
            if x not in seen:
                seen.add(x)
                stack += list(adj[x] - seen)
    return n


class Batch:
    """Collect placements (part, colour, M, category), then emit them as build steps.

    Parts are built in phases (lists of categories). Within a phase each step takes up to
    `per_step` parts that join onto what is already built, grown outwards from the step's
    first part so every step is one local cluster. A step is captioned by the first category
    it introduces (in `captions` order); steps that only repeat known work stay uncaptioned,
    as in a printed booklet."""

    def __init__(self):
        self.items = []

    def add(self, part, color, M, cat, tag="", insert=None):
        self.items.append((canon(part), color, np.asarray(M, float), cat, tag, insert))

    def parts(self, cats=None):
        return [(p, M) for p, _, M, cat, *_ in self.items if cats is None or cat in cats]

    def phase_pieces(self, phases: list) -> int:
        """Worst piece count over the cumulative phases: 1 means every phase can be built
        onto the previous ones without leaving anything loose."""
        done, worst = set(), 0
        for cats in phases:
            done |= set(cats)
            worst = max(worst, n_pieces(self.parts(done)))
        return worst

    def emit(self, sub, phases: list, captions: dict, per_step: int = 6):
        prior = []
        for it in sub.items:            # parts already in the submodel, sub-assemblies included
            if hasattr(it, "part"):
                prior.append((it.part, it.M))
            else:
                prior += [(p, it.M @ M) for p, _, M in it.sub.flatten_local()]
        adj = links(prior + self.parts())
        n0 = len(prior)
        built = set(range(n0))
        told = set()
        pos = {j: it[2][:3, 3] for j, it in enumerate(self.items)}
        for cats in phases:
            todo = [j for j, it in enumerate(self.items) if it[3] in cats]
            # start at the back-left of the lowest layer
            todo.sort(key=lambda j: (-pos[j][1] // 8, pos[j][2] * -1, pos[j][0]))
            while todo:
                step, anchor = [], None
                while todo and len(step) < per_step:
                    ready = [j for j in todo if adj[n0 + j] & built or not built]
                    if not ready:
                        if step:
                            break
                        ready = todo[:1]
                    low = max(pos[j][1] // 8 for j in ready)      # lowest layer first
                    ready = [j for j in ready if pos[j][1] // 8 == low]
                    if anchor is None:
                        j = ready[0]
                        anchor = pos[j]
                    else:
                        j = min(ready, key=lambda j: np.linalg.norm(pos[j] - anchor))
                        if np.linalg.norm(pos[j] - anchor) > 140 and len(step) >= 2:
                            break
                    step.append(j)
                    built.add(n0 + j)
                    todo.remove(j)
                new = [c for c in captions if c not in told and
                       any(self.items[j][3] == c for j in step)]
                told.update(self.items[j][3] for j in step)
                sub.step(captions[new[0]] if new else "")
                for j in step:
                    part, color, M, cat, tag, insert = self.items[j]
                    sub.place(part, color, (0, 0, 0), tag=tag, insert=insert).M = M
        self.items = []
