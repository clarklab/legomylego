"""VHS Cassette - a life-size (1:1) VHS video cassette in real LEGO.

Units: LDU (stud 20, plate 8, brick 24), -Y is up, the dust door faces the front (-Z).
Footprint 23 x 13 studs (x -230..230, z -130..130), 8 plates tall (y -64..0), i.e.
184.0 x 104.0 x 25.6 mm against the real 187 x 103 x 25 mm.

Sub-assemblies: bottom half (floor, walls, tape path, door hinge bases), dust door, the
two reels and the top half (smoked window, labels, reel pins; the reels hang in it).
Moving groups: `flap` (door, about its hinge axis) and `reel_l` / `reel_r` (reels, about
their pins). `reel_l` is the supply reel - on the left when you hold the cassette label-up
with the door pointing away from you, which is +X here.
"""
from __future__ import annotations

import numpy as np

from brickkit.ldraw.matrix import rot, transform, translate
from kit import (BIG_PLATES, BRICK, PLATE, S, TILE, TILES, Batch, cell_ids, line_rects,
                 pack, quarter_M, rect_M)

Y_BOTTOM, Y_FLOOR = -8, -16              # bottom plates [-8, 0], floor tiles [-16, -8]
Y_C1, Y_C2, Y_C3 = -16, -40, -48          # wall courses: plate, brick, plate
Y_TOP_PLATE, Y_TOP_TILE = -56, -64
NI, NK = 11, 6                           # cells: x = 20 i (|i| <= 11), z = 20 k (|k| <= 6)

REEL_AXES = {"reel_l": (110, 10), "reel_r": (-110, 10)}   # supply (full) at +X
DOOR_AXIS = (-50, -104)                  # (y, z) of the door hinge axis, which runs along X
HINGE_X = (-30, 30)                      # the two door hinges
HINGE_W = rot(x=90) @ rot(y=180)         # 3937 / 6134 with the hinge top facing the front
SNOT = rot(x=90)                         # studs facing the front (-Z); local +Z is world up

CELLS = {(i, k) for i in range(-NI, NI + 1) for k in range(-NK, NK + 1)}


def near(cells, x, z, r):
    """Cells whose centres are within r (in x and in z) of (x, z)."""
    return {(i, k) for i, k in cells if abs(S * i - x) < r and abs(S * k - z) < r}


# ------------------------------------------------------------------------------ bottom half
SCREWS = [(-10, -2), (10, -2), (-9, 5), (9, 5), (0, 5)]   # screw heads, recessed in the floor
ROUND_HOLES = [(0, -2), (0, 0)]           # lamp hole, reel-lock release hole
# floor plates laid out by hand where the edge structure needs them to reach the floor tiles
FIXED_FLOOR = [(-9, -2, -4, -3), (-1, 1, -4, -3), (2, 9, -4, -3)]     # under the front beam
for _s in (-1, 1):
    FIXED_FLOOR += [tuple(sorted((_s * 10, _s * 11))) + (-6, -6),       # front corner
                    tuple(sorted((_s * 8, _s * 11))) + (-5, -5),        # mouth end + corner
                    tuple(sorted((_s * 10, _s * 11))) + (-4, -3),       # behind the corner
                    tuple(sorted((_s * 10, _s * 11))) + (4, 6)]         # back corner


