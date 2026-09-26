"""VHS Cassette - a life-size (1:1) VHS video cassette in real LEGO.

Units: LDU (stud 20, plate 8, brick 24), -Y is up, the dust flap faces the front (-Z).
Body 23 x 12 studs (x -230..230, z -110..130), the flap 16 LDU in front of it, 8 plates
tall (y -64..0): 184.0 x 102.4 x 25.6 mm against the real 187 x 103 x 25 mm.

Built like a modern display set: an inner chassis (the core: floor, spindle bearings, lamp
tube, brake release, tape run, guide rollers and the posts the shell lands on), two reels that
drop onto their spindles, end walls, a top shell built upside down (grip bands, two glass
windows on SNOT hangers, recessed face label, spine label) and a full-length dust flap
hung on two Technic pins.

Moving groups: `flap` (the dust flap, about the pin axis) and `reel_l` / `reel_r` (reels,
about their red spindle axles). `reel_l` is the supply reel: on the left when you hold the
cassette label-up with the flap pointing away from you, which is +X here.
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
PIVOT = (-54.0, -100.0)                  # (y, z) of the flap's pin axis, which runs along X
LAMP = (10, -50)                         # lamp tube centre (a 2 x 2 round brick sits on a
                                         # cell corner, 4 mm right of the middle)
STUDS_FWD = rot(x=90)                    # SNOT: studs toward -Z, part's top face at origin z
STUDS_BACK = rot(x=-90)                  # SNOT: studs toward +Z
UPRIGHT_1XN = orient((0, 1, 0), (0, 0, 1), (1, 0, 0))   # 1 x N along Y, studs toward -Z
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


def row_parts(table, spans, y, z, R, colour="shell"):
    """1 x N (or 2 x N) SNOT runs along X: spans of (i0, i1); y is the run's centre."""
    out = []
    for i0, i1 in spans:
        n = i1 - i0 + 1
        x = S * (i0 + i1) / 2
        Rr = R @ rot(y=90) if (table is PLATE2 and n == 1) else R
        out.append((table[n], colour, transform((x, y, z), Rr)))
    return out


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
    """A reel built around its own axis: a white lower flange (8 x 8 round plate), a black
    tape pack, a clear upper flange ring (Trans-Clear 4 x 4 macaroni tiles, r 60..80 LDU) and
    a white hub: a flat ring of 2 x 2 macaroni tiles round a 2 x 2 round plate whose four
    studs are the hub's bumps. A red Technic axle runs through the round plates' holes and
    the hub's axle hole: its end is the red dot in the middle of the hub, and underneath it
    is the spindle that turns in the chassis' round bearing holes."""
    s = model.submodel(name, title)
    s.step("Lower flange: a white 8 x 8 round plate with a hole in the middle")
    s.place("74611", "flange", (0, -8, 0))
    if full:
        s.step("A full pack of tape: a black 8 x 8 round plate")
        s.place("74611", "tape", (0, -16, 0))
    else:
        s.step("Nearly empty: a second white plate, so the flange shows round a thin pack")
        s.place("74611", "flange", (0, -16, 0))
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
    s.step("The red spindle: push the axle up through the hub")
    s.place("32062", "spindle", (0, -4, 0), rot(z=90), insert=(0, 1, 0))
    return s


# ------------------------------------------------------------------------------ chassis
SCREWS = [(-10, -3), (10, -3), (-10, 4), (10, 4), (0, 5)]


