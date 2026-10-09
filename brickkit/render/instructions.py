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
from .scene import BLENDER, MESHES, _colors, export_meshes, run_blender

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
    also: list = field(default_factory=list)    # small extra pictures for new parts the main one
                                                # cannot show: [{"image", "text"}]


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


SEEN = 0.3            # of what could ever show of a piece: with less it is not "in the picture"
LEAST = 0.06          # ... and with less than this in every picture it cannot be shown at all
FADE = 0.72           # how pale what is built is drawn in such a piece's own picture (the step
                      # pictures' 0.38 leaves a black piece on dark grey: hard to make out)
# the pictures' cameras: (degrees round from the step pictures' own azimuth, elevation)
LOOKS = {"above": (0, 32), "below": (0, -30), "behind": (180, 32), "behind_below": (180, -30)}
# where a piece the step's own picture does not show is looked for, in turn: (picture, the
# camera for a step seen from above / from below, with the step's other pieces on?, its words)
EXTRA = [("under", ("below", "above"), True,
          ("From below: the outlined piece{s} click{v} in here.", "From above: the outlined piece{s}.")),
         ("behind", ("behind", "behind_below"), True, ("From behind: the outlined piece{s}.",) * 2),
         ("behind_under", ("behind_below", "behind"), True,
          ("From behind and below: the outlined piece{s}.", "From behind: the outlined piece{s}.")),
         ("first", ("above", "below"), False,
          ("First the outlined piece{s}: the others go on over {it}.",) * 2)]


def _extra_pictures(sight, items, visible: list[int], new: list[int], view: str) -> tuple[dict, list]:
    """Where each new piece of a step can be seen, by measuring (render/visibility.py). A piece
    the step's own picture does not show (less than SEEN of it) is looked for in the EXTRA
    pictures in turn: from the other side with everything on (it is seen where it clicks in),
    from behind, and last on its own with what was built before (it goes on first, the rest
    over it). A sub-assembly counts as one piece. `sight(look)`: the Sight from a LOOKS
    camera. Returns ({picture: part indices}, the part indices no picture shows)."""
    groups: dict = {}
    for n in new:
        groups.setdefault(items[n][0], []).append(n)
    fresh = set(new)
    old = [v for v in visible if v not in fresh]
    flat = lambda gs: [n for g in gs for n in g]       # noqa: E731

    def shows(g, look, shown) -> bool:
        return float(np.mean([sight(look).seen(n, shown) for n in g])) >= SEEN

    out: dict = {}
    rest = [g for g in groups.values() if not shows(g, view, visible)]
    for key, looks, whole, _ in EXTRA:
        if not rest:
            break
        look = looks[0 if view == "above" else 1]
        shown = visible if whole else old + flat(rest)
        got = [g for g in rest if shows(g, look, shown)]
        if got:
            out[key] = flat(got)
            rest = [g for g in rest if g not in got]
    for g in list(rest):                               # mostly inside something (an axle through
        best = (LEAST, None)                           # its holes): where the most of it shows
        for key, looks, whole, _ in EXTRA:
            look = looks[0 if view == "above" else 1]
            shown = visible if whole else old + flat(rest)
            frac = float(np.mean([sight(look).seen(n, shown) for n in g]))
            if frac > best[0]:
                best = (frac, key)
        if best[1]:
            out.setdefault(best[1], []).extend(g)
            rest.remove(g)
    return out, flat(rest)


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
    sights: dict = {}
    unseen: list = []                                  # pieces no picture of their step shows
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
        main = {"name": name, "set": sub_name, "visible": visible, "new": new,
                "azimuth": front + 30, "elevation": LOOKS[view][1],
                "highlight": len(visible) > len(new)}
        jobs.append(main)
        parts, subs = {}, {}
        for k in sorted({items[n][0] for n in new}):
            it = sub.items[k]
            if isinstance(it, Placement):
                key = (part_id(it.part), it.color.ldraw)
                parts[key] = parts.get(key, 0) + 1
            else:
                subs[it.sub.name] = subs.get(it.sub.name, 0) + 1
        also = []

        def sight(look, sub_name=sub_name, items=items):          # (made when first asked for)
            if (sub_name, look) not in sights:
                from .visibility import Sight
                turn, el = LOOKS[look]
                sights[sub_name, look] = Sight(engine, [(it[1], it[3]) for it in items], front + 30 + turn, el)
            return sights[sub_name, look]

        where, nowhere = _extra_pictures(sight, items, visible, new, view)
        before = [v for v in visible if v not in set(new)]
        k_ = 0 if view == "above" else 1
        whole_ = {key: looks[k_] for key, looks, whole, _ in EXTRA if whole}
        if (not hint and not nowhere and len(where) == 1 and next(iter(where)) in whole_
                and len(where[next(iter(where))]) == len(new)):
            # none of the step's pieces show in its picture and all of them show from one
            # other side: that is the step's picture, then (tiles on a wall's far face)
            view = whole_[next(iter(where))]
            main["azimuth"], main["elevation"] = front + 30 + LOOKS[view][0], LOOKS[view][1]
            where = {}
        for key, looks, whole, words in EXTRA:
            if key not in where:
                continue
            turn, el = LOOKS[looks[k_]]
            many = len({items[n][0] for n in where[key]}) > 1
            jobs.append({"name": f"{name}_{key}", "set": sub_name, "new": where[key], "fade": FADE,
                         "visible": visible if whole else before + where[key],
                         "azimuth": front + 30 + turn, "elevation": el, "highlight": True})
            also.append({"image": f"{name}_{key}.jpg",
                         "text": words[k_].format(s="s" if many else "", v="" if many else "s",
                                                  it="them" if many else "it")})
        for n in nowhere:
            unseen.append({"step": number, "submodel": sub_name, "part": part_id(items[n][1])})
        steps.append(StepInfo(number, sub_name, s, sub.captions[s], f"{name}.jpg",
                              [(p, c, q) for (p, c), q in sorted(parts.items())],
                              sorted(subs.items()), view, also))
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
            "used_subs": sorted(used_subs), "unseen": unseen}


