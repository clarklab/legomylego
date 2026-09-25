"""Core of the Baby Metroid: base disc, fang mechanism, stand socket.

Frame: LDraw units, -Y up, dome rim at y = 0; the base disc spans y 56..72.

Fang mechanism (+X fang shown; the others are quarter turns of it):
  pivot   P = (120, 106): a short axle along Z in two Technic bricks hanging under the disc
  fang    white bent beam locked on the axle (z -10..10), tip bending inward, tooth at the tip
  lever   thin 1x3 on the axle (z -20..-10) pointing inward: pin hole L = (100, 106)
  link    thick 1x5 (round holes, 80 LDU) from L up through the disc to H = (100, 26)
  hub     four Technic bricks 1x6 in a pinwheel under a 6x6 plate; their outer holes are H
Opening a fang pushes its lever end down, which pulls the hub down, which opens the other three
fangs through their links. The +X axle also carries a 24T gear driven by a vertical worm
(self-locking, so the fangs hold any position); a 12T bevel pair turns the worm's axle into a
horizontal axle with a knob outside the skirt at the back (+Z)."""
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
H_Y = 26.0                       # hub pin height at rest
GEAR_Z = 80.0                    # 24T on the +X axle (z 70..90)
WORM_X = 80.0                    # vertical worm axle at (80, z=80)
KNOB_Y = 18.0                    # knob axle height
BEVEL_D = 20.0
OPEN_DEG = 45.0
WORM_PHASE = 320.0
KNOB_PHASE = 15.0
KNOB_SENSE = 1.0
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


def pose(t: float) -> dict:
    theta = OPEN_DEG * t
    s = hub_drop(theta)
    a = math.radians(theta)
    lx, ly = P[0] - LEVER * math.cos(a), P[1] + LEVER * math.sin(a)
    hx, hy = P[0] - LEVER, H_Y + s
    psi = math.degrees(math.atan2(lx - hx, ly - hy))
    fang = about_axis((0, 0, 1), -theta, (P[0], P[1], 0))
    link = translate(0, s, 0) @ about_axis((0, 0, 1), -psi, (hx, H_Y, 0))
    out = {"hub": translate(0, s, 0)}
    for k in range(4):
        Q = quarter(k)
        Qi = np.linalg.inv(Q)
        out[f"fang_{k}"] = Q @ fang @ Qi
        out[f"link_{k}"] = Q @ link @ Qi
    out["gear24"] = out["fang_0"]
    worm = -24.0 * theta
    out["worm"] = about_axis((0, 1, 0), worm, (WORM_X, 0, GEAR_Z))
    out["knob"] = about_axis((0, 0, 1), KNOB_SENSE * worm, (WORM_X, KNOB_Y, 0))
    return out


# ---------------------------------------------------------------------------- disc
def _rotate_cells(cells, k):
    R = rot(y=QUARTERS[k])
    out = set()
    for i, j in cells:
        c = R @ np.array([(i + .5) * 20, 0, (j + .5) * 20])
        out.add((int(math.floor(c[0] / 20)), int(math.floor(c[2] / 20))))
    return out


def hole_cells() -> set:
    links = set()
    for k in range(4):
        links |= _rotate_cells({(4, -2), (5, -2)}, k)       # link x 91..109, z -40..-20
    worm = {(3, 3), (4, 3), (3, 4), (4, 4)}                  # vertical axle at (80, 80)
    return links | worm


def disc(sub, color="skirt_accent") -> set:
    cells = ring_cells(DISC_R) - hole_cells()
    plates = {6: "3666", 4: "3710", 2: "3023b", 1: "3024"}
    a = pack_cells(cells, lengths=(6, 4, 2, 1), offset=0, mode="x")
    b = pack_cells(cells, lengths=(6, 4, 2, 1), offset=1, mode="z")
    # a 1x1 in both layers over the same cell would be a loose column: leave those cells out
    singles_a = {(i, k) for i, k, n, _ in a if n == 1}
    singles_b = {(i, k) for i, k, n, _ in b if n == 1}
    loose = singles_a & singles_b
    a = [r for r in a if not (r[2] == 1 and r[:2] in loose)]
    b = [r for r in b if not (r[2] == 1 and r[:2] in loose)]
    sub.step("Base disc: two crossed layers of plates")
    for i, k, n, axis in a:
        _place_run(sub, plates[n], color, i, k, n, axis, DISC_TOP, "disc")
    for i, k, n, axis in b:
        _place_run(sub, plates[n], color, i, k, n, axis, DISC_TOP + 8, "disc")
    return cells - loose


