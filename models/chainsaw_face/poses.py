"""The two key poses and the motion between them.

t = 0 (the static model, the hero pose): the chainsaw raised high overhead in both fists.
t = 1: the chainsaw swung down in front of him, held across his hips.

The hero pose is solved by inverse kinematics (kin.solve_key): the saw is placed overhead,
and each fist's clip must sit exactly on its handle bar, the fist pointing away from the
engine. Both shoulder axles lie on one line across the chest, so turning both arms by the
same angle about it (the shoulders' flexion) carries the fists and the saw together as one
rigid body: both grips stay exact at every t without solving anything. From t = 0 to 1 the
arms swing forward and down by SWING degrees, the waist turns a little to his right and the
head drops to look at the saw."""
from __future__ import annotations

from functools import lru_cache

import numpy as np

import kin
from head import TOP as HEAD_TOP

HERO = dict(waist=0.0, head=(-12.0, 5.0, 0.0), saw=((-30, -875, -30), 105.0, 15.0, 0.0),
            arm_nom={1: (147, 2, 16, 35, 13, -84, 16), -1: (157, 4, 16, 43, -170, 24, 22)})
LOWERED = dict(swing=-120.0, waist=-12.0, head=(10.0, -10.0, 0.0))
ARMS = {-1: "front", 1: "rear"}   # right fist on the front handle, left on the rear
HEAD_CLEARANCE = 20              # the raised saw stays this far above the head's crown


def ease(t: float) -> float:
    return t * t * (3 - 2 * t)


@lru_cache(maxsize=None)
def hero() -> dict:
    """The hero pose: torso, saw and both arms' joint angles."""
    torso = kin.torso_matrix(HERO["waist"])
    head = kin.head_matrix(torso, *HERO["head"])
    saw = kin.saw_matrix(*HERO["saw"])
    assert kin.head_clearance(saw, head, HEAD_TOP) >= HEAD_CLEARANCE, \
        "the raised saw is too close to the head"
    obs = kin.obstacles(torso, head, saw)
    q = {sd: kin.solve_key(torso, saw, sd, ARMS[sd], HERO["arm_nom"][sd], 0, obs)
         for sd in (1, -1)}
    for sd in (1, -1):
        err = kin.exact_grip(torso, saw, sd, ARMS[sd], q[sd])[1]
        assert err < 1e-6, f"no exact grip for side {sd} (miss {err:.2f} LDU)"
    return dict(torso=torso, saw=saw, q=q)


def shoulder_swing(theta: float) -> np.ndarray:
    """Turn by theta about the shoulder line (torso frame; + = over the head and back)."""
    sy = kin.SHOULDER[1]
    return kin.T((0, sy, 0)) @ kin.R("x", -theta) @ kin.T((0, -sy, 0))


def upper_spec(t: float):
    s = ease(t)
    waist = HERO["waist"] + (LOWERED["waist"] - HERO["waist"]) * s
    head = tuple(x + (y - x) * s for x, y in zip(HERO["head"], LOWERED["head"]))
    return waist, head, LOWERED["swing"] * s


@lru_cache(maxsize=None)
def frames(t: float) -> dict:
    """World matrix of every moving segment at pose t (plus the joint angles, '_q_*')."""
    H = hero()
    waist, head, theta = upper_spec(float(t))
    torso = kin.torso_matrix(waist)
    carry = torso @ shoulder_swing(theta) @ np.linalg.inv(H["torso"])
    out = {"torso": torso, "head": kin.head_matrix(torso, *head), "saw": carry @ H["saw"]}
    for sd in (1, -1):
        n = "l" if sd > 0 else "r"
        q = np.array(H["q"][sd], float)
        q[0] += theta                       # the swing is the shoulders' flexion
        up, fore, hand = kin.arm_chain(torso, sd, q)
        out[f"upper_arm_{n}"], out[f"forearm_{n}"], out[f"hand_{n}"] = up, fore, hand
        out[f"_q_{n}"] = q
    return out


