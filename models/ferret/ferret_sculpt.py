"""Voxel sculpting on the stud grid: brick layers -> real parts, curved-slope caps, and a build
planner that orders parts so every part attaches to what is already built along a clear path.

Grid: cell (i, j) covers x in [20i, 20i+20) and z in [20j, 20j+20) LDU (plus the sculpt origin).
Heights are counted in plates (8 LDU) above the ground; a brick band k spans plates [3k, 3k+3).
LDraw: -Y is up, so a part whose top is at plate level p sits at y = -8p."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from brickkit.ldraw.matrix import rot

STUD, PLATE_H = 20, 8

BRICK = {(1, 1): "3005", (1, 2): "3004", (1, 3): "3622", (1, 4): "3010", (1, 6): "3009",
         (1, 8): "3008", (2, 2): "3003", (2, 3): "3002", (2, 4): "3001", (2, 6): "2456",
         (2, 8): "3007", (2, 10): "3006"}
PLATE = {(1, 1): "3024", (1, 2): "3023", (1, 3): "3623", (1, 4): "3710", (1, 6): "3666",
         (1, 8): "3460", (2, 2): "3022", (2, 3): "3021", (2, 4): "3020", (2, 6): "3795",
         (2, 8): "3034"}
TILE = {(1, 1): "3070b", (1, 2): "3069b", (1, 3): "63864", (1, 4): "2431", (2, 2): "3068b"}

# direction the low edge of a slope faces -> rotation (every slope in LDraw faces -Z)
FACING = {(0, -1): None, (0, 1): rot(y=180), (1, 0): rot(y=-90), (-1, 0): rot(y=90)}


@dataclass
class Piece:
    part: str
    role: str
    cells: frozenset            # footprint {(i, j)}
    p0: int                     # bottom, plates above ground
    p1: int                     # top
    studs: frozenset            # cells with studs on top (at p1)
    anti: dict                  # plate level -> cells with anti-studs there
    pos: tuple                  # LDraw position (sculpt frame)
    rot: np.ndarray | None = None
    band: int = 0
    note: str = ""
    idx: int = -1

    @property
    def top_anti(self):
        return self.anti


def _center(cells) -> tuple[float, float]:
    I = [c[0] for c in cells]
    J = [c[1] for c in cells]
    return STUD * (min(I) + max(I) + 1) / 2, STUD * (min(J) + max(J) + 1) / 2


def rect(i0, j0, ni, nj):
    return frozenset((i, j) for i in range(i0, i0 + ni) for j in range(j0, j0 + nj))


def block(table: dict, cells, p1: int, role: str, height: int, studs=True, band=0) -> Piece:
    """A rectangular brick/plate/tile covering `cells` with its top at plate level p1."""
    I = sorted({c[0] for c in cells})
    J = sorted({c[1] for c in cells})
    ni, nj = len(I), len(J)
    key = (min(ni, nj), max(ni, nj))
    part = table[key]
    x, z = _center(cells)
    r = None if (ni >= nj) else rot(y=90)
    cells = frozenset(cells)
    return Piece(part, role, cells, p1 - height, p1, cells if studs else frozenset(),
                 {p1 - height: cells}, (x, -PLATE_H * p1, z), r, band)


def brick(cells, p1, role, band=0):
    return block(BRICK, cells, p1, role, 3, band=band)


def plate(cells, p1, role, band=0):
    return block(PLATE, cells, p1, role, 1, band=band)


def tile(cells, p1, role, band=0):
    return block(TILE, cells, p1, role, 1, studs=False, band=band)


def roof_pieces(ramp: list, d: tuple, p0: int, role: str, band: int) -> list[Piece]:
    """Low (2-plate) cap for a ramp with nothing behind its high end: a curved slope over the two
    outer cells (cheese slope if only one), plate + tile on any further inner cells."""
    R = FACING[d]
    out = []
    outer, inner = ramp[:2], ramp[2:]
    x, z = _center(outer)
    cells = frozenset(outer)
    if len(outer) == 2:
        out.append(Piece("11477", role, cells, p0, p0 + 2, frozenset(), {p0: frozenset({outer[0]})},
                         (x, -PLATE_H * p0, z), R, band, "cap"))
    else:
        out.append(Piece("54200", role, cells, p0, p0 + 2, frozenset(), {p0: cells},
                         (x, -PLATE_H * p0, z), R, band, "cap"))
    if inner:
        base = plate(inner, p0 + 1, role, band)
        top = tile(inner, p0 + 2, role, band)
        base.note = top.note = "cap"
        out += [base, top]
    return out


def ramp_pieces(ramp: list, d: tuple, p0: int, role: str, band: int) -> list[Piece]:
    """Cap pieces for a ramp of 1-3 cells ordered outer (low) -> inner (high), sitting on a
    surface at plate level p0 and reaching p0 + 3 at the high end. d = outward direction."""
    n = len(ramp)
    R = FACING[d]
    cells = frozenset(ramp)
    x, z = _center(ramp)
    if n == 3:
        low, mid = ramp[0], ramp[1]
        return [Piece("50950", role, cells, p0, p0 + 3, frozenset(), {p0: frozenset({low, mid})},
                      (x, -PLATE_H * (p0 + 3), z), R, band, "cap")]
    base = plate(ramp, p0 + 1, role, band)
    base.note = "cap"
    if n == 2:
        top = Piece("11477", role, cells, p0 + 1, p0 + 3, frozenset(),
                    {p0 + 1: frozenset({ramp[0]})}, (x, -PLATE_H * (p0 + 1), z), R, band, "cap")
    else:
        top = Piece("54200", role, cells, p0 + 1, p0 + 3, frozenset(),
                    {p0 + 1: cells}, (x, -PLATE_H * (p0 + 1), z), R, band, "cap")
    return [base, top]


# --------------------------------------------------------------------------------------------
# packing

def pack(cells, sizes, axis: str, p1: int, role: str, height: int = 3, band: int = 0,
         table=None) -> list[Piece]:
    """Greedy cover of `cells` with rectangles from `sizes` [(w, n)], long side along `axis`
    first ('x' or 'z'), largest first."""
    table = table or (BRICK if height == 3 else PLATE)
    left = set(cells)
    out = []
    sizes = sorted(sizes, key=lambda s: (-s[0] * s[1], -s[1]))
    order = sorted(left, key=(lambda c: (c[1], c[0])) if axis == "x" else (lambda c: (c[0], c[1])))
    for c in order:
        if c not in left:
            continue
        done = False
        for w, n in sizes:
            for ax in ((axis, "z" if axis == "x" else "x") if w != n else (axis,)):
                ni, nj = (n, w) if ax == "x" else (w, n)
                r = rect(c[0], c[1], ni, nj)
                if r <= left:
                    out.append(block(table, r, p1, role, height, band=band))
                    left -= r
                    done = True
                    break
            if done:
                break
        if not done:
            raise ValueError(f"cannot cover cell {c} (sizes {sizes})")
    return out


def _rects_containing(c, sizes):
    for w, n in sizes:
        for ni, nj in {(n, w), (w, n)}:
            for a in range(ni):
                for b in range(nj):
                    yield rect(c[0] - a, c[1] - b, ni, nj)


def pack_layer(cells, role_of: dict, supported: set, sizes_of, axis: str, p1: int, band: int,
               height: int = 3) -> list[Piece]:
    """Cover one layer. Cells without support (nothing above or below them in the same section)
    are covered first, each by a brick that also reaches a supported cell, so no brick floats;
    a brick may swallow hidden 'core' cells but never mixes two visible roles. The rest is packed
    per role with long bricks along `axis` (alternate it between layers for a running bond)."""
    table = BRICK if height == 3 else PLATE
    left = set(cells)
    out = []
    rim = [c for c in sorted(cells) if c not in supported]
    rimset = set(rim)
    for c in rim:
        if c not in left:
            continue
        role = role_of[c]
        best, best_score = None, None
        for r in _rects_containing(c, sizes_of(role)):
            if not r <= left or not (r & supported):
                continue
            if any(role_of[x] not in (role, "core") for x in r):
                continue
            score = 3 * len(r & rimset) + min(len(r), 4)
            if best_score is None or score > best_score:
                best, best_score = r, score
        if best is not None:
            out.append(block(table, best, p1, role, height, band=band))
            left -= best
    groups: dict[str, set] = {}
    for c in left:
        groups.setdefault(role_of[c], set()).add(c)
    for role, rc in groups.items():
        out += pack(rc, sizes_of(role), axis, p1, role, height, band=band, table=table)
    return out


class _UF:
    def __init__(self):
        self.p = {}

    def find(self, a):
        self.p.setdefault(a, a)
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


def _rect_role(r, role_of):
    vis = {role_of[c] for c in r if role_of[c] != "core"}
    if len(vis) > 1:
        return None
    return vis.pop() if vis else "core"


def pack_section(layers, sizes_of, height: int = 3):
    """Pack the layers of one sub-assembly so it holds together as one piece.

    `layers` = [(band, cells, role_of, axis)] in build order (each layer is stacked on, or hung
    from, the previous one). The first layer is packed with long bricks; every later layer is
    packed greedily with the brick that bridges the most still-separate clusters of the previous
    layer (then the biggest), so the bonds knit the whole section together.
    Returns (pieces, number of separate clusters left)."""
    table = BRICK if height == 3 else PLATE
    all_sizes = sorted({s for r in ("core",) for s in sizes_of(r)} |
                       {s for _, _, ro, _ in layers for r in set(ro.values()) for s in sizes_of(r)},
                       key=lambda s: -s[0] * s[1])
    uf = _UF()
    pieces: list[Piece] = []
    prev_owner: dict = {}

    def ok_rect(r, role_of):
        role = _rect_role(r, role_of)
        if role is None:
            return None
        ni = len({x[0] for x in r})
        nj = len({x[1] for x in r})
        return role if (min(ni, nj), max(ni, nj)) in sizes_of(role) else None

    def fill(cells, role_of, axis, touch, u):
        """Greedy cover; rim cells (no neighbour layer) first, then bricks bridging the most
        separate clusters below. Unions the bridged clusters in `u`. -> [(rect, role)]"""
        left = set(cells)
        rim = sorted(c for c in cells if c not in touch)
        out = []
        while left:
            cand = [c for c in rim if c in left][:1] or sorted(left)
            best = None
            for c in cand:
                for r in _rects_containing(c, all_sizes):
                    if not r <= left:
                        continue
                    role = ok_rect(r, role_of)
                    if role is None:
                        continue
                    comps = {u.find(prev_owner[x]) for x in r if x in prev_owner}
                    ni = len({x[0] for x in r})
                    along = (ni > len(r) // ni) == (axis == "x")
                    score = (bool(r & touch), len(comps), len(r), along)
                    if best is None or score > best[0]:
                        best = (score, r, role, comps)
            _, r, role, comps = best
            comps = list(comps)
            for cp in comps[1:]:
                u.union(cp, comps[0])
            out.append((r, role))
            left -= r
        return out

    def roots_after(rects, base):
        u = _UF()
        u.p = dict(base.p)
        for r, _ in rects:
            comps = [u.find(prev_owner[x]) for x in r if x in prev_owner]
            for cp in comps[1:]:
                u.union(cp, comps[0])
        return u, len({u.find(i) for i in set(prev_owner.values())})

    for t, (band, cells, role_of, axis) in enumerate(layers):
        p1 = height * (band + 1)
        nxt = layers[t + 1][1] if t + 1 < len(layers) else set()
        touch = set(prev_owner) | set(nxt)          # cells that bond to a neighbouring layer
        base = _UF()
        base.p = dict(uf.p)
        trial = _UF()
        trial.p = dict(uf.p)
        rects = fill(cells, role_of, axis, touch, trial)
        # repair: make one brick span each junction between clusters that are still apart
        failed = set()
        u, n_roots = roots_after(rects, base)
        for _ in range(200):
            pair = None
            for c in sorted(cells):
                if c not in prev_owner:
                    continue
                for n in ((c[0] + 1, c[1]), (c[0], c[1] + 1)):
                    if n in cells and n in prev_owner and (c, n) not in failed and \
                            u.find(prev_owner[c]) != u.find(prev_owner[n]):
                        pair = (c, n)
                        break
                if pair:
                    break
            if pair is None:
                break
            c1, c2 = pair
            hit = [rr for rr in rects if c1 in rr[0] or c2 in rr[0]]
            freed = set().union(*(rr[0] for rr in hit))
            new_role = ok_rect(frozenset(pair), role_of)
            if new_role is None:
                # bonding matters more than a colour edge: let one colour bleed by a stud
                new_role = next((role_of[c] for c in pair if role_of[c] != "core"
                                 and (1, 2) in sizes_of(role_of[c])), None)
            if new_role is None:
                failed.add(pair)
                continue
            keep = [rr for rr in rects if rr not in hit]
            t_uf = _UF()
            t_uf.p = dict(base.p)
            rest = fill(freed - set(pair), role_of, axis, touch, t_uf)
            cand = keep + [(frozenset(pair), new_role)] + rest
            u2, n2 = roots_after(cand, base)
            if n2 < n_roots:
                rects, u, n_roots = cand, u2, n2
            else:
                failed.add(pair)
        owner: dict = {}
        for r, role in rects:
            p = block(table, r, p1, role, height, band=band)
            p.idx = len(pieces)
            pieces.append(p)
            uf.find(p.idx)
            for x in r:
                if x in prev_owner:
                    uf.union(prev_owner[x], p.idx)
                owner[x] = p.idx
        # pieces of the previous layer under/over the same cells are connected to these
        prev_owner = owner
    roots = {uf.find(p.idx) for p in pieces}
    return pieces, len(roots)


# --------------------------------------------------------------------------------------------
# planning

@dataclass
class Plan:
    order: list
    stuck: list = field(default_factory=list)


def _index(pieces):
    occ = {}
    for n, p in enumerate(pieces):
        for c in p.cells:
            for lv in range(p.p0, p.p1):
                occ.setdefault((c, lv), set()).add(n)
    return occ


def relations(pieces, travel: int = 4):
    """below[n]: pieces n sits on; above[n]: pieces sitting on n; over[n] / under[n]: pieces in
    the way when n is pushed down from above / up from below."""
    occ = _index(pieces)
    tops = {}
    for n, p in enumerate(pieces):
        for c in p.studs:
            tops.setdefault((c, p.p1), set()).add(n)
    below = [set() for _ in pieces]
    above = [set() for _ in pieces]
    for n, p in enumerate(pieces):
        for lv, cells in p.anti.items():
            for c in cells:
                for m in tops.get((c, lv), ()):
                    if m != n:
                        below[n].add(m)
                        above[m].add(n)
    over = [set() for _ in pieces]
    under = [set() for _ in pieces]
    for n, p in enumerate(pieces):
        for c in p.cells:
            for lv in range(p.p1, p.p1 + travel):
                over[n] |= occ.get((c, lv), set())
            for lv in range(p.p0 - travel, p.p0):
                under[n] |= occ.get((c, lv), set())
        over[n].discard(n)
        under[n].discard(n)
    return below, above, over, under


def plan(pieces, key, seed=None) -> Plan:
    """Greedy build order: repeatedly add the lowest-`key` piece that touches the built part and
    can slide in (down onto what it sits on, or up into what it hangs from) without hitting
    anything already built."""
    n = len(pieces)
    below, above, over, under = relations(pieces)
    built = np.zeros(n, bool)
    order = []
    keys = [key(p) for p in pieces]
    remaining = set(range(n))
    if seed is None:
        # start in the biggest connected cluster
        from brickkit.checks.base import components
        comp = components(n, [(a, b) for a in range(n) for b in below[a]])[0]
        seed = min(comp, key=lambda m: keys[m])
    first = seed
    order.append(first)
    built[first] = True
    remaining.discard(first)
    # blocks[m]: pieces whose way in (from above or from below) m would block once built
    blocks = [set() for _ in range(n)]
    for x in range(n):
        for m in over[x] | under[x]:
            blocks[m].add(x)

    def kills(m) -> int:
        """How many unbuilt pieces would be shut in (blocked above and below) by building m."""
        built[m] = True
        dead = sum(1 for x in blocks[m] if not built[x]
                   and any(built[o] for o in over[x]) and any(built[u] for u in under[x]))
        built[m] = False
        return dead

    while remaining:
        cands = [m for m in remaining
                 if (any(built[b] for b in below[m]) and not any(built[o] for o in over[m]))
                 or (any(built[a] for a in above[m]) and not any(built[u] for u in under[m]))]
        if not cands:
            return Plan([pieces[m] for m in order], [pieces[m] for m in sorted(remaining)])
        cands.sort(key=lambda m: keys[m])
        best = next((m for m in cands if not kills(m)), None)
        if best is None:
            best = min(cands, key=lambda m: (kills(m), keys[m]))
        order.append(best)
        built[best] = True
        remaining.discard(best)
    return Plan([pieces[m] for m in order])


def steps(order, max_parts: int = 8):
    """Split an ordered list into steps: a new step when full, or when a piece overlaps (in plan
    view) a piece of another height band already in the step."""
    out, cur = [], []
    for p in order:
        clash = any(q.band != p.band and (q.cells & p.cells) for q in cur)
        if cur and (len(cur) >= max_parts or clash):
            out.append(cur)
            cur = []
        cur.append(p)
    if cur:
        out.append(cur)
    return out


def emit(sub, groups, origin=(0, 0, 0), captions=None):
    """Place the planned pieces in a submodel, one builder step per group."""
    ox, oy, oz = origin
    for g, grp in enumerate(groups):
        sub.step(captions[g] if captions else "")
        for p in grp:
            x, y, z = p.pos
            sub.place(p.part, p.role, (x + ox, y + oy, z + oz), p.rot, note=p.note)
