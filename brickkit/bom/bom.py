from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
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


@lru_cache(maxsize=1)
def pick_a_brick_data() -> dict:
    """What Pick a Brick sells, learned from uploads (data/pick_a_brick.json)."""
    f = Path(__file__).resolve().parents[1] / "data" / "pick_a_brick.json"
    return json.loads(f.read_text()) if f.exists() else {}


def choose_element(ids) -> str:
    """The LEGO element ID for a part/colour: the newest, but not one from a block Pick a Brick
    doesn't stock when an older ID exists, and swapped for the one Pick a Brick accepted when
    an upload showed it rejects ours (data/pick_a_brick.json)."""
    if not ids:
        return ""
    d = pick_a_brick_data()
    ranges = d.get("avoid_ranges", [])
    num = lambda e: int(e) if str(e).isdigit() else 0
    ok = [e for e in ids if not any(lo <= num(e) <= hi for lo, hi in ranges)] or list(ids)
    best = max(ok, key=num)
    return d.get("use_instead", {}).get(best, best)


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
                             choose_element(e.element_ids if e else []),
                             bool(e is None or e.rare), catalog.bl_type(part)))
    lines.sort(key=lambda l: (l.color.name, l.ldraw_part))
    return lines


@dataclass
class HardwareLine:
    """A bought non-LEGO item (not on BrickLink): a placed stand-in part or `model.hardware`."""
    id: str
    name: str
    description: str
    qty: int
    low: float                   # USD each, rough
    high: float
    where: str


def build_hardware(placed, catalog, items=()) -> list[HardwareLine]:
    """Hardware list: placed stand-in parts (data/hardware.json; parts that are `part_of` an
    item, such as a clock's hands, count with it) plus a model's `hardware_items`."""
    counts = Counter(p.part for p in placed if catalog.hardware_counts(p.part))
    lines = []
    for part, qty in sorted(counts.items()):
        h = catalog.hardware_info(part)
        lines.append(HardwareLine(h["id"], h["name"], h["description"], qty,
                                  float(h["price"][0]), float(h["price"][1]), h["where"]))
    for it in items:
        lines.append(HardwareLine("", it["name"], it.get("description", ""), int(it["qty"]),
                                  float(it["price"][0]), float(it["price"][1]),
                                  it.get("where", "")))
    return lines


def write_hardware_csv(lines: list[HardwareLine], path) -> None:
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["qty", "item", "description", "price_each_usd_low", "price_each_usd_high",
                    "where_to_buy", "stand_in_part"])
        for l in lines:
            w.writerow([l.qty, l.name, l.description, f"{l.low:.2f}", f"{l.high:.2f}", l.where,
                        l.id])


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
        gone = set(pick_a_brick_data().get("unavailable", []))
        for l in lines:
            if l.element_id and l.element_id not in gone:     # the rest: BrickLink
                w.writerow([l.element_id, l.qty])
