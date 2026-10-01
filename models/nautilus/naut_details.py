"""The Nautilus's superstructure and ends: the wheelhouse (an alligator's head, its two round
eye windows looking forward, searchlight eyes over them), the breathers behind it, the toothed
crest arch, the ram, and the fish tail with its propeller and rudder.

Hull frame as naut_shape: side keels centred on y = 0, bow toward -X, port toward -Z. The deck
strip's top is at y = -80."""
from __future__ import annotations

import numpy as np

import naut_shape as shp
from brickkit.ldraw.matrix import rot, transform
from naut_kit import PLATE, S, Batch, ids_of, orient, pack, rect_part, side_R

DECK = shp.DECK_STRIP                # the deck strip's top
FACE_FWD = rot(y=90)                 # a side-stud brick with its side studs facing the bow
SNOT_FWD = orient((0, 0, 1), (1, 0, 0))   # a plate standing on a forward face, studs forward
ACROSS = rot(y=90)                   # a 1 x 2 plate lying across the hull

WH = (-240, -60)                     # the wheelhouse's x range: front face, back
WH_BASE = DECK - 8                   # its base plates' top
WH_FRONT = (-240, -140)              # the head, ahead of the sloping back
WH_C1 = WH_BASE - 24                 # the head's first course's top
WH_C2 = WH_C1 - 24                   # its second course's top
EYE_Y = WH_C1 + 10                   # the eye windows' middle (the front brick's side studs)
EYE_Z = 30                           # on that brick's outer side studs, at the head's corners
VENTS = (-60, 20)                    # the breathers behind it
SEARCHLIGHT_Z = 30


def _plates(bt, cells, top, role, cat, shift=0, below=None):
    sizes = [(1, 1), (1, 2), (1, 3), (1, 4), (1, 6), (2, 2), (2, 3), (2, 4), (2, 6), (4, 4)]
    rects = pack(cells, sizes, below, prefer="x", shift=shift)
    for i0, i1, k0, k1 in rects:
        part, R = rect_part(PLATE, i1 - i0 + 1, k1 - k0 + 1)
        bt.add(part, role, transform((S * (i0 + i1 + 1) / 2, top, S * (k0 + k1 + 1) / 2), R),
               cat)
    return rects


