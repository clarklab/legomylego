"""Building-technique warnings: brittle transparent clips, moving transparent parts, banned
parts, and parts whose geometry makes the collision check less precise."""
from __future__ import annotations

from ..ldraw.library import part_id
from .base import CheckResult, describe, register, status_of


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
    banned = set(cfg.get("banned_parts", []))
    for p in ctx.placed:
        if part_id(p.part) in banned:
            items.append({"severity": "fail", "part": describe(p), "problem": "banned part"})
    return CheckResult("technique", status_of(items, default_fail=False),
                       f"{len(items)} note(s)", items)
