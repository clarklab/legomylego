"""Chainsaw Face's skeleton: forward kinematics for every limb segment, and inverse kinematics
for the legs (feet planted on the stand's studs) and for both arms (fists on the chainsaw's
handles).

All matrices are 4x4 world transforms in LDU (-Y up, the figure faces -Z). The right-hand
limbs are built as mirror images of the left ones, so a right limb's local transforms are
the left ones conjugated by the mirror X (x -> -x); the same joint angles give mirror poses.

Joint angles (degrees):
* legs (hip ball flexion/abduction, knee): solved so both shoes sit on their studs;
* waist: turn about the vertical;
* neck ball: nod (+ = chin down), turn (+ = to his left), tilt;
* shoulder ball: flexion (arm forwards and up), abduction (arm out to the side), twist;
* elbow: flexion; wrist ball: spin (about the forearm), flexion, sideways;
* the saw: its engine centre and heading are the pose's input; both fists grip their handle
  bars through the arms' inverse kinematics."""
from __future__ import annotations

import math

import numpy as np
from scipy.optimize import least_squares

from arms import ELBOW, FA_LEN, GRIP
from body import NECK, PELVIS_BALL, SHOULDER
from legs import ANKLE, KNEE_XZ, KNEE_Y, SHOE_BALL
from saw import FRONT_BAR, REAR_BAR

X = np.diag([-1.0, 1.0, 1.0, 1.0])

PELVIS_Y = -488                   # waist plane (world y)
SHOE_Y = -48                      # shoes' undersides sit on the stand's deck
SHOES = {1: (80, 0), -1: (-80, 0)}    # (x, z) of each ankle over the stand


def T(p) -> np.ndarray:
    M = np.eye(4)
    M[:3, 3] = p
    return M


def R(axis: str, deg: float) -> np.ndarray:
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    M = np.eye(4)
    if axis == "x":
        M[1:3, 1:3] = [[c, -s], [s, c]]
    elif axis == "y":
        M[0, 0], M[0, 2], M[2, 0], M[2, 2] = c, s, -s, c
    else:
        M[0:2, 0:2] = [[c, -s], [s, c]]
    return M


def side_local(M: np.ndarray, side: int) -> np.ndarray:
    """A left-style local transform, turned into the given side's."""
    return M if side > 0 else X @ M @ X


def mirror_pt(p, side: int):
    return (side * p[0], p[1], p[2])


# ------------------------------------------------------------------------------ legs
PELVIS = T((0, PELVIS_Y, 0))


def leg_chain(side: int, f: float, a: float, k: float, pelvis=None):
    """World (thigh, shin) for hip flexion f, abduction a (outwards), knee flexion k."""
    hip = (PELVIS if pelvis is None else pelvis) @ T(mirror_pt(PELVIS_BALL, side))
    thigh = hip @ side_local(R("z", -a) @ R("x", -f), side)
    knee = (KNEE_XZ[0], KNEE_Y, KNEE_XZ[1])
    shin = thigh @ side_local(T(knee) @ R("x", k), side)
    return thigh, shin


def ankle_of(shin: np.ndarray, side: int) -> np.ndarray:
    return (shin @ np.append(mirror_pt(ANKLE, side), 1.0))[:3]


def shoe_matrix(side: int) -> np.ndarray:
    x, z = SHOES[side]
    return T((x, SHOE_Y, z))


def solve_leg(side: int, pelvis=None, q0=(4.0, 3.0, 6.0)):
    """Hip and knee angles that put the ankle ball in the shoe on its studs (the hips may be
    moved, e.g. lowered for a knee bend)."""
    x, z = SHOES[side]
    target = np.array([x, SHOE_Y + SHOE_BALL[1], z])

    def res(q):
        _, shin = leg_chain(side, *q, pelvis=pelvis)
        return ankle_of(shin, side) - target

    sol = least_squares(res, list(q0), xtol=1e-14, ftol=1e-14, gtol=1e-14)
    assert np.abs(sol.fun).max() < 1e-6, sol.fun
    return leg_chain(side, *sol.x, pelvis=pelvis), sol.x


# ------------------------------------------------------------------------------ upper body
def torso_matrix(waist: float) -> np.ndarray:
    return PELVIS @ R("y", waist)


def head_matrix(torso: np.ndarray, nod: float, turn: float, tilt: float = 0.0):
    return torso @ T(NECK) @ R("y", turn) @ R("x", -nod) @ R("z", tilt)


