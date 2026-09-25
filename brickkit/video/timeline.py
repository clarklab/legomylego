"""Build-video timeline (engine side; no Blender needed).

`build_timeline(engine, model, booklet=False)` plans the whole video and returns a JSON-able dict.
Every frame number is absolute (frame 0 is the first frame of the video, at `fps`).

    fps, frames        frame rate and total length
    segments           [{name, start, end, kind}] in play order; kind: card | scene | booklet
    scene              model scene for Blender (render/scene.py's model_scene; LEDs handled here)
    scene_range        [start, end): the frames rendered in the model scene
    build              per instance: appear frame (float), drop length (frames), start offset (LDU)
    camera             per scene frame: pos and target (LDraw coords), lens (mm)
    groups             moving groups: names, per-instance group index, per-frame pose matrices
    lift               per-instance flag, per-frame world matrices of the lifted parts
    lights             LEDs (instance, colour, power) and per scene frame levels (dim, led, glow)

Storyboard (a segment is dropped when it doesn't apply to the model):
    title      model name and piece count on the brand yellow
    build      parts drop in, in instruction order, while the camera orbits the front
    showcase   slow orbit round the finished model; stretches so the video lasts ~37 s
    mechanism  `model.pose(t)` 0 -> 1 -> 0 from a low 3/4 angle (flat models: from above)
    lights     studio lights dim, LEDs and glowing parts fade in          (if model.lights/glow)
    lift       everything but `exclude_tag` rises and hovers   (if meta["video"]["lift"])
    booklet    the instruction booklet's pages turn             (if out/booklet.pdf exists)
    end        logo and the site URL

Per-model tweaks go in `model.meta["video"]` (all optional):
    {"lift": {"exclude_tag": "stand", "height": 80}, "seconds": {"build": 15},
     "build_first": "tag", "drop": 24}
"""
from __future__ import annotations

import math

import numpy as np

from ..ldraw.matrix import apply, translate
from ..model.builder import Placement
from ..render.scene import model_scene

FPS = 30
LENS = 70.0
MARGIN = 1.3              # frame = 1/MARGIN of the image is model (a little air round it)
DROP = 24.0               # LDU a part travels as it drops in (about a stud)
DROP_FRAMES = 8           # how long a drop takes
SECONDS = {"title": 2.0, "build": 15.0, "mechanism": 6.0, "lights": 3.0, "lift": 3.0,
           "booklet": 5.0, "end": 2.0}
TARGET_SECONDS = 37.0     # the showcase orbit fills the video up to this length
SHOWCASE_SECONDS = (3.0, 20.0)
ORDER = ("title", "build", "showcase", "mechanism", "lights", "lift", "booklet", "end")
KIND = {"title": "card", "end": "card", "booklet": "booklet"}
FADE_IN = {"build": 10, "booklet": 12, "end": 12}   # crossfade from the previous segment's last frame
LIGHTS_DIM = 0.16         # studio light level with the LEDs on
LIFT_DIM = 0.3


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
    """Pieces on the parts list (what the title card counts; the site and booklet agree)."""
    from ..bom.bom import build_bom
    return sum(line.qty for line in build_bom(placed, engine.catalog,
                                              getattr(model, "extras", ())))


def video_config(model) -> dict:
    return dict(model.meta.get("video", {}) or {})


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


def fit(points: np.ndarray, az: float, el: float, lens: float = LENS, margin: float = MARGIN):
    """Target and distance that frame `points` (n, 3) tightly and centred from (az, el)."""
    t = (18.0 / lens) / margin          # tan(half fov) for a 36 mm square sensor, with margin
    d, r, u = view_basis(az, el)
    target = (points.min(0) + points.max(0)) / 2
    dist = 0.0
    for _ in range(4):
        c = points - target
        cd, cr, cu = c @ d, c @ r, c @ u
        dist = float(max((cd + np.abs(cr) / t).max(), (cd + np.abs(cu) / t).max()))
        depth = np.maximum(dist - cd, 1e-6)
        x, y = cr / depth, cu / depth
        target = target + r * (x.max() + x.min()) / 2 * dist + u * (y.max() + y.min()) / 2 * dist
    c = points - target
    cd, cr, cu = c @ d, c @ r, c @ u
    dist = float(max((cd + np.abs(cr) / t).max(), (cd + np.abs(cu) / t).max()))
    return target, dist


