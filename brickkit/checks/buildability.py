"""Can every step be built? Each new part (or sub-assembly) must slide into place along one
of its connection axes (or its insertion hint) without hitting what is already built, and
each submodel must be one piece at the end of every step."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import numpy as np

from ..ldraw.matrix import translate
from ..model.builder import Placement
from ..snaps.match import find_connections
from .base import CheckResult, components, register


@dataclass
class Unit:
    step: int
    label: str
    parts: list          # [(part, M in submodel frame)]
    insert: tuple | None


def _units(sub) -> list[Unit]:
    units = []
    for it in sub.items:
        if isinstance(it, Placement):
            units.append(Unit(it.step, f"{it.part[:-4]} {it.color.name}", [(it.part, it.M)],
                              it.insert))
        else:
            parts = [(p, it.M @ M) for p, _, M in it.sub.flatten_local()]
            units.append(Unit(it.step, f"sub-assembly {it.sub.name}", parts, it.insert))
    return units


def _unique(dirs):
    out, seen = [], set()
    for d in dirs:
        d = np.asarray(d, float)
        d = d / np.linalg.norm(d)
        k = tuple(np.round(d, 3))
        if k not in seen:
            seen.add(k)
            out.append(d)
    return out


def _clear(ctx, unit: Unit, d, items, boxes, stride: float, travel: float) -> bool:
    for k in np.arange(stride, travel + 1e-6, stride):
        T = translate(*(d * k))
        for part, M in unit.parts:
            if ctx.collide.hits(part, T @ M, items, boxes):
                return False
    return True


@register("buildability")
def check_buildability(ctx, cfg) -> CheckResult:
    stride = float(cfg.get("stride", 2.0))
    min_travel = float(cfg.get("travel", 24.0))
    items: list[dict] = []
    tried = 0
    for sub in ctx.model.submodels.values():
        if not sub.items:
            continue
        units = _units(sub)
        flat, owner = [], []
        for ui, u in enumerate(units):
            for part, M in u.parts:
                flat.append((part, M))
                owner.append(ui)
        boxes_all = ctx.collide.aabbs(flat)
        wc = [[c.transformed(M) for c in ctx.shadow.connectors(part)] for part, M in flat]
        links: dict[int, list] = defaultdict(list)
        for c in find_connections(wc):
            ua, ub = owner[c.a], owner[c.b]
            if ua != ub:
                links[ua].append((ub, c.ca.axis, c.overlap))
                links[ub].append((ua, c.ca.axis, c.overlap))
        parts_of = defaultdict(list)
        for i, ui in enumerate(owner):
            parts_of[ui].append(i)
        built: list[int] = []
        built_parts: list[int] = []

        def add(ui: int):
            built.append(ui)
            built_parts.extend(parts_of[ui])

        for s in range(sub.n_steps):
            pending = [ui for ui, u in enumerate(units) if u.step == s]
            while pending:
                bset = set(built)
                # units already attached to the build, or with an explicit insertion direction,
                # are tried in the order they are listed; others wait until nothing else fits
                attached = [ui for ui in pending if any(o in bset for o, _, _ in links[ui])
                            or units[ui].insert is not None]
                progress = False
                for ui in attached:
                    tried += 1
                    if _insertable(ctx, units[ui], ui, links, set(built), flat, built_parts,
                                   boxes_all, stride, min_travel):
                        pending.remove(ui)
                        add(ui)
                        progress = True
                if progress:
                    continue
                free = [ui for ui in pending if ui not in attached]
                if not free:
                    break
                # nothing attached can go in yet: set down one unattached unit and retry
                pending.remove(free[0])
                add(free[0])
            for ui in pending:
                items.append({"submodel": sub.name, "step": s + 1, "part": units[ui].label,
                              "problem": "no clear path to push it into place"})
                add(ui)
            bset = set(built)
            index = {u: k for k, u in enumerate(built)}
            edges = [(index[a], index[b]) for a in built for b, _, _ in links[a] if b in bset]
            comps = components(len(built), edges)
            if len(comps) > 1:
                items.append({"submodel": sub.name, "step": s + 1,
                              "part": ", ".join(units[built[i]].label for i in comps[1][:5]),
                              "problem": f"step leaves {len(comps)} loose pieces"})
    return CheckResult("buildability", "fail" if items else "pass",
                       f"{tried} insertions tried across {len(ctx.model.submodels)} submodel(s); "
                       f"{len(items)} problem(s)", items, {"insertions": tried})


def _insertable(ctx, unit, ui, links, built, flat, built_parts, boxes_all, stride, min_travel):
    if not built_parts:
        return True
    dirs, depth = [], 0.0
    for other, axis, ov in links[ui]:
        if other in built:
            dirs += [axis, -axis]
            depth = max(depth, ov)
    if unit.insert is not None:
        dirs.insert(0, np.asarray(unit.insert, float))
    if not dirs:
        return True   # not attached yet; the loose-piece check decides
    items = [flat[i] for i in built_parts]
    boxes = boxes_all[built_parts]
    travel = max(min_travel, depth + 8.0)
    return any(_clear(ctx, unit, d, items, boxes, stride, travel) for d in _unique(dirs))
