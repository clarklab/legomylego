"""The clock stage: a 10 x 10 stud core with four SNOT clock faces and four real quartz clock
inserts (bought, not LEGO: stand-in part bk-clock-insert-35mm).

Frame: the stage's own, with the clocks' centre at y = 0 on the tower axis; the -Z face is
face 0 and the others follow by turning about Y (FACES). Each face (u across, v down):

    z -116..-108  tiles: red ring (4 x 4 macaroni, r 60..80), white ring (3 x 3 macaroni,
                  r 40..60) round a 32 mm round window, tan corners, red pilasters and bands
    z -108..-100  SNOT plates (studs out) with a 4 x 4 hole behind the window
    z -100.. -92  the insert's bezel (up to 38 mm) pressed against the plates' back
    z  -92.. -50  its movement and setting knob (35 mm body, 20 mm overall)

The insert sits in a slot open to the top: its body rests on two tile rails 40 mm apart
(it centres itself between them), the bezel behind the face plates. With the lift-off top
removed it lifts straight out; the knobs and batteries face the open middle of the tower.
Four inserts back to back need the faces at least 88 LDU from the axis (35 mm bodies 20 mm
deep); here they are 100 LDU (4 cm), leaving a 45 mm shaft between their backs.

Core layers (y down): B0 plates 104..120, B1 side-stud bricks 80..104 (studs at 90), B2
plates 64..80, floor F1 56..64 and F2 48..56 (notched under the bezels, a channel under each
body), rails 40..48. Corner blocks (2 x 2 at each corner) rise from 64 to -120: side-stud
brick courses every 40 LDU (studs at 50, 10, -30, -70) with two plates between, capped at
-120 with one stud each for the lift-off top."""
from __future__ import annotations

import math

import numpy as np

from brickkit.ldraw.matrix import rot, transform, translate
from kit import (AV, PLATE, PLATE1, S, TILE1, Batch, orient, rect_M, studs_toward, use_M,
                 weave)

FACES = {"s": 0, "w": 90, "n": 180, "e": 270}      # rot(y=a) turns face "s" (-Z) to it
INSERT = "bk-clock-insert-35mm"
R_BODY = 43.75
RAIL_X = 20.0                                      # the rails' inner edges, +-20 LDU
RAIL_TOP = 40.0
INSERT_Y = RAIL_TOP - math.sqrt(R_BODY ** 2 - RAIL_X ** 2) - 0.1    # ~1 LDU below centre
Z_FACE = -100.0                                    # back of the face plates = bezel front
Z_PLATE = -108.0                                   # plates' stud side
Z_TILE = -116.0                                    # tiles' top
HOUR_Z, MIN_Z = 2.0, 0.9                           # hands in front of the dial (insert frame)
TOP = -120                                         # top of the fixed stage (corner caps)
BRICK_TOPS = (40, 0, -40, -80)                     # corner-block side-stud courses
OUT = np.array([0.0, 0.0, -1.0])                   # face 0's outward normal
UP = np.array([0.0, 1.0, 0.0])                     # v (down the face)
ACROSS = np.array([1.0, 0.0, 0.0])                 # u (along the face)


FLAT_TO_STAGE = translate(0, 0, Z_PLATE) @ transform((0, 0, 0), rot(x=90))   # face 0


def face_R(name: str) -> np.ndarray:
    return rot(y=FACES[name])


def face_M(name: str) -> np.ndarray:
    return transform((0, 0, 0), face_R(name))


# ------------------------------------------------------------------ one clock face (SNOT)
def _snot(a_u, a_v):
    """Rotation of a tile/plate lying on the face, studs out (-Z), local X along (a_u, a_v)
    in the face (u = +X, v = +Y)."""
    return orient((a_u, a_v, 0.0), (0.0, 0.0, 1.0))


def _ring_R(q_u: int, q_v: int) -> np.ndarray:
    """A macaroni tile (arc centre at its origin, the ring in local +X/-Z) turned into the
    face quadrant (sign of u, sign of v)."""
    a = {(1, 1): (1, 0), (-1, 1): (0, 1), (-1, -1): (-1, 0), (1, -1): (0, -1)}[(q_u, q_v)]
    return _snot(*a)


def _quarter_R(o_u: int, o_v: int) -> np.ndarray:
    """Tile Round 1 x 1 Quarter (25269, arc centre at local (-10, 10)) with its arc centre
    toward the cell corner (o_u, o_v) (signs)."""
    a = {(1, 1): (-1, 0), (-1, -1): (1, 0), (1, -1): (0, 1), (-1, 1): (0, -1)}[(o_u, o_v)]
    return _snot(*a)


