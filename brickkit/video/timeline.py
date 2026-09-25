"""Build-video timeline (engine side; no Blender needed).

The video is an edit of beat-aligned segments (see `plan_segments`). Graphics-only segments
(open, title, palette, outro) are drawn by the compositor; the booklet flip has its own Blender
scene; the model-scene segments are planned here, frame by frame, for render/blender_animate.py:

    build       parts drop in, in instruction order, section by section; each section is its
                own orbiting shot (the cut between sections hides under a wipe), with speed
                ramps: every section starts slow and speeds up, and the last pieces slow down
    scan        slow orbit of the finished model, framed to one side for the checks panel
    mechanism   `model.pose`: build pose -> 0 -> 1 -> build pose, slow, close on the moving parts
    lights      the studio goes dark, then the LEDs and glowing parts switch on   (lights/glow)
    lift        everything but `exclude_tag` rises and hovers         (meta["video"]["lift"])
    colourways  slow push round the model; each colourway renders its own frames (variants)

`build_timeline(engine, model, segments, ...)` returns a JSON-able dict; every frame number is
absolute (frame 0 is the first frame of the video, at `fps`):

    fps, frames, beat   frame rate, length, frames per beat
    segments            [{name, start, end, kind}] kind: gfx | scene | booklet
    scene               model scene for Blender (render/scene.py's model_scene)
    scene_range         [start, end): the frames rendered in the model scene
    build               per instance: appear frame, drop length, start offset (LDU), video
                        order, booklet step, section; `sections` [{title, start, end, ...}]
    camera              per scene frame: pos and target (LDraw coords), lens (mm), az, el
    shots               per scene segment: framing window and layout hints for the graphics
    groups              moving groups: names, per-instance group, per-frame pose matrices
    lift                per-instance flag, per-frame world matrices of the lifted parts
    lights              LEDs and per scene frame levels (dim, led, glow); power-on frame
    variants            colourways: per variant the instance colours and the frames it shows
    mechanism           per mechanism frame the pose parameter u (0..1) and the groups' angles

Per-model tweaks go in `model.meta["video"]` or model.toml [video] (all optional), e.g.
    {"lift": {"exclude_tag": "stand", "height": 80}, "beats": {"build": 28}, "drop": 24,
     "build_first": "tag", "sections": [[1, "Base"], [40, "Dome"]]}
"""
from __future__ import annotations

import fnmatch
import math
import re
from collections import OrderedDict

import numpy as np

from ..ldraw.matrix import apply, translate
from ..model.builder import Placement
from ..render.scene import model_scene

FPS = 30
BEAT = 15                 # frames per beat (120 BPM at 30 fps); themes pick their own
LENS = 70.0
MARGIN = 1.3              # frame = 1/MARGIN of the image is model (a little air round it)
DROP = 24.0               # LDU a part travels as it drops in (about a stud)
DROP_FRAMES = 8           # how long a drop takes
ORDER = ("open", "title", "palette", "build", "scan", "mechanism", "lights", "lift",
         "colourways", "booklet", "outro")
KIND = {"open": "gfx", "title": "gfx", "palette": "gfx", "outro": "gfx", "booklet": "booklet"}
BEATS = {"open": 6, "title": 8, "palette": 8, "build": 32, "scan": 12, "mechanism": 12,
         "lights": 8, "lift": 6, "colourway": 4, "booklet": 12, "outro": 8}
MAX_SECTIONS = 6
LIGHTS_DIM = 0.16         # studio light level with the LEDs on
DARK = 0.035              # the blackout before the LEDs switch on
LIFT_DIM = 0.3
WIPE_BEATS = 2            # colourway wipe length


# ---------------------------------------------------------------------------- helpers
def smootherstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * x * (x * (6 * x - 15) + 10)


def ease_out(x):
    x = np.clip(x, 0.0, 1.0)
    return 1 - (1 - x) ** 3


def _gauss(a: np.ndarray, sigma: float) -> np.ndarray:
    if sigma <= 0 or len(a) < 3:
        return a
    from scipy.ndimage import gaussian_filter1d
    return gaussian_filter1d(a, sigma, axis=0, mode="nearest")


def _near(angle: float, ref: float) -> float:
    """`angle` plus a whole number of turns, as close as possible to `ref` (degrees)."""
    return angle + 360.0 * round((ref - angle) / 360.0)


def bom_pieces(engine, model, placed) -> int:
    """Pieces on the parts list (what the title counts; the site and booklet agree)."""
    from ..bom.bom import build_bom
    return sum(line.qty for line in build_bom(placed, engine.catalog,
                                              getattr(model, "extras", ())))


def video_config(model) -> dict:
    """model.toml [video] merged under model.meta["video"] (design.py wins)."""
    toml = model.meta.get("_video_toml") or {}
    meta = model.meta.get("video", {}) or {}
    return {**toml, **meta}


def corners(engine, placed) -> np.ndarray:
    """(n, 8, 3) world bounding-box corners of every placed part."""
    boxes = {}
    out = np.zeros((len(placed), 8, 3))
    for i, p in enumerate(placed):
        if p.part not in boxes:
            lo, hi = engine.geom.mesh(p.part).bbox
            boxes[p.part] = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1])
                                      for z in (lo[2], hi[2])])
        out[i] = apply(p.M, boxes[p.part])
    return out


def insert_directions(model) -> list:
    """World-space insertion hint of every part, in `model.flatten()` order (None = from above).
    A hint is the direction a part comes in from (see checks/buildability.py)."""
    out = []

    def walk(sub, W):
        for it in sub.items:
            if isinstance(it, Placement):
                d = None
                if it.insert is not None:
                    v = W[:3, :3] @ np.asarray(it.insert, float)
                    n = float(np.linalg.norm(v))
                    d = v / n if n > 1e-9 else None
                out.append(d)
            else:
                walk(it.sub, W @ it.M)

    walk(model.main, np.eye(4))
    return out


