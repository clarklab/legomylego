"""Export a model for the viewer site: site/models/<slug>/{model.glb, model.json, ...} and the
site-wide index site/models.json.

GLB: one mesh per (part, fixed colour) in the part's own LDraw frame; one node per placed part
named "p<i>" (main colour, recoloured by the site per colourway) plus "p<i>c<code>" nodes for
sub-pieces that have their own fixed colour. Node matrices map LDraw (LDU, -Y up) to glTF
metres (+Y up, front toward +Z): C = diag(0.0004, -0.0004, -0.0004).

JSON: see `model_json` for the schema; poses are 4x4 row-major matrices in glTF space that
pre-multiply each moving node's rest matrix."""
from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

import numpy as np
import trimesh

from . import paths
from .bom.bom import build_bom
from .ldraw.library import part_id

LDU_M = 0.0004
C = np.diag([LDU_M, -LDU_M, -LDU_M, 1.0])
C_INV = np.linalg.inv(C)
SITE_DIR = paths.ROOT / "site"


def to_gltf(M: np.ndarray) -> np.ndarray:
    """A pose (world-space LDraw transform) expressed in glTF space."""
    return C @ M @ C_INV


def _part_meshes(engine, part: str) -> dict[int, trimesh.Trimesh]:
    """{colour code (16 = main): mesh in LDU} with smooth normals split at 35 degrees."""
    m = engine.geom.mesh(part)
    out = {}
    for code in np.unique(m.colors):
        tris = m.tris[m.colors == code]
        if len(tris) == 0:
            continue
        v = tris.reshape(-1, 3)
        f = np.arange(len(v)).reshape(-1, 3)
        tm = trimesh.Trimesh(vertices=v, faces=f, process=True)
        try:
            tm = tm.smoothed(angle=math.radians(35))
        except Exception:
            pass
        out[int(code)] = tm
    return out