def core_layout(variant: int) -> Batch:
    b = Batch()
    floor = {(i, k) for i, k in CELLS if k <= 5} - MOUTH

    # F0 [-8, 0]: the bottom, with its round holes and screw heads
    f0_fixed = set()
    for x in REEL_X.values():             # Technic plate: its middle hole is the drive hole
        b.add("3709b", "shell", transform((x, Y_F0, REEL_Z)), "f0")
        f0_fixed |= cells(x - 40, x + 40, REEL_Z - 20, REEL_Z + 20)
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
    for x in REEL_X.values():             # round tile with a hole: the spindle's upper bearing
        b.add("15535", "shell", transform((x, Y_F1, REEL_Z)), "f1")
        f1_fixed |= cells(x - 20, x + 20, REEL_Z - 20, REEL_Z + 20)
    b.add("4032a", "shell", transform((LAMP[0], Y_F1, LAMP[1])), "f1")
    f1_fixed |= cells(LAMP[0] - 20, LAMP[0] + 20, LAMP[1] - 20, LAMP[1] + 20)
    for s in (-1, 1):                     # white bases of the guide rollers and posts
        b.add("6141", "roller", transform((s * 200, Y_F1, -100)), "f1")
        b.add("6141", "roller" if s < 0 else "shell", transform((s * 200, Y_F1, -80)), "f1")
        f1_fixed |= {(s * 10, -5), (s * 10, -4)}
    rest = floor - f1_fixed
    smooth = {c for c in rest if reel_dist(*c) < 90}
    for r in weave(smooth, "z", (8, 6, 4, 3, 2, 1), phase=variant // 4):   # columns along Z
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
    for x in (-180, 0, 180):               # bricks with a side stud carry the tape run
        b.add("87087", "shell", transform((x, -40, -80)), "tape_posts")

    # the tape: black tiles on a plate stood on its edge, studs to the front
    for part, colour, M in row_parts(PLATE1, [(-9, -2), (-1, 1), (2, 9)], -30, -98,
                                     STUDS_FWD, "tape"):
        b.add(part, colour, M, "tape_back", insert=(0, 0, -1))
    for part, colour, M in row_parts(TILE1, [(-9, -4), (-3, -1), (0, 0), (1, 3), (4, 9)],
                                     -30, -106, STUDS_FWD, "tape"):
        b.add(part, colour, M, "tape", insert=(0, 0, -1))
    return b


CORE_PHASES = [["f0", "f1"], ["lamp", "brake"], ["rollers", "ledges", "tape_posts"],
               ["tape_back"], ["tape"]]


def core(model):
    sub = model.submodel("core", "Chassis")
    best_layout(core_layout, CORE_PHASES).emit(sub, CORE_PHASES, {
        "f0": "Chassis, bottom layer: the Technic plates' middle holes are the reel drive "
              "holes and the lamp hole; silver screw heads sit flush underneath",
        "f1": "Second floor layer: smooth tiles where the reels turn, round tiles with a "
              "hole over the drive holes (the spindle bearings)",
        "lamp": "The lamp tube: a black 2 x 2 round brick over the lamp hole",
        "brake": "The white reel-lock release, over its hole at the back",
        "rollers": "White tape guide rollers at the front corners, a white guide post and "
                   "the posts the top shell's flap pivots land on",
        "ledges": "Ledges the window hangers land on",
        "tape_posts": "Bricks with a side stud: they carry the tape run",
        "tape_back": "The tape run: a black 1 x N plate stood on its edge",
        "tape": "Black tiles on it: the tape stretched across the front"})
    return sub


# ------------------------------------------------------------------------------ windows
def window(model):
    """Door frame 1 x 6 x 6 laid flat with its glass: the frame's studs and anti-studs run
    across the cassette. A 2 x 6 plate stood on edge takes the frame's back end; half-round
    plates with a side stud hang it from the top shell."""
    s = model.submodel("window", "Window")
    s.step("A window: a 2 x 6 plate stood on its edge, studs to the front")
    s.place("3795", "shell", (0, -44, 82), STUDS_FWD)
    s.step("Door frame 1 x 6 x 6, laid flat and pushed onto the plate's top row")
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
    t1 |= {(i, -5) for i in range(-9, 10)} | {(i, -4) for i in range(-10, 11)}
    t1 |= {(i, k) for i in range(-4, 5) for k in (-3, 4)} | SIDE_RIMS
    t1 |= {(s * 11, k) for s in (-1, 1) for k in range(-3, 5)}
    t1 |= {(i, k) for i in range(-11, 12) for k in (5, 6)}
    t3 = {(i, -4) for i in range(-9, 10)}     # none over the tape: it reads against shadow
    t3 |= {(s * i, k) for s in (-1, 1) for i in (4, 11) for k in range(-3, 5)}
    t3 |= {(i, k) for i in range(-11, 12) for k in (5, 6)}
    return t1, t3 - LABEL_BASE


def top_layout(variant: int) -> Batch:
    b = Batch()

    def add(part, colour, M, cat, insert=None):
        b.add(part, colour, FLIP @ M, cat, insert=insert)

    t2_cells, t3_cells = top_cells()
    t1 = []
    for k, half in ((-5, 9), (-4, 10), (5, 11), (6, 11)):
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
    t2 = weave(t2_cells, "z", phase=variant)                       # columns across T1
    for r in t2:
        p, M = rect_M(PLATE, r, Y_T2)
        add(p, "shell", M, "t2")
    for s in (-1, 1):                         # the flap's pivot blocks (Technic pin hole)
        add("11458", "shell", transform((s * 200, Y_T3, -90), rot(y=90)), "t3")
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
        "t3": "A third layer, with the flap's pivot blocks (plates with a pin hole)"})
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
    return sub