# ---------------------------------------------------------------------------- camera maths
def view_basis(az: float, el: float):
    """Unit vectors (LDraw coords) for a camera at azimuth/elevation (degrees): `d` points from
    the target to the camera, `r` and `u` span the image plane. Azimuth 0 looks at the front
    (-Z), matching render/blender_scene.py's cameras."""
    a, e = math.radians(az), math.radians(el)
    d = np.array([math.sin(a) * math.cos(e), -math.sin(e), -math.cos(a) * math.cos(e)])
    up = np.array([0.0, -1.0, 0.0])
    u = up - d * float(up @ d)
    u /= np.linalg.norm(u)
    r = np.cross(u, d)
    return d, r, u


def camera_basis(pos, target):
    """(right, up, forward) of the video camera (LDraw coords): Blender's track-to with the
    camera's -Z at the target and its Y towards world up, as blender_animate.py sets it."""
    f = np.asarray(target, float) - np.asarray(pos, float)
    f /= np.linalg.norm(f)
    up = np.array([0.0, -1.0, 0.0])
    u = up - f * float(up @ f)
    n = np.linalg.norm(u)
    u = u / n if n > 1e-9 else np.array([0.0, 0.0, 1.0])
    r = np.cross(f, u)
    return r, u, f


def project(points, pos, target, lens, size=1.0):
    """Image coordinates of world points (n, 3) for the video camera: (n, 3) array of x, y (in
    pixels of a size x size image, y down) and depth. The sensor is 36 mm across the square."""
    r, u, f = camera_basis(pos, target)
    c = np.asarray(points, float) - np.asarray(pos, float)
    z = c @ f
    k = lens / 36.0 / np.maximum(z, 1e-6)
    x = size / 2 + (c @ r) * k * size
    y = size / 2 - (c @ u) * k * size
    return np.stack([x, y, z], axis=-1)


def fit(points: np.ndarray, az: float, el: float, lens: float = LENS, margin: float = MARGIN,
        window=(-1.0, 1.0, -1.0, 1.0)):
    """Target and distance that frame `points` (n, 3) from (az, el) inside `window`
    (x0, x1, y0, y1) in normalised image coordinates (-1..1, y up), `margin` of air round it."""
    x0, x1, y0, y1 = window
    hw, hh = (x1 - x0) / 2, (y1 - y0) / 2
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    t0 = 18.0 / lens                      # tan(half fov) for a 36 mm square sensor
    tx, ty = t0 * hw / margin, t0 * hh / margin
    d, r, u = view_basis(az, el)
    target = (points.min(0) + points.max(0)) / 2
    dist = 0.0
    for _ in range(5):
        c = points - target
        cd, cr, cu = c @ d, c @ r, c @ u
        dist = float(max((cd + np.abs(cr) / tx).max(), (cd + np.abs(cu) / ty).max()))
        depth = np.maximum(dist - cd, 1e-6)
        x, y = cr / depth, cu / depth
        target = target + r * (x.max() + x.min()) / 2 * dist + u * (y.max() + y.min()) / 2 * dist
    c = points - target
    cd, cr, cu = c @ d, c @ r, c @ u
    dist = float(max((cd + np.abs(cr) / tx).max(), (cd + np.abs(cu) / ty).max()))
    # move the centred framing into the window: shift the camera sideways in its own plane
    target = target - r * cx * t0 * dist - u * cy * t0 * dist
    return target, dist


def projected_aspect(points, az, el) -> float:
    """Width / height of the points' silhouette box seen from (az, el)."""
    d, r, u = view_basis(az, el)
    c = points - points.mean(0)
    return float(np.ptp(c @ r) / max(np.ptp(c @ u), 1e-6))


def shape_of(points: np.ndarray, front: float) -> dict:
    """How tall and how long (front to back) the model is: `tall` 0 for a cassette lying down,
    1 for anything as tall as it is deep; `long` > 1.5 for a ferret seen nose-on."""
    ext = points.max(0) - points.min(0)
    a = math.radians(front)
    fwd = np.array([-math.sin(a), 0.0, math.cos(a)])       # front-to-back in the model frame
    side = np.array([math.cos(a), 0.0, math.sin(a)])
    c = points - points.mean(0)
    depth, width = float(np.ptp(c @ fwd)), float(np.ptp(c @ side))
    foot = math.sqrt(max(1.0, ext[0]) * max(1.0, ext[2]))
    tall = float(np.clip((ext[1] / foot - 0.25) / (0.8 - 0.25), 0, 1))
    ratio = depth / max(width, 1.0)
    # azimuths (relative to the front) that look along a long model: foreshortened, avoided
    end_on = [0.0, 180.0] if ratio > 1.4 else ([90.0, -90.0] if ratio < 1 / 1.4 else [])
    return {"tall": tall, "long": ratio, "end_on": end_on, "extent": ext.tolist()}


def avoid_end_on(az: float, shape: dict, margin: float = 46.0) -> float:
    """Turn `az` (relative to the front) away from any end-on view by at least `margin`."""
    for e in shape.get("end_on", []):
        d = (az - e + 180.0) % 360.0 - 180.0
        if abs(d) < margin:
            az = e + (margin if d >= 0 else -margin)
    return az


# ---------------------------------------------------------------------------- segments
def plan_segments(model, *, booklet: bool, beat: int = BEAT, variants=(), fps: int = FPS,
                  cfg: dict | None = None) -> list[dict]:
    """Beat-aligned segments in play order: [{name, start, end, kind, beats}]."""
    cfg = video_config(model) if cfg is None else cfg
    beats = dict(BEATS)
    for k, v in (cfg.get("seconds") or {}).items():          # older configs: seconds
        beats[k] = max(1, round(float(v) * fps / beat))
    beats.update({k: int(v) for k, v in (cfg.get("beats") or {}).items()})
    has = {
        "open": True, "title": True, "palette": True, "build": True, "scan": True,
        "outro": True,
        "mechanism": model.pose is not None and bool(model.groups),
        "lights": bool(model.lights) or bool(model.glow_tags),
        "lift": bool(cfg.get("lift")),
        "colourways": len(variants) > 0,
        "booklet": bool(booklet),
    }
    skip = set(cfg.get("skip", ()))
    beats["colourways"] = beats.get("colourways", beats["colourway"] * (1 + len(variants)))
    out, f = [], 0
    for n in ORDER:
        if not has[n] or n in skip:
            continue
        k = int(beats[n]) * beat
        out.append({"name": n, "start": f, "end": f + k, "kind": KIND.get(n, "scene"),
                    "beats": int(beats[n])})
        f += k
    return out


