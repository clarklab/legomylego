from __future__ import annotations

import json
import re
from dataclasses import dataclass

from .. import paths
from ..ldraw.library import LDrawLibrary, normalize, part_id
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

    def canonical(self, part: str) -> str:
        """Follow LDraw '~Moved to X' aliases to the current file name."""
        name = normalize(part)
        for _ in range(5):
            m = re.match(r"~Moved to\s+(\S+)", self.ldraw.description(name))
            if not m:
                break
            name = normalize(m.group(1))
        return name

    def rb_part(self, part: str) -> str:
        pm = self._pm(part)
        if "rebrickable" in pm:
            return pm["rebrickable"]
        pid = part_id(part)
        if pid in self.rb.parts:
            return pid
        m = re.match(r"^(\d+)[a-z]$", pid)
        if m and m.group(1) in self.rb.parts:
            return m.group(1)
        return pid

    def search(self, text: str, color=None, limit: int = 40) -> list[tuple]:
        """(sets, part, name, has_ldraw) for Rebrickable parts whose name contains every word."""
        words = text.lower().split()
        c = self.color(color) if color else None
        rows = []
        for pnum, (name, _) in self.rb.parts.items():
            low = name.lower()
            if not all(w in low for w in words):
                continue
            if c is not None:
                key = (pnum, c.rb_id)
                sets = self.rb.set_count.get(key, 0)
                if not sets and key not in self.rb.elements:
                    continue
            else:
                sets = max((self.rb.set_count.get((pnum, cid), 0)
                            for cid in self.rb.part_colors.get(pnum, ())), default=0)
            rows.append((sets, pnum, name, self.ldraw.resolve(pnum) is not None))
        rows.sort(key=lambda r: -r[0])
        return rows[:limit]

    def bl_part(self, part: str) -> str:
        return self._pm(part).get("bricklink", self.rb_part(part))

    def bl_type(self, part: str) -> str:
        return self._pm(part).get("bricklink_type", "P")

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
