"""Can every step be built? Each new part (or sub-assembly) must slide into place along one
of its connection axes (or its insertion hint) without hitting what is already built, and
each submodel must be one piece at the end of every step. Clips and hinges snap on (their
fingers flex) and Technic pins click in (the split, flared tip compresses in the hole), so the
parts a unit clips, hinges or pins onto never block its path."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import numpy as np

from ..ldraw.matrix import translate
from ..model.builder import Placement
from ..snaps.match import find_connections
from .base import CheckResult, components, register

SNAP_KINDS = ("clip", "hinge", "pin")   # connections that flex as they go on (see docstring)


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


def _lowest(unit: Unit) -> float:
    """Largest y (LDraw +Y is down) of a unit's part origins: lower parts are built first."""
    return max(M[1, 3] for _, M in unit.parts)


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
        snaps: dict[int, set] = defaultdict(set)     # unit -> parts it snaps onto
        for c in find_connections(wc):
            ua, ub = owner[c.a], owner[c.b]
            if ua != ub:
                links[ua].append((ub, c.ca.axis, c.overlap))
                links[ub].append((ua, c.ca.axis, c.overlap))
                if c.kind in SNAP_KINDS:
                    snaps[ua].add(c.b)
                    snaps[ub].add(c.a)
        parts_of = defaultdict(list)
        for i, ui in enumerate(owner):
            parts_of[ui].append(i)
        bottoms = defaultdict(lambda: -1e9)                  # lowest point (max y) per unit
        for i, ui in enumerate(owner):
            bottoms[ui] = max(bottoms[ui], float(boxes_all[i][1][1]))
        built: list[int] = []
        built_parts: list[int] = []

        def add(ui: int):
            built.append(ui)
            built_parts.extend(parts_of[ui])

        for s in range(sub.n_steps):
            pending = [ui for ui, u in enumerate(units) if u.step == s]

            def attached(ui):
                bset = set(built)
                return any(o in bset for o, _, _ in links[ui])

            while pending:
                progress = False
                for ui in list(pending):                     # in the order they are listed
                    u = units[ui]
                    if u.insert is None and not attached(ui):
                        continue                             # loose for now: set down later
                    if u.insert is None and any(
                            units[o].insert is None and not attached(o)
                            and _lowest(units[o]) > _lowest(u) + 0.5 for o in pending if o != ui):
                        continue                             # a lower loose part goes first
                    tried += 1
                    blockers = [i for i in built_parts if i not in snaps[ui]]
                    if _insertable(ctx, u, ui, links, set(built), flat, blockers, boxes_all,
                                   stride, min_travel):
                        pending.remove(ui)
                        add(ui)
                        progress = True
                if progress:
                    continue
                free = [ui for ui in pending if units[ui].insert is None and not attached(ui)]
                if not free:
                    break
                ui = max(free, key=lambda u: _lowest(units[u]))  # set down the lowest loose part
                pending.remove(ui)
                add(ui)
            for ui in pending:
                items.append({"submodel": sub.name, "step": s + 1, "part": units[ui].label,
                              "problem": "no clear path to push it into place"})
                add(ui)
            bset = set(built)
            index = {u: k for k, u in enumerate(built)}
            edges = [(index[a], index[b]) for a in built for b, _, _ in links[a] if b in bset]
            comps = components(len(built), edges)
            if len(comps) > 1 and s < sub.n_steps - 1:
                # loose pieces lying on the table next to the model are fine mid-build (a
                # plate layer laid out before the crossing layer locks it); not at the end
                table = max(bottoms[ui] for ui in built)
                comps = [c for c in comps
                         if not any(abs(bottoms[built[i]] - table) < 0.5 for i in c)] or [[]]
                comps = [[]] + [c for c in comps if c]
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