# ---------------------------------------------------------------------------- build plan
def _stem(caption: str) -> str:
    """'Layer 3 (2/4)' -> 'Layer'; 'Base disc: bottom layer' -> 'Base disc'."""
    s = re.split(r"[:;,.(]", caption or "", maxsplit=1)[0]
    s = re.sub(r"\b\d+(\s*(of|/)\s*\d+)?\b", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:1].upper() + s[1:] if s else ""


def build_order(model, placed, cfg) -> tuple[list[int], np.ndarray]:
    """Video order of the parts (instruction order, bottom-up and sweeping round within a step)
    and each part's booklet step (1-based, running maximum along the video order)."""
    order = {k: i for i, k in enumerate(model.instruction_order())}
    first = cfg.get("build_first")
    pos = np.array([p.M[:3, 3] for p in placed])
    cx, cz = (pos[:, 0].min() + pos[:, 0].max()) / 2, (pos[:, 2].min() + pos[:, 2].max()) / 2
    front = float(model.meta.get("azimuth_offset", 0.0))

    def key(p):
        x, y, z = p.M[:3, 3]
        ang = (math.degrees(math.atan2(x - cx, -(z - cz))) - front + 90.0) % 360.0
        phase = 0 if (first and first in p.tags) else 1
        return (phase, p.build_order, order.get((p.owner, p.local_step), p.build_order),
                -round(y / 8.0), round(ang, 1), math.hypot(x - cx, z - cz))

    seq = sorted(range(len(placed)), key=lambda i: key(placed[i]))
    step = np.zeros(len(placed), int)
    run = 0
    for i in seq:
        p = placed[i]
        run = max(run, order.get((p.owner, p.local_step), p.build_order) + 1)
        step[i] = run
    return seq, step


def build_sections(model, placed, seq, step, cfg, max_sections: int = MAX_SECTIONS) -> list[dict]:
    """Sections of the build in video order: [{title, parts: [instances in video order],
    first_step, last_step}]. From config (`sections = [[step, title], ...]`) or automatic:
    the top-level sub-assemblies (by title) and the main model's step captions, merged down to
    at most `max_sections`."""
    conf = cfg.get("sections")
    keys = []
    marks = []
    if conf:
        # a marker is a booklet step number, or the start of a step's caption (the first step
        # whose caption starts with it): captions survive renumbering
        caps = [model.submodels[sub].captions[k] if k < len(model.submodels[sub].captions) else ""
                for sub, k in model.instruction_order()]
        for m in conf:
            at, title = (m[0], m[1]) if isinstance(m, (list, tuple)) else (m.get("step", m.get("caption")), m["title"])
            if isinstance(at, str):
                hit = next((i + 1 for i, c in enumerate(caps) if c.lower().startswith(at.lower())), None)
                if hit is None:
                    continue
                at = hit
            marks.append((int(at), str(title)))
        marks.sort()
    if marks:
        for i in seq:
            t = marks[0][1]
            for s, title in marks:
                if step[i] >= s:
                    t = title
            keys.append(t)
    else:
        main = model.main
        for i in seq:
            p = placed[i]
            if len(p.path) > 1:
                sub = model.submodels.get(p.path[1])
                keys.append(sub.title if sub else p.path[1])
            else:
                cap = main.captions[p.local_step] if p.local_step < len(main.captions) else ""
                keys.append(_stem(cap) or main.title)
    runs: list[dict] = []
    for i, k in zip(seq, keys):
        if runs and runs[-1]["title"] == k:
            runs[-1]["parts"].append(i)
        else:
            runs.append({"title": k, "parts": [i]})
    if not marks:
        n = len(seq)
        while len(runs) > 1 and (len(runs) > max_sections or
                                 min(len(r["parts"]) for r in runs) < 0.03 * n):
            j = min(range(len(runs)), key=lambda k: len(runs[k]["parts"]))
            if j == 0:
                nb = 1
            elif j == len(runs) - 1:
                nb = j - 1
            else:
                nb = j - 1 if len(runs[j - 1]["parts"]) <= len(runs[j + 1]["parts"]) else j + 1
            a, b = sorted((j, nb))
            big = runs[a] if len(runs[a]["parts"]) >= len(runs[b]["parts"]) else runs[b]
            runs[a:b + 1] = [{"title": big["title"], "parts": runs[a]["parts"] + runs[b]["parts"]}]
            # neighbours that now share a title join up
            merged = []
            for r in runs:
                if merged and merged[-1]["title"] == r["title"]:
                    merged[-1]["parts"] += r["parts"]
                else:
                    merged.append(r)
            runs = merged
    for r in runs:
        r["first_step"] = int(step[r["parts"][0]])
        r["last_step"] = int(step[r["parts"][-1]])
    return runs


def speed(tau: np.ndarray, first: bool, last: bool) -> np.ndarray:
    """Relative build speed through a section (tau 0..1): every section eases in after its
    wipe; the first starts slower (single bricks you can follow); the last slows for the final
    pieces."""
    v = 0.35 + 0.65 * smootherstep(tau / 0.18)
    if first:
        v = 0.08 + 0.92 * smootherstep(tau / 0.3)
    if last:
        v = v * (1 - 0.75 * smootherstep((tau - 0.8) / 0.2))
    return v


