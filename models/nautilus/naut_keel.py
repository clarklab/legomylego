"""Under the hull and on the deck: the saw keel along the bow, the two keel fins (the stand's
posts meet them), the raised after deck and the hatch abaft the dorsal fin.

* **Saw keel**: a blade two studs wide hanging under the core along the bow, under the traced
  bottom line, its underside a chain of inverted curved slopes and steps, a tooth (an inverted
  45 degree slope each side) under every fourth pair of columns.
* **Keel fins**: fins built sideways (naut_fin) hanging under the keel strip
  (naut_shape.FWD_FIN, REAR_FIN), see KEEL_FINS. The forward post of the stand meets the keel
  strip just ahead of the forward fin, the after one the after fin's keel: post_tops().

Hull frame (naut_shape): LDU, -Y up, bow toward -X."""
from __future__ import annotations

import numpy as np

import naut_relief as rel
import naut_shape as shp
from brickkit.ldraw.matrix import rot, transform
from naut_body import (BAND2, UNDER2, _R_down, chain_band, cols_from, keel_band,
                       profile_band)
from naut_kit import S, Batch

BELLY = shp.KEEL_TOP + 16            # the keel strip's underside (168)
FIN_W = (-1, 0)                      # the fins and the blade: two studs wide


def _bot(line):
    return lambda x: float(np.interp(x, *line))


# ------------------------------------------------------------------ keel fins
# The two keel fins hang under the keel strip (naut_shape.REAR_FIN, FWD_FIN), built sideways like
# a LEGO set's fins (naut_fin): a core one stud thick on the middle line; on each side a face of
# plates and wedge plates on its side studs (the outline: the after fin's trailing edge falling
# at 45 degrees, the forward fin's tail swept aft and its chamfered forefoot), tiled. Over the
# core, in every column, a plate 1 x 2 across (pushed into the keel strip's underside) and a
# jumper under it, the plate's underside pin in the jumper's open stud; the core hangs from the
# jumpers' middles. Under it, jumpers across again: the keel line two studs wide (the after post
# plugs into it, inverted tiles go under the rest). Built upright, from the keel up, and pushed
# up under the hull.
FIN_TOP = BELLY + 16                 # 184: under the plates and jumpers, the faces' top edge
KEEL_FINS = {
    # U0: the face grid's first column's x; core_to: the core's underside (the keel's top)
    "rear": dict(U0=160.0, cols=17, core_to=248.0),
    "fwd": dict(U0=-400.0, cols=18, core_to=264.0),
}


def fin_bottom(which: str) -> float:
    """The keel fin's underside (its keel of jumpers): y."""
    return KEEL_FINS[which]["core_to"] + 8.0


def post_tops() -> tuple:
    """Where the stand's posts meet the hull (hull frame): (x, z, y of the underside) of a
    2 x 2 stud area each: the keel strip's underside ahead of the forward fin, the after fin's
    underside (its keel of jumpers). The forward one is a stud aft of the photo's, clear of the
    bow's end wall, so the lights' lead can come down a shaft in the core to it."""
    xa, xb = shp.POSTS
    xa, xb = S * round(xa / S) + 20, S * round(xb / S)   # (the forward one: clear of the wall)
    return ((xa, 0.0, float(BELLY)), (xb, 0.0, fin_bottom("rear")))


def _fin_face(which: str):
    """The keel fin's port face (naut_fin.Fin, hanging from FIN_TOP, rows counted down)."""
    import naut_fin as nf
    fin = nf.Fin(KEEL_FINS[which]["U0"], FIN_TOP, hanging=True)
    if which == "rear":                             # three rows
        fin.plate(0, 0, 6, 2)
        fin.plate(6, 0, 8, 2)
        fin.plate(0, 2, 8, 1)
        fin.plate(8, 2, 6, 1)
        fin.wedge("2450", 0, 14, 0)                 # the trailing edge: falling 45 degrees
    else:                                           # four rows
        fin.plate(0, 0, 6, 2)
        fin.plate(6, 0, 6, 2)
        fin.plate(12, 0, 3, 2)
        fin.wedge("24307", 2, 15, 0)                # the tail swept aft, 1:2, twice
        fin.wedge("24307", 2, 16, 2)
        fin.wedge("41770", 1, 0, 2)                 # the forefoot, chamfered 1:4
        fin.plate(4, 2, 6, 2)
        fin.plate(10, 2, 6, 2)
    return fin


