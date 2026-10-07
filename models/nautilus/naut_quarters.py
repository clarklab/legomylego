"""The hull's quarters: the skins between the midbody's panels and the bow and tail modules
(naut_shape.QUARTERS: the forebody x -800 .. -480, the afterbody 360 .. 880).

`build_quarters(model, parent)` builds them onto the hull sub-assembly `parent` (hull frame: LDU,
-Y up, bow toward -X, port toward -Z). The hull leaves its stepped shells out there and gives
the core's side studs (naut_relief.quarter_interface); the side keels' top studs and undersides
are bare for the skins' clips.

**The forebody.** The bow's cone runs on aft into the quarter, on the same facets, so the
plating is continuous through the bow's station (each facet's panels meet on one of its grid
lines there):

* over the side keels, the bow's facets A (on the side keels' line, 1:3 in plan) and E (on the
  ridge line, at 0.36) meet on their crease; aft of the station their panels rise to the
  wheelhouse's front (x -640), where the deck strip (narrowed to the core forward of it) ends
  under them. From there to the midbody the upper panels are the midbody's own (a, b), hinged on
  the side keels' bars and the deck strip's.
* under the side keels, the facet c (hung on clips under the side keels, 2:7 in plan) and C (on
  the keel line, 0.4, on the core's side studs) meet on their seam; c narrows to nothing at the
  bow's station, C runs on under the bow to its point.

Each facet's angles are the bow cone's (naut_bow: its creases solved so each panel meets its
neighbours on its wedge plates' angle), within a few LDU of the midbody's where they meet. E and
C carry a lip, a row of tiles past their crease over A's and c's stepped edges (naut_bow
GRID_LIP; A's and c's studs under it stay bare). A and c, C end cell by cell at the
wheelhouse's front and the midbody, under a rib on the next panel's first column (a plate
proud: naut_panels.build_panel `ribs`); E ends on a grid column line. The ridge before the
wheelhouse is a wall on the deck strip, capped four studs wide over the E panels' edges where
the crest arch's band leaves room.

**The afterbody.** Over the side keels each side is one rounded, tapering body, the pillow
(PILLOWS "p"): a rigid panel ten rows wide hinged on clips on the side keels' studs along a
line converging 1:4 on the tail (parallel to the side keels' edge), leaning in until its top
row rests on the deck strip, which narrows under it in wedge plates (naut_shape.AFT_DECK_EDGE,
naut_frame.aft_deck_wedges). Its section is an arch: curved slopes 4 x 2 (93606) along both
edges, their high ends inward, and two plates and tiles over the flat middle; aft it ends in two
big curved wedges (41749 / 41750, 8 x 3 x 2 open, tall edges together: a lens) that close it to a
point by the after deck's end, a curved slope 2 x 2 beside their roots. Its front meets the
midbody's a and b at x 360. (AFT_UPPER "ab" restores the faceted a and b panels.)

Under the side keels the midbody's lower facets go on at their own angles (the sections match at
x 360), each one long thin panel of its thickness (EdgePanel: a carrier layer, tiles on it): c
on clips on the side keels' studs along a line converging 1:4, d on clips on the core's side
studs along a keel line rising aft (2:9). d laps over c along a 1:4 edge (a run of wedge plates
on top of the carrier, flush with the tiles, their studs out like a row of rivets: TOP_WEDGES),
a few LDU past the crease; c's lower edge steps along under d. The edges are fitted by a dynamic
programme (fit_edge). Each c panel ends at the station in a curved wedge 6 x 2 (41747 / 41748)
sweeping in under the side keels toward the fin's lower lobe (SWEEPS), its root flush with the
panel's tiles on plates hung under the carrier. Aft of the after deck the stern's top is two
studs wide on the core between the pillows' lenses: tiles, then a curved slope 2 x 2 rolling
down to the tail's stock, a narrow wrist into the fin (naut_tail_new).

Also here: tiles on the core's bare side studs where they show by the stern, and plates under
the deck's edge along the salon's gull wing (its hinge can't carry a lip).

Needs from the hull (naut_shape / naut_frame / design / naut_body / naut_panels): the deck strip
only over the core forward of the wheelhouse (QUARTER_DECK_FWD) and eight studs wide on to the
after deck's end (QUARTER_DECK_AFT), the deck strip's bars at DECK_BARS, its studs there held
back from the early tiles, the wheelhouse's eyes a level up, no stern ridge when STERN_TOP, and
the midbody's panels' ribs (naut_panels.ribs, their tiles placed here last: RIB_TILES).
"""
from __future__ import annotations

import math
from functools import lru_cache

import numpy as np

import naut_bow as bow
import naut_panels as pn
import naut_relief as rel
import naut_shape as shp
from brickkit.ldraw.matrix import rot, transform
from naut_kit import pack as kit_pack

S = 20
FWD = tuple(shp.QUARTERS[0])                 # (-800, -480)
X_WH = shp.QUARTER_DECK_FWD                  # -640: the wheelhouse's front
ROLE, CORE = "hull", "core"
# the prismatic upper panels between the wheelhouse's front and the midbody (the midbody's a, b):
# their hinges' columns (a's on both its edges and b's on the seam; b's own on the deck strip)
P_UP = (X_WH, FWD[1])
P_HINGES = {"a": ([-610.0, -550.0], [-610.0, -550.0]), "b": ([-610.0, -550.0], [-590.0, -530.0])}
DECK_BARS = tuple(P_HINGES["b"][1])          # the deck strip's bars for them (naut_frame)
PRISM_RIB = "a"                              # a rib over its joint with the cone's panel A


def core_stud(x: float, y: float) -> bool:
    """Is there a side stud on the core's faces at (x, y) (a quarter's column, a course)?"""
    if not any(a <= x < b for a, b in shp.QUARTERS):
        return False
    i = int(math.floor(x / S))
    if i in rel.joint_cols():
        return False
    return any(abs(y - yy) < 0.5 for yy in rel.course_studs(x))


# ------------------------------------------------------------------ the forebody's cone
def _keel_strip_or_post(pts) -> bool:
    """A box (its corners, world) that would reach the keel strip's front end or the stand's
    front post's top: they stand inside |z| 80 aft of x -520 and under y 140."""
    for p in pts:
        if p[0] > -522 and abs(p[2]) < 82 and p[1] > 140:
            return True
    return False


def fwd_cut(name: str) -> dict:
    """Each facet's part in the forebody's quarter: from the bow's station joint (a grid column
    line) aft to the wheelhouse's front (A and E) or the midbody (c and C), cell by cell (its
    end steps within a stud of that plane, under the rib on the next panel's end), E to the
    last grid column line wholly forward of it."""
    if name == "A":
        return dict(joint=("aft", bow.XS), x_max=X_WH)
    if name == "E":                    # (its end on a column line: the rib on b would hit it)
        return dict(joint=("aft", bow.XS), joint2=("fore", X_WH), x_max=X_WH)
    if name == "c":
        return dict(x_max=FWD[1], x_min=bow.XS - 4)
    return dict(x_max=FWD[1], y_min=9.0, forbid=_keel_strip_or_post)


@lru_cache(maxsize=None)
def fwd_plan(side: int) -> dict:
    P = {f: bow.Panel(f, side, fwd_cut(f)) for f in "AEcC"}
    fixed = {"chine_up": bow.chine_clips(side, "up", xr=(bow.XS + 10, X_WH - 14)),
             "chine_lo": bow.chine_clips(side, "lo", xr=(bow.XS + 10, FWD[1] - 14)),
             "ridge": bow.spine_clips(side, "up", xr=(bow.XS + 10, X_WH - 30), avail=core_stud),
             "keel": bow.spine_clips(side, "lo", xr=(bow.XS + 10, FWD[1] - 30), avail=core_stud)}
    return bow.pair_up(side, P, fixed)


_MADE = {}                      # the forebody's cone panels' parts (hull frame), for the lips


def _cone_panels(model, parent, plan, names, prefix: str, side: int):
    sname = "port" if side < 0 else "stbd"
    for name in names:
        p = plan["P"][name]
        sub = model.submodel(f"{prefix}_{name}_{sname}",
                             f"The forebody's quarter: panel {name}, {sname}")
        if name in bow.LIP_UNDER:          # its lip clears the panel under it
            p.lip_avoid = _MADE.get((bow.LIP_UNDER[name], side), [])
        elif name in bow.LIP_OVER:         # its studs under the lip stay bare
            bow.prepare_lip(p, plan["P"][bow.LIP_OVER[name]])
        items = bow.panel_parts(p, plan["grid"][name], plan["diag"][name])
        _MADE[(name, side)] = [(q[0], p.M @ q[2]) for q in items]
        if plan["bars"].get(name):
            items += bow._to_local(p.M, [(q[0], q[1], q[2], "bars", None)
                                         for q in plan["bars"][name]])
        bow.emit(sub, items, caption=f"Panel {name}: plates, wedge plates, tiles", connected=True)
        parent.step(f"Clip panel {name} on" if side < 0 else "")
        bow.use_M(parent, sub, p.M, insert=tuple(np.round(p.n, 6)))


def _place(parent, items, caption: str = "", per_step: int = 12):
    for k, it in enumerate(items):
        part, role, M = it[:3]
        ins = it[3] if len(it) > 3 else None
        if k % per_step == 0:
            parent.step(caption if k == 0 else "")
        pl = parent.place(part, role, (0, 0, 0), insert=ins)
        pl.M = np.asarray(M, float)


def _fixed_items(plan, side: int) -> list:
    out = []
    for line in ("chine_up", "chine_lo", "ridge", "keel"):
        for k in plan["used"].get(line, []):
            parts = plan["fixed"][line][k][0]
            ins = {"chine_up": None, "chine_lo": (0, 1, 0)}.get(line, (0, 0, side))
            out += [(p, r, M, ins) for p, r, M in parts]
    return out


# ------------------------------------------------------------------ the ridge before the wheelhouse
RIDGE_X = (-740.0, X_WH)          # aft of the crest's front foot, up to the wheelhouse's front


def _crest_bottoms() -> dict:
    """{column: y of the crest arch's band's underside} (naut_body.crest_plan), its feet's
    columns (standing on the deck) as None."""
    import naut_body as nb
    cols, levels, bottoms, _ = nb.crest_plan()
    foot = set(getattr(nb, "CREST_FOOT_I", ()))
    return {i: (None if i in foot else -8.0 * b + 8.0) for i, b in zip(cols, bottoms)}


