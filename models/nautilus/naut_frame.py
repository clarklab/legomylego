"""The Nautilus's side keels and deck strip.

* **Side keels**: a flange two plates thick at the waterline, a lens in plan: ten studs across
  at the salon windows, tapering 1:6 (12 x 3 wedge plates) then 1:4 (4 x 2 wedge plates) to
  two studs at the bow tip and at the tail stock. The lower layer is narrower, stepping in
  under the wedges, so the edge reads as a thin keel line. At each salon window they are cut
  back under the window's frame and round the lamp behind it, and the core's cells are left
  out where the lamps' leads go down. They are the hull's base: a sub-assembly that holds
  together by itself (the layouts are tried until it does).
* **Deck strip**: plain plates on the core's top (no wedge plates' stud notches on show).

Hull frame (naut_shape): the side keels are centred on y = 0, the bow toward -X, the port side
toward -Z. Cells: column i is x in [20 i, 20 i + 20], row k is z in [20 k, 20 k + 20]."""
from __future__ import annotations

import naut_shape as shp
from brickkit.ldraw.matrix import rot, transform
from naut_kit import AV, PLATE, S, Batch, cells_of, components, ids_of, pack, rect_part

TAIL_STOCK = 480.0        # the side keels' layers run on, two studs wide, to here
WEDGE = {  # kind -> (part narrowing toward -X on the port side, its starboard twin, width)
    "12x3": ("47397", "47398", 60), "6x2": ("78443", "78444", 40), "4x2": ("41770", "41769", 40)}
MID = shp.WIDE            # amidships: the deck four studs wide
DECK_HW = 40.0
# the deck: four studs wide from under the wheelhouse to the dorsal fin, two wide on to the
# bow's ridge and the raised aft deck
DECK = (("rect", MID[0] - 120, MID[1] + 120, DECK_HW),
        ("rect", shp.PROW_X, MID[0] - 120, 20),
        ("rect", MID[1] + 120, 300, 20))


def rect_M(i0, i1, k0, k1, top):
    return (S * (i0 + i1 + 1) / 2, top, S * (k0 + k1 + 1) / 2)


def add_rects(bt, rects, top, role, cat, table=PLATE):
    for i0, i1, k0, k1 in rects:
        part, R = rect_part(table, i1 - i0 + 1, k1 - k0 + 1)
        bt.add(part, role, transform(rect_M(i0, i1, k0, k1, top), R), cat)


def fill(bt, cells, top, role, cat, below=None, shift=0, prefer="x", maxlen=12, table=PLATE):
    sizes = [s for s in AV.sizes(table, role) if s[1] <= maxlen]
    rects = pack(cells, sizes, below, prefer=prefer, shift=shift)
    add_rects(bt, rects, top, role, cat, table)
    return rects


def cells_x(x0, x1):
    return range(int(round(min(x0, x1) / S)), int(round(max(x0, x1) / S)))


