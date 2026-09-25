"""Core of the Baby Metroid: base disc, fangs, tap mechanism.

Frame: LDraw units, -Y up, dome rim at y = 0; the base disc spans y 56..72. The model is built
in its RESTING state: the body up, fangs open.

Tap lamp: the whole body slides down the stand's fixed centre axle. A clear tube hangs under
the body (it belongs to the stand, see stand.py) and presses the battery box's green on/off
button, a push-on/push-off switch inside a real LEGO element. Rubber belts in the stand push
the tube, and with it the body, back up.

Fangs (+X fang shown; the others are quarter turns of it):
  pivot   P = (120, 106): a short axle along Z in two Technic bricks hanging under the disc
  fang    white bent beam locked on the axle, tip bending inward, tooth at the tip
  lever   thin 1x3 on the axle pointing inward: pin hole L
  link    thick 1x5 (round holes, 80 LDU) from L up through the disc to the hub pin H
  hub     FIXED on top of the stand's centre axle, above the disc
Pushing the body down moves the levers down past the fixed hub pins, which turns all four
fangs shut together; the belts bring it back and the fangs open again."""
from __future__ import annotations

import math

import numpy as np

from brickkit.ldraw.matrix import rot, transform, translate
from brickkit.shapes.rings import ring_cells
from brickkit.shapes.shell import pack_cells, _place_run

DISC_R = 10.0
DISC_TOP = 56
DISC_BOTTOM = 72
P = np.array([120.0, 106.0])     # pivot (x, y)
LEVER = 20.0                     # inward
LINK = 80.0
H_Y = 26.0                       # hub pin height relative to the body with the fangs shut
REST_DROP = 16.0                 # at rest the hub pins sit this much lower (fangs open)
H_REST = H_Y + REST_DROP         # 42: hub pin height, fixed in the world
PRESS = 10.5                     # tap stroke: the box's button bottoms out here
QUARTERS = [0, -90, 180, 90]     # +X, +Z, -X, -Z

ALONG_Z = rot(y=90)                                                    # local X -> Z
ALONG_Y = rot(z=90)                                                    # local X -> Y
HANG = np.array([[-1, 0, 0], [0, 0, 1], [0, 1, 0]], float).T          # local z->+Y, y->+Z
INWARD = np.array([[0, -1, 0], [0, 0, 1], [-1, 0, 0]], float).T       # local z->-X, y->+Z


def quarter(k: int) -> np.ndarray:
    return transform((0, 0, 0), rot(y=QUARTERS[k]))


def about_axis(axis, deg: float, point=(0, 0, 0)) -> np.ndarray:
    x, y, z = np.asarray(axis, float) / np.linalg.norm(axis)
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    R = np.array([[c + x * x * (1 - c), x * y * (1 - c) - z * s, x * z * (1 - c) + y * s],
                  [y * x * (1 - c) + z * s, c + y * y * (1 - c), y * z * (1 - c) - x * s],
                  [z * x * (1 - c) - y * s, z * y * (1 - c) + x * s, c + z * z * (1 - c)]])
    M = np.eye(4)
    M[:3, :3] = R
    p = np.asarray(point, float)
    return translate(*p) @ M @ translate(*(-p))


def spin(axis, deg: float) -> np.ndarray:
    return about_axis(axis, deg)[:3, :3]


# ---------------------------------------------------------------------------- kinematics
def hub_drop(theta: float) -> float:
    t = math.radians(theta)
    return LINK + LEVER * math.sin(t) - math.sqrt(LINK ** 2 - (LEVER * (1 - math.cos(t))) ** 2)


def theta_for_drop(s: float) -> float:
    """Fang angle (deg) that puts the hub pins `s` below their shut position."""
    lo, hi = -10.0, 80.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if hub_drop(mid) < s:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


OPEN_DEG = theta_for_drop(REST_DROP)     # about 51.5 degrees at rest


def fang_turn(theta: float) -> np.ndarray:
    """+X fang (and its lever) turned open by theta from the shut geometry."""
    return about_axis((0, 0, 1), -theta, (P[0], P[1], 0))


def link_move(theta: float) -> np.ndarray:
    """+X link moved from its shut geometry to fang angle theta (hub pins s lower)."""
    s = hub_drop(theta)
    a = math.radians(theta)
    lx, ly = P[0] - LEVER * math.cos(a), P[1] + LEVER * math.sin(a)
    hx, hy = P[0] - LEVER, H_Y + s
    psi = math.degrees(math.atan2(lx - hx, ly - hy))
    return translate(0, s, 0) @ about_axis((0, 0, 1), -psi, (hx, H_Y, 0))


