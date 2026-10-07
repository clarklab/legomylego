"""Massive shapes on the hull built studs up: a stack of brick levels over cells, sloped where a
level steps back (the wheelhouse, the after deckhouse), and the wheelhouse itself.

`slope_stack(h, base_y)`: h maps cells (i, k) (column i: x in [20 i, 20 i + 20], row k: z in
[20 k, 20 k + 20]) to a number of brick levels standing on a surface whose top is at base_y.
Where a level steps back one cell from the level under it, a 45 degree slope (2 x 1, 2 x 2 or
2 x 4) fills the step; two cells, a 33 degree slope (3 x 1, 3 x 2); a corner stepping back both
ways, a 45 degree double convex corner. Studs left on top get tiles.

Hull frame (naut_shape): LDU, -Y up, bow toward -X, port toward -Z."""
from __future__ import annotations

from collections import defaultdict

import numpy as np

import naut_shape as shp
from brickkit.ldraw.matrix import rot, transform
from naut_kit import (AV, BRICK, PLATE, S, TILE, Batch, connected, ids_of, orient, pack,
                      rect_part)

LV = 24
DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))
SLOPE45 = {1: "3040", 2: "3039", 4: "3037"}       # by width (studs across the slope)
SLOPE33 = {1: "4286", 2: "3298"}
CORNER45 = "3045"


def cell_xz(c) -> tuple[float, float]:
    return S * c[0] + S / 2, S * c[1] + S / 2


def _R_down(d) -> np.ndarray:
    """A slope brick turned so that it slopes down toward d (grid (di, dk)): local -Z -> d."""
    ez = -np.array([d[0], 0.0, d[1]])
    ey = np.array([0.0, 1.0, 0.0])
    return orient(np.cross(ey, ez), ey, ez)


