"""What a parts list costs: a BrickLink price and a Pick a Brick price.

BrickLink (with API credentials, see live_price.py): each line at the average it sold for new
over the last six months (or, with no sales, the average asking price now), USD, weighted by
quantity. Pick a Brick (pab_price.py): each LEGO element at its price on lego.com's US shop that
day; a line Pick a Brick doesn't sell is named, not guessed.

Each line also keeps a low-high range: the BrickLink sold and asking averages, or, for a line
BrickLink has no data for and on a machine without credentials, rough price bands by part type
(data/price_bands.json), scaled up for transparent colours and for part/colour combinations that
appear in few sets. The range is a fallback; the two prices are what is shown."""
from __future__ import annotations

import json
from dataclasses import dataclass

from .. import paths
from .bom import BomLine, HardwareLine


@dataclass
class PriceLine:
    line: BomLine
    low: float        # per piece, USD
    high: float
    basis: str
    live: bool = False
    bricklink: float | None = None    # per piece, USD: six-month sold average (else asking now)
    pab: float | None = None          # per piece on Pick a Brick, USD; None: not sold there
    bestseller: bool | None = None    # Pick a Brick's Bestseller range (one fast parcel)


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
                                   f", for sale {now and f'{now:.3f}' or 'n/a'}", live=True,
                     bricklink=past or now)


def estimate(lines: list[BomLine], catalog, live: dict | None = None,
             pab: dict | None = None) -> list[PriceLine]:
    out = _estimate(lines, catalog, live)
    if pab:
        for p in out:
            got = pab["prices"].get(p.line.element_id) if p.line.element_id else None
            if got and got.get("ok"):
                p.pab, p.bestseller = got["usd"], got.get("bestseller")
    return out


def _estimate(lines: list[BomLine], catalog, live: dict | None = None) -> list[PriceLine]:
    bands = _bands()
    out = []
    for l in lines:
        if live:
            pl = _live_line(l, live)
            if pl:
                out.append(pl)
                continue
        o = bands["overrides"].get(l.ldraw_part)
        if o and not l.kind:
            out.append(PriceLine(l, o["low"], o["high"], o.get("note", "fixed")))
            continue
        name = f" {l.name.lower()} "
        if l.kind and l.kind in bands.get("minifig", {}):      # a minifig head, torso, legs
            rule = {**bands["minifig"][l.kind], "match": f"minifig {l.kind}"}
        else:
            rule = next(r for r in bands["rules"] if r["match"] in name)
        f, basis = 1.0, rule["match"].strip() or "other"
        if "trans" in l.color.name.lower():
            f *= bands["colour_factor"]["trans"]
            basis += ", transparent"
        e = catalog.element(l.rb_part if l.kind else l.ldraw_part + ".dat", l.color)
        sets = e.set_count if e else 0
        for s in bands["scarcity"]:
            if sets <= s["max_sets"]:
                f *= s["factor"]
                basis += f", in {sets} set(s)"
                break
        out.append(PriceLine(l, rule["low"] * f, rule["high"] * f, basis))
    return out


def _label(p: PriceLine) -> str:
    l = p.line
    return f"{l.qty} x {l.name} ({l.bl_part or l.rb_part}), {l.color.name}"


