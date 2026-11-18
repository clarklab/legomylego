"""VHS Cassette - a life-size (1:1) VHS video cassette in real LEGO.

Units: LDU (stud 20, plate 8, brick 24), -Y is up, the dust flap faces the front (-Z).
Body 23 x 12 studs (x -230..230, z -110..130), the flap 16 LDU in front of it, 8 plates
tall (y -64..0): 184.0 x 102.4 x 25.6 mm against the real 187 x 103 x 25 mm.

Built like a modern display set: an inner chassis (the core: floor, the two reel drive holes,
lamp tube, brake release, tape run, guide rollers and the posts the shell lands on), two reels
that drop into their drive holes, end walls, a top shell built upside down (grip bands, two
glass windows on SNOT hangers, recessed face label, spine label, and the flap's four hinge
plates on four Technic pins, two at each front corner) and a full-length dust flap pressed
onto those hinge plates.

Moving groups: `flap` (the dust flap, about the pin axis) and `reel_l` / `reel_r` (reels,
about their red spindle axles). `reel_l` is the supply reel: on the left when you hold the
cassette label-up with the flap pointing away from you, which is +X here.

Each reel is turned from underneath, like a real cassette's: a square drive hole in the bottom,
4 x 4 studs, and in the middle of it the reel's drive hub, a white round plate upside down on
the red axle, whose four studs are the pegs a fingertip turns it by (`DRIVE`, `reel`).
"""
from __future__ import annotations

import math

import numpy as np

from brickkit.ldraw.matrix import rot, transform, translate
from kit import (PLATE, PLATE1, PLATE2, S, TILE, TILE1, TILE2, Batch, orient, quarter_M,
                 rect_M, weave)

NI = 11                                  # cells x = 20 i, |i| <= 11
Y_F0, Y_F1 = -8, -16                     # tops of the two floor layers
Y_T3, Y_T2, Y_T1 = -48, -56, -64         # tops of the three top-shell layers
REEL_X = {"reel_l": 110, "reel_r": -110}  # hub centres 88 mm apart; supply (full) at +X
REEL_Z = -10
DRIVE = 2                                # the drive hole under a reel: this many studs out from
                                         # its middle each way (4 x 4, 32 mm; a real one is 30)
PIVOT = (-54.0, -100.0)                  # (y, z) of the flap's pin axis, which runs along X
# along that axis at each front corner, from the end inwards (x = s * these, s = +-1): the outer
# hinge plate, the outer pivot block, the inner hinge plate, the inner pivot block; a pin joins
# each hinge plate to the block inside it
HINGE_X, BLOCK_X, PIN_X = (220, 180), (200, 160), (210, 170)   # (outer, inner)
LAMP = (10, -50)                         # lamp tube centre (a 2 x 2 round brick sits on a
                                         # cell corner, 4 mm right of the middle)
STUDS_FWD = rot(x=90)                    # SNOT: studs toward -Z, part's top face at origin z
STUDS_BACK = rot(x=-90)                  # SNOT: studs toward +Z
UPRIGHT_1XN = orient((0, 1, 0), (0, 0, 1), (1, 0, 0))   # 1 x N along Y, studs toward -Z
HINGE_UP = orient((0, -1, 0), (0, 0, 1), (-1, 0, 0))    # the same, the other way up: a plate with
                                         # a pin hole under one end stands with that end at the top
FLIP = transform((0, 0, 0), rot(z=180))  # the top shell is built upside down
FLAT = transform((0, 0, 0), rot(x=-90))  # the flap is built lying on its back

CELLS = {(i, k) for i in range(-NI, NI + 1) for k in range(-5, 7)}
MOUTH = {(i, -5) for i in range(-7, 8)}  # the head-drum mouth, open underneath


def cells(x0, x1, z0, z1):
    """Stud cells covered by the LDU rectangle x0..x1, z0..z1."""
    return {(i, k) for i in range(round((x0 + 10) / S), round((x1 - 10) / S) + 1)
            for k in range(round((z0 + 10) / S), round((z1 - 10) / S) + 1)}


def reel_dist(i, k):
    return min(math.hypot(S * i - x, S * k - REEL_Z) for x in REEL_X.values())


# the flap's pivots, in the cassette's own frame (world)
def block_M(s, x):
    """A pivot block: Plate 1 x 2 with Pin Hole on Top (11458) in the top shell's third layer,
    running front to back, its pin hole on the pivot axis at x = s * x."""
    return transform((s * x, Y_T3, -90), rot(y=90))


