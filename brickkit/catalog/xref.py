"""Cross-references LDraw files carry in their headers, e.g.

    0 Minifig Head with Standard Grin Pattern (Hollow Stud)
    0 !KEYWORDS BrickLink 3626p01, Rebrickable 3626cpr0001, set 10246

Printed parts and minifigure assemblies are numbered differently in LDraw (a part per print),
Rebrickable and BrickLink (a number per print and, for assemblies, per colour combination);
these keywords are the only mapping between them that ships with the libraries. Also kept:
the sub-file lines of LDraw "shortcuts" (a torso with its arms and hands, hips with legs), which
say which LDraw files and colours make up an assembly."""
from __future__ import annotations

import os
import pickle
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from .rebrickable import write_pickle

KW_RE = re.compile(r"\b(Rebrickable|Bricklink|BrickLink)\s+([0-9A-Za-z][0-9A-Za-z_.\-]*)")


@dataclass
class LDrawXref:
    rebrickable: dict    # ldraw id -> [Rebrickable part numbers]
    bricklink: dict      # ldraw id -> [BrickLink item numbers]
    by_rebrickable: dict  # Rebrickable part number (lower case) -> [ldraw ids]
    shortcuts: dict      # ldraw id -> [(colour code, 12 floats, sub-file)] of a shortcut

    def rb_for(self, ldraw_id: str) -> str | None:
        got = self.rebrickable.get(ldraw_id.lower())
        return got[0] if got else None

    def bl_for(self, ldraw_id: str) -> str | None:
        got = self.bricklink.get(ldraw_id.lower())
        return got[0] if got else None

    def ldraw_for(self, rb_part: str) -> list[str]:
        return list(self.by_rebrickable.get(rb_part.lower(), ()))


def _scan_file(path: Path):
    kws, shortcut, subs = [], False, []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for n, line in enumerate(fh):
            s = line.strip()
            if s.startswith("0 !KEYWORDS"):
                kws.append(s[11:])
            elif s.startswith("0 !LDRAW_ORG"):
                shortcut = "Shortcut" in s
            elif s.startswith("1 "):
                if not shortcut:
                    break                    # a part: the header is over
                t = s.split()
                if len(t) >= 15:
                    subs.append((t[1], tuple(float(v) for v in t[2:14]), " ".join(t[14:]).lower()))
            elif n > 60 and not shortcut:
                break
    return " , ".join(kws), subs if shortcut else None


def build_xref(ldraw_root: Path) -> LDrawXref:
    rb, bl, by_rb, short = defaultdict(list), defaultdict(list), defaultdict(list), {}
    d = Path(ldraw_root) / "parts"
    for f in os.listdir(d):
        fl = f.lower()
        if not fl.endswith(".dat"):
            continue
        pid = fl[:-4]
        kw, subs = _scan_file(d / f)
        for system, num in KW_RE.findall(kw):
            num = num.rstrip(".")
            if system.lower() == "rebrickable":
                rb[pid].append(num)
                by_rb[num.lower()].append(pid)
            else:
                bl[pid].append(num)
        if subs:
            short[pid] = subs
    return LDrawXref(dict(rb), dict(bl), dict(by_rb), short)


def load_xref(ldraw_root: Path, cache: Path) -> LDrawXref:
    ldraw_root, cache = Path(ldraw_root), Path(cache)
    stamp = max((ldraw_root / "parts").stat().st_mtime, (ldraw_root / "LDConfig.ldr").stat().st_mtime)
    if cache.exists() and cache.stat().st_mtime > stamp:
        with open(cache, "rb") as fh:
            return pickle.load(fh)
    x = build_xref(ldraw_root)
    write_pickle(x, cache)
    return x
