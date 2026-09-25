"""brickkit command line: fetch | new | build | verify | bom | all"""
from __future__ import annotations

import argparse

from . import paths


def _build(engine, slug):
    from .io.mpd import write_mpd
    from .project import Project
    proj = Project(slug, paths.MODELS_DIR)
    model = proj.build(engine.catalog)
    placed = model.flatten()
    out = write_mpd(model, proj.out / f"{slug}.mpd")
    print(f"{model.name}: {len(placed)} parts, {len(model.instruction_order())} steps -> {out}")
    return proj, model


def _verify(engine, proj, model) -> int:
    from .checks import run_checks
    from .checks.report import write_report
    results = run_checks(engine.context(model, proj.checks_config))
    data = write_report(results, proj.out, model.name)
    for r in results:
        print(f"[{r.status.upper()}] {r.name}: {r.summary}")
        for item in r.items[:5]:
            print(f"        {item}")
    print(f"overall: {data['status'].upper()} -> {proj.out / 'report.html'}")
    return 1 if data["status"] == "fail" else 0


def _bom(engine, proj, model) -> None:
    from .bom.bom import build_bom, write_bricklink_xml, write_parts_csv, write_pick_a_brick_csv
    lines = build_bom(model.flatten(), engine.catalog)
    write_parts_csv(lines, proj.out / "parts.csv")
    write_bricklink_xml(lines, proj.out / "bricklink_wanted.xml")
    write_pick_a_brick_csv(lines, proj.out / "pick_a_brick.csv")
    print(f"parts list: {sum(l.qty for l in lines)} pieces in {len(lines)} lines "
          f"-> {proj.out / 'parts.csv'}")


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
        sub.add_parser(c).add_argument("slug")
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
    if args.cmd == "find":
        for sets, part, name, has_ld in engine.catalog.search(args.text, args.color, args.limit):
            print(f"{sets:5d}  {part:12s} {'ldraw' if has_ld else '     '}  {name}")
        return 0
    proj, model = _build(engine, args.slug)
    code = 0
    if args.cmd in ("verify", "all"):
        code = _verify(engine, proj, model)
    if args.cmd in ("bom", "all"):
        _bom(engine, proj, model)
    return code