# ------------------------------------------------------------------ wheelhouse
def wheelhouse(model):
    """An alligator's head, low and long, sloping up to its brow: plates four studs wide on
    the deck; at the back two 18-degree slopes rising forward; the head - a brick with four
    studs on its face at the front, 45-degree slopes back to back behind it (the sloped
    sides), and on them another 18-degree slope rising to the brow. The two big
    round eye windows (clear dishes) sit on the front brick's outer studs, at the head's
    corners; two searchlight eyes over them; the crest arch springs from a brick with a stud
    on its side at the brow.""" 
    sub = model.submodel("wheelhouse", "Wheelhouse")
    bt = Batch()
    i0, i1 = int(WH[0] // S), int(WH[1] // S)
    _plates(bt, {(i, k) for i in range(i0, i1) for k in range(-2, 2)}, WH_BASE, "hull", "base")
    xf = WH[0] + 10                                      # the front column's middle
    bt.add("30414", "hull", transform((xf, WH_C1, 0), FACE_FWD), "c1")
    for x in range(WH[0] + 40, WH_FRONT[1], 40):         # the sloped sides, 2 x 2 each
        bt.add("3039", "hull", transform((x, WH_C1, -10)), "c1")
        bt.add("3039", "hull", transform((x, WH_C1, 10), rot(y=180)), "c1")
    for z in (-20, 20):                                  # the back: slopes rising forward
        bt.add("30363", "hull", transform((WH_FRONT[1] + 10, WH_BASE - 24, z), rot(y=-90)),
               "c1")
    # the head's top: an 18-degree slope up to the brow, the arch's brick beside its top end
    bt.add("30363", "hull", transform((WH[0] + 30, WH_C2, 0), rot(y=-90)), "c2")
    bt.add("3024", "hull", transform((xf, WH_C1 - 8, 10)), "c2")      # the arch's brick
    bt.add("87087", "hull", transform((xf, WH_C2 - 8, 10)), "c2")
    for z in (-EYE_Z, EYE_Z):                            # the eye windows, on round plates
        bt.add("4073", "hull", transform((WH[0] - 8, EYE_Y, z), SNOT_FWD), "eyes")
        bt.add("4740", "glass", transform((WH[0] - 16, EYE_Y, z), SNOT_FWD), "eyes", "eye")
    bt.emit(sub, phases=[["base"], ["c1"], ["c2"], ["eyes"]],
            captions={"base": "The wheelhouse", "c1": "The head: its sides slope in",
                      "c2": "Its brow", "eyes": "Two round windows look forward"},
            per_step=8, reach=160)
    return sub


def searchlights(hs):
    """The searchlight eyes on the wheelhouse's head (placed on the hull after the crest, which
    goes on past them)."""
    hs.step("The searchlight eyes")
    for z in (-SEARCHLIGHT_Z, SEARCHLIGHT_Z):
        hs.place("6141", "lamp", (WH[0] + 10, WH_C1 - 8, z), tag="searchlight",
                 insert=(0, -1, 0))




# ------------------------------------------------------------------ breathers
def breathers() -> Batch:
    """Vent flaps behind the wheelhouse: two rows of grille slopes rising aft, the second row
    on a plate step (built on the hull)."""
    bt = Batch()
    i0 = int(VENTS[0] // S)
    _plates(bt, {(i, k) for i in range(i0 + 2, i0 + 4) for k in range(-2, 2)}, DECK - 8,
            "hull", "vents")
    for ia, bottom in ((i0, DECK), (i0 + 2, DECK - 8)):
        for k in range(-2, 2):
            bt.add("61409", "hull", transform((S * ia + 20, bottom, S * k + 10), rot(y=90)),
                   "vents")
    return bt


# ------------------------------------------------------------------ crest arch
# The crest: a thin rail of 1 x 4 plates standing on edge (studs facing port), each turned to
# follow the traced crest and pivoting on one stud where it overlaps the next (alternate
# plates on two layers), from a side stud at the wheelhouse's brow forward and down to a side
# stud on the bow's tip brick by the ram; tooth plates along it, raked back.
ARCH_PITCHES = (60.0, 60.0, 60.0, 60.0, 40.0)   # each plate's end studs (the pivots) apart:
ARCH_PART = {60.0: "3710", 40.0: "3623", 100.0: "3666"}   # 1 x 4, 1 x 3, 1 x 6
ARCH_PLATES = len(ARCH_PITCHES)
FOOT = np.array([shp.BOW_TIP_X + 10, shp.FL_A - 24 - 8 - 24 + 10])   # the bow's side stud
ARCH_Z = (-8.0, -16.0)               # the two layers' stud faces (layer B on the side studs)
# the rail's line (its studs), from the brow to the bow: the traced crest
# (naut_shape.CREST_ARCH) less half the rail, kept clear above the deck and the bow's ridge
ARCH_PATH = ((-230, -134), (-260, -134), (-290, -128), (-320, -114), (-345, -98),
             (-365, -92), (-385, -84), (-405, -76), (-425, -68), (-445, -60), (-465, -54),
             (-490, -54))
TEETH = ((1, 1), (1, 3), (3, 1), (3, 3))   # (plate, stud from its aft end): on the outer layer
TOOTH_DIR = (0.45, -0.89)            # raked back: up and aft


def _path_point(t, k=0.0):
    """The point at arc length t along the rail's line, lifted by k times a bump that is
    zero at both ends (so the chain's slack spreads along the arch)."""
    pts = np.array(ARCH_PATH, float)
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)])
    t = min(max(t, 0.0), cum[-1])
    j = min(int(np.searchsorted(cum, t, side="right")) - 1, len(seg) - 1)
    p = pts[j] + (pts[j + 1] - pts[j]) * (t - cum[j]) / seg[j]
    f = t / cum[-1]
    return p + np.array([0.0, -k * 6.75 * f * (1 - f) ** 2])     # most lift nearer the head


