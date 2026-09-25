"""Hero renders for a model's site page and booklet: out/hero (plain), out/hero_lit (lights on),
out/hero_open (mechanism at the end of its range).

    python tools/hero.py SLUG [--size 1000] [--samples 128]
"""
import argparse

from brickkit import paths
from brickkit.engine import Engine
from brickkit.project import Project
from brickkit.render.scene import render_model

ap = argparse.ArgumentParser()
ap.add_argument("slug")
ap.add_argument("--size", type=int, default=1000)
ap.add_argument("--samples", type=int, default=128)
ap.add_argument("--only", help="comma list of hero, hero_lit, hero_open")
args = ap.parse_args()
engine = Engine()
proj = Project(args.slug, paths.MODELS_DIR)
model = proj.build(engine.catalog)
view = {"name": "hero", "azimuth": -35, "elevation": 22, "lens": 60}
jobs = [("hero", dict(views=[view]))]
if model.lights:
    jobs.append(("hero_lit", dict(views=[{**view, "name": "hero", "elevation": 30}],
                                  lights_on=True)))
if model.pose is not None:
    # a low view shows a tall model's underside (the Metroid's fangs); a flat one needs height
    el = float(model.meta.get("hero_open_elevation", 18))
    jobs.append(("hero_open", dict(views=[{"name": "hero", "azimuth": -25, "elevation": el,
                                           "lens": 60}], pose_t=1.0)))
if args.only:
    jobs = [j for j in jobs if j[0] in args.only.split(",")]
for out, kw in jobs:
    files = render_model(engine, model, proj.out / out, size=(args.size, args.size),
                         samples=args.samples, **kw)
    print("rendered", *files)
