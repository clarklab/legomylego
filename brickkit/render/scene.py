"""Export a model as a scene description and render it with Blender (headless)."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import numpy as np

from ..ldraw.matrix import apply

BLENDER = os.environ.get("BRICKKIT_BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender")
SCRIPT = Path(__file__).with_name("blender_scene.py")

# name -> (azimuth, elevation) in degrees; azimuth 0 looks at the model's front (LDraw -Z)
VIEWS = {
    "front": (0, 8), "three_quarter": (-35, 22), "three_quarter_right": (35, 22),
    "side": (90, 6), "back": (180, 15), "top": (0, 80), "low": (-25, -8),
}


def view_spec(name: str, lens: float = 70.0, ortho: bool = False) -> dict:
    az, el = VIEWS[name]
    return {"name": name, "azimuth": az, "elevation": el, "lens": lens, "ortho": ortho}


def export_meshes(engine, parts, mesh_dir: Path) -> dict[str, str]:
    mesh_dir.mkdir(parents=True, exist_ok=True)
    out = {}
    for part in sorted(parts):
        f = mesh_dir / (part.replace("/", "__") + ".npz")
        src = engine.lib.resolve(part)
        if not f.exists() or (src and f.stat().st_mtime < src.stat().st_mtime):
            m = engine.geom.mesh(part)
            np.savez_compressed(f, tris=m.tris.astype(np.float32), colors=m.colors,
                                edges=m.edges.astype(np.float32), edge_colors=m.edge_colors)
        out[part] = str(f)
    return out


def _colors(engine, placed) -> dict:
    codes = {p.color.ldraw for p in placed}
    for part in {p.part for p in placed}:
        codes |= {int(c) for c in np.unique(engine.geom.mesh(part).colors) if c not in (16, 24)}
    out = {}
    for code in codes:
        lc = engine.lib.colors.get(code)
        if lc is not None:
            out[str(code)] = {"name": lc.name, "rgb": lc.rgb, "alpha": lc.alpha,
                              "material": lc.material}
    return out


def bounds(engine, placed) -> list[list[float]]:
    pts = []
    for p in placed:
        lo, hi = engine.geom.mesh(p.part).bbox
        corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1])
                            for z in (lo[2], hi[2])])
        pts.append(apply(p.M, corners))
    allp = np.concatenate(pts)
    return [allp.min(0).tolist(), allp.max(0).tolist()]


def model_scene(engine, model, *, pose_t: float | None = None, lights_on: bool = False,
                placed=None) -> dict:
    """Scene dict (meshes, instances, colours, lights) without render settings."""
    if placed is None:
        pose = model.pose(pose_t) if (pose_t is not None and model.pose) else None
        placed = model.flatten(pose=pose)
    meshes = export_meshes(engine, {p.part for p in placed}, engine.cache / "blender")
    instances = []
    for p in placed:
        glow = 0.0
        if lights_on:
            for tag, strength in model.glow_tags.items():
                if tag in p.tags:
                    glow = strength
        instances.append({"part": p.part, "color": p.color.ldraw, "matrix": p.M.tolist(),
                          "glow": glow, "order": p.build_order, "tags": list(p.tags)})
    lights = []
    if lights_on:
        for light in model.lights:
            found = model.find(light["part"], placed)
            if found:
                lights.append({"pos": found[0].M[:3, 3].tolist(), "color": light["color"],
                               "power": light["power"]})
    return {"meshes": meshes, "instances": instances, "colors": _colors(engine, placed),
            "bounds": bounds(engine, placed), "lights": lights}


def run_blender(scene: dict, work_dir: Path, script: Path = SCRIPT, timeout: int = 3600) -> str:
    work_dir.mkdir(parents=True, exist_ok=True)
    sf = work_dir / "scene.json"
    sf.write_text(json.dumps(scene))
    cmd = [BLENDER, "-b", "--factory-startup", "-P", str(script), "--", str(sf)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0 or "BRICKKIT_DONE" not in r.stdout:
        raise RuntimeError("Blender failed:\n" + r.stdout[-4000:] + "\n" + r.stderr[-4000:])
    return r.stdout


def render_model(engine, model, out_dir, *, views=("three_quarter",), size=900, samples=64,
                 pose_t: float | None = None, lights_on: bool = False, background="#F7F8FA",
                 ground: bool = True, transparent: bool = False, lens: float = 70.0,
                 placed=None) -> list[Path]:
    out_dir = Path(out_dir).resolve()
    scene = model_scene(engine, model, pose_t=pose_t, lights_on=lights_on, placed=placed)
    w, h = (size, size) if isinstance(size, int) else size
    scene.update({
        "views": [v if isinstance(v, dict) else view_spec(v, lens) for v in views],
        "size": [w, h], "samples": samples, "background": background, "ground": ground,
        "transparent": transparent, "out_dir": str(out_dir),
    })
    run_blender(scene, out_dir)
    return [out_dir / f"{v['name']}.png" for v in scene["views"]]