def bottom_layout(variant: int) -> Batch:
    b = Batch()
    spindle = set().union(*(near(CELLS, ax, az, 40) for ax, az in REEL_AXES.values()))
    posts = {(0, 5)}                      # screw boss at the back centre

    # bottom plates
    cells = {(i, k) for i, k in CELLS
             if not (k == -6 and abs(i) <= 9) and not (k == -5 and abs(i) <= 7)}
    cells -= spindle | set(SCREWS) | set(ROUND_HOLES)
    cells -= set(cell_ids(FIXED_FLOOR))
    order, prefer, shift = [("col", "z", 0), ("row", "x", 0), ("col", "z", 7), ("row", "x", 11),
                            ("col", "x", 3), ("row", "z", 5)][variant % 6]
    base = FIXED_FLOOR + pack(cells, BIG_PLATES, order, prefer, shift=shift + variant // 6 * 13)
    below = cell_ids(base)
    for r in base:
        p, M = rect_M(PLATE, r, Y_BOTTOM)
        b.add(p, "shell", M, "floor")
    for i, k in SCREWS:
        b.add("6141", "metal", transform((S * i, Y_BOTTOM, S * k)), "screws")
    for i, k in ROUND_HOLES:
        b.add("85861", "shell", transform((S * i, Y_BOTTOM, S * k)), "floor")

    # course 1 of the walls (level with the floor tiles)
    c1 = [(10, 11, -6, -4), (-11, -10, -6, -4)]                # front corners + beam ends
    for s in (-1, 1):
        c1 += line_rects([(s * 11, k) for k in range(-3, 7)], phase=(3, 4)[variant % 2])
    c1 += [(-10, -9, 6, 6)] + line_rects([(i, 6) for i in range(-8, 9)], phase=4)
    c1 += [(9, 9, 6, 6), (0, 0, 4, 5)]
    for r in c1:
        white = r[2] == r[3] == 6 and -8 <= r[0] and r[1] <= 8
        p, M = rect_M(PLATE, r, Y_C1)
        b.add(p, "label" if white else "shell", M, "walls_1")
    b.add("3024", "detail", transform((S * 10, Y_C1, S * 6)), "walls_1")   # write-protect tab
    taken = cell_ids(c1) | {(10, 6): 0}

    # smooth floor for the reels, with round rims around the drive holes
    floor = {(i, k) for i in range(-10, 11) for k in range(-3, 6)} - set(taken)
    rim = set().union(*(near(CELLS, ax, az, 60) for ax, az in REEL_AXES.values()))
    for r in pack(floor - rim, TILES, "row", "x", below=below, shift=variant // 3):
        p, M = rect_M(TILE, r, Y_FLOOR)
        b.add(p, "shell", M, "floor_tiles")
    for ax, az in REEL_AXES.values():
        for dx in (-50, 50):
            for dz in (-50, 50):
                b.add("98138", "shell", transform((ax + dx, Y_FLOOR, az + dz)), "floor_tiles")
        for q in range(4):
            b.add("79393", "shell", quarter_M("79393", q, Y_FLOOR, (ax, az)), "spindle")

    # course 2: bricks; the spine label shows white on the back wall
    for s in (-1, 1):
        for r in line_rects([(s * 11, k) for k in range(-4, 7)], (6, 4, 3, 2, 1), phase=2):
            p, M = rect_M(BRICK, r, Y_C2)
            b.add(p, "shell", M, "walls_2")
        b.add("3005", "shell", transform((s * 200, Y_C2, -120)), "corners")
        for i in (10, 11):                       # light path: a hole through each front corner
            b.add("6541", "shell", transform((s * S * i, Y_C2, -100), rot(y=90)), "corners")
        b.add("3005", "shell", transform((s * S * 10, Y_C2, -80)), "walls_2")
    b.add("4070", "button", transform((-220, Y_C2, -120), rot(y=90)), "corners")  # door release
    b.add("3005", "shell", transform((220, Y_C2, -120)), "corners")
    back = [(-10, -9, 6, 6)] + line_rects([(i, 6) for i in range(-8, 9)], (6, 4, 3, 2, 1),
                                          phase=3) + [(9, 10, 6, 6)]
    for r in back:
        white = -8 <= r[0] and r[1] <= 8
        p, M = rect_M(BRICK, r, Y_C2)
        b.add(p, "label" if white else "shell", M, "walls_2")
    for i, k in posts:
        b.add("3005", "shell", transform((S * i, Y_C2, S * k)), "walls_2")

    # front beam: tape backing (bricks with side studs), metal guide pins, rollers, cap plates
    for x in (-130, -50, 50, 130):
        b.add("30414", "shell", transform((x, -32, -80)), "tape_path")
    b.add("87087", "shell", transform((0, -32, -80)), "tape_path")
    for s in (-1, 1):
        for y in (-16, -24, -32):
            b.add("6141", "metal", transform((s * 180, y, -80)), "tape_path")
        b.add("3062b", "roller", transform((s * 180, -32, -100)), "tape_path")
    for x0, x1 in ((-190, -30), (-30, 30), (30, 190)):
        b.add(PLATE[(1, (x1 - x0) // S)], "shell", transform(((x0 + x1) / 2, Y_C2, -80)),
              "beam_top")
    for x0, x1 in ((-170, -110), (-110, -30), (-30, 30), (30, 110), (110, 170)):   # the tape
        b.add(TILE[(1, (x1 - x0) // S)], "tape", transform(((x0 + x1) / 2, -22, -98), SNOT),
              "tape")

    # course 3: plates tying the walls, the beam and the corners together
    c3 = [(10, 11, -6, -5), (-11, -10, -6, -5), (0, 0, -4, -4), (0, 0, 5, 5)]
    c3 += line_rects([(i, -4) for i in range(-11, -2)], phase=4)
    c3 += line_rects([(i, -4) for i in range(3, 12)], phase=5)
    for s in (-1, 1):
        c3 += line_rects([(s * 11, k) for k in range(-3, 7)], phase=(5, 2)[variant % 2])
    c3 += line_rects([(i, 6) for i in range(-10, 11)], phase=5)
    for r in c3:
        p, M = rect_M(PLATE, r, Y_C3)
        b.add(p, "shell", M, "walls_3")

    # the door's hinge mounts: side-stud plates carrying the hinge bases
    for x in HINGE_X:
        b.add("99206", "shell", transform((x, Y_TOP_PLATE, -80)), "hinge_mounts")
        b.add("3937", "shell", transform((x, DOOR_AXIS[0], -114), HINGE_W), "hinges")
    return b


BOTTOM_PHASES = [["floor", "screws", "floor_tiles", "spindle", "walls_1"],
                 ["corners", "walls_2"], ["tape_path", "beam_top"], ["tape"], ["walls_3"],
                 ["hinge_mounts"], ["hinges"]]


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


def bottom_half(model):
    sub = model.submodel("bottom_half", "Bottom half")
    best_layout(bottom_layout, BOTTOM_PHASES).emit(sub, BOTTOM_PHASES, {
        "floor": "Bottom half: floor plates, tied together by the tiles and the first wall course",
        "screws": "Silver screw heads sit in the floor: five of them, like the real thing",
        "spindle": "Round rims around the two reel drive holes",
        "floor_tiles": "Smooth floor tiles: the reels slide on these",
        "walls_1": "First course of the walls; the spine label starts white at the back",
        "corners": "Front corners: a hole through each side for the tape-end light path, "
                   "and the grey door release button on the right",
        "walls_2": "Walls",
        "tape_path": "Tape path: backing bricks with side studs, silver guide pins, white rollers",
        "beam_top": "Cap the front beam",
        "tape": "Stretch the tape across the mouth",
        "walls_3": "Top course: ties the walls, corners and front beam together",
        "hinge_mounts": "Door hinge mounts: plates with studs on the side",
        "hinges": "Hinge bases, pushed onto the side studs"})
    return sub


# ------------------------------------------------------------------------------ dust door
def door(model):
    sub = model.submodel("door", "Dust door")
    P1 = {1: "3024", 2: "3023", 3: "3623", 4: "3710", 6: "3666", 8: "3460"}
    P2 = {2: "3022", 3: "3021", 4: "3020", 6: "3795", 8: "3034"}
    T1 = {1: "3070b", 2: "3069b", 3: "63864", 4: "2431", 6: "6636", 8: "4162"}
    T2 = {2: "3068b", 3: "26603", 4: "87079", 6: "69729"}

    def run(table, x0, x1, y, z):
        """SNOT part spanning x0..x1, face centred at height y, body front at z."""
        sub.place(table[(x1 - x0) // S], "shell", ((x0 + x1) / 2, y, z), SNOT)

    sub.step("Dust door, built flat: start with a 2 x 6 plate")
    run(P2, -190, -70, -40, -122)
    sub.step("Add plates and tie them with a tile")
    run(P2, -70, -30, -40, -122)
    run(P2, -30, 30, -40, -122)
    run(T1, -130, -10, -50, -130)
    sub.step("Complete the plate row")
    run(P2, 30, 70, -40, -122)
    run(P2, 70, 190, -40, -122)
    run(T1, 10, 130, -50, -130)
    run(T1, -10, 10, -50, -130)
    sub.step("Smooth outer face")
    run(T1, -190, -130, -50, -130)
    run(T1, 130, 190, -50, -130)
    for x0, x1 in ((-190, -130), (-130, -10), (10, 130), (130, 190)):
        run(T2, x0, x1, -20, -130)
    sub.place("3069b", "shell", (0, -20, -130), SNOT @ rot(y=90))
    sub.step("Lower edge of the door")
    for x0, x1 in ((-190, -30), (-30, 30), (30, 190)):
        run(P1, x0, x1, -10, -122)
    for z, caption in ((-114, "Top edge: fillers that swing up with the door"),
                       (-106, "Second layer of fillers")):
        sub.step(caption)
        for x0, x1 in ((-190, -110), (-110, -50), (-10, 10), (50, 110), (110, 190)):
            run(P1, x0, x1, -50, z)
    sub.step("Hinge tops")
    for x in HINGE_X:
        sub.place("6134", "shell", (x, DOOR_AXIS[0], -114), HINGE_W)
    return sub


# ------------------------------------------------------------------------------ reels
def reel(model, name: str, title: str, full: bool):
    """A reel: white lower flange, tape pack, raised white hub with a centre bore; it turns
    on a half pin that hangs from the top half."""
    s = model.submodel(name, title)
    s.step("Hub core: the pin runs through its opening")
    s.place("11833", "hub", (0, -16, 0))
    s.step("Lower flange from four quarter circles")
    for q in range(4):
        s.place("30565", "flange", (0, 0, 0)).M = quarter_M("30565", q, -8)
    s.step("Tape wound on the reel" if full
           else "Just a few turns of tape left, so the flange shows")
    for q in range(4):
        s.place("79393", "tape", (0, 0, 0)).M = quarter_M("79393", q, -16)
        s.place("27507", "tape" if full else "flange", (0, 0, 0)).M = quarter_M("27507", q, -16)
    s.step("Hub with its drive teeth")
    s.place("60474", "hub", (0, -24, 0))
    return s


# ------------------------------------------------------------------------------ top half
def top_layout(variant: int) -> Batch:
    b = Batch()
    top = {(i, k) for i, k in CELLS if k >= -4 or abs(i) >= 10}
    hinge_raised = {(i, -4) for i in (-2, -1, 1, 2)}
    pins = set().union(*(near(CELLS, ax, az, 20) for ax, az in REEL_AXES.values()))
    win_tiles = {(i, k) for i in range(-7, 8) for k in range(-1, 3)}
    win_plates = {(i, k) for i in range(-7, 8) for k in range(-2, 4)} - pins
    label = {(i, k) for i in range(-8, 9) for k in (4, 5)}
    grip = {(i, k) for i in (-11, -10, 10, 11) for k in (-6, -5)}
    arrows = {(i, k) for i in (-3, -2, 2, 3) for k in (-4, -3, -2)}

    order, prefer, shift = [("row", "x", 0), ("col", "z", 0), ("row", "x", 9), ("col", "z", 5),
                            ("row", "z", 3), ("col", "x", 17)][variant % 6]
    plates = pack(top - hinge_raised - pins - win_plates, BIG_PLATES, order, prefer,
                  shift=shift + variant // 6 * 7)
    # smoked glass: plates run front-to-back and are staggered column by column, so they
    # straddle the edge rows where the black frame tiles take over (that bonds the window in)
    glass = []
    for i in range(-7, 8):
        pin_col = (i, 0) in pins
        splits = [(-2, -1), (2, 3)] if pin_col else (
            [(-2, -1), (0, 1), (2, 3)] if i % 2 == 0 else [(-2, -2), (-1, 0), (1, 2), (3, 3)])
        glass += [(i, i, k0, k1) for k0, k1 in splits]
    below = cell_ids(plates) | cell_ids(glass, 1000)
    for r in plates:
        p, M = rect_M(PLATE, r, Y_TOP_PLATE)
        b.add(p, "shell", M, "plates")
    for r in glass:
        p, M = rect_M(PLATE, r, Y_TOP_PLATE)
        b.add(p, "window", M, "window")
    for ax, az in REEL_AXES.values():
        b.add("4032a", "bore", transform((ax, Y_TOP_PLATE, az)), "window")
    for k in range(-1, 3):                    # glass tiles run left-right, staggered by row
        cuts = [-7] + list(range(-6 if k % 2 == 0 else -5, 8, 2))
        edges = cuts + [8]
        for i0, i1 in zip(edges, edges[1:]):
            p, M = rect_M(TILE, (i0, i1 - 1, k, k), Y_TOP_TILE)
            b.add(p, "window", M, "window_tiles")
    for x in (-130, -50, 50, 130):
        b.add("87079", "label", transform((x, Y_TOP_TILE, 90)), "label")
    b.add("3069b", "label", transform((0, Y_TOP_TILE, 90), rot(y=90)), "label")
    for s in (-1, 1):
        for k in (-6, -5):
            b.add("2412b", "shell", transform((s * 210, Y_TOP_TILE, S * k)), "grip")
        b.add("22385", "arrow", transform((s * 50, Y_TOP_TILE, -60)), "arrows")
    rest = top - win_tiles - label - grip - arrows
    for r in pack(rest, TILES, ("col", "row")[variant % 2], "z", below=below):
        p, M = rect_M(TILE, r, Y_TOP_TILE)
        b.add(p, "shell", M, "tiles")
    return b


TOP_PHASES = [["plates", "window", "tiles", "window_tiles", "label", "grip", "arrows"]]


def top_half(model, reels):
    sub = model.submodel("top_half", "Top half")
    best_layout(top_layout, TOP_PHASES).emit(sub, TOP_PHASES,
                 {"plates": "Top half, built face up: plates first",
                  "window": "Smoked window: see-through plates, and black holders over the "
                            "reel hubs",
                  "window_tiles": "Window glass tiles",
                  "tiles": "Smooth top tiles",
                  "label": "White face label recess",
                  "grip": "Grip ridges on the front corners",
                  "arrows": "Moulded arrows pointing to the door"})
    sub.step("Turn the top half over and push in the two reel pins")
    for ax, az in REEL_AXES.values():
        sub.place("4274", "spring", (ax, -48, az), rot(z=-90))
    sub.step("Slide the full supply reel onto its pin")
    ax, az = REEL_AXES["reel_l"]
    sub.use(reels["reel_l"], (ax, -16, az), tag="reel_l", insert=(0, 1, 0))
    sub.step("Slide the nearly empty take-up reel onto its pin")
    ax, az = REEL_AXES["reel_r"]
    sub.use(reels["reel_r"], (ax, -16, az), tag="reel_r", insert=(0, 1, 0))
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
    """t = 0: door shut, reels at rest. t = 1: door up 90 degrees; the reels have turned as if
    playing (both the same way; the small take-up pack spins faster, 4 : 3)."""
    y, z = DOOR_AXIS
    out = {"flap": translate(0, y, z) @ transform((0, 0, 0), rot(x=-90.0 * t))
           @ translate(0, -y, -z)}
    for g, deg in (("reel_l", 270.0), ("reel_r", 360.0)):
        ax, az = REEL_AXES[g]
        out[g] = (translate(ax, 0, az) @ transform((0, 0, 0), rot(y=deg * t))
                  @ translate(-ax, 0, -az))
    return out


def build(model):
    reels = {"reel_l": reel(model, "reel_full", "Supply reel (full)", True),
             "reel_r": reel(model, "reel_empty", "Take-up reel (nearly empty)", False)}
    bottom = bottom_half(model)
    flap = door(model)
    top = top_half(model, reels)

    main = model.main
    main.step("The bottom half")
    main.use(bottom)
    main.step("Click the dust door onto its two hinges")
    main.use(flap, tag="flap", insert=(0, 0, -1))
    main.step("Lower the top half, reels and all, onto the bottom half")
    main.use(top, insert=(0, -1, 0))

    model.moving_group("flap", "flap")
    model.moving_group("reel_l", "reel_l")
    model.moving_group("reel_r", "reel_r")
    model.pose = pose
    model.extra_checks.append(check_dimensions)
