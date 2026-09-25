"""The ferret's head: a small sculpture in plate-high layers (finer than the brick-high body),
smoothed with cheese slopes and tiles, with sockets for the face details.

Coordinates as in the body: cell (i, j) = stud column/row (x = 20i, z = 20j LDU, nose at j = 0),
plate level p = height above the ground in plates. Shape parameters in millimetres."""
from __future__ import annotations

import math

import numpy as np

import ferret_sculpt as sc

STUD, PLATE = 8.0, 3.2          # mm

# (centre x, h, z), (radii x, h, z) -- unioned ellipsoids
PARTS = [
    ((0.0, 99.0, 58.0), (25.0, 20.0, 29.0)),     # cranium
    ((0.0, 96.0, 36.0), (20.0, 13.0, 16.0)),     # brow / bridge of the nose
    ((0.0, 88.0, 16.0), (15.0, 11.0, 16.0)),     # muzzle with puffy whisker pads
    ((0.0, 79.0, 24.0), (10.0, 7.0, 16.0)),      # lower jaw
    ((16.0, 90.0, 46.0), (12.5, 12.0, 16.0)),    # cheeks
    ((-16.0, 90.0, 46.0), (12.5, 12.0, 16.0)),
]

ROWS = range(0, 10)             # z cells of the head (a clear row, then the neck at row 11)
COLS = range(-5, 5)
LEVELS = range(20, 45)
SHELF_ROW, SHELF_TOP = 8, 27    # the throat shelf (part of the chest) under rows 8-10
SEAT = SHELF_TOP + 1            # the head rides on a turntable one plate above the shelf
SEAT_ROW = SHELF_ROW - 1        # from this row back, the head stays above the seat, so the
                                # jaw swings clear of the shelf when the head turns
LIFT_MM = 3.2                   # the head shape sits this much higher (the turntable plate)
TURNTABLE = ((-1, 8), SHELF_TOP)   # 2x2 turntable: lower-left cell, bottom plate
PIVOT_Z = 20.0 * (TURNTABLE[0][1] + 1)   # LDU: the head turns about x = 0, z = PIVOT_Z
TURN = 20.0                     # degrees the head is turned towards the viewer (nose to -X)
TURN_RANGE = (-15.0, 30.0)      # how far it can be posed either way (mechanism sweep)

# Eyes and ears: a round 1x1 plate with a side bar (32828), turned so the bar points out (and
# forward), carrying a 2x2 dish: a glossy eye, or a round cupped ear.
# (cell, plate level or None = on top of the head there, degrees from straight ahead, side)
EYE_LOOK, EAR_LOOK = 45.0, 55.0
EYES = [((-2, 4), 31, EYE_LOOK, -1), ((1, 4), 31, EYE_LOOK, 1)]
EARS = [((-3, 7), None, EAR_LOOK, -1), ((2, 7), None, EAR_LOOK, 1)]
NOSE = ((-1, 0), 28)            # 1x2 brick with two side studs: left cell, bottom plate
TONGUE = ((-1, 0), 25)          # 1x1 brick with a side stud under the nose: the "blep"
WHISKERS = [(-2, 1), (1, 1)]    # clip tiles on the whisker pads (on top of the head there)


def yaw_of(look: float, side: int) -> float:
    """Rotation about Y that turns the 32828's bar (+X) to point `look` degrees off straight
    ahead (-Z), out to the given side (-1 = -X, +1 = +X)."""
    return 90.0 + look if side < 0 else 90.0 - look


def dish_local():
    """Where a 2x2 dish sits on a 32828's bar, in the 32828's frame: its underside slides over
    the end of the bar and its dome faces along the bar."""
    return (26.0, 2.0, 0.0), sc.rot(z=90)


def mount_matrix(c, p0, look, side):
    from brickkit.ldraw.matrix import transform
    return transform(((c[0] + 0.5) * 20, -8 * (p0 + 1), (c[1] + 0.5) * 20),
                     sc.rot(y=yaw_of(look, side)))