# ---------------------------------------------------------------------------- plan
def plan_segments(model, booklet: bool, fps: int = FPS) -> list[dict]:
    cfg = video_config(model)
    secs = {**SECONDS, **cfg.get("seconds", {})}
    has = {
        "title": True, "build": True, "showcase": True, "end": True,
        "mechanism": model.pose is not None and bool(model.groups),
        "lights": bool(model.lights) or bool(model.glow_tags),
        "lift": bool(cfg.get("lift")),
        "booklet": bool(booklet),
    }
    names = [n for n in ORDER if has[n]]
    other = sum(secs[n] for n in names if n != "showcase")
    lo, hi = SHOWCASE_SECONDS
    secs["showcase"] = cfg.get("seconds", {}).get("showcase",
                                                  min(hi, max(lo, TARGET_SECONDS - other)))
    out, f = [], 0
    for n in names:
        k = int(round(secs[n] * fps))
        out.append({"name": n, "start": f, "end": f + k, "kind": KIND.get(n, "scene"),
                    "fade_in": FADE_IN.get(n, 0)})
        f += k
    return out


def build_schedule(model, placed, seg, cfg, front_az: float):
    """Appear frame (float) for each part: instruction order (build_order, then the step inside
    its sub-assembly), then bottom-up and sweeping round the model within a step. Parts of a
    step are staggered across the step's share of the segment."""
    order = {k: i for i, k in enumerate(model.instruction_order())}
    first = cfg.get("build_first")
    pos = np.array([p.M[:3, 3] for p in placed])
    cx, cz = (pos[:, 0].min() + pos[:, 0].max()) / 2, (pos[:, 2].min() + pos[:, 2].max()) / 2

    def key(p):
        x, y, z = p.M[:3, 3]
        ang = (math.degrees(math.atan2(x - cx, -(z - cz))) - front_az + 90.0) % 360.0
        phase = 0 if (first and first in p.tags) else 1
        return (phase, p.build_order, order.get((p.owner, p.local_step), p.build_order),
                -round(y / 8.0), round(ang, 1), math.hypot(x - cx, z - cz))

    seq = sorted(range(len(placed)), key=lambda i: key(placed[i]))
    steps: list[list[int]] = []
    last = None
    for i in seq:
        k = key(placed[i])[:3]
        if k != last:
            steps.append([])
            last = k
        steps[-1].append(i)
    n_frames = seg["end"] - seg["start"]
    lead, hold = 6, max(12, int(n_frames * 0.08))
    span = max(1.0, n_frames - lead - hold - DROP_FRAMES)
    w = np.array([len(s) + 1.5 for s in steps])
    edges = np.concatenate([[0.0], np.cumsum(w)]) / w.sum() * span
    appear = np.zeros(len(placed))
    for s, idx in enumerate(steps):
        a, b = edges[s], edges[s + 1]
        # the last part of a step lands as the next step starts
        for j, i in enumerate(idx):
            appear[i] = seg["start"] + lead + a + (b - a) * (j / len(idx))
    return appear, seq, len(steps)


