"""Brand sizzle reel: several models in one quick, beat-cut reel.

    brickkit sizzle [SLUG ...] [--config showreel/sizzle.toml] [--out DIR] [--stills 30,400]
        -> DIR/sizzle.mp4 (1080 x 1080, 30 fps, H.264 + AAC), DIR/sizzle_poster.jpg,
           DIR/sizzle_contact.jpg

Everything is cut on the music's beats. With `music` (a file next to the config: the track
ElevenLabs made from showreel/audio/sfx.toml) the beats are found in the track itself
(video/beats.py: tempo, beat times, which beat starts the bar); without it a fixed grid at
`bpm` drives the house synth instead. The timeline is counted in bars of that grid:

    open     the logo, the tagline slammed word by word on the beats, then the open's last
             bar shared out between the models on the grid (one beat each for four; five go
             1/2, 1/2, 1, 1, 1): each one's cut-out on a coloured card, a teaser before the drop
    model    per model: its name slams over a few quick cuts of its own footage - the build
             time-lapse sped up, its signature moment (the key frame of it on a beat), its
             turntable, ... - with a stat chip or two and a caption
    finale   the models' turntables popping into a grid across the first bar (2 x 2 up to
             four; three across past that, the last row centred), the line
             ("5 models · 7,953 pieces · every brick checked")
    outro    the logo, the URL typed onto a yellow pill, the small print

Footage is each model's own, read-only: the video's cached plates (out/video_frames/full/
<segment>/), its turntable (out/turntable.mp4) and its hero cut-out; the frames used are
copied (as JPEG) into DIR/work/footage first, so a showreel re-rendering alongside doesn't
matter. The compositor is the showreels' (web/, a sizzle.html page with web/sizzle.js); the
sound is audio.py's: the music bed, the models' own recorded sounds and the house SFX on the
cuts, mastered to -16 LUFS / -2 dBTP (so the AAC encode stays under -1.5); the encoded
track is decoded and checked against the WAV for the AAC encoder's occasional clicks
(check_sound), and encoded again if it has one.

Config (showreel/sizzle.toml), shots in beats of the grid:

    title, url, tagline, line, music, bpm, [theme] overrides
    [timeline]   open, finale, outro (bars); open_words = [[word, beat], ...]
    [[model]]    slug, bars, caption, chips (pieces | headline | steps | colours), name (to
                 show instead of the model's), break (the music's kick and bass drop out
                 under the section: a filter break, back on the next section's first beat)
                 [[model.shot]] source (build | turntable | <any plate segment> | still +
                 file, a picture in the model's out/), beats, from/to (0..1 of the source) or
                 at (a frame) + lead (beats before it lands), speed, zoom + focus (crop in),
                 push, caption, sfx (a sound file) + sfx_align ("start" | "peak")
"""
from __future__ import annotations

import hashlib
import json
import math
import shutil
import subprocess
import time
import tomllib
from pathlib import Path

import numpy as np

from .. import paths

FPS = 30
CONFIG = paths.ROOT / "showreel" / "sizzle.toml"
SIZE = {"full": 1080, "preview": 540}
TP = -2.0           # dBTP for the master: the AAC encode adds up to ~0.5 dB, and the reel's
                    # dense track and hits get it there; the file still ends up under -1.5
CHIP_LABEL = {"pieces": "pieces", "steps": "steps", "colours": "colours"}


# ---------------------------------------------------------------------------- config, models
def load_config(path: Path) -> dict:
    cfg = tomllib.loads(Path(path).read_text())
    cfg["_dir"] = str(Path(path).resolve().parent)
    return cfg


def _read_json(p: Path, tries: int = 5) -> dict:
    for k in range(tries):          # a showreel re-rendering may be rewriting it right now
        try:
            return json.loads(p.read_text())
        except (ValueError, OSError):
            time.sleep(1.0 + k)
    return json.loads(p.read_text())


