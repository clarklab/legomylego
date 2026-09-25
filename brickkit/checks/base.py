from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from functools import cached_property
from typing import Callable

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
        return find_connections(self.world_connectors())


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
