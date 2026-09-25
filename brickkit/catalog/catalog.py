from __future__ import annotations

import json
from dataclasses import dataclass

from .. import paths
from ..ldraw.library import LDrawLibrary, part_id
from .colors import Color, ColorTable
from .rebrickable import RBIndex, load_index


def _data(name: str) -> dict:
    return json.loads((paths.DATA_DIR / name).read_text())


@dataclass
class ElementInfo:
    part: str
    color: Color
    element_ids: list[str]
    last_year: int
    set_count: int

    @property
    def rare(self) -> bool:
        return self.set_count < 3 or self.last_year < 2016


class Catalog:
    def __init__(self, ldraw: LDrawLibrary, rb: RBIndex, part_map: dict, bl_colors: dict,
                 aliases: dict, masses: dict):
        self.ldraw = ldraw
        self.rb = rb
        self.part_map = part_map
        self.masses = masses
        self.colors = ColorTable(ldraw.colors, rb.colors, bl_colors, aliases)

    @classmethod
    def load(cls, ldraw: LDrawLibrary, rb_dir, cache_path) -> "Catalog":
        return cls(ldraw, load_index(rb_dir, cache_path), _data("part_map.json"),
                   _data("bricklink_colors.json"), _data("color_aliases.json"),
                   _data("masses.json"))

    def color(self, key) -> Color:
        return self.colors.get(key)

    def _pm(self, part: str) -> dict:
        return self.part_map.get(part_id(part), {})

    def rb_part(self, part: str) -> str:
        return self._pm(part).get("rebrickable", part_id(part))

    def bl_part(self, part: str) -> str:
        return self._pm(part).get("bricklink", self.rb_part(part))

    def in_bom(self, part: str) -> bool:
        return self._pm(part).get("bom", True)

    def mass_override(self, part: str) -> float | None:
        return self.masses.get(part_id(part))

    def part_name(self, part: str) -> str:
        row = self.rb.parts.get(self.rb_part(part))
        return row[0] if row else self.ldraw.description(part)

    def element(self, part: str, color) -> ElementInfo | None:
        c = self.color(color)
        if c.rb_id is None:
            return None
        key = (self.rb_part(part), c.rb_id)
        ids = self.rb.elements.get(key, [])
        sets = self.rb.set_count.get(key, 0)
        if not ids and not sets:
            return None
        ids = sorted(ids, key=lambda e: int(e) if e.isdigit() else 0)
        return ElementInfo(part_id(part), c, ids, self.rb.last_year.get(key, 0), sets)

    def substitutes(self, part: str, color, limit: int = 6) -> list[str]:
        c = self.color(color)
        rbp = self.rb_part(part)
        out = []
        others = sorted(self.rb.part_colors.get(rbp, ()),
                        key=lambda cid: -self.rb.set_count.get((rbp, cid), 0))
        for cid in others:
            if cid != c.rb_id and len(out) < limit // 2 + 1:
                out.append(f"{rbp} in {self.rb.colors[cid]['name']} "
                           f"({self.rb.set_count.get((rbp, cid), 0)} sets)")
        for alt in sorted(self.rb.related.get(rbp, ())):
            if (alt, c.rb_id) in self.rb.elements or self.rb.set_count.get((alt, c.rb_id)):
                out.append(f"{alt} in {c.name}")
        return out[:limit]