def _walk(k):
    """Pivots walked along the (lifted) line a plate at a time; returns them and how far the
    last one ends from the bow's stud along the line (negative: short of it)."""
    pts, t = [np.array(ARCH_PATH[0], float)], 0.0
    total = float(np.sum(np.linalg.norm(np.diff(np.array(ARCH_PATH, float), axis=0), axis=1)))
    for L in ARCH_PITCHES:
        q = pts[-1]
        lo, hi = t, t + 3 * L
        for _ in range(60):
            m = (lo + hi) / 2
            lo, hi = (m, hi) if np.linalg.norm(_path_point(m, k) - q) < L else (lo, m)
        t = (lo + hi) / 2
        pts.append(_path_point(t, k))
    return pts, t - total


def arch_pivots():
    """Pivot studs P0..Pn: P0 the brow's stud, Pn the bow's, each plate's pitch apart, all on
    the rail's line lifted just enough in the middle to take up the chain's slack."""
    lo, hi = 0.0, 80.0
    for _ in range(60):
        k = (lo + hi) / 2
        _, over = _walk(k)
        lo, hi = (k, hi) if over > 0 else (lo, k)
    pts, _ = _walk((lo + hi) / 2)
    pts[-1] = np.array(ARCH_PATH[-1], float)
    return pts


CREST_FRAME = transform((0.0, 0.0, 0.0), side_R(-1))   # its own frame: up = to port
UP = (0, -1, 0)


