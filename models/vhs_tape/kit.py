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
TILES = [(2, 6), (2, 4), (2, 3), (2, 2), (1, 8), (1, 6), (1, 4), (1, 3), (1, 2), (1, 1)]

# quarter-circle parts: arc centre in the part's own frame; natural quadrant is (+x, -z)
ARC = {"30565": (-40, 40), "79393": (0, 0), "27507": (0, 0), "27925": (-10, 10)}


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


def pack(cells, sizes, order="row", prefer="x", below=None, shift=0) -> list[tuple]:
    """Greedy cover of stud cells by rectangles (both orientations). With `below`
    (cell -> id of the part underneath) each rectangle is chosen to join as many still
    separate groups of parts below as possible (union-find), then by area; otherwise by area.
    `shift` rotates the scan start so alternative layouts can be tried.
    Returns (i0, i1, k0, k1) tuples."""
    parent = {}

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
            box = {(i + a, k + b) for a in range(w) for b in range(d)}
            if not box <= free:
                continue
            groups = {root(below[x]) for x in box if x in below} if below else set()
            score = (len(groups), w * d)
            if best is None or score > best[0]:
                best = (score, box, (i, i + w - 1, k, k + d - 1))
            if not below:
                break
        if best:
            free -= best[1]
            out.append(best[2])
            if below:
                ids = [root(below[x]) for x in best[1] if x in below]
                for a in ids[1:]:
                    parent[root(a)] = root(ids[0])
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
    """Collect placements (part, colour, M, category), then emit them as build steps: each
    part joins onto what is already built, parts of one category share a step, and the next
    part is the nearest ready one so steps stay local (good for instructions)."""

    def __init__(self):
        self.items = []

    def add(self, part, color, M, cat, tag=""):
        self.items.append((canon(part), color, np.asarray(M, float), cat, tag))

    def parts(self):
        return [(p, M) for p, _, M, _, _ in self.items]

    def emit(self, sub, captions: dict, order: list, per_step: int = 8):
        prior = [(it.part, it.M) for it in sub.items if hasattr(it, "part")]
        adj = links(prior + self.parts())
        n0 = len(prior)
        built = set(range(n0))
        rank = {c: r for r, c in enumerate(order)}
        todo = sorted(range(len(self.items)), key=lambda j: (
            rank.get(self.items[j][3], 99), -self.items[j][2][1, 3], self.items[j][2][2, 3],
            self.items[j][2][0, 3]))
        cur, count, last = None, 0, None
        while todo:
            ready = [j for j in todo if adj[n0 + j] & built or not built] or todo[:1]
            best_rank = min(rank.get(self.items[j][3], 99) for j in ready)
            same = [j for j in ready if self.items[j][3] == cur] if count < per_step else []
            pool = same or [j for j in ready if rank.get(self.items[j][3], 99) == best_rank]
            if last is not None:
                pool.sort(key=lambda j: (-self.items[j][2][1, 3] // 8,
                                         np.linalg.norm(self.items[j][2][:3, 3] - last)))
            j = pool[0]
            part, color, M, cat, tag = self.items[j]
            if cat != cur or count >= per_step:
                sub.step(captions.get(cat, ""))
                cur, count = cat, 0
            pl = sub.place(part, color, (0, 0, 0), tag=tag)
            pl.M = M
            built.add(n0 + j)
            todo.remove(j)
            count += 1
            last = M[:3, 3]
        self.items = []
