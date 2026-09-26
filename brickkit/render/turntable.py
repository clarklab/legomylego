"""Turntable loops: a slow photoreal (Cycles) orbit of the finished model with its mechanism
and lights doing their thing, as a short seamless muted MP4. The site plays it where the 3D
viewer can't run (no WebGL 2).

    brickkit turntable SLUG [--seconds 12] [--fps 24] [--size 720] [--samples 48] [--preview]

What moves, per model (model.meta["turntable"] can override):
  - lights and a mechanism (a tap lamp): tap, fangs bite, lights on; later tap, lights off
  - a mechanism only: it swings through its range and back, `cycles` times per loop
  - neither: just the orbit
Frames are rendered by the build video's Blender animator (render/blender_animate.py) from a
timeline written here: the model fully built, groups posed per frame, LEDs and glow per
frame, a camera orbiting once. Frames already on disk are reused, so a run resumes."""
from __future__ import annotations

import json
import math
import shutil
import subprocess
from pathlib import Path

import numpy as np

from .scene import BLENDER, blender_slot, model_scene

SCRIPT = Path(__file__).with_name("blender_animate.py")
LENS = 50.0
ELEVATION = 22.0
START_AZ = -35.0          # the hero render's angle, relative to the model's front
BACKDROP = "#EEF0F3"
CHUNK = 48                # frames per Blender process (the GPU lock is taken per chunk)