def hinge_M(s, x):
    """A hinge plate: 1 x 2 plate with a pin hole under one end (18677), standing on the back
    of the flap with that end at the top, studs to the front, the hole on the pivot axis."""
    return transform((s * x, PIVOT[0] + 10, -110), HINGE_UP)


def pin_M(s, x):
    """A Technic pin with friction (2780), two studs long, along the pivot axis at x = s * x."""
    return transform((s * x, PIVOT[0], PIVOT[1]))


def row_parts(table, spans, y, z, R, colour="shell"):
    """1 x N (or 2 x N) SNOT runs along X: spans of (i0, i1); y is the run's centre."""
    out = []
    for i0, i1 in spans:
        n = i1 - i0 + 1
        x = S * (i0 + i1) / 2
        Rr = R @ rot(y=90) if (table is PLATE2 and n == 1) else R
        out.append((table[n], colour, transform((x, y, z), Rr)))
    return out


def merge_lone(sub):
    """When the last step is one lone piece, it goes on in the step before it whose pieces are
    nearest (of the two before it): no booklet step is a lone piece."""
    last = [it for it in sub.items if it.step == sub.current_step]
    if len(last) != 1 or not hasattr(last[0], "part") or sub.current_step < 2:
        return
    at = last[0].M[:3, 3]
    near = {}
    for it in sub.items:
        if it.step in (sub.current_step - 1, sub.current_step - 2) and hasattr(it, "part"):
            near[it.step] = min(near.get(it.step, 1e9), float(np.linalg.norm(it.M[:3, 3] - at)))
    if near:
        last[0].step = min(near, key=near.get)    # (the step left empty is reused by the next)


def best_layout(layout, phases, tries=36):
    """The first layout variant whose every build phase joins into one piece."""
    best = None
    for v in range(tries):
        b = layout(v)
        n = b.phase_pieces(phases)
        if best is None or n < best[0]:
            best = (n, b)
        if n == 1:
            break
    return best[1]


# ------------------------------------------------------------------------------ reels
def reel(model, name: str, title: str, full: bool):
    """A reel built around its own axis: a light grey lower flange (8 x 8 round plate), a second
    one on it (on the full reel, the tape pack), a clear upper flange ring (Trans-Clear 4 x 4
    macaroni tiles, r 60..80 LDU) and a white hub: a flat ring of 2 x 2 macaroni tiles round a 2 x 2 round plate whose four
    studs are the hub's bumps. A red Technic axle runs through the round plates' holes and
    the hub's axle hole: its end is the red dot in the middle of the hub. Underneath, a second
    white round plate is pushed onto the axle upside down, up against the lower flange: the
    drive hub. It turns in the square hole the chassis' tiles leave for it (the reel's
    bearing), its four studs are the pegs the reel is turned by from underneath, and the
    axle's two axle holes, one in each hub, make the reel turn with it."""
    s = model.submodel(name, title)
    s.step("The lower flange and the tape pack: two light grey 8 x 8 round plates with a "
           "hole in the middle, one on the other")
    s.place("74611", "flange", (0, -8, 0))
    s.place("74611", "pack" if full else "flange", (0, -16, 0))
    s.step("The hub: a round plate with an axle hole, and a flat white ring round it")
    s.place("4032a", "hub", (0, -24, 0))
    for q in range(4):
        s.place("27925", "hub").M = quarter_M("27925", q, -24)
    s.step("Tape wound round the hub" if full else "Just a few turns of tape left on the hub")
    for q in range(4):
        s.place("79393", "tape").M = quarter_M("79393", q, -24)
    s.step("Clear upper flange")
    for q in range(4):
        s.place("27507", "clear").M = quarter_M("27507", q, -24)
    s.step("The red spindle and the drive hub: push the axle up through the reel, then a white "
           "round plate onto its lower end, studs down. Its four studs are the pegs you turn "
           "the reel by from underneath")
    s.place("32062", "spindle", (0, -4, 0), rot(z=90), insert=(0, 1, 0))
    s.place("4032a", "hub", (0, 8, 0), rot(z=180), insert=(0, 1, 0))
    return s


# ------------------------------------------------------------------------------ chassis
SCREWS = [(-10, -3), (10, -3), (-10, 4), (10, 4), (0, 5)]


