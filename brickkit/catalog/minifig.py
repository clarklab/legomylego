"""Minifigures: what LEGO sells against what LDraw models.

LEGO, Rebrickable and BrickLink sell a minifigure's body as three assemblies, each numbered
per print and colour combination:

| component | LDraw pieces | Rebrickable | BrickLink |
|---|---|---|---|
| head | 3626c (print 3626cpXXX) | 3626cprNNNN | 3626cpbNNNN |
| torso | 973 (print 973pXXX), arms 3818/3819, hands 3820 x2 | 973cAAhBBprNNNN | 973pbNNNNc01 |
| legs | hips 3815b, legs 3816c/3817c (+ prints) | 970cAA[patBB][prNNNN] | 970c00[pbNNNN] |

The torso assembly's colour is the torso's, `AA`/`BB` (Rebrickable's minifigure colour codes,
e.g. 05 Dark Blue, 02 Light Nougat) give the arms and hands; the legs assembly's colour is the
hips', `AA` gives the legs. The only mapping between the systems that ships with the libraries
is the `!KEYWORDS Rebrickable ..., BrickLink ...` LDraw header lines (`xref.py`), and LDraw has
a model for only some prints: a component without one is drawn with plain pieces in the right
colours (`stand_in`), while the parts lists name the real printed part.
"""
from __future__ import annotations

import csv
import gzip
import pickle
import re
from collections import defaultdict
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from .colors import Color
from .rebrickable import fig_sets, tables_mtime, write_pickle

HEAD, TORSO, LEGS = "head", "torso", "legs"
KIND_CATEGORY = {59: HEAD, 60: TORSO, 61: LEGS}

# the LDraw pieces of a plain component (a stand-in for a print LDraw has no model of)
PLAIN = {HEAD: {"head": "3626c"},
         TORSO: {"torso": "973", "arm_r": "3818", "arm_l": "3819", "hand_r": "3820",
                 "hand_l": "3820"},
         LEGS: {"hips": "3815b", "leg_r": "3816c", "leg_l": "3817c"}}


@dataclass(frozen=True)
class FigPiece:
    slot: str            # head | torso arm_r arm_l hand_r hand_l | hips leg_r leg_l
    part: str            # LDraw file, e.g. "973p2u.dat"
    color: Color


@dataclass(frozen=True)
class Component:
    """A minifigure component as bought (one line on the parts lists) and the LDraw pieces
    that draw it."""
    kind: str            # head | torso | legs
    rb_part: str         # Rebrickable part number
    color: Color         # the element's colour: the head's, the torso's, the hips'
    name: str
    bl_part: str         # BrickLink item number ("" when no cross-reference is known)
    pieces: tuple        # (FigPiece, ...)
    stand_in: bool       # LDraw has no model of this print: plain pieces in its colours
    source: str = ""     # the LDraw file the pieces come from (a shortcut or a printed part)
    arm_color: Color | None = None     # torso
    hand_color: Color | None = None    # torso
    leg_color: Color | None = None     # legs

    def piece(self, slot: str) -> FigPiece:
        return next(p for p in self.pieces if p.slot == slot)

    @property
    def label(self) -> str:
        return f"{self.rb_part} {self.color.name}"


@dataclass
class FigIndex:
    """Whole minifigures from Rebrickable (for searching by character): fig_num -> row."""
    figs: dict           # fig_num -> {"name", "parts": [(part, color_id, qty)], "sets", "year"}


def _rows(d: Path, name: str):
    with gzip.open(d / f"{name}.csv.gz", "rt", encoding="utf-8") as fh:
        yield from csv.DictReader(fh)