def slope_stack(h: dict, base_y: float, role: str = "hull", fixed=None, cat: str = "body",
                base_cells=None, no_tile=(), flat_top=False, curved=False) -> Batch:
    """The stack's parts (see the module's docstring). `fixed`: {level: {cells}} filled by
    parts the caller adds itself. `base_cells`: cells of the surface under level 0 (a slope's
    foot may stand on them; default: the stack's own footprint). `curved`: where a level steps
    back two cells and nothing stands on the step's top, curved 3 x 1 slopes instead of 33
    degree ones."""
    fixed = fixed or {}
    bt = Batch()
    nl = max(h.values(), default=0)
    base_cells = set(h) if base_cells is None else set(base_cells)
    bsizes = [s for s in AV.sizes(BRICK, role) if s[1] <= 8]
    below = None
    tops = set()                              # (level, cell) with a stud left on top
    overhung = defaultdict(set)               # level -> cells a slope of the level over hides
    for lv in range(nl):
        y_top = base_y - LV * (lv + 1)
        here = {c for c, n in h.items() if n > lv} - fixed.get(lv, set())
        under = (lambda c: c in base_cells) if lv == 0 else (lambda c: h.get(c, 0) == lv)
        if flat_top and lv == nl - 1:
            under = lambda c: False            # the top level: plain bricks
        used, slopes = set(), []
        # corners first: a cell stepping back both ways, its three neighbours a level lower
        for c in sorted(here):
            ds = [d for d in DIRS if (c[0] + d[0], c[1] + d[1]) not in here
                  and under((c[0] + d[0], c[1] + d[1]))]
            for d1 in ds:
                for d2 in ds:
                    if d1[0] * d2[0] + d1[1] * d2[1] != 0 or d1 >= d2:
                        continue
                    fr = {(c[0] + d1[0], c[1] + d1[1]), (c[0] + d2[0], c[1] + d2[1]),
                          (c[0] + d1[0] + d2[0], c[1] + d1[1] + d2[1])}
                    if c in used or fr & used or not all(under(f) and f not in here for f in fr):
                        continue
                    a, b = (d1, d2) if _corner_ok(d1, d2) else (d2, d1)
                    slopes.append(("corner", c, a, b, 1))
                    used |= {c} | fr
        # straight slopes: one cell back (45) or two (33), runs across the slope merged
        runs = defaultdict(list)
        for c in sorted(here - used):
            for d in DIRS:
                f1 = (c[0] + d[0], c[1] + d[1])
                if f1 in here or f1 in used or not under(f1):
                    continue
                f2 = (f1[0] + d[0], f1[1] + d[1])
                deep = 2 if (f2 not in here and f2 not in used and under(f2)) else 1
                back = (c[0] - d[0], c[1] - d[1])
                runs[(d, deep)].append(c)
                used |= {c, f1} | ({f2} if deep == 2 else set())
                break
        for (d, deep), cells in runs.items():
            across = (abs(d[1]), abs(d[0]))        # unit step across the slope
            cells = sorted(cells, key=lambda c: (c[0] * across[0] + c[1] * across[1]))
            if curved and deep == 2:
                top_here = [c for c in cells if h[c] == lv + 1]
                for c in top_here:                   # curved 3 x 1 slopes, smooth on top
                    x, z = cell_xz(c)
                    bt.add("50950", role, transform((x + d[0] * S, y_top, z + d[1] * S),
                                                    _R_down(d)), cat)
                cells = [c for c in cells if c not in top_here]
            table = SLOPE45 if deep == 1 else SLOPE33
            group = []
            for c in cells + [None]:
                if group and (c is None or (c[0] - group[-1][0], c[1] - group[-1][1]) != across
                              or len(group) == max(table)):
                    _emit_run(bt, group, d, deep, table, y_top, role, cat, tops, lv)
                    group = []
                if c is not None:
                    group.append(c)
        if lv > 0:
            overhung[lv - 1] |= used - here
        for kind, c, a, b, _ in slopes:
            x, z = cell_xz(c)
            bt.add(CORNER45, role, transform((x, y_top, z), _R_down(a)), cat)
            tops.add((lv, c))
        # plain bricks, bonded to the level under them
        cells = here - used
        if cells:
            rects = pack(cells, bsizes, below, prefer="x", shift=lv)
            for i0, i1, k0, k1 in rects:
                part, R = rect_part(BRICK, i1 - i0 + 1, k1 - k0 + 1)
                bt.add(part, role, transform((S * (i0 + i1 + 1) / 2, y_top,
                                              S * (k0 + k1 + 1) / 2), R), cat)
            below = ids_of(rects)
            for c in cells:
                if h[c] == lv + 1:
                    tops.add((lv, c))
        else:
            below = None
    # tiles on the studs left on top
    by_lv = defaultdict(set)
    for lv, c in tops:
        if h.get(c, 0) == lv + 1 and c not in no_tile and c not in overhung[lv]:
            by_lv[lv].add(c)
    tsizes = [s for s in AV.sizes(TILE, role) if s[1] <= 4]
    for lv, cells in by_lv.items():
        y = base_y - LV * (lv + 1) - 8
        for i0, i1, k0, k1 in pack(cells, tsizes, prefer="x"):
            part, R = rect_part(TILE, i1 - i0 + 1, k1 - k0 + 1)
            bt.add(part, role, transform((S * (i0 + i1 + 1) / 2, y, S * (k0 + k1 + 1) / 2), R),
                   cat + "_tiles")
    return bt


def _corner_ok(d1, d2) -> bool:
    """3045 slopes down toward its local -Z and +X: with -Z -> d1, is +X -> d2?"""
    ez = -np.array([d1[0], 0.0, d1[1]])
    ex = np.cross([0.0, 1.0, 0.0], ez)
    return np.allclose(ex, [d2[0], 0.0, d2[1]])


def _emit_run(bt, group, d, deep, table, y_top, role, cat, tops, lv):
    """Slope bricks along a run of back cells (a slope's stud row), widest first."""
    n = 0
    while n < len(group):
        w = max(k for k in table if k <= len(group) - n)
        cs = group[n:n + w]
        xs = [cell_xz(c) for c in cs]
        x = sum(p[0] for p in xs) / w
        z = sum(p[1] for p in xs) / w
        bt.add(table[w], role, transform((x, y_top, z), _R_down(d)), cat)
        for c in cs:
            tops.add((lv, c))
        n += w