def build_timeline(engine, model, *, booklet: bool = False, fps: int = FPS) -> dict:
    cfg = video_config(model)
    segs = plan_segments(model, booklet, fps)
    seg = {s["name"]: s for s in segs}
    total = segs[-1]["end"]
    front = float(model.meta.get("azimuth_offset", 0.0))

    placed = model.flatten()
    glow_or_lights = bool(model.lights) or bool(model.glow_tags)
    scene = model_scene(engine, model, lights_on=glow_or_lights, placed=placed)
    scene["lights"] = []                      # LEDs are parented to their parts in Blender
    C = corners(engine, placed)

    # -- build -------------------------------------------------------------------------------
    appear, seq, n_steps = build_schedule(model, placed, seg["build"], cfg, front)
    drop = float(cfg.get("drop", DROP))
    dirs = insert_directions(model)
    assert len(dirs) == len(placed)
    offsets = [((d if d is not None else np.array([0.0, -1.0, 0.0])) * drop).tolist() for d in dirs]

    # -- moving groups -----------------------------------------------------------------------
    group_names: list[str] = []
    inst_group = [-1] * len(placed)
    mech = seg.get("mechanism")
    pose_frames, pose_after = [], []
    moving = np.zeros(len(placed), bool)
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
        u = mech_curve(n)
        ident = np.eye(4)
        rest0 = model.pose(0.0)
        settle = int(n * 0.16)                # ease from the build pose into pose(0) meanwhile
        for k in range(n):
            P = model.pose(float(u[k]))
            row = []
            for g in group_names:
                M = np.asarray(P.get(g, ident), float)
                if k < settle and not np.allclose(rest0.get(g, ident), ident):
                    s = float(smootherstep(k / max(1, settle)))
                    M = ident + (np.asarray(rest0.get(g, ident)) - ident) * s
                row.append(M.reshape(-1).tolist())
            pose_frames.append(row)
        pose_after = [np.asarray(rest0.get(g, ident), float).reshape(-1).tolist()
                      for g in group_names]

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
    s0 = seg["build"]["start"]
    s1 = max(s["end"] for s in segs if s["kind"] == "scene")
    nf = s1 - s0
    dim, led = np.ones(nf), np.zeros(nf)
    L = seg.get("lights")
    if L:
        a, n = L["start"] - s0, L["end"] - L["start"]
        f = np.arange(nf)
        dim = 1 - (1 - LIGHTS_DIM) * smootherstep((f - a) / (0.45 * n))
        led = smootherstep((f - a - 0.2 * n) / (0.55 * n))
        if lift_seg:
            b = lift_seg["start"] - s0
            dim = np.where(f >= b, LIGHTS_DIM + (LIFT_DIM - LIGHTS_DIM) *
                           smootherstep((f - b) / (0.5 * (lift_seg["end"] - lift_seg["start"]))),
                           dim)
    leds = []
    for light in model.lights:
        found = model.find(light["part"], placed)
        if found:
            leds.append({"instance": found[0].index, "color": light["color"],
                         "power": float(light["power"]),
                         "offset": [float(v) for v in light.get("offset", (0, 0, 0))]})

    # -- camera ------------------------------------------------------------------------------
    cam = plan_camera(model, segs, seg, front, C, appear, seq, moving, group_names, inst_group,
                      pose_frames, lifted, lift_frames, placed, fps)

    return {
        "fps": fps, "frames": total, "segments": segs, "scene": scene,
        "scene_range": [s0, s1],
        "model": {"name": model.name, "slug": model.slug, "variant": model.variant,
                  "parts": len(placed), "pieces": bom_pieces(engine, model, placed),
                  "steps": n_steps},
        "build": {"appear": appear.tolist(), "drop": DROP_FRAMES, "offset": offsets,
                  "order": seq},
        "camera": cam,
        "groups": {"names": group_names, "instance": inst_group,
                   "start": mech["start"] if mech else 0, "frames": pose_frames,
                   "after": pose_after},
        "lift": {"instance": lifted.tolist(), "start": lift_seg["start"] if lift_seg else 0,
                 "frames": lift_frames},
        "lights": {"leds": leds, "dim": dim.tolist(), "led": led.tolist(), "glow": led.tolist(),
                   "start": s0},
    }


def mech_curve(n: int) -> np.ndarray:
    """Pose parameter per frame: settle, open, hold, close, rest."""
    k = np.arange(n) / max(1, n - 1)
    a, b, c, d = 0.17, 0.5, 0.6, 0.93
    u = np.where(k < a, 0.0, np.where(k < b, smootherstep((k - a) / (b - a)),
                 np.where(k < c, 1.0, 1 - smootherstep((k - c) / (d - c)))))
    return np.clip(u, 0.0, 1.0)


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