def build_fig_index(d: Path) -> FigIndex:
    d = Path(d)
    if not (d / "minifigs.csv.gz").exists():
        return FigIndex({})
    names = {r["fig_num"]: r["name"] for r in _rows(d, "minifigs")}
    inv_set = {r["id"]: r["set_num"] for r in _rows(d, "inventories")}
    set_year = {r["set_num"]: int(r["year"]) for r in _rows(d, "sets")}
    in_sets = fig_sets(d, inv_set)
    parts = defaultdict(list)
    for r in _rows(d, "inventory_parts"):
        f = inv_set.get(r["inventory_id"], "")
        if f.startswith("fig-") and r["is_spare"] != "True":
            parts[f].append((r["part_num"], int(r["color_id"]), int(r["quantity"])))
    figs = {}
    for f, name in names.items():
        sets = in_sets.get(f, set())
        figs[f] = {"name": name, "parts": parts.get(f, []), "sets": len(sets),
                   "year": max((set_year.get(s, 0) for s in sets), default=0)}
    return FigIndex(figs)


def load_fig_index(d: Path, cache: Path) -> FigIndex:
    d, cache = Path(d), Path(cache)
    if cache.exists() and cache.stat().st_mtime > tables_mtime(d):
        with open(cache, "rb") as fh:
            return pickle.load(fh)
    idx = build_fig_index(d)
    write_pickle(idx, cache)
    return idx


CODE_RE = {TORSO: re.compile(r"^973c(\d+)h(\d+)"), LEGS: re.compile(r"^970c(\d+)")}
PRINT_RE = {TORSO: re.compile(r"^973c\d+h\d+(pr\d+)$"),
            LEGS: re.compile(r"^970c\d+((?:pat\d+)?pr\d+)$")}


def _print_words(name: str) -> set[str]:
    """The words describing a print, without the arms/hands/legs colours."""
    name = re.sub(r",[^,]*\b(Arms|Hands|Legs)\b.*$", "", name)
    return set(re.findall(r"[a-z0-9']+", name.lower()))