GROUPS = ["torso", "head", "upper_arm_l", "forearm_l", "hand_l", "upper_arm_r", "forearm_r",
          "hand_r", "saw"]


def pose(t: float) -> dict:
    t = float(t)
    if t == 0.0:
        return {g: np.eye(4) for g in GROUPS}
    f0, ft = frames(0.0), frames(t)
    return {g: ft[g] @ np.linalg.inv(f0[g]) for g in GROUPS}


# ------------------------------------------------------------------------------ the dance
# The sunset chainsaw dance: he swings the roaring chainsaw overhead in wide
# arcs. One loop (u in [0, 1), u = 0 and 1 the same): the waist twists the raised saw from
# one side to the other and back; as it goes, the arms, fists and saw swing together about
# the shoulder line (both shoulders turn about the same line, so both fists stay on their
# handles exactly): high overhead as it passes his face, swung forward and down at each side,
# so the saw's tip draws a big arc over his head. The head is thrown back and follows the
# saw; the knees dip at the low end of each arc (the hips drop and the legs are re-solved so
# the shoes stay put). The whole-body spin is left to the video. The waist is a turntable, so
# the torso twists but doesn't lean.
DANCE_WAIST = 40.0          # degrees each way
DANCE_ARC = 40.0            # arms + saw swung forward at each side (degrees)
DANCE_NOD = (-12.0, 2.0)    # head thrown back: mean, bob (degrees)
DANCE_DIP = 4.0             # hips drop at each end of the swing (LDU)
DANCE_LOOK = 0.25           # the head turns after the saw by this much of the waist's turn
LEG_GROUPS = ["pelvis", "thigh_l", "shin_l", "thigh_r", "shin_r"]
ARM_GROUPS = ["upper_arm_l", "forearm_l", "hand_l", "upper_arm_r", "forearm_r", "hand_r",
              "saw"]


@lru_cache(maxsize=None)
def _rest_legs():
    out = {}
    for sd in (1, -1):
        (thigh, shin), q = kin.solve_leg(sd)
        n = "l" if sd > 0 else "r"
        out[f"thigh_{n}"], out[f"shin_{n}"], out[f"_q_{n}"] = thigh, shin, q
    return out


def dance_frames(u: float) -> dict:
    """World matrices of every moving segment at dance phase u."""
    import math
    ph = 2 * math.pi * (u % 1.0)
    f0 = frames(0.0)
    rest = _rest_legs()
    waist = DANCE_WAIST * math.sin(ph)
    rock = -DANCE_ARC * (1 - math.cos(2 * ph)) / 2
    dip = DANCE_DIP * (1 - math.cos(2 * ph)) / 2
    nod = DANCE_NOD[0] - DANCE_NOD[1] * math.cos(2 * ph)
    pelvis = kin.T((0, dip, 0)) @ kin.PELVIS
    torso = pelvis @ kin.R("y", waist)
    carry = torso @ shoulder_swing(rock) @ np.linalg.inv(f0["torso"])
    out = {"pelvis": pelvis, "torso": torso,
           "head": kin.head_matrix(torso, nod, DANCE_LOOK * waist, 0.0)}
    for g in ARM_GROUPS:
        out[g] = carry @ f0[g]
    for sd in (1, -1):
        n = "l" if sd > 0 else "r"
        (thigh, shin), _ = kin.solve_leg(sd, pelvis, rest[f"_q_{n}"])
        out[f"thigh_{n}"], out[f"shin_{n}"] = thigh, shin
    return out


def performance(u: float) -> dict:
    """The dance as pose deltas (like pose(t)): {group: 4x4 applied on top of the model}."""
    f0 = frames(0.0)
    rest = {**_rest_legs(), "pelvis": kin.PELVIS}
    cur = dance_frames(float(u))
    return {g: cur[g] @ np.linalg.inv(rest[g] if g in rest else f0[g]) for g in cur}
