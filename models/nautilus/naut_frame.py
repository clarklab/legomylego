"""The Nautilus's side keels, deck strip and keel strip.

* **Side keels**: a flange two plates thick at the waterline, a lens in plan: 24 studs across
  along the midbody, tapering 1:6, 1:4 then 1:3 (wedge plates) to six studs at the bow tip and
  at the tail stock. The lower layer is narrower, stepping in under the wedges, so the edge
  reads as a thin keel line. Inside the salon the flange is cut back to a ring round the room;
  along each salon window's boss it is cut back behind the boss. They are the hull's base: a
  sub-assembly that holds together by itself (the layouts are tried until it does).
* **Bars for the midbody's panels** (naut_panels): plates with a bar on the end on the side
  keels (over and under them), in the deck strip's upper layer and the keel strip's lower one.
* **Deck strip**: plates on the core and bulkheads, eight studs wide amidships.
* **Keel strip**: plates under them, six studs wide.

Hull frame (naut_shape): the side keels are centred on y = 0, the bow toward -X, the port side
toward -Z. Cells: column i is x in [20 i, 20 i + 20], row k is z in [20 k, 20 k + 20]."""
from __future__ import annotations

import naut_shape as shp
from brickkit.ldraw.matrix import rot, transform
from naut_kit import (AV, PLATE, S, Batch, cells_of, components, connected, ids_of, orient, pack,
                      rect_part)

# kind -> (part narrowing toward -X on the port side, its starboard twin, width, drop per plate)
WEDGE = {"12x3": ("47397", "47398", 60, 40), "4x2": ("41770", "41769", 40, 20),
         "6x3": ("54384", "54383", 60, 40)}
SALON_RING = 140          # inside the salon the side keels keep only |z| >= this (a ring)
WINDOW_CUT = shp.WINDOW_Z - 14   # along the windows' bosses they are cut back to |z| <= this
TAIL_STUB = 1180          # the side keels run on two studs wide under the tail stock to here
RAM_TIP = -1300           # and on past the bow tip as the ram, to here


def rect_M(i0, i1, k0, k1, top):
    return (S * (i0 + i1 + 1) / 2, top, S * (k0 + k1 + 1) / 2)


def add_rects(bt, rects, top, role, cat, table=PLATE, insert=None):
    for i0, i1, k0, k1 in rects:
        part, R = rect_part(table, i1 - i0 + 1, k1 - k0 + 1)
        bt.add(part, role, transform(rect_M(i0, i1, k0, k1, top), R), cat, insert=insert)


def cells_x(x0, x1):
    return range(int(round(min(x0, x1) / S)), int(round(max(x0, x1) / S)))


