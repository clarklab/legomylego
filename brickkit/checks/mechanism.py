"""Sweep the model's pose function: no collisions, linkage stays connected, gears mesh."""
from __future__ import annotations

import re

import numpy as np

from ..snaps.match import find_connections
from .base import CheckResult, components, describe, register

TEETH_RE = re.compile(r"(\d+)\s*Tooth", re.I)
PITCH = 1.25   # LEGO gears are module 1 mm: pitch radius = teeth * 0.5 mm = teeth * 1.25 LDU


def _teeth(ctx, part: str) -> int | None:
    name = ctx.catalog.part_name(part)
    if "worm" in name.lower():
        return 8
    m = TEETH_RE.search(name)
    return int(m.group(1)) if m else None


def _axis(ctx, p) -> np.ndarray:
    conns = [c.transformed(p.M) for c in ctx.shadow.connectors(p.part)]
    ax = [c for c in conns if c.kind == "cyl" and any(s[0] == "A" for s in c.secs)]
    c = ax[0] if ax else (conns[0] if conns else None)
    return c.axis if c is not None else p.M[:3, 1]


def _gear_items(ctx) -> list[dict]:
    items = []
    for ta, tb, kind in ctx.model.gear_pairs:
        a, b = ctx.model.find(ta, ctx.placed), ctx.model.find(tb, ctx.placed)
        if len(a) != 1 or len(b) != 1:
            items.append({"problem": f"gear pair {ta}/{tb}: tag must match exactly one part"})
            continue
        a, b = a[0], b[0]
        na, nb = _teeth(ctx, a.part), _teeth(ctx, b.part)
        if na is None or nb is None:
            items.append({"problem": f"gear pair {ta}/{tb}: unknown tooth count"})
            continue
        aa, ab = _axis(ctx, a), _axis(ctx, b)
        d = b.M[:3, 3] - a.M[:3, 3]
        want = PITCH * (na + nb)
        cross = np.cross(aa, ab)
        if kind == "spur":
            if np.linalg.norm(cross) > 1e-3:
                items.append({"problem": f"gear pair {ta}/{tb}: spur gear axes not parallel"})
                continue
            dist = float(np.linalg.norm(d - np.dot(d, aa) * aa))
        elif kind in ("worm", "bevel"):
            if abs(float(np.dot(aa, ab))) > 1e-3:
                items.append({"problem": f"gear pair {ta}/{tb}: {kind} axes not perpendicular"})
                continue
            dist = float(abs(np.dot(d, cross)) / np.linalg.norm(cross))
            if kind == "bevel":
                want = 0.0
        else:
            continue
        if abs(dist - want) > 0.6:
            items.append({"problem": f"gear pair {ta}/{tb}: centres {dist:.1f} LDU apart, "
                                     f"need {want:.1f} for {na}T + {nb}T"})
    return items


@register("mechanism")
def check_mechanism(ctx, cfg) -> CheckResult:
    m = ctx.model
    items = _gear_items(ctx)
    for fn in m.extra_checks:
        items += fn(ctx)
    if m.pose is None:
        return CheckResult("mechanism", "fail" if items else "pass",
                           "no moving parts defined" if not items else f"{len(items)} problem(s)",
                           items)
    n = int(cfg.get("poses", 24))
    base_pieces = len(components(len(ctx.placed), [(c.a, c.b) for c in ctx.connections]))
    for t in np.linspace(0.0, 1.0, n):
        placed = m.flatten(pose=m.pose(float(t)))
        moving = {i for i, p in enumerate(placed) if m.group_of(p) is not None}
        for i, j in ctx.collide.pairs([(p.part, p.M) for p in placed], only=moving):
            items.append({"pose": round(float(t), 3), "a": describe(placed[i]),
                          "b": describe(placed[j]), "problem": "parts collide while moving"})
        conns = find_connections(ctx.world_connectors(placed))
        pieces = len(components(len(placed), [(c.a, c.b) for c in conns]))
        if pieces > base_pieces:
            items.append({"pose": round(float(t), 3),
                          "problem": f"model falls apart into {pieces} pieces at this pose"})
    return CheckResult("mechanism", "fail" if items else "pass",
                       f"{n} poses swept for {len(m.groups)} moving group(s); "
                       f"{len(m.gear_pairs)} gear pair(s); {len(items)} problem(s)", items,
                       {"poses": n})
