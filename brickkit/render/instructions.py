"""Instruction images for the booklet: one picture per step (earlier parts pale, new parts in
full colour), one picture per finished sub-assembly, and one picture per part/colour for the
callouts and the inventory - all rendered in one Blender run (Workbench engine: clean studio
shading, cavity edges and outlines, like printed LEGO instructions)."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from ..ldraw.library import part_id
from ..ldraw.matrix import apply
from ..model.builder import Placement, Use
from .scene import BLENDER, _colors, export_meshes, run_blender

SCRIPT = Path(__file__).with_name("blender_instructions.py")


@dataclass
class StepInfo:
    number: int                      # 1-based across the whole booklet
    submodel: str
    local_step: int
    caption: str
    image: str
    new_parts: list = field(default_factory=list)       # [(part, colour code, qty)]
    new_subs: list = field(default_factory=list)        # [(submodel name, qty)]
    view: str = "above"


def _local_items(sub):
    """[(item index, part, colour code, M, step)] for every part in a submodel's own frame;
    parts of used sub-assemblies carry the Use's item index and step."""
    out = []
    for k, it in enumerate(sub.items):
        if isinstance(it, Placement):
            out.append((k, it.part, it.color.ldraw, it.M, it.step))
        else:
            for part, color, M in it.sub.flatten_local():
                out.append((k, part, color.ldraw, it.M @ M, it.step))
    return out


def _bbox(engine, items) -> tuple[np.ndarray, np.ndarray]:
    pts = []
    for _, part, _, M, _ in items:
        lo, hi = engine.geom.mesh(part).bbox
        corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1])
                            for z in (lo[2], hi[2])])
        pts.append(apply(M, corners))
    allp = np.concatenate(pts)
    return allp.min(0), allp.max(0)


def _view_for(engine, items, visible: list[int], new: list[int], hint: str | None) -> str:
    """'above' unless told otherwise, or unless the new parts sit under what is built."""
    if hint:
        return hint
    old = [items[n] for n in visible if n not in set(new)]
    if not new or not old:
        return "above"
    lo_new, hi_new = _bbox(engine, [items[n] for n in new])
    lo_old, hi_old = _bbox(engine, old)
    # LDraw +Y is down: new parts below the old ones' middle, and under them in plan -> below
    below = lo_new[1] > (lo_old[1] + hi_old[1]) / 2
    overlap = (lo_new[0] < hi_old[0] and hi_new[0] > lo_old[0]
               and lo_new[2] < hi_old[2] and hi_new[2] > lo_old[2])
    return "below" if below and overlap else "above"


def plan(engine, model, out_dir: Path) -> dict:
    """Build the render job list and the booklet's step list."""
    out_dir = Path(out_dir)
    order = model.instruction_order()
    front = float(model.meta.get("azimuth_offset", 0.0))
    sets, jobs, steps = {}, [], []
    used_subs = set()
    for sub in model.submodels.values():
        if not sub.items:
            continue
        items = _local_items(sub)
        sets[sub.name] = [{"part": p, "color": c, "matrix": M.tolist()} for _, p, c, M, _ in items]
        for it in sub.items:
            if isinstance(it, Use):
                used_subs.add(it.sub.name)
    number = 0
    for sub_name, s in order:
        sub = model.submodels[sub_name]
        items = _local_items(sub)
        visible = [n for n, it in enumerate(items) if it[4] <= s]
        new = [n for n, it in enumerate(items) if it[4] == s]
        if not new:
            continue
        number += 1
        hint = getattr(sub, "views", {}).get(s)
        view = _view_for(engine, items, visible, new, hint)
        name = f"step_{number:04d}"
        jobs.append({"name": name, "set": sub_name, "visible": visible, "new": new,
                     "azimuth": front + 30, "elevation": 32 if view == "above" else -30})
        parts, subs = {}, {}
        for k in sorted({items[n][0] for n in new}):
            it = sub.items[k]
            if isinstance(it, Placement):
                key = (part_id(it.part), it.color.ldraw)
                parts[key] = parts.get(key, 0) + 1
            else:
                subs[it.sub.name] = subs.get(it.sub.name, 0) + 1
        steps.append(StepInfo(number, sub_name, s, sub.captions[s], f"{name}.jpg",
                              [(p, c, q) for (p, c), q in sorted(parts.items())],
                              sorted(subs.items()), view))
    # finished sub-assemblies (for "build this first" callouts and the overview)
    for name in list(used_subs) + [model.main.name]:
        items = _local_items(model.submodels[name])
        jobs.append({"name": f"sub_{name}", "set": name, "visible": list(range(len(items))),
                     "new": [], "azimuth": front + 30, "elevation": 30, "all_full": True})
    # one picture per part/colour
    combos = sorted({(p.part, p.color.ldraw) for p in model.flatten()}
                    | {(part, color.ldraw) for part, color, _, _ in model.extras}
                    | {(pt, c) for s in sets.values() for pt, c in
                       ((i["part"], i["color"]) for i in s)})
    part_jobs = [{"name": f"part_{part_id(p).replace('/', '_')}_{c}", "part": p, "color": c}
                 for p, c in combos]
    return {"sets": sets, "jobs": jobs, "part_jobs": part_jobs, "steps": steps,
            "used_subs": sorted(used_subs)}


def render(engine, model, out_dir: Path, *, size=(1100, 820), part_px_per_ldu: float = 1.6,
           only_parts: bool = False) -> dict:
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    p = plan(engine, model, out_dir)
    parts = {i["part"] for s in p["sets"].values() for i in s}
    codes = {i["color"] for s in p["sets"].values() for i in s}
    for part in parts:
        codes |= {int(c) for c in np.unique(engine.geom.mesh(part).colors) if c not in (16, 24)}
    colors = {}
    for code in codes:
        lc = engine.lib.colors.get(code)
        if lc is not None:
            colors[str(code)] = {"rgb": lc.rgb, "alpha": lc.alpha, "material": lc.material}
    scene = {"meshes": export_meshes(engine, parts, engine.cache / "blender"), "colors": colors,
             "sets": p["sets"], "jobs": [] if only_parts else p["jobs"],
             "part_jobs": p["part_jobs"], "size": list(size), "out_dir": str(out_dir),
             "part_px_per_ldu": part_px_per_ldu}
    run_blender(scene, out_dir, script=SCRIPT, timeout=7200)
    (out_dir / "plan.json").write_text(json.dumps({
        "steps": [s.__dict__ for s in p["steps"]], "used_subs": p["used_subs"],
        "part_images": {f"{part_id(j['part'])}_{j['color']}": j["name"] + ".png"
                        for j in p["part_jobs"]}}, indent=1))
    return p
