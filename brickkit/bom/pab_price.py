"""Pick a Brick prices: what each LEGO element costs on lego.com's Pick a Brick today.

LEGO has no public API for this; the Pick a Brick page loads its prices from lego.com's
GraphQL endpoint, and this asks it the same question, one element at a time, gently (a pause
between requests), at most once a day per element: answers are cached per day under
.cache/prices/, as BrickLink's are. Each answer also says whether the element is a Bestseller
("pab": shipped together within days) or a Standard piece ("bap": a later parcel of its own).
Set BRICKKIT_NO_PICK_A_BRICK=1 to leave Pick a Brick out (no requests are made)."""
from __future__ import annotations

import datetime as dt
import json
import os
import time
import urllib.error
import urllib.request

from .. import paths

URL = "https://www.lego.com/api/graphql/PickABrickQuery"
QUERY = ("query PickABrickQuery($input: ElementQueryInput!) { searchElements(input: $input) { "
         "results { id designId deliveryChannel availability price { centAmount currencyCode } } "
         "total } }")
PAUSE = 0.25          # s between requests


class PickABrick:
    """Cached Pick a Brick lookups for one day (US shop, USD)."""

    def __init__(self, day: str | None = None, locale: str = "en-US"):
        self.day = day or dt.date.today().isoformat()
        self.locale = locale
        self.path = paths.CACHE / "prices" / f"pick_a_brick_{self.day}.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.cache = json.loads(self.path.read_text()) if self.path.exists() else {}
        self.calls = 0
        self._last = 0.0

    def save(self) -> None:
        self.path.write_text(json.dumps(self.cache, indent=0, sort_keys=True))

    def lookup(self, element: str) -> dict:
        """{ok, usd (each), bestseller, available} for an element ID, or {ok: False, error}."""
        if element in self.cache:
            return self.cache[element]
        wait = PAUSE - (time.time() - self._last)
        if wait > 0:
            time.sleep(wait)
        body = json.dumps({"operationName": "PickABrickQuery", "query": QUERY,
                           "variables": {"input": {"perPage": 20, "page": 1, "query": element}}})
        req = urllib.request.Request(URL, data=body.encode(), method="POST", headers={
            "content-type": "application/json", "x-locale": self.locale,
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/129.0 Safari/537.36"})
        with urllib.request.urlopen(req, timeout=30) as r:      # network errors: the caller's
            data = json.loads(r.read().decode())
        self._last = time.time()
        self.calls += 1
        res = ((data.get("data") or {}).get("searchElements") or {}).get("results") or []
        hit = next((e for e in res if str(e.get("id")) == element), None)
        if hit is None:
            out = {"ok": False, "error": "not on Pick a Brick"}
        else:
            price = hit.get("price") or {}
            out = {"ok": True, "usd": round(int(price.get("centAmount") or 0) / 100, 2),
                   "bestseller": hit.get("deliveryChannel") == "pab",
                   "available": hit.get("availability") or "", "design": hit.get("designId")}
        self.cache[element] = out
        return out


def pab_prices(lines, day: str | None = None, log=print) -> dict | None:
    """{"day", "prices": {element: lookup}} for BOM lines' element IDs, or None when switched off
    or lego.com can't be reached."""
    if os.environ.get("BRICKKIT_NO_PICK_A_BRICK"):
        return None
    pab = PickABrick(day)
    out = {}
    try:
        for l in lines:
            if l.element_id:
                out[l.element_id] = pab.lookup(l.element_id)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        log(f"Pick a Brick prices unavailable ({e}); left out")
        return None
    finally:
        pab.save()
    log(f"Pick a Brick: {len(out)} elements, {pab.calls} new lookups, dated {pab.day}")
    return {"day": pab.day, "prices": out}
