"""Minifigures in a model: `Model.minifig(...)` stands a figure up from its LDraw pieces and
records what is bought (catalog/minifig.py: a head, a torso assembly, a legs assembly, plus
the headwear and accessories, which are ordinary parts).

The figure's frame: the origin is on the top of the plate it stands on (studs' base), midway
between the two studs its feet go on (x = -10 and +10 LDU), facing -Z like everything else.
Standard minifigure geometry (LDraw / LDCad), in LDU: feet 28 below the legs' hip pins, the
hip pins 12 below the top of the hips, the hips 32 below the neck, the head on the neck stud
(24 tall); the foot holes sit 1.2 in front of the legs' axis, so the body stands 1.2 behind
the studs. The arms hang on the shoulder pins tilted out by 9.79 degrees and swing about
them; the hands sit on the wrists turned 45 degrees and twist about them; the hand's clip
holds a 3.2 mm bar (an accessory's), whose axis it lines up with its own."""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

import numpy as np

from ..catalog.minifig import HEAD, LEGS, TORSO, Component
from ..ldraw.matrix import rot, transform, translate

SHOULDER_TILT = math.degrees(math.asin(0.17007442))   # the torso's shoulder pin axes (LDCad)
SHOULDER = (15.552, 9.0, 0.0)          # left shoulder pin on the torso (x mirrored for right)
WRIST = (5.0, 18.8839, -9.8839)        # the left hand's wrist on its arm (x mirrored)
HAND_TILT = 45.0                       # a hand sits on its wrist turned this far
# the hand's clip (LDCad SNAP_CLP of 3820), in the hand's frame: centre and a frame whose -Y
# is the axis of the bar it holds
CLIP = np.array([[1, 0, 0, 0], [0, 0.9681, -0.2504, -0.82275], [0, 0.2504, 0.9681, -9.8951],
                 [0, 0, 0, 1]], float)
FOOT_Z = 1.2                           # the body stands this far behind its studs
HIPS_Y, TORSO_Y = -40.0, -72.0         # tops of the hips and of the torso (the neck's base)
BAR_RADIUS = 4.0


def _rx(deg):
    return transform((0, 0, 0), rot(x=deg))


def _ry(deg):
    return transform((0, 0, 0), rot(y=deg))


def _rz(deg):
    return transform((0, 0, 0), rot(z=deg))


@dataclass
class Pose:
    """Angles in degrees. Arms and legs: + swings them forward (an arm at 90 points ahead,
    a leg at 90 sits); hands: twist about the wrist; head: + turns it to the figure's own
    left (+X when it faces the front, -Z)."""
    head: float = 0.0
    arm_r: float = 0.0
    arm_l: float = 0.0
    hand_r: float = 0.0
    hand_l: float = 0.0
    leg_r: float = 0.0
    leg_l: float = 0.0

    @classmethod
    def of(cls, p) -> "Pose":
        if p is None:
            return cls()
        if isinstance(p, Pose):
            return p
        return cls(**dict(p))


def frames(pose: Pose) -> dict[str, np.ndarray]:
    """Each piece's frame in the figure's frame."""
    hips = translate(0, HIPS_Y, FOOT_Z)
    torso = translate(0, TORSO_Y, FOOT_Z)
    sx, sy, sz = SHOULDER
    wx, wy, wz = WRIST
    arm_r = torso @ translate(-sx, sy, sz) @ _rz(SHOULDER_TILT) @ _rx(-pose.arm_r)
    arm_l = torso @ translate(sx, sy, sz) @ _rz(-SHOULDER_TILT) @ _rx(-pose.arm_l)
    return {
        "hips": hips,
        "leg_r": hips @ translate(0, 12, 0) @ _rx(-pose.leg_r),
        "leg_l": hips @ translate(0, 12, 0) @ _rx(-pose.leg_l),
        "torso": torso,
        "arm_r": arm_r,
        "arm_l": arm_l,
        "hand_r": arm_r @ translate(-wx, wy, wz) @ _rx(HAND_TILT) @ _rz(pose.hand_r),
        "hand_l": arm_l @ translate(wx, wy, wz) @ _rx(HAND_TILT) @ _rz(pose.hand_l),
        "head": torso @ translate(0, -24, 0) @ _ry(-pose.head),
    }


def grip_up(arm: float = 0.0) -> float:
    """The arm swing that holds a bar upright in a hand twisted 0 (the hand's clip leans
    14.5 degrees off its wrist): use it as the arm angle when the accessory should stand
    up, e.g. a spear held at the side. It leans out with the arm, by the shoulder's 9.8
    degrees."""
    return 45.0 + math.degrees(math.atan2(0.2504, 0.9681)) + arm


@dataclass
class Held:
    """An accessory held in a hand's clip by a bar: `grip` is where along the bar (LDU from
    the bar's start, as LDCad gives it; default the middle of its 3.2 mm stretch), `spin`
    turns the accessory about
    the bar, `flip` holds it upside down (by default its top, LDraw's -Y, is on the thumb's
    side), `bar` picks one of several bars."""
    part: str
    color: object
    hand: str = "right"
    grip: float | None = None
    spin: float = 0.0
    flip: bool = False
    bar: int = 0

    @classmethod
    def of(cls, spec) -> "Held":
        if isinstance(spec, Held):
            return spec
        if isinstance(spec, dict):
            return cls(**spec)
        part, color, *rest = spec
        return cls(part, color, *rest)


def bars(shadow, part: str) -> list:
    """An accessory's bars a hand can hold (male cylinders of 3.2 mm, LDCad), longest first."""
    out = []
    for c in shadow.connectors(part):
        if c.kind == "cyl" and c.gender == "M" and any(
                s == "R" and abs(r - BAR_RADIUS) < 0.6 for s, r, _ in c.secs):
            out.append(c)
    return sorted(out, key=lambda c: -c.total_length())


