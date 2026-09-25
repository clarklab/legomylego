"""Build video: `brickkit video SLUG` -> models/SLUG/out/video.mp4 (1080x1080 H.264, 30 fps).

Pipeline (see timeline.py for the storyboard):
  1. timeline.build_timeline plans every frame (engine side, no Blender);
  2. title and end cards are drawn with Pillow;
  3. the model-scene segments render in Blender EEVEE (render/blender_animate.py, which builds
     the scene with render/blender_scene.py's SceneBuilder);
  4. the booklet flip renders in its own Blender scene (booklet_flip.py) if out/booklet.pdf exists;
  5. crossfades are blended in and ffmpeg encodes.

Frames are cached per segment in out/video_frames/<full|preview>/<segment>/ with a hash of
everything that segment depends on (its slice of the timeline, render settings, the code), so a
re-run only renders what changed. `--preview` renders 540x540 at low samples, every 2nd frame
(-> out/video_preview.mp4); `--segments build,lift` renders and encodes just those segments
(-> out/video_build+lift.mp4)."""
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
from . import timeline as T

ANIMATE = Path(__file__).resolve().parent.parent / "render" / "blender_animate.py"
SCENE_SCRIPT = ANIMATE.with_name("blender_scene.py")
FLIP = Path(__file__).resolve().with_name("booklet_flip.py")
LOGO = paths.ROOT / "logo.png"
URL = "lego.superfun.games"
YELLOW = (255, 219, 6)          # the logo's background
RED = (226, 21, 42)
INK = (22, 22, 24)
QUALITY = {   # samples per engine
    "full": {"size": 1080, "samples": {"eevee": 48, "cycles": 24}, "step": 1, "page_px": 2048},
    "preview": {"size": 540, "samples": {"eevee": 12, "cycles": 8}, "step": 2, "page_px": 1024},
}
FONTS = {
    "heavy": ["/Library/Fonts/SF-Pro-Rounded-Heavy.otf", "/Library/Fonts/SF-Pro-Rounded-Black.otf",
              "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf",
              "/System/Library/Fonts/Supplemental/Arial Black.ttf", "DejaVuSans-Bold.ttf"],
    "bold": ["/Library/Fonts/SF-Pro-Rounded-Bold.otf",
             "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf",
             "/System/Library/Fonts/Supplemental/Arial Bold.ttf", "DejaVuSans-Bold.ttf"],
}


