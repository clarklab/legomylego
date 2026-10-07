"""A showreel's companion segment: smaller builds featured with the model (its `[[companions]]`
in model.toml, the same blocks the site shows in their own section), each with `video = true`.

After the booklet, before the outro, each companion gets COMPANION_BEATS beats: its eyebrow and
heading, its own turntable loop on a card, chips for its pieces, steps and Pick a Brick price,
then the scale beat - the model's hero cut-out beside a cut-out of the companion at the same
scale, each measured by its height. Nothing is rendered in 3D for it but the companion's
transparent hero still (a Cycles still, cached like the title's); its turntable is the one
`brickkit turntable` made (out/turntable.mp4), turned into frames as the sizzle reel does.

    [[companions]]
    slug = "caldwell_mini"
    eyebrow = "Kids' build"          # the label over the heading (else "Also")
    heading = "The mini courthouse"  # (else the companion's name)
    price = { pick_a_brick = 9.87 }  # a chip: about $10 on Pick a Brick
    video = true                     # feature it in the showreel
    video_chips = ["pieces", "steps", "price"]   # optional: which chips, in order
"""
from __future__ import annotations

import shutil
from pathlib import Path

COMPANION_BEATS = 10            # per companion
CHIPS = ("pieces", "steps", "price")


def video_companions(config: dict) -> list[dict]:
    """The model.toml's [[companions]] blocks featured in the video (video = true)."""
    return [dict(c) for c in config.get("companions", []) or [] if c.get("video")]


def _height_mm(engine, placed) -> float:
    from .timeline import corners
    C = corners(engine, placed).reshape(-1, 3)
    return float(C[:, 1].max() - C[:, 1].min()) * 0.4


def size_label(mm: float) -> str:
    """'65 cm' (whole centimetres from 10 cm up), '6.4 cm' (one decimal below), '9 mm'."""
    if mm < 10:
        return f"{mm:.0f} mm"
    if mm < 100:
        return f"{mm / 10:.1f} cm".replace(".0 cm", " cm")
    return f"{mm / 10:.0f} cm"


def solid_box(path: Path, alpha: int = 200) -> list[float] | None:
    """The box (0..1 of the image) of a cut-out's solid pixels: the model, not its shadow (so
    it can stand on a line)."""
    import numpy as np
    from PIL import Image
    with Image.open(path) as im:
        a = np.asarray(im.convert("RGBA"))[:, :, 3]
    ys, xs = np.nonzero(a > alpha)
    if not len(xs):
        return None
    h, w = a.shape
    return [round(xs.min() / w, 5), round(ys.min() / h, 5), round((xs.max() + 1) / w, 5),
            round((ys.max() + 1) / h, 5)]


def clean_cutout(src: Path, dst: Path) -> Path:
    """A copy of a cut-out for standing on the reel's backdrop: its shadow catcher's faint veil
    over the whole picture taken out (alpha lowered by 12, continuously, so nothing shows a
    contour) and faded to nothing near the picture's edges, so no rectangle shows; the model
    and the shadow under it stay. Made again only when the source is newer."""
    import numpy as np
    from PIL import Image
    if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
        return dst
    with Image.open(src) as im:
        a = np.asarray(im.convert("RGBA")).astype(np.float32)
    h, w = a.shape[:2]
    al = np.clip((a[:, :, 3] - 12.0) * 255.0 / 243.0, 0, 255)
    edge = lambda n: np.clip(np.minimum(np.arange(n), np.arange(n)[::-1]) / (0.08 * n), 0, 1)  # noqa: E731
    al *= np.outer(edge(h), edge(w))
    a[:, :, 3] = np.where(a[:, :, 3] > 250, 255, al)
    dst.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(a.round().astype(np.uint8), "RGBA").save(dst)
    return dst


def price_label(usd: float) -> str:
    """About what it costs: '$10' (to the dollar from $5 up, rounded), else '$4.50'."""
    return f"${usd:,.0f}" if usd >= 5 else f"${usd:.2f}"


def companion_info(engine, proj, block: dict) -> dict:
    """What the segment shows of one companion: its name, eyebrow, heading, pieces, steps,
    height, Pick a Brick price and where its footage is (its out/: turntable.mp4, hero)."""
    from ..bom.bom import build_bom
    from ..project import Project
    cp = Project(block["slug"], proj.dir.parent)
    model = cp.build(engine.catalog)
    placed = model.flatten()
    pieces = int(sum(line.qty for line in build_bom(placed, engine.catalog,
                                                    getattr(model, "extras", ()))))
    price = (block.get("price") or {}).get("pick_a_brick")
    chips = []
    for k in block.get("video_chips") or CHIPS:
        if k == "pieces":
            chips.append({"value": f"{pieces:,}", "label": "pieces"})
        elif k == "steps":
            chips.append({"value": f"{len(model.instruction_order()):,}", "label": "steps"})
        elif k == "price" and price:
            chips.append({"value": "~" + price_label(float(price)), "label": "Pick a Brick"})
    tt = cp.out / "turntable.mp4"
    return {"slug": cp.slug, "name": model.name, "model": model, "out": cp.out,
            "eyebrow": block.get("eyebrow") or "Also", "heading": block.get("heading") or model.name,
            "pieces": pieces, "steps": len(model.instruction_order()),
            "height_mm": round(_height_mm(engine, placed), 1),
            "price": float(price) if price else None, "chips": chips,
            "turntable": tt if tt.exists() else None}


