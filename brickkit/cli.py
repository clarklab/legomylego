"""brickkit command line: fetch | new | build | verify | bom | all"""
from __future__ import annotations

import argparse
from pathlib import Path

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
    out = write_mpd(model, _out(proj, variant) / f"{slug}.mpd", engine.lib)
    figs = len([p for p in placed if p.buy is not None and p.buy_lead and p.buy.kind == "torso"])
    print(f"{model.name}: {len(placed)} parts, {len(model.instruction_order())} steps"
          + (f", {figs} minifigure(s)" if figs else "") + f" -> {out}")
    for fig in model.minifigs:
        for c in fig.stand_ins:
            print(f"  {fig.title}: no LDraw model of {c.kind} {c.rb_part} ({c.name[:60]}); "
                  "drawn plain in its colours")
    for part in sorted({p.part for p in placed if engine.catalog.is_approximate(p.part)}):
        print(f"  {part[:-4]} ({engine.catalog.part_name(part)[:60]}): a real LEGO part LDraw "
              "has no model of, drawn with brickkit's approximate 3D model")
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
    from .bom.bom import (build_bom, build_hardware, write_bricklink_xml, write_hardware_csv,
                          write_parts_csv, write_pick_a_brick_csv)
    placed = model.flatten()
    lines = build_bom(placed, engine.catalog, model.extras)
    hardware = build_hardware(placed, engine.catalog, model.hardware_items)
    out = _out(proj, model.variant)
    write_parts_csv(lines, out / "parts.csv")
    if hardware:
        write_hardware_csv(hardware, out / "hardware.csv")
    else:
        (out / "hardware.csv").unlink(missing_ok=True)
    missing = write_bricklink_xml(lines, out / "bricklink_wanted.xml")
    for l in missing:
        print(f"  not in bricklink_wanted.xml (no BrickLink number known): {l.qty} x "
              f"{l.rb_part} {l.color.name} {l.name[:70]}")
    write_pick_a_brick_csv(lines, out / "pick_a_brick.csv")
    import json
    from .bom.live_price import live_prices
    from .bom.price import estimate, hardware_summary, summary, write_estimate_md
    live = None
    try:
        live = live_prices(lines)
    except Exception as e:                        # no network, refused keys: say so, go on
        print(f"live prices unavailable ({e}); using price bands")
    day = live["day"] if live else None
    priced = estimate(lines, engine.catalog, live)
    from .bom.bom import minifig_count
    n_figs = minifig_count(model)
    low, high = write_estimate_md(model.name, priced, out / "price_estimate.md", day, hardware,
                                  minifigs=n_figs)
    s = summary(priced, day)
    if n_figs:
        s["minifigs"] = n_figs
    if hardware:
        s["hardware"] = hardware_summary(hardware)
    (out / "price.json").write_text(json.dumps(s, indent=1))
    print(f"parts list: {sum(l.qty for l in lines)} pieces in {len(lines)} lines"
          + (f" ({n_figs} minifigure(s))" if n_figs else "") + " "
          f"-> {out / 'parts.csv'}; price ${low:,.0f}-${high:,.0f}"
          f"{f' (BrickLink, {day})' if day else ' (rough estimate)'}")
    if hardware:
        h = s["hardware"]
        print(f"hardware (not LEGO): {h['items']} item(s) in {h['lines']} line(s) -> "
              f"{out / 'hardware.csv'}; about ${h['low']:,.0f}-${h['high']:,.0f}")


def _who(name: str | None) -> str | None:
    import os
    return name or os.environ.get("BRICKKIT_AGENT")


def _claim(args) -> int:
    from . import claims
    who = _who(args.who)
    if not who:
        print("say who you are: --as NAME (or set BRICKKIT_AGENT)")
        return 2
    try:
        if args.cmd == "release":
            done = claims.release(args.slug, who, args.force)
            print(f"{args.slug}: released" if done else f"{args.slug}: was not claimed")
            return 0
        c = claims.claim(args.slug, who, args.stage, args.note, args.take)
        print(f"{args.slug}: claimed by {c['who']}" + (f" (stage {c['stage']})" if c.get("stage") else ""))
        return 0
    except claims.Claimed as e:
        held = e.args[0]
        print(f"{args.slug}: claimed by {claims.label(held)}"
              + (f" - {held['note']}" if held.get("note") else "")
              + (": stale, take it with --take" if held.get("stale") and args.cmd == "claim" else ""))
        return 1
    except FileNotFoundError as e:
        print(e)
        return 1