def rows_within(hw):
    """Rows k whose cells lie within |z| <= hw."""
    n = int(max(hw, 0) // S)
    return range(-n, n)


def lens_layer(bt, top, pieces, role, cat, below=None, shift=0, prefer="x"):
    """One plate layer whose outline is made of pieces, symmetric about the middle line:
    ("rect", x0, x1, hw) - |z| < hw from x0 to x1, in plates;
    ("wedge", x_wide, x_narrow, hw, kind) - a pair of wedge plates, full width at x_wide
    (out to |z| = hw), narrowing 1:N toward x_narrow; plates fill in between them.
    Returns the plates' rectangles (for bonding the next layer)."""
    cells = set()
    for pc in pieces:
        if pc[0] == "rect":
            _, x0, x1, hw = pc
            cells |= {(i, k) for i in cells_x(x0, x1) for k in rows_within(hw)}
        else:
            _, xw, xn, hw, kind = pc
            w = WEDGE[kind][2]
            d = 1 if xn > xw else -1
            for side in (-1, 1):
                wedge(bt, min(xw, xn), max(xw, xn), hw, kind, d, side, top, role, cat)
            cells |= {(i, k) for i in cells_x(xw, xn) for k in rows_within(hw - w)}
    if not cells:
        return []
    return fill(bt, cells, top, role, cat, below, shift, prefer)


# ------------------------------------------------------------------ side keels
def segments():
    """Taper segments [(x0, x1, hw at the wide end, kind, d)] with x0 < x1; d = -1 if the
    segment narrows toward the bow."""
    out = []
    for xw, xn, hw, kind in shp.TAPERS:
        out.append((min(xw, xn), max(xw, xn), hw, kind, 1 if xn > xw else -1))
    return out


def wedge(bt, x0, x1, hw, kind, d, side, top, role, cat):
    """A wedge plate on a tapering edge, its full width at the segment's wide end (|z| from
    hw - width to hw), narrowing toward the bow (d = -1) or the stern (d = 1)."""
    left, right, w = WEDGE[kind]
    if d < 0:
        part, R = (left if side < 0 else right), rot(y=90)
    else:
        part, R = (right if side < 0 else left), rot(y=-90)
    bt.add(part, role, transform(((x0 + x1) / 2, top, side * (hw - w / 2)), R), cat)


def keel_plan(lower: bool):
    """The cells of one layer of the side keels (less the salon windows' cuts) and, for the
    upper layer, its wedge plates [(x0, x1, hw, kind, d, side)]. The upper layer has the full
    outline (wedge plates on the tapers); the lower one steps in under each wedge so the
    wedge's full column sits on it."""
    cells, wedges = set(), []
    for i in cells_x(*shp.WIDE):
        cells |= {(i, k) for k in rows_within(shp.FLANGE_HW - (20 if lower else 0))}
    for x0, x1, hw, kind, d in segments():
        w = WEDGE[kind][2]
        if lower:           # under the wedge's full (straight) column
            cells |= {(i, k) for i in cells_x(x0, x1)
                      for k in rows_within(hw - (40 if kind == "12x3" else 20))}
            continue
        wedges += [(x0, x1, hw, kind, d, side) for side in (-1, 1)]
        cells |= {(i, k) for i in cells_x(x0, x1) for k in rows_within(hw - w)}
    for i in cells_x(shp.STERN_X, TAIL_STOCK):       # the tail stock's root, two studs wide
        cells |= {(i, -1), (i, 0)}
    return {c for c in cells if not salon_cut(*c)}, wedges


def wedge_cells(x0, x1, hw, kind, d, side) -> set:
    """The cells under a wedge plate's full (inner) column: where it sits on the lower layer."""
    w = WEDGE[kind][2]
    zi = hw - w                                     # its inner edge
    k = int(round(side * zi / S)) + (0 if side > 0 else -1)
    return {(i, k) for i in cells_x(x0, x1)}


def salon_cut(i, k) -> bool:
    """Side keel cells cut away at the salon windows: under the window's frame (beyond
    |z| = 60), round the lamp behind it (beyond 40), and the core's two cells where the leads
    go down the core (the side keels hold together round it)."""
    x = S * i + S / 2
    zmax = max(abs(S * k), abs(S * k + S))
    for (x0, x1), lim in ((shp.SALON_NOTCH, 60), (shp.LAMP_X, 40)):
        if x0 <= x < x1 and zmax > lim:
            return True
    return shp.SHAFT_X[0] <= x < shp.SHAFT_X[1] and zmax <= 20     # the core's cells


def build_frame(model):
    """The side keels (the pointed lens at the waterline): a sub-assembly two plates thick,
    the hull's base. The upper layer is laid out first (wedge plates and long plates); the
    lower layer is packed to join its pieces, trying a few layouts until the two layers hold
    together as one piece."""
    sub = model.submodel("side_keels", "Side keels")
    cells_a, wedges = keel_plan(lower=False)
    cells_b, _ = keel_plan(lower=True)
    sizes = [s for s in AV.sizes(PLATE, "hull") if s[1] <= 12]
    # the lower layer's bridges: a 2 x 4 plate across each join between stretches (each
    # taper, the stock's root)
    bridges = []
    for b in sorted({x for seg in segments() for x in seg[:2]} | {TAIL_STOCK}):
        i0 = int(round(b / S)) - 2
        box = {(i, k) for i in range(i0, i0 + 4) for k in (-1, 0)}
        if box <= cells_b and not any(box & cells_of(r) for r in bridges):
            bridges.append((i0, i0 + 3, -1, 0))
    rest_b = cells_b - {c for r in bridges for c in cells_of(r)}
    best = None
    for order in ("a_first", "b_first"):
        for pa, pb in (("x", "z"), ("x", "x"), ("z", "z"), ("z", "x")):
            for shift in range(0, 24, 3):
                bt = Batch()
                for w in wedges:
                    wedge(bt, w[0], w[1], w[2], w[3], w[4], w[5], shp.FL_A, "hull", "keel")
                if order == "a_first":        # the lower layer packed to join the upper's
                    groups = {c: n for n, w in enumerate(wedges) for c in wedge_cells(*w)}
                    ra = pack(cells_a, sizes, prefer=pa, shift=shift)
                    groups.update(ids_of(ra, start=len(wedges)))
                    rb = bridges + pack(rest_b, sizes, groups, prefer=pb, shift=shift + 1)
                else:                         # the upper layer packed to join the lower's
                    rb = bridges + pack(rest_b, sizes, prefer=pb, shift=shift + 1)
                    groups = ids_of(rb)
                    for w in wedges:          # a wedge joins what is under it already
                        under = {groups[c] for c in wedge_cells(*w) if c in groups}
                        if len(under) > 1:
                            g0 = min(under)
                            groups = {c: (g0 if g in under else g) for c, g in groups.items()}
                    ra = pack(cells_a, sizes, groups, prefer=pa, shift=shift)
                rb = _join_up(rb, ra, wedges, sizes)
                add_rects(bt, ra, shp.FL_A, "hull", "keel")
                add_rects(bt, rb, shp.FL_B, "hull", "keel")
                n = len(components(bt.parts()))
                if best is None or n < best[0]:
                    best = (n, bt)
                if n == 1:
                    break
            if best[0] == 1:
                break
        if best[0] == 1:
            break
    best[1].emit(sub, phases=[["keel"]],
                 captions={"keel": "The side keels: wedge plates make the taper"},
                 per_step=10, reach=200)
    return sub


def _pieces(rb, ra, wedges):
    """Which piece each lower-layer rectangle ends up in (they join through the upper layer's
    rectangles and wedges over them)."""
    parent = {}

    def root(a):
        parent.setdefault(a, a)
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    tops = [cells_of(r) for r in ra] + [wedge_cells(*w) for w in wedges]
    for n, r in enumerate(rb):
        root(n)
        cr = cells_of(r)
        for t, ct in enumerate(tops):
            if cr & ct:
                parent[root(n)] = root(("top", t))
    return [root(n) for n in range(len(rb))]


def _join_up(rb, ra, wedges, sizes, tries=30):
    """Repair the lower layer where it leaves pieces apart: merge a rectangle of a stray piece
    with a neighbour of another piece into one plate across their join (the rest of the two
    re-packed), until it holds together or nothing more helps."""
    ok = {(a, b) for a, b in sizes} | {(b, a) for a, b in sizes}
    rb = list(rb)
    for _ in range(tries):
        piece = _pieces(rb, ra, wedges)
        if len(set(piece)) == 1:
            return rb
        main = max(set(piece), key=piece.count)
        done = False
        for n, r in enumerate(rb):
            if piece[n] == main or done:
                continue
            for m, q in enumerate(rb):
                if piece[m] == piece[n] or done:
                    continue
                cr, cq = cells_of(r), cells_of(q)
                if not any((i + di, k + dk) in cq for i, k in cr
                           for di, dk in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    continue
                u = cr | cq
                i_s = sorted({c[0] for c in u})
                k_s = sorted({c[1] for c in u})
                for i0 in i_s:
                    for i1 in i_s:
                        for k0 in k_s:
                            for k1 in k_s:
                                if done or i1 < i0 or k1 < k0:
                                    continue
                                if (i1 - i0 + 1, k1 - k0 + 1) not in ok:
                                    continue
                                t = (i0, i1, k0, k1)
                                ct = cells_of(t)
                                if not (ct <= u and ct & cr and ct & cq):
                                    continue
                                rest = pack(u - ct, sizes) if u - ct else []
                                trial = [x for j, x in enumerate(rb) if j not in (n, m)]
                                trial += [t] + rest
                                if len(set(_pieces(trial, ra, wedges))) < len(set(piece)):
                                    rb, done = trial, True
        if not done:
            return rb
    return rb


def deck_batch() -> Batch:
    """The deck strip on the core's top: plates, built on the hull."""
    bd = Batch()
    lens_layer(bd, shp.DECK_STRIP, DECK, "hull", "deck", prefer="z")
    return bd


def deck_hw(x: float) -> float:
    for pc in DECK:
        if pc[0] == "rect":
            if min(pc[1], pc[2]) <= x <= max(pc[1], pc[2]):
                return pc[3]
        else:
            _, xw, xn, hw, kind = pc
            if min(xw, xn) <= x <= max(xw, xn):
                return hw - abs(x - xw) * shp.SLOPE.get(kind, 1 / 6)
    return 0.0