def clock_face(model):
    """The face panel: a SNOT plate layer (studs out) with tiles, built as one piece and
    pressed onto the tower's side studs. u from -100 to +120: the extra column at the right
    covers the corner (the neighbouring face ends at the tower's core)."""
    s = model.submodel("clock_face", "Clock face")
    b = Batch()
    to_flat = np.linalg.inv(FLAT_TO_STAGE)       # built lying on its back, studs up

    def plate(n, u, v, along, colour, cat):
        a = (0, 1) if along == "v" else (1, 0)
        b.add(PLATE1[n], colour, to_flat @ transform((u, v, Z_PLATE), _snot(*a)), cat)

    def tile(part, u, v, R, colour, cat):
        b.add(part, colour, to_flat @ transform((u, v, Z_TILE), R), cat)

    # plates: vertical columns (1 x 12 full height, 1 x 4 above and below the window hole)
    for u, colour in ((-90, "trim"), (90, "wall"), (110, "trim")):
        plate(12, u, 0, "v", colour, "plates")
    for u in (-70, -50, 50, 70):
        plate(12, u, 0, "v", "wall", "plates")
    for u in (-30, -10, 10, 30):
        for v in (-80, 80):
            plate(4, u, v, "v", "wall", "plates")
    # tiles: bands top and bottom across the whole width, tan rows above and below the ring
    for v in (-110, 110):
        tile(TILE1[8], -20, v, _snot(1, 0), "trim", "bands")
        tile(TILE1[3], 90, v, _snot(1, 0), "trim", "bands")
    for v in (-90, 90):
        tile(TILE1[8], 0, v, _snot(1, 0), "wall", "rows")
    # pilasters: red strips up the sides
    for u, colour in ((-90, "trim"), (90, "wall"), (110, "trim")):
        tile(TILE1[6], u, -40, _snot(0, 1), colour, "pilasters")
        tile(TILE1[4], u, 60, _snot(0, 1), colour, "pilasters")
    # the clock ring: red outer ring, white inner ring, tan corners outside it
    for qu in (1, -1):
        for qv in (1, -1):
            R = _ring_R(qu, qv)
            tile("27507", 0, 0, R, "trim", "ring")
            tile("79393", 0, 0, R, "dial", "dial")
            tile(TILE1[1], 70 * qu, 70 * qv, _snot(1, 0), "wall", "corners")
            tile("25269", 70 * qu, 50 * qv, _quarter_R(qu, qv), "wall", "corners")
            tile("25269", 50 * qu, 70 * qv, _quarter_R(qu, qv), "wall", "corners")
    phases = [["plates"], ["bands", "rows"], ["pilasters"], ["ring", "dial", "corners"]]
    b.emit(s, phases, {
        "plates": "Clock face: plates side by side, studs to the front. Leave a 4 x 4 hole "
                  "in the middle",
        "bands": "Tiles across the top and bottom tie the plates together",
        "pilasters": "Pilasters up the sides: red at the corners",
        "ring": "The clock ring: four red macaroni tiles",
        "dial": "Four white macaroni tiles make the clock face round the window",
        "corners": "Tan corners outside the ring"}, per_step=8)
    return s


# ------------------------------------------------------------------ the core
def _corner_block(b: Batch, R: np.ndarray, x0=70, x1=90, z0=-90, z1=-70):
    """The 2 x 2 corner column at the face's right end (+X, -Z), built from 64 up to TOP."""
    def M(x, y, z, Rl=None):
        Rp = R if Rl is None else R @ Rl
        return transform(R @ np.array([x, y, z], float), Rp)

    for top in BRICK_TOPS:
        b.add("26604", "core", M(x1, top, z0), f"blocks{top}")                   # -Z, +X
        b.add("87087", "core", M(x0, top, z0), f"blocks{top}")                   # -Z
        b.add("87087", "core", M(x1, top, z1, rot(y=-90)), f"blocks{top}")       # +X
        b.add("3005", "core", M(x0, top, z1), f"blocks{top}")
        b.add("3022", "core", M(80, top - 8, -80), f"blocks{top}")
        b.add("3022", "core", M(80, top - 16, -80), f"blocks{top}")
    b.add("3022", "core", M(80, -104, -80), "cap")
    b.add("3022", "core", M(80, -112, -80), "cap")
    b.add("3024", "core", M(x1, -120, z0), "cap")                                 # the stud
    b.add("3069b", "core", M(x0, -120, -80, rot(y=90)), "cap")
    b.add("3070b", "core", M(x1, -120, z1), "cap")


def _plate_layer(b: Batch, cells, y, cat, along, phase=0, colour="core"):
    lengths = [n for n in (10, 8, 6, 4, 3, 2, 1) if AV.ok(PLATE1[n], colour)]
    for r in weave(cells, along, lengths, phase):
        p, M = rect_M(PLATE, r, y)
        b.add(p, colour, M, cat)


def _cells(fn) -> set:
    return {(i, k) for i in range(-5, 5) for k in range(-5, 5) if fn(i, k)}


def _rot_cells(cells, name) -> set:
    """Cells of face 0 turned to another face (about the tower axis)."""
    R = face_R(name)
    out = set()
    for i, k in cells:
        x, z = 20 * i + 10, 20 * k + 10
        p = R @ np.array([x, 0.0, z])
        out.add((int(round((p[0] - 10) / 20)), int(round((p[2] - 10) / 20))))
    return out