def prepare(engine, proj, blocks: list[dict], work: Path, size: int, render: bool,
            log=print) -> list[dict]:
    """Each featured companion's info and footage under work/companions/<slug>/: its turntable
    as frames (turntable/00000.jpg ..., at the video's frame rate) and a transparent hero
    cut-out (hero_cut, rendered once when `render`; else the companion's opaque hero)."""
    from . import hero_cutout
    from .reel import hero
    from .sizzle import turntable_frames
    from .timeline import FPS, corners, shape_of
    out = []
    for block in blocks:
        info = companion_info(engine, proj, block)
        d = work / "companions" / info["slug"]
        frames = 0
        if info["turntable"] is not None:
            frames = turntable_frames(info["turntable"], d / "turntable", size, FPS)
        else:
            log(f"companion {info['slug']}: no out/turntable.mp4 (brickkit turntable "
                f"{info['slug']}); its hero instead")
        model = info.pop("model")
        shape = shape_of(corners(engine, model.flatten()).reshape(-1, 3),
                         float(model.meta.get("azimuth_offset", 0.0)))
        cut = hero_cutout(engine, model, info["out"], shape, render, log, dest=d)
        h = hero(info["out"], cut)
        if h is not None and h["cutout"]:
            clean_cutout(cut, d / "cut.png")
            h["url"] = f"work/companions/{info['slug']}/cut.png"
            h["box"] = [round(float(v), 5) for v in h["box"]]
            h["stand"] = solid_box(cut)
        elif h is not None:                       # the opaque site hero, copied beside it
            shutil.copyfile(info["out"] / "hero" / "hero.png", d / "hero.png")
            h["url"] = f"work/companions/{info['slug']}/hero.png"
        info.update(turntable_frames=frames, cut=h, out=str(info["out"]),
                    turntable=str(info["turntable"]) if info["turntable"] else None)
        out.append(info)
    return out


def graphics(items: list[dict], stats: dict, hero_file: Path | None = None,
             work: Path | None = None) -> list[dict]:
    """The compositor's companions: per companion its texts, chips, turntable frames (URL
    pattern and count), cut-out, the scale beat's heights (the model's and its own, mm, with
    their labels) and the model's own cut-out (`big`: a clean copy in work/companions/, its
    solid box `stand`), or None without a transparent one."""
    big = None
    if hero_file is not None and Path(hero_file).exists() and work is not None:
        clean_cutout(Path(hero_file), Path(work) / "companions" / "hero.png")
        big = {"url": "work/companions/hero.png", "stand": solid_box(Path(hero_file))}
    out = []
    for it in items:
        out.append({
            "slug": it["slug"], "eyebrow": it["eyebrow"], "heading": it["heading"],
            "chips": it["chips"],
            "turntable": ({"url": f"work/companions/{it['slug']}/turntable/", "n": it["turntable_frames"]}
                          if it["turntable_frames"] else None),
            "cut": it["cut"], "big": big,
            "scale": {"big_mm": float(stats["dims_mm"][2]), "small_mm": it["height_mm"],
                      "big": size_label(float(stats["dims_mm"][2])),
                      "small": size_label(it["height_mm"])}})
    return out


def marks(seg: dict, n: int, B: int) -> dict:
    """Each companion's moments in the segment (COMPANION_BEATS beats apiece): the heading,
    its card, its chips, the scale beat (the model, the companion dropping in beside it, the
    measures drawn)."""
    span = (seg["end"] - seg["start"]) // max(1, n)
    items = []
    for k in range(n):
        a = seg["start"] + k * span
        items.append({"start": a, "end": a + span, "head": a + B // 2, "card": a + B,
                      "chips": [a + 2 * B + j * B // 2 for j in range(3)],
                      "scale": a + int(5.5 * B), "drop": a + int(6.5 * B),
                      "measure": a + int(7.25 * B)})
    return {"items": items}


def cues(m: dict, add) -> None:
    """The segment's sound effects: a whoosh as the heading rises, a pop as the card lands,
    blips for the chips, a whoosh into the scale beat, the companion's snap as it lands, ticks
    as the measures draw."""
    for it in m["items"]:
        add(it["head"] - 4, "whoosh", dur=6, gain=0.5)
        add(it["card"] + 4, "pop", gain=0.7)
        for j, f in enumerate(it["chips"]):
            add(f, "blip", pitch=j)
        add(it["scale"] - 6, "whoosh", dur=8, gain=0.55)
        add(it["drop"] + 6, "snap", gain=0.8)
        for j in range(4):
            add(it["measure"] + 3 * j, "tick", gain=0.3)