def export_glb(engine, placed, path: Path) -> None:
    scene = trimesh.Scene()
    cache: dict[str, dict[int, trimesh.Trimesh]] = {}
    for p in placed:
        if p.part not in cache:
            cache[p.part] = _part_meshes(engine, p.part)
            for code, tm in cache[p.part].items():
                scene.add_geometry(tm, geom_name=f"{part_id(p.part)}__{code}")
        world = C @ p.M
        for code in cache[p.part]:
            name = f"p{p.index}" if code == 16 else f"p{p.index}c{code}"
            scene.graph.update(frame_to=name, frame_from=scene.graph.base_frame,
                               matrix=world, geometry=f"{part_id(p.part)}__{code}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(scene.export(file_type="glb"))


def _colors(engine, codes) -> dict:
    out = {}
    for code in sorted(codes):
        lc = engine.lib.colors.get(code)
        c = engine.catalog.colors.by_code.get(code)
        if lc is not None:
            out[str(code)] = {"name": c.name if c else lc.name, "hex": lc.rgb, "alpha": lc.alpha,
                              "material": lc.material}
    return out


def _fixed_codes(engine, placed) -> set:
    codes = set()
    for part in {p.part for p in placed}:
        codes |= {int(c) for c in np.unique(engine.geom.mesh(part).colors) if c not in (16, 24)}
    return codes


def model_json(engine, proj, model, placed, *, files: dict, variants: list[tuple]) -> dict:
    order = model.instruction_order()
    steps = [{"index": n, "submodel": sub, "caption": model.submodels[sub].captions[s],
              "local_step": s} for n, (sub, s) in enumerate(order)]
    nodes = []
    for p in placed:
        nodes.append({"part": part_id(p.part), "name": engine.catalog.part_name(p.part),
                      "join": p.build_order, "sub": p.owner, "local_step": p.local_step,
                      "group": model.group_of(p)})
    # geometry extents in mm
    lo, hi = np.full(3, np.inf), np.full(3, -np.inf)
    for p in placed:
        a, b = engine.geom.mesh(p.part).bbox
        corners = np.array([[x, y, z] for x in (a[0], b[0]) for y in (a[1], b[1]) for z in (a[2], b[2])])
        w = corners @ p.M[:3, :3].T + p.M[:3, 3]
        lo, hi = np.minimum(lo, w.min(0)), np.maximum(hi, w.max(0))
    dims = ((hi - lo) * 0.4).round(1).tolist()
    mech = None
    if model.pose is not None:
        samples = [round(float(t), 4) for t in np.linspace(0, 1, 25)]
        poses = []
        for t in samples:
            pose = model.pose(t)
            poses.append({g: to_gltf(pose[g]).reshape(-1).round(6).tolist()
                          for g in model.groups if g in pose})
        mech = {"groups": list(model.groups), "samples": samples, "poses": poses}
    lights = []
    for light in model.lights:
        ldu = model.light_position(light, placed)
        if ldu is not None:
            pos = (C @ np.append(ldu, 1.0))[:3]
            lights.append({"name": light["name"], "pos": pos.round(5).tolist(),
                           "color": light["color"], "power": light["power"]})
    glow = [{"tag": t, "strength": s} for t, s in model.glow_tags.items()]
    glow_nodes = sorted({p.index for p in placed for t in model.glow_tags if t in p.tags})
    codes = set(_fixed_codes(engine, placed))
    var_out = []
    for name, title, vmodel in variants:
        vplaced = vmodel.flatten()
        codes |= {p.color.ldraw for p in vplaced}
        var_out.append({"name": name, "title": title, "colors": [p.color.ldraw for p in vplaced],
                        "bom": _bom_rows(engine, vplaced, vmodel.extras)})
    report_path = proj.out / "report.json"
    checks = []
    if report_path.exists():
        rep = json.loads(report_path.read_text())
        checks = [{"name": c["name"], "status": c["status"], "summary": c["summary"]}
                  for c in rep["checks"]]
    return {
        "slug": proj.slug, "name": model.name,
        "description": proj.config.get("model", {}).get("description", ""),
        "parts": len(placed), "dims_mm": dims,
        "front_azimuth": float(model.meta.get("azimuth_offset", 0.0)),
        "colors": _colors(engine, codes), "variants": var_out,
        "nodes": nodes, "steps": steps, "mechanism": mech, "lights": lights,
        "glow_nodes": glow_nodes, "glow": glow, "checks": checks, "files": files,
    }


def _bom_rows(engine, placed, extras=()) -> list[dict]:
    return [{"qty": l.qty, "part": l.ldraw_part, "name": l.name, "colour": l.color.name,
             "hex": engine.lib.colors[l.color.ldraw].rgb if l.color.ldraw in engine.lib.colors else "",
             "element_id": l.element_id, "bricklink_part": l.bl_part,
             "bricklink_colour": l.color.bl_id, "rare": l.rare}
            for l in build_bom(placed, engine.catalog, extras)]


def export_model(engine, proj, model, site_dir: Path | None = None) -> Path:
    site = Path(site_dir or SITE_DIR)
    dst = site / "models" / proj.slug
    dst.mkdir(parents=True, exist_ok=True)
    placed = model.flatten()
    export_glb(engine, placed, dst / "model.glb")
    files = {"glb": "model.glb"}
    for name, src in [("mpd", proj.out / f"{proj.slug}.mpd"), ("booklet", proj.out / "booklet.pdf"),
                      ("video", proj.out / "video.mp4"), ("parts_csv", proj.out / "parts.csv"),
                      ("bricklink_xml", proj.out / "bricklink_wanted.xml"),
                      ("pick_a_brick_csv", proj.out / "pick_a_brick.csv")]:
        if src.exists():
            shutil.copy2(src, dst / src.name)
            files[name] = src.name
    renders = []
    for d in ("renders", "hero"):
        for png in sorted((proj.out / d).glob("*.png")) if (proj.out / d).exists() else []:
            target = dst / "renders" / f"{d}_{png.name}"
            target.parent.mkdir(exist_ok=True)
            shutil.copy2(png, target)
            renders.append(f"renders/{target.name}")
    files["renders"] = renders
    variants = [("default", proj.config.get("model", {}).get("palette_title", "Standard"), model)]
    for name in proj.variants():
        variants.append((name, proj.variant_title(name), proj.build(engine.catalog, name)))
    data = model_json(engine, proj, model, placed, files=files, variants=variants)
    (dst / "model.json").write_text(json.dumps(data, separators=(",", ":")))
    update_index(site)
    return dst


def update_index(site: Path) -> None:
    items = []
    for mj in sorted((site / "models").glob("*/model.json")):
        if mj.parent.name.startswith("_"):
            continue                                   # test models stay off the index
        d = json.loads(mj.read_text())
        items.append({"slug": d["slug"], "name": d["name"], "description": d.get("description", ""),
                      "parts": d["parts"], "dims_mm": d["dims_mm"],
                      "variants": [v["title"] for v in d["variants"]],
                      "thumbnail": (d["files"].get("renders") or [None])[0],
                      "status": ("pass" if all(c["status"] != "fail" for c in d["checks"])
                                 else "fail") if d["checks"] else "unknown"})
    (site / "models.json").write_text(json.dumps({"models": items}, indent=2))
