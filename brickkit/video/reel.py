"""Showreel edit plan (engine side; no Blender, no browser).

`plan_reel(...)` turns the model's own data into everything the graphics layer (web/reel.js)
and the sound (audio.py) need, so every number on screen comes from the model, its parts list
and its check report:

    model       name, slug, URL, pieces, steps, colours, part designs, sub-assemblies, size
    stats       the title's chips (size, steps, colours, sub-assemblies, plus [video] facts)
    palette     pieces per colour (the parts list; colours for the themes' brick wipes)
    checks      the eight checks from out/report.json, each with its headline number
    build       when each part lands (sorted), the height reached, sections, the final piece
    camera      the per-frame video camera, for 3D-tracked graphics (x-ray lines, callouts)
    scan        layout, silhouette box per frame, connection points (from the checks' matcher)
    mechanism   name, labels, pose parameter and angle per frame, tracked callouts
    lights      power-on frame and tracked lamp positions
    colourways  wipes and each colourway's swatches
    cold_open   (with one) its shots, the cut to black, the sun's place on screen per frame
    marks       beat-aligned key frames of every segment (the graphics and the music share them)
    transitions every cut and its wipe style

Callouts come from model.toml [video.callouts] (or meta["video"]["callouts"]):

    [[video.callouts]]
    label = "Dust door"      # text on screen
    tag = "flap"             # parts under a tag (glob: "fang_*" -> one anchor per fang)
    part = "3937"            # ...or of a part number, or `color = "Trans-Brown"`
    sub = "Swings 90°"       # optional second line (default: the angle a moving group turns)
    xray = true              # also draw the parts' outlines, for parts hidden inside

Without config, each moving group gets a callout.

Recorded sounds (optional) come from model.toml [video.audio] (see `audio_assets`): a chainsaw
pulled, idling and screaming in the cold open, horror stings on the title and the big cuts.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np

from . import timeline as T

URL = "bricks.superfun.games"
DISCLAIMER = "Unofficial fan model · computer-checked, not yet built with real bricks"
MOODS = {"cold_open": "cold", "open": "intro", "title": "rise", "build": "groove",
         "scan": "breakdown", "mechanism": "halftime", "lights": "feature", "lift": "feature",
         "colourways": "groove", "booklet": "groove_light", "outro": "end"}
CHECK_TITLES = {"real_elements": "Real parts", "connections": "Connections",
                "collisions": "Collisions", "buildability": "Buildable",
                "stability": "Stable", "mechanism": "Mechanism", "electrics": "Electrics",
                "technique": "Technique"}
MAX_PULSES = 28          # first parts of the build that get a landing ring
MAX_POINTS = 1400        # connection points drawn in the scan
# recorded sounds by role: peak level (dBFS, against the music bed at audio.MUSIC_REF)
SAMPLE_LEVEL = {"pull_start": -9.0, "idle": -17.5, "scream": -8.5, "burst": -11.0,
                "sting": -11.0, "hit": -11.5, "boom": -11.0, "band": -12.0,
                "click": -12.0, "snap_on": -11.0, "snap_off": -15.0, "room": -30.0,
                "ambience": -20.0, "ping": -15.0, "bubbles": -17.0, "groan": -13.0,
                "churn": -16.0}
# a cold-open set's own sounds (shared, in brickkit/data/audio/<set>/, made by
# tools/elevenlabs_sfx.py from the sfx.toml there): used for the roles a model's [video.audio]
# doesn't give
SCENE_SOUNDS = {"deep_sea": {"ambience": "ambience_2.mp3", "pings": ["ping_1.mp3", "ping_2.mp3"],
                             "bubbles": ["bubbles_2.mp3", "bubbles_3.mp3"],
                             "groan": "groan_1.mp3", "churn": "churn_2.mp3"}}
SCREAM_GAP = 1.4         # s: at least this between the cold open's screams


# ---------------------------------------------------------------------------- config
def configure(proj, model) -> dict:
    """Merge model.toml [video] into the model (under design.py's meta["video"])."""
    model.meta["_video_toml"] = dict(proj.config.get("video", {}) or {})
    return T.video_config(model)


def colourway_variants(engine, proj, model, log=print) -> dict:
    """Colourways that share the model's parts and positions (only their colours differ):
    {name: {"title", "model"}}. Others are skipped (a colour swap can't show them)."""
    if model.variant:
        return {}
    base = model.flatten()
    out = {}
    for name in proj.variants():
        vm = proj.build(engine.catalog, name)
        vp = vm.flatten()
        same = len(vp) == len(base) and all(
            a.part == b.part and np.allclose(a.M, b.M) for a, b in zip(base, vp))
        if same:
            out[name] = {"title": proj.variant_title(name), "model": vm}
        else:
            log(f"colourway {name}: different parts, left out of the colour swap")
    return out


# ---------------------------------------------------------------------------- model data
def _fmt_len(mm: float, unit: str) -> str:
    return f"{mm / (10 if unit == 'cm' else 1):.0f}"


def model_stats(engine, proj, model, placed, tl, out_dir: Path, booklet_steps: int | None,
                cfg: dict) -> dict:
    from ..bom.bom import build_bom
    lines = build_bom(placed, engine.catalog, getattr(model, "extras", ()))
    C = T.corners(engine, placed).reshape(-1, 3)
    ext = (C.max(0) - C.min(0)) * 0.4                      # LDU -> mm
    w, h, d = float(ext[0]), float(ext[1]), float(ext[2])
    unit = "mm" if max(w, h, d) < 250 else "cm"
    dims = f"{_fmt_len(w, unit)} × {_fmt_len(d, unit)} × {_fmt_len(h, unit)} {unit}"
    shape = tl["model"]["shape"]
    if shape["long"] > 1.8 or shape["long"] < 1 / 1.8:
        big = max(w, d)
        headline = (f"{big / 10:.0f}" if big >= 250 else f"{big:.0f}", "cm long" if big >= 250
                    else "mm long")
    elif h >= max(w, d):
        headline = (f"{h / 10:.0f}" if h >= 250 else f"{h:.0f}",
                    "cm tall" if h >= 250 else "mm tall")
    else:
        headline = (dims.rsplit(" ", 1)[0], unit)
    if unit == "mm" and (shape["long"] > 1.8 or shape["long"] < 1 / 1.8):
        headline = (dims.rsplit(" ", 1)[0], unit)        # a cassette: all three matter
    report = _report(out_dir)
    mass = None
    for c in report.get("checks", []):
        if c.get("name") == "stability":
            mass = c.get("stats", {}).get("mass_g")
    steps = booklet_steps or len(model.instruction_order())
    return {
        "name": model.name, "slug": model.slug, "url": URL,   # the outro links to the site
        "pieces": int(sum(line.qty for line in lines)), "parts": len(placed),
        "steps": int(steps), "colours": len({line.color.name for line in lines}),
        "designs": len({line.ldraw_part for line in lines}), "lines": len(lines),
        "subassemblies": max(0, sum(1 for s in model.submodels.values()
                                    if getattr(s, "kit", None) is None) - 1),
        "dims_mm": [round(w, 1), round(d, 1), round(h, 1)], "dims": dims,
        "headline": list(headline), "mass_g": mass,
        "notice": proj.config.get("model", {}).get("notice", ""),
        "disclaimer": DISCLAIMER,
        "mechanism_name": model.meta.get("mechanism_name", ""),
        "facts": [str(x) for x in cfg.get("facts", [])],
    }


def title_chips(stats: dict) -> list[dict]:
    """One compact row beside the piece counter: size, steps, colours, then any [video] facts
    (the title keeps what fits in the row)."""
    chips = [{"value": stats["headline"][0], "label": stats["headline"][1]},
             {"value": f"{stats['steps']:,}", "label": "steps"},
             {"value": f"{stats['colours']}", "label": "colours"}]
    for f in stats["facts"]:
        chips.append({"value": "", "label": f})
    return chips


def palette(engine, model, placed) -> list[dict]:
    """Pieces per colour on the parts list, most first."""
    from ..bom.bom import build_bom
    lines = build_bom(placed, engine.catalog, getattr(model, "extras", ()))
    qty: Counter = Counter()
    info = {}
    for line in lines:
        qty[line.color.name] += line.qty
        info[line.color.name] = line.color
    out = []
    for name, n in qty.most_common():
        c = info[name]
        out.append({"name": name, "rgb": c.rgb if c.rgb.startswith("#") else "#" + c.rgb,
                    "qty": int(n), "trans": bool(c.alpha < 255)})
    return out


def _report(out_dir: Path) -> dict:
    f = out_dir / "report.json"
    try:
        return json.loads(f.read_text())
    except (OSError, ValueError):
        return {}


def checks(out_dir: Path) -> dict:
    """The check report as panel rows: title, status, a headline number and a short line."""
    rep = _report(out_dir)
    rows = []
    for c in rep.get("checks", []):
        name, st, s = c.get("name", ""), c.get("status", "pass"), c.get("stats", {}) or {}
        title = CHECK_TITLES.get(name, name.replace("_", " ").capitalize())
        big, small = "", c.get("summary", "")
        if name == "real_elements":
            big = f"{s.get('combinations', 0):,}"
            rare, bad = s.get("rare", 0), s.get("not_real", 0)
            small = "part/colour pairs, all real" if not bad else f"{bad} not real"
            if rare:
                small = f"part/colour pairs · {rare} rare"
        elif name == "connections":
            big = f"{s.get('connections', 0):,}"
            kinds = sorted((s.get("by_kind") or {}).items(), key=lambda kv: -kv[1])
            small = " · ".join(f"{v:,} {k}" for k, v in kinds[:3]) or "connections"
        elif name == "collisions":
            big = f"{s.get('pairs', 0):,}"
            small = "overlapping parts"
        elif name == "buildability":
            big = f"{s.get('insertions', 0):,}"
            small = "insertions tried, all clear" if st == "pass" else "insertions tried"
        elif name == "stability":
            ang = s.get("tip_angle_deg")
            big = f"{ang:.0f}°" if ang is not None else "✓"
            m = s.get("mass_g")
            small = "before it tips" + (f" · {m:,.0f} g" if m else "")
        elif name == "mechanism":
            p = s.get("poses")
            big = f"{p}" if p else "—"
            small = "poses swept, no clashes" if p else "no moving parts"
        elif name == "electrics":
            runs = s.get("runs") or []
            big = f"{len(runs)}" if runs else "—"
            small = ("cable runs, all long enough" if runs else "no electrics")
        elif name == "technique":
            n = len(c.get("items", []))
            big = f"{n}"
            small = "notes" if n != 1 else "note"
        rows.append({"name": name, "title": title, "status": st, "big": big, "small": small,
                     "na": big == "—"})
    n_pass = sum(r["status"] == "pass" for r in rows)
    n_warn = sum(r["status"] == "warn" for r in rows)
    n_fail = sum(r["status"] == "fail" for r in rows)
    if not rows:
        summary = "no report"
    elif n_fail:
        summary = f"{n_fail} failed"
    elif n_warn:
        summary = f"{n_pass} passed · {n_warn} warning" + ("s" if n_warn > 1 else "")
    else:
        summary = f"{n_pass} / {len(rows)} passed"
    return {"status": rep.get("status", "pass"), "rows": rows, "summary": summary}


def hero(out_dir: Path, cut: Path | None = None) -> dict | None:
    """The title's still: the transparent cutout (and its model's box inside it, 0..1), or
    else the site hero as a framed card."""
    from PIL import Image
    if cut is not None and cut.exists():
        with Image.open(cut) as im:
            a = np.asarray(im.convert("RGBA"))[:, :, 3]
        ys, xs = np.nonzero(a > 40)          # the model, not its faint shadow
        if len(xs):
            h, w = a.shape
            return {"url": f"cut/{cut.name}", "cutout": True,
                    "box": [xs.min() / w, ys.min() / h, (xs.max() + 1) / w, (ys.max() + 1) / h]}
    f = out_dir / "hero" / "hero.png"
    if not f.exists():
        return None
    return {"url": "out/hero/hero.png", "cutout": False, "box": [0.0, 0.0, 1.0, 1.0]}


def write_wire(engine, placed, path: Path) -> dict:
    """Every part's LDraw edge lines in world coordinates (float32 x1 y1 z1 x2 y2 z2) and the
    part each belongs to (uint16), for the x-ray and tracked outlines."""
    xyz, part = [], []
    for i, p in enumerate(placed):
        E = np.asarray(engine.geom.mesh(p.part).edges, float).reshape(-1, 3)
        if not len(E):
            continue
        W = (p.M[:3, :3] @ E.T).T + p.M[:3, 3]
        xyz.append(W.reshape(-1, 6).astype(np.float32))
        part.append(np.full(len(W) // 2, i, np.uint16))
    xyz = np.concatenate(xyz) if xyz else np.zeros((0, 6), np.float32)
    part = np.concatenate(part) if part else np.zeros(0, np.uint16)
    path.write_bytes(xyz.astype("<f4").tobytes() + part.astype("<u2").tobytes())
    return {"url": f"frames/{path.name}", "count": int(len(part))}


def connection_points(engine, model, limit: int = MAX_POINTS) -> list:
    """Where the parts connect (midpoints of matched connectors), sampled evenly."""
    try:
        conns = engine.context(model).connections
    except Exception:          # noqa: BLE001 - graphics only: no dots rather than no video
        return []
    pts = [((np.asarray(c.ca.origin) + np.asarray(c.cb.origin)) / 2, c.kind) for c in conns
           if c.ca is not None and c.cb is not None]      # press fits have no connector points
    if len(pts) > limit:
        rng = np.random.default_rng(7)
        pts = [pts[i] for i in sorted(rng.choice(len(pts), limit, replace=False))]
    return [[round(float(p[0]), 1), round(float(p[1]), 1), round(float(p[2]), 1), k]
            for p, k in pts]


# ---------------------------------------------------------------------------- projection
def _cam(tl, f):
    cam = tl["camera"]
    k = int(np.clip(f - cam["start"], 0, len(cam["pos"]) - 1))
    return cam["pos"][k], cam["target"][k], cam["lens"][k]


def screen(tl, f, pts) -> np.ndarray:
    pos, tgt, lens = _cam(tl, f)
    return T.project(np.asarray(pts, float).reshape(-1, 3), pos, tgt, lens, 1080.0)


def _group_matrix(tl, f, g):
    grp = tl["groups"]
    k = f - grp["start"]
    if g < 0 or not grp["frames"] or k < 0 or k >= len(grp["frames"]):
        return np.eye(4)
    return np.array(grp["frames"][k][g]).reshape(4, 4)


# ---------------------------------------------------------------------------- callouts
_matches = T.part_matches
_instances = T.part_instances
default_callouts = T.default_callouts


def part_label(name: str) -> str:
    """A catalogue name for the screen: 'Dish 2 x 2 Inverted [Radar]' -> 'Dish 2×2 inverted'."""
    import re
    name = re.sub(r"\s*[\[(].*?[\])]", "", name).strip()
    name = re.sub(r"(\d)\s*x\s*(\d)", "\\1\u00d7\\2", name)
    words = name.split(" ")
    return " ".join(words[:1] + [w if any(c.isdigit() for c in w) else w.lower() for w in words[1:]])


def callouts(engine, model, placed, C, tl, cfg, log=print) -> list[dict]:
    """Callouts for the mechanism shot, each anchor tracked through the shot's camera and
    the moving groups' poses: [{label, sub, n, xray, parts, side, y, track: [[x, y], ...]}]."""
    seg = next((s for s in tl["segments"] if s["name"] == "mechanism"), None)
    if seg is None:
        return []
    conf = cfg.get("callouts") or default_callouts(model)
    gi = tl["groups"]["instance"]
    names = tl["groups"]["names"]
    angles = tl["mechanism"]["angles"]
    frames = list(range(seg["start"], seg["end"]))
    out = []
    told = set()                              # groups whose turn a callout already gives
    for sel in conf:
        inst = _instances(placed, sel)
        if not inst:
            log(f"callout {sel.get('label')!r}: no parts match {sel}; left out")
            continue
        anchors = []
        for idx in inst:
            c = C[idx].reshape(-1, 3)
            centre = (c.min(0) + c.max(0)) / 2
            g = gi[idx[0]]
            track = []
            for f in frames:
                M = _group_matrix(tl, f, g)
                w = M[:3, :3] @ centre + M[:3, 3]
                x, y, _ = screen(tl, f, w)[0]
                track.append([round(float(x), 1), round(float(y), 1)])
            anchors.append({"track": track, "group": int(g)})
        sub = sel.get("sub")
        if sub is None:
            # how far its group turns (once per group), else what the part is
            g = gi[inst[0][0]]
            kinds = {placed[i].part for idx in inst for i in idx}
            if g >= 0 and g not in told and names[g] in angles and angles[names[g]] > 1:
                sub = f"turns {angles[names[g]]:.0f}\u00b0"
                told.add(g)
            elif len(kinds) == 1:
                sub = part_label(engine.catalog.part_name(next(iter(kinds))))
            else:
                sub = f"{sum(len(i) for i in inst)} pieces"
        mid = len(frames) // 2
        mx = float(np.mean([a["track"][mid][0] for a in anchors]))
        my = float(np.mean([a["track"][mid][1] for a in anchors]))
        out.append({"label": str(sel.get("label", "")), "sub": str(sub), "n": len(inst),
                    "xray": bool(sel.get("xray", False)),
                    "parts": sorted({i for idx in inst for i in idx}),
                    "anchors": anchors, "side": "left" if mx < 540 else "right",
                    "x": mx, "y": my})
    mid = frames[len(frames) // 2]
    P = np.clip(screen(tl, mid, C.reshape(-1, 3))[:, :2], 0, 1080)
    layout_callouts(out, [float(P[:, 0].min()), float(P[:, 1].min()),
                          float(P[:, 0].max()), float(P[:, 1].max())],
                    top=200.0 if cfg.get("_osd") else 150.0)
    return out


def layout_callouts(out: list[dict], box, margin: float = 64.0, size: float = 1080.0,
                    top: float = 250.0, bottom: float = 880.0) -> None:
    """Where each label goes: in rows above and below a wide model, in columns beside a tall
    one. Sets align, lx/ly (label box anchor, px), attach (where the leader meets the label)
    and elbow (a bend, or None)."""
    x0, y0, x1, y1 = box
    H = 86.0                                         # label box height (title + sub)
    gap = 320.0
    per_row = int((size - 2 * margin - 300) // gap) + 1       # label centres between the margins
    if (x1 - x0) > 1.25 * (y1 - y0) and len(out) <= 2 * per_row:
        cy = (y0 + y1) / 2
        rows = {"top": [c for c in out if c["y"] < cy], "bottom": [c for c in out if c["y"] >= cy]}
        for a, b in (("top", "bottom"), ("bottom", "top")):
            while len(rows[a]) > per_row:          # a full row hands its middle-most on
                c = min(rows[a], key=lambda c: abs(c["y"] - cy))
                rows[a].remove(c)
                rows[b].append(c)
        for row in ("top", "bottom"):
            items = sorted(rows[row], key=lambda c: c["x"])
            if not items:
                continue
            ly = max(top, y0 - H - 50) if row == "top" else min(y1 + 50, bottom - H)
            lo, hi = margin + 150, size - margin - 150
            xs = [float(np.clip(c["x"], lo, hi)) for c in items]
            for k in range(1, len(xs)):
                xs[k] = max(xs[k], xs[k - 1] + gap)
            over = xs[-1] - hi
            if over > 0:
                xs = [x - over for x in xs]
                for k in range(len(xs) - 2, -1, -1):
                    xs[k] = min(xs[k], xs[k + 1] - gap)
            for c, x in zip(items, xs):
                c.update(align="center", lx=round(x, 1), ly=round(ly, 1),
                         attach=[round(x, 1), round(ly + (H if row == "top" else 0), 1)],
                         elbow=None)
        return
    # balance the columns: the one nearest the middle crosses over while one side has 2+ more
    mid = (x0 + x1) / 2
    while True:
        left = [c for c in out if c["side"] == "left"]
        right = [c for c in out if c["side"] == "right"]
        big, small = (left, "right") if len(left) > len(right) else (right, "left")
        if abs(len(left) - len(right)) < 2:
            break
        c = min(big, key=lambda c: abs(c["x"] - mid))
        c["side"] = small
    for side in ("left", "right"):
        items = sorted([c for c in out if c["side"] == side], key=lambda c: c["y"])
        n = len(items)
        if not n:
            continue
        for k, c in enumerate(items):
            ideal = min(max(c["y"], top), bottom)
            slot = top + (bottom - top) * (k + 0.5) / n if n > 1 else ideal
            c["label_y"] = 0.5 * ideal + 0.5 * slot
        for k in range(1, n):
            items[k]["label_y"] = max(items[k]["label_y"], items[k - 1]["label_y"] + 100)
        over = items[-1]["label_y"] - bottom
        if over > 0:
            for c in items:
                c["label_y"] -= over
        for c in items:
            y = round(c["label_y"], 1)
            x = margin if side == "left" else size - margin
            c.update(align=side, lx=x, ly=round(y - 43, 1),
                     attach=[x + (10 if side == "left" else -10), y],
                     elbow=[x + (200 if side == "left" else -200), y])


# ---------------------------------------------------------------------------- marks
def _B(tl):
    return tl["beat"]


def marks(tl, extras: dict) -> dict:
    """Key frames inside each segment, on the beat grid."""
    B = _B(tl)
    out = {}
    for s in tl["segments"]:
        a, name = s["start"], s["name"]
        if name == "cold_open":
            co = tl["cold_open"]
            out[name] = {"shots": [a + f for f, _ in co["shots"]], "catch": co["catch"],
                         "cut": co["cut"]}
        elif name == "open":
            out[name] = {"drop": a + B // 4, "land": a + B, "wipe": a + B, "wipe_end": a + 2 * B,
                         "words": [a + 2 * B, a + 2 * B + B // 2, a + 3 * B],
                         "band": a + 4 * B, "out": s["end"] - B // 2}
        elif name == "title":
            n = max(1, extras.get("chips", 4))
            out[name] = {"name": a + B // 4, "hero": a + B // 2, "count0": a + B,
                         "count1": a + 4 * B,
                         "chips": [a + 4 * B + round(k * 3 * B / n) for k in range(n)]}
        elif name == "palette":
            out[name] = {"head": a + B // 4, "swatch0": a + B // 2, "swatch1": a + 5 * B // 2,
                         "morph0": a + 3 * B, "morph1": a + 9 * B // 2, "count": a + 5 * B}
        elif name == "build":
            out[name] = {"sections": [x["start"] for x in tl["build"]["sections"]],
                         "land_last": tl["build"]["land_last"]}
        elif name == "scan":
            n = max(1, extras.get("checks", 8))
            span = 6 * B
            out[name] = {"sweep0": a + B, "sweep1": a + 7 * B,
                         "checks": [a + B + B // 2 + round(k * span / n) for k in range(n)],
                         "summary": a + 8 * B + B // 2, "fade0": a + 7 * B, "fade1": a + 9 * B}
        elif name == "mechanism":
            n = max(1, extras.get("callouts", 0))
            out[name] = {"gauge": a + B // 2,
                         "callouts": [a + B + round(k * 0.75 * B) for k in range(n)]}
        elif name == "lights":
            out[name] = {"power_on": tl["lights"]["power_on"],
                         "power_off": tl["lights"].get("power_off"), "label": a + B // 2}
        elif name == "lift":
            out[name] = {"label": a + B}
        elif name == "colourways":
            cw = tl.get("colourways") or {"wipes": []}
            out[name] = {"wipes": cw["wipes"],
                         "labels": [a + B // 2] + [w[1] - B // 2 for w in cw["wipes"]]}
        elif name == "booklet":
            bk = extras.get("booklet") or {}
            fan0 = a + bk.get("fan_start", 6 * B)
            settle = a + bk.get("settle", 9 * B)
            out[name] = {"head": fan0 + 4, "fan": fan0,
                         "chips": [min(s["end"] - B, settle + k * B // 3) for k in range(3)]}
        elif name == "outro":
            out[name] = {"logo": a + B // 2, "url": a + 3 * B // 2, "fine": a + 5 * B // 2}
    return out


def transitions(tl, theme) -> list[dict]:
    """Every cut, with its wipe: the theme's between segments, bricks into the build, a quick
    band between build sections, the house stud wipe into the outro. (Out of a cold open's
    black it's a straight cut.)"""
    B = _B(tl)
    segs = tl["segments"]
    out = []
    for a, b in zip(segs, segs[1:]):
        if a["name"] == "cold_open":
            continue
        kind = theme["transition"]
        if b["name"] == "build":
            kind = "bricks"
        elif b["name"] == "outro":
            kind = "studs"
        elif a["name"] == "open":
            kind = "studs" if theme["transition"] == "studs" else theme["transition"]
        out.append({"frame": b["start"], "type": kind, "half": B // 2, "from": a["name"],
                    "to": b["name"]})
    for s in tl["build"]["sections"][1:]:
        out.append({"frame": s["start"], "type": "band", "half": B // 2, "from": "build",
                    "to": "build"})
    return sorted(out, key=lambda t: t["frame"])


# ---------------------------------------------------------------------------- the plan
def plan_reel(engine, proj, model, tl, theme, out_dir: Path, work: Path, *,
              booklet_plan=None, booklet_steps=None, hero_file: Path | None = None,
              log=print) -> dict:
    cfg = T.video_config(model)
    placed = model.flatten()
    C = T.corners(engine, placed)
    B = tl["beat"]
    seg = {s["name"]: s for s in tl["segments"]}
    stats = model_stats(engine, proj, model, placed, tl, out_dir, booklet_steps, cfg)
    chk = checks(out_dir)
    reel = {
        "fps": tl["fps"], "frames": tl["frames"], "beat": B, "theme": theme,
        "segments": tl["segments"], "model": stats, "chips": title_chips(stats),
        "palette": palette(engine, model, placed), "thumbs": [],
        "hero": hero(out_dir, hero_file), "logo": "logo.png", "checks": chk,
    }
    # build: landings in order, the step reached, the sections, landing rings
    appear = np.asarray(tl["build"]["appear"])
    land = appear + tl["build"]["drop"]
    order = np.argsort(land, kind="stable")
    steps = np.asarray(tl["build"]["step"])
    run = np.maximum.accumulate(steps[order])
    height = np.maximum.accumulate(np.asarray(tl["build"]["top_mm"])[order])
    pulses = []
    for i in [int(x) for x in order[:MAX_PULSES]]:
        f = int(round(land[i]))
        c = C[i].reshape(-1, 3)
        x, y, _ = screen(tl, f, (c.min(0) + c.max(0)) / 2)[0]
        pulses.append([f, round(float(x), 1), round(float(y), 1)])
    last = int(order[-1])
    c = C[last].reshape(-1, 3)
    b = seg["build"]
    final = [[round(float(v), 1) for v in screen(tl, f, (c.min(0) + c.max(0)) / 2)[0][:2]]
             for f in range(int(land[last]) - 2, b["end"])]
    reel["build"] = {
        "land": np.round(land[order], 2).tolist(), "step": run.tolist(),
        "height": np.round(height, 1).tolist(), "ground_up": T.ground_up(cfg),
        "sections": tl["build"]["sections"], "land_last": tl["build"]["land_last"],
        "pulses": pulses, "final": {"start": int(land[last]) - 2, "track": final,
                                    "part": engine.catalog.part_name(placed[last].part)},
    }
    # the camera, for anything tracked in 3D
    reel["camera"] = {k: tl["camera"][k] for k in ("start", "pos", "target", "lens", "az", "el")}
    reel["wire"] = write_wire(engine, placed, work / "wire.bin")
    reel["parts"] = {"color": [p.color.rgb for p in placed],
                     "group": [int(g) for g in tl["groups"]["instance"]]}
    # per-shot silhouette boxes (screen px) for layout
    shots = {}
    allc = C.reshape(-1, 3)
    for s in tl["segments"]:
        if s["kind"] != "scene":
            continue
        boxes = []
        for f in range(s["start"], s["end"], max(1, (s["end"] - s["start"]) // 12)):
            P = screen(tl, f, allc)
            boxes.append([P[:, 0].min(), P[:, 1].min(), P[:, 0].max(), P[:, 1].max()])
        bx = np.array(boxes)
        shots[s["name"]] = dict(tl["shots"].get(s["name"], {}),
                                box=[round(float(v), 1) for v in
                                     (bx[:, 0].min(), bx[:, 1].min(), bx[:, 2].max(),
                                      bx[:, 3].max())])
    reel["shots"] = shots
    if "scan" in seg:
        reel["scan"] = {"points": connection_points(engine, model)}
    # mechanism: pose, angle of the first group, callouts
    if "mechanism" in seg:
        u = tl["mechanism"]["u"]
        names = tl["groups"]["names"]
        co = callouts(engine, model, placed, C, tl, dict(cfg, _osd=theme.get("overlay") == "vhs"),
                      log)
        ang = {}
        if names:
            # the gauge reads the first callout's group: degrees if it turns, mm if it slides
            gi = tl["groups"]["instance"]
            first = next((gi[i] for c in co for i in c["parts"] if gi[i] >= 0), 0)
            g = names[first]
            ts = np.linspace(0, 1, 97)
            Ms = [np.asarray((model.pose(float(t)) or {}).get(g, np.eye(4)), float) for t in ts]
            cum = np.concatenate([[0.0], np.cumsum([T.rotation_deg(np.linalg.inv(A) @ Bm)
                                                    for A, Bm in zip(Ms, Ms[1:])])])
            if cum[-1] > 1.0:
                ang = {"group": g, "unit": "\u00b0", "value": np.round(np.interp(u, ts, cum), 1).tolist()}
            else:
                mm = [0.4 * float(np.linalg.norm(M[:3, 3] - Ms[0][:3, 3])) for M in Ms]
                ang = {"group": g, "unit": " mm", "value": np.round(np.interp(u, ts, mm), 1).tolist()}
        reel["mechanism"] = {
            "name": model.meta.get("mechanism_name") or "Mechanism",
            "labels": list(model.meta.get("mechanism_labels") or ["", ""]),
            "u": u, "angle": ang, "callouts": co,
            "groups": tl["groups"]["frames"], "start": tl["groups"]["start"],
            "sweep": tl["mechanism"]["angles"],
        }
    if "lights" in seg:
        L = seg["lights"]
        leds = []
        for led in tl["lights"]["leds"]:
            tr = [[round(float(v), 1) for v in screen(tl, f, led["pos"])[0][:2]]
                  for f in range(L["start"], L["end"])]
            leds.append({"name": led.get("name", ""), "color": led["color"], "track": tr})
        reel["lights"] = {"power_on": tl["lights"]["power_on"],
                          "power_off": tl["lights"].get("power_off"),
                          "off_label": str(cfg.get("lights_off_label") or "Lights off"), "leds": leds,
                          "label": str(cfg.get("lights_label") or "Lights on"),
                          "tap": bool(cfg.get("lights_tap"))}
    if "lift" in seg:
        reel["lift"] = {"label": str(cfg.get("lift_label") or (cfg.get("lift") or {}).get("label")
                                     or "Lift-off")}
    if tl.get("colourways"):
        reel["colourways"] = colourway_items(engine, proj, model, placed, tl, cfg)
    if booklet_plan:
        fan = booklet_plan["fan"]
        reel["booklet"] = {"pages": booklet_plan["n_pages"], "leaves": booklet_plan["leaves"],
                           "turn": booklet_plan["turn"], "flip_end": booklet_plan["flip"]["end"],
                           "fan_start": fan["start"], "settle": fan["settle"],
                           "sheets": [sh["t0"] + sh["dur"] for sh in fan["sheets"]],
                           "files": [n for n, f in (("Instructions", "booklet.pdf"),
                                                    ("Parts list", "parts.csv"),
                                                    ("BrickLink list", "bricklink_wanted.xml"))
                                     if (out_dir / f).exists()]}
    if tl.get("cold_open"):
        reel["cold_open"] = cold_open_graphics(tl)
    extras = {"chips": len(reel["chips"]), "checks": len(chk["rows"]),
              "callouts": len(reel.get("mechanism", {}).get("callouts", [])),
              "booklet": reel.get("booklet")}
    reel["marks"] = marks(tl, extras)
    reel["transitions"] = transitions(tl, theme)
    reel["cues"] = cue_sheet(reel, tl, theme,
                             audio_assets(proj, cfg, (tl.get("cold_open") or {}).get("scene")))
    return reel


def cold_open_graphics(tl) -> dict:
    """What the compositor needs for the cold open: its frames, shots, letterbox, and where the
    sun is on screen each frame ([x, y] px of 1080, or None behind the camera or indoors) for
    the flare; with taps (a tap lamp) also the taps, the lights' level per frame and where the
    lamp's head is on screen."""
    co = tl["cold_open"]
    e, a = np.radians(co["sun"]["elevation"]), np.radians(co["sun"]["azimuth"])
    d = np.array([np.sin(a) * np.cos(e), -np.sin(e), np.cos(a) * np.cos(e)])
    cam = co["camera"]
    outdoors = co["scene"] == "sunset_road"         # the sun (else there's none to flare)
    sun, lamp = [], []
    px, pz = co["pivot"]
    glow = np.array([px, co["ground_y"] - 0.7 * co["height"], pz])      # a lamp's head
    for pos, tgt, lens in zip(cam["pos"], cam["target"], cam["lens"]):
        x, y, z = T.project((np.asarray(pos) + d * 1e7)[None], pos, tgt, lens, 1080.0)[0]
        sun.append([round(float(x), 1), round(float(y), 1)] if z > 0 and outdoors else None)
        if co.get("taps") is not None:
            x, y, _ = T.project(glow[None], pos, tgt, lens, 1080.0)[0]
            lamp.append([round(float(x), 1), round(float(y), 1)])
    out = {"start": co["start"], "end": co["end"], "cut": co["cut"],
           "shots": [co["start"] + f for f, _ in co["shots"]], "letterbox": co["letterbox"],
           "sun": sun, "size": co["sun"]["size"], "lens": cam["lens"]}
    if co.get("taps") is not None:                  # a tap lamp: when it clicks, how bright
        out.update(scene=co["scene"], taps=co["taps"], led=co["led"], lamp=lamp)
    elif not outdoors:
        out["scene"] = co["scene"]
    return out


def colourway_items(engine, proj, model, placed, tl, cfg) -> dict:
    """Each colourway's title and swatches: its most used colours among those that change."""
    cw = tl["colourways"]
    names = cw["order"]
    counts = {}
    counts[names[0]] = Counter(p.color.name for p in placed)
    rgb = {p.color.name: p.color.rgb for p in placed}
    for n in names[1:]:
        v = tl["variants"][n]
        c = Counter()
        for code in v["instance_colors"]:
            name, hexrgb = v.get("names", {}).get(str(code), [str(code), "#888888"])
            c[name] += 1
            rgb[name] = hexrgb
        counts[n] = c
    allc = set().union(*counts.values())
    same = {c for c in allc if len({counts[n].get(c, 0) for n in names}) == 1}
    items = []
    default_title = (cfg.get("default_title") or proj.config.get("model", {}).get("palette_title")
                     or "Original")
    for k, n in enumerate(names):
        top = [c for c, _ in counts[n].most_common() if c not in same][:4]
        items.append({"name": n, "title": default_title if k == 0 else tl["variants"][n]["title"],
                      "swatches": [{"name": c, "rgb": rgb[c] if rgb[c].startswith("#")
                                    else "#" + rgb[c]} for c in top]})
    return {"order": names, "wipes": cw["wipes"], "frames": cw["frames"], "items": items}


# ---------------------------------------------------------------------------- sound cues
def audio_assets(proj, cfg, scene: str | None = None) -> dict | None:
    """[video.audio]: the model's recorded sounds (files in its `dir`, default "audio/"):

        pull_start = "pull_start_1.mp3"   the cold open's pull-start; `catch` = s into it where
        catch = 0.73                      the engine catches (the running engine takes over)
        idle = "idle_1.mp3"               the running engine, looped under the cold open
        screams = ["scream_3.mp3", ...]   full-throttle revs: on the swing's peaks, the build's
                                          section changes (and the title without a burst)
        burst = "rev_burst_2.mp3"         rev-rev-REEEE on the title's stamp
        stings = [...]                    horror stings: the first on the title's stamp, the
        hits = [...]                      rest (with the metal hits and the booms, in turn) on
        booms = [...]                     the big cuts
        levels = { scream = -6 }          optional: peak dBFS per role (SAMPLE_LEVEL)
    and for a tap cold open (a tap lamp):
        clicks = ["click_2.mp3", ...]     the switch, on each tap (in turn)
        snaps_on = [...]                  a pop as the light comes on (in turn)...
        snaps_off = [...]                 ...and a softer one as it goes off
        room = "crickets_2.mp3"           the night outside, looped under it
    and for a glide (deep_sea; the set's own SCENE_SOUNDS fill in what isn't given):
        ambience = "..."                  the deep, looped under it
        pings = [...]                     sonar pings, at the start and after each cut
        bubbles = [...]                   bursts of bubbles on the cuts and as the bow passes
        groan = "..."                     the hull groaning, once
        churn = "..."                     the propeller, looped, louder as the stern nears

    `scene`: the cold open's set (its own sounds). Returns {"samples": {name: {path, sha1}},
    "roles": {role: [names]}, "catch", "levels"} or None without the table or set sounds."""
    import hashlib

    from ..paths import DATA_DIR
    a = dict(cfg.get("audio") or {})
    shared = SCENE_SOUNDS.get(scene or "")
    if not a and not shared:
        return None
    d = proj.dir / str(a.get("dir", "audio"))
    samples, roles = {}, {}

    def use(name, where=d):
        p = where / str(name)
        if not p.exists():
            raise SystemExit(f"[video.audio]: {p} is missing (tools/elevenlabs_sfx.py makes it)")
        samples[str(name)] = {"path": str(p), "sha1": hashlib.sha1(p.read_bytes()).hexdigest()}
        return str(name)
    singles = ("pull_start", "idle", "burst", "room", "ambience", "groan", "churn")
    lists = ("screams", "stings", "hits", "booms", "clicks", "snaps_on", "snaps_off", "pings",
             "bubbles")
    for role in singles:
        if a.get(role):
            roles[role] = [use(a[role])]
    for role in lists:
        if a.get(role):
            v = a[role]
            roles[role] = [use(x) for x in ([v] if isinstance(v, str) else v)]
    for role, v in (shared or {}).items():
        if role not in roles:
            where = DATA_DIR / "audio" / scene
            roles[role] = [use(x, where) for x in ([v] if isinstance(v, str) else v)]
    return {"samples": samples, "roles": roles, "catch": float(a.get("catch", 0.5)),
            "levels": {**SAMPLE_LEVEL, **(a.get("levels") or {})}}


def rev_peaks(curve, fps: float, gap: float = SCREAM_GAP, floor: float = 0.55,
              after: int = 0) -> list[int]:
    """Frames where the rev curve peaks (the saw's fastest moments), strongest first taken,
    at least `gap` s apart, above `floor`, not before frame `after`; in time order."""
    c = np.asarray(curve, float)
    k = np.arange(1, len(c) - 1)
    cand = [int(i) for i in k[(c[k] >= c[k - 1]) & (c[k] > c[k + 1]) & (c[k] >= floor)]
            if i >= after]
    out: list[int] = []
    for i in sorted(cand, key=lambda i: -c[i]):
        if all(abs(i - j) >= gap * fps for j in out):
            out.append(i)
    return sorted(out)


def tap_cues(cut: int, co: dict, roles: dict, add, play) -> None:
    """A tap cold open's sound: the switch clicking on every tap, a pop as the light comes on
    and a softer one as it goes off (recorded, in turn; else synthesised: a plastic snap, the
    power-up and power-down), the night outside under it all (the `room` recording, else a
    faint wind) and a mains hum while it's lit; all of it stopped dead at the cut."""
    a = co["start"]
    n = cut - a
    ons = offs = 0
    for i, (f, state) in enumerate(co["taps"]):
        if f >= cut:
            continue
        if roles.get("clicks"):
            play(f, roles["clicks"][i % len(roles["clicks"])], "click", align="peak", until=cut)
        else:
            add(f, "snap", gain=0.8)
        if state == "on":
            if roles.get("snaps_on"):
                play(f, roles["snaps_on"][ons % len(roles["snaps_on"])], "snap_on", align="peak",
                     until=cut, fade_out=0.15)
            else:
                add(f, "power", gain=0.8)
            ons += 1
        else:
            if roles.get("snaps_off"):
                play(f, roles["snaps_off"][offs % len(roles["snaps_off"])], "snap_off", until=cut,
                     fade_out=0.1)
            else:
                add(f, "power_off", gain=0.8)
            offs += 1
    if roles.get("room"):
        play(a, roles["room"][0], "room", loop=True, dur=n, until=cut, fade_in=0.5)
    else:
        add(a, "wind", dur=n, gain=0.35)
    led = np.clip(np.asarray(co.get("led") or [], float)[:n], 0.0, 1.0)
    if len(led) and led.max() > 0:
        add(a, "hum", dur=n, curve=np.round(led, 3).tolist(), gain=1.0)


def glide_cues(cut: int, co: dict, roles: dict, add, play, fps: float) -> None:
    """A glide's sound (deep_sea): the deep's rumble under it all, a sonar ping at the start
    and after each cut, bubbles bursting on the cuts and as the bow sweeps past, the hull
    groaning once, the propeller churning louder as the stern nears the camera (recorded, the
    set's own unless the model has its own; else a low wind and blips); all stopped at the
    cut."""
    a = co["start"]
    n = cut - a
    shots = [f for f, _ in co["shots"]]
    if roles.get("ambience"):
        play(a, roles["ambience"][0], "ambience", loop=True, dur=n, until=cut, fade_in=0.6)
    else:
        add(a, "wind", dur=n, gain=0.6)
    pings = [a + int(0.25 * fps)] + [a + f + int(0.4 * fps) for f in shots[1:]]
    for i, f in enumerate(p for p in pings if p < cut - int(0.3 * fps)):
        if roles.get("pings"):
            play(f, roles["pings"][i % len(roles["pings"])], "ping", until=cut, fade_out=0.3)
        else:
            add(f, "blip", pitch=-6, gain=0.6)
    if roles.get("bubbles"):
        b = roles["bubbles"]
        fb = a + shots[-1] + int(0.62 * (n - shots[-1])) if len(shots) > 1 else a + n // 2
        for i, f in enumerate([a + f for f in shots[1:]] + [fb]):
            if f < cut:
                play(f, b[i % len(b)], "bubbles", until=cut, fade_out=0.2)
    if roles.get("groan") and len(shots) > 1:
        play(a + shots[1] + int(0.5 * fps), roles["groan"][0], "groan", until=cut, fade_out=0.4)
    if roles.get("churn"):
        g = co["glide"]
        F = np.asarray(g["forward"], float)
        stern = np.asarray(g["path"], float)[:n] - F * float(g["extent"]["behind"])
        d = np.linalg.norm(np.asarray(co["camera"]["pos"], float)[:n] - stern, axis=1)
        near = (float(g["length"]) * 0.6 / np.maximum(d, 1e-6)) ** 1.5
        gc = np.clip(0.25 + near, 0.0, 1.0)
        play(a, roles["churn"][0], "churn", loop=True, dur=n, until=cut, fade_in=0.4,
             offset=1.5, gain_curve=np.round(gc, 3).tolist())


def cue_sheet(reel, tl, theme, assets: dict | None = None) -> dict:
    """The audio.py cue sheet: sections with moods, and every SFX on the frame it belongs.
    With `assets` (audio_assets) recorded sounds take over the chainsaw and add horror stings."""
    B = tl["beat"]
    mk = reel["marks"]
    fps = tl["fps"]
    ev = []

    def add(frame, kind, **kw):
        ev.append({"frame": float(frame), "type": kind, **kw})

    tape = theme.get("transition") == "glitch"
    film = theme.get("transition") == "burn"
    grind = theme.get("music") == "grindhouse"
    roles = (assets or {}).get("roles", {})
    lv = (assets or {}).get("levels", SAMPLE_LEVEL)

    def play(frame, name, role, **kw):
        add(frame, "sample", file=name, level=float(lv.get(role, -12.0)), **kw)
    cold = tl.get("cold_open") or {}
    if "cold_open" in mk and cold.get("taps") is not None:
        tap_cues(mk["cold_open"]["cut"], cold, roles, add, play)
    elif "cold_open" in mk and cold.get("glide") is not None:
        glide_cues(mk["cold_open"]["cut"], cold, roles, add, play, fps)
    elif "cold_open" in mk and "idle" in roles:   # the real chainsaw: pulled, running, screaming
        m, co = mk["cold_open"], tl["cold_open"]
        a, cut = co["start"], m["cut"]
        n = cut - a
        catch = min(n - 1, int(round((assets["catch"] if "pull_start" in roles else 0.0) * fps)))
        screams = roles.get("screams", [])
        peaks = rev_peaks(co["rev"][:n], fps, after=catch + int(0.3 * fps)) if screams else []
        if "pull_start" in roles:
            play(a, roles["pull_start"][0], "pull_start", until=min(cut, a + catch + int(0.6 * fps)),
                 fade_out=0.4)
        k = np.arange(catch, n)                   # the engine under the screams, ducked for them
        gc = np.ones(len(k))
        for p in peaks:
            w = np.clip(1 - np.abs(k - p) / (0.8 * fps), 0.0, 1.0)
            gc = np.minimum(gc, 1 - 0.6 * (0.5 - 0.5 * np.cos(np.pi * w)))
        play(a + catch, roles["idle"][0], "idle", loop=True, dur=n - catch, until=cut,
             fade_in=0.25 if "pull_start" in roles else 0.0, gain_curve=np.round(gc, 3).tolist())
        for i, p in enumerate(peaks):
            play(a + p, screams[i % len(screams)], "scream", align="peak", until=cut,
                 fade_out=0.25)
        add(a, "wind", dur=n, gain=0.8)
    elif "cold_open" in mk:                       # the engine and the wind, cut dead at the cut
        m, co = mk["cold_open"], tl["cold_open"]
        n = m["cut"] - co["start"]
        add(co["start"], "chainsaw_bed", dur=n, curve=co["rev"][:n],
            catch=m["catch"] - co["start"], gain=1.0)
        add(co["start"], "wind", dur=n, gain=0.8)
    # the big cuts' stings in turn: metal hit, boom, string stab, ...
    cut_stings = []
    for i in range(max(len(roles.get(r, [])) for r in ("hits", "booms", "stings"))):
        for role, lst in (("hit", roles.get("hits", [])), ("boom", roles.get("booms", [])),
                          ("sting", roles.get("stings", [])[1:])):
            if i < len(lst):
                cut_stings.append((role, lst[i]))
    bands = 0
    big = 0
    for t in reel["transitions"]:
        if t["type"] == "band":
            add(t["frame"] - 6, "burn" if film else "whoosh", dur=6, gain=0.5)
            if roles.get("screams"):              # a rev under the build's section change
                sc = roles["screams"]
                play(t["frame"], sc[(bands + 1) % len(sc)], "band", align="peak", fade_out=0.3,
                     duck=[3.0, 0.4])
                bands += 1
            continue
        if tape and t["type"] == "glitch":
            add(t["frame"] - 3, "glitch", dur=7, gain=0.8)
        elif film and t["type"] == "burn":
            add(t["frame"] - t["half"], "burn", dur=t["half"], gain=0.8)
        else:
            add(t["frame"] - t["half"], "whoosh", dur=t["half"], gain=0.8)
        boom = False
        stamp = t["to"] == "title" and grind and bool(roles.get("stings") or roles.get("burst"))
        if cut_stings and not stamp:              # a horror sting on the cut (the title's stamp
            #                                       has its own a moment later)
            role, name = cut_stings[big % len(cut_stings)]
            play(t["frame"], name, role, align="peak", duck=[4.0, 0.7])
            boom = role == "boom"
            big += 1
        if t["to"] in ("build", "scan", "outro") and not boom:
            add(t["frame"], "hit", gain=0.9 if t["to"] == "build" else 0.7)
    if "open" in mk:
        o = mk["open"]
        add(o["drop"], "whoosh", dur=o["land"] - o["drop"], gain=0.6)
        add(o["land"], "snap", gain=0.9)
        add(o["land"], "hit", gain=0.55)
        for k, w in enumerate(o["words"]):
            add(w, "hit" if k == len(o["words"]) - 1 else "pop", gain=0.4)
        add(o["band"], "blip", pitch=4)
    if "title" in mk:
        m = mk["title"]
        if grind and (roles.get("stings") or roles.get("burst") or roles.get("screams")):
            add(m["hero"], "slap", gain=1.0)      # the stamp: a string stab and a real saw
            if roles.get("stings"):
                play(m["hero"], roles["stings"][0], "sting", align="peak", duck=[5.0, 0.8])
            if roles.get("burst"):
                play(m["hero"] + 2, roles["burst"][0], "burst", fade_out=0.3)
            elif roles.get("screams"):
                play(m["hero"] + 2, roles["screams"][0], "scream", fade_out=0.3)
        elif grind:                   # the name is stamped on the hero beat, then the saw starts
            add(m["hero"], "slap", gain=1.0)
            add(m["hero"], "hit", gain=0.5)
            add(m["hero"] + 3, "chainsaw", gain=0.9)
        else:
            add(m["name"], "whoosh", dur=6, gain=0.5)
        for f in range(m["count0"], m["count1"], 3):
            add(f, "tick", gain=0.35)
        add(m["count1"], "pop", gain=0.8)
        for k, f in enumerate(m["chips"]):
            add(f, "blip", pitch=k)
    if "palette" in mk:
        m = mk["palette"]
        n = min(len(reel["palette"]), 24)
        for k in range(n):
            add(m["swatch0"] + (m["swatch1"] - m["swatch0"]) * k / max(1, n), "pop",
                gain=0.35, pitch=k % 7)
        add(m["morph0"], "whoosh", dur=m["morph1"] - m["morph0"], gain=0.5)
    if "build" in mk:
        land = reel["build"]["land"]
        last = -99.0
        rng = np.random.default_rng(3)
        for k, f in enumerate(land):
            if f - last >= 3.0:                     # at most ten clicks a second
                add(f, "click", gain=0.55 if k < 40 else 0.4, pitch=int(rng.integers(0, 6)))
                last = f
        add(mk["build"]["land_last"], "snap", gain=1.0)
        add(mk["build"]["land_last"], "pass", gain=0.7)
    if "scan" in mk:
        m = mk["scan"]
        add(m["sweep0"], "scan", dur=m["sweep1"] - m["sweep0"], gain=0.7)
        for k, (f, row) in enumerate(zip(m["checks"], reel["checks"]["rows"])):
            add(f, "warn" if row["status"] != "pass" else "blip", pitch=k)
        add(m["summary"], "pass", gain=0.9)
    if "mechanism" in mk:
        m = mk["mechanism"]
        s = next(x for x in tl["segments"] if x["name"] == "mechanism")
        u = np.asarray(reel["mechanism"]["u"])
        moving = np.abs(np.diff(u, prepend=u[0])) > 1e-3
        k = 0
        while k < len(u):
            if moving[k]:
                e = k
                while e < len(u) and moving[e]:
                    e += 1
                add(s["start"] + k, "motor", dur=e - k, gain=0.6)
                k = e
            k += 1
        for f in m["callouts"]:
            add(f, "blip", pitch=2, gain=0.5)
    if "lights" in mk and mk["lights"]["power_on"] is not None:
        add(mk["lights"]["power_on"] - 2 * B, "riser", dur=2 * B, gain=0.5)
        if reel.get("lights", {}).get("tap"):
            add(mk["lights"]["power_on"] - 1, "snap", gain=0.9)
        add(mk["lights"]["power_on"], "power", gain=1.0)
        if mk["lights"].get("power_off") is not None:
            if reel.get("lights", {}).get("tap"):
                add(mk["lights"]["power_off"] - 1, "snap", gain=0.9)
            add(mk["lights"]["power_off"], "power_off", gain=0.9)
    if "lift" in mk:
        s = next(x for x in tl["segments"] if x["name"] == "lift")
        add(s["start"], "riser", dur=(s["end"] - s["start"]) // 2, gain=0.6)
    if "colourways" in mk:
        for w in mk["colourways"]["wipes"]:
            add(w[0], "glitch" if tape else "burn" if film else "whoosh", dur=w[1] - w[0], gain=0.7)
        for f in mk["colourways"]["labels"]:
            add(f, "pop", gain=0.6)
    if "booklet" in reel and "booklet" in mk:
        s = next(x for x in tl["segments"] if x["name"] == "booklet")
        bk = reel["booklet"]
        lv = bk["leaves"]
        add(s["start"] + lv[0]["start"], "page", gain=0.7)            # the cover opens
        if len(lv) > 1:                                             # the thumb-flip
            r0 = s["start"] + lv[1]["start"]
            r1 = s["start"] + lv[-1]["start"] + lv[-1]["dur"]
            add(r0, "riffle", dur=r1 - r0, gain=0.8)
            for k, lf in enumerate(lv[1:]):
                add(s["start"] + lf["start"] + 0.35 * lf["dur"], "flick",
                    gain=0.35 + 0.35 * k / max(1, len(lv) - 2), pitch=k)
        for k, f in enumerate(bk.get("sheets", [])):                # sheets dealt into the fan
            add(s["start"] + f, "slap", gain=0.3 if k < len(bk["sheets"]) - 1 else 0.75)
        for f in mk["booklet"]["chips"]:
            add(f, "blip", pitch=3, gain=0.5)
    if "outro" in mk:
        m = mk["outro"]
        add(m["logo"], "hit", gain=0.8)
        add(m["logo"], "snap", gain=0.7)
        for k in range(len(reel["model"]["url"])):
            if k % 2 == 0:
                add(m["url"] + k * 0.7, "type", gain=0.35)
    theme_music = theme.get("music", "brand")
    for e in ev:                                  # theme flavour
        if theme_music == "playful" and e["type"] == "pop":
            e["type"] = "boing" if e.get("gain", 1) > 0.5 else "pop"
        elif grind and e["type"] in ("blip", "pop", "type"):
            e["type"] = "typewriter"              # labels are typed, results stamped
        elif grind and e["type"] == "pass":
            e["type"] = "slap"
    sections = [{"name": s["name"], "start": s["start"], "end": s["end"],
                 "mood": MOODS.get(s["name"], "groove")} for s in tl["segments"]]
    out = {"fps": tl["fps"], "frames": tl["frames"], "beat_frames": B, "style": theme_music,
           "seed": sum(map(ord, reel["model"]["slug"])), "sections": sections,
           "events": sorted(ev, key=lambda e: e["frame"])}
    if assets:
        out["samples"] = assets["samples"]
    return out