def model_info(slug: str, models_dir: Path | None = None) -> dict:
    """What the reel needs of a model, from its last showreel run (read-only): name, pieces,
    size, steps, colours, notice, and its footage - plate segments with their frame counts, the
    turntable, the hero cut-out."""
    out_dir = (models_dir or paths.MODELS_DIR) / slug / "out"
    work = out_dir / "video_frames" / "full"
    if not (work / "reel.json").exists():
        raise SystemExit(f"{slug}: no showreel yet (run `brickkit video {slug}` first)")
    r = _read_json(work / "reel.json")
    plates = {}                       # segment -> {n, first}: plates are numbered from the
    for d in sorted(p for p in work.iterdir() if p.is_dir()):    # segment's start; a colourway
        ks = sorted(int(f.stem) for f in d.glob("*.png") if f.stem.isdigit())   # renders its span
        if ks:
            plates[d.name] = {"n": len(ks), "first": ks[0]}
    m = r["model"]
    return {"slug": slug, "name": m["name"], "pieces": int(m["pieces"]), "steps": int(m["steps"]),
            "colours": int(m.get("colours", 0)), "headline": list(m["headline"]),
            "notice": m.get("notice", ""), "plates": plates, "work": str(work), "out": str(out_dir),
            "turntable": str(out_dir / "turntable.mp4") if (out_dir / "turntable.mp4").exists() else None,
            "hero": str(out_dir / "video_frames" / "hero_cut" / "hero.png")
            if (out_dir / "video_frames" / "hero_cut" / "hero.png").exists() else None}


# ---------------------------------------------------------------------------- the beat grid
def music_grid(cfg: dict, work: Path, log=print) -> dict:
    """{"beats": [frame of every beat], "bar0": index of the first bar's first beat,
    "bpm", "track": path or None, "length": frames the music lasts}. Beats before the first
    detected one are extended back by the period (so the grid covers the pre-roll)."""
    music = cfg.get("music")
    if music:
        from . import beats as Bt
        track = Path(cfg["_dir"]) / music
        # found again when the track or the tracker changes
        sha = hashlib.sha1(track.read_bytes() + Path(Bt.__file__).read_bytes()).hexdigest()
        cache = work / "beats.json"
        res = None
        if cache.exists():
            c = json.loads(cache.read_text())
            if c.get("sha1") == sha:
                res = c
        if res is None:
            from . import audio as A
            x = A.load_sample(track, 48000)
            res = dict(Bt.track(x, 48000, prefer=float(cfg.get("bpm", 128))), sha1=sha,
                       seconds=len(x) / 48000)
            work.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(res))
        log(f"music: {track.name}, {res['bpm']:.2f} BPM, {len(res['beats'])} beats found")
        return grid_from_beats(res["beats"], res["downbeat"], res["bpm"], res["seconds"],
                               str(track))
    bpm = float(cfg.get("bpm", 128.57))
    period = 60.0 / bpm
    n = int(cfg.get("bars_total", 24)) * 4 + 8
    return grid_from_beats([i * period for i in range(n)], 0, bpm, n * period, None)


def grid_from_beats(beats_s, downbeat: int, bpm: float, seconds: float, track) -> dict:
    """Beats (s) -> frames, extended back to the start by whole periods, the bar phase kept."""
    b = list(beats_s)
    period = 60.0 / bpm
    lead = 0
    while b[0] - period >= -1e-6:
        b.insert(0, b[0] - period)
        lead += 1
    first_bar = (downbeat + lead) % 4
    frames = [int(round(t * FPS)) for t in b]
    return {"beats": frames, "bar0": first_bar, "bpm": bpm, "track": track,
            "length": int(round(seconds * FPS))}


# ---------------------------------------------------------------------------- the plan
def _bar(g, k: int) -> int:
    """Frame where bar k starts (bar 0: the first bar of the grid)."""
    i = g["bar0"] + 4 * k
    if i < len(g["beats"]):
        return g["beats"][i]
    per = (g["beats"][-1] - g["beats"][0]) / max(1, len(g["beats"]) - 1)
    return int(round(g["beats"][-1] + (i - len(g["beats"]) + 1) * per))


