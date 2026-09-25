"""Hollow shells of revolution (domes, bowls, bodies) built from bonded rings of bricks and
plates, with slopes on the exposed steps so the outside reads as a smooth curve.

Conventions (LDraw): -Y is up; bricks/plates have their origin on the top face; slopes have
their origin on the bottom face with the low side facing -Z; tiles have their origin on the top
face. Cells are stud positions around the vertical axis at (0, 0) (see rings.py)."""
from __future__ import annotations

from dataclasses import dataclass, field

from ..ldraw.matrix import rot
from .rings import cell_center, exposed, pack_angular, pack_cells, pair_unsupported, ring_cells

HEIGHT = {"brick": 24, "plate": 8}
# rotation (about Y) that turns a part's -Z side toward the given outward direction
FACING = {(0, -1): 0, (0, 1): 180, (1, 0): -90, (-1, 0): 90}


@dataclass
class ShellVocab:
    brick: dict = field(default_factory=lambda: {2: "3065", 1: "3005"})
    plate: dict = field(default_factory=lambda: {2: "3023b", 1: "3024"})
    slope1: str | None = "54200"     # 1x1 slope, 16 tall, low side -Z, origin on bottom face
    slope2: str | None = "11477"     # 1x2 curved slope along Z, 16 tall, low side -Z
    tile1: str | None = "3070b"      # flat tile for exposed plate-layer cells
    slope45: str | None = "3040b"    # 1x2 45-degree slope brick: high cell at origin, low cell at -Z


@dataclass
class Layer:
    kind: str        # brick | plate
    r_out: float     # studs
    r_in: float      # studs


def plan_layers(profile, top: float, *, thickness: float = 1.0, max_step: float = 1.0,
                bricks_only: bool = False, closed_top: bool = True, reach: float = 0.7
                ) -> list[Layer]:
    """Walk up from height 0 to `top` (LDU above the base). `profile(h)` gives the outer radius
    in studs at h. Uses a brick layer when the radius changes by at most `max_step` studs over
    a brick height, otherwise a plate layer. Inner radii make every layer overlap its
    neighbours by at least one stud so the shell is one connected piece."""
    hs, kinds, h = [], [], 0.0
    while h < top - 1e-6:
        r0, r1 = profile(h), profile(min(h + 24, top))
        kind = "brick" if bricks_only or abs(r1 - r0) <= max_step else "plate"
        if h + HEIGHT[kind] > top + 1e-6:
            kind = "plate"
        hs.append(h)
        kinds.append(kind)
        h += HEIGHT[kind]
    radii = [profile(h + HEIGHT[k] / 2) for h, k in zip(hs, kinds)]
    r_in = []
    for n, r in enumerate(radii):
        v = r - thickness
        if n + 1 < len(radii):
            v = min(v, radii[n + 1] - 1.0)      # the ring above rests on this one
        if n > 0:
            v = min(v, radii[n - 1] - 1.0)      # this ring rests on the one below (flares)
        r_in.append(v)
    if closed_top:
        r_in[-1] = 0.0
    # every cell of the ring above must be at most ~one stud from a supported cell, also on
    # the diagonal staircases: walk down from the top thickening rings where needed
    for n in range(len(radii) - 2, -1, -1):
        r_in[n] = min(r_in[n], r_in[n + 1] + reach)
    return [Layer(k, r, max(0.0, v)) for k, r, v in zip(kinds, radii, r_in)]


def _place_run(sub, part, color, i, k, n, axis, y, tag):
    cx = (i + (n / 2 if axis == "x" else 0.5)) * 20
    cz = (k + (n / 2 if axis == "z" else 0.5)) * 20
    return sub.place(part, color, (cx, y, cz), rot(y=90) if axis == "z" and n > 1 else None,
                     tag=tag)