def _digest(obj) -> str:
    return hashlib.sha1(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def _file_hash(*files: Path) -> str:
    h = hashlib.sha1()
    for f in files:
        h.update(Path(f).read_bytes())
    return h.hexdigest()


# ---------------------------------------------------------------------------- cards (Pillow)
def _font(kind: str, size: int):
    from PIL import ImageFont
    for f in FONTS[kind]:
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def _ease(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


def _text_layer(size: int, text: str, font, fill, max_w: int):
    """RGBA layer with centred text, shrunk to fit max_w."""
    from PIL import Image, ImageDraw
    while True:
        box = font.getbbox(text)
        if box[2] - box[0] <= max_w or font.size <= 12:
            break
        font = font.font_variant(size=int(font.size * 0.94))
    w, h = box[2] - box[0], box[3] - box[1]
    im = Image.new("RGBA", (w + 8, h + 8), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((4 - box[0], 4 - box[1]), text, font=font, fill=fill)
    return im


def _paste(canvas, layer, cx, cy, alpha=1.0, scale=1.0):
    from PIL import Image
    if alpha <= 0:
        return
    if scale != 1.0:
        layer = layer.resize((max(1, int(layer.width * scale)), max(1, int(layer.height * scale))),
                             Image.LANCZOS)
    if alpha < 1.0:
        a = layer.getchannel("A").point(lambda v: int(v * alpha))
        layer = layer.copy()
        layer.putalpha(a)
    canvas.alpha_composite(layer, (int(round(cx - layer.width / 2)), int(round(cy - layer.height / 2))))


def _pill(text, font, s):
    from PIL import Image, ImageDraw
    box = font.getbbox(text)
    tw, th = box[2] - box[0], box[3] - box[1]
    pw, ph = int(tw + 64 * s), int(th + 38 * s)
    im = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, pw - 1, ph - 1), radius=ph // 2, fill=RED + (255,))
    d.text(((pw - tw) / 2 - box[0], (ph - th) / 2 - box[1]), text, font=font, fill=(255, 255, 255))
    return im


def _logo(width: int):
    from PIL import Image
    with Image.open(LOGO) as im:
        im = im.convert("RGBA")
        return im.resize((width, int(im.height * width / im.width)), Image.LANCZOS)


def title_frames(name: str, pieces: int, frames: list[int], n: int, size: int, out: Path):
    """Model name and piece count on the brand yellow; the text eases up into place."""
    from PIL import Image
    s = size / 1080
    title = _text_layer(size, name, _font("heavy", int(150 * s)), INK, int(900 * s))
    pill = _pill(f"{pieces:,} real LEGO pieces", _font("bold", int(50 * s)), s)
    logo = _logo(int(250 * s)) if LOGO.exists() else None
    for f in frames:
        t = f / max(1, n - 1)
        im = Image.new("RGBA", (size, size), YELLOW + (255,))
        a1, a2, a3 = _ease(f / 16), _ease((f - 6) / 16), _ease((f - 2) / 18)
        zoom = 1.0 + 0.025 * t
        if logo is not None:
            _paste(im, logo, size / 2, size * 0.8, a3, zoom)
        _paste(im, title, size / 2, size * 0.4 + (1 - a1) * 40 * s, a1, zoom)
        _paste(im, pill, size / 2, size * 0.4 + title.height / 2 + 80 * s + (1 - a2) * 30 * s,
               a2, zoom)
        im.convert("RGB").save(out / f"{f:05d}.png")


def end_frames(frames: list[int], n: int, size: int, out: Path):
    """Logo and the site URL."""
    from PIL import Image
    s = size / 1080
    logo = _logo(int(600 * s)) if LOGO.exists() else None
    url = _text_layer(size, URL, _font("heavy", int(62 * s)), INK, int(900 * s))
    for f in frames:
        im = Image.new("RGBA", (size, size), YELLOW + (255,))
        a1, a2 = _ease((f - 2) / 20), _ease((f - 12) / 16)
        if logo is not None:
            _paste(im, logo, size / 2, size * 0.43, 1.0, 0.93 + 0.07 * a1)
        _paste(im, url, size / 2, size * 0.8 + (1 - a2) * 24 * s, a2)
        im.convert("RGB").save(out / f"{f:05d}.png")


# ---------------------------------------------------------------------------- Blender runs
CHUNK = 40      # frames per Blender process: the GPU lock is released between chunks


def _run_blender(script: Path, job: dict, job_path: Path, label: str, log) -> float:
    """Render the job's missing frames, CHUNK frames per Blender process. GPU jobs take the
    machine-wide Blender lock (render/scene.py's blender_slot) one chunk at a time, so other
    agents' renders queue in between instead of thrashing the GPU alongside a long video; a
    CPU-only Cycles job leaves the GPU alone and skips the lock. Returns render seconds (not
    counting time spent waiting for the lock)."""
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


# ---------------------------------------------------------------------------- caching
def _keyed(block, f):
    frames = block["frames"]
    if not frames or f < block["start"]:
        return None
    k = f - block["start"]
    if k >= len(frames):
        return block.get("after") or frames[-1]
    return frames[k]


def segment_digest(tl: dict, seg: dict, q: dict, extra=None) -> str:
    """Hash of everything the frames of one segment depend on."""
    base = {"seg": seg, "q": q, "extra": extra}
    if seg["kind"] == "card":
        base.update(model=tl["model"], code=_file_hash(Path(__file__)),
                    logo=LOGO.stat().st_mtime_ns if LOGO.exists() else 0)
        return _digest(base)
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
    scene = {k: v for k, v in tl["scene"].items()}
    base.update(frames=_digest(per_frame), scene=_digest(scene),
                build=_digest(tl["build"]) if building else None,
                groups=[tl["groups"]["names"], tl["groups"]["instance"]],
                lift=tl["lift"]["instance"], leds=lt["leds"],
                code=_file_hash(ANIMATE, SCENE_SCRIPT))
    return _digest(base)


def _prepare_dir(d: Path, digest: str, force: bool) -> None:
    stamp = d / ".hash"
    if d.exists() and (force or not stamp.exists() or stamp.read_text() != digest):
        shutil.rmtree(d)
    d.mkdir(parents=True, exist_ok=True)
    stamp.write_text(digest)


# ---------------------------------------------------------------------------- encode
def encode(sequence, out: Path, fps: float, size: int, log) -> None:
    """sequence: [(png, None) | (png, (prev_png, weight))]; pipes raw RGB into ffmpeg."""
    from PIL import Image
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg not found on PATH")
    tmp = out.with_name(out.stem + ".tmp.mp4")
    cmd = [ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{size}x{size}", "-r", f"{fps:g}", "-i", "-",
           "-vf", "scale=out_color_matrix=bt709:out_range=tv",
           "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
           "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
           "-color_range", "tv", "-movflags", "+faststart", str(tmp)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    cache: dict[str, np.ndarray] = {}

    def load(p):
        if p not in cache:
            with Image.open(p) as im:
                a = np.asarray(im.convert("RGB"), np.float32)
            if a.shape[:2] != (size, size):
                a = np.asarray(Image.fromarray(a.astype(np.uint8)).resize((size, size),
                                                                          Image.LANCZOS),
                               np.float32)
            cache.clear() if len(cache) > 4 else None
            cache[p] = a
        return cache[p]

    try:
        for png, fade in sequence:
            a = load(str(png))
            if fade is not None:
                prev, w = fade
                a = load(str(prev)) * (1 - w) + a * w
            proc.stdin.write(np.clip(a + 0.5, 0, 255).astype(np.uint8).tobytes())
        proc.stdin.close()
    except BrokenPipeError:
        pass
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg failed")
    tmp.replace(out)
    log(f"encoded {len(sequence)} frames at {fps:g} fps -> {out}")


# ---------------------------------------------------------------------------- main entry
def make_video(engine, proj, model, out_dir: Path, *, preview: bool = False,
               segments: list[str] | None = None, force: bool = False,
               render_engine: str = "eevee", device: str = "gpu", log=None) -> Path:
    """Render and encode the build video; returns the .mp4 path. `render_engine` is "eevee"
    (default, fast) or "cycles" (the stills' renderer, slower); `device` "gpu" or "cpu" (Cycles
    only; useful when other renders are hogging the GPU)."""
    log = log or (lambda msg: print(msg, flush=True))
    t_start = time.time()
    qname = "preview" if preview else "full"
    q = QUALITY[qname]
    step, size = q["step"], q["size"]
    samples = q["samples"][render_engine]
    work = out_dir / "video_frames" / qname
    work.mkdir(parents=True, exist_ok=True)

    # booklet (optional)
    pdf = next((p for p in (out_dir / "booklet.pdf", proj.out / "booklet.pdf") if p.exists()), None)
    plan = None
    if pdf is not None:
        from .booklet_flip import prepare
        secs = {**T.SECONDS, **T.video_config(model).get("seconds", {})}
        plan = prepare(pdf, out_dir / "video_frames" / "pages", int(round(secs["booklet"] * T.FPS)),
                       T.FPS, q["page_px"])

    tl = T.build_timeline(engine, model, booklet=plan is not None)
    (work / "timeline.json").write_text(json.dumps(tl))
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
    log(f"{model.name}: {tl['model']['parts']} parts placed, {tl['model']['pieces']} pieces "
        f"on the parts list, {tl['model']['steps']} build steps; "
        f"video {tl['frames'] / tl['fps']:.1f} s: " +
        ", ".join(f"{s['name']} {(s['end'] - s['start']) / tl['fps']:.1f}s" for s in tl["segments"]))

    def frames_of(seg):
        return [f for f in range(seg["start"], seg["end"]) if f % step == 0]

    render_q = {"size": size, "samples": samples, "engine": render_engine, "device": device}
    scene_jobs, book_job = [], None
    for seg in chosen:
        d = work / seg["name"]
        extra = plan if seg["kind"] == "booklet" else None
        _prepare_dir(d, segment_digest(tl, seg, render_q, extra), force)
        fr = frames_of(seg)
        if seg["kind"] == "card":
            todo = [f for f in fr if not (d / f"{f:05d}.png").exists()]
            if todo:
                local = [f - seg["start"] for f in todo]
                n = seg["end"] - seg["start"]
                tmp = d / "_tmp"
                tmp.mkdir(exist_ok=True)
                if seg["name"] == "title":
                    title_frames(model.name, tl["model"]["pieces"], local, n, size, tmp)
                else:
                    end_frames(local, n, size, tmp)
                for f in todo:
                    (tmp / f"{f - seg['start']:05d}.png").replace(d / f"{f:05d}.png")
                tmp.rmdir()
                log(f"{seg['name']} card: {len(todo)} frames")
        elif seg["kind"] == "scene":
            scene_jobs += [[f, str(d / f"{f:05d}.png")] for f in fr]
        else:
            book_job = [[f - seg["start"], str(d / f"{f:05d}.png")] for f in fr]

    timings = {}
    if scene_jobs:
        job = {"timeline": str(work / "timeline.json"), "frames": scene_jobs,
               "size": [size, size], "samples": samples, "engine": render_engine,
               "device": device}
        timings["scene"] = _run_blender(ANIMATE, job, work / "scene_job.json", "model scene", log)
    if book_job:
        job = {"plan": plan, "frames": book_job, "size": [size, size], "samples": samples,
               "engine": render_engine, "device": device}
        timings["booklet"] = _run_blender(FLIP, job, work / "booklet_job.json", "booklet", log)

    # compose: crossfade into a segment from the previous segment's last frame
    sequence, prev_seg = [], None
    for seg in chosen:
        d = work / seg["name"]
        fr = frames_of(seg)
        prev_last = None
        if prev_seg is not None and seg["fade_in"] and prev_seg["end"] == seg["start"]:
            pf = frames_of(prev_seg)
            prev_last = work / prev_seg["name"] / f"{pf[-1]:05d}.png"
        for f in fr:
            png = d / f"{f:05d}.png"
            if not png.exists():
                raise RuntimeError(f"missing frame {png}")
            k = f - seg["start"]
            if prev_last is not None and k < seg["fade_in"]:
                w = float(T.smootherstep((k + 1) / (seg["fade_in"] + 1)))
                sequence.append((png, (prev_last, w)))
            else:
                sequence.append((png, None))
        prev_seg = seg

    tag = "" if not segments else "_" + "+".join(s["name"] for s in chosen)
    out = out_dir / f"video{tag}{'_preview' if preview else ''}.mp4"
    encode(sequence, out, T.FPS / step, size, log)
    total = time.time() - t_start
    log(f"done in {total / 60:.1f} min" +
        "".join(f"; {k} render {v / 60:.1f} min" for k, v in timings.items() if v))
    return out