def core_batch() -> Batch:
    b = Batch()
    full = _cells(lambda i, k: True)
    corners0 = {(i, k) for i in (3, 4) for k in (-5, -4)}
    corners = set().union(*(_rot_cells(corners0, f) for f in FACES))
    notch0 = {(i, -5) for i in range(-3, 3)}                       # under the bezel
    channel0 = {(i, k) for i in (-1, 0) for k in (-4, -3)}         # under the body
    notches = set().union(*(_rot_cells(notch0 | channel0, f) for f in FACES))
    _plate_layer(b, full, 112, "b0", "x", 0)
    _plate_layer(b, full, 104, "b0", "z", 1)
    for f in FACES:                                                # side-stud bricks, B1
        R = face_R(f)
        for x in (-40, 40):
            b.add("30414", "core", transform(R @ np.array([x, 80, -90.0]), R), "b1")
        b.add("26604", "core", transform(R @ np.array([90.0, 80, -90]), R), "b1")
    _plate_layer(b, full, 72, "b2", "x", 2)
    _plate_layer(b, full, 64, "b2", "z", 3)
    _plate_layer(b, full - corners, 56, "floor", "x", 0)
    _plate_layer(b, full - corners - notches, 48, "floor", "z", 1)
    for f in FACES:
        R = face_R(f)
        for x in (-30, 30):                                        # rails
            b.add("3069b", "core", transform(R @ np.array([x, RAIL_TOP, -60.0]), R @ rot(y=90)),
                  "rails")
        _corner_block(b, R)
    return b


CORE_PHASES = [["b0"], ["b1"], ["b2"], ["floor"], ["rails"],
               ["blocks40"], ["blocks0"], ["blocks-40"], ["blocks-80"], ["cap"]]


# ------------------------------------------------------------------ inserts and hands
def hand_angles(t: float) -> tuple[float, float]:
    """(hour, minute) hand angles in degrees clockwise from 12: 10:10 at t = 0, two hours
    later at t = 1."""
    minutes = 10 * 60 + 10 + 120 * t
    return minutes * 0.5, minutes * 6.0


def clock_stage(model, face):
    s = model.submodel("clock_stage", "Clock stage")
    core_batch().emit(s, CORE_PHASES, {
        "b0": "Clock stage: two layers of plates", "b1": "Bricks with side studs all round",
        "b2": "Two more layers of plates", "floor": "The floor: leave the gaps at the "
        "front of each side and the channel in the middle", "rails":
        "Two tiles on each side: the rails the clock inserts rest on",
        "blocks40": "The corner columns: bricks with side studs and 2 x 2 plates",
        "cap": "Cap each corner with one stud: the lift-off top holds on these"},
        per_step=8)
    for n, f in enumerate(FACES):
        R = face_R(f)
        s.step("Press a clock face onto the side studs" if n == 0 else "")
        use_M(s, face, transform((0, 0, 0), R) @ FLAT_TO_STAGE, insert=tuple(R @ OUT))
    h0, m0 = hand_angles(0.0)
    for n, f in enumerate(FACES):
        R = face_R(f)
        s.step("Slide a quartz clock insert (not LEGO, see the start of the book) down "
               "behind the face: its bezel goes behind the plates, its body rests on the "
               "rails" if n == 0 else "")
        s.place(INSERT, "clock", tag=f"clock_{f}", insert=(0, -1, 0)).M = transform(
            R @ np.array([0.0, INSERT_Y, Z_FACE]), R)
        s.place("bk-clock-hand-hour", "clock", tag=f"hour_{f}",
                insert=tuple(R @ OUT)).M = transform(
            R @ np.array([0.0, INSERT_Y, Z_FACE + HOUR_Z]), R @ rot(z=h0))
        s.place("bk-clock-hand-minute", "clock", tag=f"minute_{f}",
                insert=tuple(R @ OUT)).M = transform(
            R @ np.array([0.0, INSERT_Y, Z_FACE + MIN_Z]), R @ rot(z=m0))
        model.press_fit(f"clock_{f}", "rests on its rails, bezel behind the face plates")
        model.press_fit(f"hour_{f}", "on the insert's spindle")
        model.press_fit(f"minute_{f}", "on the insert's spindle")
    return s


def hand_pose(t: float, stage_M: np.ndarray) -> dict:
    """World transforms of the eight hand groups at pose t (the stage placed at stage_M)."""
    h0, m0 = hand_angles(0.0)
    h, m = hand_angles(t)
    out = {}
    for f in FACES:
        R = face_R(f)
        axis_pt = stage_M @ np.append(R @ np.array([0.0, INSERT_Y, Z_FACE]), 1.0)
        Rw = stage_M[:3, :3] @ R
        for g, a in ((f"hour_{f}", h - h0), (f"minute_{f}", m - m0)):
            Rt = np.eye(4)
            Rt[:3, :3] = Rw @ rot(z=a) @ Rw.T
            out[g] = translate(*axis_pt[:3]) @ Rt @ translate(*(-axis_pt[:3]))
    return out