def _beat(g, bar: int, k: float) -> int:
    """Frame of beat k (0-based, may be fractional) counted from bar `bar`'s start."""
    i0 = g["bar0"] + 4 * bar
    beats = g["beats"]
    i = i0 + k
    lo = int(math.floor(i))
    per = (beats[-1] - beats[0]) / max(1, len(beats) - 1)
    if lo + 1 < len(beats) and lo >= 0:
        return int(round(beats[lo] + (i - lo) * (beats[lo + 1] - beats[lo])))
    return int(round(beats[-1] + (i - len(beats) + 1) * per))


def _source_frames(info: dict, src: str) -> tuple[int, int]:
    """(frames, number of the first) of a footage source."""
    if src == "turntable":
        return int(12 * FPS), 0                     # the loop, at 30 fps after extraction
    if src.startswith("still-"):
        return 1, 0                                 # a picture: one frame, pushed in
    if src not in info["plates"]:
        raise SystemExit(f"{info['slug']}: no {src!r} footage (has {', '.join(info['plates'])})")
    return info["plates"][src]["n"], info["plates"][src]["first"]


def plan_shot(info: dict, shot: dict, start: int, end: int, beat_len: float,
              key: int | None = None) -> dict:
    """Which footage frame shows at each output frame of a shot: {src, start, end, from,
    speed, key?}. `at` + `lead`: frame `at` of the source lands `lead` beats in (on output
    frame `key` when given: the grid's beat, else `lead` average beats after `start`), at
    `speed` (default 1); else from/to (fractions of the source) spread over the shot. A
    `file` (source "still": a picture in the model's out/, e.g. renders/tower_close.png) is
    one frame. `zoom` and `focus` ([x, y], 0..1 of the frame: the point kept in the middle)
    crop into the footage; `push` is how far it creeps in over the shot (default 0.04)."""
    src = shot["source"]
    if src == "still":
        src = "still-" + Path(str(shot["file"])).stem
    n, first = _source_frames(info, src)
    length = max(1, end - start)
    if "at" in shot:                                # `at` counts from the segment's start
        speed = float(shot.get("speed", 1.0))
        if key is None:
            key = start + int(round(float(shot.get("lead", 1)) * beat_len))
        f0 = float(shot["at"]) - first - (key - start) * speed
        out = {"from": f0, "speed": speed, "key": key}
    else:
        a = float(shot.get("from", 0.0)) * (n - 1)
        if "speed" in shot:
            speed = float(shot["speed"])
        else:
            b = float(shot.get("to", 1.0)) * (n - 1)
            speed = (b - a) / length
        out = {"from": a, "speed": speed}
    out.update(src=src, start=start, end=end, n=n, first=first)
    if src.startswith("still-"):
        out["file"] = str(shot["file"])
    for k in ("zoom", "push"):
        if k in shot:
            out[k] = float(shot[k])
    if "focus" in shot:
        out["focus"] = [float(v) for v in shot["focus"]]
    return out


def frame_of(shot: dict, f: int) -> int:
    """The source frame a planned shot shows at output frame f (clamped to the footage)."""
    k = shot["from"] + (f - shot["start"]) * shot["speed"]
    return int(np.clip(math.floor(k + 0.5), 0, shot["n"] - 1))     # as the page's Math.round


def spread(n: int, beats: int = 4, long_first: bool = True) -> list[tuple[float, float]]:
    """n hits over `beats` beats on the grid: (start, length) in beats. One a beat when there
    are as many beats (4 in 4), else eighths shared out (sixteenths past 2 a beat), the longer
    ones first (5 in 4: 1, 1, 1, 1/2, 1/2 - an accelerating fill) or last (1/2, 1/2, 1, 1, 1:
    the last one holds a whole beat, as under a wipe)."""
    if n <= 0:
        return []
    unit = 1.0 if n <= beats else 0.5 if n <= 2 * beats else 0.25
    units = int(round(beats / unit))
    base, extra = divmod(units, n)
    if base == 0:                                   # more hits than sixteenths: just split it
        return [(beats * k / n, beats / n) for k in range(n)]
    lens = [base + (1 if k < extra else 0) for k in range(n)]
    if not long_first:
        lens.reverse()
    out, t = [], 0
    for ln in lens:
        out.append((t * unit, ln * unit))
        t += ln
    return out


