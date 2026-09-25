"""brickkit command line: fetch | new | build | verify | bom | all"""
from __future__ import annotations

import argparse

from . import paths


def _out(proj, variant):
    d = proj.out / "variants" / variant if variant else proj.out
    d.mkdir(parents=True, exist_ok=True)
    return d


def _build(engine, slug, variant=None):
    from .io.mpd import write_mpd
    from .project import Project
    proj = Project(slug, paths.MODELS_DIR)
    model = proj.build(engine.catalog, variant)
    placed = model.flatten()
    out = write_mpd(model, _out(proj, variant) / f"{slug}.mpd")
    print(f"{model.name}: {len(placed)} parts, {len(model.instruction_order())} steps -> {out}")
    return proj, model


def _verify(engine, proj, model, names=None) -> int:
    from .checks import run_checks
    from .checks.report import write_report
    results = run_checks(engine.context(model, proj.checks_config), names)
    out = _out(proj, model.variant)
    data = write_report(results, out, model.name + (f" ({model.variant})" if model.variant else ""))
    for r in results:
        print(f"[{r.status.upper()}] {r.name}: {r.summary}")
        for item in r.items[:5]:
            print(f"        {item}")
    print(f"overall: {data['status'].upper()} -> {out / 'report.html'}")
    return 1 if data["status"] == "fail" else 0


def _bom(engine, proj, model) -> None:
    from .bom.bom import build_bom, write_bricklink_xml, write_parts_csv, write_pick_a_brick_csv
    lines = build_bom(model.flatten(), engine.catalog)
    out = _out(proj, model.variant)
    write_parts_csv(lines, out / "parts.csv")
    write_bricklink_xml(lines, out / "bricklink_wanted.xml")
    write_pick_a_brick_csv(lines, out / "pick_a_brick.csv")
    print(f"parts list: {sum(l.qty for l in lines)} pieces in {len(lines)} lines "
          f"-> {out / 'parts.csv'}")


def _new(slug: str, name: str | None) -> int:
    dst = paths.MODELS_DIR / slug
    if dst.exists():
        print(f"{dst} already exists")
        return 1
    dst.mkdir(parents=True)
    for f in (paths.TEMPLATES_DIR / "model").iterdir():
        text = f.read_text().replace("{{slug}}", slug).replace("{{name}}", name or slug)
        (dst / f.name).write_text(text)
    print(f"created {dst}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="brickkit")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch", help="download part libraries")
    p = sub.add_parser("new", help="scaffold a new model")
    p.add_argument("slug")
    p.add_argument("--name")
    for c in ("build", "verify", "bom", "all"):
        p = sub.add_parser(c)
        p.add_argument("slug")
        p.add_argument("--variant")
    p = sub.add_parser("render", help="render stills with Blender")
    p.add_argument("slug")
    p.add_argument("--views", default="three_quarter,front,side,top")
    p.add_argument("--size", type=int, default=900)
    p.add_argument("--samples", type=int, default=64)
    p.add_argument("--pose", type=float)
    p.add_argument("--lights", action="store_true")
    p.add_argument("--out", default="renders")
    p.add_argument("--variant")
    p = sub.add_parser("inspect", help="show a part's size and connection points")
    p.add_argument("parts", nargs="+")
    p = sub.add_parser("find", help="search real LEGO parts by name, optionally in a colour")
    p.add_argument("text")
    p.add_argument("--color")
    p.add_argument("--limit", type=int, default=40)
    args = ap.parse_args(argv)

    if args.cmd == "fetch":
        from .fetch import fetch
        fetch()
        return 0
    if args.cmd == "new":
        return _new(args.slug, args.name)

    from .engine import Engine
    engine = Engine()
    if args.cmd == "inspect":
        import numpy as np
        for part in args.parts:
            part = engine.catalog.canonical(part)
            lo, hi = engine.geom.mesh(part).bbox
            print(f"{part}: {engine.lib.description(part)}")
            print(f"  bbox x[{lo[0]:.0f},{hi[0]:.0f}] y[{lo[1]:.0f},{hi[1]:.0f}] z[{lo[2]:.0f},{hi[2]:.0f}]")
            for c in engine.shadow.connectors(part):
                o = np.round(c.origin, 1).tolist()
                a = np.round(c.axis, 2).tolist()
                shape = " ".join(f"{s}{r:g}x{ln:g}" for s, r, ln in c.secs) or f"r{c.radius:g}"
                print(f"  {c.kind} {c.gender} {shape:18s} at {o} axis {a}"
                      f"{' centred' if c.center else ''}{' group=' + c.group if c.group else ''}")
        return 0
    if args.cmd == "find":
        for sets, part, name, has_ld in engine.catalog.search(args.text, args.color, args.limit):
            print(f"{sets:5d}  {part:12s} {'ldraw' if has_ld else '     '}  {name}")
        return 0
    proj, model = _build(engine, args.slug, getattr(args, "variant", None))
    if args.cmd == "render":
        from .render.scene import render_model
        files = render_model(engine, model, _out(proj, model.variant) / args.out,
                             views=args.views.split(","),
                             size=args.size, samples=args.samples, pose_t=args.pose,
                             lights_on=args.lights)
        for f in files:
            print(f"rendered {f}")
        return 0
    code = 0
    if args.cmd in ("verify", "all"):
        code = _verify(engine, proj, model)
    if args.cmd in ("bom", "all"):
        _bom(engine, proj, model)
    if args.cmd == "all" and not args.variant:
        for name in proj.variants():
            print(f"--- variant {name}")
            vmodel = proj.build(engine.catalog, name)
            code = max(code, _verify(engine, proj, vmodel, ["real_elements", "technique"]))
            _bom(engine, proj, vmodel)
    return code