def _new(slug: str, name: str | None, quick: bool = False, who: str | None = None) -> int:
    """Scaffold models/SLUG: model.toml and design.py; `quick` (a Quick Bricks model, see
    docs/new-model.md): also NOTES.md to fill in and reference/ for what was pasted. `who`:
    claim it as well (making the folder is what decides between two who start at once)."""
    dst = paths.MODELS_DIR / slug
    try:
        dst.mkdir(parents=True)
    except FileExistsError:
        print(f"{dst} already exists")
        return 1
    if who:
        from . import claims
        claims.claim(slug, who, "1", "taking it in")
    for f in (paths.TEMPLATES_DIR / ("quick" if quick else "model")).iterdir():
        text = f.read_text().replace("{{slug}}", slug).replace("{{name}}", name or slug)
        (dst / f.name).write_text(text)
    if quick:
        (dst / "reference").mkdir()
    print(f"created {dst}" + (": save the source in reference/, then fill in NOTES.md "
                              "(docs/new-model.md)" if quick else ""))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="brickkit")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch", help="download part libraries")
    p = sub.add_parser("new", help="scaffold a new model")
    p.add_argument("slug")
    p.add_argument("--name")
    p.add_argument("--quick", action="store_true",
                   help="a Quick Bricks model: also NOTES.md and reference/ (docs/new-model.md)")
    p.add_argument("--as", dest="who", help="claim it too, under this name (or BRICKKIT_AGENT)")
    p = sub.add_parser("import", help="a new model from a Studio .io or an LDraw .ldr / .mpd "
                                      "file: its exact parts and positions as a design.py")
    p.add_argument("slug")
    p.add_argument("file")
    p.add_argument("--name")
    p.add_argument("--sub", help="just this sub-model of the file")
    p.add_argument("--as", dest="who", help="claim it too, under this name (or BRICKKIT_AGENT)")
    p = sub.add_parser("ways", help="how each piece can go on (the video's planner): the way it "
                                    "comes from, as an insert= hint; what had no clear way")
    p.add_argument("slug")
    p.add_argument("--all", action="store_true", help="every piece, not just the unusual ones")
    p = sub.add_parser("claim", help="claim a model before working on it (models/SLUG/CLAIM)")
    p.add_argument("slug")
    p.add_argument("--as", dest="who", help="who you are (or set BRICKKIT_AGENT)")
    p.add_argument("--stage", default="", help='what you will do, e.g. "2-3" (docs/new-model.md)')
    p.add_argument("--note", default="")
    p.add_argument("--take", action="store_true", help="take over a stale claim")
    p = sub.add_parser("release", help="give a claimed model back")
    p.add_argument("slug")
    p.add_argument("--as", dest="who")
    p.add_argument("--force", action="store_true", help="release someone else's claim")
    p = sub.add_parser("status", help="where each model is: source, notes, checks, parts lists, "
                                      "booklet, video, site - and what to do next")
    p.add_argument("slugs", nargs="*", help="(default: the Quick Bricks models)")
    p.add_argument("--all", action="store_true", help="every model")
    p.add_argument("--check", action="store_true",
                   help="also build each Quick Bricks model and audit its video plan")
    for c in ("build", "verify", "bom", "all"):
        p = sub.add_parser(c)
        p.add_argument("slug")
        p.add_argument("--variant")
    p = sub.add_parser("render", help="render stills with Blender")
    p.add_argument("slug")
    p.add_argument("--views", default="three_quarter,front,side,top",
                   help="comma list: front, three_quarter, three_quarter_right, side, back, top, low, "
                        "or close:TAG for a close-up of the parts under a tag (a minifigure)")
    p.add_argument("--size", type=int, default=900)
    p.add_argument("--samples", type=int, default=64)
    p.add_argument("--pose", type=float)
    p.add_argument("--lights", action="store_true")
    p.add_argument("--out", default="renders")
    p.add_argument("--variant")
    p = sub.add_parser("turntable", help="photoreal orbit loop (MP4) with the mechanism "
                                          "and lights going, for the site's no-WebGL view")
    p.add_argument("slug")
    p.add_argument("--variant")
    p.add_argument("--seconds", type=float, default=12.0)
    p.add_argument("--fps", type=int, default=24)
    p.add_argument("--size", type=int, default=720)
    p.add_argument("--samples", type=int, default=48)
    p.add_argument("--preview", action="store_true")
    p = sub.add_parser("quick", help="Quick Bricks: a short vertical build video for TikTok and "
                                      "Instagram (out/SLUG-1080x1920.mp4)")
    p.add_argument("slug")
    p.add_argument("--preview", action="store_true", help="540x960, 15 fps, low samples")
    p.add_argument("--set", help="a preset workshop or random (else [quick] set)")
    p.add_argument("--surface", help="the surface layer (blue_mat, green_mat, kraft, oak, baseplate, lego_yellow, lego_blue, lego_green, lego_red)")
    p.add_argument("--room", help="the room layer (workbench, studio, window, night, bookshelf)")
    p.add_argument("--light", help="the light layer (morning, day, evening)")
    p.add_argument("--seed", type=int, help="for --set random")
    p.add_argument("--seconds", type=float, help="the loop's length (else [quick] seconds)")
    p.add_argument("--stills", help="comma list of frames: render just those, no video")
    p.add_argument("--force", action="store_true", help="render every frame again")
    p.add_argument("--remix", action="store_true",
                   help="no rendering: the frames there are, with the sound mixed again")
    p.add_argument("--cover", action="store_true",
                   help="no rendering: just the cover picture, picked again from the frames "
                        "there are ([quick] cover)")
    p.add_argument("--layout", action=argparse.BooleanOptionalAction, default=None,
                   help="start with the parts laid out in a grid (else [quick] layout: under "
                        "25 pieces)")
    p.add_argument("--no-audio", action="store_true")
    p.add_argument("--device", choices=("gpu", "cpu"), default="gpu")
    p = sub.add_parser("booklet", help="instruction booklet PDF")
    p.add_argument("slug")
    p.add_argument("--variant")
    p.add_argument("--no-render", action="store_true", help="reuse existing pictures")
    p = sub.add_parser("worksheet", help="a class's sorting sheet (out/worksheet.pdf): every piece "
                                         "as an outline at its real size, and a word about the model")
    p.add_argument("slug")
    p = sub.add_parser("video", help="build video (out/SLUG-1080x1080.mp4) rendered with Blender")
    p.add_argument("slug")
    p.add_argument("--variant")
    p.add_argument("--preview", action="store_true", help="540x540, low samples, every 2nd frame")
    p.add_argument("--segments", help="comma list, e.g. build,mechanism (default: all)")
    p.add_argument("--force", action="store_true", help="re-render cached frames")
    p.add_argument("--engine", choices=("eevee", "cycles"), default="eevee")
    p.add_argument("--device", choices=("gpu", "cpu"), default="gpu", help="Cycles only")
    p.add_argument("--no-audio", action="store_true", help="no music or sound effects")
    p.add_argument("--no-render", action="store_true",
                   help="compose from the plates already rendered (grey where missing)")
    p.add_argument("--stills", help="comma list of frames: write composed PNGs, no video")
    p.add_argument("--theme", help="try another theme for this run (brand, scan, tape, playful, "
                                   "grindhouse, abyss): out/video_THEME*.mp4, the model's own left "
                                   "alone")
    p.add_argument("--cold-open", metavar="SCENE", help="try a cold open (sunset_road, "
                   "night_desk, deep_sea) for this run: tagged outputs like --theme; --segments "
                   "cold_open for just it")
    p.add_argument("--scratch", metavar="DIR", help="write this run's work and outputs under DIR "
                   "(the model's out/ is only read)")
    p.add_argument("--workers", type=int, default=4, help="parallel compositor pages")
    p = sub.add_parser("sizzle", help="brand sizzle reel of several models, cut on the music's "
                                      "beats (showreel/sizzle.toml -> showreel/sizzle.mp4)")
    p.add_argument("slugs", nargs="*", help="models (default: the config's, in its order)")
    p.add_argument("--config", help="the reel's TOML (default showreel/sizzle.toml)")
    p.add_argument("--out", help="output folder (default: the config's folder)")
    p.add_argument("--stills", help="comma list of frames: write composed PNGs, no video")
    p.add_argument("--preview", action="store_true", help="540x540 at 15 fps")
    p.add_argument("--no-audio", action="store_true")
    p.add_argument("--workers", type=int, default=4, help="parallel compositor pages")
    p = sub.add_parser("viewer", help="export the model (and its colourways) to the viewer site")
    p.add_argument("slug")
    p.add_argument("--site", help="site directory (default: site/)")
    p = sub.add_parser("inspect", help="show a part's size and connection points")
    p.add_argument("parts", nargs="+")
    p = sub.add_parser("find", help="search real LEGO parts by name, optionally in a colour")
    p.add_argument("text")
    p.add_argument("--color")
    p.add_argument("--limit", type=int, default=40)
    p.add_argument("--minifig", choices=("head", "torso", "legs", "any"),
                   help="search minifigure components (assemblies as sold), one row per colour")
    p.add_argument("--ldraw", action="store_true", help="--minifig: only prints LDraw models")
    p = sub.add_parser("figs", help="search whole minifigures by name and list their parts")
    p.add_argument("text")
    p.add_argument("--limit", type=int, default=15)
    args = ap.parse_args(argv)

    if args.cmd == "fetch":
        from .fetch import fetch
        fetch()
        return 0
    if args.cmd == "new":
        return _new(args.slug, args.name, args.quick, _who(args.who))
    if args.cmd in ("claim", "release"):
        return _claim(args)
    if args.cmd == "status":
        from .status import status, table, waiting
        print(table(status(args.slugs, args.all, args.check)))
        todo = [] if args.slugs else waiting()
        if todo:
            print("\nWaiting in inbox/ (not taken in yet):")
            w = max(len(t["name"]) for t in todo)
            for t in todo:
                what = f"{t['files']} file{'s' if t['files'] != 1 else ''} ({', '.join(t['kinds']) or 'empty'})"
                print(f"  {t['name'].ljust(w)}  {what.ljust(24)}  {t['next']}")
        return 0
    if args.cmd == "sizzle":                  # no model to build: it uses their showreels' footage
        from .video.sizzle import CONFIG, make_sizzle
        stills = [int(x) for x in args.stills.split(",") if x.strip()] if args.stills else None
        out = make_sizzle(Path(args.config) if args.config else CONFIG, args.slugs or None,
                          Path(args.out) if args.out else None, stills=stills,
                          preview=args.preview, audio=not args.no_audio, workers=args.workers)
        print(f"sizzle -> {out}")
        return 0

    from .engine import Engine
    engine = Engine()
    if args.cmd == "import":
        from .io.ldraw_import import import_model
        r = import_model(engine, args.slug, Path(args.file), args.name, args.sub, _who(args.who))
        print(f"{args.slug}: {r['parts']} parts in {r['steps']} steps "
              f"({'the file\'s own' if r['own_steps'] else 'a build order worked out'}) -> {r['dir']}")
        for line in r["fixed"]:
            print(f"  Studio's part matched to LDraw's: {line}")
        for part in r["unknown"]:
            print(f"  LDraw has no file for {part}: swap it for the LDraw print or the plain part")
        return 0
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
    if args.cmd == "find" and args.minifig:
        figs = engine.catalog.figs
        kind = None if args.minifig == "any" else args.minifig
        for r in figs.search(args.text, kind, args.color, args.limit, ldraw_only=args.ldraw):
            print(f"{r['sets']:4d} {r['year'] or '':>4} {r['part']:20s} {r['colour'][:18]:18s} "
                  f"{(r['ldraw'] or '-')[:12]:12s} {(r['bricklink'] or '-')[:14]:14s} "
                  f"{'E' if r['element'] else ' '} {r['name'][:110]}")
        return 0
    if args.cmd == "find":
        for sets, part, name, has_ld in engine.catalog.search(args.text, args.color, args.limit):
            print(f"{sets:5d}  {part:12s} {'ldraw' if has_ld else '     '}  {name}")
        return 0
    if args.cmd == "figs":
        cat = engine.catalog
        for r in cat.figs.figures(args.text, args.limit):
            print(f"{r['fig']}  {r['name']}  ({r['sets']} set(s), {r['year'] or 'no set'})")
            for part, cid, qty in r["parts"]:
                ld = cat.figs._sources(part, cat.figs.kind(part)) if cat.figs.kind(part) else []
                has = (ld[0] if ld else "-") if cat.figs.kind(part) else (
                    "ldraw" if cat.ldraw.resolve(part) else "-")
                print(f"    {qty} x {part:20s} {cat.rb.colors[cid]['name'][:18]:18s} "
                      f"{has[:12]:12s} {cat.part_name(part)[:90]}")
        return 0
    proj, model = _build(engine, args.slug, getattr(args, "variant", None))
    if args.cmd == "turntable":
        from .render.turntable import make_turntable
        make_turntable(engine, model, _out(proj, model.variant), seconds=args.seconds,
                       fps=args.fps, size=args.size, samples=args.samples, preview=args.preview)
        return 0
    if args.cmd == "ways":
        import numpy as np

        from .video import assemble as A
        from .video import quick as Q
        placed = model.flatten()
        seq = Q.build_sequence(model, placed)
        sc = A.assemble(engine, model, placed, seq, log=lambda m: None)
        words = {(0, -1, 0): "above", (0, 1, 0): "below", (1, 0, 0): "+X", (-1, 0, 0): "-X",
                 (0, 0, 1): "the back", (0, 0, -1): "the front"}
        for k, it in enumerate(sc["items"]):
            p = placed[it.parts[0]]
            flags = [w for w, on in (("joined as a unit", it.kind == "join"), ("the build is lifted", bool(it.carry)),
                                     ("set down on it", it.mode == "under"), ("NO CLEAR WAY", it.forced)) if on]
            if not (args.all or flags or it.way not in ("stud", "table")):
                continue
            d = np.round(it.axis, 3) + 0.0
            print(f"#{k:<3} step {p.local_step + 1:<3} {p.part.removesuffix('.dat'):<12} {'/'.join(p.tags)[:18]:<18} "
                  f"{it.way:<6} from {words.get(tuple(int(round(v)) for v in d), 'an angle'):<10} "
                  f"insert=({', '.join(f'{v:g}' for v in d)})  {'; '.join(flags)}")
        print(f"{len(sc['items'])} pieces and joins; the steps' order {'kept' if sc['order'] == seq else 'CHANGED (a piece had to wait)'}; "
              f"{sum(it.forced for it in sc['items'])} with no clear way in")
        return 0
    if args.cmd == "quick":
        from .video.quick import make_quick
        stills = [int(x) for x in args.stills.split(",") if x.strip()] if args.stills else None
        out = make_quick(engine, proj, model, preview=args.preview, set_name=args.set,
                         seconds=args.seconds, audio=not args.no_audio, force=args.force,
                         stills=stills, device=args.device, remix=args.remix,
                         cover=args.cover,
                         layers={"surface": args.surface, "room": args.room, "light": args.light,
                                 "seed": args.seed, "layout": args.layout})
        print(f"quick -> {out}")
        return 0
    if args.cmd == "booklet":
        from .booklet.booklet import make_booklet
        pdf = make_booklet(engine, proj, model, rerender=not args.no_render,
                           out_dir=_out(proj, model.variant))
        print(f"booklet -> {pdf}")
        return 0
    if args.cmd == "worksheet":
        from .booklet.worksheet import make_worksheet
        print(f"worksheet -> {make_worksheet(engine, proj, model)}")
        return 0
    if args.cmd == "video":
        from .video import make_video
        segs = [s.strip() for s in args.segments.split(",") if s.strip()] if args.segments else None
        stills = [int(x) for x in args.stills.split(",") if x.strip()] if args.stills else None
        out = make_video(engine, proj, model, _out(proj, model.variant), preview=args.preview,
                         segments=segs, force=args.force, render_engine=args.engine,
                         device=args.device, audio=not args.no_audio,
                         render=not args.no_render, stills=stills, workers=args.workers,
                         theme_name=args.theme, cold_open=args.cold_open,
                         scratch=Path(args.scratch).resolve() if args.scratch else None)
        print(f"video -> {out}")
        return 0
    if args.cmd == "viewer":
        from .viewer_export import export_model
        dst = export_model(engine, proj, model, args.site)
        print(f"viewer bundle -> {dst}")
        return 0
    if args.cmd == "render":
        from .render.scene import render_model, trans_settings
        files = render_model(engine, model, _out(proj, model.variant) / args.out,
                             views=args.views.split(","),
                             size=args.size, samples=args.samples, pose_t=args.pose,
                             lights_on=args.lights, settings=trans_settings(proj.config))
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
