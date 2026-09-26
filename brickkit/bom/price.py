"""Price estimate for a parts list, a low-high range per line.

With BrickLink API credentials set up (see live_price.py), lines are priced from BrickLink's
price guide on the day: low = average price sold over the last six months, high = average
asking price of what's for sale now (new, USD, weighted by quantity). Lines BrickLink has no
data for, or every line without credentials, fall back to rough price bands by part type
(data/price_bands.json), scaled up for transparent colours and for part/colour combinations
that appear in few sets."""
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
    live: bool = False


def _bands() -> dict:
    return json.loads((paths.DATA_DIR / "price_bands.json").read_text())


def _live_line(l: BomLine, live: dict) -> PriceLine | None:
    got = live["prices"].get((l.bl_type, l.bl_part, l.color.bl_id if l.bl_type == "P" else None))
    if not got:
        return None
    stock, sold = got.get("stock", {}), got.get("sold", {})
    now = stock.get("avg") if stock.get("ok") else None
    past = sold.get("avg") if sold.get("ok") else None
    if not now and not past:
        return None
    low, high = sorted((past or now, now or past))
    return PriceLine(l, low, high, f"BrickLink {live['day']}: sold {past and f'{past:.3f}' or 'n/a'}"
                                   f", for sale {now and f'{now:.3f}' or 'n/a'}", live=True)


def estimate(lines: list[BomLine], catalog, live: dict | None = None) -> list[PriceLine]:
    bands = _bands()
    out = []
    for l in lines:
        if live:
            pl = _live_line(l, live)
            if pl:
                out.append(pl)
                continue
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


def summary(priced: list[PriceLine], day: str | None = None) -> dict:
    """Totals and a one-line description of where the numbers come from."""
    n_live = sum(p.live for p in priced)
    low = sum(p.low * p.line.qty for p in priced)
    high = sum(p.high * p.line.qty for p in priced)
    if n_live and day:
        note = (f"BrickLink price guide, {day}: {n_live} of {len(priced)} part lines priced "
                "live (six-month sold average to current asking average, new, USD)"
                + ("; the rest estimated from typical prices." if n_live < len(priced) else "."))
    else:
        note = "A rough range from typical BrickLink prices per part type, not live market data."
    return {"low": round(low, 2), "high": round(high, 2), "currency": "USD", "note": note,
            "source": "bricklink" if n_live else "estimate", "date": day if n_live else None,
            "live_lines": n_live, "lines": len(priced)}


def write_estimate_md(name: str, priced: list[PriceLine], path, day: str | None = None
                      ) -> tuple[float, float]:
    s = summary(priced, day)
    low, high = s["low"], s["high"]
    rows = sorted(priced, key=lambda p: -(p.low + p.high) * p.line.qty)
    if s["source"] == "bricklink":
        intro = [f"**${low:,.0f} - ${high:,.0f}** for {sum(p.line.qty for p in priced):,} "
                 f"pieces in {len(priced)} lines, new parts on BrickLink, before shipping. "
                 f"Priced {day}.", "",
                 f"From BrickLink's price guide on {day}, new condition, USD, weighted by "
                 "quantity: the low end is the average sold over the last six months, the high "
                 "end the average asking price of what's for sale now. "
                 f"{s['live_lines']} of {s['lines']} lines priced live"
                 + ("; the rest use typical price bands (`brickkit/data/price_bands.json`)."
                    if s["live_lines"] < s["lines"] else "."), ""]
    else:
        intro = [f"**Roughly ${low:,.0f} - ${high:,.0f}** for {sum(p.line.qty for p in priced):,} "
                 f"pieces in {len(priced)} lines, new parts on BrickLink, before shipping.", "",
                 "This is a rough range from typical per-piece prices by part type (see "
                 "`brickkit/data/price_bands.json`), scaled up for transparent colours and for "
                 "part/colour combinations that appeared in few sets. It is not live market "
                 "data: set up BrickLink API credentials (see `brickkit/bom/live_price.py`) "
                 "for dated prices.", ""]
    md = [f"# {name}: price estimate", ""] + intro + [
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