def plan_camera(model, segs, seg, front, C, appear, seq, moving, group_names, inst_group,
                pose_frames, lifted, lift_frames, placed, fps) -> dict:
    from scipy.interpolate import PchipInterpolator
    s0 = seg["build"]["start"]
    s1 = max(s["end"] for s in segs if s["kind"] == "scene")
    nf = s1 - s0
    allpts = C.reshape(-1, 3)
    b = seg["build"]

    # how flat the model is: 0 for a cassette lying down, 1 for anything as tall as it is deep.
    # Flat models are seen from higher up (they fill more of the square frame) and their
    # mechanism from above; tall ones get the low 3/4 mechanism shot.
    ext = allpts.max(0) - allpts.min(0)
    tall = float(np.clip((ext[1] / max(1.0, min(ext[0], ext[2])) - 0.25) / (0.8 - 0.25), 0, 1))
    lift_el = 12.0 * (1 - tall)
    mech_el = 24.0 + (3.0 - 24.0) * tall

    # azimuth / elevation keys (degrees, relative to the model's front) ---------------------
    keys: list[tuple[float, float, float]] = []       # (frame, az, el)
    b_az = (-80.0, -30.0)                             # build orbit, round the front
    keys.append((b["start"], b_az[0], 30.0))
    keys.append((b["end"], b_az[1], 22.0))
    sh = seg["showcase"]
    t_show = (sh["end"] - sh["start"]) / fps
    want = max(40.0, 16.0 * t_show)
    after = [s for s in segs if s["kind"] == "scene" and s["start"] >= sh["end"]]
    nxt = after[0]["name"] if after else None
    pref = {"mechanism": (40.0, -40.0), "lights": (12.0,), "lift": (-2.0,)}
    if nxt:
        best = None
        for a in pref[nxt]:
            for k in range(-1, 4):
                end = a - 20.0 + 360.0 * k
                sweep = end - b_az[1]
                if sweep >= 30 and (best is None or abs(sweep - want) < abs(best[0] - want)):
                    best = (sweep, a + 360.0 * k)
        sweep, a_next = best
    else:
        sweep, a_next = want, None
    a_end = b_az[1] + sweep
    keys.append(((sh["start"] + sh["end"]) / 2, b_az[1] + sweep * 0.5, 15.0))
    keys.append((sh["end"], a_end, 18.0))
    last_az = a_end
    move = int(0.9 * fps)
    for s in after:
        n = s["end"] - s["start"]
        m = min(move, n // 3)
        if s["name"] == "mechanism":
            a = a_next if a_next is not None and nxt == "mechanism" else _near(40.0, last_az)
            keys += [(s["start"] + m, a, mech_el), (s["end"], a + 10.0, mech_el + 1.0)]
            last_az = a + 10.0
        elif s["name"] == "lights":
            a = _near(12.0, last_az)
            keys += [(s["start"] + m, a, 13.0), (s["end"], a - 6.0, 11.0)]
            last_az = a - 6.0
        elif s["name"] == "lift":
            a = _near(-2.0, last_az)
            keys += [(s["start"] + m, a, 8.0), (s["end"], a - 10.0, 6.0)]
            last_az = a - 10.0
    kf = np.array([k[0] for k in keys], float)
    frames = np.arange(s0, s1, dtype=float)
    az = PchipInterpolator(kf, [k[1] for k in keys], extrapolate=True)(frames) + front
    el = PchipInterpolator(kf, [k[2] for k in keys], extrapolate=True)(frames)
    nm = seg.get("mechanism")
    el = el + lift_el * np.array([0.0 if nm and nm["start"] <= f < nm["end"] else 1.0
                                  for f in frames])
    el = _gauss(el, 12)
    lens = np.full(nf, LENS)

    target = np.zeros((nf, 3))
    dist = np.zeros(nf)

    # build: frame the parts placed so far (the camera pulls back as the model grows) --------
    order_appear = appear[seq]
    full = np.array([fit(allpts, az[i], el[i])[1] for i in range(0, nf, 5)])
    full_d = np.interp(np.arange(nf), np.arange(0, nf, 5), full)
    nb = b["end"] - b["start"]
    raw_t, raw_d = np.zeros((nb, 3)), np.zeros(nb)
    for k in range(nb):
        f = b["start"] + k
        # frame what will be there a second and a half from now: the camera anticipates
        n = max(int(np.searchsorted(order_appear, f + 45, side="right")), 1)
        pts = C[seq[:n]].reshape(-1, 3)
        raw_t[k], raw_d[k] = fit(pts, az[k], el[k])
        raw_d[k] = max(raw_d[k], 0.55 * full_d[k])
    win = 40
    fwd = np.array([raw_d[k:k + win].max() for k in range(nb)])
    target[:nb] = _gauss(raw_t, 18)
    dist[:nb] = np.maximum(_gauss(fwd, 14), raw_d)

    def blend_in(s, t_goal, d_goal):
        """Ease from the previous frame's framing to the goal arrays over the first second."""
        i0, n = s["start"] - s0, s["end"] - s["start"]
        m = min(move, n // 3)
        w = smootherstep(np.arange(n) / max(1, m))[:, None]
        pt, pd = target[i0 - 1].copy(), dist[i0 - 1]
        target[i0:i0 + n] = pt + (t_goal - pt) * w
        dist[i0:i0 + n] = pd + (d_goal - pd) * w[:, 0]

    for s in [x for x in segs if x["kind"] == "scene" and x["name"] != "build"]:
        i0, n = s["start"] - s0, s["end"] - s["start"]
        idx = np.arange(i0, i0 + n)
        if s["name"] == "showcase":
            fits = [fit(allpts, az[i], el[i]) for i in idx[::4]]
            d_goal = np.full(n, max(f[1] for f in fits))
            t_goal = np.tile(np.mean([f[0] for f in fits], axis=0), (n, 1))
        elif s["name"] == "mechanism":
            pts = [C[moving].reshape(-1, 3)] if moving.any() else [allpts]
            for row in (pose_frames[len(pose_frames) // 2],) if pose_frames else ():
                for gi, g in enumerate(group_names):
                    M = np.array(row[gi]).reshape(4, 4)
                    sel = np.array(inst_group) == gi
                    pts.append(apply(M, C[sel].reshape(-1, 3)))
            mp = np.concatenate(pts)
            # the moving parts and everything above their lowest point (LDraw +Y is down):
            # the mechanism in the context of what it moves, without a stand below it
            low = mp[:, 1].max()
            above = C[C.mean(1)[:, 1] <= low].reshape(-1, 3)
            k = idx[len(idx) // 2]
            tm, dm = fit(np.concatenate([mp, above]), az[k], el[k], margin=1.05)
            tc, _ = fit(mp, az[k], el[k])
            tf, df = fit(allpts, az[k], el[k])
            # tall models: close in on the mechanism (the top may crop); flat ones: whole model
            dm = float(np.clip(dm * (0.85 + 0.3 * (1 - tall)), 0.45 * df, 0.95 * df))
            t_goal = np.tile(tm + (tc - tm) * 0.35 * tall, (n, 1))
            d_goal = dm * (1 - 0.05 * smootherstep(np.arange(n) / n))
        elif s["name"] == "lights":
            glow = [p.index for p in placed if any(t in p.tags for t in model.glow_tags)]
            k = idx[len(idx) // 2]
            tf, df = fit(allpts, az[k], el[k])
            gc = C[glow].reshape(-1, 3).mean(0) if glow else tf
            t_goal = np.tile(tf + (gc - tf) * 0.2, (n, 1))
            d_goal = df * (1.0 - 0.07 * smootherstep(np.arange(n) / n))
        else:  # lift
            H = np.array([np.array(m).reshape(4, 4)[:3, 3] for m in lift_frames])
            top = C.copy()
            top[lifted] = top[lifted] + np.array([0, -max(0.0, -H[:, 1].min()), 0])
            pts = top.reshape(-1, 3)
            fits = [fit(pts, az[i], el[i]) for i in idx[::6]]
            d_goal = np.full(n, max(f[1] for f in fits))
            t_goal = np.tile(np.mean([f[0] for f in fits], axis=0), (n, 1))
        blend_in(s, t_goal, d_goal)

    target = _gauss(target, 5)
    dist = _gauss(dist, 5)
    pos = np.zeros((nf, 3))
    for i in range(nf):
        d, _, _ = view_basis(az[i], el[i])
        pos[i] = target[i] + d * dist[i]
    return {"start": s0, "pos": np.round(pos, 3).tolist(), "target": np.round(target, 3).tolist(),
            "lens": lens.tolist(), "az": np.round(az, 3).tolist(), "el": np.round(el, 3).tolist()}