def keel_fin(model, which: str):
    """A keel fin (see KEEL_FINS): built upright from its keel, pushed up under the keel
    strip."""
    name = "forward" if which == "fwd" else "after"
    spec = KEEL_FINS[which]
    sub = model.submodel(f"keel_fin_{which}", f"The {name} keel fin")
    fin = _fin_face(which)
    fb = fin.build(range(spec["cols"]), core_to=spec["core_to"])
    if fin.unheld:
        print(f"warning: {name} keel fin: face parts {fin.unheld} not held")
    xc = lambda c: spec["U0"] + S * c + S / 2
    top = {c for c, k in fin.core_cells if k == 0}
    last = int(round((spec["core_to"] - FIN_TOP) / 8)) - 1
    bottom = {c for c, k in fin.core_cells if k == last}
    bt = Batch()
    for c in sorted(bottom):
        bt.add("15573", "hull", transform((xc(c), spec["core_to"], 0), rot(y=90)), "fin_base")
    bt.items += fb.items
    for c in sorted(top):
        bt.add("15573", "hull", transform((xc(c), FIN_TOP - 8, 0), rot(y=90)), "fin_top")
        bt.add("3023", "hull", transform((xc(c), BELLY, 0), rot(y=90)), "fin_top2")
    bt.emit(sub, phases=[["fin_base"], ["fin_core"], ["fin_top"], ["fin_top2"], ["fin_port"],
                         ["fin_stbd"], ["fin_tiles"]],
            captions={"fin_base": f"The {name} keel fin, built upright: its keel, jumpers "
                                  "across",
                      "fin_core": "Its core: bricks with studs on both sides, plates",
                      "fin_top": "Jumpers across its top",
                      "fin_top2": "Plates 1 x 2 across on the jumpers (their pins in the "
                                  "jumpers' studs): they go into the keel strip",
                      "fin_port": "The port face: plates and wedge plates on the side studs",
                      "fin_stbd": "The starboard face",
                      "fin_tiles": "Tiles on both faces"}, per_step=10, reach=200)
    return sub


# ------------------------------------------------------------------ the saw keel
# The saw keel: a blade two studs wide hanging under the core from the keel strip's end to the
# ram, a plate or two under the traced bottom line, its underside a chain of inverted curved
# slopes and steps (naut_relief.fit_chain, deepest aft) with a tooth (an inverted 45 degree
# slope each side) under every fourth pair of columns, at a step.
SAW = (-27, -60)                       # its columns, from the keel strip's end to the ram
SAW_TEETH = tuple(range(-30, -60, -4))  # each tooth's aft column
SAW_PIECES = (("flat", (0,), 0, 0.10), ("24201", (0, -1), -1, 0.0), ("drop", (-1,), -1, 0.3),
              ("tooth", (-1, -1), -1, 0.0))


def saw_plan():
    cols = list(range(SAW[0], SAW[1] - 1, -1))
    base = [round(rel.core_bot(S * i + S / 2) / 8) for i in cols]
    t = [shp.bot(S * i + S / 2) / 8 + 1.5 for i in cols]
    forced = {cols.index(i): "tooth" for i in SAW_TEETH}
    depths, pieces = rel.fit_chain(t, [b + 1 for b in base], SAW_PIECES,
                                   range(min(base) + 1, max(base) + 6), forced=forced,
                                   end_w=0.0)
    return cols, depths, base, pieces


SAW_CAPTIONS = {"blade": "The saw keel's blade: plates pushed up under the core",
                "blade_under": "Curved slopes under its steps",
                "teeth": "Its teeth"}


def saw_keel() -> Batch:
    """The saw keel (see SAW), built in place under the core (in the hull's frame): its blade's
    plates pushed up one under another, curved slopes under its steps, then its teeth (emit with
    phases blade, blade_under, teeth, all hanging)."""
    cols, depths, base, pieces = clip_plan(*saw_plan())
    bt = keel_band(cols, depths, base, pieces, d=+1, cat="blade")
    for name, k0, m in pieces:
        if name != "tooth":
            continue
        front = cols[k0 + 1]                    # the tooth's front column
        y = 8 * depths[k0 + 1]
        for k in FIN_W:                         # 45 degree inverted slopes: the upright face aft
            bt.add("2310", "spine", transform((S * front + S / 2, y, S * k + S / 2),
                                              _R_back(-1)), "teeth", insert=(0, 1, 0))
    return bt