# ------------------------------------------------------------------ the wheelhouse
DECK_TOP = shp.DECK_STRIP - 8          # the deck strip's upper plates' top (-168)
# the alligator's head, level by level (bricks over the deck): its front steps back 45 degrees
# from the second level to the peak, its back 33 degrees, its sides narrow 45 degrees
WH_FRONT = (-600, -600, -580, -560, -540)
WH_BACK = (-340, -340, -380, -420, -480)
WH_HW = (80, 80, 80, 60, 40)
EYE_X = -520.0                          # the eyes' middles: on the head's sides
EYE_LV = 2                              # the level of the bricks with side studs they hang on
PEAK = DECK_TOP - LV * len(WH_FRONT)    # the peak's top (-288): the crest stands on it
CREST_SEAT = {(i, k) for i in (-27, -26, -25) for k in (-1, 0)}


def wheelhouse_h() -> dict:
    h = {}
    for i in range(-31, -16):
        for k in range(-4, 4):
            x, z = cell_xz((i, k))
            n = 0
            for lv in range(len(WH_FRONT)):
                if WH_FRONT[lv] <= x - 10 and x + 10 <= WH_BACK[lv] and abs(z) + 10 <= WH_HW[lv]:
                    n = lv + 1
                else:
                    break
            if n:
                h[(i, k)] = n
    return h


def eye_y() -> float:
    """The eyes' middle height: their mounting plates' second row of anti-studs on the side
    studs of level EYE_LV's bricks (10 under the bricks' tops)."""
    return DECK_TOP - LV * (EYE_LV + 1) + 10 - 10