# ---------------------------------------------------------------------------- submodels
def bearing_submodel(model):
    b = model.submodel("fang_bearing", "Fang bearing")
    b.place("3003", "frame_dark", (P[0], DISC_BOTTOM, 40))                  # 2x2 brick
    b.step()
    for z in (30, 50):
        b.place("3700", "frame_dark", (P[0], DISC_BOTTOM + 24, z))
    return b


def fang_submodel(model, driven: bool):
    name = "fang_driven" if driven else "fang"
    f = model.submodel(name, "Fang with drive gear" if driven else "Fang")
    if driven:
        f.place("3706", "frame_dark", (P[0], P[1], 40), ALONG_Z)          # axle 6: z -20..100
    else:
        f.place("3705", "frame_dark", (P[0], P[1], 20), ALONG_Z)          # axle 4: z -20..60
    f.step("Bone-white fang")
    f.place("32348", "fang", (P[0], P[1], 0), HANG)                       # z -10..10
    tip = HANG @ np.array([48.0, 0, 96.0])
    tx, ty = P[0] + tip[0], P[1] + tip[1]
    ang = math.degrees(math.atan2(0.6, -0.8))
    f.place("32062", "frame_dark", (tx, ty, 10), spin((0, 0, 1), ang) @ ALONG_Z)
    d = np.array([0.8, -0.6, 0.0])
    f.place("41669", "fang", (tx, ty, 20), np.array([[0.6, 0.8, 0.0], [0, 0, 1.0], d]).T)
    f.step("Lever and spacer")
    f.place("6632", "frame_dark", (P[0], P[1], -15), INWARD)              # z -20..-10
    f.place("32123b", "frame", (P[0], P[1], 15), None)                    # half bush z 10..20
    return f


def link_submodel(model):
    k = model.submodel("link", "Link")
    k.place("32316", "frame_dark", (P[0] - LEVER, (P[1] + H_Y) / 2, -30), HANG)
    return k


def hub_submodel(model):
    h = model.submodel("hub", "Hub")
    h.place("3958", "frame_dark", (0, H_Y - 18, 0))                       # 6x6 plate, y 8..16
    h.step("Four arms")
    for k in range(4):
        R = rot(y=QUARTERS[k])
        c = R @ np.array([60.0, 0, -10.0])
        h.place("3894", "frame_dark", (c[0], H_Y - 10, c[2]), R)          # hole at y=26
    return h