def build_schedule(model, placed, seg, cfg, beat: int = BEAT):
    """Appear frame (float) of each part, video order, booklet step, the sections with their
    frame ranges, and the frame the last part lands. Sections get time by parts ** 0.6 (small
    ones stay readable), at least two beats each, and start on a beat."""
    seq, step = build_order(model, placed, cfg)
    secs = build_sections(model, placed, seq, step, cfg)
    a, b = seg["start"], seg["end"]
    lead = 4
    land_last = b - 2 * beat                      # the last piece lands on a beat...
    t0, t1 = a + lead, land_last - DROP_FRAMES    # ...so it appears DROP_FRAMES before
    w = np.array([len(s["parts"]) ** 0.6 for s in secs])
    span = t1 - t0
    dur = w / w.sum() * span
    floor = min(2 * beat, span / len(secs))
    for _ in range(4):
        low = dur < floor
        if not low.any():
            break
        dur[low] = floor
        rest = ~low
        dur[rest] *= (span - floor * low.sum()) / max(dur[rest].sum(), 1e-9)
    edges = np.concatenate([[t0], t0 + np.cumsum(dur)])
    for k in range(1, len(secs)):                 # section starts on beats (not before t0)
        e = a + round((edges[k] - a) / beat) * beat
        edges[k] = float(np.clip(e, edges[k - 1] + 6, t1 - 6 * (len(secs) - k)))
    appear = np.zeros(len(placed))
    for k, s in enumerate(secs):
        idx = s["parts"]
        s0, s1 = edges[k] + (lead if k else 0), edges[k + 1]
        if k == len(secs) - 1:
            s1 = t1
        # step weights: a step's parts share its slot, plus a little breath between steps
        st = np.array([step[i] for i in idx])
        brk = np.concatenate([[True], st[1:] != st[:-1]])
        u = np.cumsum(np.where(brk, 1.5, 0.0) + 1.0)
        if len(u) > 1:
            u = (u - u[0]) / (u[-1] - u[0])
        else:                                     # one part: the final piece lands on the beat
            u = np.array([1.0 if k == len(secs) - 1 else 0.3])
        tau = np.linspace(0, 1, 256)
        v = speed(tau, k == 0, k == len(secs) - 1)
        prog = np.concatenate([[0.0], np.cumsum((v[1:] + v[:-1]) / 2)])
        prog /= prog[-1]
        times = np.interp(u, prog, tau)
        for j, i in enumerate(idx):
            appear[i] = s0 + (s1 - s0) * times[j]
        s["start"] = int(round(edges[k])) if k else a
        s["end"] = int(round(edges[k + 1])) if k < len(secs) - 1 else b
    return appear, seq, step, secs, land_last


# ---------------------------------------------------------------------------- part selectors
def part_matches(p, sel) -> bool:
    """Does a placed part match a selector {tag (glob), part (number or list), color}?"""
    if "tag" in sel and not any(fnmatch.fnmatchcase(t, sel["tag"]) for t in p.tags):
        return False
    if "part" in sel:
        want = sel["part"] if isinstance(sel["part"], list) else [sel["part"]]
        if p.part.removesuffix(".dat") not in [str(w).removesuffix(".dat") for w in want]:
            return False
    if "color" in sel and p.color.name != sel["color"]:
        return False
    return any(k in sel for k in ("tag", "part", "color"))


def part_instances(placed, sel) -> list[list[int]]:
    """Matching parts, split into anchors: one per distinct tag value matched by a glob
    (fang_0, fang_1, ...), one per part for part/colour selectors, else one anchor."""
    hit = [p for p in placed if part_matches(p, sel)]
    if not hit:
        return []
    if "tag" in sel and any(ch in sel["tag"] for ch in "*?["):
        groups: OrderedDict = OrderedDict()
        for p in hit:
            key = next(t for t in p.tags if fnmatch.fnmatchcase(t, sel["tag"]))
            groups.setdefault(key, []).append(p.index)
        return list(groups.values())
    if "tag" not in sel and "part" in sel:
        return [[p.index] for p in hit]              # each part its own anchor (hinges x 2)
    return [[p.index for p in hit]]


def default_callouts(model) -> list[dict]:
    """One callout per moving group (numbered groups like fang_0..3 share one)."""
    out, seen = [], set()
    for g, tag in model.groups.items():
        stem = tag.rstrip("0123456789").rstrip("_")
        if stem != tag:
            if stem in seen:
                continue
            seen.add(stem)
            out.append({"tag": stem + "_*", "label": stem.replace("_", " ").capitalize()})
        else:
            out.append({"tag": tag, "label": tag.replace("_", " ").capitalize()})
    return out


# ---------------------------------------------------------------------------- mechanism
def rest_parameter(model) -> float | None:
    """The pose parameter at which every group is back where it was built (identity), if any."""
    def err(t):
        P = model.pose(float(t)) or {}
        e = 0.0
        for M in P.values():
            M = np.asarray(M, float)
            e = max(e, float(np.abs(M[:3, :3] - np.eye(3)).max()),
                    float(np.abs(M[:3, 3]).max()) / 100.0)   # 1 LDU off counts as 0.01
        return e
    ts = np.linspace(0, 1, 101)
    k = int(np.argmin([err(t) for t in ts]))
    lo, hi = ts[max(0, k - 1)], ts[min(len(ts) - 1, k + 1)]
    for _ in range(40):
        m1, m2 = lo + (hi - lo) / 3, hi - (hi - lo) / 3
        if err(m1) < err(m2):
            hi = m2
        else:
            lo = m1
    t = float((lo + hi) / 2)
    return t if err(t) < 1e-3 else None


def mech_curve(n: int, rest: float = 0.0) -> np.ndarray:
    """Pose parameter per frame: rest, ease to 0, open to 1, hold, back to rest."""
    k = np.arange(n) / max(1, n - 1)
    keys = [(0.0, rest), (0.1, rest), (0.28, 0.0), (0.6, 1.0), (0.7, 1.0), (0.94, rest),
            (1.0, rest)]
    if rest < 1e-3:                               # already at 0: open sooner, hold longer
        keys = [(0.0, 0.0), (0.12, 0.0), (0.48, 1.0), (0.64, 1.0), (0.93, 0.0), (1.0, 0.0)]
    u = np.zeros(n)
    for (ka, ua), (kb, ub) in zip(keys, keys[1:]):
        m = (k >= ka) & (k <= kb)
        u[m] = ua + (ub - ua) * smootherstep((k[m] - ka) / max(kb - ka, 1e-9))
    return np.clip(u, 0.0, 1.0)


def power_on_frame(seg: dict, beat: int) -> int:
    """The lights segment: lights out for two beats, then on."""
    n = seg["end"] - seg["start"]
    return seg["start"] + int(min(n - beat, 2 * beat))


