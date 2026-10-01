"""Building-technique warnings: brittle transparent clips, moving transparent parts, banned
parts, parts whose geometry makes the collision check less precise, locking hinges set
between their clicks, and parts resting on studs their snap data has no holes for."""
from __future__ import annotations

import math

import numpy as np

from ..ldraw.library import part_id
from .base import CheckResult, describe, register, status_of

CLICK_GROUPS = ("lckhng",)      # LDCad's group for LEGO's locking ("click") hinges
CLICK_STEP = 22.5               # degrees between a locking hinge's clicks
CLICK_TOL = 1.0                 # degrees either side of a click that still counts as on it


def hinge_angle(axis, Ra, Rb) -> float:
    """Angle (degrees) part b's frame is turned from part a's about a hinge axis: between an
    axis of each frame that lies across the hinge."""
    axis = np.asarray(axis, float) / np.linalg.norm(axis)

    def across(R):
        k = int(np.argmin(np.abs(R.T @ axis)))
        v = R[:, k] - np.dot(R[:, k], axis) * axis
        return v / np.linalg.norm(v)
    ua, ub = across(Ra), across(Rb)
    return math.degrees(math.atan2(float(np.dot(axis, np.cross(ua, ub))), float(np.dot(ua, ub))))


def off_click(angle: float, step: float) -> float:
    """How far (degrees) an angle is from the nearest multiple of `step`."""
    r = angle % step
    return min(r, step - r)


def click_hinge_items(ctx, step: float, tol: float, groups) -> list:
    items = []
    for c in ctx.connections:
        if c.kind != "hinge" or c.ca.group not in groups:
            continue
        pa, pb = ctx.placed[c.a], ctx.placed[c.b]
        a = hinge_angle(c.ca.axis, pa.M[:3, :3], pb.M[:3, :3])
        if off_click(a, step) > tol:
            near = step * round(a / step)
            items.append({"severity": "warn", "part": f"{describe(pa)} / {describe(pb)}",
                          "problem": f"locking hinge at {a:.1f} degrees: it only holds at its "
                                     f"clicks, every {step:g} degrees (nearest {near:g})"})
    return items


def _is_stud(c) -> bool:
    return (c.kind == "cyl" and c.gender == "M" and c.secs
            and c.secs[0][0] in ("R", "S") and abs(c.secs[0][1] - 6) < 0.7)


def holeless_items(ctx) -> list:
    """Parts with studs on top but no stud holes underneath in their snap data that sit on
    another part's studs: they look seated but connect to nothing there (a gap in the snap
    data, to fill with an overlay in brickkit/data/shadow)."""
    up = np.array([0.0, -1.0, 0.0])
    cand = []
    for i, p in enumerate(ctx.placed):
        cs = ctx.shadow.connectors(p.part)
        bottom = ctx.geom.mesh(p.part).bbox[1][1]
        tops = any(_is_stud(c) and np.allclose(c.axis, up, atol=1e-6) for c in cs)
        # anything that connects through its underside (stud holes either way up, a pin)
        under = any(c.kind == "cyl" and abs(c.axis[1]) > 0.999 and
                    bottom - 6.5 <= c.origin[1] <= bottom + 1 for c in cs)
        if tops and not under:
            cand.append(i)
    if not cand:
        return []
    items_all = [(p.part, p.M) for p in ctx.placed]
    boxes = ctx.collide.aabbs(items_all)
    out, seen = [], set()
    for i in cand:
        p = ctx.placed[i]
        lo, hi = ctx.geom.mesh(p.part).bbox
        inv = np.linalg.inv(p.M)
        b0, b1 = boxes[i]
        near = np.nonzero(np.all((boxes[:, 0] < b1 + 4) & (b0 - 4 < boxes[:, 1]), axis=1))[0]
        found = False
        for j in near:
            if j == i or found:
                continue
            for c in ctx.shadow.connectors(ctx.placed[j].part):
                if not _is_stud(c):
                    continue
                w = c.transformed(inv @ ctx.placed[j].M)
                if not np.allclose(w.axis, up, atol=1e-3):
                    continue
                x, y, z = w.origin
                if abs(y - hi[1]) < 0.6 and lo[0] + 2 < x < hi[0] - 2 and lo[2] + 2 < z < hi[2] - 2:
                    found = True
                    break
        if found and p.part not in seen:
            seen.add(p.part)
            out.append({"severity": "warn", "part": describe(p),
                        "problem": "sits on studs but its snap data has no stud holes, so it "
                                   "connects to nothing there (add a shadow overlay)"})
    return out


@register("technique")
def check_technique(ctx, cfg) -> CheckResult:
    items = []
    for c in ctx.connections:
        if c.kind == "clip":
            p = ctx.placed[c.a if c.ca.kind == "clp" else c.b]
            if p.color.is_trans:
                items.append({"severity": "warn", "part": describe(p),
                              "problem": "clip on a transparent part (brittle plastic)"})
    for part in sorted({p.part for p in ctx.placed}):
        if not ctx.geom.mesh(part).certified:
            items.append({"severity": "warn", "part": part_id(part),
                          "problem": "geometry not BFC-certified; collision check less precise"})
    if ctx.model.groups:
        for p in ctx.placed:
            g = ctx.model.group_of(p)
            tag = ctx.model.groups.get(g)
            # a whole moving body, or a captive clear slider, is meant to move as it is
            if g and tag != "*" and tag not in ctx.model.captive_tags and p.color.is_trans:
                items.append({"severity": "warn", "part": describe(p),
                              "problem": "transparent part in a moving group"})
    items += click_hinge_items(ctx, float(cfg.get("click_step", CLICK_STEP)),
                               float(cfg.get("click_tolerance", CLICK_TOL)),
                               tuple(cfg.get("click_groups", CLICK_GROUPS)))
    items += holeless_items(ctx)
    banned = set(cfg.get("banned_parts", []))
    for p in ctx.placed:
        if part_id(p.part) in banned:
            items.append({"severity": "fail", "part": describe(p), "problem": "banned part"})
    return CheckResult("technique", status_of(items, default_fail=False),
                       f"{len(items)} note(s)", items)
