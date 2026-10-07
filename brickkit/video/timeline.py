"""Build-video timeline (engine side; no Blender needed).

The video is an edit of beat-aligned segments (see `plan_segments`). Graphics-only segments
(open, title, palette, outro) are drawn by the compositor; the booklet flip has its own Blender
scene; the model-scene segments are planned here, frame by frame, for render/blender_animate.py:

    build       the model grows up from the table: parts by the height of their lowest point,
                outward from the centre, each waiting for something to stand on or connect
                to, dropping a short way into place (or, with build_order = "instructions",
                in instruction order); sections (height bands) are orbiting shots of their own,
                with speed ramps: each starts slow, speeds up, the last pieces slow down
    scan        slow orbit of the finished model, framed to one side for the checks panel
    mechanism   `model.pose`: build pose -> 0 -> 1 -> build pose, slow, close on the moving parts
    lights      the studio goes dark, then the LEDs and glowing parts switch on (lights/glow);
                with lights_tap the mechanism presses as they do, with lights_off a second
                tap switches them off again
    lift        everything but `exclude_tag` rises and hovers         (meta["video"]["lift"])
    colourways  slow push round the model; each colourway renders its own frames (variants)
    cold_open   (opt-in, first) the model performs in a scene of its own - "sunset_road": on a
                two-lane road into a low sun - looping meta["performance"] (else swinging
                model.pose) while it spins, in three shots; or "night_desk", a tap lamp on a
                desk at night, tapped on, off and on (motion "tap"), in two; then a hard cut to
                black for a beat (`cold_open_plan`; config [video.cold_open])
    coda        (opt-in, last) the last image, after the outro: the model far off in the dark
                sea and a giant squid rising out of the murk, going for it (`coda_plan`;
                config [video.coda])

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
    cold_open           (only with one) its own scene, motion, camera and rev curve: see
                        `cold_open_plan`
    coda                (only with one) the same fields for the coda, and its creature: see
                        `coda_plan`

Per-model tweaks go in `model.meta["video"]` or model.toml [video] (all optional), e.g.
    {"lift": {"exclude_tag": "stand", "height": 80}, "beats": {"build": 28}, "drop": 24,
     "build_order": "ground_up" | "instructions", "sections": [[1, "Base"], ["Layer 1 (", "Dome"]],
     "lights_tap": true, "lights_off": true}
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
ORDER = ("cold_open", "open", "title", "build", "scan", "mechanism", "lights", "lift",
         "colourways", "booklet", "companions", "outro", "coda")
KIND = {"open": "gfx", "title": "gfx", "outro": "gfx", "booklet": "booklet", "cold_open": "cold",
        "coda": "cold", "companions": "gfx"}
BEATS = {"open": 6, "title": 8, "build": 36, "scan": 12, "mechanism": 12, "lights": 8,
         "lift": 6, "colourway": 4, "booklet": 12, "outro": 8, "companion": 10}
LIGHTS_OFF_BEATS = 2      # extra lights beats when the lights also switch off again
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
    co = cold_open_config(model, cfg)
    if co is not None and "cold_open" not in (cfg.get("beats") or {}):
        # the performance, then a beat of black
        beats["cold_open"] = max(2, round(co["seconds"] * fps / beat)) + COLD_BLACK_BEATS
    cc = coda_config(model, cfg)
    if cc is not None and "coda" not in (cfg.get("beats") or {}):
        beats["coda"] = max(2, round(cc["seconds"] * fps / beat))
    has = {
        "cold_open": co is not None, "coda": cc is not None,
        "open": True, "title": True, "build": True, "scan": True, "outro": True,
        "mechanism": model.pose is not None and bool(model.groups),
        "lights": bool(model.lights) or bool(model.glow_tags),
        "lift": bool(cfg.get("lift")),
        "colourways": len(variants) > 0,
        "booklet": bool(booklet),
        "companions": bool(cfg.get("companions")),    # [[companions]] with video = true
    }
    skip = set(cfg.get("skip", ()))
    if cfg.get("lights_off") and "lights" not in (cfg.get("beats") or {}):
        beats["lights"] += LIGHTS_OFF_BEATS
    beats["colourways"] = beats.get("colourways", beats["colourway"] * (1 + len(variants)))
    beats["companions"] = beats.get("companions", beats["companion"] * len(cfg.get("companions") or []))
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


LAYER = 8.0              # LDU: parts whose lowest points are within a plate share a layer


def ground_up_order(engine, model, placed, C) -> list[int]:
    """Parts in the order they'd go on growing the model up from the table: by the height of
    their lowest point (a plate per layer), outward from the centre within a layer. Support
    aware: a part waits until it stands on the ground or something it connects to is there
    (so a hanging fang follows its bearing); anything left unsupported goes lowest first."""
    import heapq
    n = len(placed)
    low = C[:, :, 1].max(1)                          # LDraw +Y is down: the lowest point
    ground = float(low.max())
    layer = np.round((ground - low) / LAYER)
    ctr = C.reshape(-1, 3).mean(0)
    mid = C.mean(1)
    radial = np.hypot(mid[:, 0] - ctr[0], mid[:, 2] - ctr[2])
    nbrs: list[set] = [set() for _ in range(n)]
    try:
        for c in engine.context(model).connections:
            nbrs[c.a].add(c.b)
            nbrs[c.b].add(c.a)
    except Exception:          # noqa: BLE001 - no connection data: plain height order
        pass
    key = [(float(layer[i]), round(float(radial[i]), 1), i) for i in range(n)]
    heap = [key[i] for i in range(n) if layer[i] <= 0.5]
    heapq.heapify(heap)
    queued = {k[2] for k in heap}
    rest = sorted(key)
    ri = 0
    order, done = [], np.zeros(n, bool)
    while len(order) < n:
        if not heap:                                 # nothing supported: the lowest left
            while done[rest[ri][2]]:
                ri += 1
            heapq.heappush(heap, rest[ri])
            queued.add(rest[ri][2])
        _, _, i = heapq.heappop(heap)
        if done[i]:
            continue
        done[i] = True
        order.append(i)
        for j in nbrs[i]:
            if not done[j] and j not in queued:
                heapq.heappush(heap, key[j])
                queued.add(j)
    return order


def height_bands(model, placed, seq, step, cfg, max_bands: int = 4) -> list[dict]:
    """Sections for a ground-up build: runs of the video order named after the section most
    of their parts belong to (sub-assemblies, captions or [video] sections), smoothed and
    merged to at most `max_bands`; one untitled section when they wouldn't tell apart."""
    inst_order, inst_step = build_order(model, placed, cfg)
    label = {}
    for sec in build_sections(model, placed, inst_order, inst_step, cfg):
        for i in sec["parts"]:
            label[i] = sec["title"]
    names = sorted(set(label.values()))
    n = len(seq)
    if len(names) < 2 or n < 8:
        runs = [{"title": "", "parts": list(seq)}]
    else:
        idx = {t: k for k, t in enumerate(names)}
        onehot = np.zeros((n + 1, len(names)))
        for k, i in enumerate(seq):
            onehot[k + 1, idx[label[i]]] = 1
        cum = onehot.cumsum(0)
        w = max(4, n // 8)
        maj = [names[int(np.argmax(cum[min(n, k + w)] - cum[max(0, k - w)]))] for k in range(n)]
        runs = []
        for k, i in enumerate(seq):
            if runs and runs[-1]["title"] == maj[k]:
                runs[-1]["parts"].append(i)
            else:
                runs.append({"title": maj[k], "parts": [i]})
        while len(runs) > 1 and (len(runs) > max_bands or
                                 min(len(r["parts"]) for r in runs) < n / 10):
            j = min(range(len(runs)), key=lambda k: len(runs[k]["parts"]))
            nb = 1 if j == 0 else j - 1 if j == len(runs) - 1 else (
                j - 1 if len(runs[j - 1]["parts"]) <= len(runs[j + 1]["parts"]) else j + 1)
            a, b = sorted((j, nb))
            big = runs[a] if len(runs[a]["parts"]) >= len(runs[b]["parts"]) else runs[b]
            runs[a:b + 1] = [{"title": big["title"], "parts": runs[a]["parts"] + runs[b]["parts"]}]
            merged = []
            for r in runs:
                if merged and merged[-1]["title"] == r["title"]:
                    merged[-1]["parts"] += r["parts"]
                else:
                    merged.append(r)
            runs = merged
        if len(runs) < 2:
            runs = [{"title": "", "parts": list(seq)}]
        for r in runs:                     # a name only where it's mostly true
            share = sum(label[i] == r["title"] for i in r["parts"]) / len(r["parts"])
            if share < 0.6:
                r["title"] = ""
    for r in runs:
        r["first_step"] = int(min(step[i] for i in r["parts"]))
        r["last_step"] = int(max(step[i] for i in r["parts"]))
    return runs


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


def ground_up(cfg) -> bool:
    """The build grows up from the table (default) or follows the instructions."""
    return str(cfg.get("build_order", "ground_up")) != "instructions"


def build_schedule(model, placed, seg, cfg, beat: int = BEAT, engine=None, C=None):
    """Appear frame (float) of each part, video order, booklet step, the sections with their
    frame ranges, and the frame the last part lands. Sections get time by parts ** 0.6 (small
    ones stay readable), at least two beats each, and start on a beat."""
    seq, step = build_order(model, placed, cfg)
    if ground_up(cfg) and engine is not None:
        seq = ground_up_order(engine, model, placed, C)
        secs = height_bands(model, placed, seq, step, cfg)
    else:
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


def power_off_frame(seg: dict, beat: int) -> int:
    """With lights_off: on for about five beats, then a tap switches them off."""
    return seg["end"] - int(3 * beat)


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


# ---------------------------------------------------------------------------- cold open
# [video.cold_open] (model.toml) over these; model.meta["performance_info"] holds the model's own
# facts (hide_tags, ground_y, pivot [x, z], cycle seconds, rev_tag)
COLD = {"scene": "sunset_road", "seconds": 7.0, "motion": "performance", "spin_turns": 1.5,
        "hide_tags": [], "cycle": 2.5, "sun_elevation": 2.4, "sun_azimuth": 0.0,
        "sun_size": 1.4, "letterbox": 0.09, "rev_tag": "saw"}
COLD_SCENES = ("sunset_road", "night_desk", "deep_sea")
COLD_MOTIONS = ("performance", "pose", "tap", "glide", "flythrough")
COLD_HIDE = {"deep_sea": ("stand",)}    # a set that hides a display stand by default
COLD_MOTION = {"night_desk": "tap", "deep_sea": "glide"}   # a set's motion unless one is given
# the set's look: [video.cold_open] keys handed to the set as they are (render/blender_cold_open.py
# LOOK and DESK_LOOK have the defaults and the units)
COLD_LOOK = ("exposure", "sky_strength", "sky_tint", "sun_strength", "sun_color", "sun_disc",
             "fill_strength", "haze", "dust", "moon_strength", "moon_color", "lamp_gain",
             "spill_strength", "spill_color")
COLD_BLACK_BEATS = 1          # the hard cut to black before the reel proper
COLD_CATCH = 0.45             # s: the engine catches (the pull-start before it)
COLD_START, COLD_RAMP = 0.55, 0.9   # s: the performance comes up to speed
# shots: (from, name, lens mm, camera height / figure height, camera azimuth deg (0: looking
# into the sun), feet and head as fractions of the picture's height (None: the wide shot, its
# head just under the sun's middle so the swing crosses it), dolly: how much closer it ends,
# exposure (EV, stopped down when looking into the sun)
COLD_SHOTS = ((0.0, "wide", 300.0, 0.3, 0.0, 0.18, None, 0.05, -2.2),
              (0.42, "low", 70.0, 0.2, -12.0, 0.14, 0.8, 0.04, -0.4),
              (0.72, "close", 38.0, 0.07, 24.0, 0.14, 0.9, 0.07, 0.0))
# night_desk: the same fields, the azimuth from the model's front (as view_basis), `from` None
# for the cut to the close shot: in the dark between the second and third taps (else halfway)
DESK_SHOTS = ((0.0, "room", 40.0, 1.25, -28.0, 0.2, 0.72, 0.14, 0.0),
              (None, "close", 75.0, 0.55, 14.0, -0.1, 0.8, 0.07, 0.0))
# motion "tap" (a tap lamp): the pose pressed (0 -> 1) and let go, the lights toggling on each
# press, push-on/push-off, starting dark. Taps at these beats from the start (on, off, on) unless
# [video.cold_open] taps = [seconds, ...]
TAP_BEATS = (2.0, 6.0, 8.0)
TAP_DOWN, TAP_HOLD, TAP_UP = 4, 2, 7    # frames: pressed in, held at the bottom (the click), let go
TAP_KICK = {"on": 0.05, "off": 0.025}   # the camera punches in on a tap: this much more lens
# motion "glide" (deep_sea): the whole model cruises forward GLIDE_LENGTHS of its own length
# over the performance, banking, pitching and bobbing gently, its performance loop (or pose)
# running; three shots (from, name, lens mm): a wide approach from below, a low tracking shot
# along its side, a close one of the bow passing the camera
GLIDE_LENGTHS = 1.6
GLIDE_SHOTS = ((0.0, "approach", 28.0), (0.38, "side", 40.0), (0.7, "bow", 20.0))

def cold_open_config(model, cfg) -> dict | None:
    """The cold open's settings ([video.cold_open] over the defaults), or None without one."""
    co = cfg.get("cold_open")
    if not co:
        return None
    out = dict(COLD)
    info = model.meta.get("performance_info") or {}
    for k, keys in (("cycle", ("cycle", "cycle_s")), ("rev_tag", ("rev_tag",))):
        for key in keys:
            if key in info:
                out[k] = info[key]
    out.update(co if isinstance(co, dict) else {})
    if "motion" not in (co if isinstance(co, dict) else {}):
        out["motion"] = COLD_MOTION.get(out["scene"], out["motion"])
    out["hide_tags"] = sorted(set(out.get("hide_tags") or []) | set(info.get("hide_tags") or [])
                              | set(COLD_HIDE.get(out["scene"], ())))
    if out["scene"] not in COLD_SCENES:
        raise SystemExit(f"unknown cold open scene {out['scene']!r}; choose from "
                         f"{', '.join(COLD_SCENES)}")
    if out["motion"] not in COLD_MOTIONS:
        raise SystemExit(f"cold open motion {out['motion']!r}: {', '.join(COLD_MOTIONS)}")
    if out["motion"] in ("tap", "glide", "flythrough") and \
            "spin_turns" not in (co if isinstance(co, dict) else {}):
        out["spin_turns"] = 0.0                   # a lamp stays put; a glide doesn't spin
    if "forward" in info and "forward" not in out:
        out["forward"] = info["forward"]
    return out


# motion "flythrough" (deep_sea): a glide, its shots two dramatic ones - under the bow, then
# wide from below and to the side, dark against the water - and one long take: along its side to
# a window, in through it (the hull parts in the camera's way hidden as it passes), through the
# room past what is there, out the far side and away into a dark sea. The room comes from the
# model: meta["flythrough"] (or [video.cold_open.flythrough]), points in its own frame (`origin`
# in the model's): enter, exit (where the camera passes through the hull), path (waypoints
# inside), look (what to look at from each), slow (how long to linger at each, 1 = the room's
# pace), interior {bounds [[lo], [hi]], tags} (what the room is; its tagged parts are never hidden)
FLY_LENGTHS = 1.3
FLY_SHOTS = ((0.0, "under", 20.0), (0.13, "silhouette", 32.0), (0.26, "flythrough", 22.0))
# the take's pieces (their shares of its time) and lenses: along the hull, to the window, the
# room, out through the far wall, back from it, away into the dark
FLY_PIECES = (("hull", 0.18, 24.0), ("push", 0.06, 20.0), ("room", 0.47, 18.0), ("out", 0.025, 20.0),
              ("back", 0.09, 24.0), ("away", 0.175, 30.0))
FLY_CLEAR = 0.018          # the camera's clearance: hull parts closer than this (x the model's
FLY_AHEAD = 0.022          # length), or this far ahead of it, are hidden while it passes
FLY_TURN = 0.0012          # a degree's turn takes as long as moving this much of the length


def flythrough_config(model, co) -> dict:
    """The model's flythrough (meta, the config's over it), its points in the model's frame."""
    f = dict(model.meta.get("flythrough") or {})
    f.update(co.get("flythrough") or {})
    if "enter" not in f or "exit" not in f:
        raise SystemExit("cold open motion flythrough: the model needs meta['flythrough'] (or "
                         "[video.cold_open.flythrough]) with enter, exit and the interior")
    o = np.asarray(f.get("origin", (0.0, 0.0, 0.0)), float)
    pts = lambda v: [np.asarray(p, float) + o for p in v]     # noqa: E731
    inner = f.get("interior") or {}
    b = np.asarray(inner.get("bounds", [f["enter"], f["exit"]]), float) + o
    path = pts(f.get("path") or [])
    look = pts(f.get("look") or [])
    return {"enter": np.asarray(f["enter"], float) + o, "exit": np.asarray(f["exit"], float) + o,
            "path": path, "look": look + [None] * (len(path) - len(look)),
            "slow": list(f.get("slow") or []) + [1.0] * len(path),
            "bounds": np.array([b.min(0), b.max(0)]), "tags": set(inner.get("tags") or [])}


def _spline(P, n=64):
    """A centripetal Catmull-Rom curve through the points P (k, 3): (samples (s, 3), the
    index of the segment each sample is on)."""
    P = np.asarray(P, float)
    Q = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out, seg = [], []
    for i in range(1, len(Q) - 2):
        p0, p1, p2, p3 = Q[i - 1:i + 3]
        t0 = 0.0
        t1 = t0 + max(np.linalg.norm(p1 - p0), 1e-6) ** 0.5
        t2 = t1 + max(np.linalg.norm(p2 - p1), 1e-6) ** 0.5
        t3 = t2 + max(np.linalg.norm(p3 - p2), 1e-6) ** 0.5
        for t in np.linspace(t1, t2, n, endpoint=False):
            a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
            a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
            a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
            b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
            b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
            out.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
            seg.append(i - 1)
    out.append(P[-1])
    seg.append(len(P) - 2)
    return np.array(out), np.array(seg)


def _turn(c, a, b, f: float, F, N, U):
    """The point seen from c a fraction f of the way from looking at a to looking at b: the
    view turning (yaw about U, the shorter way round, and pitch), its distance eased between."""
    da, db = a - c, b - c
    ra, rb = np.linalg.norm(da) + 1e-9, np.linalg.norm(db) + 1e-9
    ya, yb = math.atan2(da @ N, da @ F), math.atan2(db @ N, db @ F)
    pa, pb = math.asin(np.clip(da @ U / ra, -1, 1)), math.asin(np.clip(db @ U / rb, -1, 1))
    y = ya + ((yb - ya + math.pi) % (2 * math.pi) - math.pi) * f
    p = pa + (pb - pa) * f
    d = (F * math.cos(y) + N * math.sin(y)) * math.cos(p) + U * math.sin(p)
    return c + d * (ra + (rb - ra) * f)


def _box_distance(pts, C):
    """Distance from each of `pts` (p, 3) to each part's oriented box (corners C (n, 8, 3)):
    (n, p)."""
    o = C[:, 0]
    E = np.stack([C[:, 4] - o, C[:, 2] - o, C[:, 1] - o], 1)          # (n, 3, 3) its edges
    L2 = np.maximum((E ** 2).sum(-1), 1e-9)                              # (n, 3)
    q = pts[None, :, :] - o[:, None, :]                                  # (n, p, 3)
    a = np.clip(np.einsum("npk,nek->npe", q, E) / L2[:, None, :], 0.0, 1.0)
    near = o[:, None, :] + np.einsum("npe,nek->npk", a, E)
    return np.linalg.norm(pts[None, :, :] - near, axis=-1)


def flythrough_camera(m, fps, spins, path, F, U, N, ext, length, fly, C, keep):
    """The flythrough's shots, per frame: camera pos, target, focus (model's world, LDraw),
    lens, exposure; shots; and the take's facts: frames it crosses the hull in and out, the
    parts hidden per frame (near the camera, not `keep`), how dark the sea is (murk), where
    something huge waits in the dark."""
    pos, tgt, foc = np.zeros((m, 3)), np.zeros((m, 3)), np.zeros((m, 3))
    lens, ev = np.zeros(m), np.zeros(m)
    D = -U
    b = [int(round(a * m)) for a, _, _ in FLY_SHOTS] + [m]
    shots = [[b[i], name] for i, (_, name, _) in enumerate(FLY_SHOTS) if b[i + 1] > b[i]]

    def towards(az, el):
        a, e = math.radians(az), math.radians(el)
        return (F * math.cos(a) + N * math.sin(a)) * math.cos(e) + U * math.sin(e)
    # under the bow: still, low and just off its path, as it passes over
    k = np.arange(b[0], b[1])
    e = smootherstep((k - b[0]) / max(1, b[1] - b[0] - 1))
    p = path[b[1] - 1] + F * (ext["ahead"] * 0.35) + D * (ext["below"] + 0.16 * length) \
        + N * 0.08 * length
    pos[k] = p - np.outer(e, F * 0.04 * length)
    tgt[k] = path[k] + F * ext["ahead"] * 0.55
    foc[k] = path[k] + F * ext["ahead"] * 0.5
    lens[k] = FLY_SHOTS[0][2]
    # wide: below it and to the side, looking up past it at the light
    k = np.arange(b[1], b[2])
    e = smootherstep((k - b[1]) / max(1, b[2] - b[1] - 1))
    p = path[(b[1] + b[2]) // 2] + towards(-70.0, -24.0) * 1.0 * length
    pos[k] = p + np.outer(e, F * 0.14 * length + U * 0.06 * length)      # drifting up with it
    tgt[k] = path[k] + U * 0.12 * length
    foc[k] = path[k]
    lens[k] = FLY_SHOTS[1][2]
    # the take, in the model's own frame (carried with it), then into the world
    t0 = b[2]
    nt = m - t0
    cen = fly["bounds"].mean(0)
    flat = lambda v: v - U * float(v @ U)                               # noqa: E731
    n_in = flat(fly["enter"] - cen)
    n_in /= np.linalg.norm(n_in)
    n_out = flat(fly["exit"] - cen)
    n_out /= np.linalg.norm(n_out)
    en, ex = fly["enter"], fly["exit"]
    room = [en] + fly["path"] + [ex]
    looks = [en - n_in * 0.1 * length] + list(fly["look"]) + [ex + n_out * 0.3 * length]
    pieces = {
        "hull": ([en + n_in * 0.24 * length - F * 0.32 * length + U * 0.05 * length,
                  en + n_in * 0.12 * length],
                 [en + F * 0.3 * length, en]),
        "push": ([en + n_in * 0.12 * length, en], [en, en - n_in * 0.1 * length]),
        "room": (room, looks),
        "out": ([ex, ex + n_out * 0.1 * length], [ex + n_out * 0.3 * length] * 2),
        "back": ([ex + n_out * 0.1 * length,
                  ex + n_out * 0.55 * length - F * 0.2 * length + D * 0.12 * length],
                 [ex + n_out * 0.3 * length, cen]),
        "away": ([ex + n_out * 0.55 * length - F * 0.2 * length + D * 0.12 * length,
                  ex + n_out * 1.5 * length - F * 0.9 * length + D * 0.45 * length],
                 [cen, cen]),
    }
    share = np.array([s for _, s, _ in FLY_PIECES])
    ends = np.r_[0, np.round(np.cumsum(share) / share.sum() * nt)].astype(int)
    cam_m, look_m, lens_t = [], [], []
    for (name, _, ln), f0, f1 in zip(FLY_PIECES, ends, ends[1:]):
        pts, lks = pieces[name]
        if name == "room":
            cur, seg = _spline(pts)
            w = np.interp(seg + 0.5, np.arange(len(pts)), [1.0] + fly["slow"][:len(pts) - 2] + [1.0])
        else:
            cur = np.array([pts[0] + (pts[1] - pts[0]) * s for s in np.linspace(0, 1, 65)])
            seg = np.zeros(len(cur), int)
            w = np.ones(len(cur))
        # what it looks at along the piece: the given points, else straight ahead
        L_pts = []
        for i, (c, sg) in enumerate(zip(cur, seg)):
            j = min(sg + 1, len(lks) - 1) if name == "room" else 1
            j0 = min(sg, len(lks) - 1) if name == "room" else 0
            a_ = lks[j0] if lks[j0] is not None else None
            b_ = lks[j] if lks[j] is not None else None
            ahead = cur[min(i + 4, len(cur) - 1)] - cur[max(i - 4, 0)]
            ahead = c + ahead / (np.linalg.norm(ahead) + 1e-9) * 0.2 * length
            a_ = ahead if a_ is None else a_
            b_ = ahead if b_ is None else b_
            fr = np.clip(i / max(1, len(cur) - 1) * (len(lks) - 1) - j0, 0, 1) if name == "room" \
                else i / max(1, len(cur) - 1)
            L_pts.append(_turn(c, a_, b_, smootherstep(fr), F, N, U))
        L_pts = np.array(L_pts)
        # time along the piece: for the way it moves (slowed where asked) and the way it turns
        v = L_pts - cur
        v /= np.linalg.norm(v, axis=1)[:, None] + 1e-9
        turn = np.degrees(np.arccos(np.clip((v[1:] * v[:-1]).sum(1), -1.0, 1.0)))
        dl = np.r_[0.0, np.linalg.norm(np.diff(cur, axis=0), axis=1) * w[1:] + FLY_TURN * length * turn]
        s_at = np.cumsum(dl) / max(dl.sum(), 1e-9)
        n = f1 - f0
        q = np.linspace(0, 1, n, endpoint=False) if name != "away" else np.linspace(0, 1, n)
        cam_m.append(np.array([np.interp(q, s_at, cur[:, a]) for a in range(3)]).T)
        look_m.append(np.array([np.interp(q, s_at, L_pts[:, a]) for a in range(3)]).T)
        lens_t.append(np.full(n, ln))
    cam_m = np.concatenate(cam_m)
    look_m = np.concatenate(look_m)
    lens_t = _gauss(np.concatenate(lens_t), 6.0)
    # smooth the joins (velocity and aim), keep the window crossings where they are
    cam_m = np.stack([_gauss(cam_m[:, a], 2.5) for a in range(3)], 1)
    look_m = np.stack([_gauss(look_m[:, a], 4.0) for a in range(3)], 1)
    k_in = t0 + int(ends[2])                              # the take reaches the window
    k_out = t0 + int(ends[3])                             # the far wall
    for i in range(nt):
        M = spins[t0 + i]
        pos[t0 + i] = (M @ np.r_[cam_m[i], 1.0])[:3]
        tgt[t0 + i] = (M @ np.r_[look_m[i], 1.0])[:3]
        foc[t0 + i] = tgt[t0 + i]
    lens[t0:] = lens_t
    warm = np.zeros(m)                                    # how much we're in the room: the
    warm[max(0, k_in - 4):k_out + 2] = 1.0                # lamplight leads us in at the window
    room_k = np.clip(_gauss(warm, 4.0), 0.0, 1.0)
    murk = smootherstep((np.arange(m) - (k_out - 0.8 * fps)) / (1.3 * fps))   # dark out there
    # hull parts in the camera's way: near it or just ahead, wherever it goes near the hull
    hide = {}
    lo, hi = C.reshape(-1, 3).min(0), C.reshape(-1, 3).max(0)
    r, ahead = FLY_CLEAR * length, FLY_AHEAD * length
    cand = np.nonzero(~keep)[0]
    for i in range(nt):
        c = cam_m[i]
        if (c < lo - ahead - r).any() or (c > hi + ahead + r).any():
            continue
        d = look_m[i] - c
        d /= np.linalg.norm(d) + 1e-9
        probe = c[None] + np.outer(np.linspace(0, ahead, 5), d)
        near = _box_distance(probe, C[cand]).min(1) < r
        if near.any():
            hide[t0 + i] = cand[near].tolist()
    # something huge in the dark: below and beyond the model as the camera ends up seeing it,
    # its arms reaching up towards it
    fwd = cen - cam_m[-1]
    fwd = flat(fwd) / (np.linalg.norm(flat(fwd)) + 1e-9)
    side = np.cross(U, fwd)
    lurk_m = cen + fwd * 0.9 * length + side * 0.2 * length + D * 0.6 * length
    reach = U * 0.8 - fwd * 0.35 + side * 0.3
    lurk = (spins[m - 1] @ np.r_[lurk_m, 1.0])[:3]
    return pos, tgt, foc, lens, ev, shots, {
        "enter": k_in, "exit": k_out, "inside": [k_in, k_out], "hide": hide, "murk": murk,
        "room": room_k,
        "lurk": {"pos": lurk, "facing": spins[m - 1][:3, :3] @ (reach / np.linalg.norm(reach)),
                 "size": 0.8 * length,
                 "from": k_out}}


def glide_axes(Cv, pivot, front: float, forward=None):
    """The model's own axes for a glide (LDraw): F forward (horizontal: `forward`, else along
    its longest horizontal extent, towards -X or -Z), U up, N the side shown to the camera (the
    model's front, made square to F); and its extents from the pivot: ahead, behind (along F),
    half-width (along N), above and below."""
    U = np.array([0.0, -1.0, 0.0])
    if forward is not None:
        F = np.asarray(forward, float) * [1, 0, 1]
    else:
        span = np.ptp(Cv, axis=0)
        F = np.array([-1.0, 0, 0]) if span[0] >= span[2] else np.array([0, 0, -1.0])
    F /= np.linalg.norm(F)
    N = view_basis(front, 0.0)[0]
    N = N - F * float(N @ F)
    if np.linalg.norm(N) < 1e-3:
        N = np.cross(U, F)
    N /= np.linalg.norm(N)
    d = Cv - pivot
    ext = {"ahead": float((d @ F).max()), "behind": float(-(d @ F).min()),
           "half": float(np.abs(d @ N).max()), "above": float((d @ U).max()),
           "below": float(-(d @ U).min())}
    return F, U, N, ext


def glide_carry(m: int, fps: int, pivot, F, U, N, length: float, lengths: float = GLIDE_LENGTHS):
    """Per frame the whole model's transform (LDraw 4x4) for a glide: forward through the pivot
    at mid-performance, `lengths` of its `length` in all, banking a few degrees, its nose
    lifting and dipping, a slow bob; and its centre's path (m, 3)."""
    t = np.arange(m) / fps
    s = np.arange(m) / max(1, m - 1) - 0.5
    roll = 4.0 * np.sin(2 * np.pi * t / 5.5 + 0.6)
    pitch = 2.5 * np.sin(2 * np.pi * t / 4.3 + 2.0) - 1.0
    yaw = 1.5 * np.sin(2 * np.pi * t / 7.0)
    bob = 0.02 * length * np.sin(2 * np.pi * t / 3.7)
    path = pivot + np.outer(s * lengths * length, F) + np.outer(bob, U)
    out = []
    for k in range(m):
        R = (_axis_rot(F, roll[k]) @ _axis_rot(N, pitch[k]) @ _axis_rot(U, yaw[k]))
        M = np.eye(4)
        M[:3, :3] = R
        out.append(translate(*path[k]) @ M @ translate(*(-np.asarray(pivot, float))))
    return np.array(out), path


def _axis_rot(axis, deg: float) -> np.ndarray:
    x, y, z = np.asarray(axis, float) / np.linalg.norm(axis)
    a = math.radians(deg)
    c, s_ = math.cos(a), math.sin(a)
    return np.array([[c + x * x * (1 - c), x * y * (1 - c) - z * s_, x * z * (1 - c) + y * s_],
                     [y * x * (1 - c) + z * s_, c + y * y * (1 - c), y * z * (1 - c) - x * s_],
                     [z * x * (1 - c) - y * s_, z * y * (1 - c) + x * s_, c + z * z * (1 - c)]])


def glide_camera(m: int, path, F, U, N, ext: dict, length: float):
    """The glide's three shots, per frame: camera pos, target, focus (LDraw), lens; shots.
    approach: still, below it and off its bow, as it comes out of the blue towards the camera;
    side: tracking along its shown side a little below and slower than it, so it slides
    through the frame; bow: still, just off its path, the bow sweeping past the lens."""
    pos, tgt, foc, lens = np.zeros((m, 3)), np.zeros((m, 3)), np.zeros((m, 3)), np.zeros(m)
    D = -U
    shots = []
    bounds = [int(round(a * m)) for a, _, _ in GLIDE_SHOTS] + [m]

    def towards(az, el):                       # a unit vector from the model: az from F to N
        a, e = math.radians(az), math.radians(el)
        return (F * math.cos(a) + N * math.sin(a)) * math.cos(e) + U * math.sin(e)
    for i, (_, name, ln) in enumerate(GLIDE_SHOTS):
        f0, f1 = bounds[i], bounds[i + 1]
        if f1 <= f0:
            continue
        shots.append([f0, name])
        k = np.arange(f0, f1)
        e = smootherstep((k - f0) / max(1, f1 - f0 - 1))
        if name == "approach":
            p = path[f1 - 1] + towards(42.0, -15.0) * 0.82 * length
            pos[k] = p + np.outer(1 - e, towards(42.0, -15.0) * 0.1 * length)   # easing in
            tgt[k] = path[k] + F * 0.12 * length
            foc[k] = path[k] + F * 0.2 * length
        elif name == "side":
            speed = path[f1 - 1] - path[f0]
            base = path[f0] + np.outer(0.75 * (k - f0) / max(1, f1 - f0 - 1), speed)
            pos[k] = base + towards(90.0, -7.0) * (ext["half"] + 1.0 * length) - F * 0.05 * length
            aim = np.outer(-0.18 + 0.4 * e, F * length)
            tgt[k] = path[k] + aim
            foc[k] = path[k] + aim * 0.5
        else:
            fb = f0 + int(0.62 * (f1 - f0))
            p = path[min(fb, m - 1)] + F * ext["ahead"] * 0.55 + N * (ext["half"] + 0.07 * length) \
                + D * 0.03 * length
            pos[k] = p
            bow = path[k] + F * ext["ahead"] * 0.6
            tgt[k] = bow
            foc[k] = path[k] + F * ext["ahead"] * 0.45 + N * ext["half"]
        lens[k] = ln
    return pos, tgt, foc, lens, shots


def tap_program(m: int, fps: int, beat: int, taps=None):
    """A tap lamp pressed and let go: ([[frame, "on" | "off"]], u, led, kick) for m frames.
    `taps` in seconds (default TAP_BEATS); each press clicks at the bottom of its travel (its
    frame), where the push-on/push-off switch toggles the lights: on with a flash that settles
    (led above 1 for a few frames), off in a few frames. u: the pose parameter (0 rest, 1 pressed,
    a small rebound after); kick: 0..1 per frame, the camera's jolt after each click."""
    at = [round(float(s) * fps) for s in taps] if taps else [round(b * beat) for b in TAP_BEATS]
    at = [c for c in sorted(at) if TAP_DOWN <= c < m - TAP_HOLD - 2]
    k = np.arange(m, dtype=float)
    u, led, kick = np.zeros(m), np.zeros(m), np.zeros(m)
    out = []
    for i, c in enumerate(at):
        state = "on" if i % 2 == 0 else "off"
        out.append([int(c), state])
        up0 = c + TAP_HOLD
        p = smootherstep((k - (c - TAP_DOWN)) / TAP_DOWN) * (1 - smootherstep((k - up0) / TAP_UP))
        r0 = up0 + TAP_UP
        p += np.where((k >= r0) & (k < r0 + 6), 0.12 * np.sin(np.pi * (k - r0) / 6), 0.0)
        u = np.maximum(u, p)
        d = np.maximum(k - c, 0.0)
        if state == "on":
            led = np.where(k >= c, 1.0 + 0.9 * np.exp(-d / 2.2), led)
        else:
            led = np.where(k >= c, np.where(d < 5, np.exp(-d / 0.8), 0.0), led)
        kick = np.maximum(kick, np.where(k >= c, np.exp(-d / 5.0), np.where(k == c - 1, 0.55, 0.0)))
    return out, np.clip(u, 0.0, 1.0), led, kick


def led_list(model, placed) -> list[dict]:
    """The model's LEDs for the renderers: instance, colour, power, offset, position."""
    leds = []
    for light in model.lights:
        found = model.find(light["part"], placed)
        if found:
            leds.append({"instance": found[0].index, "color": light["color"],
                         "power": float(light["power"]), "name": light.get("name", ""),
                         "offset": [float(v) for v in light.get("offset", (0, 0, 0))],
                         "pos": model.light_position(light, placed).tolist()})
    return leds


def spin_curve(n: int, turns: float) -> np.ndarray:
    """Degrees turned by each frame: `turns` in three lurches (30 %, 40 %, 30 % of it), each
    easing in and out, overlapping a little so the turn never quite stops."""
    k = np.arange(n) / max(1, n - 1)
    out = np.zeros(n)
    for (a, b), share in zip(((0.1, 0.42), (0.38, 0.7), (0.66, 0.98)), (0.3, 0.4, 0.3)):
        out += share * smootherstep((k - a) / (b - a))
    return 360.0 * float(turns) * out


def _frame_shot(H: float, R: float, hc: float, lens: float, feet: float, top: float | None,
                sun: tuple[float, float] | None = None) -> tuple[float, float]:
    """(horizontal distance, pitch deg) for a camera hc above the ground framing a figure H
    tall and R round (spinning): its feet at `feet` of the frame's height and its head at `top`;
    with top None, its head just under the middle of the sun (elevation, size deg), the sun
    above it. The figure's width stays inside."""
    a = math.atan(18.0 / lens)
    if top is None:
        el, size = sun
        head = math.radians(max(el - 0.3 * size, 0.2))
        d = (H - hc) / math.tan(head)
    else:
        want = 2 * a * (top - feet)
        lo, hi = H * 0.02, H * 5000.0
        for _ in range(80):                   # the figure's angular height shrinks with d
            mid = math.sqrt(lo * hi)
            got = math.atan((H - hc) / mid) + math.atan(hc / mid)
            lo, hi = (mid, hi) if got > want else (lo, mid)
        d = hi
    d = max(d, 1.25 * R / math.tan(0.8 * a))   # the swing's reach fits across
    p = -math.atan(hc / d) + a - 2 * a * feet
    return d, math.degrees(p)


def cold_open_plan(engine, model, placed, C, seg: dict, co: dict, fps: int, beat: int,
                   black_beats: int = COLD_BLACK_BEATS) -> dict:
    """The cold open, frame by frame (frames relative to its start, the performance only: the
    last `black_beats` are black). JSON-able:
        start, end, cut        its frames; black from `cut`
        scene, sun             the set ("sunset_road"), the sun's elevation/azimuth/size (deg;
                               azimuth 0 is straight ahead of the camera, down the road, +Z)
        look                   the set's look overrides from the config (COLD_LOOK keys)
        ground_y, pivot        the road's height and the spin's axis ([x, z]) in LDU
        height, radius         how tall the figure is and how far its swing reaches
        hidden                 instances not shown (hide_tags: a display stand)
        groups                 {names, instance}: the moving groups (the mechanism's groups)
        frames                 per frame, per group a 4x4 world matrix (LDraw, row-major)
        spin                   per frame the figure's turn about the pivot (4x4 LDraw)
        u                      per frame the performance's phase (pose parameter as fallback)
        camera                 per frame pos, target (LDU), lens (mm) and exposure (EV);
                               `shots` [[frame, name]]
        rev                    per frame 0..1: how hard the engine revs (the saw's speed)
        catch                  the frame the engine catches
    and with motion "tap" (tap_program): motion, taps [[frame, "on" | "off"]] (absolute), led
    (per frame, above 1 in the flash as they come on), leds (led_list); scene night_desk adds
    front (the model's azimuth_offset: the room is laid out behind it); with motion "glide":
    motion, leds and led (lit throughout), glide {forward, side, length, extent, path (its
    centre per frame)}, the spin carrying it along the path, and camera.focus per frame; with
    motion "flythrough" (a glide through the model's room) also flythrough {enter, exit, inside
    (absolute frames: the camera crosses the hull), hide {frame (relative): [instances]}, murk
    and room (per frame 0..1: the sea's dark, the room's lamplight), bounds, at {enter, exit}
    (LDU), keep (instances never hidden), lurk {pos, facing, size, from (relative frame)}}"""
    n = seg["end"] - seg["start"]
    m = n - black_beats * beat
    info = model.meta.get("performance_info") or {}
    hide = set(co["hide_tags"])
    hidden = [p.index for p in placed if hide & set(p.tags)]
    vis = np.ones(len(placed), bool)
    vis[hidden] = False
    if not vis.any():
        vis[:] = True
        hidden = []
    Cv = C[vis].reshape(-1, 3)
    ground_y = float(info.get("ground_y", Cv[:, 1].max()))
    px, pz = info.get("pivot", ((Cv[:, 0].min() + Cv[:, 0].max()) / 2,
                                (Cv[:, 2].min() + Cv[:, 2].max()) / 2))
    pivot = np.array([float(px), ground_y, float(pz)])
    # the motion: the performance loop (or the pose swinging 0..1..0), coming up to speed; or
    # tapped, a tap lamp
    tap = co["motion"] == "tap"
    fly = co["motion"] == "flythrough"
    glide = co["motion"] == "glide" or fly
    perf = model.meta.get("performance") if co["motion"] in ("performance", "glide",
                                                              "flythrough") else None
    fn = perf or model.pose
    t = np.arange(m) / fps
    tp = t if glide else np.cumsum(smootherstep((t - COLD_START) / COLD_RAMP)) / fps
    cyc = float(co["cycle"])
    u = (tp / cyc) % 1.0 if perf else 0.5 - 0.5 * np.cos(2 * np.pi * tp / cyc)
    if tap:
        taps, u, led, kick = tap_program(m, fps, beat, co.get("taps"))
    names, inst = [], [-1] * len(placed)
    if fn is not None:
        probe = fn(0.0) or {}
        for p in placed:
            g = model.group_of(p)
            if g is not None and g in probe and vis[p.index]:
                if g not in names:
                    names.append(g)
                inst[p.index] = names.index(g)
    ident = np.eye(4)
    mats = np.zeros((m, len(names), 4, 4))
    for k in range(m):
        P = (fn(float(u[k])) or {}) if names else {}
        for j, g in enumerate(names):
            mats[k, j] = np.asarray(P.get(g, ident), float)
    yaw = spin_curve(m, float(co["spin_turns"]))
    from ..ldraw.matrix import rot, transform
    spins = np.array([translate(*pivot) @ transform((0, 0, 0), rot(y=a)) @ translate(*(-pivot))
                      for a in yaw])
    if glide:                                     # cruising: carried through the water
        front = float(model.meta.get("azimuth_offset", 0.0))
        centre = (Cv.min(0) + Cv.max(0)) / 2
        F, U, N, ext = glide_axes(Cv, centre, front, co.get("forward"))
        length = ext["ahead"] + ext["behind"]
        spins, gpath = glide_carry(m, fps, centre, F, U, N, length,
                                   float(co.get("glide_lengths", FLY_LENGTHS if fly else GLIDE_LENGTHS)))
    # every part's centre per frame (for the height, the reach and the saw's speed)
    gi = np.array(inst)
    ctr = C.mean(1)
    step = max(1, m // 60)

    def centres(k, sel):
        c = np.c_[ctr[sel], np.ones(int(sel.sum()))]
        out = np.empty((int(sel.sum()), 3))
        gs = gi[sel]
        for j in set(gs.tolist()):
            M = spins[k] @ (mats[k, j] if j >= 0 else ident)
            out[gs == j] = (c[gs == j] @ M.T)[:, :3]
        return out
    tops, reach = [], []
    for k in range(0, m, step):
        pts = []
        for j in set(gi[vis].tolist()):
            M = mats[k, j] if j >= 0 else ident
            sel = vis & (gi == j)
            pts.append(apply(M, C[sel].reshape(-1, 3)))
        q = np.concatenate(pts)
        tops.append(q[:, 1].min())
        reach.append(float(np.hypot(q[:, 0] - pivot[0], q[:, 2] - pivot[2]).max()))
    H = float(ground_y - min(tops))
    R = float(max(reach))
    # the engine revs with the saw's speed
    saw = vis & np.array([co["rev_tag"] in p.tags for p in placed])
    if not saw.any():
        saw = vis & (gi >= 0) if (gi >= 0).any() else vis
    path = np.array([centres(k, saw).mean(0) for k in range(m)])
    speed = np.r_[0.0, np.linalg.norm(np.diff(path, axis=0), axis=1)] * fps
    speed = _gauss(speed, 1.5)
    top = float(np.percentile(speed, 95)) or 1.0
    rev = np.clip(speed / top, 0.0, 1.0) ** 0.8
    catch = int(round(COLD_CATCH * fps))
    rev = rev * smootherstep((t - COLD_START) / COLD_RAMP)
    rev[:catch] = 0.0
    if tap or glide:                              # no engine
        rev[:] = 0.0
        catch = 0
    # the camera: hard cuts between the shots, each a slow move
    el = float(co["sun_elevation"])
    band = float(co["letterbox"])
    pos = np.zeros((m, 3))
    tgt = np.zeros((m, 3))
    lens = np.zeros(m)
    ev = np.zeros(m)
    shots = []
    plan = COLD_SHOTS
    if co["scene"] == "night_desk":               # azimuths from the model's front
        front = float(model.meta.get("azimuth_offset", 0.0))
        cut_at = ((taps[1][0] + taps[2][0]) / 2 / m if tap and len(taps) >= 3 else 0.5)
        plan = tuple((cut_at if a0 is None else a0, name, ln, hc_k, -(front + az), feet, top_k,
                      dolly, ev_k) for a0, name, ln, hc_k, az, feet, top_k, dolly, ev_k in DESK_SHOTS)
    if glide and not fly:
        plan = ()
        pos, tgt, focus, lens, shots = glide_camera(m, gpath, F, U, N, ext, length)
    if fly:                                       # through its room (flythrough_camera)
        plan = ()
        fc = flythrough_config(model, co)
        keep = np.array([bool(fc["tags"] & set(p.tags)) for p in placed]) | ~vis
        pos, tgt, focus, lens, ev, shots, take = flythrough_camera(
            m, fps, spins, gpath, F, U, N, ext, length, fc, C, keep)
    for i, (a0, name, ln, hc_k, az, feet, top_k, dolly, ev_k) in enumerate(plan):
        f0 = int(round(a0 * m))
        f1 = int(round(plan[i + 1][0] * m)) if i + 1 < len(plan) else m
        if f1 <= f0:
            continue
        shots.append([f0, name])
        feet_f = band + (1 - 2 * band) * feet
        top_f = None if top_k is None else band + (1 - 2 * band) * top_k
        hc = hc_k * H
        d, pitch = _frame_shot(H, R, hc, ln, feet_f, top_f, (el, float(co["sun_size"])))
        for k in range(f0, f1):
            e = float(smootherstep((k - f0) / max(1, f1 - f0 - 1)))
            dk = d * (1 - dolly * e)
            fov = 2 * math.degrees(math.atan(18.0 / ln))           # a slow arc: a tenth of a frame
            azk = math.radians(az + (0.1 if az >= 0 else -0.1) * fov * e * (az != 0))
            fwd = np.array([math.sin(azk), 0.0, math.cos(azk)])
            cam = pivot - fwd * dk + np.array([0.0, -hc, 0.0])
            pr = math.radians(pitch)
            look = np.array([fwd[0] * math.cos(pr), -math.sin(pr), fwd[2] * math.cos(pr)])
            pos[k], tgt[k], lens[k], ev[k] = cam, cam + look * dk, ln, ev_k
    if tap:                                       # the jolt of each click: a quick punch-in
        amp = np.zeros(m)
        for c, state in taps:
            amp[c - 1:] = TAP_KICK[state]
        lens = lens * (1.0 + amp * kick)
    r5 = lambda a: np.round(a, 5).tolist()   # noqa: E731
    extra = {}
    if tap:
        extra.update(motion="tap", taps=[[seg["start"] + c, st] for c, st in taps], led=r5(led),
                     leds=led_list(model, placed))
    if co["scene"] == "night_desk":
        extra["front"] = float(model.meta.get("azimuth_offset", 0.0))
    if fly:
        lb = fc["bounds"]
        extra["flythrough"] = {"enter": seg["start"] + take["enter"],
                               "exit": seg["start"] + take["exit"],
                               "inside": [seg["start"] + v for v in take["inside"]],
                               "hide": {str(k): v for k, v in take["hide"].items()},
                               "murk": r5(take["murk"]), "room": r5(take["room"]),
                               "bounds": r5(lb),
                               "at": {"enter": r5(fc["enter"]), "exit": r5(fc["exit"])},
                               "keep": np.nonzero(keep & vis)[0].tolist(),
                               "lurk": {"pos": r5(take["lurk"]["pos"]),
                                        "facing": r5(take["lurk"]["facing"]),
                                        "size": round(take["lurk"]["size"], 3),
                                        "from": take["lurk"]["from"]}}
    if glide:
        extra.update(motion=co["motion"], leds=led_list(model, placed), led=[1.0] * m,
                     glide={"forward": r5(F), "side": r5(N), "length": round(length, 3),
                            "extent": {k: round(v, 3) for k, v in ext.items()},
                            "path": r5(gpath)})
    cam_out = {"pos": r5(pos), "target": r5(tgt), "lens": lens.tolist(), "exposure": ev.tolist()}
    if glide:
        cam_out["focus"] = r5(focus)
    return extra | {
        "start": seg["start"], "end": seg["end"], "cut": seg["start"] + m, "scene": co["scene"],
        "sun": {"elevation": el, "azimuth": float(co["sun_azimuth"]), "size": float(co["sun_size"])},
        "look": {k: co[k] for k in COLD_LOOK if k in co},
        "ground_y": ground_y, "pivot": [float(pivot[0]), float(pivot[2])], "height": H,
        "radius": R, "hidden": hidden, "letterbox": band,
        "groups": {"names": names, "instance": inst},
        "frames": [[r5(M.reshape(-1)) for M in row] for row in mats],
        "spin": [r5(M.reshape(-1)) for M in spins], "u": r5(u), "yaw": r5(yaw),
        "camera": cam_out, "shots": shots,
        "rev": r5(rev), "catch": seg["start"] + catch,
    }


# ---------------------------------------------------------------------------- the coda
# [video.coda] (opt-in): the video's last moments, after the outro. scene "deep_sea": the cold
# open's sea gone dark, the model cruising with its lights on, and its `creature` coming out of
# the murk at it: "squid", a giant squid about the model's size, arms first - its arms writhing,
# its two long tentacles uncoiling and reaching for the model, its eye catching the light - the
# two of them in one frame, seen from off the model's side; the picture fades to black as it
# closes in (`fade` s). Its own set renders it (render/blender_cold_open.py, as a cold open: the
# plan has the same fields, see coda_plan). Its keys: scene, creature, seconds; model (false:
# leave the model out), murk (0..1: how dark the sea is), size (the squid's mantle, in the
# model's lengths: its body and arms are about twice that, its tentacles reach as far again),
# glide_lengths (how far the model cruises over the shot), exposure (EV, on the set's own), roll
# (degrees the squid is turned from side on, away from the camera), fade (s of fading to black
# at the end; the compositor's).
CODA = {"scene": "deep_sea", "creature": "squid", "seconds": 4.0, "model": True,
        "murk": 0.85, "size": 0.34, "glide_lengths": 0.25, "exposure": -0.4, "roll": 25.0,
        "fade": 1.2}
CODA_SCENES = ("deep_sea",)
CODA_CREATURES = ("squid",)
CODA_LENS = 28.0
# the shot: the camera off the model's side and a little below it (model lengths), the model up
# a little left of the middle; the squid's head (screen x, y, depth in model lengths from the
# camera) from the murk beyond the model, low on the right, closing on it (eased out)
CODA_CAMERA = (1.9, 0.3)
CODA_MODEL_AT = (0.42, 0.4)
CODA_HEAD = ((0.0, (0.98, 0.84), 2.6), (0.55, (0.77, 0.66), 2.0), (1.0, (0.67, 0.58), 1.8))


def coda_config(model, cfg) -> dict | None:
    """The coda's settings ([video.coda] over CODA), or None without one."""
    cc = cfg.get("coda")
    if not cc:
        return None
    out = dict(CODA)
    out.update(cc if isinstance(cc, dict) else {})
    if out["scene"] not in CODA_SCENES:
        raise SystemExit(f"unknown coda scene {out['scene']!r}; choose from {', '.join(CODA_SCENES)}")
    if out["creature"] not in CODA_CREATURES:
        raise SystemExit(f"unknown coda creature {out['creature']!r}; choose from "
                         f"{', '.join(CODA_CREATURES)}")
    return out


def _unproject(pos, r, u, f, sx, sy, depth, lens):
    """The point `depth` in front of the camera (along f) at screen fractions (sx, sy)."""
    k = 36.0 / lens
    return pos + depth * (f + r * (sx - 0.5) * k - u * (sy - 0.5) * k)


def coda_shot(m: int, path, F, U, N, length: float, cc: dict):
    """The coda's take, per frame (LDraw): camera pos, target, focus, lens; the creature
    {pos (its head), axis (where its arms point), back, size (its mantle, LDU), reach (its
    tentacles: 0 coiled .. 1 reaching out), rim, glint (0.. its edges and eyes lit), light (the
    way its own light travels), seed}; and murk (0..1 per frame, how dark the sea is)."""
    L = float(length)
    D = -U
    mid = path[m // 2]
    k = np.arange(m)
    e = smootherstep(k / max(1, m - 1))
    cam0 = mid + N * CODA_CAMERA[0] * L + D * CODA_CAMERA[1] * L       # off its side, below
    # aim so the model sits where CODA_MODEL_AT says, a few corrections of the aim
    f = (mid - cam0) / np.linalg.norm(mid - cam0)
    for _ in range(4):
        x, y, _ = project(mid[None], cam0, cam0 + f, CODA_LENS)[0]
        r, u, _ = camera_basis(cam0, cam0 + f)
        f = f + (r * (x - CODA_MODEL_AT[0]) - u * (y - CODA_MODEL_AT[1])) * 36.0 / CODA_LENS
        f /= np.linalg.norm(f)
    r, u, _ = camera_basis(cam0, cam0 + f)
    # the squid's head along the shot, in the first frame's view
    t_k = np.array([a for a, _, _ in CODA_HEAD])
    e2 = 1.0 - (1.0 - k / max(1, m - 1)) ** 2
    sx = np.interp(e2, t_k, [p[0] for _, p, _ in CODA_HEAD])
    sy = np.interp(e2, t_k, [p[1] for _, p, _ in CODA_HEAD])
    dz = np.interp(e2, t_k, [d for _, _, d in CODA_HEAD]) * L
    head = np.array([_unproject(cam0, r, u, f, a, b, c, CODA_LENS) for a, b, c in zip(sx, sy, dz)])
    head = _gauss(head, 3.0)
    # the camera pushes in a little
    pos = cam0 + np.outer(e, (mid - cam0) * 0.06)
    tgt = pos + f * L
    # it goes for the model arms first: the arms point at its middle, flattened towards the
    # picture's plane (seen side on), its back up in the picture
    aim = path + U * 0.04 * L - head
    aim /= np.linalg.norm(aim, axis=1, keepdims=True)
    axis = aim - np.outer(aim @ f, f) * 0.85
    axis /= np.linalg.norm(axis, axis=1, keepdims=True)
    back = U - axis * (axis @ U)[:, None]
    fp = f - axis * (axis @ f)[:, None]
    fp /= np.linalg.norm(fp, axis=1, keepdims=True)
    back = back - fp * (back * fp).sum(1)[:, None]
    back /= np.linalg.norm(back, axis=1, keepdims=True)
    a_ = math.radians(float(cc["roll"]))         # rolled away a little: its belly and fins seen
    back = back * math.cos(a_) + fp * math.sin(a_)
    u_ = k / max(1, m - 1)
    reach = 0.12 + 0.88 * smootherstep((u_ - 0.25) / 0.6)         # coiled, then reaching out
    rim = smootherstep(u_ / 0.45)                                # out of the murk
    glint = smootherstep((u_ - 0.42) / 0.1) * (0.85 + 0.6 * np.exp(-np.maximum(u_ - 0.52, 0) * 12))
    murk = np.full(m, float(cc["murk"]))
    light = D - f * 0.45 + r * 0.15
    squid = {"pos": head, "axis": axis, "back": back, "size": float(cc["size"]) * L,
             "reach": reach, "rim": rim, "glint": glint, "light": light / np.linalg.norm(light),
             "seed": 7}
    return pos, tgt, head, np.full(m, CODA_LENS), squid, murk


def coda_plan(engine, model, placed, C, seg: dict, cc: dict, fps: int, beat: int) -> dict:
    """The coda (coda_config), frame by frame: the fields of a deep_sea glide's cold_open_plan
    (the model cruising far off, slowly: `glide_lengths`; hidden altogether with model =
    false), one shot ("coda") of coda_shot's camera, and coda {creature, murk (per frame),
    fade (frames: the compositor fades the last of them to black), squid (coda_shot's, per
    frame)}."""
    co = cold_open_config(model, {"cold_open": {"scene": cc["scene"], "motion": "glide",
                                                "seconds": cc["seconds"],
                                                "glide_lengths": cc["glide_lengths"]}})
    plan = cold_open_plan(engine, model, placed, C, seg, co, fps, beat, black_beats=0)
    m = seg["end"] - seg["start"]
    g = plan["glide"]
    F, N = np.array(g["forward"]), np.array(g["side"])
    U = np.array([0.0, -1.0, 0.0])
    pos, tgt, foc, lens, squid, murk = coda_shot(m, np.array(g["path"]), F, U, N, g["length"], cc)
    r5 = lambda a: np.round(a, 5).tolist()   # noqa: E731
    if not cc.get("model", True):
        plan.update(hidden=list(range(len(placed))), leds=[])
    plan.update(camera={"pos": r5(pos), "target": r5(tgt), "focus": r5(foc),
                        "lens": lens.tolist(), "exposure": [float(cc["exposure"])] * m},
                shots=[[0, "coda"]],
                coda={"creature": cc["creature"], "murk": r5(murk),
                      "fade": int(round(float(cc["fade"]) * fps)),
                      "squid": {k: (r5(v) if isinstance(v, np.ndarray) else v)
                                for k, v in squid.items()}})
    return plan


# ---------------------------------------------------------------------------- timeline
def build_timeline(engine, model, segments: list[dict], *, fps: int = FPS, beat: int = BEAT,
                   variants: dict | None = None, backdrop: str | None = None,
                   cfg: dict | None = None) -> dict:
    """`variants`: {name: {"title": str, "model": Model}} colourways with the same parts in
    the same places as `model` (see make_video); `cfg` the video config (default the model's,
    video_config)."""
    cfg = video_config(model) if cfg is None else cfg
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
    appear, seq, step, sections, land_last = build_schedule(model, placed, b, cfg, beat, engine, C)
    drop = float(cfg.get("drop", DROP))
    if ground_up(cfg):                        # each part drops a short way into place
        offsets = [[0.0, -drop, 0.0] for _ in placed]
    else:                                     # along its insertion direction
        dirs = insert_directions(model)
        assert len(dirs) == len(placed)
        offsets = [((d if d is not None else np.array([0.0, -1.0, 0.0])) * drop).tolist()
                   for d in dirs]
    top = C[:, :, 1].min(1)                   # each part's highest point (LDraw -Y up)
    ground_y = float(C[:, :, 1].max())
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
            taps = tap_curve(L["end"] - L["start"], on)
            if cfg.get("lights_off"):             # and a second tap switches them off
                taps = np.maximum(taps, tap_curve(L["end"] - L["start"],
                                                  power_off_frame(L, beat) - L["start"]))
            for uu in taps:
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
    power_on = power_off = None
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
        if cfg.get("lights_off"):
            power_off = power_off_frame(L, beat)
            off = power_off - L["start"]
            flick[k >= off] = 0.0
            d = np.where(k >= off, LIGHTS_DIM + (1 - LIGHTS_DIM) * smootherstep((k - off - 2) / (1.2 * beat)), d)
        dim[a:a + n] = d
        led[a:a + n] = flick
        if lift_seg and lift_seg["start"] == L["end"] and not cfg.get("lights_off"):
            a2, n2 = lift_seg["start"] - s0, lift_seg["end"] - lift_seg["start"]
            k2 = np.arange(n2)
            dim[a2:a2 + n2] = LIGHTS_DIM + (LIFT_DIM - LIGHTS_DIM) * smootherstep(k2 / (0.5 * n2))
            led[a2:a2 + n2] = 1.0
    leds = led_list(model, placed)

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
    cold = None
    if "cold_open" in seg:
        cold = cold_open_plan(engine, model, placed, C, seg["cold_open"],
                              cold_open_config(model, cfg), fps, beat)
    coda = None
    if "coda" in seg:
        coda = coda_plan(engine, model, placed, C, seg["coda"], coda_config(model, cfg), fps, beat)

    return {
        "fps": fps, "beat": beat, "frames": total, "segments": segments, "scene": scene,
        "scene_range": [s0, s1],
        "model": {"name": model.name, "slug": model.slug, "variant": model.variant,
                  "parts": len(placed), "pieces": bom_pieces(engine, model, placed),
                  "steps": len(model.instruction_order()), "shape": shape},
        "build": {"appear": appear.tolist(), "drop": DROP_FRAMES, "offset": offsets,
                  "order": seq, "step": step.tolist(), "section": section_of.tolist(),
                  "land_last": land_last, "top_mm": np.round((ground_y - top) * 0.4, 1).tolist(),
                  "sections": [{k: v for k, v in s.items() if k != "parts"} |
                               {"parts": len(s["parts"])} for s in sections]},
        "camera": cam, "shots": shots,
        "groups": {"names": group_names, "instance": inst_group,
                   "start": mech["start"] if mech else 0, "frames": pose_frames, "after": []},
        "mechanism": {"u": u_frames, "rest": rest, "angles": angles},
        "lift": {"instance": lifted.tolist(), "start": lift_seg["start"] if lift_seg else 0,
                 "frames": lift_frames},
        "lights": {"leds": leds, "dim": dim.tolist(), "led": led.tolist(), "glow": led.tolist(),
                   "start": s0, "power_on": power_on, "power_off": power_off},
        "variants": var_out, "colourways": cw, "cold_open": cold, "coda": coda,
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
