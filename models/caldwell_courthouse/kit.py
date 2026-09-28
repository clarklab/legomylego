"""Caldwell County Courthouse: model-local helpers. Part tables, availability, orientation,
course packing and a Batch that turns placements into small connected build steps.

Units: LDU (stud 20, plate 8, brick 24), -Y up, the front faces -Z. Cells are stud squares:
cell (i, k) has its centre at x = 20 i + 10, z = 20 k + 10 (the grid is centred between four
studs, so the building and its tower are symmetric about x = 0 and z = 0)."""
from __future__ import annotations

import tomllib
from collections import defaultdict
from pathlib import Path

import numpy as np

from brickkit.engine import Engine
from brickkit.ldraw.matrix import rot, transform, translate
from brickkit.snaps.match import find_connections

ENG = Engine()
HERE = Path(__file__).resolve().parent
S, PL, BR = 20, 8, 24

BRICK = {1: "3005", 2: "3004", 3: "3622", 4: "3010", 6: "3009", 8: "3008"}
PLATE1 = {1: "3024", 2: "3023", 3: "3623", 4: "3710", 6: "3666", 8: "3460", 10: "4477",
          12: "60479"}
TILE1 = {1: "3070b", 2: "3069b", 3: "63864", 4: "2431", 6: "6636", 8: "4162"}
PLATE = {(1, 1): "3024", (1, 2): "3023", (1, 3): "3623", (1, 4): "3710", (1, 6): "3666",
         (1, 8): "3460", (1, 10): "4477", (1, 12): "60479", (2, 2): "3022", (2, 3): "3021",
         (2, 4): "3020", (2, 6): "3795", (2, 8): "3034", (2, 10): "3832", (2, 12): "2445",
         (2, 14): "91988", (2, 16): "4282", (4, 4): "3031", (4, 6): "3032", (4, 8): "3035",
         (4, 10): "3030", (4, 12): "3029", (6, 6): "3958", (6, 8): "3036", (6, 10): "3033",
         (6, 12): "3028", (6, 14): "3456", (6, 16): "3027", (8, 8): "41539", (8, 16): "92438",
         (16, 16): "91405"}
TILE = {(1, 1): "3070b", (1, 2): "3069b", (1, 3): "63864", (1, 4): "2431", (1, 6): "6636",
        (1, 8): "4162", (2, 2): "3068b", (2, 3): "26603", (2, 4): "87079", (2, 6): "69729"}


def canon(part: str) -> str:
    return ENG.catalog.canonical(part)


# ------------------------------------------------------------------ colours and availability
def palette() -> dict[str, str]:
    return tomllib.loads((HERE / "model.toml").read_text()).get("palette", {})


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

    def lengths(self, table: dict, role: str) -> tuple[int, ...]:
        return tuple(sorted((n for n, p in table.items() if self.ok(p, role)), reverse=True))


AV = Avail()


# ------------------------------------------------------------------ geometry helpers
def bbox(part: str):
    return ENG.geom.mesh(canon(part)).bbox


def orient(ex, ey, ez=None) -> np.ndarray:
    """3x3 rotation whose columns are where the part's local X, Y and Z axes point."""
    ex, ey = np.asarray(ex, float), np.asarray(ey, float)
    ez = np.cross(ex, ey) if ez is None else np.asarray(ez, float)
    return np.column_stack([ex, ey, ez])


def studs_toward(n, along) -> np.ndarray:
    """Rotation for a plate/tile/brick whose studs point along n and whose length (local X)
    runs along `along`."""
    n, along = np.asarray(n, float), np.asarray(along, float)
    return orient(along, -n)


def M_of(pos, R=None) -> np.ndarray:
    return transform(pos, R)


def rect_M(table: dict, rect: tuple, y: float, ox=0.0, oz=0.0):
    """(part, M) for a rectangle (i0, i1, k0, k1) of stud cells with its top at y."""
    i0, i1, k0, k1 = rect
    w, d = i1 - i0 + 1, k1 - k0 + 1
    part = table[(min(w, d), max(w, d))]
    lo, hi = bbox(part)
    bx, bz = hi[0] - lo[0], hi[2] - lo[2]
    R = np.eye(3) if abs(bx - S * w) < 1 and abs(bz - S * d) < 1 else rot(y=90)
    return part, transform((ox + S * (i0 + i1 + 1) / 2, y, oz + S * (k0 + k1 + 1) / 2), R)


def run_M(n: int, axis: str, i: int, k: int, y: float, ox=0.0, oz=0.0):
    """Placement matrix of a 1 x n run starting at cell (i, k) along x or z (top at y)."""
    if axis == "x":
        return transform((ox + S * i + S * n / 2, y, oz + S * k + S / 2))
    return transform((ox + S * i + S / 2, y, oz + S * k + S * n / 2), rot(y=90))