def _R_back(sx: int) -> np.ndarray:
    """An inverted slope's local -Z (its full-height end) toward the bow, its body running aft:
    local +Z -> world +X * sx."""
    from naut_kit import orient
    ez = np.array([sx, 0.0, 0.0])
    ey = np.array([0.0, 1.0, 0.0])
    return orient(np.cross(ey, ez), ey, ez)


# ------------------------------------------------------------------ on the deck
def aft_house(model):
    """The raised after deck: two plates over the deck strip, tiles on them (two studs wide, a
    walk, where the deck narrows aft under the quarters' pillows: naut_shape.AFT_DECK_EDGE)."""
    sub = model.submodel("aft_house", "The raised after deck")
    x0, x1, top = shp.AFT_HOUSE
    deck = shp.DECK_STRIP - 8
    cols = cols_from(lambda x: deck - 16, lambda x: deck, x0, x1)
    narrow = shp.QUARTERS_MODULE and shp.AFT_DECK_EDGE
    bt = profile_band(cols, ks=(-1, 0) if narrow else (-3, -2, -1, 0, 1, 2), cat="house")
    bt.emit(sub, phases=[["house"], ["house_top"]],
            captions={"house": "The raised after deck", "house_top": ""}, per_step=12,
            reach=200)
    return sub


HATCH_X = 340.0


def hatch(model):
    """The round hatch abaft the dorsal fin: a round brick with a round tile for its lid."""
    sub = model.submodel("hatch", "The hatch")
    deck = shp.DECK_STRIP - 8
    sub.place("3941", "hull", (HATCH_X, deck - 24, 0))
    sub.step()
    sub.place("14769", "hull", (HATCH_X, deck - 32, 0))
    return sub


# ------------------------------------------------------------------ the stern's spine
# Toward the tail the hull's rows of studs-out plates end one by one along the traced top and
# bottom lines, so the core's top and bottom step down (up) in rows' heights. A spine two studs
# wide on the core's top, from the deck's end to the tail's upper lobe, and one under it, from
# the keel strip's end to the lower lobe, fill those steps (naut_relief.fit_chain: they can
# fall no faster than a plate a column), so the hull's lines run down to the tail smoothly.
STERN_RIDGE = (39, 55)           # its columns (x 780 .. 1120)
STERN_KEEL = (26, 49)            # (x 520 .. 1000)


def stern_ridge_plan():
    cols = list(range(STERN_RIDGE[0], STERN_RIDGE[1] + 1))
    base = [round(-rel.core_top(S * i + S / 2) / 8) for i in cols]
    t = [max(-shp.top(S * i + S / 2) / 8 - 1, b) for i, b in zip(cols, base)]
    levels, pieces = rel.fit_chain(t, base, BAND2, range(min(base), max(base) + 3), end_w=0.0)
    return cols, levels, base, pieces


def clip_plan(cols, levels, base, pieces):
    """A band's plan cut at the bow and tail modules' stations: the columns within the hull
    built here, and the pieces wholly on them."""
    keep = [k for k, i in enumerate(cols) if shp.in_hull(S * i + S / 2)]
    idx = {k: n for n, k in enumerate(keep)}
    pcs = [(name, idx[k0], m) for name, k0, m in pieces
           if all(k in idx for k in range(k0, k0 + m))]
    return [cols[k] for k in keep], [levels[k] for k in keep], [base[k] for k in keep], pcs


def stern_ridge() -> Batch:
    """The stern's ridge, built in place on the core's top (in the hull's frame)."""
    cols, levels, base, pieces = clip_plan(*stern_ridge_plan())
    return chain_band(cols, levels, base, pieces, d=-1, cat="stern_ridge")


def stern_ridge_cells() -> set:
    return {(i, k) for i in clip_plan(*stern_ridge_plan())[0] for k in (-1, 0)}


def stern_keel_plan():
    cols = list(range(STERN_KEEL[0], STERN_KEEL[1] + 1))
    base = [round(rel.core_bot(S * i + S / 2) / 8) for i in cols]
    t = [max(shp.bot(S * i + S / 2) / 8 + 1, b + 1) for i, b in zip(cols, base)]
    depths, pieces = rel.fit_chain(t, [b + 1 for b in base], UNDER2,
                                   range(min(base) + 1, max(base) + 4), end_w=0.0)
    return cols, depths, base, pieces


def stern_keel() -> Batch:
    """The stern's keel, hanging under the core (in the hull's frame)."""
    cols, depths, base, pieces = clip_plan(*stern_keel_plan())
    return keel_band(cols, depths, base, pieces, d=-1, cat="stern_keel")