def ridge_levels() -> dict:
    """{column: (y of the wall's top, wide)}: the ridge between the cone's E panels' top edges,
    on the deck strip. Where it can, a plate four studs wide over the panels' edges (its
    underside over their faces) with tiles on it; under the crest arch's band, two studs wide,
    its tiles level with E's face over its edge (or just under the band)."""
    E = fwd_plan(-1)["P"]["E"]
    crest = _crest_bottoms()
    base = shp.DECK_STRIP - 8                 # the deck strip's plates' top (-168)
    out = {}
    for i in range(int(RIDGE_X[0] // S), int(RIDGE_X[1] // S)):
        x = S * i + S / 2
        if i in crest and crest[i] is None:
            continue                          # the crest's foot stands here
        yb = 8 * math.floor((min(bow._surf_y(E, x - 10, -26.0), bow._surf_y(E, x + 10, -26.0))
                             - 0.5) / 8)
        if crest.get(i) is None or yb - 16 >= crest[i]:
            if yb + 8 <= base:
                out[i] = (yb, True)
                continue
        y = 8 * math.ceil((bow._surf_y(E, x, -20.0) - 2) / 8)
        if crest.get(i) is not None:
            y = max(y, crest[i])
        if y + 8 <= base - 8:                 # at least a plate and a tile
            out[i] = (y + 8, False)
    return out


def ridge_items() -> list:
    """The ridge: plates and bricks two studs wide on the deck strip, then four studs wide
    plates and tiles on them (or two studs wide tiles)."""
    lv = ridge_levels()
    base = shp.DECK_STRIP - 8
    cells = {(i, n) for i, (t, _) in lv.items() for n in range(int(t // 8), int(base // 8))}
    out = [(part, CORE, bow._M(R, (x, ytop, 0.0)), None) for part, R, (x, ytop)
           in bow.pack_wall(cells)]
    out.sort(key=lambda it: -it[2][1, 3])
    wide = sorted(i for i, (t, w) in lv.items() if w)
    runs = []
    for i in wide:
        if runs and runs[-1][-1] == i - 1 and lv[i][0] == lv[runs[-1][-1]][0] and len(runs[-1]) < 2:
            runs[-1].append(i)
        else:
            runs.append([i])
    for r in runs:
        t = lv[r[0]][0]
        xm = S * r[0] + S * len(r) / 2
        plate, tile = ("3020", "87079") if len(r) == 2 else ("3710", "2431")
        out.append((plate, ROLE, bow._M(rot(y=90), (xm, t - 8, 0.0)), None))
        out.append((tile, ROLE, bow._M(rot(y=90), (xm, t - 16, 0.0)), None))
    for i, (t, w) in sorted(lv.items()):
        if not w:
            out.append(("3069b", ROLE, bow._M(rot(y=90), (S * i + S / 2, t - 8, 0.0)), None))
    return out


# ------------------------------------------------------------------ the prismatic upper panels
def chine_bar_items(side: int) -> list:
    """The bars on the side keels for the prismatic a panels (as naut_frame.chain_bars): two
    plates and a plate with a bar on its end at each hinge."""
    import naut_frame as frame
    B = pn.FACETS["a"].P
    out = []
    for x in P_HINGES["a"][0]:
        for n in (1, 2):
            out.append(("3023", ROLE, transform((x, shp.FL_A - 8 * n, side * (B[0] - 30)),
                                                rot(y=90)), None))
        out.append((pn.BAR, ROLE, frame.bar_M(x, shp.FL_A - 24, B[0] - 30, side), None))
    return out


def _prismatic(model, parent, side: int):
    sname = "port" if side < 0 else "stbd"
    late = []
    for key in "ab":
        f = pn.FACETS[key]
        x0, x1 = P_UP
        lips = {"a": (True, True), "b": (False, True)}[key]
        sub, M, tl = pn.build_panel(model, f"q_panel_{key}_{sname}",
                                    f"The forebody's quarter: panel {key}, {sname}", f, side,
                                    x0, x1, hinges=P_HINGES[key], lips=lips,
                                    ribs=(key in PRISM_RIB, False))   # over the cone's A
        nrm = tuple(np.round(pn.vec3(f.nrm, side), 6))
        parent.step()
        bow.use_M(parent, sub, M, insert=nrm)
        late += [(p, Mt, nrm) for p, Mt in tl]
    if late:
        parent.step("Tiles over the hinges along the seam")
        for p, Mt, nrm in late:
            parent.place(p, ROLE, (0, 0, 0), insert=nrm).M = Mt


# ------------------------------------------------------------------ the afterbody
# From the midbody (x 360) aft the hull narrows to the tail's stock. Each of the midbody's four
# facets goes on at its own angle (so the sections match at x 360), as one long thin panel of the
# midbody's thickness: a over the side keels and c under them, hung on clips on the side keels'
# studs along lines converging on the tail (a 2:9, c 1:4), b on the deck strip's bars and d on
# clips on the core's side studs along a keel line rising aft (2:9). Those slopes put the
# creases between the facets at a wedge plate's angle: 1:6 on a and 1:3 on b, 1:4 on d. The
# shallower panel laps over the steeper one's edge (b over a, d over c), its free edge straight
# along the crease (a run of wedge plates under its tiles, EdgePanel); the steeper one's edge
# runs on under it. c ends at the tail's station in a curved wedge (SWEEPS). Over the side
# keels the pillows (PILLOWS, AFT_UPPER "p") take a's and b's place; aft of the after deck the
# stern's top steps down to the tail's stock between their lenses.
AFT = tuple(shp.QUARTERS[1])                  # (360, 880)
AFT_ON = True
AFT_BARS = (390.0, 450.0, 510.0)              # the deck strip's bars for b (hw 80 to 560)
AFT_UPPER = "p"                               # over the side keels: the pillow ("p") or a, b
AFT_LOWER = "c"                               # under them: c (or a lower pillow "q": NOTES)
AFT_BELLY = "" if AFT_LOWER == "q" else "d"   # (a lower pillow would reach the keel strip)
if AFT_UPPER == "ab":
    DECK_BARS = DECK_BARS + AFT_BARS
A_DEG, B_DEG, C_DEG, D_DEG = 71.764, 30.829, 70.604, 29.795    # the midbody's facets
AFT_CHINE = dict(stud=(450.0, 150.0), slope=(2, 9), spacers=1)  # a's hinge: side keels' studs
AFT_CHINE_LO = dict(stud=(430.0, 150.0), slope=(1, 4))         # c's, under the side keels
AFT_KEEL = dict(through=(650.0, 98.0), slope=(2, 9))           # d's: core side studs
AFT_END = {"a": 1000.0, "b": AFT[1], "c": 1000.0, "d": 840.0}    # (d leaves c room aft)
OVER = {"b": "a"} if AFT_UPPER == "ab" else {}                       # who laps whom
if AFT_BELLY:
    OVER["d"] = AFT_LOWER
UNDER = {v: k for k, v in OVER.items()}
LAP = (4.0, 14.0, 7.0)        # a lapping panel's edge past the crease: least, most, aim
EDGE_K = {"a": (6, 4, 3), "b": (3,), "c": (6, 4, 3, 2), "d": (4,)}   # its wedges' slopes 1:k
JUMP = {"a": None, "c": 2000.0}              # the price of a step in a lapped panel's edge
STRIP_TO = {"b": 740.0}       # b runs on as a strip two rows wide over a's top edge to here,
                              # where a's top edge comes in under the deck strip's edge
TOP_AIM = {"a": 141.0}        # a's top edge, where it shows: up under the deck's edge, no higher
TAIL_BOT = 84.0                               # the tail's stock's underside (its first columns)


def _sec(deg: float, up: bool) -> np.ndarray:
    """A facet's section direction (port): from its outer hinge line, up (or down) inward."""
    th = math.radians(deg)
    return np.array([0.0, -math.sin(th) if up else math.sin(th), math.cos(th)])


def _outward(p, n) -> np.ndarray:
    return n if (np.asarray(p, float) - np.array([p[0], 0.0, 0.0])) @ n > 0 else -n


def _stud_line(spec: dict, y: float):
    """A hinge line 20 outboard of a line of the side keels' studs (port), at height y."""
    p, q = spec["slope"]
    sl = p / q
    xs, zs = spec["stud"]
    zb = zs + 20 * math.sqrt(1 + sl * sl)
    return bow.Line((xs, y, -zb), bow.unit(np.array([1.0, 0.0, sl])))      # |z| shrinks aft


@lru_cache(maxsize=None)
def aft_lines() -> dict:
    """The afterbody's hinge lines (port, hull frame)."""
    xk, yk = AFT_KEEL["through"]
    p, q = AFT_KEEL["slope"]
    ks = p / q
    return dict(chine=_stud_line(AFT_CHINE, -14.0 - 8 * AFT_CHINE["spacers"]),
                chine_lo=_stud_line(AFT_CHINE_LO, 18.0),
                keel=bow.Line((xk, yk + 20 * math.sqrt(1 + ks * ks), -bow.W_SPINE),
                              np.array([1.0, -ks, 0.0])),
                deck=bow.Line((360.0, -166.0, -90.0), np.array([1.0, 0.0, 0.0])))


AFT_LINE = {"a": "chine", "b": "deck", "c": "chine_lo", "d": "keel"}
AFT_DEG = {"a": (A_DEG, True), "b": (B_DEG, True), "c": (C_DEG, False), "d": (D_DEG, False)}


@lru_cache(maxsize=None)
def aft_planes() -> dict:
    """{facet: (point, outward normal)} (port): the hinge planes of a, b, c and d."""
    L = aft_lines()
    out = {}
    for k, (deg, up) in AFT_DEG.items():
        line = L[AFT_LINE[k]]
        n = bow.unit(np.cross(line.d, _sec(deg, up)))
        out[k] = (line.p, _outward(line.p, n))
    return out


def _mirror(pn_, side):
    p, n = pn_
    if side < 0:
        return np.asarray(p, float), np.asarray(n, float)
    return np.asarray(p, float) * (1, 1, -1), np.asarray(n, float) * (1, 1, -1)


def _aft_forbid(pts) -> bool:
    """Boxes (hull-frame corners) reaching the core or the spine, the deck strip and the after
    deck on it, over the stern's top line, the keel strip or the tail's side keels."""
    for p in pts:
        x, y, z = p[0], p[1], abs(p[2])
        if z < 24.0:
            return True                       # the core, the stern's ridge and keel, the spine
        if x < DECK_END + 2 and -196 < y < -151.5 and z < shp.deck_hw(min(x, DECK_END - 1)) + 0.5:
            return True                       # the deck strip and the after deck on it
        if y < _top_limit(x):
            return True                       # over the after deck's top, the stern's cap
        if x < 524 and y > 144 and z < 64:
            return True                       # the keel strip and the inverted tiles under it
        if x > 878 and -18 < y < 18:
            return True                       # the tail's side keels
        if x > 858 and y > TAIL_BOT:
            return True                       # under the tail's stock
    return False


# The stern's top (x 780 .. 880, aft of the after deck; the hull leaves its stern ridge out for
# it): tiles on the core's top, on plates stepping down to the tail's stock, over the a panels'
# top edges (four to eight studs wide; two between the pillows' lenses or the stern's sweeps).
STERN_TOP = True
DECK_END = shp.QUARTER_DECK_AFT               # the deck strip's end (x 780)
STERN_COLS = tuple(range(int(DECK_END // S), int(AFT[1] // S)))
STERN_TILE_TOP = {39: -144.0, 40: -144.0, 41: -144.0, 42: -128.0, 43: -120.0}
# with the pillows or the stern's sweeps (CURVED_STERN) the cap is two studs wide, on the core
# between them, and its last two columns are a curved slope 2 x 2 (its high end at y -144) rolling
# down toward the tail's stock
STERN_SLOPE = (42, "15068", -144.0)          # (first column, part, top of its high end)


def _stern_slope_cols() -> set:
    if not CURVED_STERN or STERN_SLOPE is None:
        return set()
    return {STERN_SLOPE[0], STERN_SLOPE[0] + 1}


@lru_cache(maxsize=None)
def stern_cap() -> dict:
    """{column: (core's top y, riser plates, the cap's underside y, its half-width)}."""
    out = {}
    for i in STERN_COLS:
        x = S * i + S / 2
        core = rel.core_top(x)
        yb = STERN_TILE_TOP[i] + 8
        if i in _stern_slope_cols():          # the curved slope's base (16 under its top)
            yb = STERN_SLOPE[2] + 16
        risers = int(round((core - yb) / 8))
        assert risers >= 0, f"stern cap {i} under the core's top"
        out[i] = (core, risers, yb, 0.0)
    return out


def _top_limit(x: float) -> float:
    """The afterbody's panels stay under this y: the after deck's top, the stern's cap."""
    if x < DECK_END:
        return -194.0
    if x < 880:
        return stern_cap()[int(x // S)][2] - 1.0
    return shp.top(min(x, 1000.0)) - 2


def stern_items(hw: dict) -> list:
    """The stern's cap: risers on the core, then a tile across each column, wide enough to
    reach over both a panels' top edges ({column: half-width})."""
    out = []
    slope = _stern_slope_cols()
    for i, (core, risers, yb, _) in sorted(stern_cap().items()):
        x = S * i + S / 2
        if i in slope and i != STERN_SLOPE[0]:
            continue                          # (the slope's second column: done with its first)
        if i in slope:                        # risers 2 x 2 under the curved slope, and a
            for n in range(risers):           # plate more under its high half (its underside
                out.append(("3022", CORE, bow._M(np.eye(3), (x + S / 2, core - 8 * (n + 1), 0.0)),
                            None))            # steps up a plate there)
            out.append(("3023", CORE, bow._M(rot(y=90), (x, yb - 8, 0.0)), None))
            R = bow.orient((0.0, 0.0, 1.0), (0.0, 1.0, 0.0), (-1.0, 0.0, 0.0))  # high end fwd
            out.append((STERN_SLOPE[1], ROLE, bow._M(R, (x + S / 2, yb, 0.0)), None))
            continue
        for n in range(risers):
            out.append(("3023", CORE, bow._M(rot(y=90), (x, core - 8 * (n + 1), 0.0)), None))
        tile = {20: "3069b", 40: "2431", 60: "6636", 80: "4162"}[hw[i]]
        out.append((tile, ROLE, bow._M(rot(y=90), (x, yb - 8, 0.0)), None))
    return out


# ------------------------------------------------------------------ edge panels
def _edge_z(segs, xl: float):
    """The free edge's local z at local x xl (None off its columns)."""
    for i0, i1, h0, h1 in segs:
        if S * i0 - 1e-6 <= xl <= S * i1 + 1e-6:
            return S * h0 + S * (h1 - h0) * (xl - S * i0) / (S * (i1 - i0))
    return None


class EdgePanel(bow.FlatPanel):
    """A thin panel (the midbody's thickness: a carrier layer of plates, tiles on it) hung on
    one hinge line, its grid along it (FlatPanel's frame), its free edge a polyline through the
    grid's corners: runs along a row line and diagonal runs at 1:k, each step a wedge plate
    (k x 2), so the edge is a straight line: in the carrier layer, its full row under the tiles
    and its triangle bare a plate under them, or (top_wedges) on the carrier in the tiles'
    layer, its full row's studs bare. `segs`: [(i0, i1, h0, h1)]: from column line i0 to i1 the
    edge runs from row line h0 to h1 (equal, or one apart over k = i1 - i0 columns)."""

    def __init__(self, name, side, hinge, normal, toward, cut, x0, segs=()):
        super().__init__(name, side, hinge, normal, toward, lambda w: True, cut=cut, rows=14,
                         x0=x0, thin=True)
        self.segs = tuple(segs)

    def edge_z(self, xl: float):
        return _edge_z(self.segs, xl)

    @lru_cache(maxsize=None)
    def layout(self):
        skin, wedges = set(), []
        for i0, i1, h0, h1 in self.segs:
            if h0 == h1:
                skin |= {(i, j) for i in range(i0, i1) for j in range(h0)}
                continue
            full = min(h0, h1) - 1
            wedges.append(dict(i0=i0, i1=i1, full=full, k=i1 - i0,
                               wide=S * (i1 if h1 > h0 else i0)))
            skin |= {(i, j) for i in range(i0, i1) for j in range(full)}
        skin = {(i, j) for i, j in skin
                if self.station_ok(S * i, S * i + S, S * j, S * j + S, -18.0, -10.0)}
        carrier = {(i, j) for i, j in skin if j >= 1
                   and self.station_ok(S * i, S * i + S, S * j, S * j + S, -10.0, -2.0)
                   and (j > 1 or self.station_ok(S * i, S * i + S, S * j, S * j + S, 6.0, 6.0))}
        def fits(w):                     # its full row, and its triangle's three corners
            j0, xw = S * w["full"], w["wide"]
            xn = S * w["i0"] if xw == S * w["i1"] else S * w["i1"]
            return self.station_ok(S * w["i0"], S * w["i1"], j0, j0 + S, -18.0, -2.0) and all(
                self.station_ok(x - 0.01, x + 0.01, z - 0.01, z + 0.01, -18.0, -2.0)
                for x, z in ((xn, j0 + S - 0.5), (xw, j0 + S), (xw, j0 + 2 * S - 0.5)))
        ok = [w for w in wedges if fits(w)]
        for w in ok:                     # on top of the carrier (not next to row 0: its tiles
            j = w["full"]                # need row 1), where the carrier can be under it
            w["top"] = getattr(self, "top_wedges", False) and j >= 2 and all(
                self.station_ok(S * i, S * i + S, S * j, S * j + S, -10.0, -2.0)
                for i in range(w["i0"], w["i1"])) and min(
                self.world(S * i, 0.0, S * j)[0] for i in (w["i0"], w["i1"])) >= \
                getattr(self, "top_from", -1e9)
        keep = getattr(self, "keep_col", None)        # (the stern's sweeps take the rest)
        if keep is not None:
            ok = [w for w in ok if all(keep(i) for i in range(w["i0"], w["i1"]))]
            skin = {(i, j) for i, j in skin if keep(i)}
            carrier = {(i, j) for i, j in carrier if keep(i)}
        wcells = {(i, w["full"]) for w in ok for i in range(w["i0"], w["i1"])}
        tcells = {(i, w["full"]) for w in ok if w["top"] for i in range(w["i0"], w["i1"])}
        carrier |= {(i, j) for i, j in tcells
                    if self.station_ok(S * i, S * i + S, S * j, S * j + S, -10.0, -2.0)}
        return dict(skin=skin | wcells, wedges=ok, carrier=carrier, wcells=wcells,
                    tcells=tcells, full=skin | wcells)

    def wedge_part(self, w) -> tuple:
        """(part, local 4x4) of the wedge plate for a run's step: its full row `full`, its
        triangle the row over it, wide at x = `wide`."""
        k = w["k"]
        xc = S * (w["i0"] + w["i1"]) / 2
        zc = S * (w["full"] + 1.0)
        sig = 1 if w["wide"] > xc else -1
        full_pt = (xc, zc - 10)
        wide_pt = (w["wide"] - sig * 5, zc + 10 - 3)
        narrow_pt = (w["wide"] - sig * (S * k - 5), zc + 10 + 6)
        for part in bow.WEDGES[k]:
            poly0 = bow.top_outline(part)
            for deg in (90, -90):
                R = bow.Ry(deg)
                poly = np.array([(R @ np.array([p[0], 0, p[1]]))[[0, 2]] for p in poly0]) + (xc, zc)
                if bow.inside(poly, full_pt) and bow.inside(poly, wide_pt) and \
                        not bow.inside(poly, narrow_pt):
                    return part, bow._M(R, (xc, -18.0 if w.get("top") else -10.0, zc))
        raise AssertionError(f"{self.name}: no wedge plate fits {w}")

    def thin_parts(self, grid_cols, shift: int = 0) -> list:
        """Plates over the carrier's cells and the wedge plates (-10 .. -2), tiles over them
        (-18 .. -10); the skin's cells with no carrier under them (row 0 along the hinge) under
        tiles two rows deep, resting on the row next to them; the grid edge's clips under row 1."""
        lay = self.layout()
        car = lay["carrier"]
        out, piece = [], {}
        sizes = [sz for sz in bow.PANEL_PLATES if sz[0] <= 2]
        rects = []
        for w in lay["wedges"]:          # under a wedge on top: a plate two rows deep (it bonds
            j = w["full"]                # the wedge's row to the one under it; every third try)
            box = {(i, jj) for i in range(w["i0"], w["i1"]) for jj in (j - 1, j)}
            if w["top"] and box <= car and (2, w["k"]) in bow.PLATE and shift % 3 == 2:
                rects.append((w["i0"], w["i1"] - 1, j - 1, j))
                car = car - box
        rects += kit_pack(car, sizes, prefer="xz"[shift % 2], shift=shift // 2) if car else []
        for n, (i0, i1, j0, j1) in enumerate(rects):
            part, R = bow.rect_part(bow.PLATE, i1 - i0 + 1, j1 - j0 + 1)
            out.append((part, ROLE, bow._M(R, (S * (i0 + i1 + 1) / 2, -10.0,
                                               S * (j0 + j1 + 1) / 2)), "carrier", None))
            for i in range(i0, i1 + 1):
                for j in range(j0, j1 + 1):
                    piece[(i, j)] = n
        for n, w in enumerate(lay["wedges"]):
            part, M = self.wedge_part(w)
            out.append((part, ROLE, M, "tiles" if w["top"] else "carrier", None))
            for i in range(w["i0"], w["i1"]):
                if not w["top"]:
                    piece[(i, w["full"])] = ("w", n)
        studs = set(piece) - lay["tcells"]
        done, pairs = set(), {}
        for i, j in sorted(lay["skin"] - studs - lay["tcells"]):
            for dj in (1, -1):
                if (i, j + dj) in studs and (i, j + dj) not in done:
                    pairs.setdefault((j, dj), []).append(i)
                    done |= {(i, j), (i, j + dj)}
                    break
        for (j, dj), cols in sorted(pairs.items()):
            jl = min(j, j + dj)
            k, first = 0, True
            while k < len(cols):
                run = [cols[k]]
                most = 1 + (shift // 7) % 4 if first else 4    # (the runs' joints move)
                first = False
                while k + 1 < len(cols) and cols[k + 1] == run[-1] + 1 and len(run) < most:
                    k += 1
                    run.append(cols[k])
                k += 1
                start, left = run[0], len(run)
                while left > 0:
                    ln = 4 if left >= 4 else (2 if left >= 2 else 1)
                    if ln == 1:
                        out.append(("3069b", ROLE, bow._M(rot(y=90), (S * start + 10, -18.0,
                                                                      S * jl + S)), "tiles", None))
                    else:
                        part, R = bow.rect_part(bow.TILE, ln, 2)
                        out.append((part, ROLE, bow._M(R, (S * start + 10 * ln, -18.0, S * jl + S)),
                                    "tiles", None))
                    start += ln
                    left -= ln
        rest = studs - done
        for i0, i1, j0, j1 in kit_pack(rest, bow.PANEL_TILES, below=piece,
                                       prefer="xz"[(shift // 2) % 2], shift=shift // 4,
                                       bridge=True):
            part, R = bow.rect_part(bow.TILE, i1 - i0 + 1, j1 - j0 + 1)
            out.append((part, ROLE, bow._M(R, (S * (i0 + i1 + 1) / 2, -18.0,
                                               S * (j0 + j1 + 1) / 2)), "tiles", None))
        for i in grid_cols:
            out.append((bow.CLIP1, bow.CLIP_ROLE, bow._M(np.eye(3), (S * i + 10, -2.0, 30.0)),
                        "clips", (0, 1, 0)))
        return out


def _aft_frame(name: str, side: int, x0: float, segs=()) -> EdgePanel:
    L = aft_lines()
    line = L[AFT_LINE[name]]
    p, n = _mirror(aft_planes()[name], side)
    if side > 0:
        line = line.mirror()
    deg, up = AFT_DEG[name]
    sec = _sec(deg, up)
    if side > 0:
        sec = sec * (1, 1, -1)
    toward = line.at_x(600.0) + 60 * (sec if name != "b" else -sec)
    if name == "d":
        toward = line.at_x(600.0) - 60 * sec * np.array([1.0, -1.0, 1.0])
    cut = dict(x_min=AFT[0], x_max=AFT_END[name], forbid=_aft_forbid)
    return EdgePanel(name, side, line, n, toward, cut, x0, segs)


@lru_cache(maxsize=None)
def _phase(name: str, side: int) -> float:
    """The world x of a grid column line on the hinge such that the column crossing x 360 does
    so halfway up the panel (the joint with the midbody's panel)."""
    if name == "b":
        return 360.0
    P = _aft_frame(name, side, 360.0)
    # the column line at local x = 0 over the panel's height (rows 0 .. 6) and depth: its least
    # x on 360 (the panel's first column then starts right at the midbody's panel's end)
    xs = [(P.R @ np.array([0.0, y, z]))[0] - (P.R @ np.array([0.0, 0.0, 10.0]))[0]
          for y in (-18.0, -10.0, 6.0) for z in (0.0, JOINT_Z[name])]
    return 360.0 - min(xs) + 0.02


JOINT_Z = {"a": 120.0, "c": 120.0, "d": 200.0}     # how far up each panel reaches at x 360


def _loc(P, w) -> np.ndarray:
    return (np.linalg.inv(P.M) @ np.append(np.asarray(w, float), 1.0))[:3]


def _plane_z(P, xl: float, yl: float, Q, yq: float) -> float:
    """Local z on panel P (at its local x xl, layer yl) of the line where P meets panel Q's
    layer yq."""
    f = lambda z: _loc(Q, P.world(xl, yl, z))[1] - yq
    a, b = f(0.0), f(100.0)
    return -a * 100.0 / (b - a)


def _free_z(P, xl: float, z_to: float = 300.0, tiles_only: bool = False) -> float:
    """How far up its rows panel P may reach at local x xl: the top of the longest run of z its
    layers may fill (row 0, along the hinge, only its tiles' layers; `tiles_only`: only its
    tiles' layer anywhere), -1 if none."""
    runs, start = [], None
    z = 0.0
    while z <= z_to:
        bare = z < S or tiles_only
        ok = P.station_ok(xl - 0.01, xl + 0.01, z, z + 0.01, -18.0, -10.0 if bare else -2.0)
        if ok and not bare and z <= 2 * S:          # (the clips' layer: under row 1 only)
            ok = P.station_ok(xl - 0.01, xl + 0.01, z, z + 0.01, 6.0, 6.0)
        if ok and start is None:
            start = z
        elif not ok and start is not None:
            runs.append((start, z - 1.0))
            start = None
        z += 1.0
    if start is not None:
        runs.append((start, z_to))
    if not runs:
        return -1.0
    return max(runs, key=lambda r: r[1] - r[0])[1]


def fit_edge(ia: int, ib: int, zmax, zmin, target, ks, pen: float = 4000.0, hmax: int = 13,
             jump: float = None):
    """The free edge's polyline from column line ia to ib: through grid corners (S i, S h),
    runs along a row line (one column) or wedges up or down a row over k columns, staying
    under zmax(x) and (as far as it can) over zmin(x), as near target(x) as it can with as few
    changes of direction as it can (dynamic programme); `jump`: the price of a step of a row
    at a column line (None: no steps). [(i0, i1, h0, h1)], or None."""
    INF = float("inf")
    cost, back = {}, {}

    def seg_cost(i, n, h0, h1):
        xs = np.linspace(S * i, S * (i + n), 4 * n + 1)
        c = 0.0
        for x in xs:
            z = S * h0 + S * (h1 - h0) * (x - S * i) / (S * n)
            if z > zmax(x) + 0.01:
                return INF
            short = zmin(x) - z
            if short > 0.01:                     # short of the least: allowed, at a price
                c += 400.0 * short + 40.0 * short ** 2
            c += 5.0 * (target(x) - z) ** 2
        return c
    for h in range(2, hmax + 1):                  # two rows at least: the hinge's and a carrier
        cost[(ia, h, "s")] = 0.0
    kinds = ["s", "f"] + [(d, k) for d in "ud" for k in ks]
    for i in range(ia, ib):
        for h in range(0, hmax + 1):
            for t in kinds:
                c0 = cost.get((i, h, t), INF)
                if c0 == INF:
                    continue
                moves = [("f", 1, h)]
                jp = jump(S * i) if callable(jump) else jump
                if jp is not None:
                    moves += [("j", 1, h + dh) for dh in (-1, 1) if 2 <= h + dh <= hmax]
                for k in ks:
                    if h >= 2 and h + 1 <= hmax:
                        moves.append((("u", k), k, h + 1))
                    if h - 1 >= 2:
                        moves.append((("d", k), k, h - 1))
                for mt, n, h1 in moves:
                    if i + n > ib:
                        continue
                    if mt == "j":                 # a step at the column line, then flat
                        if S * max(h, h1) > zmax(S * i) + 0.01:
                            continue
                        sc = seg_cost(i, 1, h1, h1)
                        sc = sc + jp if sc < INF else INF
                    else:
                        sc = seg_cost(i, n, h, h1)
                    if sc == INF:
                        continue
                    c = c0 + sc + (pen if t not in ("s", mt) else 0.0)
                    key = (i + n, h1, "f" if mt == "j" else mt)
                    if c < cost.get(key, INF):
                        cost[key] = c
                        back[key] = (i, h, t)
    ends = [(c, k) for k, c in cost.items() if k[0] == ib]
    if not ends:
        return None
    _, k = min(ends)
    segs = []
    while k in back:
        p = back[k]
        seg = (p[0], k[0], p[1], k[1])
        if k[2] == "f" and p[1] != k[1]:      # a step, then flat
            seg = (p[0], k[0], k[1], k[1])
        segs.append(seg)
        k = p
    return list(reversed(segs))


def _edge_pts(P, segs, yl: float) -> list:
    """World points along a panel's free edge (its layer yl)."""
    return [P.world(xl, yl, _edge_z(segs, xl))
            for xl in np.linspace(S * segs[0][0], S * segs[-1][1],
                                  4 * (segs[-1][1] - segs[0][0]) + 1)]


@lru_cache(maxsize=None)
def aft_edges(side: int) -> dict:
    """The afterbody's panels' free edges {facet: segs}: each lapping panel's along the crease
    (LAP past it), then the lapped one's under it (up to the crease, past the lapping edge),
    and where nothing laps over it, as near as it may go to what it meets."""
    F = {f: _aft_frame(f, side, _phase(f, side)) for f in "abcd"}
    F.update({f: pillow_panel(side, f) for f in ("p", "q") if f in (AFT_UPPER, AFT_LOWER)})
    out = {}
    memo = {}

    def free(P, x, tiles_only=False):
        key = (P.name, round(x, 3), tiles_only)
        if key not in memo:
            memo[key] = _free_z(P, x, tiles_only=tiles_only)
        return memo[key]

    def lapped(P, Q, segs, low):
        """The lapped panel Q: under the lapping one's (P's) underside, past its edge."""
        cre_q = lambda x, P=P, Q=Q: _plane_z(Q, x, -18.0, P, -2.0)
        lp = np.array(sorted((_loc(Q, w)[0], _loc(Q, w)[2])
                             for w in _edge_pts(P, segs, -2.0)))
        x_lo, x_hi = lp[0, 0], lp[-1, 0]
        covered = lambda x: x_lo - 10 <= x <= x_hi + 10

        def zmax(x):
            if covered(x):
                return min(free(Q, x), cre_q(x) - 1.0)
            # where it shows: a last row of tiles alone may reach on past the carrier's
            return min(free(Q, x, True), free(Q, x) + S)

        def zmin(x):
            if x_lo <= x <= x_hi:
                return min(float(np.interp(x, lp[:, 0], lp[:, 1])) + 4.0, cre_q(x) - 9.0)
            return 0.0

        def tgt(x):
            return cre_q(x) - 3.0 if covered(x) else min(zmax(x) - 2.0, TOP_AIM.get(low, 1e9))
        qcols = [i for i in range(*Q.cols_range)
                 if all(free(Q, x) >= 2 * S for x in (S * i, S * i + S))]
        run = _run_at_joint(Q, qcols)
        jumps = JUMP[low]
        if callable(jumps):
            jumps = (lambda f, Q: (lambda xl: f(Q.world(xl, 0.0, 10.0)[0])))(jumps, Q)
        segs_q = fit_edge(run[0], run[-1] + 1, zmax, zmin, tgt, EDGE_K[low],
                          jump=jumps)           # under the lapping edge it may step
        assert segs_q, f"afterbody: no edge for {low} over columns {run[0]} .. {run[-1]}"
        out[low] = segs_q

    for top, low in OVER.items():
        P, Q = F[top], F[low]
        if top in ("p", "q"):                   # a pillow: a rectangle, its far edge straight
            out[top] = [(min(P.cols), max(P.cols) + 1, P.cfg["rows"], P.cfg["rows"])]
            segs = out[top]
            lapped(P, Q, segs, low)
            continue
        cre = lambda x, P=P, Q=Q: _plane_z(P, x, -2.0, Q, -18.0)
        # its columns: in range, room for two rows past the hinge, and enough crease to lap
        tail = STRIP_TO.get(top)                # (on as a strip two rows wide to here)

        def in_tail(i):
            return tail is not None and max(P.world(x, 0.0, 10.0)[0]
                                            for x in (S * i, S * i + S)) <= tail + 0.01
        cols = [i for i in range(*P.cols_range)
                if all(free(P, x) >= max(2 * S, cre(x) + LAP[0]) and
                       (cre(x) + LAP[1] >= 2 * S or in_tail(i)) for x in (S * i, S * i + S))]
        run = _run_at_joint(P, cols)
        segs = fit_edge(run[0], run[-1] + 1, lambda x: min(free(P, x), max(cre(x) + LAP[1], 2 * S)),
                        lambda x: cre(x) + LAP[0], lambda x: cre(x) + LAP[2], EDGE_K[top],
                        pen=60000.0)            # its edge shows: as straight as it can be
        assert segs, f"afterbody: no edge for {top}"
        out[top] = segs
        if low in ("p", "q"):
            continue                            # (a pillow: a rectangle, its edge straight)
        lapped(P, Q, segs, low)
    return out


def _run_at_joint(P, cols) -> list:
    """The contiguous run of columns that holds the column at the joint (x 360)."""
    def x_of(i):
        return P.world(S * i + 10, 0.0, 10.0)[0]
    first = min(cols, key=lambda i: abs(x_of(i) - 370.0))
    run = [first]
    while run[-1] + 1 in cols:
        run.append(run[-1] + 1)
    while run[0] - 1 in cols:
        run.insert(0, run[0] - 1)
    return run


TOP_WEDGES = "abd"             # their wedge plates on top (studs out, like rivets),
                              # so the edge is straight in the face's own layer (a's only aft
                              # of b: under b's lap they stay under the tiles)


@lru_cache(maxsize=None)
def aft_panel(name: str, side: int) -> EdgePanel:
    """The afterbody's facet a, b, c or d: its thin edge panel (or "p": the pillow)."""
    if name in ("p", "q"):
        return pillow_panel(side, name)
    p = _aft_frame(name, side, _phase(name, side), aft_edges(side)[name])
    p.top_wedges = name in TOP_WEDGES
    if name in UNDER:
        p.top_from = STRIP_TO.get(UNDER[name], -1e9)
    if name in SWEEPS:                    # it ends where the stern's sweeps begin
        front, sig = sweep_front(name, side), p.sig
        p.keep_col = (lambda i: S * i + S <= front + 0.01) if sig > 0 else \
            (lambda i: S * i >= front - 0.01)
    return p


# ------------------------------------------------------------------ the stern's swept flanks
# The stern's sweeps (with the faceted a panels, AFT_UPPER "ab"): aft of x 700 each a panel ends
# in the stern's flank: two big curved wedges (41749 / 41750, Brick Wedged Curved 8 x 3 x 2
# Open) built into its end, one over the other on its rows 1..3 and 4..6, their tall edges
# together and their sloped edges toward the side keels and the stern's top, so the flank's
# section is a rounded lens sweeping 48 LDU in over six studs. Each c panel ends at the station
# in a curved wedge 6 x 2 (41747 / 41748) on its row 1 sweeping in under the side keels. The
# panel stops at the roots' forward face (EdgePanel.keep_col); the roots sit flush with its
# tiles, on a plate two plates under its carrier (P2, under a 6 x 2's tall column only: its
# flank's root has no room for studs), hung from the carrier by a plate (P1). `root`: the port
# panel's local x of the roots' middle (starboard: the same world x); `lens`: (row of the tall
# column, which way the flank slopes, pair); `rows`: P1's rows.
SWEEP_8 = ("41749", "41750")           # Brick Wedged Curved 8 x 3 x 2 Open (flank at -x / +x)
SWEEP_6 = ("41747", "41748")           # Brick Wedged Curved 6 x 2 (flank at -x / +x)
SWEEPS = {"a": dict(root=360.0, lens=((3, "down", SWEEP_8), (4, "up", SWEEP_8)), rows=(1, 6)),
          "c": dict(root=-520.0, lens=((1, "up", SWEEP_6),), rows=(1, 1))}
if AFT_UPPER == "p":                  # (the pillows end in their own big curved wedges)
    del SWEEPS["a"]
if AFT_LOWER == "q":
    del SWEEPS["c"]
CURVED_STERN = bool(SWEEPS) or AFT_UPPER == "p"   # the stern's top narrow, the stock a wrist


@lru_cache(maxsize=None)
def sweep_root(name: str, side: int) -> float:
    """The panel-local x of the sweeps' roots' middle (port: SWEEPS root; starboard: the
    column line nearest the same world x)."""
    x0 = SWEEPS[name]["root"]
    if side < 0:
        return x0
    Pp, Ps = _aft_frame(name, -1, _phase(name, -1)), _aft_frame(name, 1, _phase(name, 1))
    wx = Pp.world(x0, 0.0, 30.0)[0]
    return min(np.arange(-800.0, 800.0, S), key=lambda x: abs(Ps.world(x, 0.0, 30.0)[0] - wx))


def sweep_front(name: str, side: int) -> float:
    """The panel-local x of the sweeps' roots' forward face (the panel ends there)."""
    sig = _aft_frame(name, side, _phase(name, side)).sig
    return sweep_root(name, side) - sig * S


def sweep_items(p) -> list:
    """The sweeps and the plates they stand on, in panel p's frame: [(part, role, M, cat,
    insert)]."""
    cfg = SWEEPS[p.name]
    xr, sig = sweep_root(p.name, p.side), p.sig
    front = xr - sig * S
    r0, r1 = cfg["rows"]
    out = []
    # the plate under the carrier's last two columns (P1), and under it plates reaching on
    # under the roots (P2): under a 6 x 2's tall column only (its flank's root has no room
    # for studs under it)
    held = set()                              # rows whose roots stand on P2 at the roots
    for row0, flank, pair in cfg["lens"]:
        held |= {row0} if pair == SWEEP_6 else \
            {row0 + d * (1 if flank == "up" else -1) for d in range(3)}
    xp = front - sig * S                      # P1's middle (its two columns)
    out.append((*_plate(2, r1 - r0 + 1, xp, -2.0, r0), "sweep_base", (0, 1, 0)))
    runs, cur = [], []
    for j in range(r0, r1 + 1):
        if cur and ((j in held) != (cur[-1] in held) or len(cur) == 6):
            runs.append(cur)
            cur = []
        cur.append(j)
    runs.append(cur)
    for run in runs:                          # P2: four columns long where it holds roots
        if run[0] in held:
            out.append((*_plate(4, len(run), front, 6.0, run[0]), "sweep_base", (0, 1, 0)))
        else:
            out.append((*_plate(2, len(run), xp, 6.0, run[0]), "sweep_base", (0, 1, 0)))
    ey = np.array([0.0, 1.0, 0.0])            # the wedges' tops face out (local -y)
    ez = np.array([-float(sig), 0.0, 0.0])    # their tips aft
    ex = np.cross(ey, ez)                     # (0, 0, sig): +x_part up the panel for sig > 0
    R = np.column_stack([ex, ey, ez])
    for row0, flank, pair in cfg["lens"]:
        up = flank == "up"
        part = pair[1] if (up == (sig > 0)) else pair[0]
        out.append((part, ROLE, bow._M(R, (xr, -18.0, S * row0 + S / 2)), "sweep", None))
    return out


def _plate(w: int, d: int, xm: float, y: float, j0: int) -> tuple:
    """(part, role, M) of a plate w columns long (local x, centred on xm) and d rows deep from
    row j0, its top at y (a panel's frame)."""
    part, R = bow.rect_part(bow.PLATE, w, d)
    return part, ROLE, bow._M(R, (xm, y, S * j0 + S * d / 2))


def sweep_world(side: int) -> list:
    """The sweeps' parts in the hull frame: [(part, M)]."""
    out = []
    for name in SWEEPS:
        p = aft_panel(name, side)
        out += [(it[0], p.M @ it[2]) for it in sweep_items(p)]
    return out


# ------------------------------------------------------------------ the afterbody's pillows
# Over the side keels the afterbody is one curved panel a side, a PILLOW ("p"): hinged on clips
# on the side keels' studs (on two spacer plates) along a line converging 1:PILLOW_K on the
# tail, parallel to the side keels' edge, its top row resting on the deck strip, which narrows
# under it (naut_shape.AFT_DECK_EDGE). It is a long rectangle, so everything on it runs straight
# along it: on its carrier, curved bricks along each edge, their high ends inward (4 x 2,
# 93606, every two columns; or 3 x 1, 50950, every column), and between them two plates and
# tiles at their height: seen end on, the panel is an arch, the hull's section rounded. Its end
# is two big curved wedges (41749 / 41750) on rows `lens_row` and the next (their roots three
# rows wide each), tall edges together: the arch's own section, closing in 48 LDU over eight
# studs, their tips by the after deck's end clear of the core; a curved slope 2 x 2 falls aft
# beside their roots from the edge band's end. (A lower pillow "q" hung under the side keels in
# place of c and d was tried: rigid and level, it cannot follow the belly rising to the tail,
# and its far edge needs the keel strip narrowed under it; see NOTES.)
PILLOW_ON = True
PILLOW_K = 4                                  # their hinges converge 1:K in plan
PILLOW_PHASE = 4.5                            # their columns' phase: their fronts at x 360
PILLOW_LENS = True
PILLOWS = {
    "p": dict(rows=10, band=4, chine=dict(stud=(370.0, 170.0), slope=(1, PILLOW_K), spacers=2),
              which="up", x=(AFT[0], 640.0), rest=-178.0, lens_row=3),
    # the lower one (AFT_LOWER "q", in place of c and d): hung under the side keels, its far
    # edge tucked over the keel strip, which must then narrow under it (not in this build)
    "q": dict(rows=10, band=4, chine=dict(stud=(370.0, 170.0), slope=(1, 6)),
              which="lo", x=(AFT[0], 480.0), tuck=147.5),
}
BAND_PART = {4: "93606", 3: "50950"}
PILLOW_X = PILLOWS["p"]["x"]                  # (the upper one's columns: world x at its hinge)
PILLOW_CHINE = PILLOWS["p"]["chine"]


@lru_cache(maxsize=None)
def pillow_line(side: int, name: str = "p"):
    """A pillow's hinge (a Line, port; mirrored for starboard)."""
    cfg = PILLOWS[name]
    if cfg["which"] == "up":
        L = _stud_line(cfg["chine"], -14.0 - 8 * cfg["chine"]["spacers"])
    else:
        L = _stud_line(cfg["chine"], 18.0)
    return L if side < 0 else L.mirror()


@lru_cache(maxsize=None)
def pillow_theta(name: str = "p") -> float:
    """A pillow's angle (radians from the horizontal, across it): the upper one's so its top
    row's underside (local y -2, z 180 .. 200) just clears the deck's tiles."""
    cfg = PILLOWS[name]
    if "theta" in cfg:
        return math.radians(cfg["theta"])
    B = pillow_line(-1, name).at_x(AFT[0])
    if "tuck" in cfg:              # the lower one: its bottom edge's outer face at y `tuck`
        lo, hi = 0.1, 1.5          # (just over the keel strip, whose edge hides it)
        for _ in range(60):
            th = (lo + hi) / 2
            y = B[1] + (S * cfg["rows"] - 10) * math.sin(th) + 14.0 * math.cos(th)
            if y > cfg["tuck"]:
                hi = th
            else:
                lo = th
        return (lo + hi) / 2
    lo, hi = 0.3, 1.5
    for _ in range(60):
        th = (lo + hi) / 2
        y = B[1] - (S * (cfg["rows"] - 1) - 10) * math.sin(th) - 2 * math.cos(th)
        if y < cfg["rest"]:
            hi = th
        else:
            lo = th
    return (lo + hi) / 2


def pillow_axes(side: int, name: str = "p") -> tuple:
    """(along, across the panel away from its hinge, outward normal) unit vectors, hull frame."""
    L = pillow_line(side, name)
    d = bow.unit(L.d if L.d[0] > 0 else -L.d)
    ew = bow.unit(np.array([-d[2], 0.0, d[0]]))         # horizontal, square to it, outward
    if ew[2] * side < 0:
        ew = -ew
    away = np.array([0.0, -1.0 if PILLOWS[name]["which"] == "up" else 1.0, 0.0])
    th = pillow_theta(name)
    ez = -math.cos(th) * ew + math.sin(th) * away
    n = math.sin(th) * ew + math.cos(th) * away
    return d, ez, n


class PillowPanel(bow.FlatPanel):
    """A pillow (see PILLOW_ON): FlatPanel's frame on its hinge, its rows, its columns those
    wholly within its x range (an even number), and past its aft end two columns for the big
    curved wedges' roots."""

    def __init__(self, side: int, name: str = "p"):
        cfg = PILLOWS[name]
        self.cfg = cfg
        L = pillow_line(side, name)
        d, ez, n = pillow_axes(side, name)
        B = L.at_x(AFT[0])
        x0, x1 = cfg["x"]
        super().__init__(name, side, L, n, B + 50 * ez, lambda w: True,
                         cut=dict(x_min=x0, x_max=x1 + 400.0, forbid=None),
                         rows=cfg["rows"], x0=AFT[0] + PILLOW_PHASE, thin=True)
        R = cfg["rows"]
        cols = [i for i in range(*self.cols_range)
                if all(x0 - 0.01 <= self.world(x, 0.0, z)[0] <= x1 + 0.01
                       for x in (S * i, S * i + S) for z in (0.0, S * R))]
        cols.sort(key=lambda i: self.sig * i)          # from the joint aft
        if len(cols) % 2:
            cols = cols[:-1]
        self.cols = sorted(cols)
        aft = cols[-1]
        self.lens_cols = sorted([aft + self.sig, aft + 2 * self.sig]) if PILLOW_LENS else []

    def __hash__(self):
        return id(self)

    @lru_cache(maxsize=None)
    def layout(self):
        R = self.cfg["rows"]
        skin = {(i, j) for i in self.cols for j in range(R)}
        carrier = {(i, j) for i in self.cols for j in range(1, R)}
        carrier |= {(i, j) for i in self.lens_cols for j in range(1, R - 1)}
        return dict(skin=skin, wedges=[], carrier=carrier, full=set(skin))

    def thin_parts(self, grid_cols, shift: int = 0) -> list:
        """Its parts in its frame: the carrier (plates four rows wide over rows 1 .. 4, then the
        rest, on into the big curved wedges' roots, and a row of plates over its last row), two
        layers of plates over the middle rows bonding them, tiles on those; the curved bricks
        on the carrier along both edges; the big curved wedges; the clips under row 1."""
        from naut_kit import AV
        R, band = self.cfg["rows"], self.cfg["band"]
        out = []
        lens = list(self.lens_cols)
        cols = list(self.cols)
        along = sorted(cols + lens)

        def runs(n_cols, lengths, first):
            seq, left = [], n_cols
            if first and first < left:
                seq.append(first)
                left -= first
            while left > 0:
                ln = next((q for q in lengths if q <= left and left - q != 1), 1)
                seq.append(ln)
                left -= ln
            return seq

        def strip(c0, n_cols, j0, depth, y, lengths, first, cat):
            for ln in runs(n_cols, lengths, first):
                part, Rp = bow.rect_part(bow.PLATE, ln, depth)
                out.append((part, ROLE, bow._M(Rp, (S * c0 + S * ln / 2, y, S * j0 + S * depth / 2)),
                            cat, None))
                c0 += ln

        def ok_len(depth):
            return [q for q in (12, 10, 8, 6, 4, 3, 2) if (min(depth, q), max(depth, q)) in bow.PLATE
                    and AV.ok(bow.PLATE[(min(depth, q), max(depth, q))], ROLE)]

        c0, n_all = along[0], len(along)
        c1, n_p = cols[0], len(cols)
        # the carrier: four rows wide from row 1, the rest of the rows, then the last row alone
        strip(c0, n_all, 1, 4, -10.0, ok_len(4), 8, "carrier")
        if R - 2 > 4:
            strip(c0, n_all, 5, R - 6, -10.0, ok_len(R - 6), 6, "carrier")
        strip(c1, n_p, R - 1, 1, -10.0, ok_len(1), 4, "carrier")
        mid = R - 2 * band                             # the flat middle rows
        if mid > 0:
            strip(c1, n_p, band, mid, -18.0, ok_len(mid), 4, "middle")
            strip(c1, n_p, band, mid, -26.0, ok_len(mid), 6, "middle")
            tl = [q for q in (6, 4, 2) if (mid, q) in bow.TILE and AV.ok(bow.TILE[(mid, q)], ROLE)]
            for ln in runs(n_p, tl, 0):
                part, Rt = bow.rect_part(bow.TILE, ln, mid)
                out.append((part, ROLE, bow._M(Rt, (S * c1 + S * ln / 2, -34.0, S * (band + mid / 2))),
                            "tiles", None))
                c1 += ln
        R180 = np.diag([-1.0, 1.0, -1.0])
        bp = BAND_PART[band]
        step = 2 if band == 4 else 1                   # (93606 is two wide, 50950 one)
        for k in range(0, len(cols), step):            # the curved bricks along both edges
            xc = S * cols[k] + S * step / 2
            out.append((bp, ROLE, bow._M(np.eye(3), (xc, -34.0, S * band / 2)), "bands", None))
            out.append((bp, ROLE, bow._M(R180, (xc, -34.0, S * R - S * band / 2)), "bands", None))
        if lens:                                       # the big curved wedges
            sig = self.sig
            ey = np.array([0.0, 1.0, 0.0])
            ez = np.array([-float(sig), 0.0, 0.0])        # their tips aft
            Rw = np.column_stack([np.cross(ey, ez), ey, ez])
            xr = S * min(lens) + S
            r0 = self.cfg.get("lens_row", R // 2 - 1)
            for row, up in ((r0, False), (r0 + 1, True)):
                part = SWEEP_8[1] if (up == (sig > 0)) else SWEEP_8[0]
                out.append((part, ROLE, bow._M(Rw, (xr, -34.0, S * row + S / 2)), "lens", None))
            rest = sorted(set(range(1, R - 1)) - set(range(r0 - 2, r0 + 4)))
            if len(rest) == 2 and rest[1] == rest[0] + 1:   # beside their roots: a curved
                ry = bow.Ry(-90 * sig)                        # slope falling aft from the
                out.append(("15068", ROLE, bow._M(ry, (xr, -10.0, S * rest[1])), "lens", None))
            else:                                             # band's end, or tiles
                for j in rest:
                    part, Rt = bow.rect_part(bow.TILE, 2, 1)
                    out.append((part, ROLE, bow._M(Rt, (xr, -18.0, S * j + S / 2)), "lens", None))
        for i in grid_cols:
            out.append((bow.CLIP1, bow.CLIP_ROLE, bow._M(np.eye(3), (S * i + 10, -2.0, 30.0)),
                        "clips", (0, 1, 0)))
        return out


@lru_cache(maxsize=None)
def pillow_panel(side: int, name: str = "p") -> PillowPanel:
    return PillowPanel(side, name)


def pillow_world(side: int) -> list:
    """The pillows' parts in the hull frame (without their clips): [(part, M)]."""
    out = []
    for name in ("p", "q"):
        if name in (AFT_UPPER, AFT_LOWER):
            p = pillow_panel(side, name)
            out += [(it[0], p.M @ it[2]) for it in p.thin_parts([]) if it[3] != "clips"]
    return out


def pillow_row_w(x: float, row: int, side: int = -1) -> tuple:
    """(|z|, y) of the pillow's underside (local y -2) at a row's middle, at world x."""
    p = pillow_panel(side)
    inv = np.linalg.inv(p.M)
    xl = (inv @ np.array([x, 0.0, 0.0, 1.0]))[0]
    w = p.world(xl, -2.0, S * row + 10)
    # (a point at that local x is at a slightly different world x up the panel: close enough)
    return abs(w[2]), w[1]


def _flange_clip(x, zs, L, which: str, side: int, spacers: int = None):
    """A 1 x 1 clip plate on round plates on a side keels' stud (on top, or hanging under),
    turned to line L (its ring on it): (parts, ring point)."""
    stud = np.array([x, 0.0, side * zs])
    perp = bow.unit(np.array([-L.d[2], 0.0, L.d[0]]))
    if perp[2] * side < 0:
        perp = -perp
    R = bow._clip_R(L.d, (0, 1, 0), perp)
    parts = []
    if which == "up":
        sp = AFT_CHINE["spacers"] if spacers is None else spacers
        for n in range(sp):
            parts.append((bow.RP, CORE, bow._M(np.eye(3), (x, -16.0 - 8 * n, side * zs))))
        y = -16.0 - 8 * sp
    else:
        parts.append((bow.RP, CORE, bow._M(np.eye(3), (x, 8.0, side * zs))))
        y = 16.0
    parts.append((bow.CLIP1, bow.CLIP_ROLE, bow._M(R, (x, y, side * zs))))
    pt = stud + 20 * perp
    pt[1] = y + 2
    return parts, pt


def _side_clip(x, ys, L, up: bool, side: int):
    """A clip plate on a round plate on the core's side stud at (x, ys), its ring on line L 20
    over (or under) the stud: (parts, ring point)."""
    stud = np.array([x, ys, side * 20.0])
    perp = bow.unit(np.array([-L.d[1], L.d[0], 0.0]))
    if (perp[1] < 0) != up:
        perp = -perp
    ey = np.array([0.0, 0.0, -side])
    R = bow._clip_R(L.d, ey, perp)
    Rs = bow.orient((1.0, 0.0, 0.0), ey)
    parts = [(bow.RP, CORE, bow._M(Rs, (x, ys, side * 28.0))),
             (bow.CLIP1, bow.CLIP_ROLE, bow._M(R, (x, ys, side * 36.0)))]
    pt = stud + 20 * perp
    pt[2] = side * bow.W_SPINE
    return parts, pt


def _on_line(L, pt, tol=0.05) -> bool:
    return np.linalg.norm(np.cross(np.asarray(pt, float) - L.p, L.d)) < tol


def _line_studs(spec: dict) -> list:
    """The side keels' studs (x, |z|) on a hinge line's stud line."""
    p, q = spec["slope"]
    xs, zs = spec["stud"]
    return [(xs + 20 * q * m, zs - 20 * p * m) for m in range(-6, 12)]


@lru_cache(maxsize=None)
def aft_plan(side: int) -> dict:
    """The afterbody's panels a, b, c, d on one side, their clips and bars."""
    L = {k: (v if side < 0 else v.mirror()) for k, v in aft_lines().items()}
    upper, lower = AFT_UPPER, AFT_LOWER
    if upper == "p":
        L["chine"] = pillow_line(side, "p")
    if lower == "q":
        L["chine_lo"] = pillow_line(side, "q")
    P = {f: aft_panel(f, side) for f in upper + lower + AFT_BELLY}
    fixed = {"chine": [], "chine_lo": [], "keel": []}
    chine = PILLOWS["p"]["chine"] if upper == "p" else AFT_CHINE
    chine_lo = PILLOWS["q"]["chine"] if lower == "q" else AFT_CHINE_LO
    for line, spec, which in (("chine", chine, "up"), ("chine_lo", chine_lo, "lo")):
        for x, z in _line_studs(spec):
            if AFT[0] + 50 < x < AFT[1] - 30 and 30 < z < shp.flange_hw(x) - 20:
                fixed[line].append(_flange_clip(x, z, L[line], which, side,
                                                spacers=spec.get("spacers")))
    xk, yk = AFT_KEEL["through"]
    p, q = AFT_KEEL["slope"]
    for m in range(-4, 5):
        x, y = xk + 20 * q * m, yk - 20 * p * m           # up a course every q columns
        if AFT[0] < x < AFT[1] and core_stud(x, y):
            fixed["keel"].append(_side_clip(x, y, L["keel"], False, side))
    for line in fixed:
        for parts, pt in fixed[line]:
            assert _on_line(L[line], pt), f"aft {line} clip off its line"
    bars, grid, used, own = [], {f: [] for f in P}, {k: [] for k in fixed}, {f: [] for f in P}
    spans = {k: [] for k in fixed}

    def bar_ok(line):
        def ok(a, b):
            ta, tb = bow._axial(L[line], a), bow._axial(L[line], b)
            lo, hi = min(ta, tb) - 8, max(ta, tb) + 8
            if hi - lo > max(bow.BARS):
                return False
            n = next(n for n in sorted(bow.BARS) if n >= hi - lo)
            mid = (ta + tb) / 2
            return all(mid + n / 2 < s0 - 1 or mid - n / 2 > s1 + 1 for s0, s1 in spans[line])
        return ok

    def commit(line):
        def c(a, b):
            ta, tb = bow._axial(L[line], a), bow._axial(L[line], b)
            part = bow._bar(L[line], a, b)
            n = next(n for n, q in bow.BARS.items() if q == part[0])
            spans[line].append(((ta + tb) / 2 - n / 2, (ta + tb) / 2 + n / 2))
            bars.append(part)
        return c

    def clear_of_sweeps(f, ok):
        """No grid clip under the sweeps' hanging plates (two columns forward of the roots)."""
        if f not in SWEEPS:
            return ok
        front, sig = sweep_front(f, side), P[f].sig
        inv = np.linalg.inv(P[f].M)

        def ok2(a, b):
            xa, xb = ((inv @ np.append(w, 1.0))[0] for w in (a, b))
            return min(sig * (front - xa), sig * (front - xb)) > 2 * S + 14 and ok(a, b)
        return ok2

    for line, f in (("chine", upper[0]), ("chine_lo", lower), ("keel", "d")):
        if f not in P:
            continue
        pts = [(pt, parts[-1][2]) for parts, pt in fixed[line]]
        for i, partner, own_pt in bow._grid_cols(P[f], pts, own[f],
                                                  clear_of_sweeps(f, bar_ok(line)),
                                                  commit(line)):
            grid[f].append(i)
            own[f].append((bow.CLIP1, bow._grid_clip_M(P[f], i)))
            used[line].append(next(k for k, (parts, pt) in enumerate(fixed[line])
                                   if np.allclose(pt, partner)))
    if "b" in P:                       # b: clips on its hinge edge onto the deck strip's bars
        b = P["b"]
        inv = np.linalg.inv(b.M)
        for x in AFT_BARS:
            u = (inv @ np.array([x, -166.0, side * 90.0, 1.0]))[0]
            i = int(math.floor(u / 20))
            if (i, 1) in b.layout()["carrier"]:
                grid["b"].append(i)
    return dict(P=P, fixed=fixed, used=used, bars=bars, grid=grid, lines=L)


def _aft_items(side: int) -> list:
    """The afterbody's frame clips (hull frame)."""
    pl = aft_plan(side)
    out = []
    for line in ("chine", "chine_lo", "keel"):
        for k in pl["used"][line]:
            ins = {"chine": None, "chine_lo": (0, 1, 0)}.get(line, (0, 0, side))
            out += [(p, r, M, ins) for p, r, M in pl["fixed"][line][k][0]]
    return out


def _aft_bars(side: int) -> list:
    return [(p, r, M) for p, r, M in aft_plan(side)["bars"]]


def _check_covered(p, items) -> None:
    """Every cell of an edge panel's face is under a tile or a wedge plate on top (none left
    out as a stray piece)."""
    cov = set()
    for part, _, M, _, _ in items:
        if abs(M[1, 3] + 18.0) > 0.5:
            continue
        lo, hi = bow._engine().geom.mesh(bow.canon(part)).bbox
        c = np.array([[x, 0, z] for x in (lo[0], hi[0]) for z in (lo[2], hi[2])]) @ \
            M[:3, :3].T + M[:3, 3]
        cov |= {(i, j) for i in range(int(math.floor(c[:, 0].min() / S + 0.01)),
                                      int(math.ceil(c[:, 0].max() / S - 0.01)))
                for j in range(int(math.floor(c[:, 2].min() / S + 0.01)),
                               int(math.ceil(c[:, 2].max() / S - 0.01)))}
    missing = p.layout()["skin"] - cov
    assert not missing, f"afterbody panel {p.name}{p.side}: cells left bare {sorted(missing)}"


def _aft_panels(model, parent, side: int, names: str):
    sname = "port" if side < 0 else "stbd"
    pl = aft_plan(side)
    for name in names:
        p = pl["P"][name]
        items = bow.panel_parts(p, pl["grid"][name], [])
        if not items:
            continue
        if name not in ("p", "q"):
            _check_covered(p, items)
        if name in SWEEPS:
            items = items + sweep_items(p)
        sub = model.submodel(f"q_aft_{name}_{sname}", f"The afterbody's quarter: panel {name}, "
                                                       f"{sname}")
        bow.emit(sub, items, caption=f"Panel {name}: plates, wedge plates and tiles",
                 connected=True)
        parent.step(f"Clip panel {name} on" if side < 0 else "")
        bow.use_M(parent, sub, p.M, insert=tuple(np.round(p.n, 6)))


def stern_widths() -> dict:
    """{stern column: half-width of its cap}: over both a panels' top edges there."""
    out = {}
    for i in STERN_COLS:
        reach = 0.0
        if CURVED_STERN:                      # the cap stays on the core between the lenses
            out[i] = 20
            continue
        for side in (-1, 1):
            p = aft_panel("a", side)
            lo, hi = p.segs[0][0], p.segs[-1][1]
            for xl in np.linspace(S * lo, S * hi, 8 * (hi - lo) + 1):
                w = p.world(xl, -18.0, p.edge_z(xl))
                if S * i <= w[0] <= S * i + S:
                    reach = max(reach, abs(w[2]))
        out[i] = next(hw for hw in (20, 40, 60, 80) if hw >= reach - 0.5)
    return out


# ------------------------------------------------------------------ building
def _clip_cells(items) -> set:
    """Cells (i, k) of the side keels' top studs that the clips and bars take."""
    out = set()
    for it in items:
        part, M = it[0], it[2]
        if abs(M[1, 3] - (shp.FL_A - 8)) > 0.5 or abs(M[1, 0]) > 1e-6:
            continue                       # only what stands on the side keels' top
        lo, hi = bow._engine().geom.mesh(bow.canon(part)).bbox
        c = np.array([[x, 0, z] for x in (lo[0], hi[0]) for z in (lo[2], hi[2])]) @ \
            M[:3, :3].T + M[:3, 3]
        for i in range(int(math.floor(c[:, 0].min() / S)), int(math.ceil(c[:, 0].max() / S))):
            for k in range(int(math.floor(c[:, 2].min() / S)), int(math.ceil(c[:, 2].max() / S))):
                out.add((i, k))
    return out


def flange_tiles(parent, taken: set, coming=()):
    """Tiles on the side keels' bare top studs in the quarters (those under the panels can't
    go on after them), except the cells the clips and bars will take and the studs the parts
    `coming` [(part, role, M, ...)] (the clips' stacks) will stand over."""
    from naut_kit import exposed_studs, tile_studs
    flat = [(p, M) for p, _, M in parent.flatten_local()] + [(it[0], it[2]) for it in coming]
    studs = [st for st in exposed_studs(
        flat, keep=lambda x, y, z: abs(y - shp.FL_A) < 0.5 and any(a <= x < b for a, b in
                                                                   shp.QUARTERS))
        if (int(math.floor(st[0] / S)), int(math.floor(st[2] / S))) not in taken]
    tile_studs(parent, studs, caption="Tiles on the side keels in the quarters")


# ------------------------------------------------------------------ the core's bare side studs
SIDE_TILES = (700.0, 880.0, -50.0)    # x range and the lowest course: seen past the a panels'
                                      # top edges under the after deck's end and the stern's cap
SIDE_TILES_LO = None                  # (x range under the side keels)
if CURVED_STERN:                      # (and every course between the lenses' tips and the tail,
    SIDE_TILES = ((PILLOW_X[1] - 40.0) if AFT_UPPER == "p" else 700.0, 880.0, 0.0)
                                      # (and under the side keels aft of the d panels)
    SIDE_TILES_LO = ((AFT_END["d"] if AFT_BELLY else PILLOWS["q"]["x"][1] - 40.0), 880.0)


def side_stud_tiles(parent, extra=(), course=None) -> None:
    """Tiles on the core's side studs that nothing took, where they show (SIDE_TILES): turned on
    their sides, 1 x 2 where two studs stand side by side. `extra` [(part, M)]: parts still to
    come (the pillows, the stern's sweeps) that the tiles must clear. `course`: (y0, y1, True) only the
    studs with y in [y0, y1], (y0, y1, False) all but those."""
    from naut_kit import bbox, connectors
    x0, x1, y_low = SIDE_TILES
    flat = [(p, np.asarray(M, float)) for p, _, M in parent.flatten_local()]
    holes, boxes = [], []
    for j, (part, M) in enumerate(flat):
        for c in connectors(part, M):
            if c.kind == "cyl" and c.gender == "F":
                holes.append((j, np.asarray(c.origin, float)))
        lo, hi = bbox(part)
        cor = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1])
                        for z in (lo[2], hi[2])]) @ M[:3, :3].T + M[:3, 3]
        boxes.append((cor.min(0) + 0.6, cor.max(0) - 0.6))
    studs = []
    for j, (part, M) in enumerate(flat):
        for c in connectors(part, M):
            if c.kind != "cyl" or c.gender != "M" or abs(abs(c.axis[2]) - 1) > 1e-6 or not c.secs:
                continue
            if abs(c.secs[0][1] - 6) > 0.7:
                continue
            p = np.asarray(c.origin, float)
            lo_ok = SIDE_TILES_LO is not None and SIDE_TILES_LO[0] <= p[0] <= SIDE_TILES_LO[1] \
                and p[1] > 8.0
            if course is not None and (course[0] <= p[1] <= course[1]) != course[2]:
                continue
            if not ((x0 <= p[0] <= x1 and p[1] < y_low or lo_ok) and abs(p[2]) < 30):
                continue
            if any(k != j and np.linalg.norm(h - p) < 1.5 for k, h in holes):
                continue
            n = np.sign(c.axis[2])
            lo = p + np.array([-10.5, -10.5, 0.0]) + np.array([0, 0, min(0.5 * n, 10.0 * n)])
            hi = p + np.array([10.5, 10.5, 0.0]) + np.array([0, 0, max(0.5 * n, 10.0 * n)])
            if any(k != j and np.all(lo < b1) and np.all(b0 < hi) for k, (b0, b1) in
                   enumerate(boxes)):
                continue
            # it goes on from outside: nothing in its way out to 40 LDU (the side keels' tiles
            # stand in the way of the lowest course's)
            lo2, hi2 = lo.copy(), hi.copy()
            lo2[2], hi2[2] = (lo[2], hi[2] + 40.0) if n > 0 else (lo[2] - 40.0, hi[2])
            if any(k != j and np.all(lo2 < b1) and np.all(b0 < hi2) for k, (b0, b1) in
                   enumerate(boxes)):
                continue
            Mt = bow._M(bow.orient((1.0, 0.0, 0.0), (0.0, 0.0, -float(n))), p + (0, 0, 8 * n))
            if any(np.linalg.norm(np.asarray(Me)[:3, 3] - p) < 200 and bow._clash("3070b", Mt, pe, Me)
                   for pe, Me in extra):
                continue                      # under a sweep: it hides them
            studs.append((round(p[0], 2), round(p[1], 2), round(p[2], 2), int(n)))
    studs = sorted(set(studs))
    done, first = set(), True
    for st in studs:
        if st in done:
            continue
        x, y, z, n = st
        pair = (round(x + S, 2), y, z, n)
        R = bow.orient((1.0, 0.0, 0.0), (0.0, 0.0, -float(n)))
        if pair in studs and pair not in done:
            part, xc = "3069b", x + S / 2
            done |= {st, pair}
        else:
            part, xc = "3070b", x
            done.add(st)
        if first:
            parent.step("Tiles on the core's bare side studs by the stern")
            first = False
        pl = parent.place(part, ROLE, (0, 0, 0), insert=(0, 0, n))
        pl.M = bow._M(R, (xc, y, z + 8 * n))


# ------------------------------------------------------------------ the gull wing's hinge
# The salon's gull wing turns on the deck's bars at its top edge, so it can't lap over them:
# along its hinge there is a slot between the deck's edge and the wing (the wing's top edge
# swings through the space over the bars). Under the deck's edge in the salon a strip of plates
# two studs wide hangs from the deck strip's underside, half under the slot: with the wing shut
# it closes the slot's view into the lit salon; the wing swings up and away from it.
BAFFLE_Y = shp.DECK_STRIP + 8                # the deck strip's underside (its lower plates')


def baffle_items() -> list:
    """The plates under the deck's port edge along the gull wing (clear of its hinge plates
    and the salon's lamp): [(part, role, M, insert)]."""
    import naut_panels as pn
    from naut_kit import AV, PLATE, rect_part
    hinges = pn.hinge_x("b", *pn.BAY)[1]
    lamp = (shp.SALON_C[0] - 20, shp.SALON_C[0] + 20)
    k_in = int(-shp.DECK_HW // S)                # the deck's outermost row (port)
    cols = []
    for i in range(int((pn.BAY[0] + 10) // S), int((pn.BAY[1] - 30) // S)):
        x = S * i + S / 2
        if any(abs(x - h) < 25 for h in hinges) or lamp[0] - 10 < x < lamp[1] + 10:
            continue
        cols.append(i)
    lengths = [n for n in (8, 6, 4, 3, 2, 1) if (2, n) in AV.sizes(PLATE, "hull")
               or (n, 2) in AV.sizes(PLATE, "hull") or n == 1]
    out = []
    runs = []
    for i in cols:
        if runs and runs[-1][-1] == i - 1:
            runs[-1].append(i)
        else:
            runs.append([i])
    for run in runs:                             # plates two studs wide (one under the deck)
        i0, left = run[0], len(run)
        while left:
            n = next(n for n in lengths if n <= left and left - n != 1 or n == left)
            part, R = rect_part(PLATE, n, 2)
            pos = (S * i0 + S * n / 2, BAFFLE_Y, S * (k_in - 1) + S)
            out.append((part, ROLE, transform(pos, R), (0, 1, 0)))
            i0, left = i0 + n, left - n
    return out


def build_quarters(model, parent):
    """Build the quarters' skins onto the hull sub-assembly `parent` (and the plates under the
    gull wing's hinge)."""
    _place(parent, baffle_items(), caption="Plates under the deck's edge along the salon's "
                                           "gull wing")
    plans = {s: fwd_plan(s) for s in (-1, 1)}
    fixed = {s: _fixed_items(plans[s], s) + chine_bar_items(s) for s in (-1, 1)}
    aft = {s: (_aft_items(s) if AFT_ON else []) for s in (-1, 1)}
    coming = fixed[-1] + fixed[1] + aft[-1] + aft[1]
    flange_tiles(parent, _clip_cells(coming), coming)
    for s in (-1, 1) if AFT_ON else ():
        _place(parent, aft[s], caption="The afterbody's quarter: clips on the side keels and "
                                       "the core's side studs")
        _place(parent, _aft_bars(s), caption="Bars in the clips")
    if AFT_ON:                                # (the side keels' tiles stand in the way of
        side_stud_tiles(parent, extra=sweep_world(-1) + sweep_world(1)    # the lowest course's)
                        + pillow_world(-1) + pillow_world(1))
    for s in (-1, 1) if AFT_ON else ():
        _aft_panels(model, parent, s, AFT_LOWER + AFT_BELLY)
    for s in (-1, 1) if AFT_ON else ():
        _aft_panels(model, parent, s, AFT_UPPER)
    if AFT_ON and STERN_TOP:
        _place(parent, stern_items(stern_widths()), caption="The stern's top: tiles over the panels' edges")
    for s in (-1, 1):
        _place(parent, fixed[s],
               caption="The forebody's quarter: clips on the side keels and the core's side "
                       "studs, bars on the side keels")
        _place(parent, [(p, r, M) for p, r, M in plans[s]["bars"]["main"]],
               caption="Bars in the clips")
    _place(parent, ridge_items(), caption="The ridge before the wheelhouse, on the deck strip")
    for s in (-1, 1):
        _cone_panels(model, parent, plans[s], "cC", "q_fwd", s)
    for s in (-1, 1):
        _prismatic(model, parent, s)
    for s in (-1, 1):
        _cone_panels(model, parent, plans[s], "AE", "q_fwd", s)
    first = True
    for name, tiles in sorted(pn.RIB_TILES.items()):    # the ribs over the panels' joints
        for part, M, ins in tiles:
            if first:
                parent.step("Ribs over the joints between the midbody's panels and the "
                            "quarters'")
                first = False
            parent.place(part, ROLE, (0, 0, 0), insert=ins).M = np.asarray(M, float)
    pn.RIB_TILES.clear()
