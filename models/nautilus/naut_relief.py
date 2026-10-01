"""The hull body: a solid core two studs wide down the middle, with the side keels' plates
running through it, and on each side, above and below the side keels, contour layers of plates
turned studs-out (the v1 "relief", now on the pointed lens of the side keels).

* **Core**: plates two studs wide, stud up, from the keel to the deck (the bow's and stern's
  ridge and keel lines step down in it, capped with curved slopes so they read as curves). A
  course of bricks with studs on one side sits on the side keels (and hangs under them): the
  relief's anchor.
* **Relief**: on each side, rows of studs-out plates 20 LDU tall (three above the side keels,
  three below), each row as many layers deep (8 LDU each) as the hull is wide there: the
  hull's cross-section is a lens from the side keels (a stud in from their edge) to the deck's
  edge above and to the keel below, and its plan follows the side keels' taper, so the rows
  shorten toward the bow and the stern.
* **Caps**: every row's outermost layer is capped. Where the row nearer the side keels is two
  layers deeper, cheese slopes rise to it, so the rows join into one smooth sloping plane (the
  hull side); where the next column toward amidships is deeper, they rise toward it (the
  taper); elsewhere tiles. Nothing shows a bare stud or a hole into the hull.

Hull frame (naut_shape): side keels centred on y = 0 (y -8..8), the bow toward -X, port toward
-Z. Cells: column i is x in [20 i, 20 i + 20]."""
from __future__ import annotations

from collections import defaultdict

import numpy as np

import naut_shape as shp
from brickkit.ldraw.matrix import rot, transform
from naut_frame import deck_hw
from naut_kit import (AV, PLATE, S, TILE, Batch, connected, ids_of, orient, pack,
                      rect_part, runs, side_R, weather)

