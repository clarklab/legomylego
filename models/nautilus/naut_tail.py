"""The fish tail: its two swept lobes, the propeller on a smooth pin in a guard ring, the
guard's post and the rudder swinging on it.

The hull's core runs on past the stern (naut_shape.STERN_X) as the tail stock, two studs wide,
over and under the side keels' stub; its last brick over the stub is a Technic brick, the
propeller's bearing. The upper lobe stands on the stock and sweeps up and aft to a point (its
leading edge the traced line, TAIL_UPPER, a chain of curved slopes; its trailing edge climbing
steeply back to the point); the lower lobe hangs under it and sweeps down and aft to a point
(TAIL_LOWER). Between them, behind the stock, is the propeller's window: the propeller turns in
a brass ring (a square frame of plates with a round hole, quarter-round tiles on it) hung from a
bracket under the upper lobe; at the window's back the guard's post (a bar in a round brick on
the lower lobe) and the rudder clipped to it.

Hull frame (naut_shape): LDU, -Y up, bow toward -X."""
from __future__ import annotations

import numpy as np

import naut_relief as rel
import naut_shape as shp
from brickkit.ldraw.matrix import rot, transform
from naut_body import BAND2, Batch, chain_band, orient, profile_band
from naut_kit import S

STOCK_END = 1180.0                     # the side keels' stub and the stock end here
BEARING_I = int(STOCK_END // S) - 1    # the column of the propeller's Technic brick
PROP_Y = shp.FL_A - 24 + 10            # its pin hole: a brick over the stub (-22)
PROP_X = STOCK_END + 10                # the propeller's hub, on the pin's outer half
STOCK_TOP, STOCK_BOT = -96.0, 72.0     # the stock (the core) over and under the stub
WINDOW_TOP, WINDOW_BOT = -96.0, 88.0   # the propeller's window behind the stock
POST_X = 1260.0                        # the guard's post (a bar): the rudder's hinge
RUDDER_X = POST_X + 20                 # the rudder's clips' column
TIP = 1340.0
AFT_EDGE = 1286.0                      # the lobes' trailing edges start here, rising (falling)
UPPER_TIP, LOWER_TIP = (1331.0, -225.0), (1331.0, 165.0)    # ... to the lobes' points
# the guard ring: a square frame 8 x 8 with a round hole (r 60), in the plane x = GUARD_X (its
# plates' undersides: the face of a bracket's studs, hanging over the stock's end), its middle
# GUARD_C (y): two LDU off the propeller's axis, where the bracket's studs meet its plates' grid
GUARD_X = STOCK_END + 4
GUARD_C = PROP_Y - 2
GUARD_TOP = GUARD_C - 80               # the frame's top edge: the upper lobe clears it


def upper_bottom(x: float) -> float:
    if x < STOCK_END:
        return STOCK_TOP
    if x < GUARD_X + 32:
        return 8 * np.floor(GUARD_TOP / 8)
    if x < AFT_EDGE:
        return WINDOW_TOP
    return WINDOW_TOP + (x - AFT_EDGE) * (UPPER_TIP[1] - WINDOW_TOP) / (UPPER_TIP[0] - AFT_EDGE)


def lower_top(x: float) -> float:
    if x < STOCK_END:
        return STOCK_BOT
    if x < AFT_EDGE:
        return WINDOW_BOT
    return WINDOW_BOT + (x - AFT_EDGE) * (LOWER_TIP[1] - WINDOW_BOT) / (LOWER_TIP[0] - AFT_EDGE)


def upper_plan():
    """(columns from the point forward, their tops' levels, the levels they stand on, the
    chain's pieces)."""
    top = lambda x: float(np.interp(x, *shp.TAIL_UPPER))
    cols, t, base = [], [], []
    for i in range(int(TIP // S) - 1, int(1080 // S) - 1, -1):
        x = S * i + S / 2
        b = round(-upper_bottom(x) / 8)
        if -top(x) / 8 - 1 < b + 1:
            continue
        cols.append(i)
        t.append(-top(x) / 8 - 1)
        base.append(b)
    levels, pieces = rel.fit_chain(t, [b + 1 for b in base], BAND2,
                                   range(min(base) + 1, round(max(t)) + 3), end_w=0.0)
    return cols, levels, base, pieces


BRACKET_I = BEARING_I                  # the guard ring's bracket: under the lobe, over the stock


def upper_lobe(model):
    """The upper lobe: plates two studs wide on the stock and over the window, its leading edge
    a chain of curved slopes up to its point (its first layer over the stock's end is the guard
    ring's bracket)."""
    sub = model.submodel("tail_upper", "The tail's upper lobe")
    cols, levels, base, pieces = upper_plan()
    lv0 = round(-STOCK_TOP / 8) + 1
    bt = chain_band(cols, levels, base, pieces, d=+1, cat="lobe", skip={(BRACKET_I, lv0)})
    bt.emit(sub, phases=[["lobe"], ["lobe_top"]],
            captions={"lobe": "The tail's upper lobe: plates on the stock and over the window",
                      "lobe_top": "Curved slopes up its leading edge to the point"},
            per_step=12, reach=200)
    return sub


# the lower lobe's underside (depths in plates, y = 8 depth): a chain of inverted curved slopes
# from its deepest column forward and aft (see naut_relief.fit_chain)
UNDER = (("flat", (0,), 0, 0.10), ("24201", (0, -1), -1, 0.0), ("drop", (-1,), -1, 0.5))


def lower_plan():
    """{column: (top y, bottom y)} and the underside's curved slopes [(columns deep to shallow,
    the way to the deep one: +1 or -1)]."""
    bot = lambda x: float(np.interp(x, *shp.TAIL_LOWER))
    xs = [i for i in range(int(1000 // S), int(TIP // S))]
    top = {i: 8 * round(lower_top(S * i + S / 2) / 8) for i in xs}
    want = {i: bot(S * i + S / 2) / 8 - 0.5 for i in xs}
    deep = max(xs, key=lambda i: want[i])
    depth, caps = {}, []
    for run, d in ((list(range(deep, xs[0] - 1, -1)), 1), (list(range(deep + 1, xs[-1] + 1)), -1)):
        if not run:
            continue
        lv, pieces = rel.fit_chain([want[i] for i in run], [top[i] // 8 + 1 for i in run],
                                   UNDER, range(min(top[i] // 8 + 1 for i in run), 40),
                                   end_w=0.0)
        for i, l in zip(run, lv):
            depth[i] = l
        for name, k0, m in pieces:
            if name == "24201":
                caps.append(([run[k0], run[k0 + 1]], d))
    cols = {i: (top[i], 8 * depth[i]) for i in xs if 8 * depth[i] - top[i] >= 8}
    return cols, caps


def lower_cols() -> dict:
    return lower_plan()[0]


def lower_lobe(model):
    sub = model.submodel("tail_lower", "The tail's lower lobe")
    cols, caps = lower_plan()
    bt = profile_band(cols, cat="lobe", cap=False)       # built upright, pushed up as one
    from naut_body import _R_up
    for (i_deep, i_low), d in caps:                      # curved slopes under its steps
        if i_deep in cols and i_low in cols:
            for z in (-10, 10):
                bt.add("24201", "hull", transform((S * i_low + S / 2, cols[i_low][1], z),
                                                  _R_up(d)), "under", insert=(0, 1, 0))
    # tiles over the window's floor, a jumper for the guard's post
    pi = int(POST_X // S)
    for i, (t, b) in cols.items():
        if S * i + S / 2 > STOCK_END and i != pi:
            bt.add("3069b", "hull", transform((S * i + S / 2, t - 8, 0), rot(y=90)), "floor",
                   insert=(0, -1, 0))
    bt.add("15573", "spine", transform((POST_X + 10, WINDOW_BOT - 8, 0), rot(y=90)), "floor",
           insert=(0, -1, 0))
    bt.emit(sub, phases=[["lobe"], ["under"], ["floor"]],
            captions={"lobe": "The tail's lower lobe, pushed up under the stock",
                      "under": "Curved slopes under it",
                      "floor": "Tiles over the propeller's window"}, per_step=12, reach=200)
    return sub


def guard_ring(model):
    """The propeller's guard ring: a bracket for the stock's top, four plates with quarter-circle
    cutouts on its studs (an 8 x 8 square with a round hole), two plates under them joining
    them, the brass ring (four quarter-round macaroni tiles) and quarter-round tiles on the
    corners. It goes onto the stock's end from above, before the propeller (which goes in
    through it) and the upper lobe."""
    from naut_kit import side_R
    from naut_window import turned
    sub = model.submodel("guard_ring", "The propeller's guard ring")
    # its own frame: studs out toward +x (aft), u along z, v along y, from the ring's middle
    R = orient((0, 0, 1), (-1, 0, 0), (0, -1, 0))
    at = lambda u, v, w: np.array([GUARD_X + w, GUARD_C + v, u], float)
    bt = Batch()
    # a bracket 1 x 2 - 1 x 2 down: its plate goes on the stock's top at its end (under the upper
    # lobe), its two studs face aft at the ring's top row
    Rb = orient((0, 0, 1), (0, 1, 0), (-1, 0, 0))
    bt.add("99781", "hull", transform((S * BRACKET_I + S / 2, STOCK_TOP - 8, 0), Rb), "bracket")
    for su in (-1, 1):                                  # the top plates, on the bracket
        p = at(40 * su, -40, 8)
        Rf = turned("35044", R, p, (40, 0, -40), at(0, 0, 8))
        bt.add("35044", "hull", transform(p, Rf), "frame", insert=(1, 0, 0))
    for u in (70, -70):                                 # joining plates under the frame's sides
        bt.add("3023", "hull", transform(at(u, 0, 0), R @ rot(y=90)), "join", insert=(-1, 0, 0))
    for su in (-1, 1):                                  # the bottom plates, on them
        p = at(40 * su, 40, 8)
        Rf = turned("35044", R, p, (40, 0, -40), at(0, 0, 8))
        bt.add("35044", "hull", transform(p, Rf), "frame_lo", insert=(1, 0, 0))
    for su in (-1, 1):
        for sv in (-1, 1):
            p = at(0, 0, 16)
            Rm = turned("27507", R, p, (40, 0, -40), at(40 * su, 40 * sv, 16))
            bt.add("27507", "trim", transform(p, Rm), "ring", insert=(1, 0, 0))
            for u, v in ((50, 70), (70, 50), (70, 70)):
                pu, pv = u * su, v * sv
                pq = at(pu, pv, 16)
                out = 1 if u != v else -1      # the corner's round side outward
                Rq = turned("25269", R, pq, (-10, 0, 10),
                            at(pu + 10 * su * out, pv + 10 * sv * out, 16))
                bt.add("25269", "hull", transform(pq, Rq), "ring", insert=(1, 0, 0))
    bt.emit(sub, phases=[["bracket"], ["frame"], ["join"], ["frame_lo"], ["ring"]],
            order=lambda j: 0,
            captions={"bracket": "The propeller's guard ring: a bracket",
                      "frame": "Plates with quarter-circle cutouts on its studs",
                      "join": "Plates under their sides",
                      "frame_lo": "The lower two",
                      "ring": "The brass ring and rounded corners"}, per_step=8, reach=200)
    return sub


def propeller(model):
    """The propeller on a smooth Technic pin in the stock's bearing."""
    sub = model.submodel("propeller", "Propeller")
    sub.place("92842", "propeller", (PROP_X, PROP_Y, 0), rot(y=90), tag="prop",
              insert=(1, 0, 0))
    sub.step("A smooth pin in its hub, so it spins freely")
    sub.place("3673", "shaft", (STOCK_END, PROP_Y, 0), tag="prop", insert=(1, 0, 0))
    return sub


def post(model):
    """The guard's post at the back of the window: a round brick with an open stud on a
    jumper, a bar in it."""
    sub = model.submodel("rudder_post", "The rudder's post")
    x = POST_X + 10
    sub.place("3062b", "spine", (x, WINDOW_BOT - 8 - 24, 0), insert=(0, -1, 0))
    sub.step("The post: a bar")
    sub.place("63965", "spine", (x, WINDOW_BOT - 8 - 24 - 18, 0), insert=(0, -1, 0))
    return sub


def rudder(model):
    """The rudder: a blade two studs long of bricks and plates behind the post, clipped to it by
    two plates with vertical clips, so it swings about the post."""
    sub = model.submodel("rudder", "Rudder")
    x0 = RUDDER_X + 10                  # the clips' column
    x1 = x0 + S                         # the blade's aft column
    clip_R = rot(y=90)                  # the clip toward the bow
    y = WINDOW_BOT - 16                 # the blade's bottom, just over the window's floor
    layers = ["brick", "brick", "brick", "clip", "brick", "brick", "clip", "brick"]
    for n, kind in enumerate(layers):
        sub.step()
        if kind == "brick":
            y -= 24
            sub.place("3004", "hull", ((x0 + x1) / 2, y, 0), tag="rudder")
        else:
            y -= 8
            sub.place("60897", "spine", (x0, y, 0), clip_R, tag="rudder")
            sub.place("3024", "hull", (x1, y, 0), tag="rudder")
    sub.step()
    sub.place("3069b", "hull", ((x0 + x1) / 2, y - 8, 0), tag="rudder")
    return sub
