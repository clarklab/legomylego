"""LEGO-style instruction booklet: HTML (Jinja2, print CSS) -> A4 landscape PDF (Chromium).

Inputs, all produced by other brickkit steps: the instruction pictures and plan
(render/instructions.py), the check report (out/report.json), the parts list, and a cover
render. Text comes from the model's `[booklet]` table in model.toml:

    [booklet]
    subtitle = "..."                     # under the title on the cover
    intro = "..."                        # "About this model" paragraph
    you_will_need = ["...", "..."]       # besides the bricks
    notes = ["...", "..."]               # extra "before you start" notes
    works = [{title = "...", text = "...", image = "hero_open/low.png"}]   # "It works" panels
"""
from __future__ import annotations

import datetime as dt
import json
import shutil
from collections import Counter
from pathlib import Path

import numpy as np
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .. import paths
from ..bom.bom import build_bom
from ..ldraw.library import part_id
from ..ldraw.matrix import apply

TEMPLATES = Path(__file__).with_name("templates")
SITE_URL = "https://lego.superfun.games"


def _dims_cm(engine, placed) -> list[float]:
    lo, hi = np.full(3, np.inf), np.full(3, -np.inf)
    for p in placed:
        a, b = engine.geom.mesh(p.part).bbox
        corners = np.array([[x, y, z] for x in (a[0], b[0]) for y in (a[1], b[1]) for z in (a[2], b[2])])
        w = apply(p.M, corners)
        lo, hi = np.minimum(lo, w.min(0)), np.maximum(hi, w.max(0))
    return [round(v * 0.04, 1) for v in (hi - lo)]


def _hex(engine, code: int) -> str:
    lc = engine.lib.colors.get(code)
    return lc.rgb if lc else "#888888"


def _ranges(nums: list[int]) -> str:
    """[1, 4, 5, 6] -> '1, 4-6'"""
    out, start = [], None
    for k, n in enumerate(nums):
        if start is None:
            start = n
        if k + 1 == len(nums) or nums[k + 1] != n + 1:
            out.append(str(start) if start == n else f"{start}\u2013{n}")
            start = None
    return ", ".join(out)


