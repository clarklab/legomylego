"""Live prices from BrickLink's price guide, through BrickLink's official API.

BrickLink's API needs the owner's credentials: a BrickLink account registered as a seller
(free, no store needed), then https://www.bricklink.com/v2/api/register_consumer.page gives a
consumer key/secret and a token value/secret (set the allowed IP to 0.0.0.0 / 0.0.0.0).
Put them in the environment or in ~/.config/brickkit/bricklink.env (never in the repo):

    BRICKLINK_CONSUMER_KEY=...
    BRICKLINK_CONSUMER_SECRET=...
    BRICKLINK_TOKEN=...
    BRICKLINK_TOKEN_SECRET=...

For each part/colour this asks for new condition, in USD: the average asking price of what's
for sale now ("stock") and the average of what sold in the last six months ("sold"), both
weighted by quantity. Answers are cached per day under .cache/prices/, so a day's lookups are
made once. (BrickLink's price-guide web pages are off limits to scripts; the API is the
sanctioned way in.)"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import hmac
import json
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .. import paths

API = "https://api.bricklink.com/api/store/v1"
KEYS = ("BRICKLINK_CONSUMER_KEY", "BRICKLINK_CONSUMER_SECRET", "BRICKLINK_TOKEN",
        "BRICKLINK_TOKEN_SECRET")
CRED_FILE = Path.home() / ".config" / "brickkit" / "bricklink.env"


def credentials() -> dict | None:
    env = {k: os.environ.get(k, "") for k in KEYS}
    if not all(env.values()) and CRED_FILE.exists():
        for line in CRED_FILE.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                if k.strip() in KEYS and not env.get(k.strip()):
                    env[k.strip()] = v.strip().strip('"').strip("'")
    return env if all(env.values()) else None


def _q(s: str) -> str:
    return urllib.parse.quote(str(s), safe="~")


def _auth_header(method: str, url: str, params: dict, cred: dict) -> str:
    """OAuth 1.0a (HMAC-SHA1) Authorization header, as BrickLink's API expects."""
    oauth = {"oauth_consumer_key": cred["BRICKLINK_CONSUMER_KEY"],
             "oauth_token": cred["BRICKLINK_TOKEN"],
             "oauth_signature_method": "HMAC-SHA1",
             "oauth_timestamp": str(int(time.time())),
             "oauth_nonce": secrets.token_hex(12), "oauth_version": "1.0"}
    allp = {**params, **oauth}
    norm = "&".join(f"{_q(k)}={_q(v)}" for k, v in sorted(allp.items()))
    base = "&".join((method.upper(), _q(url), _q(norm)))
    key = f"{_q(cred['BRICKLINK_CONSUMER_SECRET'])}&{_q(cred['BRICKLINK_TOKEN_SECRET'])}"
    sig = base64.b64encode(hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()).decode()
    oauth["oauth_signature"] = sig
    return "OAuth realm=\"\", " + ", ".join(f'{k}="{_q(v)}"' for k, v in sorted(oauth.items()))


class PriceGuide:
    """Cached BrickLink price guide lookups for one day."""

    def __init__(self, cred: dict, day: str | None = None):
        self.cred = cred
        self.day = day or dt.date.today().isoformat()
        self.path = paths.CACHE / "prices" / f"bricklink_{self.day}.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.cache = json.loads(self.path.read_text()) if self.path.exists() else {}
        self.calls = 0

    def save(self) -> None:
        self.path.write_text(json.dumps(self.cache, indent=0, sort_keys=True))

    def lookup(self, item_type: str, item_no: str, color_id: int | None, guide: str) -> dict:
        kind = {"P": "PART", "S": "SET", "M": "MINIFIG"}.get(item_type, "PART")
        key = f"{kind}/{item_no}/{color_id}/{guide}"
        if key in self.cache:
            return self.cache[key]
        url = f"{API}/items/{kind}/{urllib.parse.quote(item_no)}/price"
        params = {"guide_type": guide, "new_or_used": "N", "currency_code": "USD"}
        if color_id is not None and kind == "PART":
            params["color_id"] = str(color_id)
        req = urllib.request.Request(url + "?" + urllib.parse.urlencode(params), headers={
            "Authorization": _auth_header("GET", url, params, self.cred),
            "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                body = json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            body = {"meta": {"code": e.code, "message": str(e)}}
        self.calls += 1
        meta, data = body.get("meta", {}), body.get("data") or {}
        if meta.get("code") != 200:
            out = {"ok": False, "error": f"{meta.get('code')} {meta.get('message', '')}".strip()}
        else:
            out = {"ok": True,
                   "avg": float(data.get("qty_avg_price") or data.get("avg_price") or 0) or None,
                   "min": float(data.get("min_price") or 0) or None,
                   "qty": int(data.get("total_quantity") or 0),
                   "lots": int(data.get("unit_quantity") or 0)}
        self.cache[key] = out
        if out.get("error", "").startswith("401") or out.get("error", "").startswith("403"):
            self.save()
            raise PermissionError("BrickLink refused the credentials: " + out["error"])
        return out


def live_prices(lines, day: str | None = None, log=print) -> dict | None:
    """{(bl_type, bl_part, bl_colour): {"stock": {...}, "sold": {...}}} for BOM lines, or None
    when no BrickLink credentials are set up."""
    cred = credentials()
    if not cred:
        return None
    guide = PriceGuide(cred, day)
    out = {}
    try:
        for l in lines:
            col = l.color.bl_id if l.bl_type == "P" else None
            key = (l.bl_type, l.bl_part, col)
            out[key] = {g: guide.lookup(l.bl_type, l.bl_part, col, g) for g in ("stock", "sold")}
    finally:
        guide.save()
    log(f"BrickLink price guide: {len(out)} lines, {guide.calls} new lookups, dated {guide.day}")
    return {"day": guide.day, "prices": out}