def build_shell(sub, layers: list[Layer], color, *, y_base: float = 0.0,
                vocab: ShellVocab | None = None, smooth: bool = True, tag: str = "",
                quadrant_steps: bool = True, caption: str = "Layer {n}",
                integrated: bool = True, base_cells=None) -> dict:
    """Place the shell into `sub`, one instruction step per layer quadrant. `y_base` is the
    LDraw y of the surface the first layer sits on. With `integrated`, a brick layer's outermost
    cells over a one-stud step become 45-degree slope bricks (one part covering the step and the
    cell behind it); other exposed steps get plate + slope or tiles. Returns stats."""
    vocab = vocab or ShellVocab()
    y = y_base
    cells_by_layer = [ring_cells(L.r_out, L.r_in) for L in layers]
    placed = 0
    for n, L in enumerate(layers):
        cells = set(cells_by_layer[n])
        h = HEIGHT[L.kind]
        support = cells_by_layer[n - 1] if n > 0 else base_cells
        parts = vocab.brick if L.kind == "brick" else vocab.plate
        pre_runs = []
        if support is not None and 2 in parts:
            pre_runs, cells = pair_unsupported(cells, support)   # before slopes claim cells
        slopes, leftovers = [], []
        if smooth and n > 0:
            ex = exposed(cells_by_layer[n - 1], cells_by_layer[n])
            used = set()
            for e, d in ex:
                x, z = cell_center(e)
                # try the dominant outward direction, then the other axis (diagonal steps)
                other = (0, 1 if z > 0 else -1) if d[0] else (1 if x > 0 else -1, 0)
                for dd in (d, other):
                    hi = (e[0] - dd[0], e[1] - dd[1])
                    if (integrated and L.kind == "brick" and vocab.slope45 and hi in cells
                            and hi not in used):
                        slopes.append((hi, dd))
                        used.add(hi)
                        break
                else:
                    leftovers.append((e, d))
            cells -= used
        if leftovers:
            placed += _smooth_cells(sub, leftovers, L.kind, color, y, vocab, tag, n)
        runs = pre_runs + (pack_angular(cells, offset=n) if tuple(sorted(parts)) == (1, 2)
                           else pack_cells(cells, lengths=tuple(parts), offset=n))
        quads = ([[r for r in runs if (r[0] >= 0) == qx and (r[1] >= 0) == qz]
                  for qx in (False, True) for qz in (False, True)] if quadrant_steps else [runs])
        for q, qruns in enumerate(quads):
            if not qruns:
                continue
            sub.step(caption.format(n=n + 1) + (f" ({q + 1}/4)" if quadrant_steps else ""))
            for i, k, length, axis in qruns:
                _place_run(sub, parts[length], color, i, k, length, axis, y - h + 0, tag)
                placed += 1
        if slopes:
            sub.step(caption.format(n=n + 1) + " slopes")
            for (i, k), d in slopes:
                sub.place(vocab.slope45, color, ((i + .5) * 20, y - h, (k + .5) * 20),
                          rot(y=FACING[d]), tag=tag)
                placed += 1
        y = y - h
    return {"layers": len(layers), "parts": placed, "top_y": y}


def _smooth_cells(sub, ex, kind, color, surface_y, vocab, tag, n) -> int:
    """Exposed step cells (of the layer below) covered with parts as tall as this layer."""
    exd = dict(ex)
    used, count = set(), 0
    sub.step(f"Smooth under layer {n + 1}")
    for c, d in ex:
        if c in used:
            continue
        x, z = (c[0] + .5) * 20, (c[1] + .5) * 20
        if kind == "plate":
            if vocab.tile1:
                sub.place(vocab.tile1, color, (x, surface_y - 8, z), tag=tag)
                used.add(c)
                count += 1
            continue
        inner = (c[0] - d[0], c[1] - d[1])
        if vocab.slope2 and inner in exd and exd[inner] == d and inner not in used:
            mx, mz = (c[0] + inner[0] + 1) * 10, (c[1] + inner[1] + 1) * 10
            sub.place(vocab.plate[2], color, (mx, surface_y - 8, mz),
                      rot(y=90) if d[0] == 0 else None, tag=tag)
            sub.place(vocab.slope2, color, (mx, surface_y - 8, mz), rot(y=FACING[d]), tag=tag)
            used |= {c, inner}
            count += 2
        elif vocab.slope1:
            sub.place(vocab.plate[1], color, (x, surface_y - 8, z), tag=tag)
            sub.place(vocab.slope1, color, (x, surface_y - 8, z), rot(y=FACING[d]), tag=tag)
            used.add(c)
            count += 2
    return count


def _smooth_cells(sub, ex, kind, color, surface_y, vocab, tag, n) -> int:
    """Exposed step cells (of the layer below) covered with parts as tall as this layer."""
    exd = dict(ex)
    used, count = set(), 0
    sub.step(f"Smooth under layer {n + 1}")
    for c, d in ex:
        if c in used:
            continue
        x, z = (c[0] + .5) * 20, (c[1] + .5) * 20
        if kind == "plate":
            if vocab.tile1:
                sub.place(vocab.tile1, color, (x, surface_y - 8, z), tag=tag)
                used.add(c)
                count += 1
            continue
        inner = (c[0] - d[0], c[1] - d[1])
        if vocab.slope2 and inner in exd and exd[inner] == d and inner not in used:
            mx, mz = (c[0] + inner[0] + 1) * 10, (c[1] + inner[1] + 1) * 10
            sub.place(vocab.plate[2], color, (mx, surface_y - 8, mz),
                      rot(y=90) if d[0] == 0 else None, tag=tag)
            sub.place(vocab.slope2, color, (mx, surface_y - 8, mz), rot(y=FACING[d]), tag=tag)
            used |= {c, inner}
            count += 2
        elif vocab.slope1:
            sub.place(vocab.plate[1], color, (x, surface_y - 8, z), tag=tag)
            sub.place(vocab.slope1, color, (x, surface_y - 8, z), rot(y=FACING[d]), tag=tag)
            used.add(c)
            count += 2
    return count