# ---------------------------------------------------------------------------- assembly
def core(model, sub):
    """Build order as a person would: bearings, worm, fangs, gears into mesh, knob drive,
    links dropped in through the disc, hub on top, pins last."""
    bearing = bearing_submodel(model)
    fang = fang_submodel(model, driven=False)
    fang_d = fang_submodel(model, driven=True)
    link = link_submodel(model)
    for k in range(4):
        sub.step(f"Fang bearing {k + 1}")
        sub.use(bearing, (0, 0, 0), quarter(k)[:3, :3], tag=f"bearing_{k}")
    sub.step("Worm bearings")
    sub.place("3709b", "frame_dark", (WORM_X, DISC_TOP - 8, GEAR_Z), rot(y=90))
    sub.place("3709b", "frame_dark", (WORM_X, DISC_BOTTOM, GEAR_Z), rot(y=90))
    sub.step("Worm on its axle, from below")
    wr = spin((0, 1, 0), WORM_PHASE)
    sub.place("3706", "frame_dark", (WORM_X, 90, GEAR_Z), wr @ ALONG_Y, tag="worm",
              insert=(0, 1, 0))                                                  # y 30..150
    sub.place("4716", "worm", (WORM_X, P[1], GEAR_Z), wr @ rot(x=90), tag="worm_gear",
              insert=(0, 1, 0))
    sub.place("3713", "frame", (WORM_X, P[1] + 30, GEAR_Z), wr @ rot(x=90), tag="worm",
              insert=(0, 1, 0))
    for k in range(4):
        Q = quarter(k)
        sub.step(f"Fang {k + 1}: slide its axle through the bearing")
        sub.use(fang_d if k == 0 else fang, (0, 0, 0), Q[:3, :3], tag=f"fang_{k}",
                insert=tuple(Q[:3, :3] @ np.array([0.0, 0, -1])))
    sub.step("Drive gear onto fang 1's axle")
    sub.place("32123b", "frame", (P[0], P[1], 65), None, tag="gear24_bush", insert=(0, 0, 1))
    sub.place("3648b", "gear_dark", (P[0], P[1], GEAR_Z), None, tag="gear24", insert=(0, 0, 1))
    sub.step("Bevel gear on top of the worm axle")
    sub.place("6589", "gear", (WORM_X, KNOB_Y + BEVEL_D, GEAR_Z), wr @ rot(x=90),
              tag="worm_bevel", insert=(0, -1, 0))
    sub.step("Knob bearing")
    sub.place("3004", "frame_dark", (WORM_X, DISC_TOP - 24, 130))
    sub.place("3700", "frame_dark", (WORM_X, KNOB_Y - 10, 130), tag="knob_bearing")
    for k in range(4):
        Q = quarter(k)
        sub.step(f"Link {k + 1}: drop it through the disc and pin it to the lever")
        sub.use(link, (0, 0, 0), Q[:3, :3], tag=f"link_{k}", insert=(0, -1, 0))
        # an axle as the pivot shaft: it slides through both round holes (a pin's collar can't)
        c = Q[:3, :3] @ np.array([P[0] - LEVER, P[1], -20.0])
        sub.place("32062", "frame_dark", c, Q[:3, :3] @ ALONG_Z, tag=f"link_{k}",
                  insert=tuple(Q[:3, :3] @ np.array([0.0, 0, -1])))
    sub.step("Hub on the four links, held by an axle through each")
    sub.use(hub_submodel(model), (0, 0, 0), None, tag="hub", insert=(0, -1, 0))
    for k in range(4):
        Q = quarter(k)
        c = Q[:3, :3] @ np.array([P[0] - LEVER, H_Y, -20.0])
        sub.place("32062", "frame_dark", c, Q[:3, :3] @ ALONG_Z, tag=f"link_{k}",
                  insert=tuple(Q[:3, :3] @ np.array([0.0, 0, -1])))
    sub.step("Stand socket")
    sub.place("3941", "frame_dark", (0, DISC_BOTTOM, 0), tag="socket")
    for g in ["hub", "gear24", "gear24_bush", "worm", "worm_gear", "worm_bevel", "knob",
              "knob_bevel"] + [f"fang_{k}" for k in range(4)] + [f"link_{k}" for k in range(4)]:
        model.moving_group(g, g)
    model.pose = pose
    model.gear_pair("gear24", "worm_gear", "worm")
    model.gear_pair("worm_bevel", "knob_bevel", "bevel")


def knob(model, sub):
    """After the skirt: the bevel gear goes in from inside, then the knob axle slides in from
    outside through the skirt's Technic bricks and the bearing, then the knob."""
    kr = spin((0, 0, 1), KNOB_PHASE)
    sub.step("Knob axle: gear inside, axle through the skirt")
    sub.place("6589", "gear", (WORM_X, KNOB_Y, GEAR_Z + BEVEL_D), kr @ rot(y=180),
              tag="knob_bevel", insert=(0, -1, 0))
    sub.place("44294", "frame", (WORM_X, KNOB_Y, 160), kr @ ALONG_Z, tag="knob",
              insert=(0, 0, 1))                                                  # z 90..230
    sub.step("Knob")
    sub.place("32072", "frame_dark", (WORM_X, KNOB_Y, 215), kr, tag="knob", insert=(0, 0, 1))


def pose_groups(p: dict) -> dict:
    """Expand group aliases: parts tagged worm_gear / worm_bevel move with the worm, etc."""
    p = dict(p)
    p["worm_gear"] = p["worm_bevel"] = p["worm"]
    p["knob_bevel"] = p["knob"]
    p["gear24_bush"] = p["gear24"]
    return p


_raw_pose = pose


def pose(t: float) -> dict:  # noqa: F811  (final pose with aliases)
    return pose_groups(_raw_pose(t))
