"""Builder API. Positions in LDU, -Y up. Colours are palette roles or real colour names."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from ..catalog.colors import Color
from ..ldraw.library import normalize
from ..ldraw.matrix import transform


@dataclass
class Placement:
    part: str
    color: Color
    M: np.ndarray
    step: int
    tag: str = ""
    note: str = ""
    insert: tuple | None = None   # optional insertion direction hint (submodel frame)


@dataclass
class Use:
    sub: "Submodel"
    M: np.ndarray
    step: int
    tag: str = ""
    note: str = ""
    insert: tuple | None = None


@dataclass
class PlacedPart:
    index: int
    part: str
    color: Color
    M: np.ndarray
    path: tuple        # submodel names from the root to the owner
    tags: tuple        # tags of every Use on the path, then the placement's own tag
    owner: str
    local_step: int
    build_order: int   # index into Model.instruction_order() when the part joins the model

    @property
    def tag_path(self) -> str:
        return "/".join(self.tags)


class Submodel:
    def __init__(self, model: "Model", name: str, title: str = ""):
        self.model = model
        self.name = name
        self.title = title or name.replace("_", " ").capitalize()
        self.items: list[Placement | Use] = []
        self.captions: list[str] = [""]

    @property
    def current_step(self) -> int:
        return len(self.captions) - 1

    @property
    def n_steps(self) -> int:
        return len(self.captions)

    def step(self, caption: str = "") -> int:
        """Start a new step (reuses the current one if it is still empty)."""
        if any(it.step == self.current_step for it in self.items):
            self.captions.append(caption)
        elif caption:
            self.captions[-1] = caption
        return self.current_step

    def place(self, part: str, color, pos=(0, 0, 0), rot=None, *, tag: str = "",
              note: str = "", insert=None) -> Placement:
        p = Placement(normalize(part), self.model.resolve_color(color), transform(pos, rot),
                      self.current_step, tag, note, insert)
        self.items.append(p)
        return p

    def use(self, sub: "Submodel", pos=(0, 0, 0), rot=None, *, tag: str = "", note: str = "",
            insert=None) -> Use:
        u = Use(sub, transform(pos, rot), self.current_step, tag, note, insert)
        self.items.append(u)
        return u

    def flatten_local(self) -> list[tuple[str, Color, np.ndarray]]:
        out = []
        for it in self.items:
            if isinstance(it, Placement):
                out.append((it.part, it.color, it.M))
            else:
                out += [(p, c, it.M @ M) for p, c, M in it.sub.flatten_local()]
        return out


class Model:
    def __init__(self, name: str, slug: str, palette: dict, catalog):
        self.name = name
        self.slug = slug
        self.palette = dict(palette)
        self.catalog = catalog
        self.submodels: dict[str, Submodel] = {}
        self.main = self.submodel(slug, name)
        self.groups: dict[str, str] = {}                 # group name -> tag
        self.pose: Callable[[float], dict] | None = None  # t in [0,1] -> {group: 4x4 world}
        self.gear_pairs: list[tuple[str, str, str]] = []  # (tag path a, tag path b, kind)
        self.lights: list[dict] = []
        self.cables: list[dict] = []
        self.extra_checks: list[Callable] = []           # fn(ctx) -> list of issue dicts
        self.meta: dict = {}

    def submodel(self, name: str, title: str = "") -> Submodel:
        if name in self.submodels:
            raise ValueError(f"submodel {name!r} already exists")
        s = Submodel(self, name, title)
        self.submodels[name] = s
        return s

    def resolve_color(self, key) -> Color:
        if isinstance(key, Color):
            return key
        return self.catalog.color(self.palette.get(key, key))

    # mechanisms and electrics -------------------------------------------------
    def moving_group(self, name: str, tag: str) -> None:
        self.groups[name] = tag

    def group_of(self, p: PlacedPart) -> str | None:
        for t in reversed(p.tags):
            for g, tag in self.groups.items():
                if t == tag:
                    return g
        return None

    def gear_pair(self, a: str, b: str, kind: str = "spur") -> None:
        self.gear_pairs.append((a, b, kind))

    def light(self, name: str, tag_path: str) -> None:
        self.lights.append({"name": name, "part": tag_path})

    def cable(self, name: str, start: str, end: str, length: float, route=()) -> None:
        self.cables.append({"name": name, "from": start, "to": end, "length": float(length),
                            "route": [tuple(map(float, p)) for p in route]})

    # flattening ---------------------------------------------------------------
    def instruction_order(self) -> list[tuple[str, int]]:
        order, built = [], set()

        def build(sub: Submodel):
            for s in range(sub.n_steps):
                for it in sub.items:
                    if it.step == s and isinstance(it, Use) and it.sub.name not in built:
                        build(it.sub)
                order.append((sub.name, s))
            built.add(sub.name)

        build(self.main)
        return order

    def flatten(self, pose: dict | None = None) -> list[PlacedPart]:
        order = {k: i for i, k in enumerate(self.instruction_order())}
        out: list[PlacedPart] = []

        def walk(sub: Submodel, W, path, tags, top):
            for it in sub.items:
                t = tags + ((it.tag,) if it.tag else ())
                bo = top if top is not None else order[(sub.name, it.step)]
                if isinstance(it, Placement):
                    out.append(PlacedPart(len(out), it.part, it.color, W @ it.M,
                                          path + (sub.name,), t, sub.name, it.step, bo))
                else:
                    walk(it.sub, W @ it.M, path + (sub.name,), t, bo)

        walk(self.main, np.eye(4), (), (), None)
        if pose:
            for p in out:
                g = self.group_of(p)
                if g in pose:
                    p.M = pose[g] @ p.M
        return out

    def find(self, tag_path: str, placed: list[PlacedPart]) -> list[PlacedPart]:
        return [p for p in placed if p.tag_path == tag_path or p.tag_path.endswith("/" + tag_path)]
