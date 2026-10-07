"""The Nautilus's tail: everything aft of the tail station (naut_shape.TAIL_STATION, x = 880),
one sub-assembly in the hull frame, pushed onto the hull along -X.

`build_tail(model, parent)` builds it and places it in `parent` (hull frame: LDU, -Y up, bow
toward -X, port toward -Z, side keels centred on y = 0). PROP_AXIS and RUDDER_AXIS give the
propeller's shaft and the rudder's post ((point), (direction)) in the hull frame; the
propeller's parts are tagged "prop", the rudder's "rudder".

**Shape.** As the photo's: the tail stock runs aft from the hull and becomes the fish tail, its
two swept lobes rising and falling to their points (naut_shape.TAIL_UPPER, TAIL_LOWER), the
propeller's window between them.

* **The stock** (x 880 .. 1000) is the bow's cone turned round (naut_bow's machinery, loaded a
  second time and set up here): the spine two studs wide, capped with curved slopes, on the
  side keels. With the hull's curved stern (naut_quarters.CURVED_STERN: the pillows' lenses,
  or the stern's sweeps) it is the fish's narrow wrist between them and the fin: tiles, then a curved slope 4 x 2 rolling down to the fin's
  top edge (WRIST_TOP); under the side keels the c panels' curved wedges sweep in along it.
  The side keels go on narrowing 1:4 to x 1120 and end in a strip two studs wide at the
  window (x 1180), the shaft line along the tail, a layer of plates on it.
* **The fish tail** (x 1000 aft) is a fin built sideways like a LEGO set's (naut_fin), in two
  sub-assemblies: over the side keels the upper half, standing on jumpers on the plates on
  their strip; under them the lower half, hanging from jumpers under it (each on a plate 1 x 2
  pushed into the side keels' underside, its pin in the jumper's open stud). Each half is a
  core one stud thick (bricks with studs on both sides) with a tiled face of plates and wedge
  plates on each side: the upper lobe's leading edge sweeps up 1:2 in wedge plates 2 x 2 to its
  point, its trailing edge falls 1:6 (a wedge plate 6 x 2 on end) to the window; the lower
  lobe's leading edge falls 1:3, 1:2 and 1:4 to its point, its trailing edge rises 1:4 (a wedge
  plate 4 x 2 on end) to the window.
* **The window** (x 1180 .. 1300, y -88 .. 104): the propeller (Pearl Gold) turns on a Technic
  axle in a Technic brick 1 x 1 in the lower half's core, inside a brass guard ring (a 7 x 7
  Technic ring hanging on an axle from a round brick under the upper half); behind it the
  rudder swings on a bar post standing on the window's floor.

**The join.** Technic bricks 1 x 1 at the station take the hull's ten side studs (11211 at
z = +-10, y = -102 .. 58); nothing crosses x = 880.
"""
from __future__ import annotations

import importlib.util
import math
from functools import lru_cache
from pathlib import Path

import numpy as np

import naut_fin as nf
import naut_shape as shp
from brickkit.ldraw.matrix import rot

S = 20
XT = float(shp.TAIL_STATION)            # 880: the station plane
HERE = Path(__file__).resolve().parent
T = np.diag([-1.0, 1.0, -1.0, 1.0])     # the cone's frame (a bow pointing -X) -> the hull's

FIN_X = 1000.0                          # the stock's spine ends here; the fish tail's fin starts
STOCK_END = 1180.0                      # the window's forward edge: the bearing's column ends here
FLANGE_END = 1120.0                     # the side keels' tip (1:4 from 100 wide at the station)
STRIP_END = 1180.0                      # their two-stud strip along the shaft line ends here
WINDOW = (1180.0, 1300.0)               # the propeller's window (x) ...
WINDOW_TOP, WINDOW_BOT = -88.0, 104.0   # ... and (y)
UPPER_BASE = -24.0                      # the upper half's jumpers' top, on the strip's plates
LOWER_BASE = 24.0                       # the lower half's jumpers' underside, under the strip