def arm_chain(torso: np.ndarray, side: int, q):
    """q = (flex, abd, twist, elbow, w_spin, w_flex, w_dev) -> world (upper, fore, hand)."""
    flex, abd, tw, el, ws, wf, wd = q
    # flexion turns the arm about the shoulder axle (the socket spins round it); abduction
    # swings it in the socket's slot; twist tips the axle out of the slot (a little only)
    upper = torso @ T(mirror_pt(SHOULDER, side)) @ side_local(
        R("x", -flex) @ R("z", -abd) @ R("y", tw), side)
    fore = upper @ side_local(T(ELBOW) @ R("x", -el), side)
    hand = fore @ side_local(T((0, FA_LEN, 0)) @ R_WRIST0 @ R("x", ws) @ R("z", wf)
                             @ R("y", wd), side)
    return upper, fore, hand


# hand frame at a straight wrist: fingers down the forearm, back of the hand outwards
R_WRIST0 = np.eye(4)
R_WRIST0[:3, :3] = np.column_stack([(0, -1, 0), (-1, 0, 0), (0, 0, -1)])


def grip_frame(hand: np.ndarray, side: int):
    """(centre, axis) of the fist's clip in world coordinates."""
    c = (hand @ np.append(mirror_pt(GRIP, side), 1.0))[:3]
    a = hand[:3, :3] @ np.array([0.0, 0.0, 1.0])
    return c, a


def saw_matrix(centre, yaw: float, pitch: float, roll: float) -> np.ndarray:
    """The saw's engine frame E placed with its engine centre (E (0, -40, 60)) at `centre`:
    yaw turns the bar about the vertical (0 = bar pointing forward, -z), pitch raises the
    bar's tip, roll turns it about its length."""
    Rw = R("y", yaw) @ R("x", -pitch) @ R("z", roll)
    return T(centre) @ Rw @ T((0, 40, -60))


def bar_line(saw: np.ndarray, which: str):
    bar = FRONT_BAR if which == "front" else REAR_BAR
    return (saw @ np.append(bar, 1.0))[:3], saw[:3, :3] @ np.array([1.0, 0, 0])


# away from the engine: where a fist on each handle has room (engine frame directions)
AWAY = {"front": np.array([0.0, 0.7, -1.0]), "rear": np.array([0.0, 0.7, 1.0])}
SLIDE = {"front": 4.0, "rear": 4.0}          # how far the fist may slide off-centre
LIMITS = [(-60, 200), (2, 85), (-16, 16), (0, 100), (-180, 180), (-90, 90), (-22, 22)]


# sample points on each arm segment (their own frames, left-handed version) and boxes the
# arm must keep out of: (frame name, lo, hi, segments checked)
ARM_PTS = {
    "upper": np.array([[x, y, z, 1.0] for x in (0, 80) for y in (60, 110, 150)
                       for z in (-20, 40)]),
    "fore": np.array([[x, y, z, 1.0] for x in (-30, 30) for y in (30, 90, 140)
                      for z in (-30, 30)]),
    "hand": np.array([[x, y, z, 1.0] for x in (-60, -20) for y in (-10, 14)
                      for z in (-20, 20)]),
}
MARGIN = 4.0


def obstacles(torso, head, saw):
    """World boxes (inverse frame, lo, hi, segments) the arms keep out of."""
    boxes = [(saw, (-42, -82, -2), (42, 2, 142), ("upper", "fore", "hand")),    # engine
             (saw, (-42, -82, -20), (42, -70, 160), ("fore", "hand")),         # handle posts
             (saw, (38, -42, -182), (58, 2, 82), ("upper", "fore")),            # guide bar
             (torso, (-102, -178, -98), (102, 2, 62), ("fore", "hand")),        # torso, bib
             (head, (-62, -92, -98), (62, 16, 42), ("upper", "fore", "hand")),  # head
             (PELVIS, (-102, 0, -98), (102, 290, 62), ("fore", "hand"))]         # hips, apron
    return [(np.linalg.inv(M), np.array(lo, float), np.array(hi, float), segs)
            for M, lo, hi, segs in boxes]


def intrusion(obs, frames: dict, side: int) -> list:
    """How deep (plus a margin) each sample point of the arm is inside each box."""
    out = []
    mirror = np.array([side, 1.0, 1.0, 1.0])
    world = {seg: (frames[seg] @ (ARM_PTS[seg] * mirror).T) for seg in frames}
    for inv, lo, hi, segs in obs:
        for seg in segs:
            w = (inv @ world[seg])[:3].T
            d = np.minimum((w - lo).min(1), (hi - w).min(1)) + MARGIN
            out.extend(np.maximum(d, 0.0).tolist())
    return out


