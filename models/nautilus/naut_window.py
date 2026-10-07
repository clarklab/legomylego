"""A salon window: the clear bubble in its raised boss, a brass ring round it and eight yellow
lights; the boss is open behind the bubble, so the salon shows through it.

The boss is built flat, studs out (a sub-assembly of plates in layers, like the hull's shells),
and pushed onto bricks with side studs on the side keels' inner ring (two rows, above and under
the side keels). Window frame (u along the hull, v down, both from the bubble's middle; w = |z|
outward; layer n spans w Z - 14 + 8 n .. + 8, Z = the bubble rim's middle plane):

  n 0   the boss's first layer, on the side studs; a 6 x 6 opening for the bubble's rim
  n 1   the two click hinges (44567) under the opening hold the bubble's fingers
  n 2   (the hinges' fingers need a notch under the opening in layers 1 and 2)
  n 3   the frame: four plates with quarter-round cutouts round a hole the bubble's size
  n 4   the brass ring round the bubble: four Pearl Gold macaroni tiles (a ring 1 stud wide
        just outside the hole); quarter-round tiles, tiles; yellow round plates for the lights
  n 5   trans-yellow caps on them

The bubble (50747, 6 x 6 half sphere) clips onto the hinges' fingers by its own two pairs of
fingers; only its dome shows through the frame's round hole."""
from __future__ import annotations

import numpy as np

import naut_shape as shp
from brickkit.ldraw.matrix import rot, transform
from naut_kit import (AV, PLATE, S, TILE, Batch, bbox, canon, connected, connectors, ids_of,
                      pack, rect_part, side_R)

Z = shp.WINDOW_Z
CX, CY = shp.SALON_C
BOSS_V = (-6, 6)               # the boss's rows of cells (v -120 .. 120)
LIGHTS_1 = ((-50, -90), (50, -90), (-50, 90), (50, 90), (-10, 90), (10, 90))   # 1 x 1
LIGHTS_2 = ((-100, 0), (100, 0))                                                 # 2 x 2
HINGES = (-20.0, 20.0)        # u of the bubble's two pairs of fingers (v = 70)
BRICK_U = (-110, -90, 90, 110)                # side-stud bricks on the side keels (u)
BRICK_V = (-10, 30)                           # their studs' rows (v): y -22 and 18


def cell(a: int, b: int) -> tuple[float, float]:
    return S * a + S / 2, S * b + S / 2


def outline() -> set:
    """The boss: a rectangle filling the gap in the side panels round the window (the panels
    over and under the side keels stop at naut_shape.BOSS_X), from the seam over it to the
    lower panel under it."""
    return {(a, b) for b in range(BOSS_V[0], BOSS_V[1]) for a in range(-7, 7)}


def opening() -> set:
    return {(a, b) for a in range(-3, 3) for b in range(-3, 3)}


def notch() -> set:
    return {(a, 3) for a in range(-2, 2)}


def square8() -> set:
    return {(a, b) for a in range(-4, 4) for b in range(-4, 4)}


def frame_studs() -> set:
    """The cells of the 8 x 8 frame (four plates with a quarter-round cutout) that keep a stud."""
    out = set()
    for a, b in square8():
        u, v = cell(a, b)
        if abs(u) == 70 or abs(v) == 70 or (abs(u) == 50 and abs(v) == 50):
            out.add((a, b))
    return out


def w_top(n: int) -> float:
    """|z| of layer n's outer face."""
    return Z - 14 + 8 * n + 8


def boss_frame(side: int) -> np.ndarray:
    return transform((CX, CY, side * (Z - 14)), side_R(side))


def at(side: int, u: float, v: float, w: float) -> np.ndarray:
    return np.array([CX + u, CY + v, side * w], float)


def turned(part: str, R0: np.ndarray, pos, local_pt, target) -> np.ndarray:
    """R0 turned about the part's own up axis (local Y) so that its local point local_pt
    lands nearest to target (world)."""
    best = None
    for k in range(4):
        R = R0 @ rot(y=90 * k)
        d = np.linalg.norm(np.asarray(pos) + R @ np.asarray(local_pt, float) - np.asarray(target))
        if best is None or d < best[0]:
            best = (d, R)
    return best[1]


def _rects(layers: list[set], sizes) -> list[list]:
    """Plates for the boss's layers (bottom first), each packed to join the pieces under it;
    tries a few layouts until they hold together."""
    best = None
    for shift in range(0, 60, 3):
        out, below = [], {}
        for n, cells in enumerate(layers):
            rects = pack(cells, sizes, below, prefer="x", shift=shift + 5 * n) if cells else []
            out.append(rects)
            below = ids_of(rects, start=1000 * (n + 1))
        pieces = connected([r for r in out if r])
        if best is None or pieces < best[0]:
            best = (pieces, out)
        if pieces == 1:
            break
    return best[1]


