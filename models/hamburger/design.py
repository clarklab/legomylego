"""Hamburger: a life-size LEGO burger in six separately built layers that click together.

Frame: LDU, -Y up, front is -Z. Every layer is built with its underside at local y = 0 and
grows toward -Y. They share one interface: a 4 x 4 plate of studs in the middle of the top face
(cells -2..1) and open anti-studs under the middle of the bottom face, so the fillings stack in
any order and any quarter turn between the buns. The top bun is the lid: a dome with no studs
free on top.

The buns and the patty are octagons 14 studs across (kit.py): four sides on the stud grid and four
diagonal "faces" turned 45 degrees, each standing on smooth tiles and pinned by one stud.
"""
from __future__ import annotations

import math

import numpy as np

from brickkit.ldraw.matrix import rot, translate

import kit
from kit import (BRICKS, CENTER, OCT6, OCT7, PLATES, QUADS, S, TILES, CUT_TURN, Face,
                 bonded_pair, cells_under, lay, octagon6, octagon7, place_rect, rect_cells,
                 rect_of, turn_toward)

SIDES = [(1, 0), (0, 1), (-1, 0), (0, -1)]
R7 = 10 * S / math.sqrt(2)      # 141.4 LDU: centre to a diagonal flat (|x| + |z| = 10)
PIN4 = [(x, 20 + z) for x in (-30, -10, 10, 30) for z in (-10, 10)]   # a 2 x 4 base's anti-studs


# ---- small geometry helpers -------------------------------------------------------------------

def cell_of(g):
    return (int(math.floor(g[0] / S)), int(math.floor(g[1] / S)))


def turn_cell(c, n):
    """Cell c after n quarter turns rot(y=90) about the axis: (x, z) -> (z, -x)."""
    i, k = c
    for _ in range(n % 4):
        i, k = k, -i - 1
    return (i, k)


def turn_cells(cells, n):
    return {turn_cell(c, n) for c in cells}


def all_turns(cells):
    return set().union(*(turn_cells(cells, n) for n in range(4)))


def place4(sub, part, color, pos, R=None, tag=""):
    """The part at pos (built for the +x side) and its three quarter turns about the axis."""
    for n in range(4):
        Rq = rot(y=90 * n)
        M = Rq if R is None else Rq @ R
        sub.place(part, color, tuple(Rq @ np.asarray(pos, float)), M, tag=tag)


def side_cells(side, outer, inner):
    """Cells of an on-grid side: the outer column (6) along |u| < outer and the inner column (5)
    along |u| < inner, for side (dx, dz)."""
    out = set()
    for col, half in ((6, outer), (5, inner)):
        for u in range(-half, half):
            i, k = (col, u) if side[0] else (u, col)
            if side[0] < 0 or side[1] < 0:
                i, k = (-col - 1, u) if side[0] else (u, -col - 1)
            out.add((i, k))
    return out


def side_floor(side):
    """The 2 x 4 plate under an on-grid side (cells 5..6 across, -2..1 along)."""
    return side_cells(side, 2, 2)


SIDE_ENDS = all_turns({(6, 2), (6, -3)})       # the two outer cells at the ends of each side


class Tables:
    """Plate, tile and brick tables cut down to what LEGO makes in a colour (in 3 or more sets,
    the latest since 2016), so packing never picks a part that doesn't exist in that colour."""

    def __init__(self, model):
        self.model = model
        self.cache = {}

    def ok(self, part, role):
        e = self.model.catalog.element(part, self.model.palette.get(role, role))
        return e is not None and e.set_count >= 3 and e.last_year >= 2016

    def __call__(self, table, role):
        key = (id(table), role)
        if key not in self.cache:
            self.cache[key] = {d: p for d, p in table.items() if self.ok(p, role) or d == (1, 1)}
        return self.cache[key]


def is_corner(g):
    return g[0] % 20 == 0 and g[1] % 20 == 0


