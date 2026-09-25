"""Cables must reach: route length (end part -> waypoints -> end part) <= cable length."""
from __future__ import annotations

import numpy as np

from .base import CheckResult, register


@register("electrics")
def check_electrics(ctx, cfg) -> CheckResult:
    m = ctx.model
    if not m.cables and not m.lights:
        return CheckResult("electrics", "pass", "no electrics in this model")
    items = []
    for light in m.lights:
        if len(m.find(light["part"], ctx.placed)) != 1:
            items.append({"light": light["name"], "problem": "light part not found (tag path)"})
    for cab in m.cables:
        a, b = m.find(cab["from"], ctx.placed), m.find(cab["to"], ctx.placed)
        if len(a) != 1 or len(b) != 1:
            items.append({"cable": cab["name"], "problem": "cable end parts not found"})
            continue
        pts = [a[0].M[:3, 3]] + [np.asarray(q) for q in cab["route"]] + [b[0].M[:3, 3]]
        need = float(sum(np.linalg.norm(pts[k + 1] - pts[k]) for k in range(len(pts) - 1)))
        if need > cab["length"]:
            items.append({"cable": cab["name"], "problem": f"needs {need:.0f} LDU of cable, "
                                                           f"has {cab['length']:.0f}"})
    return CheckResult("electrics", "fail" if items else "pass",
                       f"{len(m.lights)} light(s), {len(m.cables)} cable run(s); "
                       f"{len(items)} problem(s)", items)
