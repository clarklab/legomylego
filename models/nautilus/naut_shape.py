"""The Nautilus's shape, traced from the profile photo of a finished display model (bow to the
right in the photo; 1,775 px from the tail fin's tips to the ram's point).

Scale: the salon window's glass is 80 px across in the photo; it is LEGO's biggest clear bubble
(50747, a 6 x 6 half sphere, 120 LDU across), so 1 px = 1.5 LDU and the Nautilus is 2,662 LDU
(106 cm, 42 in) from the tail's tips to the ram's point - about 1:52, minifigure scale.

Model frame (LDU, -Y up): the hull runs along X with the BOW AT -X (so the hero three-quarter,
which looks from the front-left, sees the bow), the port side faces the front (-Z). The side
keels (the chine, the hull's widest ridge, through the salon windows) are centred on y = 0.

Photo pixel (u, v) -> model (x, y): x = -(u - 962.5) * K, y = (v - 430) * K, K = 1.5.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

K = 1.5
U0, V0 = 962.5, 430.0


def X(u: float) -> float:
    return -(u - U0) * K


def Y(v: float) -> float:
    return (v - V0) * K


def _line(pts):
    """Polyline in photo pixels -> (xs ascending, ys) in model LDU."""
    xs = np.array([X(u) for u, _ in pts])
    ys = np.array([Y(v) for _, v in pts])
    o = np.argsort(xs)
    return xs[o], ys[o]


def _interp(line, x):
    xs, ys = line
    return float(np.interp(x, xs, ys))


# hull body (no fins, deck houses or crest): top edge, bottom edge, chine
TOP = _line([(300, 360), (340, 352), (440, 342), (446, 314), (1180, 312), (1490, 302),
             (1550, 318), (1600, 334), (1650, 352), (1700, 372), (1740, 390), (1762, 400)])
BOT = _line([(300, 482), (390, 495), (490, 513), (560, 530), (620, 547), (1300, 545),
             (1350, 528), (1450, 496), (1550, 470), (1650, 442), (1720, 420), (1762, 405)])
CHINE = _line([(300, 430), (1200, 432), (1500, 421), (1762, 402)])

BOW_TIP = X(1762)          # -1199
STERN = X(300)             # +994: the hull meets the tail fin
TAIL_TIP = X(75)           # +1331
SPEAR_TIP = X(1850)        # -1331


def top(x):
    return _interp(TOP, x)


def bot(x):
    return _interp(BOT, x)


def chine(x):
    return _interp(CHINE, x)


# ------------------------------------------------------------------ things on the hull
WHEELHOUSE = (X(1335), X(1185))           # x range (front, aft end): -559 .. -334
WHEELHOUSE_TOP = Y(248)                   # -273
CREST_ARCH = _line([(1322, 226), (1360, 222), (1400, 228), (1450, 250), (1490, 280),
                    (1530, 306)])           # top of the arched crest, wheelhouse to bow deck
AFT_FIN = _line([(778, 312), (790, 250), (800, 248), (830, 262), (870, 280), (920, 300),
                 (930, 312)])
AFT_HOUSE = (X(560), X(446), Y(305))      # raised aft deck: x range and top
SALON = (X(1000), Y(432))                 # salon window centre (-56, 3)
REAR_FIN = _line([(620, 547), (690, 597), (855, 598), (858, 545)])
FWD_FIN = _line([(990, 545), (992, 606), (1190, 602), (1232, 590), (1238, 545)])
SAW_KEEL = _line([(1320, 590), (1450, 560), (1550, 522), (1650, 478), (1720, 442),
                  (1762, 410)])             # tooth tips
TAIL_UPPER = _line([(75, 280), (115, 290), (165, 320), (205, 350), (240, 361), (300, 360)])
TAIL_LOWER = _line([(75, 540), (115, 550), (165, 545), (205, 525), (240, 505), (290, 485),
                    (300, 482)])
POSTS = (X(1278), X(712))                 # the photo stand's two supports


# ------------------------------------------------------------------ the hull's frame
# Hull frame: the side keels' flange is centred on y = 0. The hull is a lens: in the constant
# midbody (WIDE, round the salon) its sides are large tiled panels on hinges (naut_panels);
# toward the ram and into the tail stock it tapers in plan (the side keels' edge: wedge plates
# of 1:6, 1:4, then 1:3) and in height (the deck and keel lines run down to the ends), built as
# stepped shells of studs-out plates smoothed with curved slopes (naut_relief). Rows of those
# shells are 20 LDU (a stud) apart, layers 8 (a plate).
FLANGE_HW = 240           # side keels: 24 studs across (beam 0.18 of the length)
FL_A, FL_B = -8, 0        # the flange's two plate layers (tops); it spans y -8..8
LEDGE = 40                # the side keels stand out this far from the hull body (less
                          # where they narrow: a third of their half-width)
WIDE = (-480.0, 360.0)    # the constant midbody: the panelled sides and the salon
BOW_TIP_X = -1200.0       # the side keels meet here (six studs wide); the ram goes on
STERN_X = 1000.0          # the side keels end here, six studs wide; the tail stock goes on
# taper segments from WIDE outward: (x_wide, x_narrow, hw at x_wide, kind) where kind is the
# wedge plate that makes the edge: "12x3" (1:6), "4x2" (1:4) or "6x3" (1:3)
TAPERS = ((-480, -720, 240, "12x3"), (-720, -960, 200, "4x2"), (-960, -1200, 140, "6x3"),
          (360, 760, 240, "4x2"), (760, 1000, 140, "6x3"))
SLOPE = {"12x3": 1 / 6, "4x2": 1 / 4, "6x3": 1 / 3}
WEDGE_LEN = {"12x3": 240, "4x2": 80, "6x3": 120}
DECK_STRIP = -160         # the deck's lower plates' top: two layers, tiles on them (-176)
CORE_TOP = DECK_STRIP + 8     # the hull's sides and the core reach up to here under the deck
KEEL_TOP = 152            # the keel strip's top: two layers (the belly at 168)
UP_ROWS = tuple(-22 - 20 * k for k in range(7))     # stud lines of the rows over the side
LO_ROWS = tuple(18 + 20 * k for k in range(7))      # keels, and under them
DECK_HW = 80              # the deck: a raised strip eight studs wide amidships
KEEL_HW = 60              # the keel strip: six studs wide

# The midbody's panel chains (naut_panels), in (|z|, y): each side of the hull is two flat
# facets over the side keels and two under them, hinged to each other and, at their ends, to
# bars on the side keels, the deck's edge and the keel strip's edge (clip and bar hinges).
CHAIN_UP = ((190.0, -30.0), (4, 3), (90.0, -166.0))   # side keels' bar, facet widths, deck's bar
CHAIN_LO = ((190.0, 18.0), (4, 4), (70.0, 162.0))     # under the side keels, ..., keel strip


def flange_hw(x: float) -> float:
    """Half-width of the side keels in plan."""
    if WIDE[0] <= x <= WIDE[1]:
        return FLANGE_HW
    for xw, xn, hw, kind in TAPERS:
        if min(xw, xn) <= x <= max(xw, xn):
            return hw - abs(x - xw) * SLOPE[kind]
    return 0.0


# With the quarters module's pillows (naut_quarters.AFT_UPPER "p") the deck strip narrows aft
# of the midbody under the pillows' top edges, its upper layer's edge 1:K in wedge plates K x 2
# (naut_frame.aft_deck_wedges), a row in every K columns. AFT_DECK_EDGE: (x from, x to, the
# edge's |z| at x from, K), or None.
AFT_DECK_EDGE = (360.0, 600.0, 100.0, 4)


def aft_deck_segment(x: float):
    """The narrowing deck's wedge segment at x: (its first x, the |z| of its wedge's full row's
    inner edge), or None."""
    if not (QUARTERS_MODULE and AFT_DECK_EDGE):
        return None
    x0, x1, z0, k = AFT_DECK_EDGE
    if not x0 <= x < x1:
        return None
    m = int((x - x0) // (20 * k))
    return x0 + 20 * k * m, z0 - 20 * m - 40


def deck_hw(x: float) -> float:
    """Half-width of the deck strip: eight studs wide amidships, narrowing to the bow's ridge
    and the raised after deck."""
    seg = aft_deck_segment(x)
    if seg is not None:
        return seg[1] + 20.0      # (its lower layer: to the wedge's full row; its triangle beyond)
    if QUARTERS_MODULE and AFT_DECK_EDGE and AFT_DECK_EDGE[1] <= x <= QUARTER_DECK_AFT:
        return 20.0
    if QUARTERS_MODULE and -880 <= x < QUARTER_DECK_FWD:
        return 20.0               # forward of the wheelhouse: just over the core (the quarters'
                                  # bow cone rises over it to the wheelhouse's front)
    if QUARTERS_MODULE and 560 < x <= QUARTER_DECK_AFT:
        return DECK_HW            # the afterbody's: the a panels' top edges up against its edges
    if -720 <= x <= 560:
        return DECK_HW
    if -880 <= x < -720 or 560 < x <= 780:
        return 60.0
    return 0.0


# ------------------------------------------------------------------ the salon
SALON_C = (-60.0, -12.0)      # the salon window's centre (x, y): just over the side keels
WINDOW_Z = 194.0              # |z| of the window bubble's rim (its middle plane)
BOSS_X = (-200.0, 80.0)       # the window's raised boss along the hull (naut_window)
SALON_BAY = (-280.0, 180.0)   # the salon inside the hull, between two bulkheads
SALON_FLOOR = 64              # its floor's top: a minifigure's eyes level with the window
BULKHEADS = (-1000, -800, -620, -320, 180, 400, 620, 840)   # bulkheads' first columns (x)


# ------------------------------------------------------------------ joins to the bow and tail
# The bow forward of BOW_STATION and the tail aft of TAIL_STATION are separate modules
# (naut_bow.build_bow(model, parent), naut_tail_new.build_tail(model, parent)), each one
# sub-assembly in the hull frame, pushed onto the hull built here along X.
#
# * The hull here stops at the station plane: the bulkheads' solid walls there (x -800..-760
#   and 840..880) are its end faces. The side keels (both layers), the deck strip, the core,
#   the hull sides, the saw keel, the stern's ridge and keel all stop at the plane; nothing of
#   the hull here crosses it. (The bow's 1:4 and the tail's 1:3 wedge plates change at it.)
# * JOIN_STUDS: the core's last column at each station (x -800..-780, 860..880) has, in each of
#   its brick courses, a 1 x 2 brick with two studs on its side (11211), the studs facing out
#   of the station (-X at the bow, +X at the tail) on the station plane, at z = -10 and +10 and
#   the heights below (the courses the hull sides hang on): 12 studs at the bow, 10 at the
#   tail. A module pushes onto them along X with a face of anti-studs (plates or bricks turned
#   to face the hull); it touches nothing else of the hull.
# * The section at each station (station_section in naut_relief: the hull sides' plate faces
#   |z| by row, the core, the deck, the side keels, the keel under the core) is what a module's
#   skin should continue from.
# * The tail module tags its propeller's parts "prop" and its rudder's "rudder", and gives
#   PROP_AXIS and RUDDER_AXIS ((point), (direction)) in the hull frame for the mechanism.
BOW_STATION, TAIL_STATION = -800.0, 880.0
# When a module is there (its file defines its build function) the hull built here stops at its
# station; when it isn't (or is still being written), the hull runs on to the ram and the tail
# stock as before (naut_tail.py's tail), so the model always builds.
_HERE = Path(__file__).resolve().parent


def _module_ready(name: str, *names: str) -> bool:
    f = _HERE / f"{name}.py"
    if not f.exists():
        return False
    text = f.read_text()
    return all(f"\ndef {n}(" in text or f"\n{n} = " in text for n in names)


BOW_MODULE = _module_ready("naut_bow", "build_bow")
TAIL_MODULE = _module_ready("naut_tail_new", "build_tail", "PROP_AXIS", "RUDDER_AXIS")
HULL_X = (BOW_STATION if BOW_MODULE else -1e9, TAIL_STATION if TAIL_MODULE else 1e9)
JOIN_STUD_Y = {"bow": (-142.0, -102.0, -62.0, -22.0, 18.0, 58.0),
               "tail": (-102.0, -62.0, -22.0, 18.0, 58.0)}
JOIN_STUD_Z = (-10.0, 10.0)

# The QUARTERS between the midbody's panels and the stations (the forebody x -800 .. -480, the
# afterbody 360 .. 880) can be skinned by a module too, naut_quarters.build_quarters(model,
# parent). When it is there, the stepped shells of plates there are left out; the core (with
# side-stud bricks all along both its faces there: naut_relief.quarter_interface), the side
# keels, the deck, the keel strip and keels, the wheelhouse, the crest and the fins stay.
QUARTERS = ((BOW_STATION, WIDE[0]), (WIDE[1], TAIL_STATION))
QUARTERS_MODULE = _module_ready("naut_quarters", "build_quarters")


QUARTER_DECK_FWD = -640.0     # with the quarters module: the deck strip's full width ends here
QUARTER_DECK_AFT = 780.0      # ... and aft it runs on as wide to here, the after deck's end


def in_quarter(x: float) -> bool:
    """Is x in a quarter that the quarters module skins (when it is there)?"""
    return QUARTERS_MODULE and any(a <= x < b for a, b in QUARTERS)


def in_hull(x: float) -> bool:
    """Is x within the hull built here (between the modules' stations, when they are there)?"""
    return HULL_X[0] <= x < HULL_X[1]