def chip_values(info: dict, which) -> list[dict]:
    out = []
    for c in which:
        if c == "headline":
            out.append({"value": str(info["headline"][0]), "label": str(info["headline"][1])})
        elif c in CHIP_LABEL:
            out.append({"value": f"{info[c]:,}", "label": CHIP_LABEL[c]})
    return out


def plan(cfg: dict, infos: dict, g: dict) -> dict:
    """The reel: segments with their shots and graphics, transitions, and the cue sheet."""
    tl = cfg.get("timeline") or {}
    models = [m for m in cfg["model"] if m["slug"] in infos]
    name = {m["slug"]: str(m.get("name") or infos[m["slug"]]["name"]) for m in models}
    bar = 0
    segs = []
    beat_len = (g["beats"][-1] - g["beats"][0]) / max(1, len(g["beats"]) - 1)
    # -- open: logo, the words, the teaser -----------------------------------------------
    ob = int(tl.get("open", 4))
    words = [[w, _beat(g, 0, float(b))] for w, b in tl.get("open_words", [])]
    teaser = []
    tb = ob - 1                                    # the open's last bar: a card a model,
    # sharing the bar on the grid, the quick ones first (the last is half under the wipe)
    for m, (t0, ln) in zip(models, spread(len(models), 4, long_first=False)):
        teaser.append({"slug": m["slug"], "name": name[m["slug"]], "start": _beat(g, tb, t0),
                       "end": _beat(g, tb, t0 + ln)})
    segs.append({"name": "sz_open", "kind": "gfx", "start": 0, "end": _bar(g, ob),
                 "logo": _beat(g, 0, 0), "words": words, "teaser": teaser,
                 "cards": [_bar(g, k) for k in range(ob)]})
    bar = ob
    # -- the models ---------------------------------------------------------------------------
    for idx, m in enumerate(models):
        info = infos[m["slug"]]
        nb = int(m.get("bars", 3))
        a, e = _bar(g, bar), _bar(g, bar + nb)
        shots, beat = [], 0.0
        for sh in m.get("shot", []):
            s0 = _beat(g, bar, beat)
            key = _beat(g, bar, beat + float(sh.get("lead", 1))) if "at" in sh else None
            beat += float(sh.get("beats", 2))
            s1 = min(e, _beat(g, bar, beat))
            if s1 <= s0:
                break
            p = plan_shot(info, sh, s0, s1, beat_len, key)
            p["caption"] = sh.get("caption", "")
            if sh.get("sfx"):
                p["sfx"] = {"file": sh["sfx"], "align": sh.get("sfx_align", "start"),
                            "gain": float(sh.get("sfx_gain", 1.0)), "level": float(sh.get("sfx_level", -9.0))}
            shots.append(p)
        if shots:
            shots[-1]["end"] = e                    # the last shot runs to the section's end
        chips = chip_values(info, m.get("chips", ["pieces", "headline"]))
        chip_at = [_beat(g, bar, 4 + 2 * k) for k in range(len(chips))]
        segs.append({"name": "sz_model", "kind": "gfx", "start": a, "end": e, "slug": m["slug"],
                     "title": name[m["slug"]], "index": idx + 1, "count": len(models),
                     "break": bool(m.get("break", False)),
                     "shots": shots, "chips": [dict(c, at=f) for c, f in zip(chips, chip_at)],
                     "caption": m.get("caption", ""),
                     "beats": [_beat(g, bar, k) for k in range(4 * nb)]})
        bar += nb
    # -- finale: the grid, the line -----------------------------------------------------------
    fb = int(tl.get("finale", 3))
    a, e = _bar(g, bar), _bar(g, bar + fb)
    n_models = len(models)
    pieces = sum(infos[m["slug"]]["pieces"] for m in models)
    line = str(cfg.get("line", "{n} models · {pieces} pieces|every brick checked"))
    line = line.format(n=n_models, pieces=f"{pieces:,}")
    hits = [t for t, _ in spread(n_models, 4)]   # the cells pop in across the first bar
    segs.append({"name": "sz_finale", "kind": "gfx", "start": a, "end": e,
                 "cells": [{"slug": m["slug"], "name": name[m["slug"]], "at": _beat(g, bar, t),
                            "from": k / max(4, n_models)} for k, (m, t) in enumerate(zip(models, hits))],
                 "line": line.split("|"), "line_at": [_beat(g, bar + 1, 2 * k) for k in range(len(line.split("|")))],
                 "pieces": pieces, "count": n_models, "beats": [_beat(g, bar, k) for k in range(4 * fb)]})
    bar += fb
    # -- outro -------------------------------------------------------------------------------
    ob2 = int(tl.get("outro", 2))
    a = _bar(g, bar)
    e = min(_bar(g, bar + ob2), g["length"]) if g.get("track") else _bar(g, bar + ob2)
    notices = [infos[m["slug"]]["notice"] for m in models if infos[m["slug"]]["notice"]]
    segs.append({"name": "sz_outro", "kind": "gfx", "start": a, "end": max(e, a + 30),
                 "logo": _beat(g, bar, 0), "url_at": _beat(g, bar, 2),
                 "fine_at": _beat(g, bar, 4), "url": cfg.get("url", ""),
                 "disclaimer": cfg.get("disclaimer", ""), "notices": notices,
                 "beats": [_beat(g, bar, k) for k in range(4 * ob2)]})
    total = segs[-1]["end"]
    # -- transitions: wipes into each section (the first model's at the drop is the brick wall)
    trans = []
    half = max(4, int(round(beat_len / 2)))
    for k, s in enumerate(segs[1:], 1):
        kind = "bricks" if k == 1 else "studs"
        col = "#FEDB05" if s["name"] == "sz_outro" or k % 2 == 0 else "#A34C32"
        trans.append({"frame": s["start"], "type": kind, "half": half, "from": segs[k - 1]["name"],
                      "to": s["name"], "color": col})
    reel = {"fps": FPS, "frames": total, "beat": int(round(beat_len)), "segments": segs,
            "transitions": trans, "marks": {}, "thumbs": [], "hero": None, "logo": "logo.png",
            "grid": {"beats": [b for b in g["beats"] if b < total], "bpm": g["bpm"]}}
    reel["cues"] = cue_sheet(reel, g, cfg)
    return reel