def build_context(engine, proj, model, img_dir: Path) -> dict:
    plan = json.loads((img_dir / "plan.json").read_text())
    placed = model.flatten()
    cfg = proj.config.get("booklet", {})
    colors = Counter(p.color.ldraw for p in placed)
    colour_rows = [{"name": engine.catalog.color(c).name, "hex": _hex(engine, c), "qty": q}
                   for c, q in colors.most_common()]
    part_images = plan["part_images"]
    titles = {name: sub.title for name, sub in model.submodels.items()}
    counts = Counter()
    for sub in model.submodels.values():
        for it in sub.items:
            if hasattr(it, "sub"):
                counts[it.sub.name] += 1
    steps = []
    last_sub = None
    for s in plan["steps"]:
        new_section = s["submodel"] != last_sub
        last_sub = s["submodel"]
        steps.append({
            **s,
            "title": titles.get(s["submodel"], s["submodel"]),
            "section_start": new_section,
            "is_main": s["submodel"] == model.main.name,
            "repeat": counts.get(s["submodel"], 1),
            "parts": [{"img": part_images.get(f"{p}_{c}"), "qty": q,
                       "name": engine.catalog.part_name(p + ".dat"),
                       "colour": engine.catalog.color(c).name} for p, c, q in s["new_parts"]],
            "subs": [{"img": f"sub_{n}.png", "qty": q, "title": titles.get(n, n)}
                     for n, q in s["new_subs"]],
        })
    sections, seen = [], set()
    for s in steps:
        if s["submodel"] not in seen:
            seen.add(s["submodel"])
            nums = [t["number"] for t in steps if t["submodel"] == s["submodel"]]
            sections.append({"name": s["submodel"], "title": s["title"], "first_step": s["number"],
                             "img": f"sub_{s['submodel']}.png", "repeat": counts.get(s["submodel"], 1),
                             "steps": len(nums), "ranges": _ranges(nums)})
    bom = build_bom(placed, engine.catalog, model.extras)
    inventory = [{"img": part_images.get(f"{l.ldraw_part}_{l.color.ldraw}"), "qty": l.qty,
                  "name": l.name, "colour": l.color.name, "hex": _hex(engine, l.color.ldraw),
                  "element": l.element_id, "bl_part": l.bl_part, "bl_colour": l.color.bl_id,
                  "rare": l.rare} for l in sorted(bom, key=lambda l: (l.color.name, l.name))]
    report = {}
    rp = proj.out / "report.json"
    if rp.exists():
        report = json.loads(rp.read_text())
    checks = [{"name": c["name"].replace("_", " "), "status": c["status"], "summary": c["summary"]}
              for c in report.get("checks", [])]
    stats = {c["name"]: c.get("stats", {}) for c in report.get("checks", [])}
    weight = stats.get("stability", {}).get("mass_g")
    return {
        "name": model.name, "slug": proj.slug,
        "subtitle": cfg.get("subtitle", ""), "intro": cfg.get("intro", ""),
        "you_will_need": cfg.get("you_will_need", []), "notes": cfg.get("notes", []),
        "works": cfg.get("works", []),
        "pieces": sum(l.qty for l in bom), "lines": len(bom), "steps": steps,
        "n_steps": len(steps), "sections": sections, "colours": colour_rows,
        "inventory": inventory, "checks": checks, "overall": report.get("status", "unknown"),
        "dims": _dims_cm(engine, placed), "weight": round(weight) if weight else None,
        "weight_text": (f"{weight / 1000:.1f} kg" if weight and weight >= 1000
                        else f"{round(weight)} g" if weight else None),
        "connections": stats.get("connections", {}).get("connections"),
        "has_mechanism": model.pose is not None, "has_lights": bool(model.lights),
        "cover": "cover.png", "logo": "logo.png", "url": f"{SITE_URL}/m/{proj.slug}",
        "site": SITE_URL, "date": dt.date.today().isoformat(),
        "variant": model.variant,
    }


def render_html(ctx: dict, out_html: Path) -> Path:
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(["html"]))
    html = env.get_template("booklet.html.j2").render(**ctx)
    out_html.write_text(html)
    return out_html


def html_to_pdf(html: Path, pdf: Path) -> Path:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(html.resolve().as_uri(), wait_until="networkidle")
        page.pdf(path=str(pdf), prefer_css_page_size=True, print_background=True)
        browser.close()
    return pdf


def make_booklet(engine, proj, model, *, rerender: bool = True, cover: Path | None = None) -> Path:
    from ..render import instructions
    from ..render.scene import render_model
    img_dir = proj.out / "booklet"
    if rerender or not (img_dir / "plan.json").exists():
        instructions.render(engine, model, img_dir)
    if cover is None:
        cover_img = img_dir / "cover.png"
        if rerender or not cover_img.exists():
            files = render_model(engine, model, img_dir / "cover_render",
                                 views=[{"name": "cover", "azimuth": -20, "elevation": 26,
                                         "lens": 60}],
                                 size=(1400, 1400), samples=128, lights_on=bool(model.lights),
                                 transparent=True, ground=False)
            shutil.copy2(files[0], cover_img)
    else:
        shutil.copy2(cover, img_dir / "cover.png")
    shutil.copy2(paths.ROOT / "logo.png", img_dir / "logo.png")
    shutil.copy2(TEMPLATES / "booklet.css", img_dir / "booklet.css")
    ctx = build_context(engine, proj, model, img_dir)
    for k, w in enumerate(ctx["works"]):                 # images are paths under out/
        src = proj.out / w["image"]
        if src.exists():
            dst = img_dir / f"works_{k}{src.suffix}"
            shutil.copy2(src, dst)
            ctx["works"][k] = {**w, "image": dst.name}
    html = render_html(ctx, img_dir / "booklet.html")
    return html_to_pdf(html, proj.out / "booklet.pdf")