PROP_Y = 34.0                           # the shaft: the Technic brick's hole in the lower core
PROP_X = 1210.0                         # the propeller's hub
RING_X = 1200.0                         # the guard ring's plane
POST_X = 1250.0                         # the rudder's post (a bar)
PROP_AXIS = ((PROP_X, PROP_Y, 0.0), (1.0, 0.0, 0.0))
RUDDER_AXIS = ((POST_X, 0.0, 0.0), (0.0, -1.0, 0.0))

ROLE, CORE, SPINE = "hull", "core", "spine"


def _M(R, pos) -> np.ndarray:
    M = np.eye(4)
    M[:3, :3] = np.asarray(R, float)[:3, :3]
    M[:3, 3] = pos
    return M


def orient(ex, ey, ez=None) -> np.ndarray:
    ex, ey = np.asarray(ex, float), np.asarray(ey, float)
    ez = np.cross(ex, ey) if ez is None else np.asarray(ez, float)
    return np.column_stack([ex, ey, ez])


# ------------------------------------------------------------------ the outline (photo)
def outline_top(x: float) -> float:
    """y of the tail's top line: the hull's deck line, then the upper lobe's leading edge."""
    if x <= shp.STERN:
        return shp.top(x)
    return float(np.interp(x, *shp.TAIL_UPPER))


def outline_bot(x: float) -> float:
    if x <= shp.STERN:
        return shp.bot(x)
    return float(np.interp(x, *shp.TAIL_LOWER))


def col_x(w: int) -> float:
    """Middle of the hull's column w (x in [20 w, 20 w + 20])."""
    return S * w + S / 2


def turned(w: int) -> int:
    """The cone's column for the hull's column w (its x' = -x)."""
    return -w - 1