# ---------------------------------------------------------------------------- sound
def cue_sheet(reel: dict, g: dict, cfg: dict) -> dict:
    """audio.py cues: the music (the track, or the house synth on the grid), whooshes and
    snaps on the wipes and slams, the models' own sounds on their shots."""
    ev = []
    base = Path(cfg["_dir"])
    samples = {}

    def smp(path):
        p = (base / path) if not Path(path).is_absolute() else Path(path)
        if not p.exists():
            p = paths.ROOT / path
        if not p.exists():
            raise SystemExit(f"sizzle: sound {path} is missing")
        key = str(path)
        samples[key] = {"path": str(p), "sha1": hashlib.sha1(p.read_bytes()).hexdigest()}
        return key

    def add(frame, kind, **kw):
        ev.append({"frame": float(frame), "type": kind, **kw})
    whoosh = cfg.get("whoosh")
    for t in reel["transitions"]:
        if whoosh:
            add(t["frame"], "sample", file=smp(whoosh), align="peak", level=-12.0)
        else:
            add(t["frame"] - t["half"], "whoosh", dur=t["half"], gain=0.8)
        add(t["frame"], "hit", gain=0.55 if t["type"] == "studs" else 0.8)
    for s in reel["segments"]:
        if s["name"] == "sz_open":
            add(s["logo"], "snap", gain=0.9)
            add(s["logo"], "hit", gain=0.5)
            for _, f in s["words"]:
                add(f, "snap", gain=0.55)
            for t in s["teaser"]:
                add(t["start"], "pop", gain=0.5, pitch=2)
        elif s["name"] == "sz_model":
            for k, sh in enumerate(s["shots"]):
                if k:
                    add(sh["start"], "click", gain=0.5, pitch=k)
                if sh.get("sfx"):
                    x = sh["sfx"]
                    at = sh.get("key", sh["start"])
                    add(at, "sample", file=smp(x["file"]), level=x["level"], gain=x["gain"],
                        align="peak" if x["align"] == "peak" else None, until=s["end"],
                        fade_out=0.3, duck=[4.0, 0.6])
            for c in s["chips"]:
                add(c["at"], "pop", gain=0.35, pitch=4)
        elif s["name"] == "sz_finale":
            for c in s["cells"]:
                add(c["at"], "click", gain=0.6, pitch=3)
            for f in s["line_at"]:
                add(f, "snap", gain=0.6)
        elif s["name"] == "sz_outro":
            add(s["logo"], "snap", gain=0.8)
            add(s["logo"], "hit", gain=0.6)
            url = s["url"]
            for k in range(0, len(url), 2):
                add(s["url_at"] + k * 0.7, "type", gain=0.3)
    for e in ev:                                   # the house sample events need no None keys
        if e.get("align") is None:
            e.pop("align", None)
    total = reel["frames"]
    cues = {"fps": FPS, "frames": total, "beat_frames": reel["beat"], "style": "brand",
            "seed": 2024, "events": sorted(ev, key=lambda e: e["frame"])}
    breaks = [s for s in reel["segments"] if s.get("break")]
    if g.get("track"):
        cues["sections"] = [{"name": "sizzle", "start": 0, "end": total, "mood": "cold"}]
        cues["track"] = {"path": g["track"], "fade_out": 0.4}
        if breaks:                                 # the kick and bass out, a sweep into the drop
            cues["track"]["breaks"] = [{"start": s["start"], "end": s["end"], "hz": 320.0,
                                        "rise": reel["beat"], "to": 1200.0, "gain": 2.5}
                                       for s in breaks]
    else:                                          # the house synth, section by section
        moods = {"sz_open": "rise", "sz_model": "groove", "sz_finale": "feature", "sz_outro": "end"}
        cues["sections"] = [{"name": s["name"], "start": s["start"], "end": s["end"],
                             "mood": "breakdown" if s.get("break") else moods[s["name"]]}
                            for s in reel["segments"]]
    if samples:
        cues["samples"] = samples
    return cues


