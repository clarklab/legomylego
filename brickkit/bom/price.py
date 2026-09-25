"""Rough price estimate for a parts list: a low-high range per line from price bands by part
type (data/price_bands.json), scaled up for transparent colours and for part/colour
combinations that appear in few sets. Not market data: for a real quote, upload
bricklink_wanted.xml to a BrickLink wanted list."""
from __future__ import annotations

import json
from dataclasses import dataclass

from .. import paths
from .bom import BomLine


@dataclass
class PriceLine:
    line: BomLine
    low: float        # per piece, USD
    high: float
    basis: str


def _bands() -> dict:
    return json.loads((paths.DATA_DIR / "price_bands.json").read_text())


def estimate(lines: list[BomLine], catalog) -> list[PriceLine]:
    bands = _bands()
    out = []
    for l in lines:
        o = bands["overrides"].get(l.ldraw_part)
        if o:
            out.append(PriceLine(l, o["low"], o["high"], o.get("note", "fixed")))
            continue
        name = f" {l.name.lower()} "
        rule = next(r for r in bands["rules"] if r["match"] in name)
        f, basis = 1.0, rule["match"].strip() or "other"
        if "trans" in l.color.name.lower():
            f *= bands["colour_factor"]["trans"]
            basis += ", transparent"
        e = catalog.element(l.ldraw_part + ".dat", l.color)
        sets = e.set_count if e else 0
        for s in bands["scarcity"]:
            if sets <= s["max_sets"]:
                f *= s["factor"]
                basis += f", in {sets} set(s)"
                break
        out.append(PriceLine(l, rule["low"] * f, rule["high"] * f, basis))
    return out


def write_estimate_md(name: str, priced: list[PriceLine], path) -> tuple[float, float]:
    low = sum(p.low * p.line.qty for p in priced)
    high = sum(p.high * p.line.qty for p in priced)
    rows = sorted(priced, key=lambda p: -(p.low + p.high) * p.line.qty)
    md = [f"# {name}: price estimate", "",
          f"**Roughly ${low:,.0f} - ${high:,.0f}** for {sum(p.line.qty for p in priced):,} "
          f"pieces in {len(priced)} lines, new parts on BrickLink, before shipping.", "",
          "This is a rough range from typical per-piece prices by part type (see "
          "`brickkit/data/price_bands.json`), scaled up for transparent colours and for "
          "part/colour combinations that appeared in few sets. It is not live market data.", "",
          "For a real quote, upload `bricklink_wanted.xml` as a BrickLink Wanted List and use "
          "Easy Buy. Parts still made can also be ordered from LEGO Pick a Brick with "
          "`pick_a_brick.csv`.", "",
          "| Qty | Part | Colour | Each (USD) | Line (USD) | Basis |",
          "|---:|---|---|---:|---:|---|"]
    for p in rows:
        l = p.line
        md.append(f"| {l.qty} | {l.bl_part} {l.name} | {l.color.name} | "
                  f"{p.low:.2f}-{p.high:.2f} | {p.low * l.qty:.2f}-{p.high * l.qty:.2f} | "
                  f"{p.basis} |")
    md.append("")
    path.write_text("\n".join(md))
    return low, high
