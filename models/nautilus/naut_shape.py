"""The Nautilus's shape, traced from the profile photo of a finished display model (bow to the
right in the photo; 1,775 px from the tail fin's tips to the ram's point).

Model frame (LDU, -Y up): the hull runs along X with the BOW AT -X (so the hero three-quarter,
which looks from the front-left, sees the bow), the port side faces the front (-Z). The chine
(the hull's widest ridge, through the salon windows) is at y = 0 amidships.

Photo pixel (u, v) -> model (x, y): x = -(u - 962.5) * K, y = (v - 430) * K, K = 1140 / 1775.
"""
from __future__ import annotations

import numpy as np

K = 1140.0 / 1775.0
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

BOW_TIP = X(1762)          # -512
SAW_FROM = X(1320)         # -230: where the saw-toothed keel starts
STERN = X(300)             # +425: the hull meets the tail fin
TAIL_TIP = X(75)           # +570
SPEAR_TIP = X(1850)        # -570

# chine half-width along the hull (plan view), LDU; the photo is a pure side view, so this is
# judged from the three-quarter photos: a long sharp bow, a shorter run aft to the tail
# Girthy: about as wide at the chine as the hull is deep (the three-quarter photos)
HALF_WIDTH = (np.array([BOW_TIP, -470, -420, -360, -300, -240, -185, 180, 250, 320, 380, 425]),
              np.array([4.0, 24, 42, 58, 72, 84, 90, 90, 84, 68, 46, 26]))


def top(x):
    return _interp(TOP, x)


def bot(x):
    return _interp(BOT, x)


def chine(x):
    return _interp(CHINE, x)


def chine_half_width(x):
    xs, ws = HALF_WIDTH
    if x < xs[0] or x > xs[-1]:
        return 0.0
    return float(np.interp(x, xs, ws))


# cross-section: the half-width at a height, as a fraction of the chine's, against s = how far
# from the chine to the deck (or the belly), 0..1. Amidships this gives bands of one stud per
# layer step: 66 at the chine, 58, 42 and 26 one, two and three studs above and below it.
UPPER = (np.array([0.0, 0.29, 0.57, 0.86, 1.0]), np.array([1.0, 0.9, 0.68, 0.45, 0.40]))
LOWER = UPPER


def half_width(x: float, y: float) -> float:
    """Half-width of the hull body at (x, y); 0 outside it."""
    t, b, c = top(x), bot(x), chine(x)
    w = chine_half_width(x)
    if w <= 0 or y < t or y > b:
        return 0.0
    if y <= c:
        s = (c - y) / max(c - t, 1e-6)
        f = np.interp(s, *UPPER)
    else:
        s = (y - c) / max(b - c, 1e-6)
        f = np.interp(s, *LOWER)
    return float(w * f)


# ------------------------------------------------------------------ things on the hull
WHEELHOUSE = (X(1185), X(1335))           # x range (aft end, front)
WHEELHOUSE_TOP = Y(248)
CREST_ARCH = _line([(1322, 226), (1360, 222), (1400, 228), (1450, 250), (1490, 280),
                    (1530, 306)])           # top of the arched crest, wheelhouse to bow deck
AFT_FIN = _line([(778, 312), (790, 250), (800, 248), (830, 262), (870, 280), (920, 300),
                 (930, 312)])
AFT_HOUSE = (X(446), X(560), Y(305))      # raised aft deck: x range and top
SALON = (X(1000), Y(432))                 # salon window centre
REAR_FIN = _line([(620, 547), (690, 597), (855, 598), (858, 545)])
FWD_FIN = _line([(990, 545), (992, 606), (1190, 602), (1232, 590), (1238, 545)])
SAW_KEEL = _line([(1320, 590), (1450, 560), (1550, 522), (1650, 478), (1720, 442),
                  (1762, 410)])             # tooth tips
TAIL_UPPER = _line([(75, 280), (115, 290), (165, 320), (205, 350), (240, 361), (300, 360)])
TAIL_LOWER = _line([(75, 540), (115, 550), (165, 545), (205, 525), (240, 505), (290, 485),
                    (300, 482)])
POSTS = (X(712), X(1278))                 # the photo stand's two supports (ours: naut_stand)


# ------------------------------------------------------------------ the hull's cross-section
# Hull frame: the side keels' flange is centred on y = 0. The hull is a faceted lens: widest at
# the salon windows, tapering in plan to the ram and into the tail stalk (the side keels: 1:6,
# then 1:4 near the ends), and in height (the deck and keel lines step down to the ends).
FLANGE_HW = 100           # side keels: 10 studs across (beam 0.18 of the length)
FL_A, FL_B = -8, 0        # the flange's two plate layers (tops); it spans y -8..8
WIDE = (-100.0, 20.0)     # the widest part: the salon windows
BOW_TIP_X = -500.0        # the side keels meet here (two studs wide); the ram goes on
STERN_X = 420.0           # the side keels end here, two studs wide; the tail stock goes on
PROW_X = -340.0           # the deck's grilles run aft from here
# taper segments from WIDE outward: (x_wide, x_narrow, hw at x_wide, kind) where kind is the
# wedge plate that makes the edge: "12x3" (1:6) or "4x2" (1:4)
TAPERS = ((-100, -340, 100, "12x3"), (-340, -420, 60, "4x2"), (-420, -500, 40, "4x2"),
          (20, 260, 100, "12x3"), (260, 340, 60, "4x2"), (340, 420, 40, "4x2"))
SLOPE = {"12x3": 1 / 6, "6x2": 1 / 6, "4x2": 1 / 4}
DECK_STRIP = -80          # the deck strip's top (plates)


def flange_hw(x: float) -> float:
    """Half-width of the side keels in plan."""
    if WIDE[0] <= x <= WIDE[1]:
        return FLANGE_HW
    for xw, xn, hw, kind in TAPERS:
        if min(xw, xn) <= x <= max(xw, xn):
            return hw - abs(x - xw) * SLOPE[kind]
    return 0.0


# ------------------------------------------------------------------ the salon windows
# Each window sits on a boss: the hull side raised to a flat face six studs square (corners cut)
# from x -100 to 20, centred on a stud-grid corner near the traced centre (SALON), so the round
# frame's anti-studs land on the hull's stud rows above and below the side keels. The side keels
# are cut back under the frame (they run into the boss), and behind it a pocket takes the light
# (a Power Functions lamp pushed into the frame's centre hole from behind); its lead goes in
# along the side keels' level and down a shaft in the core.
SALON_X = (-100.0, 20.0)       # the boss
SALON_C = (-40.0, -12.0)       # the window's centre (x, y)
SALON_FACE = 6                 # the boss face: this many layers out from the core (|z| 68)
SALON_NOTCH = (-80.0, 0.0)     # the side keels cut back to |z| <= 60 under the frame
LAMP_X = (-60.0, -20.0)        # the lamp's pocket (side keels cut back to |z| <= 40 here)
SHAFT_X = (-40.0, -20.0)       # the lead's way in and down: side keels and core cut here
