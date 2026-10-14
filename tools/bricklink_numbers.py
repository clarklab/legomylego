"""Learn BrickLink's own part numbers from its API: data/bricklink_numbers.json.

Our parts lists number a part as Rebrickable does, and BrickLink files some parts under another
number (Tile 1 x 1 with Groove: Rebrickable 3070b, BrickLink 3070; Plate Round 1 x 1: 6141 and
4073). For every line of every model's parts list this asks BrickLink's price guide for the part
under our number; where BrickLink doesn't know it, it asks which BrickLink item the line's LEGO
element is (the API's element mapping) and records Rebrickable number -> BrickLink number. The
catalogue then puts BrickLink's number in parts.csv and bricklink_wanted.xml, so the lists come
out the same on a machine without keys. A line with no LEGO element ID (Rebrickable's data has
none for that part in that colour) gets the element IDs BrickLink maps to it, where it has any.
Needs the BrickLink API keys (brickkit/bom/live_price.py); answers are cached a day, like the
prices.

    .venv/bin/python tools/bricklink_numbers.py        # then: brickkit bom SLUG for each model
"""
from __future__ import annotations

import csv
import datetime as dt
import json
from pathlib import Path

from brickkit import paths
from brickkit.bom.live_price import PriceGuide, credentials

OUT = paths.DATA_DIR / "bricklink_numbers.json"


def main() -> int:
    cred = credentials()
    if not cred:
        print("no BrickLink API keys: see brickkit/bom/live_price.py")
        return 1
    guide = PriceGuide(cred)
    data = json.loads(OUT.read_text()) if OUT.exists() else {}
    found: dict = dict(data.get("parts", {}))
    elements: dict = dict(data.get("elements", {}))
    seen, unresolved, clash = set(), [], []
    try:
        for f in sorted(paths.MODELS_DIR.glob("*/out/parts.csv")) + \
                sorted(paths.MODELS_DIR.glob("*/out/variants/*/parts.csv")):
            if f.parts[-3].startswith("_") or f.parts[-5:-4] and f.parts[-5].startswith("_"):
                continue
            for r in csv.DictReader(open(f)):
                rb, bl, col, el = (r.get("rebrickable_part", ""), r.get("bricklink_part", ""),
                                   r.get("bricklink_colour", ""), r.get("element_id", ""))
                if bl and col and not el and f"{rb}/{r.get('colour', '')}" not in elements:
                    got_els = guide.elements_for(found.get(rb, bl), int(col))
                    if got_els:
                        elements[f"{rb}/{r.get('colour', '')}"] = sorted(set(got_els), key=int)
                    else:
                        unresolved.append(f"{rb} in {r.get('colour', '')}: no LEGO element "
                                          f"number on Rebrickable or BrickLink ({f.parts[-3]})")
                if not bl or not col or (bl, col) in seen or bl in found.values():
                    continue
                seen.add((bl, col))
                got = guide.lookup("P", bl, int(col), "stock")
                if not str(got.get("error", "")).startswith("404"):
                    continue
                m = guide.mapped(el) if el else None
                if not m:
                    unresolved.append(f"{bl} colour {col} ({f.parts[-3]})")
                    continue
                no, mcol = m
                if str(mcol) != str(col):
                    clash.append(f"{bl} colour {col}: BrickLink maps element {el} to {no} "
                                 f"colour {mcol}")
                if no != bl:
                    if rb in found and found[rb] != no:
                        clash.append(f"{rb}: {found[rb]} or {no}")
                        continue
                    found[rb] = no
    finally:
        guide.save()
    OUT.write_text(json.dumps({
        "_about": ("Rebrickable part number -> BrickLink's own item number, where BrickLink files "
                   "the part under another one. Learned from BrickLink's API (an element's item "
                   "mapping) by tools/bricklink_numbers.py; brickkit's catalogue uses it for the "
                   "BrickLink number in parts.csv and bricklink_wanted.xml."),
        "checked": dt.date.today().isoformat(),
        "parts": dict(sorted(found.items())),
        "elements": dict(sorted(elements.items()))}, indent=1) + "\n")
    print(f"{len(found)} part numbers BrickLink files differently, {len(elements)} element numbers "
          f"from BrickLink -> {OUT}")
    for u in unresolved:
        print("  not found on BrickLink, and no element to map:", u)
    for c in clash:
        print("  check by hand:", c)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