def rows_within(hw):
    """Rows k whose cells lie within |z| <= hw."""
    n = int(max(hw, 0) // S)
    return range(-n, n)


# ------------------------------------------------------------------ side keels
def segments():
    """One wedge plate's length of each taper: [(x0, x1, hw at the wide end, kind, d)] with
    x0 < x1; d = -1 if the segment narrows toward the bow."""
    out = []
    for xw, xn, hw, kind in shp.TAPERS:
        d = 1 if xn > xw else -1
        n = int(round(abs(xn - xw) / shp.WEDGE_LEN[kind]))
        for j in range(n):
            a = xw + d * j * shp.WEDGE_LEN[kind]
            b = a + d * shp.WEDGE_LEN[kind]
            out.append((min(a, b), max(a, b), hw - j * WEDGE[kind][3], kind, d))
    return out


def wedge(bt, x0, x1, hw, kind, d, side, top, role, cat):
    """A wedge plate on a tapering edge, its full width at its wide end (|z| from hw - width
    to hw), narrowing toward the bow (d = -1) or the stern (d = 1)."""
    left, right, w, _ = WEDGE[kind]
    if d < 0:
        part, R = (left if side < 0 else right), rot(y=90)
    else:
        part, R = (right if side < 0 else left), rot(y=-90)
    bt.add(part, role, transform(((x0 + x1) / 2, top, side * (hw - w / 2)), R), cat)


def salon_cut(i, k) -> bool:
    """Side keel cells left out: inside the salon (a ring round the room stays) and under the
    salon windows' bubbles."""
    x = S * i + S / 2
    zmin = min(abs(S * k), abs(S * k + S))
    zmax = max(abs(S * k), abs(S * k + S))
    if shp.SALON_BAY[0] <= x < shp.SALON_BAY[1] and zmax <= SALON_RING:
        return True
    cx = shp.SALON_C[0]
    if abs(x - cx) < 60 and zmin >= SALON_RING:      # open behind the window's bubble
        return True
    return shp.BOSS_X[0] <= x < shp.BOSS_X[1] and zmin >= WINDOW_CUT


def keel_plan(lower: bool):
    """The cells of one layer of the side keels and, for the upper layer, its wedge plates
    [(x0, x1, hw, kind, d, side)]. The upper layer has the full outline (wedge plates on the
    tapers); the lower one steps in under each wedge so the wedge's full column sits on it."""
    cells, wedges = set(), []
    for i in cells_x(*shp.WIDE):
        cells |= {(i, k) for k in rows_within(shp.FLANGE_HW - (20 if lower else 0))}
    for x0, x1, hw, kind, d in segments():
        w = WEDGE[kind][2]
        if lower:           # under the wedge's full (straight) column
            cells |= {(i, k) for i in cells_x(x0, x1) for k in rows_within(hw - w + 20)}
            continue
        wedges += [(x0, x1, hw, kind, d, side) for side in (-1, 1)]
        cells |= {(i, k) for i in cells_x(x0, x1) for k in rows_within(hw - w)}
    for i in cells_x(shp.STERN_X, TAIL_STUB):     # the tail stock's stub, two studs wide
        cells |= {(i, -1), (i, 0)}
    for i in cells_x(RAM_TIP, shp.BOW_TIP_X):     # and the ram, two studs wide
        cells |= {(i, -1), (i, 0)}
    # (only between the bow and tail modules' stations, when they are there)
    wedges = [w for w in wedges if shp.in_hull((w[0] + w[1]) / 2)]
    return {c for c in cells if not salon_cut(*c) and shp.in_hull(S * c[0] + S / 2)}, wedges


def wedge_cells(x0, x1, hw, kind, d, side) -> set:
    """The cells under a wedge plate's full (inner) column: where it sits on the lower layer."""
    w = WEDGE[kind][2]
    zi = hw - w
    k = int(round(side * zi / S)) + (0 if side > 0 else -1)
    return {(i, k) for i in cells_x(x0, x1)}


def build_frame(model) -> list:
    """The side keels: two sub-assemblies (the salon's windows cut them in two), each two
    plates thick and one piece by itself. The lower layer is laid out first; the upper layer
    (wedge plates and long plates) is packed to bridge every seam of it, trying a few layouts
    until the two layers hold together."""
    cells_a, wedges = keel_plan(lower=False)
    cells_b, _ = keel_plan(lower=True)
    cx = shp.SALON_C[0]
    out = []
    for name, title, keep in (("side_keels_fore", "Side keels, forward", lambda x: x < cx),
                              ("side_keels_aft", "Side keels, aft", lambda x: x >= cx)):
        ca = {c for c in cells_a if keep(S * c[0] + S / 2)}
        cb = {c for c in cells_b if keep(S * c[0] + S / 2)}
        ws = [w for w in wedges if keep((w[0] + w[1]) / 2)]
        sub = model.submodel(name, title)
        _keel_layers(ca, cb, ws).emit(sub, phases=[["keel"]],
                                      captions={"keel": "The side keels: wedge plates make "
                                                        "the taper"}, per_step=12, reach=300)
        out.append(sub)
    return out


def _keel_layers(cells_a, cells_b, wedges) -> Batch:
    sizes = [s for s in AV.sizes(PLATE, "hull") if s[1] <= 12]
    wide = [s for s in sizes if s[0] >= 2 or s[1] <= 2]   # long plates: two studs wide or more
    best = None
    for pa, pb in (("x", "z"), ("z", "z"), ("x", "x"), ("z", "x")):
        for shift in range(0, 12, 3):
            bt = Batch()
            for w in wedges:
                wedge(bt, *w, shp.FL_A, "hull", "keel")
            rb = pack(cells_b, sizes, prefer=pb, shift=shift + 1)
            # the upper layer's edge, where the lower layer stops short: plates two studs wide
            # along it first, so each reaches over the lower layer
            ring = {c for c in cells_a if c not in cells_b}
            strip = ring | {(i, k + (1 if k < 0 else -1)) for i, k in ring} & cells_a
            two = [s for s in sizes if s[0] == 2] + [(1, 1), (1, 2)]
            ra = pack(strip, two, ids_of(rb), prefer="x", shift=shift)
            ra += pack(cells_a - strip, wide, ids_of(rb), prefer=pa, shift=shift, bridge=True)
            if len(set(_pieces(rb, ra, wedges))) > 1:
                rb = _join_up(rb, ra, wedges, sizes)
            add_rects(bt, ra, shp.FL_A, "hull", "keel")
            add_rects(bt, rb, shp.FL_B, "hull", "keel")
            n = len(components(bt.parts()))
            if best is None or n < best[0]:
                best = (n, bt)
            if n == 1:
                return bt
    return best[1]


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


# ------------------------------------------------------------------ deck and keel strips
def deck_cells():
    return {(i, k) for i in cells_x(-1200, 1000) for k in rows_within(shp.deck_hw(S * i + 10))
            if shp.in_hull(S * i + 10)}


def bar_M(x: float, top: float, w: float, side: int):
    """A 1 x 2 plate with a bar on the end (60478), its plate's middle at |z| w, its top at y top,
    the bar pointing outward (30 LDU out from the middle, 2 under the top)."""
    return transform((x, top, side * w), orient((0, 0, side), (0, 1, 0)))


def bar_cells(x: float, w: float, side: int) -> set:
    i = int((x - 10) // S)
    k0 = int(round(side * w / S - 1))
    return {(i, k0), (i, k0 + 1)}


def chain_bars() -> Batch:
    """The bars on the side keels that the midbody's panels clip onto: one over them for the
    upper panels, one hanging under them (on a plate) for the lower ones, at each hinge."""
    import naut_panels as pn
    bt = Batch()
    B, B2 = pn.FACETS["a"].P, pn.FACETS["c"].P
    for side in (-1, 1):
        for x in pn.frame_stations("a"):     # on two plates: the clip clears the tiles
            for n in (1, 2):
                bt.add("3023", "hull", transform((x, shp.FL_A - 8 * n, side * (B[0] - 30)),
                                                 rot(y=90)), "bars")
            bt.add(pn.BAR, "hull", bar_M(x, shp.FL_A - 24, B[0] - 30, side), "bars")
        for x in pn.frame_stations("c"):
            bt.add("3023", "hull", transform((x, shp.FL_B + 8, side * (B2[0] - 30)), rot(y=90)),
                   "bars_lo", insert=(0, 1, 0))
            bt.add(pn.BAR, "hull", bar_M(x, shp.FL_B + 16, B2[0] - 30, side), "bars_lo",
                   insert=(0, 1, 0))
    return bt


def chine_rail() -> Batch:
    """A rail along the midbody's chine: a row of plates on the side keels' outermost studs (tiles
    go on it with the rest), so seen from the side it hides the slot between the side keels and
    the upper panels' lower edges, up to the windows' bosses (the salon's gull wing lifts away
    from it as it opens)."""
    bt = Batch()
    sizes = [s for s in AV.sizes(PLATE, "hull") if s[0] == 1 and s[1] <= 8]
    n = int(shp.FLANGE_HW // S)
    for side, k in ((-1, -n), (1, n - 1)):
        cells = set()
        for i in cells_x(*shp.WIDE):
            x = S * i + S / 2
            if shp.BOSS_X[0] <= x < shp.BOSS_X[1]:
                continue
            cells.add((i, k))
        add_rects(bt, pack(cells, sizes, prefer="x"), shp.FL_A - 8, "hull", "rail")
    return bt


def aft_deck_wedges() -> list:
    """The narrowing deck's edge (naut_shape.AFT_DECK_EDGE): a wedge plate K x 2 each side in
    every K columns, in the upper layer, its full row on the lower layer, its triangle outside
    it: [(part, M, cells of its full row)]."""
    if not (shp.QUARTERS_MODULE and shp.AFT_DECK_EDGE):
        return []
    x0, x1, z0, kk = shp.AFT_DECK_EDGE
    parts = {4: ("41769", "41770"), 6: ("78444", "78443")}[kk]     # (port, starboard)
    L = 20 * kk
    out = []
    x = x0
    while x < x1 - 1:
        zi = shp.aft_deck_segment(x + 1)[1]          # the full row's inner edge
        for side, part in zip((-1, 1), parts):
            M = transform((x + L / 2, shp.DECK_STRIP - 8, side * (zi + 20)), rot(y=-90))
            k = int(zi // S) if side > 0 else -int(zi // S) - 1
            out.append((part, M, {(i, k) for i in cells_x(x, x + L)}))
        x += L
    return out


def deck_batch() -> Batch:
    """The deck strip on the core: two layers of plates (the upper bonding the lower across the
    salon, where there is no core under it), built on the hull; in the upper layer, the bars the
    upper panels' top edges clip onto (and, where the deck narrows aft, wedge plates on its
    edges)."""
    import naut_panels as pn
    bd = Batch()
    sizes = [s for s in AV.sizes(PLATE, "hull") if s[1] <= 12]
    cells = deck_cells()
    wedges = aft_deck_wedges()
    T = pn.FACETS["b"].Q
    bars, bar_rects = set(), []
    extra = ()
    if shp.QUARTERS_MODULE:                   # the quarters' prismatic upper panels' bars
        import naut_quarters
        extra = tuple(getattr(naut_quarters, "DECK_BARS", ()))
    for side in (-1, 1):
        for x in tuple(pn.frame_stations("b")) + extra:
            bd.add(pn.BAR, "hull", bar_M(x, shp.DECK_STRIP - 8, T[0] - 30, side), "deck")
            c = sorted(bar_cells(x, T[0] - 30, side))
            bars |= set(c)
            bar_rects.append((c[0][0], c[-1][0], c[0][1], c[-1][1]))
    for part, M, wc in wedges:
        bd.add(part, "hull", M, "deck")
        c = sorted(wc)
        bars |= set(c)
        bar_rects.append((c[0][0], c[-1][0], c[0][1], c[-1][1]))
    seeds = []                         # under each edge wedge: a plate 2 x 6 across its full
    for part, M, wc in wedges:         # row and the row inside it (it bonds the wedge in)
        c = sorted(wc)
        k_in = c[0][1] + (1 if c[0][1] < 0 else -1)
        box = {(i, k) for i, _ in c for k in (c[0][1], k_in)}
        if box <= cells and not any(box & set(cells_of(r)) for r in seeds):
            seeds.append((c[0][0], c[-1][0], min(c[0][1], k_in), max(c[0][1], k_in)))
    seeded = set().union(*(set(cells_of(r)) for r in seeds)) if seeds else set()
    bridges = []                       # where the seeds stop (each segment's start, the
    if wedges:                         # narrowing's end): a plate 2 x 4 across in the upper
        x0, x1, _, kk = shp.AFT_DECK_EDGE  # layer over the middle two rows, bonding the two
        for xb in range(int(x0) + 20 * kk, int(x1) + 1, 20 * kk):
            box = (xb // 20 - 2, xb // 20 + 1, -1, 0)
            if set(cells_of(box)) <= cells - bars:
                bridges.append(box)
    bridged = set().union(*(set(cells_of(r)) for r in bridges)) if bridges else set()
    best = None
    for s1 in range(0, 60, 7):         # the two layers, until the strip holds together
        r1 = seeds + pack(cells - seeded, sizes, prefer="x", shift=s1)
        for s2 in range(3, 40, 4):
            r2 = bridges + pack(cells - bars - bridged, sizes, ids_of(r1), prefer="z", shift=s2,
                                bridge=True)
            n = connected([r1, r2 + bar_rects])
            if best is None or n < best[0]:
                best = (n, r1, r2)
            if n == 1:
                break
        if best[0] == 1:
            break
    add_rects(bd, best[1], shp.DECK_STRIP, "hull", "deck")
    add_rects(bd, best[2], shp.DECK_STRIP - 8, "hull", "deck")
    return bd


def keel_batch(cells, standing: bool = False) -> Batch:
    """The keel strip under the core: two layers of plates, pushed up from below (the lower
    bonding the upper across the salon); in the lower one, the bars the lower panels' bottom
    edges clip onto."""
    import naut_panels as pn
    bk = Batch()
    ins = None if standing else (0, 1, 0)
    sizes = [s for s in AV.sizes(PLATE, "hull") if s[1] <= 12]
    r1 = pack(cells, sizes, prefer="x")
    add_rects(bk, r1, shp.KEEL_TOP, "hull", "keel_strip", insert=ins)
    K = pn.FACETS["d"].Q
    bars = set()
    for side in (-1, 1):
        for x in pn.frame_stations("d"):
            bk.add(pn.BAR, "hull", bar_M(x, shp.KEEL_TOP + 8, K[0] - 30, side), "keel_strip",
                   insert=ins)
            bars |= bar_cells(x, K[0] - 30, side)
    add_rects(bk, pack(cells - bars, sizes, ids_of(r1), prefer="z", shift=3, bridge=True),
              shp.KEEL_TOP + 8, "hull", "keel_strip", insert=ins)
    return bk