def pose(t: float) -> dict:
    """t = 0 resting (as built), t = 1 pressed until the box's button bottoms out."""
    d = PRESS * t
    body = translate(0, d, 0)
    theta = theta_for_drop(REST_DROP - d)
    fang = fang_turn(theta) @ np.linalg.inv(fang_turn(OPEN_DEG))
    link = link_move(theta) @ np.linalg.inv(link_move(OPEN_DEG))
    out = {"body": body, "tube": body}
    for k in range(4):
        Q = quarter(k)
        Qi = np.linalg.inv(Q)
        out[f"fang_{k}"] = body @ Q @ fang @ Qi
        out[f"link_{k}"] = body @ Q @ link @ Qi
    return out


# ---------------------------------------------------------------------------- disc
def _rotate_cells(cells, k):
    R = rot(y=QUARTERS[k])
    out = set()
    for i, j in cells:
        c = R @ np.array([(i + .5) * 20, 0, (j + .5) * 20])
        out.add((int(math.floor(c[0] / 20)), int(math.floor(c[2] / 20))))
    return out


LEAD_HOLE = {(i, k) for i in (3, 4) for k in (2, 3, 4)}   # x 60..100, z 40..100: the light
                                                         # leads' plugs pass down to the stand
CENTRE = {(i, k) for i in range(-2, 2) for k in range(-2, 2)
          if math.hypot(i + .5, k + .5) < 2.0}                 # 4x4 round: the guide plate
CENTRE_2X2 = {(-1, -1), (-1, 0), (0, -1), (0, 0)}
CENTRE_4X4 = {(i, k) for i in range(-2, 2) for k in range(-2, 2)}  # the round plate's corners
                                                                   # would clip plates there


def hole_cells() -> set:
    links = set()
    for k in range(4):
        links |= _rotate_cells({(4, -2), (5, -2)}, k)       # link x 91..109, z -40..-20
    return links


def arm_cells() -> set:
    """Where the fixed hub's arms rest on the disc: tiles there, so they don't clutch."""
    out = set()
    for k in range(4):
        out |= _rotate_cells({(2, -1), (3, -1), (4, -1), (5, -1)}, k)   # x 40..120, z -20..0
    return out