def tap_curve(n: int, on: int) -> np.ndarray:
    """A quick press peaking as the lights switch on (frame `on` of n), then released."""
    k = np.arange(n, dtype=float)
    down = smootherstep((k - (on - 7)) / 6.0)
    up = smootherstep((k - (on + 4)) / 9.0)
    return np.clip(down - up, 0.0, 1.0)


def rotation_deg(M) -> float:
    R = np.asarray(M, float)[:3, :3]
    c = (np.trace(R) - 1) / 2
    return float(np.degrees(np.arccos(np.clip(c, -1, 1))))


def lift_matrix(k: int, n: int, height: float, pivot, fps: int) -> np.ndarray:
    """Rise, then a gentle hover: bob up and down and sway a degree or two."""
    t = k / fps
    rise = float(smootherstep((k - 0.08 * n) / (0.5 * n)))
    hover = float(smootherstep((k - 0.4 * n) / (0.35 * n)))
    bob = hover * 0.07 * height * math.sin(2 * math.pi * (t - 0.4 * n / fps) / 1.7)
    y = -(height * rise + bob)
    ax = hover * 1.6 * math.sin(2 * math.pi * t / 2.3)
    az = hover * 1.2 * math.sin(2 * math.pi * t / 1.9 + 1.0)
    from ..ldraw.matrix import rot, transform
    R = transform((0, 0, 0), rot(x=ax, z=az))
    p = np.asarray(pivot, float)
    return translate(0, y, 0) @ translate(*p) @ R @ translate(*(-p))


def colourway_plan(seg: dict, names: list[str], beat: int) -> dict:
    """When each colourway shows: holds with a wipe of WIPE_BEATS between them. Returns
    {"order": names, "wipes": [[start, end], ...], "frames": {name: [start, end)}}."""
    a, b = seg["start"], seg["end"]
    n = len(names)
    wl = WIPE_BEATS * beat
    hold = (b - a - (n - 1) * wl) / n
    wipes = []
    for k in range(n - 1):
        s = a + round(((k + 1) * hold + k * wl) / beat) * beat
        wipes.append([int(s), int(s + wl)])
    frames = {}
    for k, name in enumerate(names):
        frames[name] = [a if k == 0 else wipes[k - 1][0], b if k == n - 1 else wipes[k][1]]
    return {"order": list(names), "wipes": wipes, "frames": frames}