def pin_cells(g):
    """Cells a pin covers: a round 1 x 1 plate on a stud, or a 2 x 2 jumper on a grid corner."""
    if is_corner(g):
        i, k = int(g[0] // S), int(g[1] // S)
        return rect_cells(i - 1, k - 1, 2, 2)
    return {cell_of(g)}


class Diagonals:
    """The four turned faces on the octagon's diagonal flats and their pins. Each face stands on
    smooth tiles in the floor layer and is pinned by one stud there: a round 1 x 1 plate on a
    stud of the base layer, or a 2 x 2 jumper plate (87580) whose centre stud sits on a grid
    corner, held by a stud of the base under one of its corners. The (+x, +z) face is solved;
    the others are its quarter turns, so studs stay on studs."""

    def __init__(self, items, pins, y_floor, keep_out, footprint, base_cells, reach=R7):
        def allow(g):
            cells = pin_cells(g)
            if cells & keep_out or any(min(c) < 0 for c in cells):
                return False
            if is_corner(g):        # a jumper: held by at least one stud of the base layer
                return bool(cells & base_cells)
            return cell_of(g) in base_cells

        self.base_cells = base_cells
        base = Face(turn_toward(1, 1), items, pins, reach, y_floor)
        base.solve_pin(allow)
        self.faces = [base]
        for n in (1, 2, 3):
            Rq = rot(y=90 * n)
            f = Face(base.angle, items, pins, reach, y_floor)
            f.origin, f.R = Rq @ base.origin, Rq @ base.R
            f.pin = tuple(round(float(v), 6) for v in (Rq @ [base.pin[0], 0, base.pin[1]])[[0, 2]])
            self.faces.append(f)
        self.under = cells_under([f.footprint(*footprint) for f in self.faces])
        self.pin_cells = set().union(*(pin_cells(f.pin) for f in self.faces))

    def floor(self, sub, color, y, plate_cells, *, tables, tile_color=None, extra=(),
              side_floors=True, tile_runs=()):
        """The floor layer: the pins, 2 x 4 plates under the four sides, tiles under the faces
        and plates elsewhere (`plate_cells`). `tile_runs` are cell groups each covered by one
        tile, laid first (a tile reaching past the base to close a gap beside a face)."""
        tile_color = tile_color or color
        for f in self.faces:
            part = "87580" if is_corner(f.pin) else "6141"
            sub.place(part, color, (f.pin[0], y, f.pin[1]))
        taken = set(self.pin_cells)
        for cells in tile_runs:
            if not cells & taken:
                place_rect(sub, TILES, tile_color, *rect_of(cells), y)
                taken |= cells
        for s in SIDES if side_floors else ():
            place_rect(sub, tables(PLATES, color), color, *rect_of(side_floor(s)), y)
            taken |= side_floor(s)
        for c in extra:
            place_rect(sub, PLATES, color, c[0], c[1], 1, 1, y)
            taken.add(c)
        lay(sub, tables(PLATES, color), color, plate_cells - taken - self.under, y)
        lay(sub, tables(TILES, tile_color), tile_color, (self.under & self.base_cells) - taken, y)

    def place(self, sub):
        for f in self.faces:
            f.place(sub)


def _rz(deg):
    M = np.eye(4)
    M[:3, :3] = rot(z=deg)
    return M


def _rot4(n):
    M = np.eye(4)
    M[:3, :3] = rot(y=90 * n)
    return M


# ---- the buns' curved edge -------------------------------------------------------------------

TRI_TURN = {(1, 1): 0, (1, -1): 90, (-1, -1): 180, (-1, 1): -90}   # a corner (+x, +z) -> quadrant


def curved_edge(sub, T, *, crust, y_floor, base_h, fill_role=None):
    """The edge of a bun, on a base layer (the 12-stud octagon, inset): a floor, then all round
    the 14-stud octagon a base (plates or bricks) under 2 x 2 curved slopes, so the crust curves
    in from 14 studs across to 10. The four sides sit on the stud grid, their base a 1 x 6 and a
    1 x 4 side by side; the four corners are turned faces. The middle is built up one brick high
    from the floor with `fill_role`. Returns the cells inside the edge and the y of the top of
    the curve."""
    y_base = y_floor - base_h
    table = BRICKS if base_h == 24 else PLATES
    face = [(table[(2, 4)], crust, (0, y_base, 20), None),
            ("15068", crust, (-20, y_base, 20), None),
            ("15068", crust, (20, y_base, 20), None)]
    sides = all_turns(rect_cells(5, -3, 2, 6))
    diag = Diagonals(face, PIN4, y_floor, all_turns(rect_cells(5, -2, 2, 4)), (-40, 40, 0, 40),
                     OCT6)
    interior = OCT6 - sides - diag.under

    sub.step("A floor: plates, with smooth tiles and a pin under each corner")
    diag.floor(sub, crust, y_floor, interior, tables=T)
    sub.step("The four sides of the crust curve inward")
    for n in range(4):
        Rq = rot(y=90 * n)
        sub.place(table[(1, 6)], crust, tuple(Rq @ [130, y_base, 0]), Rq @ rot(y=90))
        sub.place(table[(1, 4)], crust, tuple(Rq @ [110, y_base, 0]), Rq @ rot(y=90))
        for z in (-20, 20):
            sub.place("15068", crust, tuple(Rq @ [120, y_base, z]), Rq @ rot(y=-90))
        for z in (50, -50):
            sub.place("54200", crust, tuple(Rq @ [130, y_base, z]), Rq @ rot(y=-90))
    if fill_role:
        sub.step("Build up the middle")
        lay(sub, T(BRICKS, fill_role), fill_role, interior, y_floor - 24, along="z")
    sub.step("The four corners, turned to the diagonals, each on its pin")
    diag.place(sub)
    return interior, y_base - 16


# ---- 1 · bottom bun ---------------------------------------------------------------------------

def bottom_bun(model):
    """Golden crust underneath and round the side, curving in at the top round a pale cut face
    (40 LDU)."""
    sub = model.submodel("bottom_bun", "Bottom bun")
    T = Tables(model)
    sub.step("The base: four wedge plates make a 12-stud octagon")
    octagon6(sub, "crust", -8)
    interior, y_top = curved_edge(sub, T, crust="crust", y_floor=-16, base_h=8)
    sub.step("Build up the middle")
    rects_a, rects_b = bonded_pair(interior, T(PLATES, "crumb"), interior, T(PLATES, "crumb"))
    for r in rects_a:
        place_rect(sub, T(PLATES, "crumb"), "crumb", *r, y_top + 16)
    for r in rects_b:
        place_rect(sub, T(PLATES, "crumb"), "crumb", *r, y_top + 8)
    sub.step("The cut face: pale crumb, studs in the middle")
    sub.place("3031", "crumb", (0, y_top, 0))
    lay(sub, T(TILES, "crumb"), "crumb", interior - CENTER, y_top)
    return sub


# ---- 2 · patty ----------------------------------------------------------------------------------

def patty(model):
    """Seared beef, 32 LDU: an octagon of reddish brown with dark brown edges and grill marks.
    Its top edge dips under each of the cheese's four drooping tips."""
    sub = model.submodel("patty", "Patty")
    T = Tables(model)
    y_floor, y_mid, y_top = -16, -24, -32
    face = [("3020", "patty", (0, y_mid, 20), None),
            ("2431", "char", (0, y_top, 10), None),
            ("2431", "patty", (0, y_top, 30), None)]
    sides = all_turns(rect_cells(5, -3, 2, 6))
    diag = Diagonals(face, PIN4, y_floor, sides, (-40, 40, 0, 40), OCT7)
    interior = OCT7 - sides - diag.under

    sub.step("The base: a 14-stud octagon")
    octagon7(sub, "patty", -8)
    sub.step("A floor of plates, with smooth tiles and a pin under each corner")
    diag.floor(sub, "patty", y_floor, interior, tables=T, side_floors=False)
    sub.step("The rounded edge on the four sides, low where the cheese droops over it")
    for n in range(4):
        Rq = rot(y=90 * n)
        for z in (-20, 20):
            sub.place("15068", "patty", tuple(Rq @ [120, -8, z]), Rq @ rot(y=-90))
        for z in (50, -50):
            sub.place("54200", "char", tuple(Rq @ [130, -8, z]), Rq @ rot(y=-90))
    sub.step("Build up the middle")
    lay(sub, T(PLATES, "patty"), "patty", interior, y_mid, along="z")
    sub.step("The seared corners, turned to the diagonals, each on its pin")
    diag.place(sub)
    sub.step("The top: grill marks across the meat, studs in the middle")
    sub.place("3031", "patty", (0, y_top, 0))
    top = interior - CENTER
    marks = {c for c in top if c[1] in (-5, 4) or c[0] in (-5, 4)}
    lay(sub, T(TILES, "char"), "char", marks, y_top)
    lay(sub, T(TILES, "patty"), "patty", top - marks, y_top)
    return sub


# ---- 3 · cheese ---------------------------------------------------------------------------------

DROOP = 30.0          # degrees the cheese's tips hang down


def cheese(model):
    """A square slice laid diamond-wise, its four tips clipped on and hanging down (16 LDU).
    The diamond: |x| + |z| <= 8 studs. Each tip is a little flap on two bar-and-clip hinges along
    a line 5.5 studs out; the slice beyond 6 studs is the flap."""
    sub = model.submodel("cheese", "Cheese")
    T = Tables(model)
    yA, yB = -8, -16
    quad = {(a, b) for a in range(7) for b in range(7) if a + b <= 6}
    whole = set()
    for sx, sz in QUADS:
        whole |= {(a if sx > 0 else -a - 1, b if sz > 0 else -b - 1) for a, b in quad}
    hinge = all_turns({(3, -1), (4, -1), (3, 0), (4, 0)})
    knuckle = all_turns({(5, -1), (5, 0)})
    flap = all_turns({(6, -1), (6, 0)})
    tri = set()
    for sx, sz in QUADS:
        for a, b in ((4, 2), (2, 4)):
            tri.add((a if sx > 0 else -a - 1, b if sz > 0 else -b - 1))
    main = whole - hinge - knuckle - flap

    # tiles that tie each pair of hinge plates into the slice: 1 x 3 along the tip, from the
    # slice's own plates across both hinge plates
    ties = [turn_cells({(2 + d, k) for d in range(3)}, n) for n in range(4) for k in (-1, 0)]
    tile_cells = (main | hinge) - CENTER - tri - set().union(*ties)
    rects_a, rects_b = bonded_pair(main, T(PLATES, "cheese"), tile_cells, T(TILES, "cheese"),
                                   fixed_a=[turn_cells(hinge & {(3, -1), (4, -1)}, n)
                                            for n in range(4)] +
                                           [turn_cells(hinge & {(3, 0), (4, 0)}, n)
                                            for n in range(4)],
                                   fixed_b=ties + [CENTER] + [{c} for c in tri])

    sub.step("Lay out the slice")
    for r in rects_a:
        place_rect(sub, T(PLATES, "cheese"), "cheese", *r, yA)
    sub.step("Four pairs of plates with handles pointing to the tips")
    for z in (-10, 10):
        place4(sub, "60478", "cheese", (80, yA, z))
    sub.step("Tile the slice smooth, studs in the middle")
    sub.place("3031", "cheese", (0, yB, 0))
    for sx, sz in QUADS:
        for a, b in ((4, 2), (2, 4)):
            x, z = sx * (a + 1) * S, sz * (b + 1) * S
            turn = {(1, 1): 0, (1, -1): 90, (-1, -1): 180, (-1, 1): -90}[(sx, sz)]
            sub.place("35787", "cheese", (x, yB, z), rot(y=turn) if turn else None)
    for cells in ties:
        place_rect(sub, T(TILES, "cheese"), "cheese", *rect_of(cells), yB)
    for r in rects_b:
        place_rect(sub, T(TILES, "cheese"), "cheese", *r, yB)

    tip = model.submodel("cheese_tip", "Cheese tip")
    tip.step("A clip plate and a plate, joined by two triangle tiles")
    tip.place("60470b", "cheese", (130, yA, 0), rot(y=90))
    tip.place("3023b", "cheese", (150, yA, 0), rot(y=90))
    tip.place("35787", "cheese", (140, yB, 20))
    tip.place("35787", "cheese", (140, yB, -20), rot(y=90))
    hinge_at = np.array([110.0, yA + 2.0, 0.0])
    droop = translate(*hinge_at) @ _rz(DROOP) @ translate(*-hinge_at)
    sub.step("Clip on the four tips and let them hang")
    for n in range(4):
        M = _rot4(n) @ droop
        push = tuple(float(v) for v in np.round(M[:3, :3] @ [1.0, 0, 0], 6))   # the way out
        sub.use(tip, tuple(M[:3, 3]), M[:3, :3], tag=f"tip_{n}", insert=push)
    return sub


# ---- 4 · lettuce --------------------------------------------------------------------------------

ROSETTES = [(6, 2), (6, -2), (4, 4)]      # 2 x 2 leaf rosettes, centred on grid corners (studs)
def lettuce(model):
    """A ruffled leaf: a green octagon with a ring of leafy rosettes whose leaves curl down over
    its edge (32 LDU). The rosettes stand on 2 x 2 plates so their leaves clear the base."""
    sub = model.submodel("lettuce", "Lettuce")
    T = Tables(model)
    centres = []
    for n in range(4):
        for cx, cz in ROSETTES:
            p = rot(y=90 * n)[:3, :3] @ np.array([cx * S, 0, cz * S])
            centres.append((int(round(p[0])), int(round(p[2]))))
    rosette_cells = set().union(*(rect_cells(x // S - 1, z // S - 1, 2, 2) for x, z in centres))
    near = set()
    for i, k in rosette_cells:
        near |= rect_cells(i - 1, k - 1, 3, 3)
    inner = OCT7 - near - all_turns(rect_cells(5, -1, 2, 2))

    sub.step("The leaf: an octagon, cut back between the ruffles on the four sides")
    octagon7(sub, "lettuce", -8, arms="3020", center="3022")
    sub.step("A plate under each ruffle, and the middle built up")
    for x, z in centres:
        sub.place("3022", "lettuce", (x, -16, z))
    lay(sub, T(PLATES, "lettuce"), "lettuce", inner, -16)
    sub.step("Ruffles: leafy rosettes all round the edge")
    for x, z in centres:
        sub.place("15469", "leaf", (x, -32, z))
    sub.step("Build up the middle")
    lay(sub, T(PLATES, "lettuce"), "lettuce", inner, -24, along="z")
    sub.step("Tiles, and studs in the middle")
    sub.place("3031", "lettuce", (0, -32, 0))
    lay(sub, T(TILES, "lettuce"), "lettuce", inner - CENTER, -32)
    return sub


# ---- 5 · tomato ---------------------------------------------------------------------------------

SLICES = [(-3, -3), (3, 3)]          # slice centres (grid corners, studs)


def tomato(model):
    """Two round slices, red outside and paler inside (16 LDU), joined by the stud plate."""
    sub = model.submodel("tomato", "Tomato")
    T = Tables(model)
    sub.step("Two round slices, four quarter plates each")
    for cx, cz in SLICES:
        for sx, sz in QUADS:
            sub.place("30565", "tomato", ((cx + 2 * sx) * S, -8, (cz + 2 * sz) * S),
                      rot(y=CUT_TURN[(sx, sz)]))
    sub.step("The studs in the middle join the slices")
    sub.place("3031", "tomato", (0, -16, 0))
    sub.step("Skin, flesh and the pale middle")
    for cx, cz in SLICES:
        C = np.array([cx * S, -16, cz * S])
        inward = (-1 if cx > 0 else 1, -1 if cz > 0 else 1)
        sub.place("14769", "pulp", tuple(C))
        for q in QUADS:
            if q == inward:
                continue
            R = rot(y=CUT_TURN[q])
            sub.place("27507", "tomato", tuple(C), R)
            sub.place("79393", "tomato", tuple(C), R)
            sub.place("27925", "pulp", tuple(C + R @ [10, 0, -10]), R)
        cells = set()
        for i in range(cx - 4, cx + 4):
            for k in range(cz - 4, cz + 4):
                corners = [(i, k), (i + 1, k), (i, k + 1), (i + 1, k + 1)]
                inside = all(math.hypot(a - cx, b - cz) <= 4.01 for a, b in corners)
                in_quarter = ((i < cx) == (inward[0] < 0)) and ((k < cz) == (inward[1] < 0))
                centre_tile = abs(i + .5 - cx) < 1 and abs(k + .5 - cz) < 1
                if inside and in_quarter and (i, k) not in CENTER and not centre_tile:
                    cells.add((i, k))
        lay(sub, T(TILES, "tomato"), "tomato", cells, -16)
    return sub


# ---- 6 · top bun --------------------------------------------------------------------------------

# The 24 studs of a 6 x 6 round plate (11213): the core under the crown.
DISC = {(i, k) for i in range(-3, 3) for k in range(-3, 3) if math.hypot(i + .5, k + .5) < 2.6}
R5, R3 = 5 * S, 3 * S           # the ring's and the crown's outer flats: 10 and 6 studs across

# Sesame seeds are white 1 x 1 tiles in three shapes: quarter-round (25269, a teardrop),
# half-round (24246) and round (98138), written (part, degrees turned). They thin out from the
# crown to the rim. Sides are numbered 0..3 from +x by quarter turns (+x, -z, -x, +z); corners
# 0..3 from (+x, +z) the same way. A lane is one stud of a side or corner, by its place along it.
#
# The rim's slope, 5.5 studs out: {side or corner: (stud along it, seed)}.
SLOPE_SEEDS = {"side": {0: (30, ("25269", 180)), 3: (30, ("98138", 0)), 2: (30, ("24246", 90))},
               "corner": {3: (10, ("25269", 90)), 1: (10, ("25269", 0))}}
# The ring, 3.5 studs out: {side or corner: {lane: seed}}; the seed lies at the top of its lane.
RING_SEEDS = {"side": {3: {10: ("24246", 0)}, 2: {-10: ("25269", 0)}},
              "corner": {0: {-20: ("98138", 0)}, 2: {0: ("25269", 270)}, 1: {-20: ("24246", 180)}}}
# The ring's eight gaps, 4.75 studs out, between each slope on the grid and the turned corner
# beside it: (sign of x, sign of z, the axis of the side it lies beside, the seed part or None).
GAPS = [(1, 1, "x", None), (1, 1, "z", "25269"), (-1, 1, "z", None), (-1, 1, "x", None),
        (-1, -1, "x", None), (-1, -1, "z", "98138"), (1, -1, "z", None), (1, -1, "x", "24246")]
# The crown, 1.5 studs out: {side: {lane: seed}}; "jumper": the top of that lane is under one of
# the middle's jumper plates instead.
CROWN_SEEDS = {0: {-10: ("25269", 180)}, 1: {-10: ("98138", 0)}, 3: {-10: "jumper"}}
# The crown's middle, on the 4 x 4 plate: 1 x 2 jumper plates (x, z of the stud, degrees) whose
# seeds stand a plate proud, half a stud off the grid and turned any way; and seeds set flush.
CROWN_JUMPERS = [(0, -10, 0, ("25269", 25)), (10, 20, 90, ("24246", 200))]
CROWN_FLUSH = [(-10, 10, ("25269", 90))]


def studs_under(face, x0, x1, z0, z1, grow=7.0):
    """Cells whose stud would stand under a face's local rectangle (so they need a tile)."""
    out = set()
    for i in range(-8, 8):
        for k in range(-8, 8):
            lx, _, lz = face.R.T @ (np.array([(i + .5) * S, 0, (k + .5) * S]) - face.origin)
            if x0 - grow < lx < x1 + grow and z0 - grow < lz < z1 + grow:
                out.add((i, k))
    return out


def aim(dx, dz):
    """Rotation that points a quarter tile's round corner (25269: local +x, -z) at (dx, dz)."""
    return rot(y=turn_toward(dx, dz) + 45)


def seed_item(seed, pos):
    return (seed[0], "seed", pos, rot(y=seed[1]) if seed[1] else None)


def slope_row(crust, y, z, seed=None):
    """The rim's inner row, four studs of 30 degree slope facing -z in a face's frame (x along
    it), on a surface at y: two 1 x 2 slopes, or with a seed (stud, seed) a 1 x 1 slope and the
    seed on the bare stud beside it, level with the middle of the slope."""
    items = []
    for half in (-20, 20):
        if seed and abs(seed[0] - half) == 10:
            items.append(("54200", crust, (2 * half - seed[0], y, z), None))
            items.append(seed_item(seed[1], (seed[0], y - 8, z)))
        else:
            items.append(("85984", crust, (half, y, z), None))
    return items


def curved_band(crust, y, lanes, seeds=None, inner=True):
    """Two studs of curved slope facing -z in a face's frame, over the given lanes (studs along
    x), low end on a surface at y in the outer row (z = 10), high end on a plate one higher in
    the inner row (z = 30), where a curved slope's underside is cut back by a plate. A lane with
    a seed gets a 1 x 1 slope outside and the seed on the inner plate's stud, level with the
    top; with "jumper", just the 1 x 1 slope. `inner` adds that plate (a 1 x 2 or 1 x 3)."""
    seeds = seeds or {}
    items = []
    if inner:
        part = {2: "3023", 3: "3623"}[len(lanes)]
        items.append((part, crust, (sum(lanes) / len(lanes), y - 8, 30), None))
    if len(lanes) == 2 and not seeds:
        return items + [("15068", crust, (sum(lanes) / 2, y, 20), None)]
    for x in lanes:
        seed = seeds.get(x)
        if seed is None:
            items.append(("11477", crust, (x, y, 20), None))
            continue
        items.append(("54200", crust, (x, y, 10), None))
        if seed != "jumper":
            items.append(seed_item(seed, (x, y - 16, 30)))
    return items


def place_side(sub, items, n, reach):
    """Items given in a face's frame (x along it, -z outward, its outer edge `reach` from the
    axis), placed square to the grid on side n (0: +x, then by quarter turns)."""
    Rq = rot(y=90 * n) @ rot(y=-90)
    for part, role, (x, y, z), lrot in items:
        sub.place(part, role, tuple(Rq @ [x, y, z - reach]), Rq if lrot is None else Rq @ lrot)


def place_items(sub, face, items):
    """Some of a turned face's items (kit.Face), in its frame."""
    for part, role, local, lrot in items:
        sub.place(part, role, tuple(face.world(local)), face.R if lrot is None else face.R @ lrot)


def top_bun(model):
    """A golden dome with white sesame seeds over a pale cut face (96 LDU, the seeds to 104).
    From the rim in: a plate's worth of upright edge that turns over in a quarter-round brick, a
    30 degree slope, a ring of curved slopes, and a crown of curved slopes round a 4 x 4 plate
    with quarter-circle corners (5852). Rim, slope and ring are eight flats each, four on the
    stud grid and four turned to the diagonals; the crown is square to the grid."""
    sub = model.submodel("top_bun", "Top bun")
    T = Tables(model)
    crust = "crust"
    y_floor, y1, y3 = -16, -24, -48                 # floor; the rim's plate; the rim's top
    y_fill, y_mid, y_deck = -40, -48, -56           # the middle: bricks, plates, the deck
    y_ring, y_crown, y_plate, y_top = -64, -80, -88, -96
    # y_ring: where the ring's slopes stand (the top of the rim's slope); y_crown: the top of
    # the ring and of the round plate the crown's slopes stand on; y_plate: the 4 x 4 plate

    # the rim's four turned corners: a 2 x 4 plate, quarter-round bricks in front, a brick and
    # the slope behind
    def corner(seed=None):
        return [("3020", crust, (0, y1, 20), None), ("3010", crust, (0, y3, 30), None),
                ("37352", crust, (-20, y3, 10), None), ("37352", crust, (20, y3, 10), None),
                *slope_row(crust, y3, 30, seed)]
    sides = all_turns(rect_cells(5, -3, 2, 6))
    rim = Diagonals(corner(), PIN4, y_floor, all_turns(rect_cells(5, -2, 2, 4)),
                    (-40, 40, 0, 40), OCT6)
    for n, seed in SLOPE_SEEDS["corner"].items():
        rim.faces[n].items = corner(seed)
    interior = OCT6 - sides - rim.under

    # the ring's four turned corners: a 2 x 3 plate, a 1 x 3 plate on its inner row and three
    # curved slopes across both, pinned by the middle of the inner row on the diagonal's stud
    def ring_corner(seeds=None):
        return [("3021", crust, (0, y_ring, 20), None),
                *curved_band(crust, y_ring, (-20, 0, 20), seeds)]
    ring = Diagonals(ring_corner(), [(x, z) for x in (-20, 0, 20) for z in (10, 30)], y_deck,
                     DISC | all_turns(rect_cells(3, -1, 2, 2)), (-30, 30, 0, 40), interior,
                     reach=R5)
    for n, seeds in RING_SEEDS["corner"].items():
        ring.faces[n].items = ring_corner(seeds)
    smooth = set().union(*(studs_under(f, -30, 30, 0, 40) for f in ring.faces)) & interior
    pins = {cell_of(f.pin) for f in ring.faces}

    sub.step("The cut face underneath: four wedge plates of pale crumb")
    octagon6(sub, "crumb", -8)
    sub.step("A floor: plates, with smooth tiles and a pin under each corner")
    # beside each corner, between it and the side, a narrow gap is left open: a 1 x 2 tile
    # reaches out under it so the pale cut face doesn't show through from above
    gaps = all_turns({(5, 2), (2, 5)})
    runs = [{c, (c[0] - (c[0] > 3) + (c[0] < -4), c[1] - (c[1] > 3) + (c[1] < -4))} for c in gaps]
    rim.floor(sub, crust, y_floor, interior, tables=T, tile_runs=runs, side_floors=False)
    # the floor stops a stud short of the rim on the four sides, as it does under the corners,
    # so the bun's edge tucks in underneath all the way round
    lay(sub, T(PLATES, crust), crust, all_turns(rect_cells(5, -2, 1, 4)), y_floor)
    sub.step("A plate under each of the four sides, reaching a stud past the floor")
    for n in range(4):
        place_side(sub, [("3020", crust, (0, y1, 20), None)], n, 7 * S)
    sub.step("The four sides: quarter-round bricks outside, a brick and the slope inside")
    for n in range(4):
        side = [("37352", crust, (x, y3, 10), None) for x in (-40, 0, 40)] + \
               [("3010", crust, (0, y3, 30), None)] + \
               slope_row(crust, y3, 30, SLOPE_SEEDS["side"].get(n))
        place_side(sub, side, n, 7 * S)
    sub.step("A 1 x 1 plate under each end of the four sides, pressed on from below")
    for n in range(4):
        place_side(sub, [("3024", crust, (x, y1, 10), None) for x in (-50, 50)], n, 7 * S)
    sub.step("Build up the middle: bricks")
    lay(sub, T(BRICKS, crust), crust, interior, y_fill, along="z")
    sub.step("The four corners of the rim, turned to the diagonals, each on its pin")
    rim.place(sub)
    sub.step("A layer of plates across the middle")
    lay(sub, T(PLATES, crust), crust, interior, y_mid, along="x")
    sub.step("The deck: plates, with smooth tiles and a pin where the ring's corners will sit")
    for f in ring.faces:
        sub.place("6141", crust, (f.pin[0], y_deck, f.pin[1]))
    lay(sub, T(PLATES, crust), crust, interior - smooth - pins, y_deck, along="z")
    lay(sub, T(TILES, crust), crust, smooth - pins, y_deck)

    sub.step("The crown's core: two layers of plates, a round plate and a 4 x 4 plate")
    lay(sub, T(PLATES, crust), crust, DISC, y_ring, along="x")
    lay(sub, T(PLATES, crust), crust, DISC, y_ring - 8, along="z")
    sub.place("11213", crust, (0, y_crown, 0))
    sub.place("3031", crust, (0, y_plate, 0))
    # the ring's plates go on before its slopes (two steps), so every plate can still be
    # pushed down when its turn comes
    arms = [[("3022", crust, (0, y_ring, 20), None)] +
            curved_band(crust, y_ring, (-10, 10), RING_SEEDS["side"].get(n)) for n in range(4)]
    sub.step("The ring's plates: on each side a 2 x 2 with a 1 x 2 on its inner half")
    for n in range(4):
        place_side(sub, arms[n][:2], n, R5)
    sub.step("The ring's corners, turned to the diagonals, each on its pin: "
             "a 2 x 3 plate with a 1 x 3 on its inner row")
    for f in ring.faces:
        place_items(sub, f, f.items[:2])
    sub.step("The ring: curved slopes on each side, their high ends on the upper plate")
    for n in range(4):
        place_side(sub, arms[n][2:], n, R5)
    sub.step("Curved slopes on the ring's four corners")
    for f in ring.faces:
        place_items(sub, f, f.items[2:])
    sub.step("A round plate and a tile in each gap of the ring")
    for sx, sz, along, seed in GAPS:
        x, z = (sx * 90, sz * 30) if along == "x" else (sx * 30, sz * 90)
        # a quarter tile's square corner goes at the rim beside the slope, its round one into
        # the gap; a half-round seed points up the dome
        gap = (-sx, sz) if along == "x" else (sx, -sz)
        up = (-sx, 0) if along == "x" else (0, -sz)
        R = {"24246": rot(y=turn_toward(*up)), "98138": None}.get(seed, aim(*gap))
        sub.place("6141", crust, (x, y_ring, z))
        sub.place(seed or "25269", "seed" if seed else crust, (x, y_ring - 8, z), R)

    sub.step("The crown: curved slopes round the 4 x 4 plate, quarter circles on its corners")
    for n in range(4):
        place_side(sub, curved_band(crust, y_crown, (-10, 10), CROWN_SEEDS.get(n), inner=False),
                   n, R3)
    for q in QUADS:
        sub.place("5852", crust, (q[0] * 40, y_crown, q[1] * 40), rot(y=CUT_TURN[q]))
    sub.step("The middle of the crown: jumper plates and sesame seeds")
    for x, z, turn, seed in CROWN_JUMPERS:
        sub.place("15573", crust, (x, y_top, z), rot(y=turn) if turn else None)
    for x, z, seed in CROWN_FLUSH:
        sub.place(seed[0], "seed", (x, y_top, z), rot(y=seed[1]) if seed[1] else None)
    for x, z, turn, seed in CROWN_JUMPERS:
        sub.place(seed[0], "seed", (x, y_top - 8, z), rot(y=seed[1]) if seed[1] else None)
    return sub


def split_steps(sub, limit=8):
    """Split every step of more than `limit` parts into consecutive steps of at most `limit`,
    in the order the parts were placed, numbering the captions (1/3), (2/3) ..."""
    by_step = {}
    for it in sub.items:
        by_step.setdefault(it.step, []).append(it)
    captions, new_step = [], 0
    for s_old in range(sub.n_steps):
        group = by_step.get(s_old, [])
        caption = sub.captions[s_old]
        chunks = [group[i:i + limit] for i in range(0, len(group), limit)] or [[]]
        for n, chunk in enumerate(chunks):
            for it in chunk:
                it.step = new_step
            captions.append(caption if len(chunks) == 1 or not caption
                            else f"{caption} ({n + 1}/{len(chunks)})")
            new_step += 1
    sub.captions = captions


LAYERS = [("bottom_bun", bottom_bun, 40), ("patty", patty, 32), ("cheese", cheese, 16),
          ("lettuce", lettuce, 32), ("tomato", tomato, 16), ("top_bun", top_bun, 104)]


def build(model):
    height = 0
    for n, (name, maker, h) in enumerate(LAYERS):
        sub = maker(model)
        model.main.step("Set the bottom bun on the table" if n == 0
                        else f"Click on the {name.replace('_', ' ')}")
        model.main.use(sub, (0, -height, 0), tag=name)
        if n:
            model.moving_group(name, name, lifts_off=True)
        height += h
    model.pose = lambda t: {name: translate(0, -n * 90 * t, 0)
                            for n, (name, _, _) in enumerate(LAYERS) if n}
    for sub in model.submodels.values():
        if sub is not model.main:
            split_steps(sub)