def crest_arch(model):
    """The crest arch (see above): five 1 x 4 plates on edge on two layers, each turned on the
    studs it shares with its neighbours, tooth plates on its outer studs."""
    sub = model.submodel("crest", "Crest arch")
    bt = Batch(CREST_FRAME)              # built flat: the inner layer on the table
    pts = arch_pivots()
    ty = np.array([TOOTH_DIR[0], TOOTH_DIR[1], 0.0])
    for n in range(ARCH_PLATES):
        a, b = pts[n], pts[n + 1]
        d = (b - a) / np.linalg.norm(b - a)
        ex = np.array([d[0], d[1], 0.0])
        R = orient(ex, (0, 0, 1))
        zt = ARCH_Z[n % 2]
        c = (a + b) / 2
        L = ARCH_PITCHES[n]
        bt.add(ARCH_PART[L], "spine", transform((c[0], c[1], zt), R), f"plate{n}",
               insert=UP)
        n_studs = int(L // S) + 1
        teeth_here = {k for pn, k in TEETH if pn == n}
        for k in range(n_studs):            # tiles on the rail's bare studs
            if k in teeth_here or (n % 2 == 0 and (k in (0, n_studs - 1) or n > 0 and k == 1
                                                   or k == n_studs - 2)):
                continue                     # a tooth, under the next plate, or right by it
                                             # (that stud stays bare: a rivet)
            sp = a + d * (20 * k)
            tile = "3070b" if n % 2 else "98138"     # round where it sits by the next plate
            bt.add(tile, "spine", transform((sp[0], sp[1], zt - 8), R), f"tiles{n}",
                   insert=UP)
        for pn, k in TEETH:
            if pn != n:
                continue
            sp = a + d * (20 * k)
            zz = zt                          # a round plate lifts the tooth off the rail
            bt.add("4073", "spine", transform((sp[0], sp[1], zz - 8), orient((1, 0, 0), (0, 0, 1))),
                   f"teeth{n}", insert=UP)
            zz -= 8
            Rt = orient(np.cross((0, 0, 1), -ty), (0, 0, 1), -ty)
            bt.add("49668", "spine", transform((sp[0], sp[1], zz - 8), Rt), f"teeth{n}",
                   "tooth", insert=UP)
    bt.emit(sub, phases=[[f"plate{n}" for n in range(ARCH_PLATES)],
                         [f"tiles{n}" for n in range(ARCH_PLATES)],
                         [f"teeth{n}" for n in range(ARCH_PLATES)]],
            captions={"plate0": "The crest arch: plates on edge, each turned on one stud",
                      "tiles0": "Tiles along it",
                      "teeth0": "Tooth plates along it"}, per_step=4, reach=200)
    return sub


def crest_foot(model):
    """The bow's side stud for the crest: a brick with a stud on its side, on a plate on the
    tip brick."""
    sub = model.submodel("crest_foot", "Crest's foot")
    sub.place("3024", "hull", (FOOT[0], shp.FL_A - 24 - 8, 10))
    sub.step()
    sub.place("87087", "hull", (FOOT[0], shp.FL_A - 24 - 8 - 24, 10))
    return sub


# ------------------------------------------------------------------ ram
RAM_Y = shp.FL_A - 24 + 10           # the prow tip brick's side studs


def ram(model):
    """On the prow's tip brick (two studs facing forward): a jumper centring a round plate with
    an open stud, a 3L bar through it and a cone for the point."""
    sub = model.submodel("ram", "Ram")
    x0 = shp.BOW_TIP_X
    sub.place("15573", "ram", (x0 - 8, RAM_Y, 0), SNOT_FWD)
    sub.step()
    sub.place("85861", "ram", (x0 - 16, RAM_Y, 0), rot(z=-90), tag="ram")
    sub.step("The ram")
    sub.place("87994", "ram", (x0 - 10, RAM_Y, 0), rot(z=90), tag="ram", insert=(1, 0, 0))
    sub.step()
    sub.place("59900", "ram", (x0 - 16 - 40 - 24 + 8, RAM_Y, 0), rot(z=-90), tag="ram",
              insert=(1, 0, 0))
    return sub


# ------------------------------------------------------------------ tail
PROP_Y = 2                           # the propeller shaft (the Technic brick's hole)
PROP_X = 510
STOCK_TOP, STOCK_BOT = -32, 32       # the tail stock (the core's end) over and under it
# the fish tail, two studs thick, traced (naut_shape.TAIL_UPPER / TAIL_LOWER): plate levels
# (tops) -> x ranges. The upper lobe stands on the stock and sweeps up and aft to its tip,
# cheese slopes smoothing its leading edge; the lower lobe hangs under the stock and sweeps
# down and aft, inverted curved slopes under its steps. Between them, behind the propeller,
# the guard post and the rudder.
FIN_UP = {-40: [(420, 540)], -48: [(500, 540)], -56: [(500, 560)], -64: [(520, 560)],
          -72: [(520, 560)], -80: [(540, 580)], -88: [(540, 580)]}
UP_CAPS = ((490, -40), (510, -56), (530, -72))           # cheese slopes: (x, level under)
FIN_LO = {32: [(440, 500)], 40: [(460, 500), (520, 540)], 48: [(480, 560)],
          56: [(500, 580)], 64: [(520, 580)]}
LO_CURVES = ((450, 40), (490, 56))   # inverted curved slopes 2 x 2: (thin row's x, its top)
WINDOW_TILES = (510, 550)            # tiles across the lower lobe's top under prop and rudder
GUARD_X = 530                        # the propeller guard's post: a bar, the rudder's hinge
RUDDER_X = 550                       # the rudder blade's middle (it turns about the post)


def tail_lower() -> Batch:
    """The fish tail's lower lobe, pushed up under the stock: plate levels two studs thick
    sweeping down and aft, inverted curved slopes under its steps."""
    bt = Batch()
    _fin(bt, FIN_LO, "fin_lo", up=False)
    for x, y in LO_CURVES:            # thin row forward, deep row aft
        bt.add("32803", "hull", transform((x, y, 0), rot(y=90)), "fin_lo", insert=(0, 1, 0))
    for x in WINDOW_TILES:            # the window's floor, under the propeller and the rudder
        bt.add("3069b", "hull", transform((x, 40, 0), ACROSS), "floor", insert=(0, -1, 0))
    return bt


def tail_upper() -> Batch:
    """The fish tail's upper lobe on the stock: plate levels sweeping up and aft to its tip,
    cheese slopes smoothing its leading edge, over the propeller's window."""
    bt = Batch()
    _fin(bt, FIN_UP, "fin_up", up=True)
    for x, y in UP_CAPS:
        for z in (-10, 10):
            bt.add("54200", "hull", transform((x, y, z), rot(y=90)), "fin_up")
    return bt


def _fin(bt, levels, cat, up):
    below = None
    for n, top in enumerate(sorted(levels, key=lambda t: abs(t))):
        cells = {(i, k) for x0, x1 in levels[top] for i in range(int(x0 // S), int(x1 // S))
                 for k in (-1, 0)}
        sizes = [(1, 2), (1, 4), (2, 2), (2, 3), (2, 4), (2, 6), (2, 8)]
        rects = pack(cells, sizes, below, prefer="x", shift=n)
        for i0, i1, k0, k1 in rects:
            part, R = rect_part(PLATE, i1 - i0 + 1, k1 - k0 + 1)
            bt.add(part, "hull", transform((S * (i0 + i1 + 1) / 2, top,
                                            S * (k0 + k1 + 1) / 2), R), cat,
                   insert=None if up else (0, 1, 0))
        below = ids_of(rects)


def propeller(model):
    """The propeller on a smooth Technic pin, pushed into the tail stock's bearing."""
    sub = model.submodel("propeller", "Propeller")
    sub.place("65768", "propeller", (PROP_X, PROP_Y, 0), rot(y=90), tag="prop")
    sub.step("A smooth pin in the propeller's hub, so it spins freely")
    sub.place("3673", "shaft", (PROP_X - 10, PROP_Y, 0), tag="prop", insert=(1, 0, 0))
    return sub


def guard(model):
    """The propeller guard's post behind the propeller: a jumper on the lower lobe centres a
    round brick with an open stud, and a bar stands in it, up to just under the upper lobe."""
    sub = model.submodel("guard", "Propeller guard")
    top = 40                                             # the lower lobe's top there
    sub.place("15573", "spine", (GUARD_X, top - 8, 0), ACROSS)
    sub.step()
    sub.place("3062b", "spine", (GUARD_X, top - 32, 0))
    sub.step("The guard's post: a bar in a round brick")
    sub.place("87994", "spine", (GUARD_X, top - 68, 0), insert=(0, -1, 0))
    return sub


def rudder(model):
    """The rudder: a blade one stud long behind the guard's post, of 1 x 1 bricks and plates,
    clipped to the post by two plates with vertical clips, so it swings about the post. The
    lobes' tips reach on past it."""
    sub = model.submodel("rudder", "Rudder")
    x0 = RUDDER_X
    clip_R = rot(y=90)                                   # the clip toward the bow
    sub.place("3005", "hull", (x0, 8, 0), tag="rudder")
    sub.step()
    sub.place("3024", "hull", (x0, 0, 0), tag="rudder")
    for top in (-8, -24):                                # two clips on the post
        sub.step()
        sub.place("60897", "spine", (x0, top, 0), clip_R, tag="rudder")
        sub.step()
        sub.place("3024" if top == -8 else "3070b", "hull", (x0, top - 8, 0), tag="rudder")
    return sub


# ------------------------------------------------------------------ keel fins and saw teeth
# the belly fins (traced naut_shape.FWD_FIN / REAR_FIN), two studs thick, hanging under the
# core: plate levels (tops) -> x ranges. The forward fin's aft end hooks down and back (a
# cheese slope over the hook); the after fin's aft edge is cut back.
FWD_FIN = {80: [(-180, -60)], 88: [(-180, -60)], 96: [(-180, -40)], 104: [(-160, -40)]}
REAR_FIN = {80: [(60, 220)], 88: [(60, 200)], 96: [(60, 200)], 104: [(60, 180)]}
FWD_HOOK = (-50, 96)                 # the cheese slopes over the hook: (x, level under)
# the bow's saw keel: a tooth under each inverted curve's deep end along the keel
# (naut_relief.KEEL_SLOPES) and two more under the side keels' tip (traced SAW_KEEL)
BOW_TEETH_X = (-450, -470)


def keel_fin(model, which):
    """A belly fin, built upside down and pushed up under the core."""
    fwd = which == "fwd"
    sub = model.submodel(f"keel_fin_{which}", f"{'Forward' if fwd else 'After'} keel fin")
    bt = Batch()
    _fin(bt, FWD_FIN if fwd else REAR_FIN, "fin", up=False)
    if fwd:
        for z in (-10, 10):
            bt.add("54200", "hull", transform((FWD_HOOK[0], FWD_HOOK[1], z), rot(y=-90)),
                   "fin", insert=(0, 1, 0))
    bt.emit(sub, phases=[["fin"]],
            captions={"fin": "The forward keel fin, its tip hooked back" if fwd
                      else "The after keel fin"}, per_step=6, reach=200)
    return sub


def saw_teeth(hs, keel_slopes, flange_bottom):
    """Teeth hanging under the bow's keel (placed on the hull): tooth plates (the tooth
    curving down and out to each side) in the deep ends of the keel's inverted curved slopes,
    and under the side keels' tip."""
    hs.step("The saw keel's teeth")
    spots = [(x, v + 16) for x, v, d in keel_slopes if d < 0]
    spots += [(x, flange_bottom) for x in BOW_TEETH_X]
    for x, y in spots:
        for z in (-10, 10):
            R = None if z < 0 else rot(y=180)            # the tooth outward
            hs.place("15070", "spine", (x, y, z), R, tag="tooth", insert=(0, 1, 0))


def keel_teeth(hs, sockets):
    """Teeth along the side keels' forward third (placed on the hull): tooth plates in free
    anti-studs under the side keels' edge, the tooth curving down and forward."""
    hs.step("Teeth under the side keels' edge")
    for x, y, z in sockets:
        hs.place("15070", "spine", (x, y, z), rot(y=90), tag="tooth", insert=(0, 1, 0))


# ------------------------------------------------------------------ deck details
DORSAL = {-88: (20, 120), -96: (40, 120), -104: (60, 120), -112: (80, 120)}   # traced AFT_FIN
HATCH_X = 160                        # the round hatch aft of the dorsal fin
SKIFF = (200, 280)                   # the skiff on the after deck


def dorsal_fin(model):
    """The shark's dorsal fin on the deck: plate levels two studs thick stepping up aft, a
    cheese slope on each step's front so the leading edge is a row of teeth, and a tooth
    plate at the top raking aft."""
    sub = model.submodel("dorsal_fin", "Dorsal fin")
    bt = Batch()
    below = None
    for n, top in enumerate(sorted(DORSAL, reverse=True)):
        x0, x1 = DORSAL[top]
        cells = {(i, k) for i in range(int(x0 // S), int(x1 // S)) for k in (-1, 0)}
        rects = pack(cells, [(1, 2), (2, 2), (2, 3), (2, 4), (2, 6)], below, prefer="x",
                     shift=n)
        for i0, i1, k0, k1 in rects:
            part, R = rect_part(PLATE, i1 - i0 + 1, k1 - k0 + 1)
            bt.add(part, "hull", transform((S * (i0 + i1 + 1) / 2, top,
                                            S * (k0 + k1 + 1) / 2), R), "fin")
        below = ids_of(rects)
        nxt = DORSAL.get(top - 8)
        if nxt is not None:                       # a cheese slope on the step, rising aft
            for z in (-10, 10):
                bt.add("54200", "hull", transform((x0 + 10, top, z), rot(y=90)), "teeth")
    for z in (-10, 10):                           # the top: a tooth raking aft
        bt.add("49668", "spine", transform((DORSAL[-112][1] - 10, -120, z), rot(y=-90)),
               "teeth", "tooth")
    bt.emit(sub, phases=[["fin"], ["teeth"]],
            captions={"fin": "The dorsal fin", "teeth": "Its teeth"}, per_step=8, reach=200)
    return sub


def hatch(model):
    """The round hatch on the after deck."""
    sub = model.submodel("hatch", "Hatch")
    sub.place("4032", "frame", (HATCH_X, shp.DECK_STRIP - 8, 0))
    sub.step()
    sub.place("14769", "hull", (HATCH_X, shp.DECK_STRIP - 16, 0))
    return sub


def skiff(model):
    """The skiff on the after deck: a 2 x 4 plate, cheese slopes for its bow and stern, a
    tile between them for the well."""
    sub = model.submodel("skiff", "Skiff")
    x0, x1 = SKIFF
    sub.place("3020", "frame", ((x0 + x1) / 2, shp.DECK_STRIP - 8, 0))
    sub.step()
    for z in (-10, 10):
        sub.place("54200", "frame", (x0 + 10, shp.DECK_STRIP - 8, z), rot(y=90))
        sub.place("54200", "frame", (x1 - 10, shp.DECK_STRIP - 8, z), rot(y=-90))
    sub.place("3068b", "frame", ((x0 + x1) / 2, shp.DECK_STRIP - 16, 0))
    return sub


# ------------------------------------------------------------------ salon windows
WIN_LIGHTS = ((-10, -50), (10, -50), (-50, -10), (50, -10),      # (dx, dy) from the centre:
              (-10, 50), (10, 50), (-50, 30), (50, 30))          # two over, one each side, four under
WIN_STUDS = ((-30, -50), (30, -50), (-50, -30), (50, -30), (-30, 50), (30, 50))  # rivets
RING_STUDS = ((-30, -10), (30, -10), (-30, 10), (30, 10), (-10, -30), (10, -30),
              (-10, 30), (10, 30))


def salon_window(model, side):
    """One salon window on its boss (the hull's raised face): a round 4 x 4 frame with a pin
    hole (Pearl Gold, the iris ring, brass studs round it) with a Power Functions lamp pushed
    into its centre hole from behind, a clear jumper and a clear dish over the hole, eight
    yellow lights round it and dark rivets."""
    name = "salon_port" if side < 0 else "salon_stbd"
    sub = model.submodel(name, f"Salon window ({'port' if side < 0 else 'starboard'})")
    cx, cy = shp.SALON_C
    face = 20 + 8 * shp.SALON_FACE                  # |z| of the boss face
    R = side_R(side)

    def at(dx, dy, h):                              # a point h out from the face
        return (cx + dx, cy + dy, side * (face + h))

    led_R = rot(z=180) if side < 0 else rot(x=180)  # the lamp's nub outward, its lead up
    sub.place("62498c01", "led", at(0, 0, -2), led_R, tag="led", insert=(0, 0, side))
    sub.step("The frame, the lamp pushed into its centre hole from behind")
    sub.place("60474", "trim", at(0, 0, 8), R, insert=(0, 0, side))
    sub.step("Feed the lead in and down the shaft; press the frame on")
    sub.place("87580", "glass", at(0, 0, 16), R, tag="glass", insert=(0, 0, side))
    sub.step()
    sub.place("4740", "glass", at(0, 0, 24), R, tag="glass", insert=(0, 0, side))
    for dx, dy in RING_STUDS:
        sub.place("98138", "trim", at(dx, dy, 16), R, insert=(0, 0, side))
    lights = Batch()
    for dx, dy in WIN_LIGHTS:                       # yellow round plates under clear yellow
        lights.add("4073", "lamp_base", transform(at(dx, dy, 8), R), "bases",
                   insert=(0, 0, side))
        lights.add("98138", "lights", transform(at(dx, dy, 16), R), "lights", "lights",
                   insert=(0, 0, side))
    for dx, dy in WIN_STUDS:
        lights.add("98138", "frame", transform(at(dx, dy, 8), R), "bases",
                   insert=(0, 0, side))
    return sub, lights


# ------------------------------------------------------------------ dive planes
DIVE_X = {"fwd": -200, "aft": 120}   # each plane's hinge: middle of its bar plate (x)
DIVE_BAR = (-22.0, 90.0)             # the hinge bar: (y, |z|), at the side keels' edge
DIVE_TILT = 15.0                     # degrees each way


def dive_plane(model, which, side):
    """A dive plane: on the side keel's edge a plate with a handle (the hinge bar) on a plate,
    and the plane - a plate with a clip on its end and a tile - clipped on it, so it tilts
    about the bar."""
    sname = "port" if side < 0 else "stbd"
    tag = f"dive_{which}_{sname}"
    sub = model.submodel(tag, f"Dive plane ({which}, {sname})")
    x0 = DIVE_X[which]
    yb, zb = DIVE_BAR
    sub.place("3023", "hull", (x0, shp.FL_A - 8, side * (zb - 20)))
    sub.step()
    sub.place("48336", "hull", (x0, yb - 2, side * (zb - 20)), None if side < 0 else rot(y=180))
    sub.step("The dive plane clipped on the bar")
    R = orient((0, 0, -side), (0, 1, 0))          # the clip outboard of the plate, on the bar
    sub.place("63868", "hull", (x0, yb - 2, side * (zb + 30)), R, tag=tag, insert=(0, 0, side))
    sub.place("3069b", "hull", (x0, yb - 10, side * (zb + 30)), rot(y=90), tag=tag)
    return sub


def dive_pose(side, angle):
    """A plane's 4x4 transform (hull frame) tilted `angle` degrees about its bar."""
    from naut_kit import about
    yb, zb = DIVE_BAR
    return about((0.0, yb, side * zb), rot(x=angle))