W_STATION = int(XT // S)                # 44: the stock's first column (x 880..900)
W_FIN = int(FIN_X // S)                 # 50: the fin's first column
W_END = int(STOCK_END // S) - 1         # 58: the side keels' strip's last column


# ------------------------------------------------------------------ the stock's top and bottom
# The spine's top (x 880 .. 1000) is capped by a chain of curved and cheese slopes, its bottom
# by inverted curved slopes under its steps, as the hull's bands are (naut_body.chain_band /
# keel_band): fit_chain picks each column's level and the pieces.
TOP_PIECES = (("tile", (0,), 0, 0.10), ("85984", (-1,), -1, 0.15), ("15068", (0, -1), -1, 0.0),
              ("50950", (-1, -2, -2), -2, 0.0), ("93606", (0, -1, -2, -2), -2, 0.0))
UNDER_PIECES = (("flat", (0,), 0, 0.10), ("24201", (0, -1), -1, 0.0),
                ("4287b", (0, 0, 0), -3, -0.3), ("drop", (-1,), -1, 2.0))
STOCK_COLS = tuple(range(W_STATION, W_FIN))


def fit_chain(t: list, lb: list, pieces, levels, end_w: float = 0.6):
    """A run of columns (from its high end outward) capped by a chain of pieces: each sits on
    the steps it covers. `t`: target levels, `lb` least levels. Returns (levels, [(piece,
    first index, columns)]). (naut_relief.fit_chain's dynamic programme, without forcing.)"""
    n = len(t)
    dp = [dict() for _ in range(n + 1)]
    for A in levels:
        dp[0][A] = (0.0, None)
    hi = max(levels)
    for k in range(n):
        for A, (c0, _) in dp[k].items():
            for pi, (name, offs, dA, pen) in enumerate(pieces):
                m = len(offs)
                if k + m > n:
                    continue
                lv = [A + o for o in offs]
                if any(l < lb[k + j] or l > hi for j, l in enumerate(lv)):
                    continue
                c = c0 + pen * m + sum((l - t[k + j]) ** 2 for j, l in enumerate(lv))
                A2 = A + dA
                if A2 not in dp[k + m] or c < dp[k + m][A2][0]:
                    dp[k + m][A2] = (c, (k, A, pi))
    A = min(dp[n], key=lambda a: dp[n][a][0] + end_w * a * a)
    out, lev, k = [], [0] * n, n
    while k > 0:
        _, (k0, A0, pi) = dp[k][A]
        for j, o in enumerate(pieces[pi][1]):
            lev[k0 + j] = A0 + o
        out.append((pieces[pi][0], k0, len(pieces[pi][1])))
        k, A = k0, A0
    return lev, out[::-1]


# With the hull's curved stern (naut_quarters.CURVED_STERN) the stock is the narrow wrist
# between the pillows' lenses and the fin: its top two studs wide, tiles at y -128 from the stern cap's curved slope,
# then a curved slope 4 x 2 rolling down to the fin's top edge (y -108) at x 1000.
WRIST_TOP = ({44: 15, 45: 15, 46: 15, 47: 14, 48: 13, 49: 13},   # (under the 4 x 2's stepped
                                                                 # underside: its high end)
             (("tile", (44,)), ("tile", (45,)), ("93606", (46, 47, 48, 49))))


def wrist() -> bool:
    """Does the hull's afterbody close in on the stock (pillows or sweeps: a wrist)?"""
    if not shp.QUARTERS_MODULE:
        return False
    import naut_quarters
    return bool(getattr(naut_quarters, "CURVED_STERN", getattr(naut_quarters, "SWEEPS", None)))


@lru_cache(maxsize=None)
def top_chain():
    """{column: top level} (y = -8 level) and the pieces [(name, [columns], d)] along the
    stock's top, from the station aft (its high end forward, d = -1)."""
    if wrist():
        lv, pcs = WRIST_TOP
        return dict(lv), [(name, list(ws), -1) for name, ws in pcs]
    ws = list(STOCK_COLS)
    # toward x 1000 level with the fin's top (its face's top edge, y -108, and its tiles)
    t = [-outline_top(col_x(w)) / 8 - 1 if col_x(w) < FIN_X - 40 else 13.0 for w in ws]
    lb = [14 if w == W_STATION else 12 for w in ws]
    levels, chain = fit_chain(t, lb, TOP_PIECES, range(min(lb), round(max(t)) + 3), end_w=0.0)
    return dict(zip(ws, levels)), [(name, ws[k0:k0 + m], -1) for name, k0, m in chain]


@lru_cache(maxsize=None)
def bottom_chain():
    """{column: bottom depth} (y = 8 depth) and the pieces under the stock's bottom, from the
    station (its deep end) aft (d = -1)."""
    ws = list(STOCK_COLS)
    t = [outline_bot(col_x(w)) / 8 - 1 for w in ws]
    lb = [10 for w in ws]
    depths, chain = fit_chain(t, lb, UNDER_PIECES, range(min(lb), round(max(t)) + 3), end_w=0.0)
    return dict(zip(ws, depths)), [(name, ws[k0:k0 + m], -1) for name, k0, m in chain]


def _R_up(sx: int) -> np.ndarray:
    """A slope rising toward +X (sx = 1) or -X: its high side (local +Z) that way."""
    ez = np.array([sx, 0.0, 0.0])
    ey = np.array([0.0, 1.0, 0.0])
    return orient(np.cross(ey, ez), ey, ez)


def cap_items() -> list:
    """The stock's top: slopes and tiles on the spine. [(part, role, M)]."""
    lv, pieces = top_chain()
    out = []
    for name, ws, d in pieces:
        xs = [col_x(w) for w in ws]
        xm = sum(xs) / len(xs)
        low = -8.0 * lv[ws[-1]]
        if name == "tile":
            out.append(("3069b", ROLE, _M(rot(y=90), (xm, low - 8, 0.0))))
        elif name in ("85984", "15068"):
            out.append((name, ROLE, _M(_R_up(d), (xm, low, 0.0))))
        elif name == "50950":
            for z in (-10.0, 10.0):
                out.append((name, ROLE, _M(_R_up(d), (xm, low - 24, z))))
        elif name == "93606":
            out.append((name, ROLE, _M(_R_up(d), (xm, low - 24, 0.0))))
    return out


def under_items() -> list:
    """Inverted curved slopes under the stock's bottom steps."""
    dp, pieces = bottom_chain()
    out = []
    for name, ws, d in pieces:
        for z in (-10.0, 10.0):
            if name == "24201":
                w_low = ws[1]                 # the shallower column, outward
                out.append(("24201", ROLE, _M(_R_up(d), (col_x(w_low), 8.0 * dp[w_low], z))))
            elif name == "4287b":             # its thick end under the run's deep column
                out.append(("4287b", ROLE, _M(_R_up(d), (col_x(ws[0]), 8.0 * dp[ws[0]], z))))
    return out


# ------------------------------------------------------------------ the stock: the turned cone
def _profile():
    """The spine's top and bottom (cone columns): the stock's chains to x 1000, nothing aft of
    it (the side keels' strip runs on alone)."""
    top, bot = {}, {}
    lt, lb = top_chain()[0], bottom_chain()[0]
    for w in range(W_STATION, W_END + 1):
        if w in lt:
            top[turned(w)], bot[turned(w)] = -8.0 * lt[w], 8.0 * lb[w]
        else:                     # a layer of plates on the side keels' strip, bonding it
            top[turned(w)], bot[turned(w)] = -16.0, -8.0
    return top, bot


def quarters_skin() -> bool:
    """Do the quarters' afterbody panels (naut_quarters) run on over the stock? Then the stock
    has no panels of its own: theirs go on over its side keels to the spine."""
    if not shp.QUARTERS_MODULE:
        return False
    import naut_quarters
    return bool(getattr(naut_quarters, "AFT_ON", False))


@lru_cache(maxsize=None)
def cone():
    """naut_bow loaded a second time, set up as the tail's stock (a bow pointing -X, turned)."""
    spec = importlib.util.spec_from_file_location("naut_tail_cone", HERE / "naut_bow.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.XS = -XT
    m.PREFIX, m.TITLE = "tail", "The tail"
    m.JOIN_Y = tuple(float(y) for y in shp.JOIN_STUD_Y["tail"])
    m.JOIN_CAPTION = "The tail's stock on the hull's join, the side keels"
    m.FACETS = "" if quarters_skin() else "EC"
    m.UPPER, m.LOWER = "rest", "rest"
    m.STATION_JOINT = True           # its panels end on grid lines: the quarters' go on from them
    m.K = {"E": 2, "C": 2}
    m.RIDGE = dict(slope=0.4, stud=(-1130.0, 10.0), up=True)      # y -111.5 at the station
    m.KEEL = dict(slope=0.4, stud=(-1130.0, -30.0), up=False)      # y 91.5
    m.CHINE_UP = dict(y=-16.0)              # the upper panels rest on the side keels' tiles
    m.CHINE_LO = dict(y=6.0)
    m.SKIN_DIAG = dict(m.SKIN_DIAG, chine=0.0)
    m.FLANGE_HW = 100.0
    m.FLANGE_K = 4                          # narrowing 1:4, under the upper panels' edges
    m.FLANGE_TIP = -FLANGE_END
    m.FLANGE_STRIP_TO = -STRIP_END
    m.I_STATION = int(math.floor((m.XS - 20) / S))
    m.I_NOSE = turned(W_END)                # (its studs along the middle stay bare to here)
    m.DETAILS = {"ridge": False, "keel_teeth": False, "flange_teeth": False, "ram": False}
    m.SPINE_PROFILE = _profile
    m.SPINE_SKIP = frozenset()
    m.SPINE_CLIP_EVERY = 3
    m.EXTRA_WALL = ()
    m.FRAME = T
    return m


# ------------------------------------------------------------------ the fish tail's fin
@lru_cache(maxsize=None)
def upper_face() -> nf.Fin:
    """The upper half's port face (naut_fin.Fin, upright on its jumpers at UPPER_BASE; columns
    from x 1000, rows up: row r spans y -40 - 20 r .. -20 - 20 r)."""
    f = nf.Fin(FIN_X, UPPER_BASE)
    for k in range(5):                    # the upper lobe's leading edge: 1:2 up to its point
        f.wedge("24307", 1, 4 + 2 * k, 3 + k)
    f.wedge("78443", 0, 14, 3)            # its trailing edge: 1:6 down to the window
    cells = {(c, r) for c in range(0, 9) for r in range(3)}          # the stock, rows 0 .. 2
    cells |= {(c, 3) for c in list(range(0, 4)) + list(range(6, 14))}
    cells |= {(c, 4) for c in range(8, 14)} | {(c, 5) for c in range(10, 14)} | \
        {(c, 6) for c in range(12, 14)}
    f.fill(cells)
    return f


@lru_cache(maxsize=None)
def lower_face() -> nf.Fin:
    """The lower half's port face (naut_fin.Fin, hanging from LOWER_BASE; columns from x 1000,
    rows down: row r spans y 24 + 20 r .. 44 + 20 r)."""
    f = nf.Fin(FIN_X, LOWER_BASE, hanging=True)
    f.wedge("43723", 1, 0, 2)             # the lower lobe's leading edge: 1:3, 1:3, 1:2, 1:2,
    f.wedge("43723", 1, 3, 3)             # 1:4 down to its point
    f.wedge("24299", 1, 6, 4)
    f.wedge("24299", 1, 8, 5)
    f.wedge("41770", 1, 10, 6)
    f.wedge("41769", 2, 14, 4)            # its trailing edge: 1:4 up to the window
    cells = {(c, r) for c in range(0, 9) for r in range(2)}          # the stock, rows 0, 1
    cells |= {(c, 2) for c in range(3, 9)} | {(c, 3) for c in range(6, 9)}
    cells |= {(c, 4) for c in range(8, 14)} | {(c, 5) for c in range(10, 14)}
    f.fill(cells)
    return f


BEARING_C = int((STOCK_END - FIN_X) // S) - 1        # the lower core's column for the bearing


@lru_cache(maxsize=None)
def fins():
    """(upper fin's Batch, lower fin's Batch) and their faces."""
    up = upper_face()
    bu = up.build(range(0, 16), cat="up")
    lo = lower_face()
    Rb = orient((0, 0, 1), (0, 1, 0), (-1, 0, 0))          # the Technic brick's hole along X
    bearing = [("6541", CORE, _M(Rb, (STOCK_END - 10, LOWER_BASE, 0.0)))]
    ring = {(int((RING_X - FIN_X) // S) + d, k) for d in (-1, 0) for k in (10,)}
    bl = lo.build(range(0, 16), cat="lo", core_to=None, extra_core=bearing,
                  core_skip={(BEARING_C, k) for k in range(3)} | ring)
    return bu, bl


def floor_items() -> list:
    """Tiles on the window's floor (the lower core's top studs) round the post's round brick:
    [(part, role, M)]."""
    lo = lower_face()
    fins()
    tops = {}
    for c, k in lo.core_cells:
        x = FIN_X + S * c + S / 2
        if WINDOW[0] < x < WINDOW[1]:
            tops[c] = min(tops.get(c, 99), k)
    post_c = int((POST_X - FIN_X) // S)
    out = []
    for c, k in sorted(tops.items()):
        if c == post_c or LOWER_BASE + 8 * k > WINDOW_BOT + 0.5:
            continue
        y = LOWER_BASE + 8 * k
        out.append(("3070b", ROLE, _M(np.eye(3), (FIN_X + S * c + S / 2, y - 8, 0.0))))
    return out


# ------------------------------------------------------------------ the propeller, ring, rudder
def ring_items() -> list:
    """The guard ring hanging from the window's ceiling: two jumpers across under the upper
    core, a round brick 2 x 2 under them, an axle 3 down into the ring's upper connector:
    [(part, role, M, insert)]."""
    up = (0, 1, 0)
    Ra = orient((0, 1, 0), (-1, 0, 0), (0, 0, 1))          # an axle along Y
    Rr = orient((0, 0, 1), (1, 0, 0), (0, 1, 0))           # its plane square to X, holes in Y
    top = PROP_Y - 50.0                                    # the ring's upper connector
    out = [("15573", ROLE, _M(rot(y=90), (RING_X + s * 10, WINDOW_TOP, 0.0)), up)
           for s in (-1, 1)]
    out.append(("3941", ROLE, _M(np.eye(3), (RING_X, WINDOW_TOP + 8, 0.0)), up))
    out.append(("4519", "shaft", _M(Ra, (RING_X, top - 30, 0.0)), up))
    out.append(("79851", "trim", _M(Rr, (RING_X, PROP_Y, 0.0)), up))
    return out


def prop_items() -> list:
    """The propeller on its axle: a Technic axle 3 with a stop behind the hub, the propeller
    slid on from the front, a bush in front of it. [(part, role, M, insert)], tagged "prop"."""
    Rx = orient((0, 0, -1), (0, 1, 0), (1, 0, 0))          # local z (the hole) along X
    fwd = (-1, 0, 0)
    # the axle hides inside the stock; 24316 is only made in Reddish Brown, so it keeps that
    # colour in every colourway
    return [("24316", "Reddish Brown", _M(np.eye(3), (STOCK_END + 10, PROP_Y, 0.0)), None),
            ("65768", "propeller", _M(Rx, (PROP_X, PROP_Y, 0.0)), fwd),
            ("3713", "shaft", _M(Rx, (STOCK_END + 10, PROP_Y, 0.0)), fwd)]


def post_items() -> list:
    """The rudder's post: a round brick on the window floor's stud, a bar 6L standing in it."""
    y = floor_y()
    return [("3062b", SPINE, _M(np.eye(3), (POST_X, y - 24, 0.0))),
            ("63965", SPINE, _M(np.eye(3), (POST_X, y - 24 - 18, 0.0)))]


def floor_y() -> float:
    """The window floor's core top (y) under the post."""
    lo = lower_face()
    fins()
    c = int((POST_X - FIN_X) // S)
    return LOWER_BASE + 8 * min(k for cc, k in lo.core_cells if cc == c)


def rudder_items() -> list:
    """The rudder: a blade three studs long behind the post, shaped like a fin: an inverted 33
    degree slope under it and a 33 degree slope over it (its trailing edge thinner than its
    leading edge), bricks 1 x 3 and two plates with vertical clips between (the clips on the
    post, so it swings). [(part, role, M)] bottom up, tagged "rudder"."""
    x0 = POST_X + 20                    # the leading column: the clips (their clip on the post)
    xm = x0 + 20                        # the blade's middle (three columns, x0 .. x0 + 40)
    clip_R = rot(y=90)
    y = floor_y() - 24 - 4              # the blade's bottom, over the post's round brick
    out = [("4287b", ROLE, _M(_R_up(-1), (x0, y - 24, 0.0)))]     # thick end forward
    y -= 24
    for kind in ("clip", "brick", "clip", "brick", "brick"):
        if kind == "brick":
            y -= 24
            out.append(("3622", ROLE, _M(np.eye(3), (xm, y, 0.0))))
        else:
            y -= 8
            out.append(("60897", SPINE, _M(clip_R, (x0, y, 0.0))))
            out.append(("3023", ROLE, _M(np.eye(3), (x0 + 30, y, 0.0))))
    out.append(("4286", ROLE, _M(_R_up(-1), (x0, y - 24, 0.0))))   # high end forward
    return out


# ------------------------------------------------------------------ building
def _place(sub, items, tag="", insert=None, per_step=8, caption=""):
    for k, it in enumerate(items):
        part, role, M = it[:3]
        ins = it[3] if len(it) > 3 else insert
        if k % per_step == 0:
            sub.step(caption if k == 0 else "")
        pl = sub.place(part, role, (0, 0, 0), tag=tag, insert=ins)
        pl.M = np.asarray(M, float)


def _base_cols(fin: nf.Fin, k: int) -> list:
    """The fin's core columns over the side keels' strip with a layer k (their first)."""
    return sorted(c for c, kk in fin.core_cells if kk == k and FIN_X + S * c < STOCK_END)


def build_tail(model, parent):
    """Build the tail as one sub-assembly in the hull frame and place it in `parent`, pushed on
    from astern (along -X). Returns the sub-assembly."""
    from naut_kit import Batch
    c = cone()
    tail = c.build_cone(model)
    c.emit(tail, [(p, r, M, "cap", None) for p, r, M in cap_items()],
           caption="Curved slopes along the stock's top")
    c.emit(tail, [(p, r, M, "under", (0, 1, 0)) for p, r, M in under_items()],
           caption="Curved slopes under the stock's steps")
    bu, bl = fins()
    up, lo = upper_face(), lower_face()
    # the upper half: a sub-assembly built upright from its jumpers, the guard ring hung under
    # it, pushed down onto the plates on the side keels' strip
    ups = model.submodel("tail_upper", "The fish tail's upper half")
    bt = Batch()
    for cc in _base_cols(up, 0):
        bt.add("15573", ROLE, _M(rot(y=90), (FIN_X + S * cc + S / 2, UPPER_BASE, 0.0)),
               "up_base")
    bt.items += list(bu.items)
    bt.emit(ups, phases=[["up_base"], ["up_core"], ["up_core_tiles"]],
            captions={"up_base": "The fish tail's upper half, built upright: jumpers across",
                      "up_core": "Its core: bricks with studs on both sides, plates",
                      "up_core_tiles": "Tiles and cheese slopes along its top"},
            per_step=10, reach=200)
    up.emit_faces(ups, "Its faces: plates and wedge plates on the side studs, tiles")
    _place(ups, ring_items(), per_step=6,
           caption="The propeller's guard ring, hanging from a round brick under it")
    tail.step("The upper half, pushed down onto the plates on the side keels' strip")
    tail.use(ups, (0, 0, 0), tag="tail_upper", insert=(0, -1, 0))
    # the lower half: a sub-assembly built upright, pushed up under the side keels
    los = model.submodel("tail_lower", "The fish tail's lower half")
    bt = Batch()
    for cc in _base_cols(lo, 0):
        x = FIN_X + S * cc + S / 2
        bt.add("15573", ROLE, _M(rot(y=90), (x, LOWER_BASE - 8, 0.0)), "lo_top")
        bt.add("3023", ROLE, _M(rot(y=90), (x, LOWER_BASE - 16, 0.0)), "lo_top2")
    bt.items += list(bl.items)
    for p, r, M in floor_items():
        bt.add(p, r, M, "lo_floor")
    for p, r, M in post_items():
        bt.add(p, r, M, "lo_post")
    bt.emit(los, phases=[["lo_core"], ["lo_top"], ["lo_top2"], ["lo_floor", "lo_post"]],
            captions={"lo_core": "The fish tail's lower half, built upright: its core",
                      "lo_top": "Jumpers across its top",
                      "lo_top2": "Plates 1 x 2 across on them (their pins in the jumpers' "
                                 "studs): they go into the side keels' underside",
                      "lo_floor": "The window's floor: tiles, the rudder's post"},
            per_step=10, reach=200)
    lo.emit_faces(los, "Its faces: plates and wedge plates on the side studs, tiles")
    tail.step("The lower half, pushed up under the side keels")
    tail.use(los, (0, 0, 0), tag="tail_lower", insert=(0, 1, 0))
    prop = model.submodel("tail_propeller", "The propeller")
    _place(prop, prop_items(), tag="prop", per_step=4,
           caption="The propeller on its axle, a bush in front of it")
    tail.step("The propeller: its axle through the ring into the Technic brick")
    tail.use(prop, (0, 0, 0), tag="prop", insert=(1, 0, 0))
    rud = model.submodel("tail_rudder", "The rudder")
    _place(rud, rudder_items(), tag="rudder", per_step=3, caption="The rudder")
    tail.step("The rudder, clipped onto its post")
    tail.use(rud, (0, 0, 0), tag="rudder", insert=(1, 0, 0))
    parent.step("The tail, pushed onto the hull's station studs")
    parent.use(tail, (0, 0, 0), tag="tail", insert=(1, 0, 0))
    return tail
