"""Build video: `brickkit video SLUG` -> models/SLUG/out/video.mp4 (1080x1080 H.264 + AAC, 30 fps).

A showreel of the model, cut to a beat and driven by the model's own data:

    open        a brick drops and snaps; stud wipe; REAL LEGO PIECES. / CHECKED BY COMPUTER.
    title       the name in kinetic type over the hero still; piece counter; one stat row
    build       the time-lapse build (hero), growing up from the table, with a HUD
    scan        the finished model under a scanner: x-ray lines, the eight checks tick in
    mechanism   the moving parts, slow, with callouts tracked on real parts     (model.pose)
    lights      the set goes dark, the lights switch on                        (lights/glow)
    lift        it lifts off its stand                                          ([video] lift)
    colourways  wipes between the colourways                                    (variants)
    booklet     the instruction booklet's pages turn                            (booklet.pdf)
    outro       logo, the model's URL, the small print

Pipeline:
  1. timeline.py plans the 3D shots frame by frame; reel.py plans the graphics and the sound
     from the model's data (themes.py skins it: model.toml [video] theme = ...);
  2. the model-scene plates render in Blender EEVEE (render/blender_animate.py), colourways
     once per colour scheme, the booklet flip in its own scene (booklet_flip.py) - always under
     render/scene.py's blender_slot, one chunk of frames per Blender process;
  3. the compositor (web/, driven by compose.py in headless Chromium) draws every frame:
     plates, type, HUD, data graphics, wipes, grading;
  4. audio.py synthesises the music and effects from the cue sheet; ffmpeg encodes.

Plates are cached per segment in out/video_frames/<full|preview>/<segment>/, numbered from the
segment's start, with a hash of everything they depend on, so a re-run only renders what
changed (moving a segment in the edit keeps its plates). `--preview` is 540x540 at
low samples and 15 fps (-> out/video_preview.mp4); `--segments build,scan` makes just those
(-> out/video_build+scan.mp4); `--no-render` composes from whatever plates exist (grey where
missing) to iterate on graphics; `--stills 120,480` writes single composed frames as PNGs."""
from __future__ import annotations

import collections
import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path

import numpy as np

from .. import paths
from . import reel as R
from . import themes
from . import timeline as T

ANIMATE = Path(__file__).resolve().parent.parent / "render" / "blender_animate.py"
SCENE_SCRIPT = ANIMATE.with_name("blender_scene.py")
FLIP = Path(__file__).resolve().with_name("booklet_flip.py")
LOGO = paths.ROOT / "logo.png"
QUALITY = {   # samples per engine
    "full": {"size": 1080, "samples": {"eevee": 48, "cycles": 24}, "step": 1, "page_px": 2048,
             "crf": 18, "maxrate": "4600k"},
    "preview": {"size": 540, "samples": {"eevee": 12, "cycles": 8}, "step": 2, "page_px": 1024,
                "crf": 22, "maxrate": "2000k"},
}
MAX_MB = 40.0