def summary(priced: list[PriceLine], day: str | None = None, pab_day: str | None = None) -> dict:
    """Totals and a one-line description of where the numbers come from: `bricklink` and
    `pick_a_brick` (each None when not priced), and the fallback low-high range."""
    n_live = sum(p.live for p in priced)
    low = sum(p.low * p.line.qty for p in priced)
    high = sum(p.high * p.line.qty for p in priced)
    if n_live and day:
        note = (f"BrickLink price guide, {day}: {n_live} of {len(priced)} part lines priced "
                "live (six-month sold average to current asking average, new, USD)"
                + ("; the rest estimated from typical prices." if n_live < len(priced) else "."))
    else:
        note = "A rough range from typical BrickLink prices per part type, not live market data."
    bl = [p for p in priced if p.bricklink is not None]
    bricklink = ({"usd": round(sum(p.bricklink * p.line.qty for p in bl), 2), "date": day,
                  "lines": len(bl), "of": len(priced),
                  "missing": [_label(p) for p in priced if p.bricklink is None],
                  "basis": "new parts, the average each sold for over the last six months "
                           "(the average asking price where nothing sold), before shipping"}
                 if bl and day else None)
    pb = [p for p in priced if p.pab is not None]
    pick = ({"usd": round(sum(p.pab * p.line.qty for p in pb), 2), "date": pab_day,
             "lines": len(pb), "of": len(priced),
             "missing": [_label(p) for p in priced if p.pab is None],
             "standard": [_label(p) for p in pb if p.bestseller is False],
             "basis": "LEGO Pick a Brick, US shop, before shipping"}
            if pb and pab_day else None)
    return {"low": round(low, 2), "high": round(high, 2), "currency": "USD", "note": note,
            "source": "bricklink" if n_live else "estimate", "date": day if n_live else None,
            "live_lines": n_live, "lines": len(priced),
            "bricklink": bricklink, "pick_a_brick": pick}


def headline(s: dict) -> str:
    """'BrickLink $45 (2026-10-14) · Pick a Brick $47 (2026-10-14)', or the rough range."""
    parts = []
    if s.get("bricklink"):
        parts.append(f"BrickLink ${s['bricklink']['usd']:,.2f} ({s['bricklink']['date']})")
    if s.get("pick_a_brick"):
        pb = s["pick_a_brick"]
        miss = f", {len(pb['missing'])} line(s) not sold there" if pb["missing"] else ""
        parts.append(f"Pick a Brick ${pb['usd']:,.2f} ({pb['date']}{miss})")
    return " · ".join(parts) or f"roughly ${s['low']:,.0f}-${s['high']:,.0f} (estimate)"


def hardware_summary(hardware: list[HardwareLine]) -> dict:
    """Totals for the non-LEGO items (rough USD ranges from data/hardware.json or the model)."""
    return {"low": round(sum(h.low * h.qty for h in hardware), 2),
            "high": round(sum(h.high * h.qty for h in hardware), 2),
            "items": sum(h.qty for h in hardware), "lines": len(hardware), "currency": "USD"}