def dish_cells(c, p0, look, side, pad: float = 1.5) -> set:
    """(cell, plate) touched by the dish on a bar mount (sampled, slightly padded)."""
    M = mount_matrix(c, p0, look, side)
    pts = []
    for x in np.linspace(18.0 - pad, 30.0 + pad, 5):
        for r in (0.0, 7.0, 14.0, 20.0 + pad):
            for a in np.radians(np.arange(0, 360, 15)):
                pts.append((x, 2.0 + r * math.sin(a), r * math.cos(a), 1.0))
    W = (M @ np.array(pts).T).T
    out = set()
    for X, Y, Z, _ in W:
        out.add(((int(math.floor(X / 20)), int(math.floor(Z / 20))), int(math.floor(-Y / 8))))
    return out


def dist(x, h, z):
    x, h, z = (np.asarray(v, float)[..., None] for v in (x, h, z))
    C = np.array([c for c, _ in PARTS])
    R = np.array([r for _, r in PARTS])
    d = ((x - C[:, 0]) / R[:, 0]) ** 2 + ((h - LIFT_MM - C[:, 1]) / R[:, 1]) ** 2 + \
        ((z - C[:, 2]) / R[:, 2]) ** 2
    return d.min(-1)


def centre(c, p):
    return (c[0] + 0.5) * STUD, (p + 0.5) * PLATE, (c[1] + 0.5) * STUD


def raw_layers() -> dict[int, set]:
    L = {}
    for p in LEVELS:
        cells = set()
        for i in COLS:
            for j in ROWS:
                if j >= SEAT_ROW and p < SEAT:
                    continue
                if dist(*centre((i, j), p)) <= 1.0:
                    cells.add((i, j))
        L[p] = cells
    return L


def mounts():
    """[(kind, cell, plate level, look, side)] with ear levels resolved to the head top."""
    L = raw_layers()
    out = []
    for c, p0, look, side in EYES:
        out.append(("eye", c, p0, look, side))
    for c, p0, look, side in EARS:
        top = max(p for p in L if c in L[p])
        out.append(("ear", c, top + 1 if p0 is None else p0, look, side))
    return out


def keepout() -> set:
    """(cell, plate) that must stay empty: the space taken by the dishes and the nose."""
    out = set()
    for _, c, p0, look, side in mounts():
        out |= {ck for ck in dish_cells(c, p0, look, side) if ck[0] != c}
    (i, j), p0 = NOSE
    for p in range(p0 + 1, p0 + 4):
        for di in (-1, 0, 1, 2):
            out.add(((i + di, j - 1), p))
    (i, j), p0 = TONGUE
    for p in range(p0, p0 + 4):
        out.add(((i, j - 1), p))
    return out


def layers() -> dict[int, set]:
    L = raw_layers()
    # the eye plates need something to stand on, the nose brick its own cells
    for kind, c, p0, _, _ in mounts():
        if kind == "eye":
            for p in range(p0 - 3, p0 + 1):
                L[p].add(c)
    (i, j), p0 = NOSE
    for p in range(p0, p0 + 3):
        L[p] |= {(i, j), (i + 1, j)}
    (i, j), p0 = TONGUE
    for p in range(p0, p0 + 3):
        L[p].add((i, j))
    for c, p in keepout():
        L.get(p, set()).discard(c)
    return L


def role(c, p) -> str:
    """Sable-style face: white muzzle, chin and cheeks, dark bandit mask round the eyes,
    body-coloured crown."""
    x, h, z = centre(c, p)
    h -= LIFT_MM
    if z < 20 or h < 85:
        return "face"                                # muzzle, chin, throat
    if 90 <= h <= 105 and 20 <= z <= 58:
        return "mask"                                # the bandit band across the eyes
    if h < 90 and z < 64:
        return "face"                                # white cheeks under the mask
    return "coat"


