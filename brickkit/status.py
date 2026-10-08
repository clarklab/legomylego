"""Where each model is on its way from a pasted picture to the site (docs/new-model.md).

    brickkit status [SLUG ...] [--all] [--check]

One row per model: who has claimed it (brickkit claim), a column per stage, the workshop its
video is set in (so the next one can differ), and the next thing to do. It only
looks at files (so it is instant): what is saved in reference/, NOTES.md, the checks' report,
the parts lists, the booklet, the videos, the site's pages. "stale" means design.py has
changed since. `--check` also builds each Quick Bricks model and audits its video plan."""
from __future__ import annotations

import csv
import json
import tomllib
from pathlib import Path

from . import paths

COLUMNS = ["model", "claim", "pieces", "source", "notes", "checks", "parts", "booklet", "preview",
           "video", "site", "scene", "next"]


def _fresh(path: Path, than: Path) -> str:
    if not path.exists():
        return "-"
    return "stale" if than.exists() and path.stat().st_mtime < than.stat().st_mtime - 1 else "yes"


def model_status(slug: str, models_dir: Path | None = None, site_dir: Path | None = None) -> dict:
    """One model's row: {model, pieces, source, notes, checks, parts, booklet, preview, video,
    site, next, quick (it has a [quick] block or the Quick Bricks tag), scene}."""
    d = (models_dir or paths.MODELS_DIR) / slug
    site = site_dir or (paths.ROOT / "site")
    out = d / "out"
    design = d / "design.py"
    from . import claims
    row = {c: "-" for c in COLUMNS}
    row["model"] = slug
    row["claim"] = claims.label(claims.read(slug, models_dir))
    try:
        cfg = tomllib.loads((d / "model.toml").read_text())
    except (OSError, tomllib.TOMLDecodeError):
        row["next"] = "model.toml is missing or broken"
        return row
    tagged = cfg.get("model", {}).get("collection") == "quick_bricks"
    q = cfg.get("quick", {})
    row["quick"] = tagged or "quick" in cfg
    row["scene"] = q.get("set") or "/".join(str(q[k]) for k in ("surface", "room", "light") if k in q) or "-"
    ref = [f for f in (d / "reference").glob("*") if not f.name.startswith(".")] if (d / "reference").is_dir() else []
    row["source"] = f"{len(ref)} files" if ref else "-"
    notes = d / "NOTES.md"
    if notes.exists():
        row["notes"] = "draft" if "TODO" in notes.read_text() else "yes"
    parts_csv = out / "parts.csv"
    if parts_csv.exists():
        with parts_csv.open() as fh:
            rows = list(csv.reader(fh))[1:]
        row["pieces"] = str(sum(int(r[0]) for r in rows if r and r[0].isdigit()))
    report = out / "report.json"
    if report.exists():
        rep = json.loads(report.read_text())
        bad = [c["name"] for c in rep.get("checks", []) if c.get("status") == "fail"]
        row["checks"] = "stale" if _fresh(report, design) == "stale" else ("FAIL " + ",".join(bad) if bad else "pass")
    lists = [out / "pick_a_brick.csv", out / "bricklink_wanted.xml"]
    if all(f.exists() for f in lists):
        row["parts"] = "stale" if any(_fresh(f, design) == "stale" for f in lists) else "yes"
    row["booklet"] = _fresh(out / "booklet.pdf", design)
    row["preview"] = _fresh(out / "quick_preview.mp4", design)
    video = out / paths.video_name(slug, 1080, 1920)
    row["video"] = _fresh(video, design)
    page = site / "quick" / slug / "index.html"
    copy = site / "quick" / video.name
    if not tagged:
        row["site"] = "off"
    elif not page.exists():
        row["site"] = "tagged"
    elif video.exists() and (not copy.exists() or copy.stat().st_size != video.stat().st_size):
        row["site"] = "old video"
    else:
        row["site"] = "yes"
    steps = [("notes", "-", "write NOTES.md: the source, the parts, the steps (docs/new-model.md)"),
             ("notes", "draft", "finish NOTES.md (it still has TODOs)"),
             ("checks", "-", f"write design.py, then: brickkit all {slug}"),
             ("checks", "stale", f"brickkit all {slug}"),
             ("parts", "-", f"brickkit all {slug}"), ("parts", "stale", f"brickkit all {slug}"),
             ("booklet", "-", f"brickkit booklet {slug}"), ("booklet", "stale", f"brickkit booklet {slug}"),
             ("video", "-", f"brickkit quick {slug} --preview, look at it, then: brickkit quick {slug}"),
             ("video", "stale", f"brickkit quick {slug}"),
             ("site", "off", "when the owner says so: tag it quick_bricks, tools/quick_site.py"),
             ("site", "tagged", "tools/quick_site.py, tools/site_assets.py"),
             ("site", "old video", "tools/quick_site.py, tools/site_assets.py")]
    row["next"] = "done"
    if row["source"] == "-" and row["notes"] == "draft":     # (taken in, nothing saved yet)
        row["next"] = "save what was pasted in reference/"
    elif row["checks"].startswith("FAIL"):
        row["next"] = f"fix the failing checks: brickkit verify {slug}"
    else:
        for col, state, todo in steps:
            if row[col] == state:
                row["next"] = todo
                break
    return row


def audit(engine, slug: str) -> str:
    """Build the model and check its Quick Bricks plan (video/quick.clashes)."""
    from .project import Project
    from .video import quick as Q
    proj = Project(slug, paths.MODELS_DIR)
    model = proj.build(engine.catalog)
    pl = Q.plan(engine, model, Q.quick_config(proj.config, slug=slug), log=lambda m: None)
    n = len(Q.clashes(engine, model.flatten(), pl)) + len(pl["notes"])
    return "clean" if n == 0 else f"{n} problems"


def status(slugs=(), every: bool = False, check: bool = False, models_dir: Path | None = None,
           site_dir: Path | None = None) -> list[dict]:
    base = models_dir or paths.MODELS_DIR
    names = list(slugs) or sorted(p.parent.name for p in base.glob("*/model.toml")
                                  if not p.parent.name.startswith("_"))
    rows = [model_status(s, base, site_dir) for s in names]
    if not slugs and not every:
        rows = [r for r in rows if r.get("quick")]       # the little ones
    if check:
        from .engine import Engine
        engine = Engine()
        for r in rows:
            if r.get("quick") and r["checks"] == "pass":
                r["build"] = audit(engine, r["model"])
    return rows


def table(rows: list[dict]) -> str:
    cols = COLUMNS[:-1] + (["build"] if any("build" in r for r in rows) else []) + ["next"]
    cells = [[str(r.get(c, "-")) for c in cols] for r in rows]
    width = [max(len(c), *(len(row[k]) for row in cells)) if cells else len(c) for k, c in enumerate(cols)]
    line = lambda row: "  ".join(v.ljust(w) for v, w in zip(row, width)).rstrip()   # noqa: E731
    return "\n".join([line(cols), line(["-" * w for w in width])] + [line(row) for row in cells])