# ---------------------------------------------------------------------------- timeline
def build_timeline(engine, model, segments: list[dict], *, fps: int = FPS, beat: int = BEAT,
                   variants: dict | None = None, backdrop: str | None = None) -> dict:
    """`variants`: {name: {"title": str, "model": Model}} colourways with the same parts in
    the same places as `model` (see make_video)."""
    cfg = video_config(model)
    seg = {s["name"]: s for s in segments}
    scene_segs = [s for s in segments if s["kind"] == "scene"]
    total = segments[-1]["end"]
    front = float(model.meta.get("azimuth_offset", 0.0))

    placed = model.flatten()
    glow_or_lights = bool(model.lights) or bool(model.glow_tags)
    scene = model_scene(engine, model, lights_on=glow_or_lights, placed=placed)
    scene["lights"] = []                      # LEDs are parented to their parts in Blender
    if backdrop:                              # the theme's studio: backdrop and floor colour
        scene["backdrop"] = backdrop
        scene["ground_color"] = backdrop
    C = corners(engine, placed)
    s0 = scene_segs[0]["start"] if scene_segs else 0
    s1 = scene_segs[-1]["end"] if scene_segs else 0
    nf = s1 - s0

    # -- build -------------------------------------------------------------------------------
    b = seg["build"]
    appear, seq, step, sections, land_last = build_schedule(model, placed, b, cfg, beat)
    drop = float(cfg.get("drop", DROP))
    dirs = insert_directions(model)
    assert len(dirs) == len(placed)
    offsets = [((d if d is not None else np.array([0.0, -1.0, 0.0])) * drop).tolist() for d in dirs]
    section_of = np.zeros(len(placed), int)
    for k, s in enumerate(sections):
        section_of[s["parts"]] = k

    # -- moving groups -----------------------------------------------------------------------
    group_names: list[str] = []
    inst_group = [-1] * len(placed)
    mech = seg.get("mechanism")
    pose_frames, u_frames, angles = [], [], {}
    moving = np.zeros(len(placed), bool)
    rest = None
    if mech:
        probe = model.pose(0.0) or {}
        for p in placed:
            g = model.group_of(p)
            if g is not None and g in probe:
                if g not in group_names:
                    group_names.append(g)
                inst_group[p.index] = group_names.index(g)
                moving[p.index] = True
        n = mech["end"] - mech["start"]
        rest = rest_parameter(model)
        u = mech_curve(n, rest if rest is not None else 0.0)
        ident = np.eye(4)
        for k in range(n):
            P = model.pose(float(u[k]))
            row = []
            for g in group_names:
                M = np.asarray(P.get(g, ident), float)
                if rest is None:                   # no build pose on the sweep: blend to it
                    s = float(smootherstep(k / max(1, 0.12 * n)) *
                              smootherstep((n - 1 - k) / max(1, 0.06 * n)))
                    M = ident + (M - ident) * s
                row.append(M.reshape(-1).tolist())
            pose_frames.append(row)
        u_frames = u.tolist()
        L = seg.get("lights")
        if cfg.get("lights_tap") and L and rest is not None and L["start"] >= mech["end"]:
            # the lights switch on with a tap (the real behaviour): press as they come on
            rest_row = pose_frames[-1]
            pose_frames += [rest_row] * (L["start"] - mech["end"])
            on = power_on_frame(L, beat) - L["start"]
            for uu in tap_curve(L["end"] - L["start"], on):
                t = rest + (1.0 - rest) * float(uu)
                P = model.pose(t)
                pose_frames.append([np.asarray(P.get(g, ident), float).reshape(-1).tolist()
                                    for g in group_names])
        # how far each group turns from pose 0 to pose 1 (summed, so 270 degrees stays 270)
        ts = np.linspace(0, 1, 49)
        Ps = [model.pose(float(t)) for t in ts]
        for g in group_names:
            Ms = [np.asarray(P.get(g, ident), float) for P in Ps]
            angles[g] = round(sum(rotation_deg(np.linalg.inv(A) @ B)
                                  for A, B in zip(Ms, Ms[1:])), 1)

    # -- lift --------------------------------------------------------------------------------
    lift_cfg = cfg.get("lift") or {}
    lifted = np.zeros(len(placed), bool)
    lift_frames = []
    lift_seg = seg.get("lift")
    if lift_seg:
        ex = lift_cfg.get("exclude_tag")
        lifted = np.array([not (ex and ex in p.tags) for p in placed])
        H = float(lift_cfg.get("height", 80))
        pivot = (C[lifted].reshape(-1, 3).min(0) + C[lifted].reshape(-1, 3).max(0)) / 2
        for k in range(lift_seg["end"] - lift_seg["start"]):
            lift_frames.append(lift_matrix(k, lift_seg["end"] - lift_seg["start"], H, pivot, fps)
                               .reshape(-1).tolist())

    # -- lights ------------------------------------------------------------------------------
    dim, led = np.ones(nf), np.zeros(nf)
    power_on = None
    L = seg.get("lights")
    if L:
        a, n = L["start"] - s0, L["end"] - L["start"]
        k = np.arange(n)
        power_on = power_on_frame(L, beat)
        on = power_on - L["start"]
        d = 1 - (1 - DARK) * smootherstep(k / (1.2 * beat))
        d = np.where(k >= on, DARK + (LIGHTS_DIM - DARK) * smootherstep((k - on) / (1.5 * beat)), d)
        flick = np.zeros(n)
        for s_, e_ in ((0, 2), (4, 5), (7, n)):    # tink, tink, on
            flick[(k >= on + s_) & (k < on + e_)] = 1.0
        dim[a:a + n] = d
        led[a:a + n] = flick
        if lift_seg and lift_seg["start"] == L["end"]:
            a2, n2 = lift_seg["start"] - s0, lift_seg["end"] - lift_seg["start"]
            k2 = np.arange(n2)
            dim[a2:a2 + n2] = LIGHTS_DIM + (LIFT_DIM - LIGHTS_DIM) * smootherstep(k2 / (0.5 * n2))
            led[a2:a2 + n2] = 1.0
    leds = []
    for light in model.lights:
        found = model.find(light["part"], placed)
        if found:
            leds.append({"instance": found[0].index, "color": light["color"],
                         "power": float(light["power"]), "name": light.get("name", ""),
                         "offset": [float(v) for v in light.get("offset", (0, 0, 0))],
                         "pos": model.light_position(light, placed).tolist()})

    # -- colourways --------------------------------------------------------------------------
    var_out, cw = {}, None
    cw_seg = seg.get("colourways")
    if cw_seg and variants:
        from ..render.scene import _colors
        default = model.variant or "default"
        names = [default] + [v for v in variants if v != default]
        cw = colourway_plan(cw_seg, names, beat)
        for name in names[1:]:
            vplaced = variants[name]["model"].flatten()
            var_out[name] = {"title": variants[name]["title"],
                             "instance_colors": [p.color.ldraw for p in vplaced],
                             "names": {str(p.color.ldraw): [p.color.name, p.color.rgb]
                                       for p in vplaced},
                             "colors": _colors(engine, vplaced),
                             "frames": cw["frames"][name]}

    # -- camera ------------------------------------------------------------------------------
    shape = shape_of(C.reshape(-1, 3), front)
    cam, shots = plan_camera(model, segments, seg, front, shape, C, appear, seq, sections,
                             moving, group_names, inst_group, pose_frames, lifted, lift_frames,
                             placed, fps, beat, s0, s1, engine)

    return {
        "fps": fps, "beat": beat, "frames": total, "segments": segments, "scene": scene,
        "scene_range": [s0, s1],
        "model": {"name": model.name, "slug": model.slug, "variant": model.variant,
                  "parts": len(placed), "pieces": bom_pieces(engine, model, placed),
                  "steps": len(model.instruction_order()), "shape": shape},
        "build": {"appear": appear.tolist(), "drop": DROP_FRAMES, "offset": offsets,
                  "order": seq, "step": step.tolist(), "section": section_of.tolist(),
                  "land_last": land_last,
                  "sections": [{k: v for k, v in s.items() if k != "parts"} |
                               {"parts": len(s["parts"])} for s in sections]},
        "camera": cam, "shots": shots,
        "groups": {"names": group_names, "instance": inst_group,
                   "start": mech["start"] if mech else 0, "frames": pose_frames, "after": []},
        "mechanism": {"u": u_frames, "rest": rest, "angles": angles},
        "lift": {"instance": lifted.tolist(), "start": lift_seg["start"] if lift_seg else 0,
                 "frames": lift_frames},
        "lights": {"leds": leds, "dim": dim.tolist(), "led": led.tolist(), "glow": led.tolist(),
                   "start": s0, "power_on": power_on},
        "variants": var_out, "colourways": cw,
    }


# ---------------------------------------------------------------------------- camera plan
BUILD_ANGLES = [(-50, 30), (38, 25), (-18, 40), (62, 21), (-72, 28), (22, 34)]
LONG_ANGLES = [(-58, 27), (62, 24), (-112, 31), (104, 22), (-40, 36), (80, 30)]


def _ang_dist(a, b):
    return abs((a - b + 180.0) % 360.0 - 180.0)


def section_angles(sections, C, shape, front: float = 0.0) -> list[tuple[float, float]]:
    """(az, el) relative to the front for each build section: a cycle of pleasing angles,
    turned towards a section whose new parts sit off to one side (a head, a tail)."""
    presets = LONG_ANGLES if shape["long"] > 1.5 else BUILD_ANGLES
    lift = 16.0 * (1 - shape["tall"])
    out, prev, sofar = [], None, []
    for k, s in enumerate(sections):
        sofar = sofar + s["parts"]
        pts = C[sofar].reshape(-1, 3)
        new = C[s["parts"]].reshape(-1, 3)
        off = new.mean(0) - pts.mean(0)
        ext = np.ptp(pts[:, [0, 2]], axis=0).max()
        cand = presets[k % len(presets)]
        if cand == prev:
            cand = presets[(k + 1) % len(presets)]
        if k and np.hypot(off[0], off[2]) > 0.18 * ext:
            want = math.degrees(math.atan2(off[0], -off[2])) - front
            opts = [p for p in presets if p != prev] or presets
            cand = min(opts, key=lambda p: _ang_dist(p[0], want))
        prev = cand
        out.append((cand[0], cand[1] + lift))
    return out