def write_estimate_md(name: str, priced: list[PriceLine], path, day: str | None = None,
                      hardware: list[HardwareLine] = (), minifigs: int = 0,
                      pab_day: str | None = None) -> tuple[float, float]:
    s = summary(priced, day, pab_day)
    low, high = s["low"], s["high"]
    figs = (f", {minifigs} minifigure{'s' if minifigs != 1 else ''} among them"
            if minifigs else "")
    rows = sorted(priced, key=lambda p: -(p.low + p.high) * p.line.qty)
    if s["bricklink"] or s["pick_a_brick"]:
        return _write_two_prices(name, priced, path, s, figs, hardware)
    if s["source"] == "bricklink":
        intro = [f"**${low:,.0f} - ${high:,.0f}** for {sum(p.line.qty for p in priced):,} "
                 f"pieces in {len(priced)} lines{figs}, new parts on BrickLink, before shipping. "
                 f"Priced {day}.", "",
                 f"From BrickLink's price guide on {day}, new condition, USD, weighted by "
                 "quantity: the low end is the average sold over the last six months, the high "
                 "end the average asking price of what's for sale now. "
                 f"{s['live_lines']} of {s['lines']} lines priced live"
                 + ("; the rest use typical price bands (`brickkit/data/price_bands.json`)."
                    if s["live_lines"] < s["lines"] else "."), ""]
    else:
        intro = [f"**Roughly ${low:,.0f} - ${high:,.0f}** for {sum(p.line.qty for p in priced):,} "
                 f"pieces in {len(priced)} lines{figs}, new parts on BrickLink, before shipping.",
                 "",
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
        md.append(f"| {l.qty} | {l.bl_part or l.rb_part + ' (Rebrickable)'} {l.name} | {l.color.name} | "
                  f"{p.low:.2f}-{p.high:.2f} | {p.low * l.qty:.2f}-{p.high * l.qty:.2f} | "
                  f"{p.basis} |")
    md.append("")
    if hardware:
        h = hardware_summary(hardware)
        md += ["## Not LEGO: buy separately", "",
               f"**Roughly ${h['low']:,.0f} - ${h['high']:,.0f}** for {h['items']} item(s), not "
               "included above (not on BrickLink; see `hardware.csv`). With them the model comes "
               f"to roughly ${low + h['low']:,.0f} - ${high + h['high']:,.0f}.", "",
               "| Qty | Item | Each (USD) | Line (USD) | Where to buy |", "|---:|---|---:|---:|---|"]
        for l in hardware:
            md.append(f"| {l.qty} | {l.name}: {l.description} | {l.low:.2f}-{l.high:.2f} | "
                      f"{l.low * l.qty:.2f}-{l.high * l.qty:.2f} | {l.where} |")
        md.append("")
    path.write_text("\n".join(md))
    return low, high


def _write_two_prices(name: str, priced: list[PriceLine], path, s: dict, figs: str,
                      hardware: list[HardwareLine]) -> tuple[float, float]:
    """The price file with a BrickLink price and a Pick a Brick price, line by line."""
    n = sum(p.line.qty for p in priced)
    bl, pb = s["bricklink"], s["pick_a_brick"]
    md = [f"# {name}: price", "", f"{n:,} pieces in {len(priced)} lines{figs}.", ""]
    if bl:
        md += [f"**BrickLink: ${bl['usd']:,.2f}** for new parts, before shipping, from BrickLink's "
               f"price guide on {bl['date']}: each line at the average it sold for over the last six "
               "months (the average asking price where nothing sold), weighted by quantity."
               + (f" Not priced (no BrickLink data): {'; '.join(bl['missing'])}." if bl["missing"]
                  else ""), ""]
    if pb:
        md += [f"**Pick a Brick: ${pb['usd']:,.2f}** at LEGO Pick a Brick (US shop) on {pb['date']}, "
               "before shipping"
               + (f". Not sold there: {'; '.join(pb['missing'])}" if pb["missing"] else
                  ": every line is sold there")
               + (". All of it is in the Bestseller range, so it comes as one parcel."
                  if not pb["standard"] else
                  f". Standard pieces, sent later in a parcel of their own: {'; '.join(pb['standard'])}.")
               , ""]
    md += ["Order with `bricklink_wanted.xml` (upload as a BrickLink Wanted List, then Easy Buy) "
           "or `pick_a_brick.csv` (upload on Pick a Brick).", "",
           "| Qty | Part | Colour | BrickLink each | BrickLink line | Pick a Brick each | Pick a Brick line |",
           "|---:|---|---|---:|---:|---:|---:|"]
    money = lambda v: f"{v:.2f}" if v is not None else "-"
    rows = sorted(priced, key=lambda p: -((p.bricklink or p.pab or p.low) * p.line.qty))
    for p in rows:
        l = p.line
        md.append(f"| {l.qty} | {l.bl_part or l.rb_part + ' (Rebrickable)'} {l.name} | {l.color.name} | "
                  f"{money(p.bricklink)} | {money(p.bricklink and p.bricklink * l.qty)} | "
                  f"{money(p.pab)}{'' if p.bestseller in (None, True) else ' (Standard)'} | "
                  f"{money(p.pab and p.pab * l.qty)} |")
    md.append("")
    if hardware:
        h = hardware_summary(hardware)
        md += ["## Not LEGO: buy separately", "",
               f"**Roughly ${h['low']:,.0f} - ${h['high']:,.0f}** for {h['items']} item(s), not "
               "included above (see `hardware.csv`).", "",
               "| Qty | Item | Each (USD) | Line (USD) | Where to buy |", "|---:|---|---:|---:|---|"]
        for l in hardware:
            md.append(f"| {l.qty} | {l.name}: {l.description} | {l.low:.2f}-{l.high:.2f} | "
                      f"{l.low * l.qty:.2f}-{l.high * l.qty:.2f} | {l.where} |")
        md.append("")
    path.write_text("\n".join(md))
    return s["low"], s["high"]