def split_line(n: int, lengths, first=0) -> list[int]:
    """n studs as runs of the given lengths: a first run of `first` when it fits, then as
    few runs as possible, avoiding 1-stud runs."""
    lengths = sorted(set(lengths), reverse=True)
    best = {0: (0, 0, [])}
    for m in range(1, n + 1):
        cand = [(best[m - L][0] + (L == 1), best[m - L][1] + 1, best[m - L][2] + [L])
                for L in lengths if L <= m and m - L in best]
        if cand:
            best[m] = min(cand, key=lambda c: (c[0], c[1]))
    if first and first in lengths and n - first >= 0 and (n - first) in best \
            and (n - first == 0 or best[n - first][0] == 0):
        return [first] + sorted(best[n - first][2], reverse=True)
    return sorted(best[n][2], reverse=True)


def segments(vals: list[int]) -> list[list[int]]:
    vals = sorted(vals)
    out, cur = [], [vals[0]]
    for v in vals[1:]:
        if v == cur[-1] + 1:
            cur.append(v)
        else:
            out.append(cur)
            cur = [v]
    out.append(cur)
    return out


def weave(cells, along: str, lengths=(8, 6, 4, 3, 2, 1), phase=0) -> list[tuple]:
    """Cover cells with 1 x N runs along x (rows) or z (columns); successive lines start with
    a different run so joints stagger. Returns rects (i0, i1, k0, k1)."""
    lines = defaultdict(list)
    for i, k in cells:
        lines[k if along == "x" else i].append(i if along == "x" else k)
    out = []
    for n, key in enumerate(sorted(lines)):
        for seg in segments(lines[key]):
            first = (0, 3, 2, 4)[(n + phase) % 4]
            pos = seg[0]
            for L in split_line(len(seg), lengths, first):
                a, b = pos, pos + L - 1
                out.append((a, b, key, key) if along == "x" else (key, key, a, b))
                pos += L
    return out


def pack(cells, sizes, prefer="x", shift=0) -> list[tuple]:
    """Greedy cover of cells with rectangles from `sizes` (both orientations), biggest first."""
    free = set(cells)
    cand = set()
    for a, b in sizes:
        cand |= {(a, b), (b, a)}
    cand = sorted(cand, key=lambda s: (-s[0] * s[1], -(s[0] if prefer == "x" else s[1])))
    seq = sorted(free, key=lambda c: (c[1], c[0]))
    if shift and seq:
        seq = seq[shift % len(seq):] + seq[:shift % len(seq)]
    out = []
    for i, k in seq:
        if (i, k) not in free:
            continue
        for w, d in cand:
            box = {(i + a, k + b) for a in range(w) for b in range(d)}
            if box <= free:
                free -= box
                out.append((i, i + w - 1, k, k + d - 1))
                break
    return out


# ------------------------------------------------------------------ connectivity
def links(parts: list[tuple]) -> dict:
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
    first part so every step is one local cluster, lowest layer first. A step is captioned by
    the first category it introduces (in `captions` order)."""

    def __init__(self):
        self.items = []

    def add(self, part, color, M, cat, tag="", insert=None):
        self.items.append((canon(part), color, np.asarray(M, float), cat, tag, insert))

    def parts(self, cats=None):
        return [(p, M) for p, _, M, cat, *_ in self.items if cats is None or cat in cats]

    def emit(self, sub, phases: list, captions: dict, per_step: int = 6, reach: float = 140,
             order=None):
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
        low_of = {}
        for j, it in enumerate(self.items):
            lo, hi = bbox(it[0])
            corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1])
                                for z in (lo[2], hi[2])]) @ it[2][:3, :3].T + it[2][:3, 3]
            low_of[j] = round(corners[:, 1].max() / 4)      # lowest point, in 4 LDU bands
        for cats in phases:
            todo = [j for j, it in enumerate(self.items) if it[3] in cats]
            key = order or (lambda j: (-low_of[j], pos[j][2], pos[j][0]))
            todo.sort(key=key)
            while todo:
                step, anchor = [], None
                while todo and len(step) < per_step:
                    ready = [j for j in todo if adj[n0 + j] & built or not built]
                    if not ready:
                        if step:
                            break
                        ready = todo[:1]
                    low = max(low_of[j] for j in ready)
                    ready = [j for j in ready if low_of[j] == low]
                    if anchor is None:
                        j = ready[0]
                        anchor = pos[j]
                    else:
                        j = min(ready, key=lambda j: np.linalg.norm(pos[j] - anchor))
                        if np.linalg.norm(pos[j] - anchor) > reach and len(step) >= 2:
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


def use_M(sub, child, M, tag="", insert=None):
    M = np.asarray(M, float)
    return sub.use(child, tuple(M[:3, 3]), M[:3, :3], tag=tag, insert=insert)


def check_avail(batch: Batch, palette_roles: dict) -> list[str]:
    """Part/role pairs in a batch that don't exist (for design-time asserts)."""
    bad = []
    for part, color, *_ in batch.items:
        if isinstance(color, str) and not AV.ok(part, color):
            bad.append(f"{part} in {color}")
    return sorted(set(bad))