def solve_arm(torso, saw, side: int, which: str, q0, q_nom, w_nom=0.02, sign=0, obs=None):
    """Least-squares grip. `sign` (+1/-1) fixes which way round the clip holds the bar;
    `obs` (see obstacles) keeps the arm out of the saw, the body and the head."""
    P, a = bar_line(saw, which)
    away = saw[:3, :3] @ (AWAY[which] / np.linalg.norm(AWAY[which]))

    def res(q):
        upper, fore, hand = arm_chain(torso, side, q)
        c, ax = grip_frame(hand, side)
        d = c - P
        along = float(d @ a)
        perp = d - along * a
        out = list(np.cross(ax, a) * 200.0) + list(perp * 4.0)
        if obs is not None:
            out += [v * 2.0 for v in intrusion(obs, {"upper": upper, "fore": fore,
                                                     "hand": hand}, side)]
        out.append(max(0.0, abs(along) - SLIDE[which]) * 4.0)
        # the fist's body (towards the wrist and the back of the hand) points away
        body = hand[:3, :3] @ np.array([side * 1.0, 1.0, 0.0]) / math.sqrt(2)
        out.append((1.0 - float(body @ away)) * 8.0)
        if sign:
            out.append((float(ax @ a) - sign) * 50.0)
        out += list((np.asarray(q) - q_nom) * w_nom)
        return np.array(out)

    lo = [l for l, _ in LIMITS]
    hi = [h for _, h in LIMITS]
    q0 = np.clip(q0, lo, hi)
    sol = least_squares(res, q0, bounds=(lo, hi), xtol=1e-10, ftol=1e-10, gtol=1e-10,
                        max_nfev=800)
    return sol.x, sol


def exact_grip(torso, saw, side: int, which: str, q):
    """Refine q so the clip sits exactly on the bar (only the grip equations)."""
    P, a = bar_line(saw, which)

    def res(q):
        _, _, hand = arm_chain(torso, side, q)
        c, ax = grip_frame(hand, side)
        d = c - P
        along = float(d @ a)
        perp = d - along * a
        return np.concatenate([np.cross(ax, a) * 100.0, perp,
                               [max(0.0, abs(along) - SLIDE[which])]])

    lo = [l for l, _ in LIMITS]
    hi = [h for _, h in LIMITS]
    sol = least_squares(res, np.clip(q, lo, hi), bounds=(lo, hi), xtol=1e-14, ftol=1e-14,
                        gtol=1e-14, max_nfev=400)
    return sol.x, float(np.abs(sol.fun).max())


def away_score(hand: np.ndarray, saw: np.ndarray, side: int, which: str) -> float:
    away = saw[:3, :3] @ (AWAY[which] / np.linalg.norm(AWAY[which]))
    body = hand[:3, :3] @ np.array([side * 1.0, 1.0, 0.0]) / math.sqrt(2)
    return float(body @ away)


def clip_sign(torso, saw, side: int, which: str, q) -> int:
    _, _, hand = arm_chain(torso, side, q)
    _, ax = grip_frame(hand, side)
    return 1 if float(ax @ bar_line(saw, which)[1]) > 0 else -1


def solve_key(torso, saw, side: int, which: str, nom, sign=0, obs=None):
    """Best grip for a key pose: exact on the bar, fist pointing away from the engine, as
    close to the nominal angles as possible; tries several starting guesses."""
    nom = np.asarray(nom, float)
    starts = [nom] + [np.array([f, a, 0, e, ws, 0, 0], float) for f in (nom[0], 150, 60, -30)
                      for a in (10, 35) for e in (40, 80) for ws in (-90, 0, 90, 180)]
    best, fallback = None, None
    for n, q0 in enumerate(starts):
        if n and best is not None and best[0] > 0.6:
            break                           # the nominal start already gave a good grip
        q, _ = solve_arm(torso, saw, side, which, q0, nom, sign=sign, obs=obs)
        q, err = exact_grip(torso, saw, side, which, q)
        if fallback is None or err < fallback[0]:
            fallback = (err, q)
        if err > 1e-6 or (sign and clip_sign(torso, saw, side, which, q) != sign):
            continue
        upper, fore, hand = arm_chain(torso, side, q)
        score = away_score(hand, saw, side, which) - 0.002 * float(np.abs(q - nom).sum() / 7)
        if obs is not None:
            score -= 0.2 * sum(intrusion(obs, {"upper": upper, "fore": fore, "hand": hand},
                                         side))
        if best is None or score > best[0]:
            best = (score, q)
    if best is None:
        import warnings
        warnings.warn(f"no exact grip for side {side} on the {which} handle "
                      f"(best miss {fallback[0]:.1f} LDU)")
        return fallback[1]
    return best[1]

SAW_PTS = [np.array([x, y, z, 1.0]) for x in (-40, 0, 40, 56) for y in (0, -36, -72)
           for z in range(-180, 141, 20)]


def head_clearance(saw: np.ndarray, head: np.ndarray, crown: float) -> float:
    """How far the saw stays above the head's crown (LDU, head frame), over the head's
    footprint (6 x 7 studs, plus a stud's margin)."""
    inv = np.linalg.inv(head)
    gaps = []
    for p in SAW_PTS:
        h = inv @ (saw @ p)
        if -80 <= h[0] <= 80 and -116 <= h[2] <= 60:
            gaps.append(crown - h[1])
    return min(gaps) if gaps else 1e9
