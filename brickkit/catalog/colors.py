from __future__ import annotations

import re
from dataclasses import dataclass


def norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower().replace("grey", "gray"))


@dataclass(frozen=True)
class Color:
    name: str            # Rebrickable-style display name, e.g. "Trans-Light Blue"
    ldraw: int           # LDraw colour code
    rgb: str             # "#RRGGBB"
    alpha: int           # 255 = opaque
    rb_id: int | None    # Rebrickable colour id
    bl_id: int | None    # BrickLink colour id

    @property
    def is_trans(self) -> bool:
        return self.alpha < 255


class ColorTable:
    def __init__(self, ldraw_colors: dict, rb_colors: dict, bl_ids: dict, aliases: dict):
        rb_by_norm = {norm(r["name"]): r for r in rb_colors.values()}
        self.by_code: dict[int, Color] = {}
        self.by_norm: dict[str, Color] = {}
        for code, lc in ldraw_colors.items():
            n = aliases.get(norm(lc.name), norm(lc.name))
            rb = rb_by_norm.get(n)
            name = rb["name"] if rb else lc.name.replace("_", " ")
            col = Color(name, code, lc.rgb, lc.alpha, int(rb["id"]) if rb else None,
                        bl_ids.get(norm(name)))
            self.by_code[code] = col
            self.by_norm.setdefault(norm(name), col)
            self.by_norm.setdefault(norm(lc.name), col)

    def get(self, key) -> Color:
        if isinstance(key, Color):
            return key
        if isinstance(key, int) or (isinstance(key, str) and key.strip().isdigit()):
            return self.by_code[int(key)]
        c = self.by_norm.get(norm(key))
        if c is None:
            raise KeyError(f"unknown colour {key!r}")
        return c