def _digest(obj) -> str:
    return hashlib.sha1(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def _file_hash(*files: Path) -> str:
    h = hashlib.sha1()
    for f in files:
        h.update(Path(f).read_bytes())
    return h.hexdigest()


# ---------------------------------------------------------------------------- Blender runs
CHUNK = 40      # frames per Blender process: the GPU lock is released between chunks


def _run_blender(script: Path, job: dict, job_path: Path, label: str, log) -> float:
    """Render the job's missing frames, CHUNK frames per Blender process. GPU jobs take the
    machine-wide Blender lock (render/scene.py's blender_slot) one chunk at a time, so other
    renders queue in between instead of thrashing the GPU alongside a long video; a CPU-only
    Cycles job leaves the GPU alone and skips the lock. Returns render seconds (not counting
    time spent waiting for the lock)."""
    from contextlib import nullcontext

    from ..render.scene import BLENDER, blender_slot
    todo = [[f, p] for f, p in job["frames"] if not Path(p).exists()]
    if not todo:
        return 0.0
    cpu = job.get("engine") == "cycles" and str(job.get("device", "")).lower() == "cpu"
    log(f"{label}: rendering {len(todo)} frames in Blender"
        f"{' (CPU)' if cpu else ''}, {CHUNK} per process")
    busy, done, last = 0.0, 0, time.time()
    for c in range(0, len(todo), CHUNK):
        chunk = dict(job, frames=todo[c:c + CHUNK])
        job_path.write_text(json.dumps(chunk))
        cmd = [BLENDER, "-b", "--factory-startup", "-P", str(script), "--", str(job_path)]
        tail = collections.deque(maxlen=80)
        ok = False
        with (nullcontext() if cpu else blender_slot()):
            t0 = time.time()
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, bufsize=1)
            for line in proc.stdout:
                tail.append(line)
                if line.startswith("BRICKKIT_FRAME"):
                    done += 1
                    now = time.time()
                    if now - last > 30 or done == len(todo):
                        rate = (busy + now - t0) / done
                        log(f"  {label}: {done}/{len(todo)} frames, {rate:.1f} s/frame, "
                            f"~{rate * (len(todo) - done) / 60:.0f} min left")
                        last = now
                elif line.startswith("BRICKKIT_DONE"):
                    ok = True
            code = proc.wait()
            busy += time.time() - t0
        if code != 0 or not ok:
            raise RuntimeError(f"Blender failed ({label}):\n" + "".join(tail))
    return busy


def merge_subframes(merges) -> None:
    """Average rendered sub-frames into their frame (motion blur) and drop the parts."""
    from PIL import Image
    for out, parts in merges:
        if out.exists() or not all(Path(p).exists() for p in parts):
            continue
        acc = None
        for pth in parts:
            with Image.open(pth) as im:
                a = np.asarray(im.convert("RGB"), np.float32)
            acc = a if acc is None else acc + a
        tmp = out.with_suffix(".tmp.png")
        Image.fromarray(np.clip(acc / len(parts) + 0.5, 0, 255).astype(np.uint8)).save(tmp)
        tmp.replace(out)
        for pth in parts:
            Path(pth).unlink(missing_ok=True)


# ---------------------------------------------------------------------------- caching
def _keyed(block, f):
    frames = block["frames"]
    if not frames or f < block["start"]:
        return None
    k = f - block["start"]
    if k >= len(frames):
        return block.get("after") or frames[-1]
    return frames[k]


def segment_digest(tl: dict, seg: dict, q: dict, extra=None, variant: str | None = None,
                   legacy: bool = False) -> str:
    """Hash of everything the plates of one segment depend on - relative to the segment's
    start, so moving a segment in the edit keeps its plates. (`legacy`: the old absolute
    form, only to recognise plates rendered before; see migrate_plates.)"""
    if legacy:
        sg = {k: seg[k] for k in ("name", "start", "end", "kind")}
    else:
        sg = {"name": seg["name"], "length": seg["end"] - seg["start"], "kind": seg["kind"]}
    base = {"seg": sg, "q": q, "extra": extra}
    if seg["kind"] == "booklet":
        base.update(code=_file_hash(FLIP, SCENE_SCRIPT))
        return _digest(base)
    a, b = seg["start"], seg["end"]
    s0 = tl["scene_range"][0]
    cam, lt = tl["camera"], tl["lights"]
    per_frame = []
    for f in range(a, b):
        k = f - s0
        per_frame.append([cam["pos"][k], cam["target"][k], cam["lens"][k], lt["dim"][k],
                          lt["led"][k], lt["glow"][k], _keyed(tl["groups"], f),
                          _keyed(tl["lift"], f)])
    appear = np.asarray(tl["build"]["appear"])
    building = bool(((appear + tl["build"]["drop"]) > a).any())
    var = tl["variants"].get(variant) if variant else None
    if var is not None and not legacy:
        var = dict(var, frames=[x - a for x in var["frames"]])
    if building:
        built = [tl["build"]["appear"], tl["build"]["offset"]]
        if not legacy:
            built = [(np.asarray(built[0]) - a).round(4).tolist(), built[1]]
    base.update(frames=_digest(per_frame), scene=_digest(tl["scene"]),
                build=_digest(built) if building else None,
                groups=[tl["groups"]["names"], tl["groups"]["instance"]],
                lift=tl["lift"]["instance"], leds=lt["leds"], variant=var,
                code=_file_hash(ANIMATE, SCENE_SCRIPT))
    return _digest(base)