def wheelhouse(model):
    """The wheelhouse: an alligator's head of bricks and slopes on the deck, its two eyes (4 x 4
    clear domes on 4 x 4 plates, on bricks with side studs) bulging from its sides, a
    searchlight on its peak."""
    from naut_kit import side_R
    sub = model.submodel("wheelhouse", "The wheelhouse")
    h = wheelhouse_h()
    ie = [int((EYE_X - 40) // S) + n for n in range(4)]
    eye_cells = {(i, k) for i in ie for k in (-4, 3)}
    bt = slope_stack(h, DECK_TOP, fixed={EYE_LV: eye_cells}, no_tile=CREST_SEAT, flat_top=True,
                     curved=True,
                     base_cells={(i, k) for i in range(-40, -10) for k in range(-4, 4)})
    y_top = DECK_TOP - LV * (EYE_LV + 1)
    for side in (-1, 1):
        R = np.eye(3) if side < 0 else rot(y=180)
        bt.add("30414", "hull", transform((EYE_X, y_top, side * 70), R), "body")
    bt.emit(sub, phases=[["body"], ["body_tiles"]],
            captions={"body": "The wheelhouse: an alligator's head of bricks and slopes",
                      "body_tiles": "Tiles on top"}, per_step=12, reach=200)
    sub.step("The eyes: clear domes on plates, pushed onto the side studs")
    for side in (-1, 1):
        R = side_R(side)
        sub.place("3031", "hull", (EYE_X, eye_y(), side * 88), R, insert=(0, 0, side))
        sub.place("86500", "glass", (EYE_X, eye_y(), side * 88), R, tag="eyes",
                  insert=(0, 0, side))
    return sub


# ------------------------------------------------------------------ the crest
# The crest arch: a thin band one stud wide springing from the wheelhouse's peak and arching
# down to the deck just aft of the bow module's station (naut_shape.BOW_STATION), where the
# bow's ridge carries on to the ram (the photo's arch, squeezed a little along the hull). It
# hangs between its two ends (on jumpers: the band runs on the middle line), open underneath;
# its top is a chain of curved slopes along it (naut_relief.fit_chain) following the photo's
# arch, with spikes: two big ones (a 45 degree slope and a cheese slope) where it runs level
# over the wheelhouse's front, small raked ones (a cheese slope on a plate) down its fall.
CREST_COLS = (-25, -39)          # its columns: on the wheelhouse's peak .. its foot on the deck
CREST_SEAT_I = (-25, -26, -27)   # its seat on the peak (naut_body.CREST_SEAT)
CREST_FOOT_I = (-38, -39)        # its foot on the deck, just aft of the bow module's station
CREST_TEETH = ((-26, True), (-29, True), (-32, False), (-35, False))
CREST_X0 = -509.0                # the photo's arch, from here (its spring) ...
CREST_SQUEEZE = (851.0 - 509.0) / (790.0 - 509.0)   # ... squeezed to land at x -790
CREST_PIECES = (("tile", (0,), 0, 0.10), ("54200", (-1,), -1, 0.15), ("11477", (0, -1), -1, 0.0),
                ("50950", (-1, -2, -2), -2, 0.0), ("big", (0, 0), 0, 0.0),
                ("small", (-1,), -1, 0.0),
                ("54200", (-2,), -2, 0.6))         # (a step and a cheese slope: its fall)
CREST_DEPTH = 2                  # the band: two plates deep under its top


def crest_plan():
    """(columns from the peak forward, each one's top level (y = -8 level), each one's bottom
    level, the top's pieces [(name, first index, columns)])."""
    xs, ys = shp.CREST_ARCH
    cols = list(range(CREST_COLS[0], CREST_COLS[1] - 1, -1))
    seat = round(-PEAK / 8) + 1                       # the jumpers' top on the peak
    foot = round(-(shp.DECK_STRIP - 8) / 8) + 1       # ... on the deck
    t, lb = [], []
    for i in cols:
        x = S * i + S / 2
        xa = CREST_X0 + (x - CREST_X0) * CREST_SQUEEZE
        y = float(np.interp(xa, xs, ys))
        t.append(-y / 8 - 1)
        lb.append(seat + 1 if i in CREST_SEAT_I else (foot + 1 if i in CREST_FOOT_I else 1))
    forced = {cols.index(i): ("big" if big else "small") for i, big in CREST_TEETH}
    levels, pieces = rel_fit(t, lb, CREST_PIECES, range(foot, seat + 8), forced)
    bottoms = []
    for k, (i, l) in enumerate(zip(cols, levels)):
        # deep enough to share a level with the next column forward (where it drops two)
        b = min(l - CREST_DEPTH + 1, levels[k + 1] if k + 1 < len(levels) else l)
        if i in CREST_SEAT_I:
            b = seat + 1
        elif i in CREST_FOOT_I:
            b = foot + 1
        bottoms.append(b)
    return cols, levels, bottoms, pieces


def rel_fit(*a, **k):
    import naut_relief as rel
    return rel.fit_chain(*a, end_w=0.0, **k)


def crest(model):
    """The crest arch (see CREST_COLS), built upside down from its top: the band's plates, its
    top's curved slopes and spikes, the jumpers it stands on at its two ends."""
    sub = model.submodel("crest", "The crest arch")
    bt = Batch()
    cols, levels, bottoms, pieces = crest_plan()
    xc = lambda i: S * i + S / 2
    sizes = [s for s in AV.sizes(PLATE, "spine") if s[0] == 1 and s[1] <= 8]
    lvs = list(range(max(levels), min(bottoms) - 1, -1))
    best = None
    for shift in range(12):           # packed from its top down until it holds together
        out, prev = [], None
        for n, lv in enumerate(lvs):
            cells = {(i, 0) for i, l, b in zip(cols, levels, bottoms) if b <= lv <= l}
            nxt = {(i, 0) for i, l, b in zip(cols, levels, bottoms)
                   if n + 1 < len(lvs) and b <= lvs[n + 1] <= l}
            rects = pack(cells, sizes, prev, prefer="x", shift=lv + shift,
                         above=nxt) if cells else []
            out.append(rects)
            prev = ids_of(rects, start=1000 * lv)
        pieces_n = connected(out)
        if best is None or pieces_n < best[0]:
            best = (pieces_n, out)
        if pieces_n == 1:
            break
    for lv, rects in zip(lvs, best[1]):
        for i0, i1, _, _ in rects:
            part, R = rect_part(PLATE, i1 - i0 + 1, 1)
            bt.add(part, "spine", transform((S * (i0 + i1 + 1) / 2, -8 * lv, 0), R), "crest",
                   insert=(0, 1, 0))
    for name, k0, m in pieces:
        idx = list(range(k0, k0 + m))
        xs = [xc(cols[k]) for k in idx]
        xm = sum(xs) / m
        low = -8 * levels[idx[-1]]
        if name == "tile":
            bt.add("3070b", "spine", transform((xm, low - 8, 0)), "crest_top")
        elif name in ("54200", "11477"):
            bt.add(name, "spine", transform((xm, low, 0), _R_up(+1)), "crest_top")
        elif name == "50950":
            bt.add(name, "spine", transform((xm, low - 24, 0), _R_up(+1)), "crest_top")
        elif name == "big":                     # a 45 degree slope, a cheese slope on its stud
            yt = -8 * levels[idx[0]]
            bt.add("3040", "spine", transform((xs[0], yt - 24, 0), _R_down((-1, 0))), "spikes")
            bt.add("54200", "spine", transform((xs[0], yt - 24, 0), _R_up(+1)), "spikes")
        else:                                   # a cheese slope on a plate: a plate proud
            bt.add("3024", "spine", transform((xs[0], low - 8, 0)), "spikes")
            bt.add("54200", "spine", transform((xs[0], low - 8, 0), _R_up(+1)), "spikes")
    for i, b in zip(cols, bottoms):             # the jumpers it stands on
        if i in CREST_SEAT_I or i in CREST_FOOT_I:
            bt.add("15573", "spine", transform((xc(i), -8 * (b - 1), 0), rot(y=90)), "feet",
                   insert=(0, 1, 0))
    bt.emit(sub, phases=[["crest"], ["crest_top"], ["spikes"], ["feet"]], hanging=("crest",),
            captions={"crest": "The crest arch: a band of plates one stud wide, from its top "
                               "down (built upside down)",
                      "crest_top": "Curved slopes along its top",
                      "spikes": "The spikes",
                      "feet": "Jumpers under its two ends: it stands on the middle line"},
            per_step=12, reach=200)
    return sub


def _R_up(sx: int) -> np.ndarray:
    """A slope rising toward +X (sx = 1) or -X: its high side (local +Z) that way."""
    ez = np.array([sx, 0.0, 0.0])
    ey = np.array([0.0, 1.0, 0.0])
    return orient(np.cross(ey, ez), ey, ez)


# ------------------------------------------------------------------ fins: bands of plates
def profile_band(cols: dict, ks=(-1, 0), role: str = "hull", cat: str = "band",
                 cap: bool = True, hang: bool = False, skip_caps=()) -> Batch:
    """A thin upright shape in the x-y plane (a fin): cols {column i: (top y, bottom y)} filled
    with plates two studs (ks) wide, each plate level packed to bond to the last (`hang`: built
    downward, from the top). Its top smoothed: a curved slope where it climbs a plate a column
    for two columns, a cheese slope where it climbs two plates in one, tiles elsewhere
    (`skip_caps`: columns left bare for something else)."""
    bt = Batch()
    sizes = [s for s in AV.sizes(PLATE, role) if s[1] <= 8]
    ys = sorted({y for t, b in cols.values() for y in range(int(t), int(b), 8)},
                reverse=not hang)          # the first level built first: bond to it
    below = None
    level = lambda y: {(i, k) for i, (t, b) in cols.items() for k in ks if t <= y and y + 8 <= b}
    for n, y in enumerate(ys):
        cells = level(y)
        if not cells:
            continue
        nxt = level(ys[n + 1]) if n + 1 < len(ys) else None
        rects = pack(cells, sizes, below, prefer="x", above=nxt, bridge=True)
        for i0, i1, k0, k1 in rects:
            part, R = rect_part(PLATE, i1 - i0 + 1, k1 - k0 + 1)
            bt.add(part, role, transform((S * (i0 + i1 + 1) / 2, y, S * (k0 + k1 + 1) / 2), R),
                   cat, insert=(0, 1, 0) if hang else None)
        below = ids_of(rects)
    if not cap:
        return bt
    H = {i: -cols[i][0] // 8 for i in cols}             # plates up
    done = set(skip_caps)
    z0 = S * (min(ks) + max(ks) + 1) / 2
    wide = len(ks) == 2
    for i in sorted(cols, key=lambda i: H[i]):
        if i in done:
            continue
        x = S * i + S / 2
        for sx in (1, -1):
            n1, n2 = i + sx, i + 2 * sx
            if H.get(n1, -99) == H[i] + 1 and H.get(n2, -99) == H[i] + 2 and n1 not in done:
                part = "15068" if wide else "11477"
                bt.add(part, role, transform((x + sx * S / 2, cols[i][0], z0), _R_up(sx)),
                       cat + "_top")
                done |= {i, n1}
                break
            if H.get(n1, -99) == H[i] + 2:
                bt.add("85984" if wide else "54200", role,
                       transform((x, cols[i][0], z0), _R_up(sx)), cat + "_top")
                done.add(i)
                break
    flat = defaultdict(set)
    for i in cols:
        if i not in done:
            flat[cols[i][0]] |= {(i, k) for k in ks}
    tsizes = [s for s in AV.sizes(TILE, role) if s[1] <= 4]
    for yt, cells in flat.items():
        for i0, i1, k0, k1 in pack(cells, tsizes, prefer="x"):
            part, R = rect_part(TILE, i1 - i0 + 1, k1 - k0 + 1)
            bt.add(part, role, transform((S * (i0 + i1 + 1) / 2, yt - 8,
                                          S * (k0 + k1 + 1) / 2), R), cat + "_top")
    return bt


def cols_from(top, bot, x0: float, x1: float, q: int = 8) -> dict:
    """Columns from x0 to x1 with top(x), bot(x) (functions of the column's middle), rounded
    to plates; columns where the band would be empty are left out."""
    out = {}
    for i in range(int(np.floor(x0 / S)), int(np.ceil(x1 / S))):
        x = S * i + S / 2
        t, b = q * round(top(x) / q), q * round(bot(x) / q)
        if b - t >= q:
            out[i] = (t, b)
    return out


# ------------------------------------------------------------------ the dorsal fin
DORSAL_X = (60, 280)          # the dorsal fin's columns on the deck (naut_shape.AFT_FIN)
DORSAL_SPIKES = (2, 5, 8)     # its columns with a spike (a claw) up its leading edge


def dorsal_fin(model):
    """The shark's dorsal fin on the deck abaft the salon (naut_shape.AFT_FIN), built sideways
    like a LEGO set's fin (naut_fin): its leading edge sweeps up aft from a short toe at 1:3
    (wedge plates 6 x 3 and 3 x 2) to the peak, its trailing edge falls 1:4 to the deck (a
    wedge plate 4 x 2 on end); both faces tiled; claws up the leading edge for its spikes. It
    stands on jumpers on a plinth of plates four studs wide on the deck, the plinth tiled round
    them."""
    import naut_fin as nf
    sub = model.submodel("dorsal_fin", "The dorsal fin")
    x0, x1 = DORSAL_X
    i0, i1 = x0 // S, x1 // S
    fin = nf.Fin(x0, DECK_TOP - 16)                 # on jumpers on the plinth
    fin.wedge("54383", 1, 0, 0)                     # the leading edge: 1:3, three rows up
    fin.wedge("43722", 1, 6, 2)
    fin.wedge("41769", 2, 9, 0)                     # the trailing edge: 1:4 down to the deck
    fin.plate(6, 0, 3, 2)
    fb = fin.build(range(0, i1 - i0), spikes=DORSAL_SPIKES)
    core_cols = {c for c, _ in fin.core_cells}
    bt = Batch()
    cells = {(i, k) for i in range(i0, i1) for k in (-2, -1, 0, 1)}
    for a, b, k0, k1 in pack(cells, [s for s in AV.sizes(PLATE, "hull") if s[1] <= 8],
                             prefer="x"):
        part, R = rect_part(PLATE, b - a + 1, k1 - k0 + 1)
        bt.add(part, "hull", transform((S * (a + b + 1) / 2, DECK_TOP - 8,
                                        S * (k0 + k1 + 1) / 2), R), "plinth")
    jump = {(i0 + c, k) for c in core_cols for k in (-1, 0)}
    for c in sorted(core_cols):
        bt.add("15573", "hull", transform((x0 + S * c + S / 2, DECK_TOP - 16, 0), rot(y=90)),
               "jumpers")
    tsz = [s for s in AV.sizes(TILE, "hull") if s[0] == 1 and s[1] <= 8]
    for a, b, k0, k1 in pack(cells - jump, tsz, prefer="x"):
        part, R = rect_part(TILE, b - a + 1, k1 - k0 + 1)
        bt.add(part, "hull", transform((S * (a + b + 1) / 2, DECK_TOP - 16,
                                        S * (k0 + k1 + 1) / 2), R), "plinth_tiles")
    bt.items += fb.items
    if fin.unheld:
        print(f"warning: dorsal fin: face parts {fin.unheld} not held")
    bt.emit(sub, phases=[["plinth"], ["jumpers", "plinth_tiles"], ["fin_core"],
                         ["fin_core_tiles"], ["fin_spikes"], ["fin_port"], ["fin_stbd"],
                         ["fin_tiles"]],
            captions={"plinth": "The dorsal fin: a plinth of plates on the deck",
                      "jumpers": "Jumpers for its core, tiles round them",
                      "fin_core": "The fin's core: bricks with studs on both sides, plates",
                      "fin_spikes": "Spikes up its leading edge: claws in round plates",
                      "fin_port": "Its port face: wedge plates and plates on the side studs",
                      "fin_stbd": "Its starboard face",
                      "fin_tiles": "Tiles on both faces"}, per_step=10, reach=200)
    return sub


# ------------------------------------------------------------------ the bow's ridge
# The bow's ridge: from the deck's front end down to the ram, a spine two studs wide on the
# core's top, following the traced top line: plates, curved slopes along it (naut_relief's
# chain of slopes, two studs wide), and spikes, the crest's teeth running on down to the ram:
# (the column of a spike's back, big or small).
RIDGE_COLS = (-45, -60)          # its columns, from the deck's front end to the ram
RIDGE_TEETH = ((-47, True), (-51, False), (-54, False), (-57, False))
# pieces (see naut_relief.fit_chain): two-stud-wide tiles, cheese slopes, curved slopes, spikes
RIDGE_TEETH_PIECES = (("big", (0, 0), 0, 0.0), ("small", (-1,), -1, 0.0))


def ridge_plan():
    """(columns from the deck's end outward, their top levels (plates: y = -8 level), the
    core's top level under each, the pieces [(name, first index, columns)])."""
    import naut_relief as rel
    cols = list(range(RIDGE_COLS[0], RIDGE_COLS[1] - 1, -1))
    deck_top = round(-(shp.DECK_STRIP - 16) / 8)
    t, lb = [], []
    for i in cols:
        x = S * i + S / 2
        lb.append(round(-rel.core_top(x) / 8))
        t.append(max(-shp.top(x) / 8 - 1, lb[-1]))
    t[0] = deck_top - 1                     # level with the deck where it starts
    forced = {cols.index(i): ("big" if big else "small") for i, big in RIDGE_TEETH}
    levels, pieces = rel.fit_chain(t, lb, BAND2 + RIDGE_TEETH_PIECES,
                                   range(min(lb), deck_top + 1), forced=forced, end_w=0.0)
    return cols, levels, lb, pieces


def ridge_cells() -> set:
    """The core's top studs the ridge stands on (i, k)."""
    return {(i, k) for i in range(RIDGE_COLS[1], RIDGE_COLS[0] + 1) for k in (-1, 0)}


def bow_ridge() -> Batch:
    """The bow's ridge (see RIDGE_COLS), built in place on the core's top (in the hull's frame):
    plates up from the core's top, a chain of curved slopes along it, spikes (a 45 degree slope
    and a cheese slope on two jumpers, or a cheese slope on a jumper, standing a plate proud of
    the chain)."""
    cols, levels, base, pieces = ridge_plan()
    return chain_band(cols, levels, base, pieces, d=+1, cat="ridge")


# Two-stud-wide pieces for chain_band (see naut_relief.fit_chain): tiles, cheese slopes and
# curved slopes.
BAND2 = (("tile", (0,), 0, 0.10), ("85984", (-1,), -1, 0.15), ("15068", (0, -1), -1, 0.0),
         ("50950", (-1, -2, -2), -2, 0.0), ("93606", (0, -1, -2, -2), -2, 0.0))


def chain_band(cols, levels, base, pieces, d: int = 1, role: str = "hull", cat: str = "band",
               skip=(), z0: float = 0.0) -> Batch:
    """An upright band two studs wide (z0 its middle) whose top is a chain of slopes: columns
    `cols` from the chain's high end outward, `levels` their tops (y = -8 level), `base` the
    level each stands on (its plates from base + 1 up), `pieces` from fit_chain; the high end
    toward +x (d = 1) or -x. `skip`: (column, level) left for something else. Parts in `cat`
    (plates) and cat + "_top" (the slopes)."""
    bt = Batch()
    sizes = [s for s in AV.sizes(PLATE, role) if s[0] <= 2 and s[1] <= 8]
    ks = (-1, 0)
    below = None
    for lv in range(min(base) + 1, max(levels) + 1):
        cells = {(i, k) for i, l, b in zip(cols, levels, base) if b < lv <= l
                 and (i, lv) not in skip for k in ks}
        if not cells:
            continue
        rects = pack(cells, sizes, below, prefer="x", shift=lv)
        for i0, i1, k0, k1 in rects:
            part, R = rect_part(PLATE, i1 - i0 + 1, k1 - k0 + 1)
            bt.add(part, role, transform((S * (i0 + i1 + 1) / 2, -8 * lv,
                                          z0 + S * (k0 + k1 + 1) / 2), R), cat)
        below = ids_of(rects, start=1000 * lv)
    xc = lambda i: S * i + S / 2
    top = cat + "_top"
    for name, k0, m in pieces:
        idx = list(range(k0, k0 + m))
        xs = [xc(cols[k]) for k in idx]
        xm = sum(xs) / m
        low = -8 * levels[idx[-1]]                 # the low (outer) end's top
        if name == "tile":
            bt.add("3069b", role, transform((xm, low - 8, z0), rot(y=90)), top)
        elif name in ("85984", "15068"):
            bt.add(name, role, transform((xm, low, z0), _R_up(d)), top)
        elif name == "50950":
            for z in (-10, 10):
                bt.add(name, role, transform((xm, low - 24, z0 + z), _R_up(d)), top)
        elif name == "93606":
            bt.add(name, role, transform((xm, low - 24, z0), _R_up(d)), top)
        else:                                       # a spike on two jumpers
            yt = -8 * levels[idx[0]]
            for x in xs:
                bt.add("15573", "spine", transform((x, yt - 8, z0), rot(y=90)), top)
            if name == "big":
                bt.add("3040", "spine", transform((xs[0], yt - 32, z0), _R_down((-d, 0))), top)
                bt.add("54200", "spine", transform((xs[0], yt - 32, z0), _R_up(d)), top)
            else:                           # a cheese slope on the jumper: a step taller
                bt.add("54200", "spine", transform((xs[0], yt - 8, z0), _R_up(d)), top)
    return bt


# Under a band (keel_band): plain plates' undersides, a pair of inverted curved slopes under a
# step a plate deep over two columns, or a plain step.
UNDER2 = (("flat", (0,), 0, 0.10), ("24201", (0, -1), -1, 0.0), ("drop", (-1,), -1, 0.5))


def keel_band(cols, depths, base, pieces, d: int = 1, role: str = "hull", cat: str = "keel",
              z0: float = 0.0) -> Batch:
    """chain_band upside down, hanging under the core: columns `cols` from the deep end outward,
    `depths` their undersides (y = 8 depth), `base` the level each hangs from (its plates from
    there down), `pieces` from fit_chain (UNDER2); the deep end toward +x (d = 1) or -x. Its
    plates go in from below, pushed up one under another (category `cat`), the inverted curved
    slopes under them (cat + "_under")."""
    bt = Batch()
    sizes = [s for s in AV.sizes(PLATE, role) if s[0] <= 2 and s[1] <= 8]
    above = None
    for lv in range(min(base) + 1, max(depths) + 1):
        cells = {(i, k) for i, l, b in zip(cols, depths, base) if b < lv <= l for k in (-1, 0)}
        if not cells:
            continue
        rects = pack(cells, sizes, above, prefer="x", shift=lv)
        for i0, i1, k0, k1 in rects:
            part, R = rect_part(PLATE, i1 - i0 + 1, k1 - k0 + 1)
            bt.add(part, role, transform((S * (i0 + i1 + 1) / 2, 8 * (lv - 1),
                                          z0 + S * (k0 + k1 + 1) / 2), R), cat,
                   insert=(0, 1, 0))
        above = ids_of(rects, start=1000 * lv)
    for name, k0, m in pieces:
        if name != "24201":
            continue
        i_low = cols[k0 + 1]                       # the shallower column, outward
        for z in (-10, 10):
            bt.add("24201", role, transform((S * i_low + S / 2, 8 * depths[k0 + 1], z0 + z),
                                            _R_up(d)), cat + "_under", insert=(0, 1, 0))
    return bt


RIDGE_CAPTIONS = {"ridge": "The bow's ridge: plates on the core's top",
                  "ridge_top": "Curved slopes along it, and spikes"}