def drive_tiles(x):
    """The four 2 x 4 tiles round a reel's drive hub, as a pinwheel: (i0, i1, k0, k1) cells.
    Their inner edges leave a 2 x 2 square for the hub to turn in (the reel's bearing), their
    outer halves sit on the floor round the drive hole and their inner halves reach over it."""
    i, k = math.floor(x / S), math.floor(REEL_Z / S)   # the cell left of and in front of the
    #                                                    reel's middle (it is on a cell corner)
    return [(i - 2, i + 1, k - 2, k - 1), (i + 2, i + 3, k - 2, k + 1),
            (i, i + 3, k + 2, k + 3), (i - 2, i - 1, k, k + 3)]


def core_layout(variant: int) -> Batch:
    b = Batch()
    floor = {(i, k) for i, k in CELLS if k <= 5} - MOUTH
    holes = set()                         # the two drive holes, open underneath
    for x in REEL_X.values():
        holes |= cells(x - S * DRIVE, x + S * DRIVE, REEL_Z - S * DRIVE, REEL_Z + S * DRIVE)

    # F0 [-8, 0]: the bottom, with its drive holes, round holes and screw heads
    f0_fixed = set(holes)
    b.add("3709b", "shell", transform((LAMP[0], Y_F0, LAMP[1])), "f0")   # lamp hole
    f0_fixed |= cells(LAMP[0] - 40, LAMP[0] + 40, LAMP[1] - 20, LAMP[1] + 20)
    b.add("32124", "shell", transform((0, Y_F0, 60)), "f0")              # reel-lock release
    f0_fixed |= cells(-50, 50, 50, 70)
    for i, k in SCREWS:
        b.add("6141", "metal", transform((S * i, Y_F0, S * k)), "f0")
        f0_fixed.add((i, k))
    for r in weave(floor - f0_fixed, "x", phase=variant):      # rows along X
        p, M = rect_M(PLATE, r, Y_F0)
        b.add(p, "shell", M, "f0")

    # F1 [-16, -8]: smooth tiles under the reels, plates elsewhere
    f1_fixed = set()
    for x in REEL_X.values():             # four tiles round the drive hub: the reel's bearing
        for r in drive_tiles(x):
            p, M = rect_M(TILE, r, Y_F1)
            b.add(p, "shell", M, "f1")
        f1_fixed |= cells(x - 60, x + 60, REEL_Z - 60, REEL_Z + 60)
    b.add("4032a", "shell", transform((LAMP[0], Y_F1, LAMP[1])), "f1")
    f1_fixed |= cells(LAMP[0] - 20, LAMP[0] + 20, LAMP[1] - 20, LAMP[1] + 20)
    for s in (-1, 1):                     # white bases of the guide rollers and posts
        b.add("6141", "roller", transform((s * 200, Y_F1, -100)), "f1")
        b.add("6141", "roller" if s < 0 else "shell", transform((s * 200, Y_F1, -80)), "f1")
        f1_fixed |= {(s * 10, -5), (s * 10, -4)}
    rest = floor - f1_fixed
    smooth = {c for c in rest if reel_dist(*c) < 90}
    # (in front of and behind the four tiles a column is one cell: those go in rows, so one
    # tile ties the bottom layer's pieces under it and none is a 1 x 1)
    rows = {(i, k) for i, k in smooth if (i, k - 1) not in smooth and (i, k + 1) not in smooth}
    for r in weave(smooth - rows, "z", (8, 6, 4, 3, 2, 1), phase=variant // 4):   # columns along Z
        p, M = rect_M(TILE, r, Y_F1)
        b.add(p, "shell", M, "f1")
    for k in sorted({k for _, k in rows}):       # (a line at a time: each as few tiles as fit)
        for r in weave({c for c in rows if c[1] == k}, "x", (8, 6, 4, 3, 2, 1)):
            p, M = rect_M(TILE, r, Y_F1)
            b.add(p, "shell", M, "f1")
    for r in weave(rest - smooth, "z", phase=variant // 4 + 1):
        p, M = rect_M(PLATE, r, Y_F1)
        b.add(p, "shell", M, "f1")

    # the chassis' parts
    b.add("3941", "shell", transform((LAMP[0], -40, LAMP[1])), "lamp")
    b.add("3023", "brake", transform((0, -24, 50), rot(y=90)), "brake")
    b.add("3623", "brake", transform((0, -24, 80)), "brake")
    for s in (-1, 1):
        b.add("3062b", "roller", transform((s * 200, -40, -100)), "rollers")
        b.add("3062b", "roller" if s < 0 else "shell", transform((s * 200, -40, -80)),
              "rollers")
        b.add("3666", "shell", transform((s * 150, -24, 100)), "ledges")
        # a post under the window's front edge, at its outer corner (the reel turns under the
        # rest of it): its stud is the stop the frame comes down on if the window is pushed
        b.add("3005", "shell", transform((s * 200, -40, -60)), "rollers")
    for x in (-180, 0, 180):               # bricks with a side stud carry the tape run
        b.add("87087", "shell", transform((x, -40, -80)), "tape_posts")

    # the tape: black tiles on a plate stood on its edge, studs to the front. The tiles stop a
    # stud short of each roller: the flap's inner hinge plate hangs in front of that stud
    for part, colour, M in row_parts(PLATE1, [(-9, -2), (-1, 1), (2, 9)], -30, -98,
                                     STUDS_FWD, "tape"):
        b.add(part, colour, M, "tape_back", insert=(0, 0, -1))
    for part, colour, M in row_parts(TILE1, [(-8, -3), (-2, -1), (0, 0), (1, 2), (3, 8)],
                                     -30, -106, STUDS_FWD, "tape"):
        b.add(part, colour, M, "tape", insert=(0, 0, -1))
    return b


CORE_PHASES = [["f0", "f1"], ["lamp", "brake"], ["rollers", "ledges", "tape_posts"],
               ["tape_back"], ["tape"]]


def core(model):
    sub = model.submodel("core", "Chassis")
    b = best_layout(core_layout, CORE_PHASES)
    tape = sorted((it for it in b.items if it[3] in ("tape_back", "tape")),
                  key=lambda it: (it[3] == "tape", it[2][0, 3]))
    b.items = [it for it in b.items if it[3] not in ("tape_back", "tape")]
    b.emit(sub, CORE_PHASES[:3], {
        "f0": "Chassis, bottom layer: the two square gaps are the reel drive holes, the "
              "Technic plate's middle hole is the lamp hole; silver screw heads sit flush "
              "underneath",
        "f1": "Second floor layer: smooth tiles where the reels turn. Four 2 x 4 tiles reach "
              "over each drive hole and leave a small square in the middle for the reel's "
              "drive hub",
        "lamp": "The lamp tube: a black 2 x 2 round brick over the lamp hole",
        "brake": "The white reel-lock release, over its hole at the back",
        "rollers": "White tape guide rollers at the front corners, a white guide post, the "
                   "posts the top shell's flap pivots land on, and behind them a black 1 x 1 "
                   "brick: the front of a window rests on it",
        "ledges": "Ledges the window hangers land on",
        "tape_posts": "Bricks with a side stud: they carry the tape run"})
    # the tape by hand: its three plates in one step, its five tiles in two (3 and 2), so no
    # step is one lone piece (by distance alone the batch would split them 2 + 1 and 4 + 1)
    plates, tiles = [it for it in tape if it[3] == "tape_back"], [it for it in tape
                                                                   if it[3] == "tape"]
    for caption, run in (("The tape run: black 1 x N plates stood on their edges", plates),
                         ("Black tiles on them: the tape stretched across the front. The stud "
                          "at each end stays bare: a hinge plate of the flap hangs in front "
                          "of it", tiles[:3]),
                         ("", tiles[3:])):
        sub.step(caption)
        for part, colour, M, _, tag, insert in run:
            sub.place(part, colour, tag=tag, insert=insert).M = M
    return sub


# ------------------------------------------------------------------------------ windows
def window(model):
    """Door frame 1 x 6 x 6 laid flat with its glass: the frame's studs and anti-studs run
    across the cassette. A 2 x 6 plate stood on edge takes the frame's back end; half-round
    plates with a side stud hang it from the top shell."""
    s = model.submodel("window", "Window")
    s.step("A window: a 2 x 6 plate stood on its edge, studs to the front, and the door frame "
           "1 x 6 x 6 laid flat and pushed onto the plate's top row")
    s.place("3795", "shell", (0, -44, 82), STUDS_FWD)
    s.place("42205", "shell", (0, -54, -62), STUDS_FWD, insert=(0, 0, -1))
    s.step("The glass")
    s.place("42509", "glass", (0, -59, -58), STUDS_FWD)     # 1 LDU off LDCad's snap point:
                                                             # there the meshes overlap
    s.step("A tile caps the frame's front studs")
    s.place("6636", "shell", (0, -54, -70), STUDS_FWD, insert=(0, 0, -1))
    s.step("Six hangers on the plate's back row")
    for x in (-50, -30, -10, 10, 30, 50):
        s.place("3386", "shell", (x, -40, 100))
    return s


# ------------------------------------------------------------------------------ face label
LABEL_BASE = {(i, k) for i in range(-3, 4) for k in range(-4, 6)}
LABEL_TILES = {0: [(-3, 0), (1, 3)], 1: [(-3, -1), (0, 3)], 2: [(-3, 0), (1, 3)]}
SIDE_RIMS = {(s * 4, k) for s in (-1, 1) for k in range(-2, 4)}   # beside the windows


def label_layout(variant: int) -> Batch:
    """White 2 x N tiles (7 x 6 studs) in three staggered row pairs on black 1 x 10 plates
    that run front to back from the front grip band to the back one: the panel is the top
    shell's spine. The shell round it gives the label a black rim on all four sides."""
    b = Batch()
    for r in weave(LABEL_BASE, "z", (10,)):
        p, M = rect_M(PLATE, r, Y_T3)
        b.add(p, "shell", M, "base")
    for n, spans in LABEL_TILES.items():
        k0 = -2 + 2 * n
        for i0, i1 in spans:
            p, M = rect_M(TILE, (i0, i1, k0, k0 + 1), Y_T2)
            b.add(p, "label", M, "label")
    return b


def label_panel(model):
    sub = model.submodel("label", "Face label")
    best_layout(label_layout, [["base", "label"]]).emit(sub, [["base", "label"]], {
        "base": "The face label: black plates running front to back ...",
        "label": "... under white tiles, as big as fits between the windows"})
    return sub


# ------------------------------------------------------------------------------ top shell
def grille_row(k, half):
    """T1 tiles of one grip-band row: a plain tile in the middle, grilles out to |i| <= half,
    slots running along the cassette like the real ribs."""
    out = []
    plain = 1 if half % 2 == 0 else 3        # keeps the grilles in pairs
    if plain == 1:
        out.append(("3070b", transform((0, Y_T1, S * k))))
    else:
        out.append(("63864", transform((0, Y_T1, S * k))))
    start = (plain + 1) // 2
    for s in (-1, 1):
        for i in range(start, half + 1, 2):
            out.append(("2412b", transform((s * S * (i + 0.5), Y_T1, S * k))))
    return out


def top_cells():
    t1 = set()
    # (the front row stops four studs from each end: the corner is cut back for the flap's
    # hinge plates and pivot blocks, which sit on the pivot axis there, and its swing)
    t1 |= {(i, -5) for i in range(-7, 8)} | {(i, -4) for i in range(-10, 11)}
    t1 |= {(i, k) for i in range(-4, 5) for k in (-3, 4)} | SIDE_RIMS
    t1 |= {(s * 11, k) for s in (-1, 1) for k in range(-3, 5)}
    t1 |= {(i, k) for i in range(-11, 12) for k in (5, 6)}
    t3 = {(i, -4) for i in range(-9, 10)}     # none over the tape: it reads against shadow
    t3 -= {(s * round(BLOCK_X[1] / S), -4) for s in (-1, 1)}    # the inner pivot blocks
    t3 |= {(s * i, k) for s in (-1, 1) for i in (4, 11) for k in range(-3, 5)}
    t3 |= {(i, k) for i in range(-11, 12) for k in (5, 6)}
    return t1, t3 - LABEL_BASE


def top_layout(variant: int) -> Batch:
    b = Batch()

    def add(part, colour, M, cat, insert=None):
        b.add(part, colour, FLIP @ M, cat, insert=insert)

    t2_cells, t3_cells = top_cells()
    t1 = []
    for k, half in ((-5, 7), (-4, 10), (5, 11), (6, 11)):
        t1 += grille_row(k, half)
    for k in (-3, 4):                         # the label's black rim: front and back ...
        t1 += [("2431", transform((-50, Y_T1, S * k))), ("3070b", transform((0, Y_T1, S * k))),
               ("2431", transform((50, Y_T1, S * k)))]
    for s in (-1, 1):                         # ... and beside the windows
        t1.append(("6636", transform((s * 80, Y_T1, 10), rot(y=90))))
    for s in (-1, 1):                         # end strips beside the windows
        t1.append(("4162", transform((s * 220, Y_T1, 10), rot(y=90))))
    for part, M in t1:
        add(part, "shell", M, "t1")
    # columns across T1; but the three cells behind each cut-back corner, over both pivot
    # blocks, take a 1 x 3 plate along X: it ties the two grilles over them to the shell and
    # holds both blocks' studs (as columns they would be three loose 1 x 1s)
    corner = {(s * i, -4) for s in (-1, 1) for i in (8, 9, 10)}
    t2 = weave(t2_cells - corner, "z", phase=variant) + weave(corner, "x")
    for r in t2:
        p, M = rect_M(PLATE, r, Y_T2)
        add(p, "shell", M, "t2")
    for s in (-1, 1):                         # the flap's inner pivot blocks (Technic pin hole;
        add("11458", "shell", block_M(s, BLOCK_X[1]), "t3")   # the outer ones go on later)
    ends = {(s * i, k) for s in (-1, 1) for i in (4, 11) for k in range(-3, 5)}
    t3 = weave(t3_cells - ends, "x", phase=variant // 4) + weave(ends, "z")
    for r in t3:
        p, M = rect_M(PLATE, r, Y_T3)
        add(p, "shell", M, "t3")

    # bricks with side studs under the back band carry the spine label
    for x, part in ((-50, "30414"), (0, "87087"), (50, "30414"), (-220, "87087"),
                    (220, "87087")):
        add(part, "shell", transform((x, -40, 100), rot(y=180)), "feed")
    for part, colour, M in row_parts(PLATE2, [(-11, -6), (-5, -2), (-1, 1), (2, 5), (6, 11)],
                                     -20, 118, STUDS_BACK):
        add(part, colour, M, "spine_back")
    spine = [(-30, [(-11, -9, "shell"), (-8, -1, "label"), (0, 0, "label"), (1, 8, "label"),
                    (9, 11, "shell")]),
             (-10, [(-11, -9, "shell"), (-8, -5, "label"), (-4, -1, "label"), (0, 0, "label"),
                    (1, 4, "label"), (5, 8, "label"), (9, 9, "shell"), (11, 11, "shell")])]
    for y, spans in spine:
        for i0, i1, colour in spans:
            for part, _, M in row_parts(TILE1, [(i0, i1)], y, 126, STUDS_BACK):
                add(part, colour, M, "spine")
    add("3070b", "tab", transform((200, -10, 126), STUDS_BACK), "tab")   # write-protect tab
    return b


TOP_PHASES = [["t1", "t2"], ["t3"], ["feed"], ["spine_back"], ["spine", "tab"]]


def top_shell(model, win, label):
    sub = model.submodel("top_shell", "Top shell")
    b = best_layout(top_layout, TOP_PHASES)
    later = Batch()                           # after the label panel: spine and its bricks
    later.items = [it for it in b.items if it[3] not in ("t1", "t2", "t3")]
    b.items = [it for it in b.items if it[3] in ("t1", "t2", "t3")]
    b.emit(sub, TOP_PHASES[:2], {
        "t1": "Top shell, built upside down: the grip-band grilles and the black rims go "
              "face down, then plates on them",
        "t3": "A third layer, with the flap's inner pivot blocks (plates with a pin hole on "
              "top)"})
    merge_lone(sub)
    sub.step("The face label panel: it ties the front and back grip bands together")
    sub.use(label, FLIP[:3, 3], FLIP[:3, :3], insert=(0, -1, 0))
    later.emit(sub, TOP_PHASES[2:], {
        "feed": "Bricks with side studs for the spine label",
        "spine_back": "Spine label: plates stood on edge",
        "spine": "White tiles: the spine label; black tiles at the ends",
        "tab": "The write-protect tab: a tile you can pull off to protect your recording"})
    for s, x in ((0, -150), (1, 150)):
        sub.step("The window, hung on its six hangers" if s == 0 else "")
        M = FLIP @ translate(x, 0, 0)
        sub.use(win, M[:3, 3], M[:3, :3], insert=(0, -1, 0))
    pivots(sub)
    return sub


def pivots(sub):
    """The flap's hinges, last on the upside-down top shell, two at each front corner along
    the pivot axis. A pin goes into a hole only up to its collar, in the middle: it joins two
    holes when it is pushed into one and the other part slides onto its free half. So at each
    corner, in this order and all from the end: a pin into the inner pivot block (it is in
    the third layer), the inner hinge plate slid onto it; the outer pivot block on its stud
    (it would be in the way of that hinge plate before), a pin into it, the outer hinge plate
    onto that. The hinge plates turn on their pins; the flap goes on them last (`build`).
    Each corner's blocks and pins are tagged `pivots_l` (+X) / `pivots_r` (-X) for close-up
    renders (`brickkit render vhs_tape --views close:pivots_r`)."""
    R = FLIP[:3, :3]

    def put(part, colour, M, tag, came_from):
        """`came_from`: the way it goes on, in the cassette's frame (FLIP turns it)."""
        sub.place(part, colour, (0, 0, 0), tag=tag,
                  insert=tuple(R @ np.asarray(came_from, float))).M = FLIP @ M

    def corner(s):
        return "pivots_l" if s > 0 else "pivots_r"

    sub.step("The flap's hinges: two at each front corner. Push a pin into each inner pivot "
             "block from the end of the shell, up to the ridge in its middle: half of it "
             "sticks out", view="above")
    for s in (-1, 1):
        put("2780", "pin", pin_M(s, PIN_X[1]), corner(s), (s, 0, 0))
    sub.step("Slide a hinge plate (a 1 x 2 plate with a pin hole under one end) onto each pin, "
             "studs to the front")
    for s in (-1, 1):
        put("18677", "shell", hinge_M(s, HINGE_X[1]), "flap", (s, 0, 0))
    sub.step("The outer pivot blocks: a plate with a pin hole on top at each end, on its stud "
             "beside the hinge plate. Push a pin into each, from the end, half of it out",
             view="above")
    for s in (-1, 1):
        put("11458", "shell", block_M(s, BLOCK_X[0]), corner(s), (0, 1, 0))
        put("2780", "pin", pin_M(s, PIN_X[0]), corner(s), (s, 0, 0))
    sub.step("The outer hinge plates: slide one onto each pin, studs to the front. All four "
             "hinge plates turn on their pins")
    for s in (-1, 1):
        put("18677", "shell", hinge_M(s, HINGE_X[0]), "flap", (s, 0, 0))


# ------------------------------------------------------------------------------ dust flap
def flap(model):
    """A full-length flap built flat: plates stood on their faces with tiles on them. The
    top row is the upper half of 2 x N tiles hanging over the plates, so the flap's top edge
    is thin and swings clear of the top shell.

    Built to be handled: behind the tiles is one 2 x 16 plate, so the flap cannot fold at a
    seam, and at each end, plates that reach the top row: two 2 x 3 plates at one end, a 2 x 3
    and a 1 x 3 at the other (the 2 x 16 is a stud off the middle). The tiles at the ends hold
    them by their studs. On their backs the flap's four hinge plates (in the top shell,
    `pivots`) take two studs each, side by side, at x = +-220 and +-180."""
    sub = model.submodel("flap", "Dust flap")
    b = Batch()

    def add(part, colour, M, cat):
        b.add(part, colour, FLAT @ M, cat)

    for part, colour, M in row_parts(PLATE2, [(-8, 7)], -24, -118, STUDS_FWD):
        add(part, colour, M, "plates")           # (the 2 x 16)
    for part, x in (("3021", -210), ("3623", -180), ("3021", 170), ("3021", 210)):
        add(part, "shell", transform((x, -34, -118), UPRIGHT_1XN), "ends")
    for part, colour, M in row_parts(TILE2, [(-11, -6), (-5, -2), (-1, 1), (2, 5), (6, 11)],
                                     -44, -126, STUDS_FWD):
        add(part, colour, M, "top")
    # (the plates and the tiles over them in one phase: a plate goes down with the tile that
    # locks it to its neighbour, so no row lies loose)
    b.emit(sub, [["plates", "ends", "top"]], {
        "plates": "Dust flap, built flat: one long 2 x 16 plate and plates three studs long at "
                  "the ends, locked together by 2 x N tiles. The tiles' top halves hang over the "
                  "plates: they are the flap's top row",
        "ends": "At each end, plates three studs long reach the top row: the hinge plates go "
                "on their backs"})
    bottom = row_parts(TILE1, [(-11, -6), (-5, -2), (-1, 1), (2, 5), (6, 11)], -14, -126,
                       STUDS_FWD)
    for caption, run in (("Bottom row of tiles", bottom[:3]), ("", bottom[3:])):  # (3 and 2:
        sub.step(caption)                                       # no step of one lone tile)
        for part, colour, M in run:
            sub.place(part, colour).M = FLAT @ M
    return sub


# ------------------------------------------------------------------------------ checks & poses
REAL_MM = (187.0, 103.0, 25.0)


def check_dimensions(ctx):
    """Outer size must stay within 5 mm of a real VHS cassette (187 x 103 x 25 mm)."""
    pts = []
    for p in ctx.placed:
        lo, hi = ctx.geom.mesh(p.part).bbox
        corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1])
                            for z in (lo[2], hi[2])])
        pts.append(corners @ p.M[:3, :3].T + p.M[:3, 3])
    allp = np.concatenate(pts)
    size = (allp.max(0) - allp.min(0)) * 0.4
    got = (size[0], size[2], size[1])
    return [{"problem": f"{name} {g:.1f} mm is not within 5 mm of the real {want:.0f} mm"}
            for name, g, want in zip(("width", "depth", "height"), got, REAL_MM)
            if abs(g - want) > 5.0]