def migrate_plates(work: Path, old_tl: dict, tl: dict, q: dict, plan, log) -> None:
    """Plates rendered before plates were numbered per segment: where a segment's content is
    unchanged (same relative digest) and the plates are what the old timeline made (their
    stamp matches it), renumber them from the segment's start instead of re-rendering."""
    new = {s["name"]: s for s in tl["segments"]}
    for oseg in old_tl["segments"]:
        nseg = new.get(oseg["name"])
        if oseg["kind"] == "gfx" or nseg is None:
            continue
        keys = [None]
        if oseg["name"] == "colourways" and old_tl.get("colourways"):
            keys += old_tl["colourways"]["order"][1:]
        extra = plan if oseg["kind"] == "booklet" else None
        for v in keys:
            d = work / (oseg["name"] + (f"@{v}" if v else ""))
            stamp = d / ".hash"
            if not stamp.exists() or (d / ".relative").exists():
                continue
            try:
                ok = (stamp.read_text() == segment_digest(old_tl, oseg, q, extra, v, legacy=True)
                      and segment_digest(old_tl, oseg, q, extra, v)
                      == segment_digest(tl, nseg, q, extra, v))
            except (KeyError, IndexError):
                ok = False
            if not ok:
                continue
            files = sorted((f for f in d.glob("*.png") if f.stem.isdigit()), key=lambda f: int(f.stem))
            for f in files:                   # ascending: a target name is always free
                f.rename(d / f"{int(f.stem) - oseg['start']:05d}.png")
            stamp.write_text(segment_digest(tl, nseg, q, extra, v))
            (d / ".relative").touch()
            log(f"kept {len(files)} rendered frames of {d.name} (renumbered from its start)")


def _prepare_dir(d: Path, digest: str, force: bool) -> None:
    stamp = d / ".hash"
    if d.exists() and (force or not stamp.exists() or stamp.read_text() != digest):
        shutil.rmtree(d)
    d.mkdir(parents=True, exist_ok=True)
    stamp.write_text(digest)


# ---------------------------------------------------------------------------- encode
class Encoder:
    """Raw RGB frames into ffmpeg: H.264 (capped CRF so the file stays small), yuv420p,
    bt709, faststart; the audio track muxed in as AAC 192k."""

    def __init__(self, out: Path, fps: float, size: int, q: dict, audio: Path | None,
                 audio_offset: float = 0.0):
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg is None:
            raise RuntimeError("ffmpeg not found on PATH")
        self.out = out
        self.tmp = out.with_name(out.stem + ".tmp.mp4")
        cmd = [ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
               "-s", f"{size}x{size}", "-r", f"{fps:g}", "-i", "-"]
        if audio is not None:
            cmd += ["-ss", f"{audio_offset:.4f}", "-i", str(audio)]
        cmd += ["-map", "0:v"] + (["-map", "1:a"] if audio is not None else [])
        cmd += ["-vf", "scale=out_color_matrix=bt709:out_range=tv",
                "-c:v", "libx264", "-preset", "slow", "-crf", str(q["crf"]),
                "-maxrate", q["maxrate"], "-bufsize", str(int(q["maxrate"][:-1]) * 2) + "k",
                "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709",
                "-color_trc", "bt709", "-color_range", "tv"]
        if audio is not None:
            cmd += ["-c:a", "aac", "-b:a", "192k", "-shortest"]
        cmd += ["-movflags", "+faststart", str(self.tmp)]
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        self.n = 0

    def write(self, rgb: np.ndarray) -> None:
        self.proc.stdin.write(np.ascontiguousarray(rgb, np.uint8).tobytes())
        self.n += 1

    def close(self) -> None:
        self.proc.stdin.close()
        if self.proc.wait() != 0:
            raise RuntimeError("ffmpeg failed")
        self.tmp.replace(self.out)


