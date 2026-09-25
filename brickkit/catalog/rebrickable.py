"""Compact index over the Rebrickable CSV dumps (pickled next to the cache)."""
from __future__ import annotations

import csv
import gzip
import pickle
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

TABLES = ("parts", "colors", "elements", "inventory_parts", "inventories", "sets",
          "part_relationships", "part_categories")


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


def build_index(d: Path) -> RBIndex:
    parts = {r["part_num"]: (r["name"], int(r["part_cat_id"])) for r in _rows(d, "parts")}
    cats = {int(r["id"]): r["name"] for r in _rows(d, "part_categories")}
    colors = {int(r["id"]): r for r in _rows(d, "colors")}
    elements: dict = defaultdict(list)
    for r in _rows(d, "elements"):
        elements[(r["part_num"], int(r["color_id"]))].append(r["element_id"])
    set_year = {r["set_num"]: int(r["year"]) for r in _rows(d, "sets")}
    inv_set = {r["id"]: r["set_num"] for r in _rows(d, "inventories")}
    last_year: dict = defaultdict(int)
    sets_with: dict = defaultdict(set)
    for r in _rows(d, "inventory_parts"):
        s = inv_set.get(r["inventory_id"])
        key = (r["part_num"], int(r["color_id"]))
        last_year[key] = max(last_year[key], set_year.get(s, 0))
        sets_with[key].add(s)
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


def load_index(d: Path, cache: Path) -> RBIndex:
    d, cache = Path(d), Path(cache)
    newest = max((d / f"{t}.csv.gz").stat().st_mtime for t in TABLES)
    if cache.exists() and cache.stat().st_mtime > newest:
        with open(cache, "rb") as fh:
            return pickle.load(fh)
    idx = build_index(d)
    cache.parent.mkdir(parents=True, exist_ok=True)
    with open(cache, "wb") as fh:
        pickle.dump(idx, fh)
    return idx