def held_matrix(shadow, held: Held, hand: np.ndarray) -> np.ndarray:
    """Where the accessory goes (figure frame) so its bar lies in the hand's clip."""
    found = bars(shadow, held.part)
    if not found:
        raise ValueError(f"{held.part}: no 3.2 mm bar for a minifig hand to hold")
    c = found[min(held.bar, len(found) - 1)]
    # by default the middle of the bar's longest 3.2 mm stretch (a bottle by its neck, a
    # spyglass by its thin middle)
    thin = [(t0, t1) for t0, t1, s, r in c.intervals()
            if s == "R" and abs(r - BAR_RADIUS) < 0.6]
    lo, hi = max(thin, key=lambda iv: iv[1] - iv[0])
    t = (lo + hi) / 2 if held.grip is None else float(held.grip)
    # the bar's point at t (along its axis = the connector's -Y) goes to the clip's centre,
    # the bar's axis along the clip's; of the two ways round, the accessory's own up (LDraw
    # draws tools and weapons standing, -Y up) goes the way the thumb points, unless `flip`
    clip = hand @ CLIP
    ways = [clip @ _ry(held.spin) @ R @ translate(0, t, 0) @ np.linalg.inv(c.M)
            for R in (np.eye(4), _rz(180))]
    thumb = -clip[:3, 1]                       # the clip's axis: up when the bar stands upright
    ups = [float(np.dot(-M[:3, 1], thumb)) for M in ways]
    best = 0 if ups[0] >= ups[1] - 1e-9 else 1
    return ways[1 - best] if held.flip else ways[best]


@dataclass
class Minifig:
    """A minifigure placed in a model (what `Model.minifig` returns)."""
    name: str
    title: str
    head: Component
    torso: Component
    legs: Component
    headwear: list = field(default_factory=list)      # [(part, Color)]
    held: list = field(default_factory=list)          # [Held] (colours resolved)
    pose: Pose = field(default_factory=Pose)
    sub: object = None                                 # its Submodel
    tag: str = ""

    @property
    def components(self) -> list[Component]:
        return [self.head, self.torso, self.legs]

    @property
    def stand_ins(self) -> list[Component]:
        return [c for c in self.components if c.stand_in]

    def describe(self) -> list[str]:
        out = [f"{c.kind}: {c.rb_part} ({c.bl_part or 'no BrickLink number known'}) "
               f"{c.color.name} - {c.name}" + (" [stand-in render]" if c.stand_in else "")
               for c in self.components]
        out += [f"headwear: {p} {c.name}" for p, c in self.headwear]
        out += [f"in the {h.hand} hand: {h.part} {h.color.name}" for h in self.held]
        return out


def build_minifig(model, name: str, at=(0, 0, 0), rot3=None, *, head, torso, legs,
                  hair=None, hat=None, accessory=None, pose=None, parent=None, title: str = "",
                  tag: str | None = None, insert=None) -> Minifig:
    """See `Model.minifig`."""
    figs = model.catalog.figs

    def comp(kind, spec):
        if isinstance(spec, Component):
            return spec
        if isinstance(spec, (tuple, list)):
            return figs.component(kind, spec[0], model.resolve_color(spec[1]))
        return figs.component(kind, spec)

    c_head, c_torso, c_legs = comp(HEAD, head), comp(TORSO, torso), comp(LEGS, legs)
    pz = Pose.of(pose)
    F = frames(pz)
    title = title or name.replace("_", " ").title()
    sub = model.submodel(name, title)

    def kit(component: Component, label: str):
        k = model.submodel(f"{name}_{component.kind}",
                           f"{label} {component.bl_part or component.rb_part}")
        k.kit = component
        for piece in component.pieces:
            k.place(piece.part, piece.color, F[piece.slot][:3, 3], F[piece.slot][:3, :3])
        return k

    sub.step("Legs", view="above")
    sub.use(kit(c_legs, "Legs"))
    sub.step("Torso")
    sub.use(kit(c_torso, "Torso"))
    sub.step("Head")
    hp = c_head.pieces[0]
    sub.place(hp.part, hp.color, F["head"][:3, 3], F["head"][:3, :3], buy=c_head, tag="head")
    fig_tag = tag if tag is not None else name
    # hair and hats fit snugly over the head (LDraw's meshes overlap a little there)
    model.fits.append((f"{fig_tag}/head", f"{fig_tag}/headwear"))
    sub.fits.append(("head", "headwear"))
    headwear = []
    for spec, caption in ((hair, "Hair"), (hat, "Hat")):
        if spec is None:
            continue
        part, colour = (spec, None) if isinstance(spec, str) else spec
        col = model.resolve_color(colour if colour is not None else "Black")
        sub.step(caption)
        p = sub.place(part, col, F["head"][:3, 3], F["head"][:3, :3], tag="headwear")
        headwear.append((p.part, col))
    held = []
    specs = [] if accessory is None else (
        accessory if isinstance(accessory, list) else [accessory])
    for spec in specs:
        h = Held.of(spec)
        h = replace(h, color=model.resolve_color(h.color), part=model.canonical(h.part))
        M = held_matrix(model.catalog.shadow, h, F["hand_r" if h.hand == "right" else "hand_l"])
        sub.step(f"Into the {h.hand} hand")
        sub.place(h.part, h.color, M[:3, 3], M[:3, :3], tag="held")
        held.append(h)
    fig = Minifig(name, title, c_head, c_torso, c_legs, headwear, held, pz, sub, fig_tag)
    model.minifigs.append(fig)
    host = parent if parent is not None else model.main
    host.use(sub, at, rot3, tag=fig.tag, insert=insert)
    return fig