def contact_sheet(thumbs: list[tuple[int, np.ndarray]], path: Path, fps: int, cols: int = 8):
    """Frames sampled through the video, labelled with their time."""
    from PIL import Image, ImageDraw
    if not thumbs:
        return
    w = thumbs[0][1].shape[1]
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w, rows * w), (0, 0, 0))
    for k, (f, a) in enumerate(thumbs):
        im = Image.fromarray(a)
        ImageDraw.Draw(im).text((6, 4), f"{f / fps:5.1f}s", fill=(255, 255, 255))
        sheet.paste(im, ((k % cols) * w, (k // cols) * w))
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path, quality=88)


# ---------------------------------------------------------------------------- hero cutout
def hero_cutout(engine, model, out_dir: Path, shape: dict, render: bool, log) -> Path | None:
    """A transparent Cycles still of the finished model (shadow kept) for the title: the site
    hero's angle, turned towards broadside for long models. Cached by the model's MPD."""
    from ..render.scene import render_model
    d = out_dir / "video_frames" / "hero_cut"
    az = T.avoid_end_on(-35.0, shape, 58.0)
    view = {"name": "hero", "azimuth": az, "elevation": 20, "lens": 60}
    mpd = next(iter(sorted(out_dir.glob("*.mpd"))), None)
    stamp = _digest([view, _file_hash(mpd) if mpd else model.slug, 2])
    f = d / "hero.png"
    if f.exists() and (d / ".hash").exists() and (d / ".hash").read_text() == stamp:
        return f
    if not render:
        return f if f.exists() else None
    log("title still: rendering a transparent hero in Cycles")
    render_model(engine, model, d, views=[view], size=1200, samples=96, transparent=True,
                 lens=60)
    (d / ".hash").write_text(stamp)
    return f


# ---------------------------------------------------------------------------- main entry
def make_video(engine, proj, model, out_dir: Path, *, preview: bool = False,
               segments: list[str] | None = None, force: bool = False,
               render_engine: str = "eevee", device: str = "gpu", audio: bool = True,
               render: bool = True, stills: list[int] | None = None, workers: int = 4,
               log=None) -> Path:
    """Render and encode the showreel; returns the .mp4 path (or the stills' directory)."""
    log = log or (lambda msg: print(msg, flush=True))
    t_start = time.time()
    qname = "preview" if preview else "full"
    q = QUALITY[qname]
    step, size = q["step"], q["size"]
    samples = q["samples"][render_engine]
    work = out_dir / "video_frames" / qname
    work.mkdir(parents=True, exist_ok=True)

    cfg = R.configure(proj, model)
    theme = themes.theme_for(cfg)
    beat = int(theme["beat"])
    variants = R.colourway_variants(engine, proj, model, log)

    # booklet (optional): its pages are rendered to PNG for the flip
    pdf = next((p for p in (out_dir / "booklet.pdf", proj.out / "booklet.pdf") if p.exists()), None)
    segs = T.plan_segments(model, booklet=pdf is not None, beat=beat, variants=list(variants),
                           cfg=cfg)
    plan = None
    if pdf is not None:
        from .booklet_flip import prepare
        bseg = next(s for s in segs if s["name"] == "booklet")
        vpdfs = {v: out_dir / "variants" / v / "booklet.pdf" for v in variants}
        plan = prepare(pdf, out_dir / "video_frames" / "pages", bseg["end"] - bseg["start"],
                       T.FPS, q["page_px"], beat,
                       {k: f for k, f in vpdfs.items() if f.exists()})
        if plan is None:
            segs = T.plan_segments(model, booklet=False, beat=beat, variants=list(variants),
                                   cfg=cfg)
    tl = T.build_timeline(engine, model, segs, beat=beat, variants=variants,
                          backdrop=theme.get("backdrop"))
    old_tl = None
    if (work / "timeline.json").exists():
        try:
            old_tl = json.loads((work / "timeline.json").read_text())
        except ValueError:
            old_tl = None
    (work / "timeline.json").write_text(json.dumps(tl))
    bplan = out_dir / "booklet" / "plan.json"
    bsteps = len(json.loads(bplan.read_text())["steps"]) if bplan.exists() else None
    cut = hero_cutout(engine, model, out_dir, tl["model"]["shape"], render, log)
    reel = R.plan_reel(engine, proj, model, tl, theme, out_dir, work, booklet_plan=plan,
                       booklet_steps=bsteps, hero_file=cut, log=log)

    names = [s["name"] for s in tl["segments"]]
    if segments:
        unknown = [s for s in segments if s not in T.ORDER]
        if unknown:
            raise SystemExit(f"unknown segment(s) {unknown}; choose from {', '.join(T.ORDER)}")
        missing = [s for s in segments if s not in names]
        if missing:
            log(f"skipping segment(s) this model doesn't have: {', '.join(missing)}")
    chosen = [s for s in tl["segments"] if not segments or s["name"] in segments]
    if not chosen:
        raise SystemExit("nothing to render")
    log(f"{model.name}: {tl['model']['parts']} parts placed, {reel['model']['pieces']} pieces, "
        f"{reel['model']['steps']} steps; theme {theme['name']} at {60 * T.FPS / beat:.1f} BPM; "
        f"video {tl['frames'] / tl['fps']:.1f} s: " +
        ", ".join(f"{s['name']} {(s['end'] - s['start']) / tl['fps']:.1f}s" for s in tl["segments"]))

    def frames_of(seg, a=None, b=None):
        a = seg["start"] if a is None else a
        b = seg["end"] if b is None else b
        return [f for f in range(a, b) if (f - seg["start"]) % step == 0]

    # -- 3D plates --------------------------------------------------------------------------
    render_q = {"size": size, "samples": samples, "engine": render_engine, "device": device}
    if old_tl is not None and not force:
        migrate_plates(work, old_tl, tl, render_q, plan, log)
    plates = {"step": step}
    jobs: dict[str | None, list] = collections.OrderedDict()
    book_job, book_merge = None, []
    for seg in chosen:
        if seg["kind"] == "gfx":
            continue
        if seg["kind"] == "booklet":
            d = work / "booklet"
            _prepare_dir(d, segment_digest(tl, seg, render_q, plan), force)
            plates["booklet"] = "frames/booklet"
            # fast page turns are rendered as sub-frames and averaged (motion blur)
            book_job, book_merge = [], []
            for f in frames_of(seg):
                k = f - seg["start"]
                out = d / f"{k:05d}.png"
                subs = plan["blur"].get(str(k)) if plan else None
                if subs and not out.exists():
                    parts = [str(d / f"{k:05d}.s{j}.png") for j in range(len(subs))]
                    book_job += [[k + dt, pth] for dt, pth in zip(subs, parts)]
                    book_merge.append((out, parts))
                else:
                    book_job.append([k, str(out)])
            continue
        vlist = [None]
        if seg["name"] == "colourways" and tl.get("colourways"):
            vlist = [None] + tl["colourways"]["order"][1:]
        for v in vlist:
            key = seg["name"] + (f"@{v}" if v else "")
            d = work / key
            _prepare_dir(d, segment_digest(tl, seg, render_q, variant=v), force)
            plates[key] = f"frames/{key}"
            a, b = seg["start"], seg["end"]
            if seg["name"] == "colourways" and tl.get("colourways"):
                a, b = tl["colourways"]["frames"][v or tl["colourways"]["order"][0]]
            jobs.setdefault(v, []).extend([f, str(d / f"{f - seg['start']:05d}.png")]
                                          for f in frames_of(seg, a, b))
    reel["plates"] = plates
    timings = {}
    if render:
        for v, fr in jobs.items():
            job = {"timeline": str(work / "timeline.json"), "frames": fr, "size": [size, size],
                   "samples": samples, "engine": render_engine, "device": device, "variant": v}
            timings[f"scene{'@' + v if v else ''}"] = _run_blender(
                ANIMATE, job, work / "scene_job.json", f"model scene{' (' + v + ')' if v else ''}",
                log)
        if book_job:
            job = {"plan": plan, "frames": book_job, "size": [size, size], "samples": samples,
                   "engine": render_engine, "device": device}
            timings["booklet"] = _run_blender(FLIP, job, work / "booklet_job.json", "booklet", log)
            merge_subframes(book_merge)
    (work / "reel.json").write_text(json.dumps(reel))

    roots = {"out": out_dir, "frames": work, "cut": out_dir / "video_frames" / "hero_cut",
             "logo.png": LOGO}

    # -- stills -------------------------------------------------------------------------------
    from PIL import Image
    if stills:
        from .compose import compose
        d = work / "stills"
        d.mkdir(exist_ok=True)
        compose(sorted(stills), size, reel, roots,
                lambda f, a: Image.fromarray(a).save(d / f"{f:05d}.png"), workers=workers, log=log)
        log(f"stills -> {d}")
        return d

    # -- sound --------------------------------------------------------------------------------
    wav, offset = None, 0.0
    frames = [f for seg in chosen for f in frames_of(seg)]
    if audio:
        from .audio import render_audio
        wav = work / "audio.wav"
        cues_digest = _digest([reel["cues"], _file_hash(Path(__file__).with_name("audio.py"))])
        stamp = work / "audio.hash"
        if not wav.exists() or not stamp.exists() or stamp.read_text() != cues_digest:
            t0 = time.time()
            stats = render_audio(reel["cues"], wav)
            stamp.write_text(cues_digest)
            log(f"sound: {stats['seconds']:.1f} s at {stats['lufs']:.1f} LUFS, true peak "
                f"{stats['true_peak_db']:.1f} dBTP ({time.time() - t0:.0f} s)")
        contiguous = all(b["start"] == a["end"] for a, b in zip(chosen, chosen[1:]))
        if not contiguous:
            wav = None                          # a partial, non-contiguous cut: no sound
        else:
            offset = chosen[0]["start"] / T.FPS

    # -- compose + encode ---------------------------------------------------------------------
    from .compose import compose
    tag = "" if not segments else "_" + "+".join(s["name"] for s in chosen)
    out = out_dir / f"video{tag}{'_preview' if preview else ''}.mp4"
    enc = Encoder(out, T.FPS / step, size, q, wav, offset)
    thumbs = []
    every = int(T.FPS)
    poster_f = reel["marks"]["title"]["chips"][-1] + beat if "title" in reel["marks"] else frames[0]
    poster = {}

    def sink(f, a):
        enc.write(a)
        if (f - frames[0]) % every < step:
            thumbs.append((f, np.asarray(Image.fromarray(a).resize((270, 270), Image.LANCZOS))))
        if abs(f - poster_f) < step and "a" not in poster:
            poster["a"] = a.copy()

    t0 = time.time()
    compose(frames, size, reel, roots, sink, workers=workers, log=log)
    enc.close()
    timings["compose"] = time.time() - t0
    contact_sheet(thumbs, out_dir / "video_frames" / f"contact_sheet{tag}{'_preview' if preview else ''}.jpg",
                  T.FPS)
    if not segments and not preview and "a" in poster:
        Image.fromarray(poster["a"]).save(out_dir / "video_poster.jpg", quality=90)
    mb = out.stat().st_size / 1e6
    log(f"encoded {len(frames)} frames at {T.FPS / step:g} fps -> {out} ({mb:.1f} MB)")
    if mb > MAX_MB and not preview:
        log(f"warning: {out.name} is {mb:.1f} MB (over {MAX_MB:.0f} MB)")
    total = time.time() - t_start
    log(f"done in {total / 60:.1f} min" +
        "".join(f"; {k} {v / 60:.1f} min" for k, v in timings.items() if v))
    return out