def disc(sub, color="skirt_accent") -> set:
    cells = ring_cells(DISC_R) - hole_cells() - LEAD_HOLE
    plates = {6: "3666", 4: "3710", 2: "3023b", 1: "3024"}
    top_cells = cells - CENTRE_4X4 - arm_cells()
    bottom_cells = cells - CENTRE_2X2
    a = pack_cells(top_cells, lengths=(6, 4, 2, 1), offset=0, mode="x")
    b = pack_cells(bottom_cells, lengths=(6, 4, 2, 1), offset=1, mode="z")
    # a 1x1 in both layers over the same cell would be a loose column: leave those cells out
    singles_a = {(i, k) for i, k, n, _ in a if n == 1}
    singles_b = {(i, k) for i, k, n, _ in b if n == 1}
    loose = singles_a & singles_b
    a = [r for r in a if not (r[2] == 1 and r[:2] in loose)]
    b = [r for r in b if not (r[2] == 1 and r[:2] in loose)]
    # laid out on the table: the bottom layer (b) loose, then the top layer (a) locks it
    for layer, runs, y in (("bottom", b, DISC_TOP + 8), ("top", a, DISC_TOP)):
        mid = sorted(r[0] for r in runs)[len(runs) // 2]
        for side, half in (("left", [r for r in runs if r[0] < mid]),
                           ("right", [r for r in runs if r[0] >= mid])):
            sub.step(f"Base disc: {layer} layer, {side} half")
            for i, k, n, axis in half:
                _place_run(sub, plates[n], color, i, k, n, axis, y, "disc")
    sub.step("Guide plate in the middle (the stand's axle slides through its hole) and "
             "smooth tiles where the hub's arms will rest")
    sub.place("60474", color, (0, DISC_TOP, 0), tag="guide")
    for k in range(4):
        R = rot(y=QUARTERS[k])
        c = R @ np.array([80.0, 0, -10.0])
        sub.place("2431", color, (c[0], DISC_TOP, c[2]), R)             # 1x4 tile
    return cells - loose


# ---------------------------------------------------------------------------- submodels
def bearing_submodel(model):
    b = model.submodel("fang_bearing", "Fang bearing")
    b.place("3003", "frame_dark", (P[0], DISC_BOTTOM, 40))                  # 2x2 brick
    b.step()
    for z in (30, 50):
        b.place("3700", "frame_dark", (P[0], DISC_BOTTOM + 24, z))
    return b


def fang_submodel(model):
    f = model.submodel("fang", "Fang")
    f.place("3705", "frame_dark", (P[0], P[1], 20), ALONG_Z)              # axle 4: z -20..60
    f.step("Bone-white fang")
    f.place("32348", "fang", (P[0], P[1], 0), HANG)                       # z -10..10
    tip = HANG @ np.array([48.0, 0, 96.0])
    tx, ty = P[0] + tip[0], P[1] + tip[1]
    ang = math.degrees(math.atan2(0.6, -0.8))
    f.place("4519", "frame", (tx, ty, 0), spin((0, 0, 1), ang) @ ALONG_Z)   # axle 3: z -30..30
    d = np.array([0.8, -0.6, 0.0])
    tooth = np.array([[0.6, 0.8, 0.0], [0, 0, 1.0], d]).T
    f.place("41669", "fang", (tx, ty, 20), tooth)                             # z 10..30
    f.place("41669", "fang", (tx, ty, -20), tooth)                            # z -30..-10
    f.step("Lever and spacer")
    f.place("6632", "frame_dark", (P[0], P[1], -15), INWARD)              # z -20..-10
    f.place("32123b", "frame", (P[0], P[1], 15), None)                    # half bush z 10..20
    return f


def link_submodel(model):
    k = model.submodel("link", "Link")
    k.place("32316", "frame_dark", (P[0] - LEVER, (P[1] + H_Y) / 2, -30), HANG)
    return k


def hub_submodel(model):
    """Fixed hub: rides on top of the stand's centre axle (round plate with axle hole in the
    middle), a 6x6 plate over it, and four Technic 1x4 arms whose outer holes carry the link
    pins at H_REST. The back light's lead passes over it, clear even with the body pressed."""
    h = model.submodel("hub", "Hub")
    top = H_REST - 10                                                      # arms' top: 32
    h.place("4032a", "frame_dark", (0, top - 8, 0))                        # axle hole, 24..32
    for x, z in ((-40, 0), (40, 0), (0, -40), (0, 40)):
        h.place("3022", "frame_dark", (x, top - 8, z))
    h.step("6x6 plate on top")
    h.place("3958", "frame_dark", (0, top - 16, 0))
    h.step("Four arms")
    for k in range(4):
        R = rot(y=QUARTERS[k])
        c = R @ np.array([80.0, 0, -10.0])
        h.place("3701", "frame_dark", (c[0], top, c[2]), R)               # holes at x 60..100
    return h


# ---------------------------------------------------------------------------- assembly
def _world(M: np.ndarray):
    return M[:3, 3].copy(), M[:3, :3].copy()


def core(model, sub):
    """Build order as a person would: bearings, fangs (set open), links dropped in through
    the disc, hub on top, pins last."""
    bearing = bearing_submodel(model)
    fang = fang_submodel(model)
    link = link_submodel(model)
    for k in range(4):
        sub.step(f"Fang bearing {k + 1}")
        sub.use(bearing, (0, 0, 0), quarter(k)[:3, :3], tag=f"bearing_{k}")
    open_fang = fang_turn(OPEN_DEG)
    open_link = link_move(OPEN_DEG)
    for k in range(4):
        Q = quarter(k)
        sub.step(f"Fang {k + 1}: slide its axle through the bearing, fang swung open")
        pos, R = _world(Q @ open_fang)
        sub.use(fang, pos, R, tag=f"fang_{k}", insert=tuple(Q[:3, :3] @ np.array([0.0, 0, -1])))
    for k in range(4):
        Q = quarter(k)
        sub.step(f"Link {k + 1}: drop it through the disc and pin it to the lever")
        pos, R = _world(Q @ open_link)
        sub.use(link, pos, R, tag=f"link_{k}", insert=(0, -1, 0))
        # an axle as the pivot shaft: it slides through both round holes (a pin's collar can't)
        M = Q @ open_fang @ transform((P[0] - LEVER, P[1], -20.0), ALONG_Z)
        pos, R = _world(M)
        sub.place("32062", "frame_dark", pos, R, tag=f"link_{k}",
                  insert=tuple(Q[:3, :3] @ np.array([0.0, 0, -1])))
    sub.step("Hub on the four links, held by an axle through each")
    sub.use(hub_submodel(model), (0, 0, 0), None, tag="hub", insert=(0, -1, 0))
    for k in range(4):
        Q = quarter(k)
        c = Q[:3, :3] @ np.array([P[0] - LEVER, H_REST, -20.0])
        sub.place("32062", "frame_dark", c, Q[:3, :3] @ ALONG_Z, tag=f"link_{k}",
                  insert=tuple(Q[:3, :3] @ np.array([0.0, 0, -1])))
    for k in range(4):
        model.moving_group(f"fang_{k}", f"fang_{k}")
        model.moving_group(f"link_{k}", f"link_{k}")
    model.moving_group("tube", "tube")
    model.moving_group("body", "*", exclude={"stand", "hub"})
    model.pose = pose