# ---------------------------------------------------------------------------- footage
def turntable_frames(tt: Path, d: Path, size: int, fps: int = FPS) -> int:
    """A model's turntable loop as d/00000.jpg ... at `fps`, size x size (made again only when
    the video or the size changes). Returns how many frames there are."""
    d.mkdir(parents=True, exist_ok=True)
    stamp = d / ".source"
    sig = f"{tt.stat().st_size}-{tt.stat().st_mtime_ns}-{size}-{fps}"
    if not stamp.exists() or stamp.read_text() != sig:
        for f in d.glob("*.jpg"):
            f.unlink()
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tt), "-vf",
                        f"fps={fps},scale={size}:{size}:flags=lanczos", "-q:v", "3",
                        "-start_number", "0", str(d / "%05d.jpg")], check=True)
        stamp.write_text(sig)
    return len(list(d.glob("*.jpg")))


def footage(reel: dict, infos: dict, work: Path, size: int, log=print) -> None:
    """Copy the frames the reel shows into work/footage/<slug>/<source>/<k>.jpg (and each
    model's turntable at 30 fps, its hero cut-out), rewriting the plan's shots to the URLs."""
    from PIL import Image, ImageOps
    root = work / "footage"
    need: dict[tuple, set] = {}
    first, shots_file = {}, {}
    for s in reel["segments"]:
        if s["name"] == "sz_model":
            for sh in s["shots"]:
                ks = {frame_of(sh, f) for f in range(sh["start"], sh["end"])}
                need.setdefault((s["slug"], sh["src"]), set()).update(ks)
                first[(s["slug"], sh["src"])] = sh.get("first", 0)
                if sh.get("file"):
                    shots_file[(s["slug"], sh["src"])] = sh["file"]
        if s["name"] in ("sz_finale",):
            for c in s["cells"]:
                need.setdefault((c["slug"], "turntable"), set())
    n_new = 0
    for (slug, src), ks in need.items():
        info = infos[slug]
        d = root / slug / src
        d.mkdir(parents=True, exist_ok=True)
        if src.startswith("still-"):                # a picture, as the one frame
            pic = Path(info["out"]) / shots_file[(slug, src)]
            dst = d / "00000.jpg"
            if not dst.exists() or dst.stat().st_mtime < pic.stat().st_mtime:
                with Image.open(pic) as im:
                    ImageOps.fit(im.convert("RGB"), (size, size), Image.LANCZOS).save(dst, quality=92)
                n_new += 1
            continue
        if src == "turntable":
            turntable_frames(Path(info["turntable"]), d, size)
            continue
        for k in sorted(ks):
            dst = d / f"{k:05d}.jpg"
            src_png = Path(info["work"]) / src / f"{k + first.get((slug, src), 0):05d}.png"
            if dst.exists() and dst.stat().st_mtime >= src_png.stat().st_mtime:
                continue
            with Image.open(src_png) as im:
                im.convert("RGB").resize((size, size), Image.LANCZOS).save(dst, quality=90)
            n_new += 1
    for slug, info in infos.items():
        if info.get("hero"):
            dst = root / slug / "hero.png"
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists() or dst.stat().st_mtime < Path(info["hero"]).stat().st_mtime:
                shutil.copyfile(info["hero"], dst)
    log(f"footage: {n_new} frames copied into {root}")


