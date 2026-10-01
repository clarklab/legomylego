from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from .. import paths
from ..ldraw.library import LDrawLibrary, normalize, part_id
from .colors import Color, ColorTable
from .rebrickable import RBIndex, load_index
from .xref import LDrawXref, load_xref


def _fig_index(rb_dir, cache):
    from .minifig import load_fig_index
    return load_fig_index(rb_dir, cache)


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
                 aliases: dict, masses: dict, hardware: dict | None = None,
                 approximate: dict | None = None):
        self.ldraw = ldraw
        self.rb = rb
        self.part_map = part_map
        self.masses = masses
        self.hardware = {k: v for k, v in (hardware or {}).items() if not k.startswith("_")}
        self.approximate = {k: v for k, v in (approximate or {}).items()
                            if not k.startswith("_")}
        self.colors = ColorTable(ldraw.colors, rb.colors, bl_colors, aliases)

    @classmethod
    def load(cls, ldraw: LDrawLibrary, rb_dir, cache_path) -> "Catalog":
        cat = cls(ldraw, load_index(rb_dir, cache_path), _data("part_map.json"),
                  _data("bricklink_colors.json"), _data("color_aliases.json"),
                  _data("masses.json"), _data("hardware.json"), _data("approximate.json"))
        cache = Path(cache_path).parent
        cat._xref_loader = lambda: load_xref(ldraw.root, cache / "ldraw_xref.pkl")
        cat._fig_loader = lambda: _fig_index(rb_dir, cache / "rb_figs.pkl")
        return cat

    @cached_property
    def xref(self) -> LDrawXref:
        """Rebrickable / BrickLink numbers cited in LDraw headers (printed parts, minifigs)."""
        loader = getattr(self, "_xref_loader", None)
        return loader() if loader else LDrawXref({}, {}, {}, {})

    @property
    def shadow(self):
        """The LDCad snap library (the Engine's), for placing minifig accessories."""
        loader = getattr(self, "_shadow_loader", None)
        if loader is None:
            raise RuntimeError("catalog has no snap library (load it through an Engine)")
        return loader()

    @cached_property
    def figs(self):
        """Minifigure components: heads, torso and legs assemblies (catalog/minifig.py)."""
        from .minifig import FigCatalog
        return FigCatalog(self, self.xref, getattr(self, "_fig_loader", None))

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
        got = self.xref.rb_for(pid)          # a printed part: the number its header cites
        if got and got in self.rb.parts:
            return got
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
        pm = self._pm(part)
        if "bricklink" in pm:
            return pm["bricklink"]
        if self.approximate.get(part_id(part), {}).get("bricklink"):
            return self.approximate[part_id(part)]["bricklink"]
        if part_id(part) not in self.rb.parts and self.xref.bl_for(part_id(part)):
            return self.xref.bl_for(part_id(part))     # a printed part: its header's number
        return self.rb_part(part)

    def bl_type(self, part: str) -> str:
        return self._pm(part).get("bricklink_type", "P")

    def in_bom(self, part: str) -> bool:
        """On the LEGO parts lists (non-LEGO hardware has its own list)."""
        return self._pm(part).get("bom", True) and not self.is_hardware(part)

    def is_approximate(self, part: str) -> bool:
        """A real LEGO part LDraw has no model of, drawn with brickkit's own approximate model
        (data/approximate.json, data/ldraw/parts): on the parts lists under its real number,
        checked like any part; only its 3D shape is approximate."""
        return part_id(part) in self.approximate and self.ldraw.is_custom(part)

    def is_hardware(self, part: str) -> bool:
        """A stand-in for a bought non-LEGO item (data/hardware.json), not a LEGO element."""
        return part_id(part) in self.hardware

    def hardware_info(self, part: str) -> dict:
        """The hardware item a stand-in part is counted as: {id, name, description, price,
        where}; a 'part_of' stand-in (a clock's hands) points at its item."""
        pid = part_id(part)
        info = self.hardware.get(pid, {})
        if "part_of" in info:
            return self.hardware_info(info["part_of"])
        return {"id": pid, "name": info.get("name", self.part_name(part)),
                "description": info.get("description", ""),
                "price": tuple(info.get("price", (0.0, 0.0))), "where": info.get("where", "")}

    def hardware_counts(self, part: str) -> bool:
        """True if each placed copy of this stand-in is one item bought (not 'part_of')."""
        return self.is_hardware(part) and "part_of" not in self.hardware[part_id(part)]

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
