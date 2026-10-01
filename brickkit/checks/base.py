from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from functools import cached_property
from typing import Callable

import numpy as np

from ..model.builder import Model, PlacedPart
from ..snaps.match import Connection, find_connections

ORDER = ["real_elements", "connections", "collisions", "buildability", "stability",
         "mechanism", "electrics", "technique"]


@dataclass
class CheckResult:
    name: str
    status: str                 # pass | warn | fail
    summary: str
    items: list = field(default_factory=list)
    stats: dict = field(default_factory=dict)


REGISTRY: dict[str, Callable] = {}


def register(name: str):
    def deco(fn):
        REGISTRY[name] = fn
        return fn
    return deco


class CheckContext:
    def __init__(self, model: Model, engine, config: dict):
        self.model = model
        self.engine = engine
        self.config = config
        self.catalog = engine.catalog
        self.geom = engine.geom
        self.shadow = engine.shadow
        self.collide = engine.collide
        self.placed = model.flatten()

    def world_connectors(self, placed: list[PlacedPart] | None = None):
        placed = self.placed if placed is None else placed
        return [[c.transformed(p.M) for c in self.shadow.connectors(p.part)] for p in placed]

    @cached_property
    def connections(self) -> list[Connection]:
        return (find_connections(self.world_connectors())
                + press_links(self.model, self.engine.press_collide, self.placed)
                + kit_links(self.placed))


NUDGES = [np.array(v, float) for v in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0),
                                       (0, 0, 1), (0, 0, -1))]


def touching(collide, part, M, other, Mo, reach: float) -> bool:
    """True if `part` at M would hit `other` at Mo when nudged `reach` LDU along one of its
    own axes (use unshrunk meshes: `Engine.press_collide`)."""
    for d in NUDGES:
        T = np.eye(4)
        T[:3, 3] = M[:3, :3] @ d * reach
        if collide.collide_pair(part, T @ M, other, Mo):
            return True
    return False


def press_pairs(collide, items, press: dict) -> list[tuple[int, int]]:
    """(i, j) pairs of items [(part, M)] held together by friction: `press` maps the index of
    each press-fit item to its reach (LDU); it is linked to every item it touches."""
    if not press:
        return []
    boxes = collide.aabbs(items)
    out = set()
    for i, reach in press.items():
        box = boxes[i]
        near = np.nonzero(np.all((boxes[:, 0] < box[1] + reach) & (box[0] - reach < boxes[:, 1]),
                                 axis=1))[0]
        for j in near:
            j = int(j)
            if j != i and (min(i, j), max(i, j)) not in out and touching(
                    collide, items[i][0], items[i][1], items[j][0], items[j][1], reach):
                out.add((min(i, j), max(i, j)))
    return sorted(out)


def press_links(model, collide, placed) -> list[Connection]:
    """Connections ("press") of the model's press-fit parts (`model.press_fit`) to the parts
    they touch."""
    press = {}
    for i, p in enumerate(placed):
        for t in p.tags:
            if t in model.press_fits:
                press[i] = max(press.get(i, 0.0), model.press_fits[t]["reach"])
    pairs = press_pairs(collide, [(p.part, p.M) for p in placed], press)
    return [Connection(i, j, None, None, "press", 0.0) for i, j in pairs]


def kit_links(placed) -> list[Connection]:
    """Pieces of one bought kit (a minifig's torso with its arms and hands, its hips and
    legs) come assembled: "kit" connections join them, whatever their snaps say."""
    first: dict[int, int] = {}
    out = []
    for i, p in enumerate(placed):
        k = getattr(p, "kit", None)
        if k is None:
            continue
        if k in first:
            out.append(Connection(first[k], i, None, None, "kit", 0.0))
        else:
            first[k] = i
    return out


def components(n: int, edges) -> list[list[int]]:
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in edges:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    groups: dict[int, list[int]] = defaultdict(list)
    for i in range(n):
        groups[find(i)].append(i)
    return sorted(groups.values(), key=len, reverse=True)


def describe(p: PlacedPart) -> str:
    return f"{p.part[:-4]} {p.color.name} (#{p.index}, {p.owner} step {p.local_step + 1})"


def status_of(items: list, default_fail: bool = True) -> str:
    if not items:
        return "pass"
    if any(i.get("severity", "fail" if default_fail else "warn") == "fail" for i in items):
        return "fail"
    return "warn"


def run_checks(ctx: CheckContext, names: list[str] | None = None) -> list[CheckResult]:
    names = names or ctx.config.get("enabled") or [n for n in ORDER if n in REGISTRY]
    return [REGISTRY[n](ctx, ctx.config.get(n, {})) for n in names]
