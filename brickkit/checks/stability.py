"""Centre of mass over the footprint of the lowest parts, and tipping angle."""
from __future__ import annotations

import math

import numpy as np
from scipy.spatial import ConvexHull, QhullError

from ..geometry.mass import part_mass
from ..ldraw.matrix import apply
from .base import CheckResult, register


@register("stability")
def check_stability(ctx, cfg) -> CheckResult:
    if not ctx.placed:
        return CheckResult("stability", "pass", "empty model")
    masses, cents, pts = [], [], []
    approx = 0
    for p in ctx.placed:
        mesh = ctx.geom.mesh(p.part)
        g, c, a = part_mass(mesh, p.color.is_trans, ctx.catalog.mass_override(p.part))
        approx += a
        masses.append(g)
        cents.append(apply(p.M, [c])[0])
        if len(mesh.tris):
            pts.append(apply(p.M, mesh.tris.reshape(-1, 3)))
    masses, cents = np.array(masses), np.array(cents)
    total = float(masses.sum())
    com = (masses[:, None] * cents).sum(0) / total
    allp = np.concatenate(pts)
    ymax = allp[:, 1].max()                       # +Y is down: the lowest point
    base = allp[allp[:, 1] > ymax - 0.5][:, [0, 2]]
    stats = {"mass_g": total, "com": com.tolist(), "approx_parts": int(approx)}
    try:
        hull = ConvexHull(base)
    except (QhullError, ValueError):
        return CheckResult("stability", "fail", "footprint is a point or a line", [
            {"problem": "the model stands on a point or a line"}], stats)
    eq = hull.equations                            # outward normals: n.x + c <= 0 inside
    d_com = float((-(eq[:, :2] @ com[[0, 2]] + eq[:, 2])).min())
    cen = base[hull.vertices].mean(0)
    d_cen = float((-(eq[:, :2] @ cen + eq[:, 2])).min())
    inside = d_com > 0
    margin = d_com / d_cen if d_cen > 0 else 0.0
    height = float(ymax - com[1])
    tilt = math.degrees(math.atan2(max(d_com, 0.0), max(height, 1e-6)))
    stats.update({"margin": margin, "tip_angle_deg": tilt, "com_height_ldu": height})
    items = []
    if not inside:
        items.append({"severity": "fail", "problem": "centre of mass is outside the base"})
    elif tilt < cfg.get("min_tilt_deg", 10):
        items.append({"severity": "fail", "problem": f"tips over at only {tilt:.1f} degrees"})
    elif margin < cfg.get("min_margin", 0.25):
        items.append({"severity": "warn", "problem": f"centre of mass only {margin:.0%} "
                                                     "from the edge of the base"})
    status = "fail" if any(i["severity"] == "fail" for i in items) else (
        "warn" if items else "pass")
    return CheckResult("stability", status,
                       f"about {total:.0f} g; centre of mass {'inside' if inside else 'OUTSIDE'} "
                       f"the base ({max(margin, 0):.0%} margin); tips at {tilt:.1f} deg",
                       items, stats)