HIGHLIGHT = (255, 205, 0)          # ring round the new parts of a step
HIGHLIGHT_EDGE = (28, 28, 28)


def outline_new_parts(image: Path, mask: Path, width: int = 5, close: bool = False) -> None:
    """Draw a yellow ring with a thin dark edge around the new parts' visible pixels. `close`
    (a step's second, small picture): then cut the picture down to the ringed parts and what
    is round them - in a picture of the whole model a 1 x 1 plate is a speck."""
    from PIL import Image, ImageChops, ImageFilter
    if not mask.exists():
        return
    img = Image.open(image).convert("RGB")
    m = Image.open(mask).convert("L").point(lambda v: 255 if v > 127 else 0)
    box = m.getbbox()
    if m.size != img.size or not box:
        mask.unlink()
        return
    inner = m.filter(ImageFilter.MaxFilter(2 * width + 1))
    outer = inner.filter(ImageFilter.MaxFilter(3))
    img.paste(Image.new("RGB", img.size, HIGHLIGHT_EDGE), mask=ImageChops.subtract(outer, m))
    img.paste(Image.new("RGB", img.size, HIGHLIGHT), mask=ImageChops.subtract(inner, m))
    if close:
        W, H = img.size
        w = min(W, max(3.0 * (box[2] - box[0]), 0.5 * W))    # (half the model round it, at least:
        h = min(H, max(3.0 * (box[3] - box[1]), w * 0.75))  # an edge or a corner to find it by)
        w = min(W, max(w, h / 0.75))
        cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        x0 = int(min(max(cx - w / 2, 0), W - w))
        y0 = int(min(max(cy - h / 2, 0), H - h))
        img = img.crop((x0, y0, int(x0 + w), int(y0 + h)))
    img.save(image, quality=88)
    mask.unlink()


def render(engine, model, out_dir: Path, *, size=(1100, 820), part_px_per_ldu: float = 1.6,
           only_parts: bool = False) -> dict:
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    p = plan(engine, model, out_dir)
    parts = ({i["part"] for s in p["sets"].values() for i in s}
             | {j["part"] for j in p["part_jobs"]})         # incl. bought-only extras
    codes = {i["color"] for s in p["sets"].values() for i in s}
    for part in parts:
        codes |= {int(c) for c in np.unique(engine.geom.mesh(part).colors) if c not in (16, 24)}
    colors = {}
    for code in codes:
        lc = engine.lib.colors.get(code)
        if lc is not None:
            colors[str(code)] = {"rgb": lc.rgb, "alpha": lc.alpha, "material": lc.material}
    scene = {"meshes": export_meshes(engine, parts, engine.cache / MESHES), "colors": colors,
             "sets": p["sets"], "jobs": [] if only_parts else p["jobs"],
             "part_jobs": p["part_jobs"], "size": list(size), "out_dir": str(out_dir),
             "part_px_per_ldu": part_px_per_ldu}
    run_blender(scene, out_dir, script=SCRIPT, timeout=7200)
    for job in scene["jobs"]:
        if job.get("highlight"):
            outline_new_parts(out_dir / f"{job['name']}.jpg", out_dir / f"{job['name']}_mask.png",
                              close=job["name"].endswith(tuple("_" + e[0] for e in EXTRA)))
    (out_dir / "plan.json").write_text(json.dumps({
        "steps": [s.__dict__ for s in p["steps"]], "used_subs": p["used_subs"], "unseen": p["unseen"],
        "part_images": {f"{part_id(j['part'])}_{j['color']}": j["name"] + ".png"
                        for j in p["part_jobs"]}}, indent=1))
    return p
