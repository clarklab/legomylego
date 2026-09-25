from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

from ..catalog.colors import Color
from ..ldraw.library import part_id


@dataclass
class BomLine:
    ldraw_part: str
    rb_part: str
    bl_part: str
    name: str
    color: Color
    qty: int
    element_id: str
    rare: bool
    bl_type: str = "P"          # BrickLink item type: P part, S set (e.g. 8870 light unit)


def build_bom(placed, catalog, extras=()) -> list[BomLine]:
    """Parts list from placed parts plus a model's `extras` [(part, Color, qty, note)]."""
    counts = Counter((p.part, p.color.ldraw) for p in placed if catalog.in_bom(p.part))
    for part, color, qty, _ in extras:
        counts[(part, color.ldraw)] += qty
    lines = []
    for (part, code), qty in counts.items():
        c = catalog.color(code)
        e = catalog.element(part, c)
        lines.append(BomLine(part_id(part), catalog.rb_part(part), catalog.bl_part(part),
                             catalog.part_name(part), c, qty,
                             e.element_ids[-1] if e and e.element_ids else "",
                             bool(e is None or e.rare), catalog.bl_type(part)))
    lines.sort(key=lambda l: (l.color.name, l.ldraw_part))
    return lines


def write_parts_csv(lines: list[BomLine], path) -> None:
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["qty", "part", "name", "colour", "ldraw_colour", "rebrickable_part",
                    "rebrickable_colour", "bricklink_part", "bricklink_colour", "element_id",
                    "rare"])
        for l in lines:
            w.writerow([l.qty, l.ldraw_part, l.name, l.color.name, l.color.ldraw, l.rb_part,
                        l.color.rb_id, l.bl_part, l.color.bl_id, l.element_id, int(l.rare)])


def write_bricklink_xml(lines: list[BomLine], path) -> None:
    out = ["<INVENTORY>"]
    for l in lines:
        colour = (f"<COLOR>{l.color.bl_id}</COLOR>"
                  if l.color.bl_id is not None and l.bl_type == "P" else "")
        out.append(f"<ITEM><ITEMTYPE>{l.bl_type}</ITEMTYPE><ITEMID>{escape(l.bl_part)}</ITEMID>"
                   f"{colour}"
                   f"<MINQTY>{l.qty}</MINQTY></ITEM>")
    out.append("</INVENTORY>")
    Path(path).write_text("\n".join(out) + "\n")


def write_pick_a_brick_csv(lines: list[BomLine], path) -> None:
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["elementId", "quantity"])
        for l in lines:
            if l.element_id:
                w.writerow([l.element_id, l.qty])