def plan_camera(model, segments, seg, front, shape, C, appear, seq, sections, moving,
                group_names, inst_group, pose_frames, lifted, lift_frames, placed, fps, beat,
                s0, s1, engine):
    """Per-frame camera for every scene segment. Every segment (and every build section) is a
    shot of its own: the cuts between them hide under the graphics' wipes."""
    nf = s1 - s0
    allpts = C.reshape(-1, 3)
    tall, long_ = shape["tall"], shape["long"] > 1.5
    az = np.zeros(nf)
    el = np.zeros(nf)
    target = np.zeros((nf, 3))
    dist = np.zeros(nf)
    lens = np.full(nf, LENS)
    shots = {}

    def idx(s):
        return np.arange(s["start"] - s0, s["end"] - s0)

    def orbit(s, az0, az1, el0, el1, ease=0.5):
        az0, az1 = avoid_end_on(az0, shape), avoid_end_on(az1, shape)
        i = idx(s)
        k = np.linspace(0, 1, len(i))
        m = (1 - ease) * k + ease * smootherstep(k)
        az[i] = front + az0 + (az1 - az0) * m
        el[i] = el0 + (el1 - el0) * m
        return i

    def still(i, pts, window, margin=MARGIN, push=0.0):
        fits = [fit(pts, az[j], el[j], window=window, margin=margin) for j in i[::4]]
        d_goal = max(f[1] for f in fits)
        t_goal = np.mean([f[0] for f in fits], axis=0)
        target[i] = t_goal
        dist[i] = d_goal * (1 - push * smootherstep(np.linspace(0, 1, len(i))))

    # -- build: one orbit per section, framing what's there 1.5 s ahead ----------------------
    angles = section_angles(sections, C, shape, front)
    sec_parts = [s_["parts"] for s_ in sections]
    order_appear = appear[seq]
    for k, sec in enumerate(sections):
        s = {"start": sec["start"], "end": sec["end"]}
        a0, e0 = angles[k]
        dur = (s["end"] - s["start"]) / fps
        sweep = min(14.0 + 4.0 * dur, 34.0)
        a0 = avoid_end_on(a0, shape)
        if shape["end_on"]:     # long models turn towards broadside, never towards end-on
            broad = shape["end_on"][0] + 90.0
            d = (a0 - broad + 90.0) % 180.0 - 90.0          # signed distance to broadside
            sweep *= -1 if d > 0 else 1
        else:
            sweep *= 1 if k % 2 == 0 else -1
        i = orbit(s, a0, a0 + sweep, e0, e0 - 5.0)
        full = np.array([fit(allpts, az[j], el[j])[1] for j in i[::5]])
        full_d = np.interp(np.arange(len(i)), np.arange(0, len(i), 5), full)
        raw_t, raw_d = np.zeros((len(i), 3)), np.zeros(len(i))
        # a section at one end of a long model (a head, a tail) is framed with what's near it
        new_c = C[sec_parts[k]].reshape(-1, 3)
        focus = new_c.mean(0)
        reach = max(1.3 * float(np.ptp(new_c, axis=0).max()), 0.55 * float(np.ptp(allpts, axis=0).max()))
        near_all = np.linalg.norm(C.mean(1) - focus, axis=1) <= reach
        for n_, j in enumerate(i):
            f = j + s0
            n = max(int(np.searchsorted(order_appear, f + 45, side="right")), 1)
            sel = np.array(seq[:n])
            if k > 0:
                sel = sel[near_all[sel]] if near_all[sel].any() else sel
            pts = C[sel].reshape(-1, 3)
            raw_t[n_], raw_d[n_] = fit(pts, az[j], el[j])
            raw_d[n_] = max(raw_d[n_], 0.45 * full_d[n_])
        win = 40
        fwd = np.array([raw_d[m:m + win].max() for m in range(len(i))])
        target[i] = _gauss(raw_t, 14)
        dist[i] = np.maximum(_gauss(fwd, 10), raw_d)
    shots["build"] = {"angles": [list(a) for a in angles]}

    # -- scan: the finished model to one side, the checks panel on the other -----------------
    if "scan" in seg:
        s = seg["scan"]
        a0, a1 = ((48.0, 78.0) if long_ else (-42.0, -12.0))
        e0 = 16.0 + 16.0 * (1 - tall)
        mid = front + (a0 + a1) / 2
        side = projected_aspect(allpts, mid, e0) < 1.05
        window = (-0.96, 0.16, -0.8, 0.84) if side else (-0.9, 0.9, -0.04, 0.9)
        i = orbit(s, a0, a1, e0, e0 - 3.0, ease=0.3)
        still(i, allpts, window, margin=1.08, push=0.04)
        shots["scan"] = {"layout": "side" if side else "bottom", "window": list(window)}

    # -- mechanism: close on the moving parts in context ---------------------------------------
    if "mechanism" in seg:
        s = seg["mechanism"]
        mp_list = [C[moving].reshape(-1, 3)] if moving.any() else [allpts]
        gi = np.array(inst_group)
        for row in pose_frames[::max(1, len(pose_frames) // 8)]:
            for g in range(len(group_names)):
                M = np.array(row[g]).reshape(4, 4)
                mp_list.append(apply(M, C[gi == g].reshape(-1, 3)))
        mp = np.concatenate(mp_list)
        ctr = allpts.mean(0)
        # the action: moving parts weighted by how far they travel (a door swinging counts,
        # a round reel spinning in place hardly does)
        # (per group: how much its bounding box changes - a door's does, a reel's hardly)
        gi_m = np.array(inst_group)
        cents, wts = [], []
        for g in range(len(group_names)):
            # the parts' real outlines (a round reel's box doesn't change as it spins)
            geo = [apply(placed[i].M, np.asarray(engine.geom.mesh(placed[i].part).edges,
                                                 float).reshape(-1, 3))
                   for i in np.nonzero(gi_m == g)[0]]
            geo = [q for q in geo if len(q)]
            pts_g = np.concatenate(geo)[::7] if geo else C[gi_m == g].reshape(-1, 3)
            if not len(pts_g):
                continue
            lo, hi = pts_g.min(0), pts_g.max(0)
            change = 0.0
            for row in pose_frames[::max(1, len(pose_frames) // 12)]:
                q = apply(np.array(row[g]).reshape(4, 4), pts_g)
                change = max(change, float(np.abs(q.min(0) - lo).max()),
                             float(np.abs(q.max(0) - hi).max()))
            cents.append((lo + hi) / 2)
            wts.append(change + 1e-3)
        action = (np.array(cents) * np.array(wts)[:, None]).sum(0) / sum(wts) if wts else ctr
        off = action - ctr
        ext = np.ptp(allpts[:, [0, 2]], axis=0).max()
        half = 0.5 * float(min(np.ptp(allpts[:, 0]), np.ptp(allpts[:, 2])))
        edge = float(np.clip(np.hypot(off[0], off[2]) / max(half, 1.0), 0.0, 1.0))
        if np.hypot(off[0], off[2]) > 0.18 * ext:          # a head or a door at one side: face it
            a0 = _near(math.degrees(math.atan2(off[0], -off[2])) - front, 0.0)
            a0 = float(np.clip(a0, -60, 60)) + (-28.0 if a0 >= 0 else 28.0)
        else:
            a0 = 40.0
        e0 = 24.0 + (3.0 - 24.0) * tall + 10.0 * (1 - tall) - 20.0 * edge * (1 - tall)
        i = orbit(s, a0, a0 + 12.0, e0, e0 + 1.0)
        # context: tall models show everything above the moving parts' lowest point; others
        # what's near the moving parts
        if tall > 0.5 and not long_:
            low = mp[:, 1].max()
            ctx = C[C.mean(1)[:, 1] <= low].reshape(-1, 3)
        else:
            r = 0.6 * np.ptp(mp, axis=0).max()
            near = np.linalg.norm(C.mean(1) - mp.mean(0), axis=1) < r
            ctx = C[near].reshape(-1, 3)
        pts = np.concatenate([mp, ctx])
        # what the callouts point at, and the groups that visibly move, frame the shot
        focus_idx = set()
        for sel in (video_config(model).get("callouts") or default_callouts(model)):
            for inst in part_instances(placed, sel):
                focus_idx.update(inst)
        big = max(wts) if wts else 0.0
        for g, w_ in enumerate(wts):
            if w_ > 0.3 * big:
                focus_idx.update(np.nonzero(gi_m == g)[0].tolist())
        if focus_idx:
            fi = np.array(sorted(focus_idx))
            fp = [C[fi].reshape(-1, 3)]
            for row in pose_frames[::max(1, len(pose_frames) // 8)]:
                for g in range(len(group_names)):
                    sel_g = fi[gi_m[fi] == g]
                    if len(sel_g):
                        fp.append(apply(np.array(row[g]).reshape(4, 4), C[sel_g].reshape(-1, 3)))
            pts = np.concatenate(fp)
            mp = pts
        window = (-0.7, 0.7, -0.66, 0.76)
        k = i[len(i) // 2]
        tm, dm = fit(pts, az[k], el[k], margin=1.15, window=window)
        tf, df = fit(allpts, az[k], el[k], margin=1.0, window=window)
        if dm > 0.8 * df:                     # hardly a close-up: show the whole model
            tm, dm = tf, df
        else:                                 # a close-up: the moving parts in the middle
            tc, dc = fit(mp, az[k], el[k], margin=1.9, window=window)
            tm, dm = tc, max(dc, 0.8 * dm)
        target[i] = tm
        dist[i] = dm * (1 - 0.05 * smootherstep(np.linspace(0, 1, len(i))))
        shots["mechanism"] = {"window": list(window)}

    # -- lights --------------------------------------------------------------------------------
    if "lights" in seg:
        s = seg["lights"]
        i = orbit(s, 14.0, 6.0, 14.0 + 10 * (1 - tall), 11.0 + 10 * (1 - tall))
        glow = [p.index for p in placed if any(t in p.tags for t in model.glow_tags)]
        k = i[len(i) // 2]
        tf, df = fit(allpts, az[k], el[k])
        gc = C[glow].reshape(-1, 3).mean(0) if glow else tf
        target[i] = tf + (gc - tf) * 0.2
        dist[i] = df * (1.0 - 0.08 * smootherstep(np.linspace(0, 1, len(i))))
        shots["lights"] = {}

    # -- lift ----------------------------------------------------------------------------------
    if "lift" in seg:
        s = seg["lift"]
        i = orbit(s, -2.0, -12.0, 8.0 + 12 * (1 - tall), 6.0 + 12 * (1 - tall))
        H = np.array([np.array(m).reshape(4, 4)[:3, 3] for m in lift_frames])
        top = C.copy()
        top[lifted] = top[lifted] + np.array([0, -max(0.0, -H[:, 1].min()), 0])
        still(i, top.reshape(-1, 3), (-1, 1, -1, 1))
        shots["lift"] = {}

    # -- colourways: a slow push; room at the bottom for the swatches -------------------------
    if "colourways" in seg:
        s = seg["colourways"]
        a0, a1 = ((-62.0, -38.0) if long_ else (28.0, 50.0))
        e0 = 14.0 + 10.0 * (1 - tall)
        i = orbit(s, a0, a1, e0, e0 - 3.0, ease=0.2)
        window = (-0.9, 0.9, -0.34, 0.9)
        still(i, allpts, window, margin=1.1, push=0.06)
        shots["colourways"] = {"window": list(window)}

    pos = np.zeros((nf, 3))
    for j in range(nf):
        d, _, _ = view_basis(az[j], el[j])
        pos[j] = target[j] + d * dist[j]
    return ({"start": s0, "pos": np.round(pos, 3).tolist(),
             "target": np.round(target, 3).tolist(), "lens": lens.tolist(),
             "az": np.round(az, 3).tolist(), "el": np.round(el, 3).tolist()}, shots)