def build_window(model, side: int):
    """The boss with its bubble and lights, as one sub-assembly (built flat). Returns (sub, M)."""
    sname = "port" if side < 0 else "stbd"
    sub = model.submodel(f"window_{sname}", f"Salon window, {sname}")
    M = boss_frame(side)
    bt = Batch(M)
    R = side_R(side)
    UP = (0, -1, 0)
    sizes = [s for s in AV.sizes(PLATE, "hull") if s[0] <= 2 and s[1] <= 8]
    box = outline()
    hole = opening()
    sq = square8()
    hinge_cells = {(a, 4) for a in (-2, -1, 0, 1)}
    layer_cells = {
        0: box - hole - notch(),
        1: box - hole - notch() - hinge_cells,
        2: box - hole - notch(),
        3: box - sq,
    }
    # plates of layers 0 .. 3 (and the hinges and the frame, below)
    order = [0, 1, 2, 3]
    rects = _rects([layer_cells[n] for n in order], sizes)
    for n, rs in zip(order, rects):
        for a0, a1, b0, b1 in rs:
            part, Rl = rect_part(PLATE, a1 - a0 + 1, b1 - b0 + 1)
            u = S * (a0 + a1 + 1) / 2
            v = S * (b0 + b1 + 1) / 2
            bt.add(part, "hull", transform(at(side, u, v, w_top(n)), R @ Rl), f"L{n}", insert=UP)
    tile_sizes = [s for s in AV.sizes(TILE, "hull") if s[1] <= 4]
    # layer 1: the bubble's hinges, their fingers on the bubble's fingers (u +-20, v 70, w Z)
    for uh in HINGES:
        p = at(side, uh, 90, w_top(1))
        Rh = turned("44567b", R, p, (0, 2, -20), at(side, uh, 70, Z))
        bt.add("44567b", "hinge", transform(p, Rh), "L1", insert=UP)
    # layer 3: the frame round the bubble: its quarter-round cutouts meet in the middle
    for su in (-1, 1):
        for sv in (-1, 1):
            p = at(side, 40 * su, 40 * sv, w_top(3))
            Rf = turned("35044", R, p, (40, 0, -40), at(side, 0, 0, w_top(3)))
            bt.add("35044", "hull", transform(p, Rf), "L3", insert=UP)
    # layer 4: the brass ring (four macaroni tiles, r 60..80, on the frame's studs), a
    # quarter-round tile in each gap between the ring and the frame's corner, tiles; the
    # lights' yellow bases; layer 5: their trans-yellow caps
    for su in (-1, 1):
        for sv in (-1, 1):
            p = at(side, 0, 0, w_top(4))
            Rm = turned("27507", R, p, (40, 0, -40), at(side, 40 * su, 40 * sv, w_top(4)))
            bt.add("27507", "trim", transform(p, Rm), "L4", insert=UP)
    light1 = {(int((u - 10) // S), int((v - 10) // S)) for u, v in LIGHTS_1}
    light2 = set()
    for u, v in LIGHTS_2:
        light2 |= {(int(u // S) + da, int(v // S) + db) for da in (-1, 0) for db in (-1, 0)}

    quarters = {c for c in sq if 80 < np.hypot(*cell(*c)) < 90}
    face = (box - sq) | {c for c in sq if np.hypot(*cell(*c)) > 95}
    plain = face - light1 - light2
    for a0, a1, b0, b1 in pack(plain, tile_sizes, prefer="x"):
        part, Rl = rect_part(TILE, a1 - a0 + 1, b1 - b0 + 1)
        u, v = S * (a0 + a1 + 1) / 2, S * (b0 + b1 + 1) / 2
        bt.add(part, "hull", transform(at(side, u, v, w_top(4)), R @ Rl), "L4", insert=UP)
    for c in quarters:
        u, v = cell(*c)
        p = at(side, u, v, w_top(4))
        # the quarter tile's round side toward the ring: its square corner outward
        Rq = turned("25269", R, p, (-10, 0, 10), at(side, u + 10 * np.sign(u),
                                                     v + 10 * np.sign(v), w_top(4)))
        bt.add("25269", "hull", transform(p, Rq), "L4", insert=UP)
    for u, v in LIGHTS_1:
        bt.add("4073", "lamp_base", transform(at(side, u, v, w_top(4)), R), "L4", insert=UP)
        bt.add("98138", "lights", transform(at(side, u, v, w_top(5)), R), "lights",
               tag="lights", insert=UP)
    for u, v in LIGHTS_2:          # a yellow 2 x 2 jumper, a trans-yellow dish on its stud
        bt.add("87580", "lamp_base", transform(at(side, u, v, w_top(4)), R), "L4", insert=UP)
        bt.add("4740", "lights", transform(at(side, u, v, w_top(5)), R), "lights",
               tag="lights", insert=UP)
        bt.add("98138", "lights", transform(at(side, u, v, w_top(5) + 8), R), "lights",
               tag="lights", insert=UP)
    captions = {"L0": "The window's boss, built flat: its first layer round the opening",
                "L1": "Click hinges for the bubble",
                "L3": "The frame: four plates with quarter-round cutouts",
                "L4": "Tiles and the lights' yellow bases",
                "lights": "Eight trans-yellow lights"}
    bt.emit(sub, phases=[["L0"], ["L1"], ["L2"], ["L3"], ["L4"], ["lights"]],
            captions=captions, per_step=10, reach=200)
    # the bubble, on the hinges' fingers
    sub.step("The bubble clicks onto the hinges' fingers")
    Rb = np.eye(3) if side < 0 else rot(y=180)
    pb = sub.place("50747", "glass", (0, 0, 0), tag=f"salon_{sname}", insert=(0, 0, 0))
    pb.M = np.linalg.inv(M) @ transform(at(side, 0, 70, Z), Rb)
    return sub, M


def bricks(side: int) -> list[tuple]:
    """(part, world M, hanging) of the side-stud bricks the boss is pushed onto: on the side keels'
    ring (over them) and hanging under them."""
    out = []
    for u in BRICK_U:
        for v in BRICK_V:
            y_stud = CY + v
            top = y_stud - 10                 # the brick's top (its side stud 10 below it)
            R = rot(y=0) if side < 0 else rot(y=180)
            pos = (CX + u, top, side * (Z - 14 - 10))
            out.append(("87087", transform(pos, R), v > 0))
    return out
