"""Chainsaw Face: a posable brick-built figure of a masked chainsaw slasher, about 30 cm
(12 in) tall on a display stand, chainsaw in hand, in the style of LEGO's big football
figures.

Units: LDU (stud 20, plate 8, brick 24), -Y up, the figure faces -Z. The stand's underside is
at y = 0; see kin.py for the skeleton and the poses, and the other modules for the parts:
stand.py, legs.py, body.py (hips, apron, torso), head.py, arms.py, saw.py.

The static model is the hero pose (t = 0): the chainsaw raised overhead in both fists.
pose(t) swings it down across his hips (t = 1): see poses.py."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import kin  # noqa: E402
from arms import build_arm, build_forearm, build_hand, build_upper_arm  # noqa: E402
from body import (BIB_TOP, R_PANEL, SKIRT_TOP, build_bib, build_pelvis,  # noqa: E402
                  build_skirt, build_torso)
from head import build_head  # noqa: E402
from legs import build_leg, build_shin, build_shoe, build_thigh  # noqa: E402
from saw import build_saw  # noqa: E402
from stand import build_stand  # noqa: E402

from poses import GROUPS, LEG_GROUPS, frames, performance, pose  # noqa: E402


# ------------------------------------------------------------------------------ build
def use_M(sub, child, M, tag="", insert=None):
    M = np.asarray(M, float)
    return sub.use(child, tuple(M[:3, 3]), M[:3, :3], tag=tag, insert=insert)


def build(model):
    f0 = frames(0.0)
    legs = {sd: kin.solve_leg(sd) for sd in (1, -1)}

    # sub-assemblies
    shoe = build_shoe(model)
    stand = build_stand(model, [kin.SHOES[1], kin.SHOES[-1]], post_top=kin.PELVIS_Y + 48)
    leg_subs = {}
    for sd in (1, -1):
        n = "l" if sd > 0 else "r"
        thigh = build_thigh(model, f"thigh_{n}", sd)
        shin = build_shin(model, f"shin_{n}", sd)
        (thigh_M, shin_M), q = legs[sd]
        leg = build_leg(model, f"leg_{n}", sd, thigh, shin, np.linalg.inv(shin_M) @ thigh_M)
        leg_subs[sd] = (leg, shin_M)
    pelvis = build_pelvis(model)
    skirt = build_skirt(model)
    pelvis.step("Press the apron onto the studs at the front of the hips", view="above")
    use_M(pelvis, skirt, _panel_M(SKIRT_TOP, 80), insert=(0, 0, -1))
    torso = build_torso(model)
    bib = build_bib(model)
    torso.step("Press the apron's bib onto the studs on the belly")
    use_M(torso, bib, _panel_M(BIB_TOP, 80), insert=(0, 0, -1))
    head = build_head(model)
    saw = build_saw(model)
    arms = {}
    for sd in (1, -1):
        n = "l" if sd > 0 else "r"
        up = build_upper_arm(model, f"upper_arm_{n}", sd)
        fo = build_forearm(model, f"forearm_{n}", sd, "bracelet" if sd > 0 else "skin")
        ha = build_hand(model, f"hand_{n}", sd)
        U, F, H = f0[f"upper_arm_{n}"], f0[f"forearm_{n}"], f0[f"hand_{n}"]
        arms[sd] = (build_arm(model, f"arm_{n}", sd, up, fo, ha, U, F, H), U)

    main = model.main
    main.step("The display stand")
    main.use(stand, tag="stand")
    main.step("Shoes on the studs either side")
    for sd in (1, -1):
        use_M(main, shoe, kin.shoe_matrix(sd), tag="shoe_l" if sd > 0 else "shoe_r")
    for sd in (1, -1):
        leg, shin_M = leg_subs[sd]
        main.step(f"Pop the {'left' if sd > 0 else 'right'} leg's ankle ball into its shoe")
        use_M(main, leg, shin_M, tag="leg_l" if sd > 0 else "leg_r", insert=(0, -1, 0))
    main.step("Lower the hips onto both hip balls")
    use_M(main, pelvis, kin.PELVIS, tag="pelvis", insert=(0, -1, 0))
    main.step("Push two long pins through the post into the back of the hips")
    for y in (58, 82):
        main.place("32556b", "Tan", (0, kin.PELVIS_Y + y, 70), _rot_z_axis(), insert=(0, 0, 1),
                   tag="stand")
    main.step("The torso on the waist turntable")
    use_M(main, torso, f0["torso"], tag="torso", insert=(0, -1, 0))
    main.step("The head on the neck ball")
    use_M(main, head, f0["head"], tag="head", insert=(0, -1, 0))
    for sd in (1, -1):
        arm, U = arms[sd]
        main.step(f"The {'left' if sd > 0 else 'right'} arm: its socket clicks onto the "
                  f"shoulder ball")
        use_M(main, arm, U, tag="arm_l" if sd > 0 else "arm_r", insert=(sd, 0, 0))
    main.step("Put the chainsaw in his fists: the handles clip into the fists")
    use_M(main, saw, f0["saw"], tag="saw", insert=(0, -1, 0))

    for g in GROUPS + LEG_GROUPS:
        model.moving_group(g, g)
    model.pose = pose
    model.meta["mechanism_name"] = "Pose"
    model.meta["mechanism_labels"] = ["chainsaw raised", "chainsaw lowered"]
    model.meta["turntable"] = {"cycles": 1}
    model.extra_checks.append(check_balance)
    # the showreel's opening: the sunset chainsaw dance (see poses.py)
    model.meta["performance"] = performance
    model.meta["performance_info"] = {"hide_tags": ["stand"], "ground_y": kin.SHOE_Y,
                                      "pivot": [0.0, 0.0], "cycle_s": 2.5}


def balance(ctx, ts=np.linspace(0.0, 1.0, 13)) -> list[tuple[float, float]]:
    """(t, margin) of the centre of mass over the base's footprint as the pose moves: the
    margin is its distance inside the footprint's edge as a fraction of the footprint
    centre's (1 = at the centre, 0 = on the edge)."""
    from scipy.spatial import ConvexHull

    from brickkit.geometry.mass import part_mass
    from brickkit.ldraw.matrix import apply
    model = ctx.model
    local, pts = [], []
    for p in ctx.placed:
        mesh = ctx.geom.mesh(p.part)
        g, c, _ = part_mass(mesh, p.color.is_trans, ctx.catalog.mass_override(p.part))
        local.append((g, c))
        if len(mesh.tris):
            pts.append(apply(p.M, mesh.tris.reshape(-1, 3)))
    allp = np.concatenate(pts)
    base = allp[allp[:, 1] > allp[:, 1].max() - 0.5][:, [0, 2]]
    hull = ConvexHull(base)
    eq = hull.equations
    d_cen = float((-(eq[:, :2] @ base[hull.vertices].mean(0) + eq[:, 2])).min())
    out = []
    total = sum(g for g, _ in local)
    for t in ts:
        placed = model.flatten(pose=model.pose(float(t)))
        com = sum(g * apply(p.M, [c])[0] for (g, c), p in zip(local, placed)) / total
        d = float((-(eq[:, :2] @ com[[0, 2]] + eq[:, 2])).min())
        out.append((float(t), d / d_cen))
    return out


def check_balance(ctx) -> list[dict]:
    """The figure must stay balanced on its stand in every pose, not only the static one."""
    return [{"pose": round(t, 3), "problem": f"centre of mass only {m:.0%} from the edge of "
                                             "the base at this pose"}
            for t, m in balance(ctx) if m < 0.25]


def _rot_z_axis():
    from brickkit.ldraw.matrix import rot
    return rot(y=90)


def _panel_M(top: float, depth: float, up: bool = False) -> np.ndarray:
    """Placement of a flat panel (built studs up, cells along -z from its top edge) turned to
    face forward with its plates' undersides on studs at z = -depth, top edge at y = top."""
    M = np.eye(4)
    M[:3, :3] = R_PANEL
    M[:3, 3] = (0, top, -depth)
    return M