# ---------------------------------------------------------------------------- the sound, encoded
def _decode(mp4: Path, sr: int = 48000) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(mp4), "-vn", "-ac", "2", "-ar",
                          str(sr), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, "<f4").reshape(-1, 2).astype(float)


def encoded_faults(mp4: Path, wav: Path, sr: int = 48000) -> tuple[float, list[float]]:
    """(true peak in dBTP, times of bursts) of a video's sound track as a player decodes it,
    against the WAV it was made from: a burst is a 20 ms stretch where the decoded sound is
    off by more than -26 dBFS and by more than twice the source's own peak (a click)."""
    from .audio import load_sample, true_peak_db
    b = _decode(mp4, sr)
    a = load_sample(wav, sr)
    n, w = min(len(a), len(b)), sr // 50
    bursts = []
    for i in range(0, n - w, w):
        e, pk = np.abs(b[i:i + w] - a[i:i + w]).max(), np.abs(a[i:i + w]).max()
        if e > 0.05 and e > 2 * pk:
            bursts.append(round(i / sr, 2))
    return true_peak_db(b, sr), bursts


def _aac_options() -> list[list[str]]:
    enc = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True,
                         text=True).stdout
    out = [["-c:a", "aac_at", "-b:a", "192k"]] if " aac_at " in enc else []   # macOS's own
    return out + [["-c:a", "aac", "-b:a", "192k", "-aac_coder", "fast"],
                  ["-c:a", "aac", "-b:a", "256k"]]


def check_sound(mp4: Path, wav: Path, ceiling: float = -1.5, log=print) -> float:
    """ffmpeg's own AAC encoder now and then puts a burst into a quiet, wide passage (+10 dB
    or more: a click, the same input, the same burst; the reel's filter break and open have
    had them). Decode the track and compare it with the WAV; on a burst or a true peak over
    the ceiling, encode the sound again (the video copied): AudioToolbox's AAC where ffmpeg
    has it, else other settings, until it's clean. Returns the true peak left in `mp4`."""
    tp, bursts = encoded_faults(mp4, wav)
    if tp <= ceiling and not bursts:
        return tp
    tmp = mp4.with_name(mp4.stem + ".sound.mp4")
    for opts in _aac_options():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(mp4), "-i", str(wav), "-map", "0:v",
                        "-map", "1:a", "-c:v", "copy", *opts, "-shortest", "-movflags", "+faststart",
                        str(tmp)], check=True)
        t2, b2 = encoded_faults(tmp, wav)
        log(f"sound: the AAC encode had {len(bursts)} burst(s), true peak {tp:.1f} dBTP; "
            f"again with {' '.join(opts[1:])}: {len(b2)}, {t2:.1f} dBTP")
        if t2 <= ceiling and not b2:
            tmp.replace(mp4)
            return t2
    tmp.unlink(missing_ok=True)
    return tp