# ------------------------------------------------------------------------------ dust flap
def flap(model):
    """A full-length flap built flat: plates stood on their faces with tiles on them. The
    top row is the upper half of 2 x N tiles hanging over the plates, so the flap's top edge
    is thin and swings clear of the top shell. Technic bricks at the ends are its cheeks."""
    sub = model.submodel("flap", "Dust flap")

    def add(part, colour, M, insert=None):
        sub.place(part, colour, insert=insert).M = FLAT @ M

    sub.step("Dust flap, built flat: plates for the two lower rows")
    for part, colour, M in row_parts(PLATE2, [(-10, -5), (-4, -1), (0, 0), (1, 4), (5, 10)],
                                     -24, -118, STUDS_FWD):
        add(part, colour, M)
    sub.step("A 1 x 3 plate at each end reaches the top row")
    for s in (-1, 1):
        add("3623", "shell", transform((s * 220, -34, -118), UPRIGHT_1XN))
    sub.step("2 x N tiles: their top halves hang over the plates and make the flap's top row")
    for part, colour, M in row_parts(TILE2, [(-11, -6), (-5, -2), (-1, 1), (2, 5), (6, 11)],
                                     -44, -126, STUDS_FWD):
        add(part, colour, M)
    sub.step("Bottom row of tiles")
    for part, colour, M in row_parts(TILE1, [(-11, -6), (-5, -2), (-1, 1), (2, 5), (6, 11)],
                                     -14, -126, STUDS_FWD):
        add(part, colour, M)
    sub.step("Turn it over: Technic bricks at the ends are the flap's cheeks")
    for s in (-1, 1):
        add("6541", "shell", transform((s * 220, -54, -110), UPRIGHT_1XN))
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
             "reel_r": reel(model, "reel_empty", "Take-up reel (nearly empty)", False)}
    chassis = core(model)
    win = window(model)
    label = label_panel(model)
    top = top_shell(model, win, label)
    door = flap(model)

    main = model.main
    main.step("The chassis")
    main.use(chassis)
    main.step("Drop the full supply reel onto the right-hand bearing: its red axle goes "
              "down through the round holes")
    main.use(reels["reel_l"], (REEL_X["reel_l"], -16, REEL_Z), tag="reel_l",
             insert=(0, -1, 0))
    main.step("The nearly empty take-up reel on the left-hand bearing")
    main.use(reels["reel_r"], (REEL_X["reel_r"], -16, REEL_Z), tag="reel_r",
             insert=(0, -1, 0))
    main.step("End walls")
    for s in (-1, 1):
        main.place("3008", "shell", (s * 220, -40, 10), rot(y=90))
        main.place("3023", "shell", (s * 220, -24, -90), rot(y=90))
        main.place("3023", "shell", (s * 220, -32, -90), rot(y=90))
    main.step("Lower the top shell onto the chassis")
    main.use(top, FLIP[:3, 3], FLIP[:3, :3], insert=(0, -1, 0))
    main.step("Hold the dust flap in place and push a pin through each cheek")
    main.use(door, (0, 0, 0), rot(x=90), tag="flap", insert=(0, 0, -1))
    for s in (-1, 1):
        main.place("2780", "pin", (s * 210, PIVOT[0], PIVOT[1]))

    model.moving_group("flap", "flap")
    model.moving_group("reel_l", "reel_l")
    model.moving_group("reel_r", "reel_r")
    for g in ("reel_l", "reel_r"):
        model.captive(g, "the reel turns on its red spindle in the chassis' round bearing "
                         "holes; the top shell keeps it down")
    model.pose = pose
    model.extra_checks.append(check_dimensions)