def _smooth(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * x * (x * (x * 6 - 15) + 10)


def _pulse(t, at, rise=0.045, hold=0.035, fall=0.07):
    """0..1..0 press: up over `rise`, held, back over `fall` (loop fractions)."""
    up = _smooth((t - at) / rise)
    down = _smooth((t - at - rise - hold) / fall)
    return up * (1 - down)


def _window(t, a, b, fade=0.035):
    """1 between a and b with soft edges."""
    return _smooth((t - a) / fade) * (1 - _smooth((t - b) / fade))


def program(model, n: int) -> dict:
    """Per-frame mechanism parameter u, LED level and studio dimming for an n-frame loop."""
    cfg = dict(model.meta.get("turntable", {}))
    t = np.arange(n) / n
    u = np.zeros(n)
    led = np.zeros(n)
    has_pose = model.pose is not None
    lit = bool(model.lights) or bool(model.glow_tags)
    kind = cfg.get("program") or ("tap" if (lit and has_pose) else "swing" if has_pose
                                  else "lights" if lit else "still")
    if kind == "tap":
        taps = cfg.get("taps", (0.16, 0.6))
        for a in taps:
            u = np.maximum(u, _pulse(t, a))
        on_at = taps[0] + 0.04
        off_at = taps[1] + 0.04
        led = _window(t, on_at, off_at, fade=0.02)
    elif kind == "swing":
        k = int(cfg.get("cycles", 1))
        u = 0.5 - 0.5 * np.cos(2 * math.pi * k * t)
    elif kind == "lights":
        led = _window(t, 0.25, 0.75)
    dim = 1.0 - (1.0 - float(cfg.get("lit_studio", 0.55))) * led
    return {"kind": kind, "u": u, "led": led, "dim": dim}


def camera(model, C: np.ndarray, n: int) -> dict:
    """Once round the model at the hero render's height, at a fixed distance that fits every
    angle (no zoom breathing)."""
    from ..video.timeline import fit, view_basis
    pts = C.reshape(-1, 3)
    front = float(model.meta.get("azimuth_offset", 0.0))
    target = (pts.min(0) + pts.max(0)) / 2
    dist = max(fit(pts, front + az, ELEVATION, LENS, 1.18)[1] for az in range(0, 360, 20))
    pos, tgt = [], []
    for f in range(n):
        az = front + START_AZ + 360.0 * f / n
        d, _, _ = view_basis(az, ELEVATION)
        pos.append((target + d * dist).tolist())
        tgt.append(target.tolist())
    return {"start": 0, "pos": pos, "target": tgt, "lens": [LENS] * n}


def timeline(engine, model, n: int) -> tuple[dict, dict]:
    from ..video.timeline import corners
    placed = model.flatten()
    prog = program(model, n)
    scene = model_scene(engine, model, lights_on=bool(model.lights) or bool(model.glow_tags),
                        placed=placed)
    scene["lights"] = []                          # LEDs are parented to their parts in Blender
    scene["backdrop"] = scene["ground_color"] = BACKDROP
    names = list(model.groups)
    inst_group = [names.index(g) if (g := model.group_of(p)) in names else -1 for p in placed]
    frames = []
    if model.pose is not None and names:
        eye = np.eye(4).reshape(-1).tolist()
        for u in prog["u"]:
            pose = model.pose(float(u))
            frames.append([np.asarray(pose[g]).reshape(-1).tolist() if g in pose else eye
                           for g in names])
    leds = []
    for light in model.lights:
        found = model.find(light["part"], placed)
        if found:
            leds.append({"instance": found[0].index, "color": light["color"],
                         "power": float(light["power"]),
                         "offset": [float(v) for v in light.get("offset", (0, 0, 0))]})
    k = len(placed)
    tl = {
        "scene": scene,
        "groups": {"names": names, "instance": inst_group, "start": 0, "frames": frames,
                   "after": []},
        "lift": {"instance": [0] * k, "start": 0, "frames": []},
        "build": {"appear": [-1e6] * k, "drop": 1, "offset": [[0.0, 0.0, 0.0]] * k},
        # the animator boosts LED power 5x for EEVEE; these are Cycles frames, like the stills
        "lights": {"leds": leds, "start": 0, "dim": prog["dim"].tolist(),
                   "led": (prog["led"] / 5.0).tolist(), "glow": prog["led"].tolist()},
        "camera": camera(model, corners(engine, placed), n),
        "variants": {},
    }
    return tl, prog


def make_turntable(engine, model, out_dir: Path, *, seconds: float = 12.0, fps: int = 24,
                   size: int = 720, samples: int = 48, preview: bool = False, log=print) -> Path:
    out_dir = Path(out_dir).resolve()
    if preview:
        size, fps, samples = size // 2, fps // 2, max(8, samples // 4)
    n = int(round(seconds * fps))
    work = out_dir / "turntable_frames" / ("preview" if preview else "full")
    work.mkdir(parents=True, exist_ok=True)
    tl, prog = timeline(engine, model, n)
    tl_path = work / "timeline.json"
    stamp = json.dumps({"n": n, "size": size, "samples": samples,
                        "kind": prog["kind"]}, sort_keys=True)
    if (work / "stamp.json").exists() and (work / "stamp.json").read_text() != stamp:
        for png in work.glob("*.png"):
            png.unlink()                          # settings changed: start over
    (work / "stamp.json").write_text(stamp)
    tl_path.write_text(json.dumps(tl))
    frames = [[f, str(work / f"{f:05d}.png")] for f in range(n)]
    todo = [fr for fr in frames if not Path(fr[1]).exists()]
    log(f"{model.name}: turntable {n} frames ({prog['kind']}), {len(todo)} to render")
    for i in range(0, len(todo), CHUNK):
        chunk = todo[i:i + CHUNK]
        job = {"timeline": str(tl_path), "frames": chunk, "size": [size, size],
               "samples": samples, "engine": "cycles"}
        job_path = work / "job.json"
        job_path.write_text(json.dumps(job))
        with blender_slot():
            r = subprocess.run([BLENDER, "-b", "--factory-startup", "-P", str(SCRIPT), "--",
                                str(job_path)], capture_output=True, text=True, timeout=7200)
        if r.returncode != 0 or "BRICKKIT_DONE" not in r.stdout:
            raise RuntimeError("Blender failed:\n" + r.stdout[-3000:] + "\n" + r.stderr[-3000:])
        log(f"  frames {i + len(chunk)}/{len(todo)}")
    out = out_dir / ("turntable_preview.mp4" if preview else "turntable.mp4")
    ffmpeg = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
    subprocess.run([ffmpeg, "-v", "error", "-y", "-framerate", str(fps), "-i",
                    str(work / "%05d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-crf", "22", "-preset", "slow", "-movflags", "+faststart", "-an",
                    str(out)], check=True)
    log(f"turntable -> {out}")
    return out