CORE_HW = 20              # the core: two studs wide
LEDGE = 20                # the side keels stand this far proud of the hull body
UP_ROWS = (-22, -42, -62)  # stud lines of the relief rows over the side keels (row 0 nearest)
LO_ROWS = (18, 38, 58)     # and under them
ANCHOR_UP = shp.FL_A - 24  # the side-stud course on the side keels (top), studs at -22
ANCHOR_LO = shp.FL_B + 8   # the side-stud course under them (top), studs at 18
NL = 8
X0 = shp.BOW_TIP_X        # the core runs from the bow tip...
X1 = 500.0                # ...to the tail stock's end, over the propeller's bearing
BEARING = (480.0, shp.FL_A, 16.0)   # the Technic brick (x from, y top, y bottom) at the end
SIDE_STUD = {4: "30414", 2: "11211", 1: "87087"}   # bricks with studs on one long side
TIP_COL = int(X0 // S)    # the bow tip's column: the ram's brick


def xc(i: int) -> float:
    return S * i + S / 2


# ------------------------------------------------------------------ the core's outline
# the bow's ridge: the tip column is the ram's brick; behind it two 4 x 2 18-degree slopes,
# each a brick high, carry the ridge up to the deck (traced line naut_shape.TOP, within 5 LDU)
BOW_TOP = ((-500, -480, -32), (-480, -400, -32), (-400, -340, -56))
RIDGE_SLOPES = ((-410, -32), (-350, -56))      # 30363: (high end's column x, the level under it)
STERN_TOP = ((320, 420, -56), (420, X1, -32))
# the keel: each step a brick (24) every four studs, an inverted 4 x 1 curved slope under it;
# per column the core's bottom (the slope's deep half hangs from a plate lower than its thin
# half). (x from, x to, bottom)
BOW_BOT = ((-240, -200, 64), (-280, -240, 56), (-320, -280, 40), (-360, -320, 32),
           (-400, -360, 16))
STERN_BOT = ((220, 260, 64), (260, 300, 56), (300, 340, 40), (340, 380, 32))
# under the bow the core runs on down below the hull's sides as the saw keel's blade, this
# much deeper (its curved slopes and their teeth lower with it: traced SAW_KEEL)
BLADE = (-440, -200, 16)
KEEL_SLOPES = ((-210, 56 + 16, -1), (-290, 32 + 16, -1), (-370, 8 + 16, -1),   # 13547: (deep
               (230, 56, 1), (310, 32, 1))          # column x, thin half's top, toward)
MID_BOT = 80


def core_top(x: float) -> float:
    for a, b, t in BOW_TOP:
        if a <= x < b:
            return t
    for a, b, t in STERN_TOP:
        if a <= x < b:
            return t
    return shp.DECK_STRIP + 8          # under the deck


def core_bot(x: float) -> float:
    for a, b, v in BOW_BOT + STERN_BOT:
        if a <= x < b:
            return v
    if x < BOW_BOT[-1][0]:
        return shp.FL_B + 8                  # nothing under the side keels at the tip
    if x >= STERN_BOT[-1][1]:
        return STERN_BOT[-1][2]              # the tail stock
    return MID_BOT


def keel_bot(x: float) -> float:
    """The core's bottom: the hull's (core_bot), deeper under the bow (the saw keel's blade)."""
    a, b, d = BLADE
    if a <= x < b:
        return max(core_bot(x), shp.FL_B + 8) + d
    return core_bot(x)


def body_hw(x: float, y: float) -> float:
    """Half-width of the hull body at (x, y): a lens from the side keels (a stud in from their
    edge) to the deck's edge (or the core, where there is no deck) above, and to the core at
    the keel below."""
    w0 = shp.flange_hw(x) - LEDGE
    if y < 0:
        t = core_top(x)
        w1 = max(deck_hw(x), CORE_HW) if t <= shp.DECK_STRIP + 8 else CORE_HW
        f = (shp.FL_A - y) / (shp.FL_A - t) if t < shp.FL_A else 1.0
    else:
        b = core_bot(x)
        w1 = CORE_HW
        f = (y - shp.FL_B - 8) / (b - shp.FL_B - 8) if b > shp.FL_B + 8 else 1.0
    return w0 + (w1 - w0) * min(max(f, 0.0), 1.0)


# ------------------------------------------------------------------ the relief plan
class Relief:
    """Layer counts L[(i, r)] for the rows over (kind 'up') or under ('lo') the side keels."""

    def __init__(self, kind: str):
        self.kind = kind
        self.rows = UP_ROWS if kind == "up" else LO_ROWS
        self.L: dict = {}
        for i in range(int(X0 // S), int(X1 // S)):
            x = xc(i)
            for r, yr in enumerate(self.rows):
                if kind == "up" and core_top(x) > yr - 10:
                    continue                  # the row is above the hull's top here
                if kind == "lo" and core_bot(x) < yr + 10:
                    continue
                w = body_hw(x, yr)
                n = 2 * int((w - CORE_HW) // 16)  # an even number: cheese slopes cap the steps
                # never more than one cheese step (two layers) less than the row nearer the
                # side keels, so no row leaves a slot open under the deck or over the keel
                if r > 0 and (i, r - 1) in self.L:
                    n = max(n, self.L[(i, r - 1)] - 2, 2)
                if kind == "up" and r == len(self.rows) - 1:
                    # the row under the deck reaches out past the deck's edge, so the deck's
                    # wedge plates sit on it (their edges' stud notches hidden)
                    n = max(n, -(-int(deck_hw(x) - CORE_HW) // 8))
                boss = self.boss(i, r)
                if boss:
                    n = {"face": shp.SALON_FACE, "corner": shp.SALON_FACE - 1,
                         "lamp": 3, "shaft": 0}[boss]
                if n > 0:
                    self.L[(i, r)] = min(n, NL)

    def boss(self, i: int, r: int) -> str:
        """The salon window's boss: '' outside it, 'corner' (cut back a layer), 'lamp' (the
        pocket behind the frame for the lamp), 'shaft' (open to the core: the lamp's lead goes
        in there) or 'face'. It covers the three rows over the
        side keels and two under them (the frame's six stud rows less the side keels' own)."""
        x = xc(i)
        rows = 3 if self.kind == "up" else 2
        if not (shp.SALON_X[0] <= x < shp.SALON_X[1]) or r >= rows:
            return ""
        end = x < shp.SALON_X[0] + S or x >= shp.SALON_X[1] - S
        if end and r == rows - 1:
            return "corner"
        if self.kind == "up" and r == 0 and shp.SHAFT_X[0] <= x < shp.SHAFT_X[1]:
            return "shaft"
        if self.kind == "up" and r == 0 and shp.LAMP_X[0] <= x < shp.LAMP_X[1]:
            return "lamp"
        return "face"

    def y(self, r: float) -> float:
        return float(np.interp(r, range(len(self.rows)), self.rows))

    def toward_keel(self) -> int:
        """+1 if the side keels are toward +y from the rows (over them), else -1."""
        return 1 if self.kind == "up" else -1

    def layer(self, n: int) -> set:
        return {c for c, l in self.L.items() if l > n}

    def caps(self) -> dict:
        """(i, r) -> ('slope', (dx, dy)) - a cheese slope, its high side that way; ('tile',
        None); or ('rivet', None) - a round tile, a rivet head in a seam. The row next to the
        side keels is tiled (so the side keels' own studs can be covered); the others rise in
        cheese slopes to the row nearer the side keels, or toward amidships along the taper.
        Rivet lines run down the hull's plate seams every few columns, with the odd diagonal
        between them (the plating's triangles)."""
        out = {}
        for (i, r), l in self.L.items():
            if self.boss(i, r) in ("face", "lamp", "shaft"):
                continue                     # under the window's frame and its studs
            inner = self.L.get((i, r - 1), l + 2) if r > 0 else l
            mid = i + 1 if xc(i) < 0 else i - 1
            dx = self.L.get((mid, r), 0) - l
            if self.kind == "up" and LADDER[0] <= xc(i) < LADDER[1]:
                out[(i, r)] = ("ladder", None)
            elif self.rivet(i, r):
                out[(i, r)] = ("rivet", self.rivet(i, r))
            elif self.kind == "lo" and r == 0 and any(a <= xc(i) < b for a, b in GRILLES):
                out[(i, r)] = ("grille", None)
            elif inner - l >= 2:
                out[(i, r)] = ("slope", (0, self.toward_keel()))
            elif dx >= 2:
                out[(i, r)] = ("slope", (1 if mid > i else -1, 0))
            else:
                out[(i, r)] = ("tile", None)
        return out

    def rivet(self, i: int, r: int) -> str:
        """'seam': a rivet on a plate seam, every RIVET_PITCH columns amidships (a dark round
        tile); 'diag': a short diagonal a column clear of the seam in every other panel, a hint
        of the plating's triangles (round tiles in the hull's colour: the shape alone shows);
        '' elsewhere. Never two dark rivets side by side, so they read as rivet lines."""
        x = xc(i)
        if not (-320 < x < 300) or r == 0:
            return ""
        k = i % RIVET_PITCH
        if k == 0:
            return "seam"
        panel = i // RIVET_PITCH
        return "diag" if panel % 2 == 0 and k == r + 1 else ""

RIVET_PITCH = 7               # columns between the hull's vertical rivet seams
LADDER = (140, 180)           # a ladder up each side to the hatch: handles on the rows here
# grilles (the vents along the lower hull, traced from the photo): x ranges on the row under
# the side keels
GRILLES = ((-280, -200), (-180, -120), (100, 160), (180, 240))


def anchors(rel: Relief) -> set:
    """Columns whose core carries a side-stud brick for this relief (its row 0); none where
    the salon lights' leads go down the core."""
    return {i for (i, r) in rel.L if r == 0 and not in_shaft(xc(i))}


def in_shaft(x: float) -> bool:
    return shp.SHAFT_X[0] <= x < shp.SHAFT_X[1]


# ------------------------------------------------------------------ the core
CORE_PHASES = [["anchor", "core"], ["caps"], ["anchor_lo", "core_lo"], ["keelcaps"]]
CORE_HANGING = ("anchor_lo", "core_lo", "keelcaps")
CORE_CAPTIONS = {"core": "The core: plates two studs wide on the side keels",
                 "anchor": "Bricks with side studs: the hull sides hang on them",
                 "caps": "Slopes along the bow's ridge and at the stern",
                 "core_lo": "The core under the side keels: plates pushed up one under another",
                 "anchor_lo": "Bricks with side studs under the side keels too",
                 "keelcaps": "Curved slopes under the keel"}


def core_batch(up: Relief, lo: Relief) -> Batch:
    """The core, to be built on the side keels: plates two studs wide up to the deck and
    hanging under the side keels down to the keel; a course of side-stud bricks on the side
    keels and one under them where the relief needs them; the propeller's bearing (a Technic
    brick) at the tail stock's end; curved slopes over the bow's and stern's ridge steps and
    inverted ones under the keel's steps."""
    bt = Batch()
    a_up, a_lo = anchors(up), anchors(lo)
    # the side-stud courses: one brick row each side
    for top, cols in ((ANCHOR_UP, a_up), (ANCHOR_LO, a_lo)):
        for side, k in ((-1, -1), (1, 0)):
            for i0, i1, _, _ in runs({(i, 0) for i in cols}, (4, 2, 1)):
                part = SIDE_STUD[i1 - i0 + 1]
                R = None if side < 0 else rot(y=180)
                bt.add(part, "core", transform((S * (i0 + i1 + 1) / 2, top, S * k + 10), R),
                       "anchor_lo" if top > 0 else "anchor", insert=(0, 1, 0) if top > 0 else None)
    # the bow tip: a 1 x 2 brick across, two studs on its face for the ram
    bt.add("11211", "hull", transform((xc(TIP_COL), ANCHOR_UP, 0), rot(y=90)), "anchor")
    # plate levels: above the side keels up to the core's top, under them down to its bottom
    levels = defaultdict(set)
    for i in range(int(X0 // S), int(X1 // S)):
        x = xc(i)
        t, b = core_top(x), keel_bot(x)
        for y in range(int(shp.FL_A - 8), int(t) - 1, -8):          # plate tops, upward
            if (i in a_up or i == TIP_COL) and ANCHOR_UP <= y < shp.FL_A:
                continue
            if in_shaft(x) and ANCHOR_UP <= y < shp.FL_A:
                continue                     # the lights' leads come in here
            levels[y] |= {(i, -1), (i, 0)}
        for y in range(int(shp.FL_B + 8), int(b), 8):                # plate tops, downward
            if i in a_lo and ANCHOR_LO <= y < ANCHOR_LO + 24:
                continue
            if x > BEARING[0] and y < BEARING[2]:
                continue                     # the propeller's bearing
            if in_shaft(x):
                continue                     # the lights' leads go down here
            levels[y] |= {(i, -1), (i, 0)}
    sizes = [s for s in AV.sizes(PLATE, "core") if s[0] <= 2 and s[1] <= 12]
    below = None
    for n, y in enumerate(sorted(levels, key=lambda v: (v > 0, -v if v < 0 else v))):
        if y == shp.FL_B + 8:
            below = None                     # under the side keels: start again
        cells = levels[y]
        rects = pack(cells, sizes, below, prefer="x", shift=n)
        for i0, i1, k0, k1 in rects:
            part, R = rect_part(PLATE, i1 - i0 + 1, k1 - k0 + 1)
            bt.add(part, "core", transform((S * (i0 + i1 + 1) / 2, y, S * (k0 + k1 + 1) / 2), R),
                   "core_lo" if y > 0 else "core", insert=(0, 1, 0) if y > 0 else None)
        below = ids_of(rects)
    # the ridge: 18-degree slopes rising aft up the bow; cheese slopes down to the stern's
    for x, t in RIDGE_SLOPES:
        bt.add("30363", "hull", transform((x, t - 24, 0), rot(y=90)), "caps")
    xs = STERN_TOP[0][0] + 10
    for z in (-10, 10):
        bt.add("54200", "hull", transform((xs, STERN_TOP[0][2], z), rot(y=-90)), "caps")
    # the keel: inverted 4 x 1 curved slopes under each step, their deep half aft (or fore,
    # at the stern), thin toward the end of the hull
    for x, v, d in KEEL_SLOPES:
        for z in (-10, 10):
            bt.add("13547", "hull", transform((x, v, z), rot(y=90 if d < 0 else -90)),
                   "keelcaps", insert=(0, 1, 0))
    bt.add("3700", "hull", transform((BEARING[0] + 10, shp.FL_A, 0), rot(y=90)), "core_lo",
           insert=(0, 1, 0))
    return bt


# ------------------------------------------------------------------ the relief
def cap_R(side: int, toward) -> np.ndarray:
    """A slope on a hull side: its bottom on the relief (local -Y outward), its high side
    (local +Z) toward (dx, dy) in the hull's x-y plane."""
    ey = np.array([0, 0, -side], float)
    ez = np.array([toward[0], toward[1], 0], float)
    return orient(np.cross(ey, ez), ey, ez)


def relief_rects(rel: Relief, side: int) -> list[list]:
    """Plates for each layer, bonded to the layer under them (layer 0 to the core's side
    studs); tries a few packings until the side holds together."""
    sizes = [s for s in AV.sizes(PLATE, "hull") if s[0] <= 3 and s[1] <= 10]
    best = None
    for shift in range(0, 60, 3):
        out = []
        below = {}
        for n in range(NL):
            cells = rel.layer(n)
            if not cells:
                break
            face = boss_face(rel, n, cells)      # the window's boss face: plates of its own
            rects = []
            for part in (cells - face, face):
                if part:
                    rects += pack(part, sizes, below, prefer="x", shift=shift + n * 5,
                                  above=rel.layer(n + 1))
            out.append(rects)
            below = ids_of(rects, start=1000 * (n + 1))
        pieces = connected(out)
        if best is None or pieces < best[0]:
            best = (pieces, out)
        if pieces == 1:
            break
    return best[1]


UP = (0, -1, 0)           # in a flat-built sub-assembly's own frame: pressed on from above


def relief_frame(side: int) -> np.ndarray:
    """Where a hull side's sub-assembly sits: its local frame has the core's side face as the
    table (y = 0) and its layers stacked up (-y) outward."""
    return transform((0.0, 0.0, side * CORE_HW), side_R(side))


def boss_face(rel: Relief, n: int, cells) -> set:
    """The cells of layer n that are the salon window's boss face (its outermost layer)."""
    if n != shp.SALON_FACE - 1:
        return set()
    return {c for c in cells if rel.boss(*c) == "face"}


def build_relief(model, rel: Relief, side: int):
    sname = "port" if side < 0 else "stbd"
    where = "upper" if rel.kind == "up" else "lower"
    sub = model.submodel(f"{where}_{sname}", f"Hull side, {where}, {sname}")
    R = side_R(side)
    bt = Batch(relief_frame(side))                     # built flat, layer 0 on the table
    for n, rs in enumerate(relief_rects(rel, side)):
        z = side * (CORE_HW + 8 + 8 * n)
        face = boss_face(rel, n, rel.layer(n))
        for i0, i1, r0, r1 in rs:
            part, Rl = rect_part(PLATE, i1 - i0 + 1, r1 - r0 + 1)
            pos = (S * (i0 + i1 + 1) / 2, (rel.y(r0) + rel.y(r1)) / 2, z)
            role = "frame" if (i0, r0) in face else "hull"
            bt.add(part, role, transform(pos, R @ Rl), f"layer{n}", insert=UP)
    caps = rel.caps()
    groups = defaultdict(set)
    for c, v in caps.items():
        groups[(v, rel.L[c])].add(c)
    tile_lengths = sorted({k[1] for k in AV.sizes(TILE, "hull") if k[0] == 1})
    for ((kind, ty), l), cells in groups.items():
        zf = side * (CORE_HW + 8 * l)                       # the top layer's outer face
        if kind == "slope" and ty[0] == 0:
            for i0, i1, r, _ in runs(cells, (2, 1)):
                part = {2: "85984", 1: "54200"}[i1 - i0 + 1]
                pos = (S * (i0 + i1 + 1) / 2, rel.y(r), zf)
                bt.add(part, weather(part, pos[0], pos[1], side), transform(pos, cap_R(side, ty)),
                       "caps", insert=UP)
        elif kind == "slope":
            for i, r in sorted(cells):
                pos = (xc(i), rel.y(r), zf)
                bt.add("54200", weather("54200", pos[0], pos[1], side),
                       transform(pos, cap_R(side, ty)), "caps", insert=UP)
        elif kind == "ladder":            # a rung on each row: a tile with a handle
            for i0, i1, r, _ in runs(cells, (2, 1)):
                part, h = ("2432", 32) if i1 > i0 else ("3070b", 8)
                pos = (S * (i0 + i1 + 1) / 2, rel.y(r), zf + side * h)
                bt.add(part, "hull", transform(pos, R), "caps", insert=UP)
        elif kind == "grille":
            for i0, i1, r, _ in runs(cells, (2, 1)):
                part = "2412b" if i1 > i0 else "3070b"
                pos = (S * (i0 + i1 + 1) / 2, rel.y(r), zf + side * 8)
                bt.add(part, "hull", transform(pos, R), "caps", insert=UP)
        elif kind == "rivet":
            for i, r in sorted(cells):
                pos = (xc(i), rel.y(r), zf + side * 8)
                bt.add("98138", "rivet" if ty == "seam" else "hull", transform(pos, R), "caps",
                       insert=UP)
        else:
            for i0, i1, r, _ in runs(cells, tile_lengths):
                part, Rl = rect_part(TILE, i1 - i0 + 1, 1)
                pos = (S * (i0 + i1 + 1) / 2, rel.y(r), zf + side * 8)
                bt.add(part, weather(part, pos[0], pos[1], side), transform(pos, R @ Rl),
                       "caps", insert=UP)
    captions = {f"layer{n}": f"Layer {n + 1}" for n in range(NL)}
    captions["layer0"] = f"The {where} hull side: plates on the core's side studs"
    captions["caps"] = "Cheese slopes and tiles: the rows join into a smooth side"
    bt.emit(sub, captions=captions, per_step=8, reach=160)
    return sub