def _smooth(sub, lower, upper, next_kind, color, top_y, vocab, tag, n) -> int:
    """Cover the lower layer's exposed step cells with parts as tall as the next layer:
    a tile under a plate layer, a plate + slope (8 + 16) under a brick layer."""
    ex = exposed(lower, upper)
    if not ex:
        return 0
    sub.step(f"Smooth layer {n + 1}")
    used, count = set(), 0
    exd = dict(ex)
    for c, d in ex:
        if c in used:
            continue
        if next_kind == "plate":
            if vocab.tile1:
                sub.place(vocab.tile1, color, ((c[0] + .5) * 20, top_y - 8, (c[1] + .5) * 20), tag=tag)
                used.add(c)
                count += 1
            continue
        inner = (c[0] - d[0], c[1] - d[1])
        ry = FACING[d]
        if vocab.slope2 and inner in exd and exd[inner] == d and inner not in used:
            # 1x2 plate + 1x2 curved slope, running radially, low end at the outer cell
            mx, mz = (c[0] + inner[0] + 1) * 10, (c[1] + inner[1] + 1) * 10
            radial_z = d[0] == 0
            sub.place(vocab.plate[2], color, (mx, top_y - 8, mz), rot(y=90) if radial_z else None,
                      tag=tag)
            sub.place(vocab.slope2, color, (mx, top_y - 8, mz), rot(y=ry), tag=tag)
            used |= {c, inner}
            count += 2
        elif vocab.slope1:
            x, z = (c[0] + .5) * 20, (c[1] + .5) * 20
            sub.place(vocab.plate[1], color, (x, top_y - 8, z), tag=tag)
            sub.place(vocab.slope1, color, (x, top_y - 8, z), rot(y=ry), tag=tag)
            used.add(c)
            count += 2
    return count


def woven_disc(sub, cells, color, *, surface_y: float, plate: dict | None = None,
               tag: str = "", caption: str = "Cap") -> dict:
    """Two plate layers over `cells` with runs crossing at right angles (x then z), so the disc
    is one rigid sheet that can bridge a hole in the ring below. `surface_y` is the LDraw y of
    the surface under the first layer. Both layers go in one step (the first layer is only
    locked by the second). Returns stats and the top y."""
    plate = plate or {2: "3023b", 1: "3024"}
    best = None
    for oa in range(2):
        for ob in range(2):
            a = pack_parity(cells, "x", oa)
            b = pack_parity(cells, "z", ob)
            pieces = _sheet_pieces(a, b)
            if best is None or pieces < best[0]:
                best = (pieces, a, b)
    sub.step(caption)
    count = 0
    y = surface_y
    for runs in best[1:]:
        for i, k, n, axis in runs:
            _place_run(sub, plate[n], color, i, k, n, axis, y - 8, tag)
            count += 1
        y -= 8
    return {"parts": count, "top_y": y, "pieces": best[0]}


def pack_parity(cells, axis: str, parity: int) -> list[tuple[int, int, int, str]]:
    """1x2 runs along `axis` starting on cells where (i + k + parity) is even (a running
    bond on the absolute grid); leftover cells become 1x1."""
    cells = set(cells)
    runs, used = [], set()
    for c in sorted(cells):
        if c in used:
            continue
        nb = (c[0] + 1, c[1]) if axis == "x" else (c[0], c[1] + 1)
        if (c[0] + c[1] + parity) % 2 == 0 and nb in cells and nb not in used:
            runs.append((c[0], c[1], 2, axis))
            used |= {c, nb}
    for c in sorted(cells - used):
        runs.append((c[0], c[1], 1, axis))
    return runs


def _run_cells(run):
    i, k, n, axis = run
    return [(i + d, k) if axis == "x" else (i, k + d) for d in range(n)]


def _sheet_pieces(a, b) -> int:
    """How many separate pieces two stacked layers of runs form (1 = one rigid sheet)."""
    from .rings import cell_center  # noqa: F401  (keeps import local and cheap)
    owner = {}
    for idx, run in enumerate(a + b):
        for c in _run_cells(run):
            owner.setdefault(c, []).append(idx)
    parent = list(range(len(a) + len(b)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for ids in owner.values():
        for j in ids[1:]:
            parent[find(j)] = find(ids[0])
    return len({find(i) for i in range(len(parent))})
