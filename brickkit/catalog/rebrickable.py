"""Compact index over the Rebrickable CSV dumps (pickled next to the cache)."""
from __future__ import annotations

import csv
import gzip
import os
import pickle
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

TABLES = ("parts", "colors", "elements", "inventory_parts", "inventories", "sets",
          "part_relationships", "part_categories")
# optional: which sets each minifigure is in (`brickkit fetch` gets them). Minifigure parts are
# listed in the figure's own inventory (fig-NNNNNN), not the set's, so without these their set
# counts are counts of figures and their years unknown.
OPTIONAL = ("inventory_minifigs", "minifigs")


@dataclass
class RBIndex:
    parts: dict          # part_num -> (name, category id)
    categories: dict     # id -> name
    colors: dict         # id -> row
    elements: dict       # (part_num, color_id) -> [element_id]
    last_year: dict      # (part_num, color_id) -> latest set year
    set_count: dict      # (part_num, color_id) -> number of set inventories
    related: dict        # part_num -> {alternate / mould variants}
    part_colors: dict    # part_num -> {color_id}


def _rows(d: Path, name: str):
    with gzip.open(d / f"{name}.csv.gz", "rt", encoding="utf-8") as fh:
        yield from csv.DictReader(fh)


def fig_sets(d: Path, inv_set: dict) -> dict:
    """fig_num -> {set_num} of the sets the minifigure comes in (empty without the table)."""
    out: dict = defaultdict(set)
    if (d / "inventory_minifigs.csv.gz").exists():
        for r in _rows(d, "inventory_minifigs"):
            s = inv_set.get(r["inventory_id"])
            if s and not s.startswith("fig-"):
                out[r["fig_num"]].add(s)
    return out


def build_index(d: Path) -> RBIndex:
    parts = {r["part_num"]: (r["name"], int(r["part_cat_id"])) for r in _rows(d, "parts")}
    cats = {int(r["id"]): r["name"] for r in _rows(d, "part_categories")}
    colors = {int(r["id"]): r for r in _rows(d, "colors")}
    elements: dict = defaultdict(list)
    for r in _rows(d, "elements"):
        elements[(r["part_num"], int(r["color_id"]))].append(r["element_id"])
    set_year = {r["set_num"]: int(r["year"]) for r in _rows(d, "sets")}
    inv_set = {r["id"]: r["set_num"] for r in _rows(d, "inventories")}
    figs = fig_sets(d, inv_set)
    last_year: dict = defaultdict(int)
    sets_with: dict = defaultdict(set)
    for r in _rows(d, "inventory_parts"):
        s = inv_set.get(r["inventory_id"])
        key = (r["part_num"], int(r["color_id"]))
        # a minifigure's parts count for every set the figure comes in (a figure in no set,
        # such as a promotional one, counts as itself, of unknown year)
        for t in (figs.get(s) or (s,)) if s and s.startswith("fig-") else (s,):
            last_year[key] = max(last_year[key], set_year.get(t, 0))
            sets_with[key].add(t)
    related: dict = defaultdict(set)
    for r in _rows(d, "part_relationships"):
        if r["rel_type"] in ("A", "M"):
            related[r["child_part_num"]].add(r["parent_part_num"])
            related[r["parent_part_num"]].add(r["child_part_num"])
    part_colors: dict = defaultdict(set)
    for p, c in list(elements) + list(last_year):
        part_colors[p].add(c)
    return RBIndex(parts, cats, colors, dict(elements), dict(last_year),
                   {k: len(v) for k, v in sets_with.items()}, dict(related), dict(part_colors))


def tables_mtime(d: Path) -> float:
    d = Path(d)
    times = [(d / f"{t}.csv.gz").stat().st_mtime for t in TABLES]
    times += [(d / f"{t}.csv.gz").stat().st_mtime for t in OPTIONAL
              if (d / f"{t}.csv.gz").exists()]
    return max(times)


def write_pickle(obj, path: Path) -> None:
    """Pickle atomically (another process may be reading the cache at the same time)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    with open(tmp, "wb") as fh:
        pickle.dump(obj, fh)
    os.replace(tmp, path)


def load_index(d: Path, cache: Path) -> RBIndex:
    d, cache = Path(d), Path(cache)
    if cache.exists() and cache.stat().st_mtime > tables_mtime(d):
        with open(cache, "rb") as fh:
            return pickle.load(fh)
    idx = build_index(d)
    write_pickle(idx, cache)
    return idx
