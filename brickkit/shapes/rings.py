"""Raster rings and shells of revolution on the stud grid.

Cells are integer (i, k) stud positions on a grid centred between four studs: a cell's centre
is at (i + 0.5, k + 0.5) studs from the axis, so rings are symmetric in all four quadrants."""
from __future__ import annotations

import math
from typing import Callable

Cell = tuple[int, int]


def cell_center(c: Cell) -> tuple[float, float]:
    return c[0] + 0.5, c[1] + 0.5


def ring_cells(r_out: float, r_in: float = 0.0) -> set[Cell]:
    """Cells whose centre lies at r_in <= distance < r_out (in studs)."""
    n = int(math.ceil(r_out)) + 1
    return {(i, k) for i in range(-n, n) for k in range(-n, n)
            if r_in <= math.hypot(i + 0.5, k + 0.5) < r_out}


def tangent_axis(c: Cell) -> str:
    """Axis along the ring at this cell: 'x' in the north/south sectors, 'z' east/west."""
    x, z = cell_center(c)
    return "x" if abs(z) >= abs(x) else "z"


def outward(c: Cell) -> tuple[int, int]:
    """Dominant outward direction (dx, dz) of a cell, one of the four grid directions."""
    x, z = cell_center(c)
    if abs(x) >= abs(z):
        return (1 if x > 0 else -1, 0)
    return (0, 1 if z > 0 else -1)


def _split(n: int, lengths: tuple[int, ...], phase: int) -> list[int]:
    lengths = tuple(sorted(lengths, reverse=True))
    out, left = [], n
    if phase % 2 and n >= 2 and 1 in lengths:
        out.append(1)
        left -= 1
    while left > 0:
        piece = next(L for L in lengths if L <= left)
        out.append(piece)
        left -= piece
    return out


def pack_cells(cells, lengths: tuple[int, ...] = (2, 1), offset: int = 0,
               mode: str = "tangent") -> list[tuple[int, int, int, str]]:
    """Cover every cell exactly once with straight 1xN runs (i, k, n, axis).

    mode 'tangent' runs along the ring, 'x'/'z' force one axis. `offset` shifts where the
    seams fall, so alternating layers bond like brickwork."""
    cells = set(cells)
    if 1 not in lengths:
        raise ValueError("lengths must include 1 so any run can be covered")
    axis_of = {c: (tangent_axis(c) if mode == "tangent" else mode) for c in cells}
    runs = []
    for axis in ("x", "z"):
        mine = sorted(c for c in cells if axis_of[c] == axis)
        lines: dict[int, list[int]] = {}
        for i, k in mine:
            key, pos = (k, i) if axis == "x" else (i, k)
            lines.setdefault(key, []).append(pos)
        for key, positions in lines.items():
            positions.sort()
            start = prev = positions[0]
            for p in positions[1:] + [None]:
                if p is not None and p == prev + 1:
                    prev = p
                    continue
                at = start
                for n in _split(prev - start + 1, lengths, offset + key):
                    runs.append((at, key, n, "x") if axis == "x" else (key, at, n, "z"))
                    at += n
                if p is not None:
                    start = prev = p
    return runs


def pair_unsupported(cells, support) -> tuple[list, set]:
    """Pair every cell that has nothing under it with a free supported neighbour (1x2 run).
    Most-constrained cells go first, and each takes the neighbour fewest others need, so
    shared supported cells aren't used up greedily. Returns (runs, cells still free)."""
    free, support, runs = set(cells), set(support), []
    dirs = ((1, 0), (-1, 0), (0, 1), (0, -1))

    def options(c):
        return [(c[0] + d[0], c[1] + d[1]) for d in dirs
                if (c[0] + d[0], c[1] + d[1]) in free and (c[0] + d[0], c[1] + d[1]) in support]

    pending = {c for c in free if c not in support}
    while pending:
        c = min(pending, key=lambda c: (len(options(c)), -math.hypot(*cell_center(c)), c))
        pending.discard(c)
        opts = options(c)
        if not opts:
            continue
        demand = lambda nb: sum(1 for o in pending if nb in options(o))
        nb = min(opts, key=lambda nb: (demand(nb), nb))
        free -= {c, nb}
        a, b = min(c, nb), max(c, nb)
        runs.append((a[0], a[1], 2, "x" if a[1] == b[1] else "z"))
    return runs, free


def pack_angular(cells, offset: int = 0, support=None) -> list[tuple[int, int, int, str]]:
    """Pair neighbouring cells into 1x2 runs walking around the axis by angle (greedy
    matching), leaving few 1x1s even on diagonal staircases. `offset` rotates the starting
    angle so alternate layers get their seams in different places.

    `support` (cells of the layer below) makes every run rest on at least one supported
    cell: overhanging cells are first paired with a supported neighbour, preferring the one
    toward the axis."""
    cells = set(cells)
    if not cells:
        return []
    runs = []
    if support is not None:
        runs, cells = pair_unsupported(cells, support)
    def ang(c):
        x, z = cell_center(c)
        return math.atan2(z, x)
    start = (offset % 2) * math.pi / max(len(cells), 1) * 1.0 + (offset % 4) * 0.0
    order = sorted(cells, key=lambda c: ((ang(c) - start) % (2 * math.pi), math.hypot(*cell_center(c))))
    if offset % 2:
        order = order[1:] + order[:1]
    rank = {c: n for n, c in enumerate(order)}
    free = set(cells)
    for c in order:
        if c not in free:
            continue
        free.discard(c)
        best = None
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = (c[0] + d[0], c[1] + d[1])
            if nb in free:
                gap = (rank[nb] - rank[c]) % len(order)
                if best is None or gap < best[0]:
                    best = (gap, nb, d)
        if best is None:
            runs.append((c[0], c[1], 1, "x"))
            continue
        _, nb, d = best
        free.discard(nb)
        a = min(c, nb)
        runs.append((a[0], a[1], 2, "x" if d[1] == 0 else "z"))
    return runs


def exposed(lower, upper) -> list[tuple[Cell, tuple[int, int]]]:
    """Cells of `lower` not covered by `upper`, with their outward direction."""
    upper = set(upper)
    return [(c, outward(c)) for c in sorted(lower) if c not in upper]


def shell_layers(profile: Callable[[float], float], heights, thickness: float = 1.0
                 ) -> list[tuple[float, float, float]]:
    """(height, r_out, r_in) per layer. Each layer reaches in far enough for the next layer to
    sit on it; the last layer is solid (a cap)."""
    heights = list(heights)
    radii = [profile(h) for h in heights]
    out = []
    for n, (h, r) in enumerate(zip(heights, radii)):
        if n + 1 < len(heights):
            r_in = max(0.0, min(r - thickness, radii[n + 1] - 1.0))
        else:
            r_in = 0.0
        out.append((h, r, r_in))
    return out
