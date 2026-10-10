"""A sorting mat for a class (`brickkit worksheet SLUG` -> out/worksheet.pdf): every piece of a
model as an outline at its real size, one outline for each piece wanted, with its picture and
how many - a child takes pieces from the big bucket and puts one on each outline, and when no
outline is empty has a whole set. Above them half a page about the thing itself.

    [worksheet]                          # model.toml (all optional)
    title = "Build the ..."              # (else the model's name)
    lead = "..."                         # a sentence or two under it
    facts = ["...", "..."]               # the half page: short facts, one a line
    sources = "..."                      # small print under them: where the facts are from
    paper = "Letter"                     # or "A4"
    [worksheet.names]                    # what a child calls a piece: by part, or part/Colour
    3003 = "2 x 2 brick"
    "3069b/Black" = "1 x 2 tile, black"

The pictures are the booklet's (out/booklet/: make the booklet first). An outline is the
piece seen from above, studs up, as it lies on the table - a figure's legs and torso from the
front, lying on their backs. Print it at 100%: the sheet has a 5 cm line to check."""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..bom.bom import build_bom
from .booklet import TEMPLATES, _hex, html_to_pdf

MM = 0.4                  # mm to an LDU
EASE = 0.6                # mm an outline stands off its piece all round: the piece drops in
PAPERS = {"Letter": (215.9, 279.4), "A4": (210.0, 297.0)}
MARGIN = 10.0             # mm
GUTTER = 4.0              # mm between the sheet's two columns of pieces


def _hull(points: np.ndarray) -> np.ndarray:
    """The convex outline of 2-D points, anticlockwise."""
    from scipy.spatial import ConvexHull
    pts = np.unique(np.round(points, 2), axis=0)
    return pts[ConvexHull(pts).vertices]


def outline(engine, parts: list, front: np.ndarray | None = None) -> np.ndarray:
    """The outline (mm; its box's corner at 0, 0; y down the page) of parts [(part, 4 x 4)]
    seen from above, or with `front` (the rows: the picture's across and down, in the parts'
    frame) from the front."""
    pts = []
    for part, M in parts:
        t = engine.geom.mesh(part).tris.reshape(-1, 3)
        if len(t):
            M = np.asarray(M, float)
            pts.append(t @ M[:3, :3].T + M[:3, 3])
    p = np.concatenate(pts)
    flat = p @ np.asarray(front, float).T if front is not None else p[:, [0, 2]]
    h = _hull(flat * MM)
    c = h.mean(0)
    d = h - c
    h = c + d * (1.0 + EASE / np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-6))
    return h - h.min(0)


def _tint(hex_: str, white: float = 0.78) -> str:
    """A colour paled towards the paper, to fill an outline with (a hint of what goes there)."""
    r, g, b = (int(hex_[i:i + 2], 16) for i in (1, 3, 5))
    r, g, b = (round(v + (255 - v) * white) for v in (r, g, b))
    if min(r, g, b) > 244:                             # (white, on white paper: a light grey)
        r = g = b = 238
    return f"#{r:02x}{g:02x}{b:02x}"


def _plain(name: str) -> str:
    """A catalogue name cut down to what a child needs: 'Brick Special 1 x 4 with Masonry
    Brick Profile' -> 'Brick 1 x 4, masonry brick profile'."""
    s = re.sub(r"\s*\[.*?\]", "", name).replace(" Special", "").replace("°", "")
    s = re.sub(r"\s+with\s+", ", ", s, count=1)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:1] + s[1:].lower() if s else name


def build(engine, proj, model) -> dict:
    """What the sheet shows: the page, the words, and a row per piece wanted."""
    img_dir = proj.out / "booklet"
    if not (img_dir / "plan.json").exists():
        raise SystemExit(f"{proj.slug}: no booklet yet (its pictures are the worksheet's): "
                         f"brickkit booklet {proj.slug}")
    plan = json.loads((img_dir / "plan.json").read_text())
    cfg = proj.config.get("worksheet", {})
    names = cfg.get("names", {})
    paper = cfg.get("paper", "Letter")
    if paper not in PAPERS:
        raise SystemExit(f"[worksheet] paper: {', '.join(PAPERS)}")
    placed = model.flatten()
    kits = {name: sub.kit for name, sub in model.submodels.items()
            if getattr(sub, "kit", None) is not None}
    kit_img = {(k.rb_part, k.color.ldraw): f"sub_{name}.png" for name, k in kits.items()}
    groups: dict = {}                                  # a kit's parts as they stand in the model
    for p in placed:
        if getattr(p, "kit", None) is not None:
            groups.setdefault(p.kit, []).append(p)
    rows = []
    for l in build_bom(placed, engine.catalog, model.extras):
        img = ((kit_img.get((l.rb_part, l.color.ldraw)) if l.kind else None)
               or plan["part_images"].get(f"{l.ldraw_part}_{l.color.ldraw}"))
        kit = next((g for g in groups.values() if any(
            q.part.removesuffix(".dat") == l.ldraw_part for q in g)), None) if l.kind else None
        if kit:                                        # (a figure's legs, its torso: from the front)
            R = np.asarray(kit[0].M, float)[:3, :3]
            shape = outline(engine, [(q.part, q.M) for q in kit], front=np.array([R[:, 0], R[:, 1]]))
        else:
            shape = outline(engine, [(l.ldraw_part + ".dat", np.eye(4))])
        w, h = shape.max(0)
        if h > w * 1.01 and h > 20:                    # long things lie across the page
            shape = shape[:, ::-1]
            w, h = h, w
        hex_ = _hex(engine, l.color.ldraw)
        rows.append({
            "qty": l.qty, "img": img, "colour": l.color.name, "hex": hex_, "tint": _tint(hex_),
            "name": names.get(f"{l.ldraw_part}/{l.color.name}") or names.get(l.ldraw_part) or _plain(l.name),
            "w": round(float(w), 2), "h": round(float(h), 2),
            "points": " ".join(f"{x:.2f},{y:.2f}" for x, y in shape),
            "area": float(w * h),
        })
    order = {}
    for r in sorted(rows, key=lambda r: -r["area"]):   # colours by their biggest piece
        order.setdefault(r["colour"], len(order))
    rows.sort(key=lambda r: (order[r["colour"]], -r["area"], r["name"]))
    pw, ph = PAPERS[paper]
    wide = (pw - 2 * MARGIN - GUTTER) / 2              # a column
    big = [r["name"] for r in rows if r["w"] > wide - 6.0]
    if big:
        raise SystemExit(f"worksheet: too wide for a column of {paper} paper: {', '.join(big)}")
    for r in rows:                                     # how many of its outlines fit in a line
        r["across"] = max(1, min(r["qty"], int((wide - 6.0 + 2.0) // (r["w"] + 2.0))))
    return {
        "title": cfg.get("title") or model.name, "lead": cfg.get("lead", ""),
        "facts": list(cfg.get("facts", [])), "sources": cfg.get("sources", ""),
        "name": model.name, "pieces": sum(r["qty"] for r in rows), "rows": rows,
        "cover": "booklet/cover.png" if (img_dir / "cover.png").exists() else None,
        "paper": paper, "page_w": pw, "page_h": ph, "margin": MARGIN, "gutter": GUTTER,
        "site": "bricks.superfun.games",
    }


def make_worksheet(engine, proj, model) -> Path:
    ctx = build(engine, proj, model)
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(["html"]))
    html = proj.out / "worksheet.html"                 # (beside booklet/: its pictures are used)
    html.write_text(env.get_template("worksheet.html.j2").render(**ctx))
    return html_to_pdf(html, proj.out / "worksheet.pdf")