def pieces(sizes_of):
    """All head pieces (plates, caps, socket parts), unordered."""
    L = layers()
    sockets = []
    reserved = {}
    for kind, c, p0, look, side in mounts():
        pc = sc.Piece("32828", "Black" if kind == "eye" else "coat", frozenset({c}), p0, p0 + 1,
                      frozenset({c}), {p0: frozenset({c})},
                      ((c[0] + 0.5) * 20, -8 * (p0 + 1), (c[1] + 0.5) * 20),
                      sc.rot(y=yaw_of(look, side)), p0, f"{kind} socket")
        sockets.append(pc)
        reserved.setdefault(p0, set()).add(c)
    (i, j), p0 = NOSE
    cells = frozenset({(i, j), (i + 1, j)})
    sockets.append(sc.Piece("11211", "face", cells, p0, p0 + 3, cells, {p0: cells},
                            ((i + 1) * 20, -8 * (p0 + 3), (j + 0.5) * 20), None, p0,
                            "nose socket"))
    for p in range(p0, p0 + 3):
        reserved.setdefault(p, set()).update(cells)
    (i, j), p0 = TONGUE
    tc = frozenset({(i, j)})
    sockets.append(sc.Piece("87087", "face", tc, p0, p0 + 3, tc, {p0: tc},
                            ((i + 0.5) * 20, -8 * (p0 + 3), (j + 0.5) * 20), None, p0,
                            "tongue socket"))
    for p in range(p0, p0 + 3):
        reserved.setdefault(p, set()).add((i, j))
    # the turntable top the head rides on (it nests in the base on the throat shelf)
    (i, j), p0 = TURNTABLE
    tt = frozenset(sc.rect(i, j, 2, 2))
    sockets.append(sc.Piece("3679", "Light Bluish Gray", tt, p0, p0 + 1, tt, {},
                            (20.0 * (i + 1), -8 * (p0 + 1), 20.0 * (j + 1)), None, p0,
                            "turntable top"))
    for c in WHISKERS:
        top = max(p for p in L if c in L[p])
        cc = frozenset({c})
        sockets.append(sc.Piece("15712", "face", cc, top + 1, top + 2, frozenset(),
                                {top + 1: cc}, ((c[0] + 0.5) * 20, -8 * (top + 2), (c[1] + 0.5) * 20),
                                sc.rot(y=90), top + 1, "whisker clip"))
        reserved.setdefault(top + 1, set()).add(c)

    ps = sorted(p for p in L if L[p])
    layer_list = []
    for p in ps:
        cells = L[p] - reserved.get(p, set())
        if cells:
            layer_list.append((p, cells, {c: role(c, p) for c in cells},
                               "z" if p % 2 == 0 else "x"))
    packed, n = sc.pack_section(layer_list, sizes_of, height=1)
    caps = []
    ko = keepout()
    for p in ps:
        top = L[p] - L.get(p + 1, set())
        for c in sorted(top):
            if (c, p + 1) in ko or c in reserved.get(p + 1, set()):
                continue
            x, h, z = centre(c, p + 1)
            e = 1.5
            gx = dist(x + e, h, z) - dist(x - e, h, z)
            gz = dist(x, h, z + e) - dist(x, h, z - e)
            d = (1 if gx > 0 else -1, 0) if abs(gx) >= abs(gz) else (0, 1 if gz > 0 else -1)
            inward = (c[0] - d[0], c[1] - d[1])
            wall = sum(1 for q in (p + 1, p + 2) if inward in L.get(q, set()))
            free2 = c not in L.get(p + 2, set()) and (c, p + 2) not in ko
            r = role(c, p)
            if wall == 2 and free2:
                caps.append(sc.Piece("54200", r, frozenset({c}), p + 1, p + 3, frozenset(),
                                     {p + 1: frozenset({c})},
                                     ((c[0] + 0.5) * 20, -8 * (p + 1), (c[1] + 0.5) * 20),
                                     sc.FACING[d], p + 1, "cap"))
            else:
                t = sc.tile({c}, p + 2, r, p + 1)
                t.note = "cap"
                caps.append(t)
    return packed + sockets + caps, n, L