class FigCatalog:
    """Resolves minifigure components (by Rebrickable, BrickLink or LDraw number) to what is
    bought and the LDraw pieces that draw it. `catalog` is the main Catalog."""

    def __init__(self, catalog, xref, fig_index_loader=None):
        self.catalog = catalog
        self.xref = xref
        self._fig_loader = fig_index_loader

    @property
    def rb(self):
        return self.catalog.rb

    @cached_property
    def figs(self) -> FigIndex:
        return self._fig_loader() if self._fig_loader else FigIndex({})

    @cached_property
    def codes(self) -> dict[str, str]:
        """Rebrickable's minifigure colour codes ('05') -> colour name, learned from the plain
        assemblies' names ('970c05' 'Hips and Dark Blue Legs', '973c05h02' 'Torso, Dark Blue
        Arms, Light Nougat Hands [Plain]')."""
        out = {}
        for num, (name, _) in self.rb.parts.items():
            m = re.match(r"^970c(\d+)$", num)
            n = re.match(r"^Hips and (.+) Legs$", name)
            if m and n:
                out[m.group(1)] = n.group(1)
        for num, (name, _) in self.rb.parts.items():
            m = re.match(r"^973c(\d+)h(\d+)$", num)
            n = re.match(r"^Torso, (.+?) Arms(?: and Hands|, (.+?) Hands)", name)
            if m and n:
                out.setdefault(m.group(1), n.group(1))
                out.setdefault(m.group(2), n.group(2) or n.group(1))
        return out

    @cached_property
    def bricklink_extra(self) -> dict[str, str]:
        """BrickLink numbers for components LDraw doesn't cross-reference
        (data/minifig_bricklink.json, checked by hand)."""
        import json
        from .. import paths
        f = paths.DATA_DIR / "minifig_bricklink.json"
        d = json.loads(f.read_text()) if f.exists() else {}
        return {k: v for k, v in d.items() if not k.startswith("_")}

    @cached_property
    def by_bricklink(self) -> dict[str, str]:
        out = {}
        for ld, nums in self.xref.bricklink.items():
            for n in nums:
                out.setdefault(n.lower(), ld)
        return out

    # lookups ----------------------------------------------------------------------------
    def kind(self, rb_part: str) -> str | None:
        row = self.rb.parts.get(rb_part)
        if not row:
            return None
        k = KIND_CATEGORY.get(row[1])
        if k == TORSO and not rb_part.startswith("973"):
            return None             # one-piece torsos, robes, ... (not the standard body)
        if k == LEGS and not rb_part.startswith("970"):
            return None
        if k == HEAD and not rb_part.startswith(("3626", "28621")):
            return None
        return k

    def rb_number(self, spec: str) -> str:
        """A Rebrickable part number for `spec`: itself, or the one an LDraw file or a
        BrickLink number (through LDraw's headers) cross-references."""
        s = spec.strip()
        if s in self.rb.parts:
            return s
        low = s.lower().removesuffix(".dat")
        got = self.xref.rb_for(low)
        if got and got in self.rb.parts:
            return got
        ld = self.by_bricklink.get(low)
        got = self.xref.rb_for(ld) if ld else None
        if got and got in self.rb.parts:
            return got
        raise KeyError(f"no Rebrickable minifigure part for {spec!r}")

    def code_color(self, code: str) -> Color | None:
        name = self.codes.get(code)
        if not name:
            return None
        try:
            return self.catalog.color(name)
        except KeyError:
            return None

    def best_color(self, rb_part: str) -> Color:
        cids = self.rb.part_colors.get(rb_part, ())
        if not cids:
            raise KeyError(f"{rb_part}: LEGO never made it in any colour")
        cid = max(cids, key=lambda c: (self.rb.set_count.get((rb_part, c), 0), -c))
        return self.catalog.color(self.rb.colors[cid]["name"])

    def _desc(self, ldraw_id: str) -> str:
        return self.catalog.ldraw.description(ldraw_id).lstrip("~_=")

    def _sources(self, rb_part: str, kind: str) -> list[str]:
        """LDraw files that model this Rebrickable number (shortcuts first)."""
        out = [f for f in self.xref.ldraw_for(rb_part) if self.catalog.ldraw.resolve(f)
               and "Obsolete" not in self.catalog.ldraw.description(f)
               and not self.catalog.ldraw.description(f).startswith(("~", "="))]
        word = {HEAD: "Minifig Head", TORSO: "Minifig Torso", LEGS: "Minifig "}[kind]
        out = [f for f in out if self._desc(f).startswith(word)]
        return sorted(out, key=lambda f: (f not in self.xref.shortcuts, f))

    @cached_property
    def _prints(self) -> dict:
        """(kind, print number) -> [Rebrickable numbers]: the same print on other colours
        (Rebrickable numbers a torso or legs print once, e.g. pr0189, whatever the arms)."""
        out = defaultdict(list)
        for num in self.rb.parts:
            for kind, rx in PRINT_RE.items():
                m = rx.match(num)
                if m:
                    out[(kind, m.group(1))].append(num)
        return out

    def _sibling_source(self, rb_part: str, kind: str) -> tuple[str, str]:
        """(LDraw file, Rebrickable number) of the same print on another assembly that LDraw
        has a model of, or ("", "")."""
        m = PRINT_RE[kind].match(rb_part)
        if not m:
            return "", ""
        mine = _print_words(self.rb.parts[rb_part][0])
        for other in sorted(self._prints.get((kind, m.group(1)), ())):
            if other != rb_part:
                # newer Rebrickable print numbers restart per arm/hand colours: only a print
                # described the same way is the same print
                theirs = _print_words(self.rb.parts[other][0])
                if len(mine & theirs) < 0.75 * len(mine | theirs):
                    continue
                src = self._sources(other, kind)
                if src:
                    return src[0], other
        return "", ""

    # components -------------------------------------------------------------------------
    def component(self, kind: str, spec, color=None) -> Component:
        """`spec`: a Rebrickable number (or an LDraw file / BrickLink number that LDraw's
        headers cross-reference); `color`: the element's colour (default: the colour it came
        in most often)."""
        rb_part = self.rb_number(str(spec))
        k = self.kind(rb_part)
        if k != kind:
            raise ValueError(f"{rb_part} ({self.catalog.part_name(rb_part)}) is not a minifig "
                             f"{kind}" + (f" but a {k}" if k else ""))
        col = self.catalog.color(color) if color is not None else self.best_color(rb_part)
        name = self.rb.parts[rb_part][0]
        comp = getattr(self, f"_{kind}")(rb_part, col, name)
        if not comp.bl_part and rb_part in self.bricklink_extra:
            from dataclasses import replace
            comp = replace(comp, bl_part=self.bricklink_extra[rb_part])
        return comp

    def _bl(self, source: str, pattern: str) -> str:
        for n in self.xref.bricklink.get(source, ()):
            if re.match(pattern, n, re.I):
                return n
        return ""

    def _head(self, rb_part, col, name) -> Component:
        src = self._sources(rb_part, HEAD)
        if src:
            f = src[0]
            return Component(HEAD, rb_part, col, name, self._bl(f, r"^3626"),
                             (FigPiece("head", f + ".dat", col),), False, f)
        plain = rb_part in ("3626c", "3626b", "3626", "28621")
        base = "28621" if rb_part.startswith("28621") else "3626c"
        return Component(HEAD, rb_part, col, name, rb_part if plain else "",
                         (FigPiece("head", base + ".dat", col),), not plain, "")

    def _torso(self, rb_part, col, name) -> Component:
        m = CODE_RE[TORSO].match(rb_part)
        arm = self.code_color(m.group(1)) if m else None
        hand = self.code_color(m.group(2)) if m else None
        if arm is None or hand is None:          # fall back on the name
            n = re.search(r"([A-Z][\w\- ]+?) Arms(?: and Hands|, ([A-Z][\w\- ]+?) Hands)", name)
            if not n:
                raise ValueError(f"{rb_part}: can't tell the arm and hand colours from {name!r}")
            arm = arm or self.catalog.color(n.group(1).split(", ")[-1])
            hand = hand or self.catalog.color((n.group(2) or n.group(1)).split(", ")[-1])
        files = dict(PLAIN[TORSO])
        colours = {"torso": col, "arm_r": arm, "arm_l": arm, "hand_r": hand, "hand_l": hand}
        src = self._sources(rb_part, TORSO)
        source, bl, sibling = "", "", ""
        if not src:                  # the same print on other arms: its torso piece only
            src_s, sibling = self._sibling_source(rb_part, TORSO)
            if src_s:
                subs = self.xref.shortcuts.get(src_s) or [("16", (), src_s + ".dat")]
                for _, _, sub in subs:
                    sid = sub.removesuffix(".dat")
                    if self._desc(sid).startswith("Minifig Torso") and sid not in self.xref.shortcuts:
                        files["torso"] = sid
                        source = f"{sid} (the print of {sibling})"
        elif src:
            source = src[0]
            subs = self.xref.shortcuts.get(source)
            if subs:
                arms = []
                for code, _, sub in subs:
                    sid = sub.removesuffix(".dat")
                    d = self._desc(sid)
                    if d.startswith("Minifig Torso") or sid.startswith("973"):
                        files["torso"] = sid
                    elif d.startswith("Minifig Arm Right") or sid.startswith("3818"):
                        files["arm_r"] = sid
                    elif d.startswith("Minifig Arm Left") or sid.startswith("3819"):
                        files["arm_l"] = sid
                    elif sid.startswith("3820") or d.startswith("Minifig Hand"):
                        arms.append(sid)
                if len(arms) == 2:
                    files["hand_r"], files["hand_l"] = arms
                bl = self._bl(source, r"^973.*c\d+$")
            else:
                files["torso"] = source
        pieces = tuple(FigPiece(s, f + ".dat", colours[s]) for s, f in files.items())
        return Component(TORSO, rb_part, col, name, bl, pieces, not source, source,
                         arm_color=arm, hand_color=hand)

    def _legs(self, rb_part, col, name) -> Component:
        m = CODE_RE[LEGS].match(rb_part)
        leg = self.code_color(m.group(1)) if m else None
        if leg is None:
            n = re.search(r"Hips (?:with|and) ([A-Z][\w\- ]+?) Legs", name)
            leg = self.catalog.color(n.group(1)) if n else col
        files = dict(PLAIN[LEGS])
        src = self._sources(rb_part, LEGS)
        lib = self.catalog.ldraw
        source = src[0] if src else ""
        geometry, sibling = source, ""
        if not source:                       # the same print on other legs
            geometry, sibling = self._sibling_source(rb_part, LEGS)
        if geometry:
            subs = self.xref.shortcuts.get(geometry)
            members = ([s.removesuffix(".dat") for _, _, s in subs] if subs else [geometry])
            if not subs:                       # one printed piece: find its printed twins
                mm = re.match(r"^(3815b|3816c|3817c|20460b?|20461b?)(p.+)$", geometry)
                if mm:
                    for base in ("3815b", "3816c", "3817c"):
                        if lib.resolve(base + mm.group(2)):
                            members.append(base + mm.group(2))
            for sid in members:
                d = self._desc(sid)
                if d.startswith("Minifig Hips") and "Legs" not in d:
                    files["hips"] = sid
                elif d.startswith("Minifig Leg Right") or "Leg Right" in d:
                    files["leg_r"] = sid
                elif d.startswith("Minifig Leg Left") or "Leg Left" in d:
                    files["leg_l"] = sid
        colours = {"hips": col, "leg_r": leg, "leg_l": leg}
        pieces = tuple(FigPiece(s, f + ".dat", colours[s]) for s, f in files.items())
        printed = bool(re.search(r"(pr|pat)\d", rb_part))
        bl = self._bl(source, r"^970") if source else ""
        if not bl and not printed:
            bl = "970c00" if leg == col else (f"970c{leg.bl_id:02d}" if leg.bl_id is not None
                                             else "")
        if sibling:
            source = f"{geometry} (the print of {sibling})"
        return Component(LEGS, rb_part, col, name, bl, pieces, printed and not geometry, source,
                         leg_color=leg)

    # searching --------------------------------------------------------------------------
    def search(self, text: str, kind: str | None = None, color=None, limit: int = 40,
               ldraw_only: bool = False) -> list[dict]:
        """Minifigure components whose name contains every word, most-used first: {sets, year,
        part, colour, name, ldraw, bricklink}. One row per part and colour."""
        words = text.lower().split()
        c = self.catalog.color(color) if color else None
        rows = []
        for pnum, (name, _) in self.rb.parts.items():
            k = self.kind(pnum)
            if k is None or (kind and k != kind):
                continue
            low = name.lower()
            if not all(w in low for w in words):
                continue
            src = self._sources(pnum, k)
            if not src and k in PRINT_RE:
                sib = self._sibling_source(pnum, k)[0]
                src = ["~" + sib] if sib else []
            plain = not re.search(r"(pr|pat)\d", pnum)
            if ldraw_only and not src and not plain:
                continue
            for cid in self.rb.part_colors.get(pnum, ()):
                if c is not None and cid != c.rb_id:
                    continue
                rows.append({"sets": self.rb.set_count.get((pnum, cid), 0),
                             "year": self.rb.last_year.get((pnum, cid), 0), "part": pnum,
                             "kind": k, "colour": self.rb.colors[cid]["name"], "name": name,
                             "ldraw": src[0] if src else ("plain" if plain else ""),
                             "bricklink": (self._bl(src[0], r"^(3626|973|970)") if src else ""),
                             "element": bool(self.rb.elements.get((pnum, cid)))})
        rows.sort(key=lambda r: (-r["sets"], -r["year"]))
        return rows[:limit]

    def figures(self, text: str, limit: int = 20) -> list[dict]:
        """Whole Rebrickable minifigures whose name contains every word, in most sets first,
        with their parts."""
        words = text.lower().split()
        out = []
        for f, row in self.figs.figs.items():
            if all(w in row["name"].lower() for w in words):
                out.append({"fig": f, **row})
        out.sort(key=lambda r: (-r["sets"], -r["year"]))
        return out[:limit]