def pose(t: float) -> dict:
    """t = 0: flap shut, reels at rest. t = 1: flap up 90 degrees like a visor; the reels
    have turned as if playing (both the same way; the small take-up pack spins faster)."""
    y, z = PIVOT
    out = {"flap": translate(0, y, z) @ transform((0, 0, 0), rot(x=-90.0 * t))
           @ translate(0, -y, -z)}
    for g, deg in (("reel_l", 270.0), ("reel_r", 360.0)):
        ax = REEL_X[g]
        out[g] = (translate(ax, 0, REEL_Z) @ transform((0, 0, 0), rot(y=deg * t))
                  @ translate(-ax, 0, -REEL_Z))
    return out


def build(model):
    model.meta["mechanism_name"] = "Dust door and reels"
    model.meta["mechanism_labels"] = ["closed", "open"]
    reels = {"reel_l": reel(model, "reel_full", "Supply reel (full)", True),
             "reel_r": reel(model, "reel_empty", "Take-up reel", False)}
    chassis = core(model)
    win = window(model)
    label = label_panel(model)
    top = top_shell(model, win, label)
    door = flap(model)

    main = model.main
    main.step("Take the chassis and drop the supply reel into the right-hand drive hole: the "
              "white drive hub under the reel goes down into the small square between the "
              "four tiles")
    main.use(chassis)
    main.use(reels["reel_l"], (REEL_X["reel_l"], -16, REEL_Z), tag="reel_l",
             insert=(0, -1, 0))
    main.step("The take-up reel into the left-hand drive hole")
    main.use(reels["reel_r"], (REEL_X["reel_r"], -16, REEL_Z), tag="reel_r",
             insert=(0, -1, 0))
    main.step("End walls")
    for s in (-1, 1):
        main.place("3008", "shell", (s * 220, -40, 10), rot(y=90))
        main.place("3005", "shell", (s * 220, -40, -80))     # the wall, one stud further forward
        main.place("3070b", "shell", (s * 220, -24, -100))   # a tile at the corner: the flap's
        #                                                       hinge plate comes down onto it
    main.step("Lower the top shell onto the chassis. Turn the four hinge plates at the front "
              "corners to hang straight down, studs to the front", view="above")
    main.use(top, FLIP[:3, 3], FLIP[:3, :3], insert=(0, -1, 0))
    main.step("Press the dust flap onto the four hinge plates: each one's two studs go into the "
              "back of the plates at the flap's ends")
    main.use(door, (0, 0, 0), rot(x=90), tag="flap", insert=(0, 0, -1))

    model.moving_group("flap", "flap")
    model.moving_group("reel_l", "reel_l")
    model.moving_group("reel_r", "reel_r")
    for g in ("reel_l", "reel_r"):
        model.captive(g, "the reel's drive hub turns in the square the chassis' tiles leave "
                         "round it; the top shell keeps the reel down")
    model.pose = pose
    model.extra_checks.append(check_dimensions)