# ---------------------------------------------------------------------------- make it
def make_sizzle(config: Path = CONFIG, slugs: list[str] | None = None, out: Path | None = None,
                stills: list[int] | None = None, preview: bool = False, audio: bool = True,
                workers: int = 4, log=None) -> Path:
    from PIL import Image

    from . import LOGO, Encoder, contact_sheet
    from . import themes
    from .compose import compose
    log = log or (lambda msg: print(msg, flush=True))
    t0 = time.time()
    cfg = load_config(config)
    out = Path(out) if out else Path(cfg["_dir"])
    work = out / "work"
    work.mkdir(parents=True, exist_ok=True)
    wanted = slugs or [m["slug"] for m in cfg["model"]]
    cfg["model"] = [m for m in cfg["model"] if m["slug"] in wanted]
    infos = {s: model_info(s) for s in wanted}
    g = music_grid(cfg, work, log)
    reel = plan(cfg, infos, g)
    size = SIZE["preview" if preview else "full"]
    footage(reel, infos, work, 1080, log)
    reel["theme"] = themes.theme_for({"theme": "brand", "theme_overrides": cfg.get("theme") or {}})
    (work / "sizzle.json").write_text(json.dumps(reel))
    total = reel["frames"]
    log(f"sizzle: {len(infos)} models, {total / FPS:.1f} s at {g['bpm']:.1f} BPM: " +
        ", ".join(f"{s['name'].replace('sz_', '')}"
                  f"{' ' + s.get('slug', '') if s.get('slug') else ''} {(s['end'] - s['start']) / FPS:.1f}s"
                  for s in reel["segments"]))
    roots = {"work": work, "logo.png": LOGO}
    if stills:
        d = work / "stills"
        d.mkdir(exist_ok=True)
        compose(sorted(stills), size, reel, roots, lambda f, a: Image.fromarray(a).save(d / f"{f:05d}.png"),
                workers=workers, log=log, page="sizzle.html")
        log(f"stills -> {d}")
        return d
    wav = None
    if audio:
        from .audio import render_audio
        wav = work / "sizzle.wav"
        st = render_audio(reel["cues"], wav, tp=TP)
        log(f"sound: {st['seconds']:.1f} s at {st['lufs']:.1f} LUFS, true peak {st['true_peak_db']:.1f} dBTP")
    step = 2 if preview else 1
    frames = list(range(0, total, step))
    q = {"crf": 20 if not preview else 24, "maxrate": "5200k" if not preview else "2000k"}
    mp4 = out / ("sizzle_preview.mp4" if preview else "sizzle.mp4")
    enc = Encoder(mp4, FPS / step, size, q, wav, 0.0)
    thumbs, poster = [], {}
    # the poster: the finale's grid once the piece count has landed (just before it cuts away)
    poster_f = next((s["end"] - 8 for s in reel["segments"] if s["name"] == "sz_finale"), 0)

    def sink(f, a):
        enc.write(a)
        if f % FPS < step:
            thumbs.append((f, np.asarray(Image.fromarray(a).resize((270, 270), Image.LANCZOS))))
        if abs(f - poster_f) < step and "a" not in poster:
            poster["a"] = a.copy()

    compose(frames, size, reel, roots, sink, workers=workers, log=log, page="sizzle.html")
    enc.close()
    if wav is not None:
        log(f"sound in the video: true peak {check_sound(mp4, wav, log=log):.1f} dBTP")
    contact_sheet(thumbs, out / ("sizzle_contact_preview.jpg" if preview else "sizzle_contact.jpg"), FPS)
    if "a" in poster and not preview:
        Image.fromarray(poster["a"]).save(out / "sizzle_poster.jpg", quality=90)
    mb = mp4.stat().st_size / 1e6
    log(f"encoded {len(frames)} frames -> {mp4} ({mb:.1f} MB) in {(time.time() - t0) / 60:.1f} min")
    return mp4
