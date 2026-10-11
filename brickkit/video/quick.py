"""Quick Bricks: a short vertical build video of a small model for TikTok and Instagram.

    brickkit quick SLUG [--preview] [--set PRESET|random] [--surface S] [--room R] [--light L]
                        [--seed N] [--seconds 14] [--stills 0,90] [--layout|--no-layout]
                        [--remix]

writes models/SLUG/out/SLUG-1080x1920.mp4 (60 fps, H.264 + AAC, about 14 s, made to loop) and
out/quick_poster.jpg. Photoreal (Cycles) in a little workshop - a surface, a room and a
light, mix and match (render/quick_sets.py) - build only: it opens on
the empty set; the pieces fly in from just off frame in instruction order, each over or round
what is built to line up with its place and be pressed home (no bounce), faster and faster -
and it goes together for real (video/assemble.py): no part ever passes through another or
the table, none lands on nothing, a sub-assembly that cannot be built in place is built
beside the model and joined, and what is built is lifted for a piece that goes underneath;
the camera circles low round the model in one smooth orbit that never turns
back, growing with the build - on the front to start, on the side each close-up's part faces
as that part lands (it moves in to macro close-ups on a few landings), quicker round the back,
on the front again to end - then a cut to the empty set (the first frame again: it loops).
A model of a few pieces (layout) starts instead with them all laid out in a tidy grid behind
the build, the camera high over them; one at a time they float up and into place, and the
camera comes down to the build as the grid empties and turns round it once the table is clear.
A crisp click on every landing and a deeper snap on the last (a light music bed under them
with music = true). Nothing else: no titles, cards or graphics - just the render (the Bricks
logo, faint at the top, only with watermark = true).

Configured by model.toml's [quick] (all optional):

    [quick]
    set = "cutting_mat"          # a preset (PRESETS: surface + room + light), or "random"
    surface = "green_mat"        # any layer over the preset's (render/quick_sets.py):
    room = "bookshelf"           #   SURFACES, ROOMS, LIGHTS - any with any
    light = "evening"
    seed = 3                     # for set = "random" (else the model's name): a series varies
    seconds = 14                 # the whole loop
    highlight = ["14769p0m", "3688"]   # parts (numbers or tags) worth a macro close-up, in
                                 # order of preference (else printed parts and the last ones)
    close_ups = 2                # how many (0..3)
    layout = "auto"              # true: every part starts laid out on the table round the
                                 # build, then one at a time they float up and into place;
                                 # false: they fly in from off frame; "auto": laid out if the
                                 # model has under 25 pieces
    music = false                # true: a light music bed under the clicks (off: just the clicks)
    ending = "audio/laugh_1.mp3" # the model's own sound after the last piece (a path in its folder)
    ending_level = -3.0          # its peak, dBFS in the mix (the last snap: -5)
    ending_at = 0.25             # s after the last piece lands

    [[quick.sound]]              # more sounds of the model's own, at moments of the build
    file = "audio/bell_1.mp3"    # (a path in its folder)
    on = ["The clock tower", "14769p0m", "last"]   # when: a step's caption (its first piece
                                 # landing), a part number or tag (the one in a close-up, else
                                 # the first), "first", "last", or a time in seconds
    level = -11.0                # its peak, dBFS in the mix (a click: -9)
    at = 0.0                     # s after each of those moments
    exposure = -1.0              # EV on the render (brighter or darker sets)
    view = "filmic"              # the render's film response: "filmic" (the parts' colours
                                 # true) or "agx" (softer; a bright yellow goes pale orange)
    watermark = false            # true: the Bricks logo, small and faint, top centre
    cover = 0                    # the cover picture (quick_poster.jpg): degrees from the model's
                                 # front it is seen from - the frame of the hero nearest to that
                                 # (45: three-quarters on, for a face that is on the side)
    flex = 3.0                   # s: before the cut the finished model moves - its moving groups
                                 # go through design.py's model.pose (legs walk on the spot; a
                                 # lid opens and shuts again). That long is added before the cut:
                                 # the build keeps its own time only if `seconds` is that much longer

Planning is here (no Blender): `plan(engine, model, cfg)` -> the schedule, each part's moves
(a 4 x 4 transform per frame while it moves), the camera per frame and the sound's cues;
`clashes(engine, placed, plan)` checks a plan's own frames (part against part);
render/blender_quick.py renders the frames; ffmpeg encodes them with the logo and the sound.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import subprocess
import time
from pathlib import Path

import numpy as np

from .. import paths
from . import assemble as A
from . import timeline as T

FPS = 60              # the finals: the top rate Reels and TikTok take (every timing is in s)
SIZE = (1080, 1920)
QUICK = {"set": "cutting_mat", "seconds": 14.0, "highlight": [], "close_ups": 2, "music": False,
         "ending": None, "ending_level": -3.0, "ending_at": 0.25, "sound": [], "layout": "auto",
         "cover": 0.0, "flex": 0.0,
         "view": "filmic",
         "lens": 50.0, "samples": 32, "exposure": -1.0, "watermark": False}
# the workshop's layers (render/quick_sets.py builds them), any with any, and named combos
SURFACES = ("blue_mat", "green_mat", "kraft", "oak", "baseplate",
            "lego_yellow", "lego_blue", "lego_green", "lego_red")
ROOMS = ("workbench", "studio", "window", "night", "bookshelf")
LIGHTS = ("morning", "day", "evening")
PRESETS = {"cutting_mat": ("blue_mat", "workbench", "morning"),
           "linen": ("kraft", "window", "day"),
           "studio": ("green_mat", "studio", "day"),
           "night_shift": ("oak", "night", "evening"),
           "reading_nook": ("baseplate", "bookshelf", "morning"),
           "yellow_floor": ("lego_yellow", "studio", "day"),       # (the LEGO floors: an endless
           "blue_floor": ("lego_blue", "bookshelf", "day"),        # studded mat in one colour)
           "green_floor": ("lego_green", "window", "day"),
           "red_floor": ("lego_red", "workbench", "morning")}
SETS = tuple(PRESETS) + ("random",)
PRE = 0.45            # s of the empty set before the first part flies in
HERO = 2.0            # s from the last landing to the cut
FLEX_HOLD = 0.4       # s the model stands still again after its own movement ([quick] flex), to the cut
FLEX_OUT = 0.4        # of that movement's time: out to the pose's end (a lid open), and as long back
TAIL = 0.3            # s of the empty set after the cut (it runs on into the first frame)
RATE_RAMP = 3.2       # the last parts land this many times as often as the first
FLIGHT = (0.45, 0.24)  # s a part takes to fly in: the first, the last ones
SETTLE = 0.2          # s a part is held after it lands (what was lifted for it set down)
CLICK = 4.0           # LDU short of its place: where a part lines up before it is pressed home
PRESS = 0.86          # of its time: when it is lined up there (the rest is the press)
LIFT = 0.3            # of a piece's time: what is built is lifted clear for it by then
UNDER = (0.68, 0.72)  # of its time: a piece that goes underneath is in place; the set-down starts
LATER = (0.0, 0.05, 0.1, 0.17, 0.25, 0.37)   # s: how much later a piece may come, to keep clear
                      # of another that is still in the air
SLOW = {"join": (0.9, 0.2, 0.7), "under": (0.95, 0.2, 0.75), "lift": (0.65, 0.2, 0.45)}   # s
                      # before, after and for: a unit joined, the build set down on a piece, or
                      # lifted for one (before: its own time and the last piece's settling)
CLOSE = (0.6, 0.55)   # s of the build held round a close-up's landing: before, after
SWING = 0.45          # s the camera takes to move in to (and out of) a close-up
ORBIT = (16.0, 46.0)  # degrees a second the camera circles at: early in the build, late
SLOWEST = 4.0         # degrees a second: it never quite stops (and never turns back)
DRIFT = 6.0           # degrees a second: the drift through a close-up
FACING = (22.0, 60.0)  # degrees: in a close-up the camera is within this of the way the part
                       # faces - a part that goes on sideways, one that goes on from above
OFF_FACE = 20.0       # degrees further round than that: no close-up is made on the part
FASTEST = 110.0       # degrees a second: the most the orbit averages between two close-ups
ROUND = 300.0         # degrees: the orbit goes at least this far round (it shows every side)
CLOSE_EL = 17.0       # degrees: a close-up's camera above its part
CLOSER = 0.8          # a close-up is never further off than this share of the orbit's distance
# laid out: the build starts with every part on the table in a tidy grid behind the build, then
# one at a time they float up and into place ([quick] layout: true, false, or "auto" - under
# LAYOUT_UNDER)
LAYOUT_UNDER = 25     # pieces: a model with fewer starts laid out (layout = "auto")
LAYOUT_PRE = 1.2      # s to take the laid-out parts in before the first one lifts
LAYOUT_HERO = 3.2     # s from the last landing to the cut then: the camera's turn round the
                      # model is all at the end, once the table is clear
LAYOUT_CALM = 0.4     # the orbit's pace until then, as a share of ORBIT
FLOAT = (0.85, 0.6)   # s a laid-out part takes to float up and in: the first, the last ones
LAYOUT_GAP = (12.0, 16.0)   # LDU between neighbours in a row of the grid, between rows
LAYOUT_CLEAR = 36.0   # LDU from the build's footprint to the nearest row
LAYOUT_ROWS = (2, 8)  # how many rows: at least, at most
LAYOUT_EL = 55.0      # degrees: the camera above the table while the parts are laid out
LAYOUT_OPENING = -10.0   # degrees from the front: where the orbit starts then - square on to
                      # the grid, as it passes the front
LAYOUT_STOP = 16.0    # the most the lens stops down for that shot (f-number: more is sharp)
LAYOUT_HOLD = 0.2     # the share of the parts that lift before the camera starts down (it is down
                      # at the model when none are left)
OPENING = -35.0       # degrees from the front: where the orbit starts
LAST_LOOK = (25.0, 20.0)   # degrees from the front (either side), give or take: where it ends
BACK_PACE = 0.35      # how much faster it passes the back than the front (0: the same)
ELEVATION = (11.0, 19.0)   # degrees: the camera low by the table, rising a little with the build
MARGIN = 1.1          # air round the finished model in the frame (tighter on the base at first)
RELEASE = 0.5         # of its distance a second: how fast the camera closes in again once a unit
                      # built beside the model has joined it (it goes out for one at once)
HERO_WIDE = 1.15      # the camera this much further back than the finished model needs (it was
HERO_IN = 0.9         # framing units built beside it): it moves in for the hero, over this long (s)
TILT = 26.0           # degrees a part tumbles in its flight, straightening as it lands
SOUNDS = {"click": [f"click_{k}.mp3" for k in range(1, 7)], "snap": "snap_1.mp3",
          "swish": "swish_1.mp3", "bed": "bed_2.mp3"}
SOUND_LEVEL = {"click": -9.0, "snap": -5.0, "swish": -26.0}   # peak dBFS over the music
MUSIC_GAIN = -4.0     # dB: the music bed under the clicks (they're the point)
LUFS = -14.0          # loudness for phones (the reels' -16 is a little quiet there)
TRUE_PEAK = -5.0      # dBTP for the mix: AAC adds up to ~4 dB over the clicks' sharp attacks
MAX_MB = 50.0
QUALITY = {"full": {"size": SIZE, "fps": FPS, "samples": None, "crf": 18, "maxrate": "20000k"},
           "preview": {"size": (540, 960), "fps": 15, "samples": 16, "crf": 24, "maxrate": "3000k"}}


# ---------------------------------------------------------------------------- config
def quick_config(config: dict, over: dict | None = None, slug: str = "") -> dict:
    """model.toml's [quick] over QUICK (and `over`, the command line's), with the workshop's
    layers resolved: the preset's (or for set = "random", picked by `seed`, else by the model's
    `slug`) under any surface, room or light given."""
    out = dict(QUICK)
    out.update(config.get("quick") or {})
    out.update({k: v for k, v in (over or {}).items() if v is not None})
    if out["set"] not in SETS:
        raise SystemExit(f"unknown quick set {out['set']!r}; choose from {', '.join(SETS)}")
    seed = out.get("seed")
    if seed is None:
        seed = int(hashlib.sha1(str(slug or config.get("model", {}).get("name", "")).encode()).hexdigest()[:8], 16)
    out["seed"] = int(seed)
    if out["set"] == "random":
        rng = np.random.default_rng(int(seed))
        base = (SURFACES[rng.integers(len(SURFACES))], ROOMS[rng.integers(len(ROOMS))],
                LIGHTS[rng.integers(len(LIGHTS))])
    else:
        base = PRESETS[out["set"]]
    for key, default, names in (("surface", base[0], SURFACES), ("room", base[1], ROOMS),
                                ("light", base[2], LIGHTS)):
        out[key] = out.get(key) or default
        if out[key] not in names:
            raise SystemExit(f"unknown quick {key} {out[key]!r}; choose from {', '.join(names)}")
    out["close_ups"] = int(np.clip(int(out["close_ups"]), 0, 3))
    if out["layout"] not in (True, False, "auto"):
        raise SystemExit('[quick] layout: true, false or "auto"')
    if out["view"] not in ("filmic", "agx"):
        raise SystemExit('[quick] view: "filmic" or "agx"')
    if float(out["seconds"]) < 6:
        raise SystemExit("[quick] seconds: at least 6")
    try:
        out["cover"] = float(out["cover"])
    except (TypeError, ValueError):
        raise SystemExit("[quick] cover: degrees from the front, e.g. 0 or 45")
    if out.get("last_look") is not None:
        try:
            a, tol = (float(v) for v in out["last_look"])
        except (TypeError, ValueError):
            raise SystemExit("[quick] last_look: [degrees from the front, give or take], e.g. [0, 12]")
        out["last_look"] = (a, tol)
    return out


# ---------------------------------------------------------------------------- the order
def build_sequence(model, placed) -> list[int]:
    """Instruction order: by step (sub-assemblies as they are used), then as placed."""
    order = {k: i for i, k in enumerate(model.instruction_order())}
    return sorted(range(len(placed)), key=lambda i: (placed[i].build_order,
                                                      order.get((placed[i].owner, placed[i].local_step), 0),
                                                      i))


PRINTED = re.compile(r"^\d+[a-z]?p[0-9a-z]+(\.dat)?$")


def highlight_groups(placed, seq, cfg) -> list[list[int]]:
    """Candidates for the close-ups, by preference: each [[highlight]] entry's parts (a part
    number, with or without its .dat, or a tag), else printed parts, then the last parts, each
    group in build order."""
    def strip(p):
        return p[:-4] if p.endswith(".dat") else p
    groups = []
    for h in cfg.get("highlight") or []:
        g = [i for i in seq if strip(placed[i].part) == strip(str(h)) or str(h) in placed[i].tags]
        if g:
            groups.append(g)
    if not cfg.get("highlight"):
        printed = {}
        for i in seq:
            if PRINTED.match(placed[i].part):
                printed.setdefault(strip(placed[i].part), []).append(i)
        groups += list(printed.values())
        groups += [[seq[-2]], [seq[-1]]] if len(seq) > 2 else []
    return groups


# ---------------------------------------------------------------------------- the schedule
def schedule(n: int, seconds: float, highlights: list[int] | None = None, fps: int = FPS,
             laid: bool = False, slow: dict | None = None, flex: float = 0.0) -> dict:
    """When each part (in build order, 0..n-1) lands and how long it flies (s): the first after
    PRE s of the empty set, the rest faster and faster (RATE_RAMP), a pause before the last one,
    and CLOSE s of room round each highlighted landing (positions in the order); the last
    landing HERO s before the cut, the cut TAIL s before the end. `laid` (the parts start laid
    out on the table): LAYOUT_PRE s to look at them first, slower flights (FLOAT) and a longer
    hero (LAYOUT_HERO). `slow` {position: (s before it lands, s after, s it takes)}: what needs
    the table to itself (the build lifted for a piece, a unit joined): nothing else lands in
    that time, and it does not start until a close-up just before it is over (the camera
    would be left looking at where the unit was). `flex` (s): that much longer from the last
    landing to the cut, for the finished model to move in ([quick] flex)."""
    highlights = sorted(set(highlights or []))
    u = np.arange(n) / max(1, n - 1)
    pre, fly, hero = (LAYOUT_PRE, FLOAT, LAYOUT_HERO) if laid else (PRE, FLIGHT, HERO)
    hero += float(flex)
    flight = fly[0] + (fly[1] - fly[0]) * u
    gaps = 1.0 / (1.0 + (RATE_RAMP - 1.0) * u ** 1.4)     # relative, before each landing
    gaps[0] = 0.0
    fixed = np.zeros(n)
    if n > 1:
        gaps[-1] *= 3.0                                     # a beat before the last piece
        flight[-1] = max(0.5, flight[-1])
    for h in highlights:
        flight[h] = max(flight[h], 0.42)
        fixed[h] = max(fixed[h], CLOSE[0])
        if h + 1 < n:
            fixed[h + 1] = max(fixed[h + 1], CLOSE[1])
    for h, (before, after, takes) in (slow or {}).items():
        flight[h] = max(flight[h], takes)
        if h > 0:
            fixed[h] = max(fixed[h], before)
        if h + 1 < n:
            fixed[h + 1] = max(fixed[h + 1], after)
    for h in highlights:                               # what is built keeps still till a close-up
        if h + 1 in (slow or {}):                      # is over: a lift or a join waits for it
            fixed[h + 1] = max(fixed[h + 1], CLOSE[1] + flight[h + 1])
    span = seconds - pre - hero - TAIL - flight[0]
    free = span - fixed.sum()
    if free <= 0.05 * n or span <= 0:
        raise SystemExit(f"{n} parts don't fit in {seconds:g} s: make [quick] seconds longer")
    rel = np.where(fixed > 0, 0.0, gaps)
    k = free / rel.sum() if rel.sum() > 0 else 0.0
    g = np.where(fixed > 0, np.maximum(fixed, gaps * k), gaps * k)
    loose = (fixed == 0) & (g > 0)                     # the fixed gaps are kept whole: the others
    if loose.any() and g[~loose].sum() < span - 0.03 * loose.sum():     # give (or take) the rest
        g[loose] *= (span - g[~loose].sum()) / g[loose].sum()
    g = g * (span / g.sum()) if g.sum() > 0 else g
    land = pre + flight[0] + np.cumsum(g)
    cut = land[-1] + hero
    return {"land": land, "flight": flight, "launch": land - flight, "cut": cut,
            "end": seconds, "frames": int(round(seconds * fps)), "highlights": highlights}


# ---------------------------------------------------------------------------- the camera
def view_dir(az: float, el: float) -> np.ndarray:
    """From the target to the camera (LDraw, -Y up; az 0 looks at the front, -Z)."""
    return T.view_basis(az, el)[0]


def basis(d: np.ndarray):
    """(right, up) of a camera looking along -d (d from the target to the camera)."""
    f = -d
    up = np.array([0.0, -1.0, 0.0])
    u = up - f * float(up @ f)
    u /= np.linalg.norm(u) + 1e-12
    r = np.cross(f, u)
    return r, u


def tangents(lens: float, size=SIZE) -> tuple[float, float]:
    """tan of the half fields of view (horizontal, vertical): the 36 mm sensor on the frame's
    height (Blender's sensor fit VERTICAL)."""
    ty = 18.0 / lens
    return ty * size[0] / size[1], ty


def frame_distance(points, target, d, lens: float, margin: float = MARGIN, size=SIZE) -> float:
    """How far along d from `target` the camera must be to hold `points` in the frame."""
    tx, ty = tangents(lens, size)
    r, u = basis(d)
    c = np.asarray(points, float) - target
    cd = c @ d
    return float(max((cd + margin * np.abs(c @ r) / tx).max(), (cd + margin * np.abs(c @ u) / ty).max()))


def azimuth(d) -> float:
    """The azimuth (degrees, 0 = from the front, -Z) of a direction from the target."""
    return math.degrees(math.atan2(float(d[0]), -float(d[2])))


def facing(Ci, C, axis, front: float = 0.0) -> tuple[np.ndarray, float]:
    """(horizontal unit vector to see a part from, how far off that the camera may be in
    degrees): the way it faces if it goes on sideways (an eye, a clock); else between the
    side of the model it is on and the model's front - the face, not the back - or from
    anywhere if it is in the model's middle (a spire)."""
    a = np.asarray(axis, float) * [1, 0, 1]
    if np.linalg.norm(a) > 0.5:
        return a / np.linalg.norm(a), FACING[0]
    f = view_dir(front, 0.0)
    allp = C.reshape(-1, 3)
    half = (allp.max(0) - allp.min(0)) / 2
    r = (Ci.mean(0) - (allp.min(0) + allp.max(0)) / 2) * [1, 0, 1]
    if np.linalg.norm(r) < 0.25 * max(half[0], half[2]):
        return f, 180.0
    f = f + 0.6 * r / np.linalg.norm(r)
    return f / np.linalg.norm(f), FACING[1]


def _pick(centres, tol: float, want: float, least: float) -> float:
    """The azimuth nearest `want` that is within `tol` of one of `centres` (plus any number
    of whole turns) and not under `least`."""
    best = None
    for c in centres:
        c0 = T._near(c, want)
        for n in (-1, 0, 1, 2):
            lo, hi = c0 + 360.0 * n - tol, c0 + 360.0 * n + tol
            if hi < least:
                continue
            z = min(max(want, lo, least), hi)
            if best is None or abs(z - want) < abs(best - want) - 1e-9:
                best = z
    return least if best is None else best


def orbit(t: np.ndarray, sch: dict, windows: list, faces: list, front: float,
          opening: float = OPENING, calm: float | None = None, last=None) -> np.ndarray:
    """The camera's azimuth per frame (degrees): one smooth orbit that only ever goes one
    way. It opens on the front's three-quarter view (`opening`), circles slowly at first and faster as
    the build speeds up (ORBIT), is where each close-up's part faces when that part lands
    (`faces`: an (azimuth, give or take) per window) and drifts through the close-up, passes
    the back faster than the front, and ends on the front's three-quarter view at the cut.
    Between those it eases: no stops, no turning back. (Two close-ups too close together to
    get round in at FASTEST: the second is seen from as far round as it gets. Close-ups all on
    one side: a whole turn more between two of them, so the back is seen too.) `calm` (s:
    parts lie on the table round the build until then): it only drifts (LAYOUT_CALM) across
    the front till then - no flying low over them - and makes its turn after, to the cut."""
    from scipy.interpolate import PchipInterpolator
    land, cut = sch["land"], float(sch["cut"])

    def pace(a, b):
        x = np.linspace(a, b, 16)
        prog = np.interp(x, land, np.linspace(0, 1, len(land)), left=0.0, right=1.0)
        w = float(np.mean(ORBIT[0] + (ORBIT[1] - ORBIT[0]) * T.smootherstep(prog)))
        return w * (LAYOUT_CALM if calm is not None and b <= calm + 1e-6 else 1.0)

    keys, free = [(0.0, front + opening)], []          # free: the stretches between close-ups
    for (a, b, _), (c, tol) in zip(windows, faces):
        t0, z0 = keys[-1]
        if len(keys) > 1 and a - t0 < 0.6 and abs(T._near(c, z0) - z0) <= tol:
            keys[-1] = (b, z0 + DRIFT * (b - t0))      # straight on from the last close-up
            continue
        a = max(a, t0 + 0.1)
        m = max((a + b) / 2, a + 0.05)
        b = max(b, m + 0.05)
        quiet = 0.5 if calm is not None and b <= calm + 1e-6 else 1.0
        lead = DRIFT * quiet * (m - a)
        least = z0 + SLOWEST * quiet * (a - t0) + lead
        z = _pick([c], tol, z0 + pace(t0, a) * (a - t0) + lead, least)
        if calm is not None and a <= calm and z - z0 > 150.0:
            z = least                                  # (no turn yet: from where the drift is)
        z = max(least, (z + T._near(c, z)) / 2)        # halfway from there to face on
        z = min(z, z0 + FASTEST * (a - t0) + lead)
        free.append(len(keys) - 1)
        keys += [(a, z - lead), (b, z + DRIFT * quiet * (b - m))]
    t0, z0 = keys[-1]
    if calm is not None and t0 + 0.5 < calm < cut - 1.0:       # still drifting till the table is clear
        keys.append((calm, z0 + pace(t0, calm) * (calm - t0)))
        t0, z0 = keys[-1]
    if cut > t0 + 0.1:
        speed = pace(t0, cut) if not windows else 0.5 * (ORBIT[0] + ORBIT[1])
        look = LAST_LOOK if last is None else last     # ([quick] last_look, for a model that is
        z = _pick([front + look[0], front - look[0]], look[1],    # poor from some of that) (it may all
                  z0 + speed * (cut - t0), z0 + 0.5 * SLOWEST * (cut - t0))       # but stay)
        free.append(len(keys) - 1)
        keys.append((cut, min(z, z0 + FASTEST * (cut - t0))))
    if keys[-1][1] - keys[0][1] < ROUND and free:      # it shows every side: a whole turn more,
        turn = lambda j: (keys[j + 1][1] - keys[j][1] + 360.0) / (keys[j + 1][0] - keys[j][0])  # noqa: E731
        j = min(free, key=turn) if calm is None else free[-1]   # where there is most time for it
        if turn(j) <= 1.15 * FASTEST:
            keys = keys[:j + 1] + [(tk, z + 360.0) for tk, z in keys[j + 1:]]
    # on a long way round, knots every 45 degrees: more time at the front, less at the back
    knots = [keys[0]]
    for (t0, z0), (t1, z1) in zip(keys, keys[1:]):
        if z1 - z0 > 100.0:
            G = lambda z: math.radians(z - z0) + BACK_PACE * (                 # noqa: E731
                math.sin(math.radians(z - front)) - math.sin(math.radians(z0 - front)))
            for z in np.arange(z0 + 45.0, z1 - 22.5, 45.0):
                knots.append((t0 + (t1 - t0) * G(z) / G(z1), float(z)))
        knots.append((t1, z1))
    tk, zk = np.array(knots).T
    fps = 1.0 / float(t[1] - t[0])
    n = int(np.searchsorted(t, tk[-1], side="right"))          # (after the cut: the last look)
    pad = int(fps)
    z = np.pad(PchipInterpolator(tk, zk)(t[:n]), pad, mode="reflect", reflect_type="odd")
    z = T._gauss(z, 0.15 * fps)[pad:-pad]                      # no sudden starts or stops
    return np.concatenate([z, np.full(len(t) - n, z[-1])])


def plan_camera(model, placed, C, seq, sch: dict, groups: list[list[int]], cfg: dict, axes,
                fps: int = FPS, size=SIZE, laid: dict | None = None, final=None,
                sure: bool = False, home=None) -> dict:
    """The camera per frame: one smooth orbit low round the model (orbit(): it starts on the
    front's three-quarter view and never turns back), framing what is built so far (and
    growing with it), moving in to a macro close-up on up to `close_ups` landings - per group
    the part that faces the camera best as it lands, the orbit timed to be on that part's
    side then - and holding there (from one close-up straight into the next if they come
    close together); then out, to end on the front. `sure` (the schedule has room round the
    close-ups by now): none on a part the orbit cannot be round to in time, which would be
    seen edge on (face_on()). `home` (s, per part: when it is on the model): with units built
    beside the model, the shot takes in a unit's place on the table only until the unit has
    joined, then closes in on the model again (RELEASE): with every place a unit was ever
    built kept in the shot, a model of many sections was a speck in the middle of them. `laid` (lay_out(): the parts start laid
    out on the table): it starts high (LAYOUT_EL) in front, on the build's place and the whole
    grid behind it, stopped down to keep them sharp; it frames the build and what still lies
    there, so it closes in and comes down as the grid empties, drifting across the front, and
    makes its turn once the table is clear. Its close-ups are only on parts that land once
    half the grid has gone (no diving in and out of the wide shot). `C`: every part's corners
    where it lands (a unit built beside the model, the build standing lower on the table than
    it will); `final`: where they end up (else the same) - the hero's frame.
    Returns {pos, target, lens, focus, fstop (per frame, LDraw / mm), windows [[t0, t1,
    part]], az}."""
    n = sch["frames"]
    t = np.arange(n) / fps
    lens0 = float(cfg["lens"])
    front = float(model.meta.get("azimuth_offset", 0.0))
    opening = OPENING if laid is None else LAYOUT_OPENING
    calm = None if laid is None else float(sch["launch"][max(0, len(seq) - 3)])   # all but lifted
    last = cfg.get("last_look")                        # where the orbit ends, if not LAST_LOOK
    land = sch["land"]
    order_of = {i: k for k, i in enumerate(seq)}
    # close-ups: in group order, the part facing the camera best when it lands
    face = {i: facing(C[i], C, axes[i], front) for g in groups for i in g}
    windows = []

    def face_on(ws) -> bool:
        """With these close-ups, is each one's part seen from near enough the way it faces?
        The orbit only goes one way and no faster than FASTEST, so two parts that face
        different ways and land a moment apart cannot both be (a bolt on a figure's side, then
        its eye); nor one that faces the back while parts still lie on the table (`calm`)."""
        ws = sorted(ws)
        az = orbit(t, sch, ws, [(azimuth(face[i][0]), face[i][1]) for _, _, i in ws], front, opening, calm,
                   last)
        for _, _, i in ws:
            z = float(az[min(n - 1, int(land[order_of[i]] * fps))])
            if abs(T._near(azimuth(face[i][0]), z) - z) > face[i][1] + OFF_FACE:
                return False
        return True

    if cfg["close_ups"] > 0:
        az0 = orbit(t, sch, [], [], front, opening, calm, last)    # the orbit left to itself
        for g in groups:
            if len(windows) >= cfg["close_ups"]:
                break
            ranked = []
            for at, i in enumerate(g):                 # (of equals, the later one)
                k = order_of[i]
                if laid is not None and k < len(seq) / 2:
                    continue
                f = min(n - 1, int(land[k] * fps))
                dcam = view_dir(az0[f], 15.0) * [1, 0, 1]
                dcam /= np.linalg.norm(dcam) + 1e-12
                a = land[k] - CLOSE[0] + 0.05
                b = land[k] + CLOSE[1] - 0.05
                if k + 1 == len(seq) - 1 and land[-1] - land[k] < 1.0:     # hold for the last piece
                    b = land[-1] + 0.4
                ranked.append((round(float(face[i][0] @ dcam), 6), at, [a, b, i]))
            for _, _, w in sorted(ranked, reverse=True):
                if not sure or face_on(windows + [w]):     # (else it would be seen edge on, or
                    windows.append(w)                      # from behind: no close-up is better)
                    break
    windows.sort()
    az = orbit(t, sch, windows, [(azimuth(face[i][0]), face[i][1]) for _, _, i in windows], front,
               opening, calm, last)
    # what is built (or flying in) at each frame frames the shot; never less than the first
    # part and half the model
    built = np.zeros((n, 2, 3))
    allp = (C if final is None else final).reshape(-1, 3)
    lo_all, hi_all = allp.min(0), allp.max(0)
    beside = home is not None and final is not None and float(       # (across the table: a build
        np.abs((C - final)[..., [0, 2]]).max()) > 10.0             # only lifted is not "beside")
    mid = (lo_all + hi_all) / 2
    half = (hi_all - lo_all) / 2
    ground, tall = hi_all[1], hi_all[1] - lo_all[1]           # (LDraw: -Y up)
    least_lo = np.array([mid[0] - 0.55 * half[0], ground - 0.3 * tall, mid[2] - 0.55 * half[2]])
    least_hi = np.array([mid[0] + 0.55 * half[0], ground, mid[2] + 0.55 * half[2]])
    for f in range(n):
        tf = f / fps
        sel = [i for k, i in enumerate(seq) if sch["launch"][k] <= tf + 0.25] or [seq[0]]
        q = C[sel].reshape(-1, 3)
        if beside:                                     # (each part where it is by now)
            q = np.concatenate([final[i] if tf >= home[i] + 0.15 else C[i] for i in sel])
        built[f] = [q.min(0), q.max(0)]
    lo = np.minimum(built[:, 0], least_lo)
    hi = np.maximum(built[:, 1], least_hi)
    if not beside:                                     # (it only ever grows)
        lo, hi = np.maximum.accumulate(-lo, axis=0) * -1, np.maximum.accumulate(hi, axis=0)
    height = np.clip(np.maximum.accumulate(hi[:, 1] - lo[:, 1]) / max(1e-6, hi_all[1] - lo_all[1]), 0, 1)
    el = ELEVATION[0] + (ELEVATION[1] - ELEVATION[0]) * height
    t_h = max([float(sch.get("last", land[-1]))] + [b for _, b, _ in windows])
    hero = t >= t_h
    el = np.where(hero, ELEVATION[1] + 1.0, el)
    wide = np.zeros(n)                                 # 1: on the laid-out parts, 0: on the build
    if laid is not None:                               # high over the grid, down as it empties
        left = np.array([(np.asarray(sch["launch"]) > x).mean() for x in t])
        wide = np.clip(T._gauss(left, 0.6 * fps) / max(1e-6, 1 - LAYOUT_HOLD), 0, 1)
        wide = T.smootherstep(wide) * (~hero)
        el = el + (LAYOUT_EL - el) * wide
        lying = [laid["corners"][[k for k in range(len(seq)) if sch["launch"][k] > f / fps - 0.1]]
                 .reshape(-1, 3) for f in range(n)]
    pos, tgt, lens, foc, fstop = (np.zeros((n, 3)), np.zeros((n, 3)), np.full(n, lens0),
                                  np.zeros((n, 3)), np.zeros(n))
    dist = np.zeros(n)
    for f in range(n):
        box = np.array([[x, y, z] for x in (lo[f, 0], hi[f, 0]) for y in (lo[f, 1], hi[f, 1])
                        for z in (lo[f, 2], hi[f, 2])])
        if hero[f]:
            box = np.array([[x, y, z] for x in (lo_all[0], hi_all[0]) for y in (lo_all[1], hi_all[1])
                            for z in (lo_all[2], hi_all[2])])
        d = view_dir(az[f], el[f])
        c = (box.min(0) + box.max(0)) / 2
        tgt[f] = c
        mg = 1.0 + (MARGIN - 1.0) * (1.0 if hero[f] else height[f])      # tight on the base first
        dist[f] = frame_distance(box, c, d, lens0, mg, size)
    # smooth, and never closer than it was (the shot grows with the build), until the hero:
    # then on the finished model, if the shot had grown for more than that
    tgt = np.stack([T._gauss(tgt[:, a], (0.6 if beside else 0.35) * fps) for a in range(3)], 1)
    need = float(dist[hero].max()) if hero.any() else 0.0      # the finished model, from any side
    if beside:                                         # out at once for a unit's place, in again
        for f in range(1, n):                          # slowly once it has joined
            dist[f] = max(dist[f], dist[f - 1] * (1.0 - RELEASE / fps))
    else:
        dist = np.maximum.accumulate(dist)
    k = int(np.argmax(hero)) if hero.any() else 0
    if k > 0 and dist[k - 1] > HERO_WIDE * need:       # the camera was back for units built
        ease = T.smootherstep(np.clip((t[k:] - t[k]) / HERO_IN, 0, 1))     # beside the model: in
        dist[k:] = dist[k - 1] + (need - dist[k - 1]) * ease               # again for the hero
    dist = T._gauss(dist, 0.3 * fps)
    if laid is not None:                               # from on high: the build's place and all
        far, mid_w = np.zeros(n), np.zeros((n, 3))     # that still lies behind it
        for f in range(n):
            box = np.array([[x, y, z] for x in (lo[f, 0], hi[f, 0]) for y in (lo[f, 1], hi[f, 1])
                            for z in (lo[f, 2], hi[f, 2])])            # what is built so far
            box = np.concatenate([lying[f], box]) if len(lying[f]) else box
            mid_w[f] = (box.min(0) + box.max(0)) / 2
            mid_w[f, 1] = ground - 0.5 * laid["tall"]
            far[f] = frame_distance(box, mid_w[f], view_dir(az[f], LAYOUT_EL), lens0, 1.06, size)
        far = T._gauss(far, 0.5 * fps)
        mid_w = np.stack([T._gauss(mid_w[:, a], 0.5 * fps) for a in range(3)], 1)
        tgt += (mid_w - tgt) * wide[:, None]
        dist += (far - dist) * wide
    for f in range(n):
        d = view_dir(az[f], el[f])
        pos[f] = tgt[f] + d * dist[f]
    foc[:] = tgt
    # the close-ups: in along the orbit (the camera stays on the orbit's azimuth: only its
    # distance and height change, and it turns to look at the part), hold, out again
    axis = tgt.copy()                                  # what the orbit goes round
    sin_c, cos_c = math.sin(math.radians(CLOSE_EL)), math.cos(math.radians(CLOSE_EL))
    for a, b, i in windows:
        c_part = C[i].mean(0)
        r_part = float(np.linalg.norm(C[i].max(0) - C[i].min(0))) / 2
        lz = lens0 * 1.3
        tx, ty = tangents(lz, size)
        r_c, u_c = basis(view_dir(az[min(n - 1, int(round((a + b) / 2 * fps)))], CLOSE_EL))
        q = C[i] - c_part                              # a third of the frame wide (or tall)
        dcl = max(float(np.abs(q @ r_c).max()) / (0.34 * tx), float(np.abs(q @ u_c).max()) / (0.34 * ty),
                  2.2 * r_part + 30.0)
        sw = SWING * (1 + 2 * float(wide[min(n - 1, int(a * fps))]))   # (a longer way in from on high)
        ff = (t >= a - sw) & (t <= b + sw)
        for f in np.nonzero(ff)[0]:
            wgt = T.smootherstep((t[f] - (a - sw)) / sw) * (1 - T.smootherstep((t[f] - b) / sw))
            if wgt <= 0:
                continue
            dh = view_dir(az[f], 0.0)                               # out from the orbit's axis
            v = (c_part - axis[f]) * [1, 0, 1]
            along = float(dh @ v)
            dc = min(dcl, CLOSER * dist[f])            # (a big part of a small model: still in)
            out = along + math.sqrt(max(0.0, along * along - float(v @ v) + (dc * cos_c) ** 2))
            pc = np.array([axis[f][0], c_part[1] - dc * sin_c, axis[f][2]]) + dh * out
            pos[f] = pos[f] + (pc - pos[f]) * wgt
            tgt[f] = tgt[f] + (c_part - tgt[f]) * wgt
            foc[f] = foc[f] + (c_part - foc[f]) * wgt
            lens[f] = lens[f] + (lz - lens[f]) * wgt
    # the empty set's last frames run on into the first: the opening's camera, earlier
    cut_f = int(round(sch["cut"] * fps))
    if cut_f < n:
        k = n - cut_f
        v = pos[1] - pos[0]
        for j in range(k):
            pos[cut_f + j] = pos[0] - v * (k - j)
            tgt[cut_f + j] = tgt[0]
            foc[cut_f + j] = foc[0]
            lens[cut_f + j] = lens[0]
    # depth of field: the model (or the part) sharp, everything round it melting away; the
    # focus as deep as the model, narrowing to the part as the camera swings in
    close = np.zeros(n)
    for a, b, _ in windows:
        close = np.maximum(close, T.smootherstep((t - (a - SWING)) / SWING)
                           * (1 - T.smootherstep((t - b) / SWING)))
    model_depth = 0.5 * float(np.linalg.norm(hi_all - lo_all)) / 2
    for f in range(n):
        s = float(np.linalg.norm(foc[f] - pos[f]))
        depth = model_depth + (24.0 - model_depth) * close[f]
        fstop[f] = dof_fstop(lens[f], s * 0.4, depth * 0.4)
        if wide[f] > 1e-4:                             # the laid-out parts: all of them sharp
            deep = dof_fstop(lens[f], s * 0.4, 0.5 * (laid["b"] + 80.0) * 0.4, most=LAYOUT_STOP)
            fstop[f] += (deep - fstop[f]) * wide[f]
    return {"pos": pos, "target": tgt, "lens": lens, "focus": foc, "fstop": fstop,
            "windows": windows, "az": az}


def outward(Ci, C, axis) -> np.ndarray:
    """Horizontal unit vector a part faces out to: its insertion axis if that is sideways, else
    from the model's middle out to it."""
    a = np.asarray(axis, float) * [1, 0, 1]
    if np.linalg.norm(a) > 0.5:
        return a / np.linalg.norm(a)
    allp = C.reshape(-1, 3)
    mid = (allp.min(0) + allp.max(0)) / 2
    r = (Ci.mean(0) - mid) * [1, 0, 1]
    if np.linalg.norm(r) < 1e-6:
        return np.array([0.0, 0.0, -1.0])
    return r / np.linalg.norm(r)


def dof_fstop(lens: float, s_mm: float, depth_mm: float, coc: float = 0.05, most: float = 6.3) -> float:
    """The f-number that keeps `depth_mm` either side of the focus (at s_mm) acceptably sharp
    (circle of confusion `coc` mm on the 36 mm sensor), between f/2.8 and f/6.3 (or `most`): a
    macro's shallow focus, the set behind melting away."""
    f = lens
    n = depth_mm * f * f / max(1e-6, coc * s_mm * s_mm)
    return float(np.clip(n, 2.8, most))


# ---------------------------------------------------------------------------- laid out
_RESTING: dict = {}


def resting(engine, part: str) -> dict:
    """How a loose part lies on a table: {R (3 x 3: the part's frame to the table's, LDraw, -Y
    up), t (so R @ p + t puts its footprint's middle on the origin and its lowest point on
    y = 0), size (along its long side, across, up)}. It lies studs up if that is stable (its
    centre of mass over what touches the table), else on its broadest side that is: a plate
    with a tooth or a long inverted slope lies on its side. Its long side is along X."""
    if part in _RESTING:
        return _RESTING[part]
    from scipy.spatial import ConvexHull, QhullError
    mesh = engine.geom.mesh(part)
    V = np.unique(np.round(mesh.tris.reshape(-1, 3), 3), axis=0)
    vol, com = mesh.volume_centroid()
    com = np.asarray(com, float)
    if not (vol > 0 and np.isfinite(com).all()):
        com = V.mean(0)
    down = np.array([0.0, 1.0, 0.0])
    best, H = None, V
    try:
        hull = ConvexHull(V)
        H = V[hull.vertices]
        for nrm in np.unique(np.round(hull.equations[:, :3], 2), axis=0):
            nrm = nrm / (np.linalg.norm(nrm) + 1e-12)
            h = H @ nrm
            S = H[h > h.max() - 0.5]                   # what touches the table
            a = np.cross(nrm, [1.0, 0.0, 0.0] if abs(nrm[0]) < 0.9 else [0.0, 0.0, 1.0])
            a /= np.linalg.norm(a)
            b = np.cross(nrm, a)
            try:
                foot = ConvexHull(np.stack([S @ a, S @ b], 1))
            except (QhullError, ValueError):
                continue
            inside = foot.equations[:, :2] @ [com @ a, com @ b] + foot.equations[:, 2]
            if inside.max() > -1.0:                    # it would tip off this side
                continue
            key = (0 if nrm @ down > 0.999 else 1, -round(foot.volume / 20.0),   # (.volume: its area)
                   round(float(h.max() - com @ nrm), 1))
            if best is None or key < best[0]:
                best = (key, nrm)
    except (QhullError, ValueError):
        pass
    nrm = down if best is None else best[1]
    c = float(np.clip(nrm @ down, -1, 1))
    if c > 0.9999:
        R = np.eye(3)
    elif c < -0.9999:
        R = T._axis_rot([1.0, 0.0, 0.0], 180.0)
    else:
        R = T._axis_rot(np.cross(nrm, down), math.degrees(math.acos(c)))
        if (R @ nrm) @ down < 0.999:
            R = R.T
    W = V @ R.T
    spans = []
    for deg in range(0, 180, 5):                       # the tightest box round its footprint
        Y = T._axis_rot(down, float(deg))
        q = W @ Y.T
        e = q.max(0) - q.min(0)
        spans.append((round(float(e[0] * e[2]), 1), -round(float(e[0]), 1), deg))
    Y = T._axis_rot(down, float(min(spans)[2]))
    R = Y @ R
    W = V @ R.T
    lo, hi = W.min(0), W.max(0)
    out = {"R": R, "t": -np.array([(lo[0] + hi[0]) / 2, hi[1], (lo[2] + hi[2]) / 2]),
           "size": (float(hi[0] - lo[0]), float(hi[2] - lo[2]), float(hi[1] - lo[1])),
           "hull": H}                                  # (its outermost points, its own frame)
    _RESTING[part] = out
    return out


def lay_out(engine, placed, C, seq, front: float = 0.0, bodies: list | None = None) -> dict:
    """The parts laid out on the table before the build, knolled: a tidy grid behind the
    build's place, every part lying as it would (resting) with its long side along the rows.
    The grid is the model taken apart: its rows are the build's steps in order, the first
    furthest back and the last nearest the build (short steps share a row, a long one gets a
    row for each kind of part), so from the front it reads from the top down like a list, and
    the rows empty towards the build as it is built; no row is wider than the build, so in
    the upright frame the grid stands tall. In a row the same parts sit together and the row
    mirrors the model: each part on the side it will be on, the middle ones in the middle,
    the right-hand ones turned round to face the left-hand ones. `bodies`: the pieces (a bought
    kit's parts lie together, as the kit stands in the model). Returns {start: {part index:
    4 x 4}, corner_of {part index: (8, 3)}, box (the grid's [[x0, z0], [x1, z1]]), tall, a, b
    (the grid's size along and across the rows), rows}."""
    allp = C.reshape(-1, 3)
    lo, hi = allp.min(0), allp.max(0)
    mid = (lo + hi) / 2
    ground = hi[1]
    F = T._axis_rot([0.0, 1.0, 0.0], -front)           # the grid's frame: rows along X, front -Z
    if abs((F @ view_dir(front, 0.0))[2] + 1) > 1e-6:
        F = F.T
    across = lambda i: float((F @ (C[i].mean(0) - mid))[0])     # noqa: E731
    mates = {b[0]: list(b) for b in (bodies or [[i] for i in seq])}     # a piece by its first part
    seq = [i for i in seq if i in mates]
    lie, local = {}, {}
    for i, body in mates.items():
        if len(body) == 1:
            lie[i] = resting(engine, placed[i].part)
            L = np.eye(4)
            L[:3, :3], L[:3, 3] = lie[i]["R"], lie[i]["t"]
            local[i] = {i: L}
            continue
        q = np.concatenate([A.hull(engine, placed[j].part) @ np.asarray(placed[j].M, float)[:3, :3].T
                            + np.asarray(placed[j].M, float)[:3, 3] for j in body])
        qlo, qhi = q.min(0), q.max(0)                  # a kit: upright, as it stands in the model
        tr = A.trans(-np.array([(qlo[0] + qhi[0]) / 2, qhi[1], (qlo[2] + qhi[2]) / 2]))
        lie[i] = {"size": (float(qhi[0] - qlo[0]), float(qhi[2] - qlo[2]), float(qhi[1] - qlo[1]))}
        local[i] = {j: tr @ np.asarray(placed[j].M, float) for j in body}
    gap, row_gap = LAYOUT_GAP
    width = lambda row: sum(lie[i]["size"][0] for i in row) + gap * (len(row) - 1)   # noqa: E731
    foot = np.abs((allp - mid) @ F.T).max(0)           # half the build's footprint, in the grid
    n_rows = int(np.clip(round(math.sqrt(1.5 * len(seq))), *LAYOUT_ROWS))
    per_row = math.ceil(len(seq) / n_rows)
    steps = []                                         # the build's steps, in order
    for i in seq:
        key = (placed[i].build_order, placed[i].owner, placed[i].local_step)
        if steps and steps[-1][0] == key:
            steps[-1][1].append(i)
        else:
            steps.append((key, [i]))
    widest = max(2 * foot[0], 10 * 20.0)               # a row: no wider than the build
    kind = lambda i: (placed[i].part, placed[i].color.name)     # noqa: E731
    rows, cur = [], []
    for _, st in steps:
        if width(st) > widest:                         # a step too long for a row: a row (or
            if cur:                                    # more) for each kind of part in it
                rows.append(cur)
            cur = []
            for k in dict.fromkeys(kind(i) for i in st):
                for i in (i for i in st if kind(i) == k):
                    if cur and (kind(cur[-1]) != k and width(cur + [j for j in st if kind(j) == k]) > widest
                                or width(cur + [i]) > widest):
                        rows.append(cur)
                        cur = []
                    cur.append(i)
            continue
        if cur and (len(cur) + len(st) > per_row + 1 or width(cur + st) > widest):
            rows.append(cur)
            cur = []
        cur = cur + st
    if cur:
        rows.append(cur)
    start, corners = {}, {}

    def place(row, z):
        groups = {}
        for i in row:
            groups.setdefault((placed[i].part, placed[i].color.name), []).append(i)
        left, middle, right = [], [], []
        for g in sorted(groups.values(), key=lambda g: -np.mean([abs(across(i)) for i in g])):
            g = sorted(g, key=across)                  # the outermost kinds outermost
            k = len(g) // 2
            left += g[:k]
            middle += g[k:len(g) - k]
            right = g[len(g) - k:] + right
        x = -width(row) / 2
        for j, i in enumerate(left + middle + right):
            r = lie[i]
            Y = np.eye(3) if j < len(left) + len(middle) else T._axis_rot([0.0, 1.0, 0.0], 180.0)
            slot = np.eye(4)
            slot[:3, :3] = F.T @ Y
            slot[:3, 3] = mid * [1, 0, 1] + [0.0, ground, 0.0] + F.T @ np.array([x + r["size"][0] / 2, 0.0, z])
            for m, L in local[i].items():
                M = slot @ L
                start[m] = M
                Mf = np.asarray(placed[m].M, float)
                corners[m] = (C[m] - Mf[:3, 3]) @ Mf[:3, :3] @ M[:3, :3].T + M[:3, 3]
            x += r["size"][0] + gap

    depth = lambda row: max(lie[i]["size"][1] for i in row)     # noqa: E731
    z = foot[2] + LAYOUT_CLEAR                         # behind the build: the last step's row
    for row in reversed(rows):                         # nearest it, the first furthest back
        place(row, z + depth(row) / 2)
        z += depth(row) + row_gap
    every = np.concatenate(list(corners.values()))
    return {"start": start, "corner_of": corners, "corners": np.array([corners[i] for i in sorted(corners)]),
            "box": np.array([every.min(0)[[0, 2]], every.max(0)[[0, 2]]]),
            "a": float(max(width(r) for r in rows)), "b": float(z - row_gap - foot[2] - LAYOUT_CLEAR),
            "tall": float(max(r["size"][2] for r in lie.values())), "rows": [list(r) for r in rows]}


def lens_room(fl: list, cam: dict) -> float:
    """How clear of the lens the parts stay on their way in: the least distance from a moving
    part to the camera, as a share of the camera's distance to what it looks at."""
    pos, tgt = np.asarray(cam["pos"]), np.asarray(cam["target"])
    least = 9.0
    for p in fl:
        if p is None:
            continue
        b = np.array(p["frames"]).reshape(-1, 4, 4)[:, :3, 3]
        f = np.clip(p["launch"] + np.arange(len(b)), 0, len(pos) - 1)
        least = min(least, float((np.linalg.norm(b - pos[f], axis=1)
                                  / np.linalg.norm(pos[f] - tgt[f], axis=1)).min()))
    return least


# ---------------------------------------------------------------------------- the parts' flights
def _axis_rot(axis, deg):
    return T._axis_rot(axis, deg)


def _ease(u: float, laid: bool) -> float:
    """How far along its way a piece is at u of its time: off frame it comes fast and settles;
    off the table it eases out of rest and into place."""
    return u * u * (3 - 2 * u) if laid else 1 - (1 - u) ** 2.4


def _press(u: float, length: float, laid: bool, click: float = CLICK) -> float:
    """The distance covered at u of the time, on a way `length` long: eased to a near stop
    `click` LDU short of the end (lined up on its studs) by PRESS of the time, then pressed
    home - quicker and quicker, and it stops dead: no bounce."""
    click = min(click, 0.4 * length)
    if u >= 1.0:
        return length
    if u <= PRESS:
        return (length - click) * _ease(u / PRESS, laid)
    return length - click + click * ((u - PRESS) / (1 - PRESS)) ** 1.7


def _at(path: dict, dist: float):
    """(middle's offset from its seat, turn left 1..0) `dist` along a route."""
    s = path["s"]
    k = int(np.clip(np.searchsorted(s, dist), 1, len(s) - 1))
    w = 0.0 if s[k] - s[k - 1] < 1e-9 else float(np.clip((dist - s[k - 1]) / (s[k] - s[k - 1]), 0, 1))
    return path["p"][k - 1] + (path["p"][k] - path["p"][k - 1]) * w, float(path["q"][k - 1] + (path["q"][k] - path["q"][k - 1]) * w)


def _blend(A0, A1, w: float) -> np.ndarray:
    """Between two poses that differ by a move (not a turn)."""
    M = np.array(A1, float)
    M[:3, 3] = A0[:3, 3] + (A1[:3, 3] - A0[:3, 3]) * w
    return M


def motion(engine, placed, script: dict, sch: dict, cam: dict, laid: dict | None, fps: int = FPS,
           size=SIZE, log=None) -> tuple[list[dict], list[float], list[str]]:
    """Every part's moves, per frame, from the build's script (assemble.assemble) and the
    schedule of its items: [{launch, land, frames (4 x 4 world transforms, flat, from its
    launch to the end of its settling), start (laid out: where it lies till then, and again
    after the cut), moves [{at, frames}] (later: its unit lifted for a piece, or joined)}].
    A piece starts just off the frame, out to the side it faces and up (or lying in the
    grid, or where its unit was built), and takes assemble.route()'s way in - over or round
    what is built, down at a gate in line with its way in, straight in the last stretch - to
    line up a hair short of its place and press home (no bounce). What is built is lifted for
    a piece that needs it under it, and set down on it. Two pieces in the air at once keep out
    of each other's way: the later one comes from the other side, or a few frames later (so a
    landing may be a little after its time in the schedule: never before the one before it).
    Also returns when (s) each item lands, and what had no clear way."""
    n = len(placed)
    out: list = [None] * n
    notes: list[str] = []
    up = np.array([0.0, -1.0, 0.0])
    settle = max(2, int(round(SETTLE * fps)))
    ground = script["ground"]
    items = script["items"]
    col = engine.collide
    lying = set(range(n)) if laid else set()           # still in the grid
    air: list = []                                     # (f0, f1, parts, frames) still on their way
    lands: list[float] = []
    last_land, last_end, held = -1, 0, 0               # (held: the build is up for a piece till then)
    flat = lambda Ms: [np.round(np.asarray(M, float).reshape(-1), 4).tolist() for M in Ms]   # noqa: E731
    for k, it in enumerate(items):
        f0s = int(round(sch["launch"][k] * fps))
        f1s = max(int(round(sch["land"][k] * fps)), f0s + 3)
        span = f1s - f0s
        slow = it.kind == "join" or bool(it.carry)
        movers = [(placed[i].part, it.seat[i]) for i in it.parts]
        lying -= set(it.parts)
        still = list(it.still) + [(j, during) for j, (_, during, _) in it.carry.items()]
        if laid:
            still += [(j, laid["start"][j]) for j in sorted(lying)]
        world = A.World(engine, placed, still, ground)
        pts = np.concatenate([col.world_aabb(part, M) for part, M in movers])
        c = (pts.min(0) + pts.max(0)) / 2
        lead = it.parts[0]
        fc = min(len(cam["pos"]) - 1, f0s)
        cpos, ctgt = cam["pos"][fc], cam["target"][fc]
        dcam = (cpos - ctgt) / np.linalg.norm(cpos - ctgt)
        right, _ = basis(dcam)
        from_table = it.source is not None or bool(laid)
        routes: dict = {}

        def way(opt: int) -> dict:
            """Its route. 0, 1: from one side of the frame or the other (tumbling in, if it
            comes from off the frame); 2, 3: the same without the tumble, and 4: from straight
            overhead - for a tight place a tumbling piece does not fit into."""
            if opt in routes:
                return routes[opt]
            flip = opt in (1, 3)
            turn, tilt = None, None
            if from_table:                             # from where it stands or lies
                X0 = np.asarray(it.source[lead] if it.source is not None else laid["start"][lead], float) \
                    @ np.linalg.inv(it.seat[lead])
                turn, start = X0[:3, :3], X0[:3, :3] @ c + X0[:3, 3] - c
            else:                                      # from just off the frame
                a = it.axis * [1, 0, 1]
                side = a / np.linalg.norm(a) if np.linalg.norm(a) > 0.5 else unit_out(c, script["middle"])
                if abs(float(it.axis @ up)) > 0.7 or float(side @ dcam) > 0.5:    # (not straight at the lens)
                    s_r = float(side @ right)
                    sgn = math.copysign(1.0, s_r) if abs(s_r) > 0.15 else (1.0 if k % 2 else -1.0)
                    side = right * sgn * (-0.8 if flip else 0.8) + side * 0.35 - dcam * 0.25
                    side *= [1, 0, 1]
                    side /= np.linalg.norm(side) + 1e-12
                elif flip:                             # (sideways on: from higher up instead)
                    side = side * 0.6
                tx, _ = tangents(float(cam["lens"][fc]), size)
                reach = 1.15 * float(np.linalg.norm(cpos - ctgt)) * tx      # just off the frame's side
                start = side * reach + up * (0.9 if flip and np.linalg.norm(side) < 0.9 else 0.55) * reach \
                    + it.axis * it.travel
                tilt_axis = np.cross(up, side)
                if np.linalg.norm(tilt_axis) > 1e-6 and opt < 2:
                    tilt = (tilt_axis, TILT)
                if opt == 4:
                    start = up * 0.9 * reach + it.axis * it.travel
            if it.mode == "under":                     # along the table, in under what is held up
                flatr = right * [1, 0, 1] / (np.linalg.norm(right * [1, 0, 1]) + 1e-12)
                sgn = (1.0 if float(start @ flatr) >= 0 else -1.0) * (-1.0 if flip else 1.0)
                fwd = np.cross(flatr, up)
                ways = [(h, 16.0) for h in (flatr * sgn, -flatr * sgn, fwd, -fwd)]
            else:
                ways = [(it.axis, it.travel)]
            routes[opt] = A.route(world, movers, start, turn, ways, tilt=tilt, direct=not from_table,
                                  hop=30.0 if flip and from_table else 10.0)
            return routes[opt]

        def fly(path: dict, f0: int, f1: int):
            total = float(path["s"][-1])
            frames = {i: [] for i in it.parts}
            carried = {j: [] for j in it.carry}
            for f in range(f0, f1 + settle):
                u = (f - f0) / (f1 - f0)
                if f < f1:
                    if it.mode == "under":             # (it is there before the set-down)
                        dist = total * _ease(min(1.0, u / UNDER[0]), True)
                    else:
                        dist = _press(u, total, from_table)
                    pm, q = _at(path, dist)
                    for (_, M), i in zip(A.poses(movers, path["c"], pm, path["R"](q)), it.parts):
                        frames[i].append(M)
                else:                                  # settled; and set down again with the rest
                    w = T.smootherstep((f - f1 + 1) / settle)
                    for i in it.parts:
                        frames[i].append(_blend(it.seat[i], it.rest[i], w))
                for j, (before, during, after) in it.carry.items():
                    if f < f1:
                        M = _blend(before, during, T.smootherstep(u / LIFT))
                        if it.mode == "under" and u > UNDER[1]:       # set down on the piece
                            drop = float(np.linalg.norm(during[:3, 3] - after[:3, 3]))
                            M = _blend(during, after, _press((u - UNDER[1]) / (1 - UNDER[1]), drop, True) / max(drop, 1e-9))
                    elif it.mode == "under":
                        M = np.array(after, float)
                    else:
                        M = _blend(during, after, T.smootherstep((f - f1 + 1) / settle))
                    carried[j].append(M)
            return frames, carried

        def crossing(frames: dict, f0: int, f1: int) -> int:
            """Frames in which it is in another piece that is still in the air."""
            hits = 0
            for g0, g1, others, gframes in air:
                for f in range(max(f0, g0), min(f1, g1)):
                    if any(col.collide_pair(placed[i].part, frames[i][f - f0], placed[j].part, gframes[j][f - g0])
                           for i in it.parts for j in others):
                        hits += 1
            return hits

        least = max(0, last_land + 1 - f1s, (last_end - f0s) if slow else (held - f1s))
        best = None
        for opts in ((0, 1), (2, 3, 4)):               # (the plain ways only if those are blocked)
            if best is not None and (best[1]["clear"] or from_table):
                break
            for more in (int(round(x * fps)) for x in LATER):
                for opt in opts:
                    path = way(opt)
                    if best is not None and not path["clear"] and best[1]["clear"]:
                        continue
                    f0, f1 = f0s + least + more, f1s + least + more
                    frames, carried = fly(path, f0, f1)
                    score = (not path["clear"], crossing(frames, f0, f1), more, opt)
                    if best is None or score < best[0]:
                        best = (score, path, f0, f1, frames, carried)
                    if score[:2] == (False, 0):
                        break
                if best[0][:2] == (False, 0):
                    break
        _, path, f0, f1, frames, carried = best
        if not path["clear"] or it.forced:
            notes.append(f"{A_name(placed, it.parts)}: no clear way in")
        if best[0][1]:
            notes.append(f"{A_name(placed, it.parts)}: crosses another piece in the air")
        for i in it.parts:
            if it.kind == "piece":
                out[i] = {"launch": f0, "land": f1, "frames": flat(frames[i]), "moves": []}
                if laid:
                    out[i]["start"] = np.round(np.asarray(laid["start"][i], float).reshape(-1), 4).tolist()
            else:
                out[i]["moves"].append({"at": f0, "frames": flat(frames[i])})
        for j, Ms in carried.items():
            out[j]["moves"].append({"at": f0, "frames": flat(Ms)})
        air = [g for g in air if g[1] > f0] + [(f0, f1, list(it.parts), frames)]
        lands.append(float(sch["land"][k]) + (f1 - f1s) / fps if f1 > f1s else float(sch["land"][k]))
        last_land, last_end = f1, f1 + settle
        if slow:
            held = f1 + settle
    return out, lands, notes


def flex_moves(model, placed, parts: list[dict], cut: float, flex: float, fps: int) -> tuple[int, int]:
    """The finished model's own movement ([quick] flex, s), added to `parts` as one more move
    for every part in a moving group: from where it stands, through design.py's model.pose,
    over the `flex` s that end FLEX_HOLD s before the cut. The model always ends as it stands
    in its booklet. A pose that comes round to where it began (a walk on the spot: pose(1)
    moves nothing) is played once, t going evenly from 0 to 1: the pose itself starts and
    ends gently, or it jerks. One that ends somewhere else (a lid open, a head tipped back)
    is played there and back: eased out to t = 1 over FLEX_OUT of the time, held, and eased
    home over as long. Returns the move's (first, last) frame."""
    f1 = int(round((cut - FLEX_HOLD) * fps))
    f0 = f1 - max(2, int(round(flex * fps)))
    round_trip = all(np.allclose(np.asarray(G, float), np.eye(4), atol=1e-6) for G in model.pose(1.0).values())

    def t_at(u: float) -> float:
        if round_trip:
            return u
        return float(T.smootherstep(min(u, 1.0 - u) / FLEX_OUT)) if min(u, 1.0 - u) < FLEX_OUT else 1.0
    group = [model.group_of(p) for p in placed]
    rest = {i: np.asarray((p["moves"][-1]["frames"] if p["moves"] else p["frames"])[-1], float).reshape(4, 4)
            for i, p in enumerate(parts) if group[i] is not None}
    frames = {i: [] for i in rest}
    for f in range(f0, f1 + 1):
        G = model.pose(t_at((f - f0) / (f1 - f0)))
        for i, M in rest.items():
            g = G.get(group[i])
            frames[i].append(np.round((M if g is None else np.asarray(g, float) @ M).reshape(-1), 4).tolist())
    for i, Ms in frames.items():
        parts[i]["moves"].append({"at": f0, "frames": Ms})
    return f0, f1


def unit_out(c, middle) -> np.ndarray:
    """Horizontal unit vector from the model's middle out to c (the front, if it is there)."""
    r = (np.asarray(c, float) - middle) * [1, 0, 1]
    if np.linalg.norm(r) < 1e-6:
        return np.array([0.0, 0.0, -1.0])
    return r / np.linalg.norm(r)


def A_name(placed, parts) -> str:
    p = placed[parts[0]]
    tag = "/".join(p.tags)
    return p.part.removesuffix(".dat") + (f" ({tag})" if tag else "")


def pose_at(pl: dict, i: int, f: int):
    """Part i's 4 x 4 at frame f of a plan (None: not there yet, or gone after the cut and not
    laid out): what render/blender_quick.py shows."""
    p = pl["parts"][i]
    if f >= pl["cut"] or f < p["launch"]:
        return np.array(p["start"]).reshape(4, 4) if "start" in p else None
    M = p["frames"][min(f - p["launch"], len(p["frames"]) - 1)]
    for mv in p.get("moves", ()):
        if f >= mv["at"]:
            M = mv["frames"][min(f - mv["at"], len(mv["frames"]) - 1)]
    return np.array(M).reshape(4, 4)


def clashes(engine, placed, pl: dict, every: int = 1) -> list[dict]:
    """Where a plan breaks the rules, straight from its frames: a moving part in a part that
    stands still (but a clip's last flex onto its bar) or under the table, and a part that
    lands on nothing. [{part, frame, other | "table" | "air"}], one per part and other."""
    from ..snaps.match import find_connections
    wc = [[c.transformed(p.M) for c in engine.shadow.connectors(p.part)] for p in placed]
    snap, joined = {}, {}
    for c in find_connections(wc):
        joined.setdefault(c.a, set()).add(c.b)
        joined.setdefault(c.b, set()).add(c.a)
        if c.kind in A.SNAP:                           # a pin in its hole: its whole length
            snap[(c.a, c.b)] = snap[(c.b, c.a)] = A.FLEX if c.kind in A.CROSS else 30.0
    col = engine.collide
    n = len(placed)
    ground = max(A.low(engine, p.part, np.asarray(p.M, float)) for p in placed)
    rel = lambda Mi, Mj: np.linalg.inv(Mj) @ Mi        # noqa: E731
    seated = {}
    found: dict = {}
    prev = [None] * n
    for f in range(0, pl["cut"], every):
        now = [pose_at(pl, i, f) for i in range(n)]
        moving = [i for i in range(n) if now[i] is not None and pl["parts"][i]["launch"] <= f
                  and (prev[i] is None or not np.allclose(prev[i], now[i], atol=1e-4))]
        there = [i for i in range(n) if now[i] is not None and pl["parts"][i]["launch"] <= f]
        lying = [i for i in range(n) if now[i] is not None and pl["parts"][i]["launch"] > f]
        for i in moving:
            if A.low(engine, placed[i].part, now[i]) > ground + 0.6:
                found.setdefault((i, "table"), f)
            box = col.world_aabb(placed[i].part, now[i])
            for j in there + lying:
                if j == i or (i, j) in found:
                    continue
                if prev[i] is not None and prev[j] is not None and now[j] is not None \
                        and np.allclose(rel(now[i], now[j]), rel(prev[i], prev[j]), atol=1e-4):
                    continue                           # moving together
                bj = col.world_aabb(placed[j].part, now[j])
                if np.any(box[1] <= bj[0] + 0.5) or np.any(bj[1] <= box[0] + 0.5):
                    continue
                if not col.collide_pair(placed[i].part, now[i], placed[j].part, now[j]):
                    continue
                if (i, j) in snap:                     # the last of a clip's way onto its bar
                    off = rel(now[i], now[j])[:3, 3] - rel(np.asarray(placed[i].M, float), np.asarray(placed[j].M, float))[:3, 3]
                    if np.linalg.norm(off) <= snap[(i, j)] + 0.5:
                        continue
                found.setdefault((i, j), f)
        prev = now
    for i in range(n):                                 # as it lands: on the table, or on a part
        f = pl["parts"][i]["land"]
        M = pose_at(pl, i, min(f, pl["cut"] - 1))
        if abs(A.low(engine, placed[i].part, M) - ground) < 1.0:
            continue
        held = False
        for j in joined.get(i, ()):
            Mj = pose_at(pl, j, min(f, pl["cut"] - 1))
            if Mj is not None and pl["parts"][j]["launch"] <= f and np.allclose(
                    rel(M, Mj), rel(np.asarray(placed[i].M, float), np.asarray(placed[j].M, float)), atol=0.05):
                held = True
                break
        if not held and not _kit_mate_holds(placed, pl, i, f):
            found.setdefault((i, "air"), f)
    return [{"part": i, "other": o, "frame": f} for (i, o), f in sorted(found.items(), key=lambda kv: kv[1])]


def report(placed, pl: dict, wrong: list[dict]) -> list[str]:
    """What a plan gets wrong, in words (nothing, if it builds for real): what clashes()
    found in its frames, and the pieces no clear way in was found for."""
    out = [f"  quick: {note}" for note in pl.get("notes", ())]
    name = lambda i: A_name(placed, [i])               # noqa: E731
    for w in wrong[:12]:
        what = {"table": "dips under the table", "air": "lands on nothing"}.get(
            w["other"]) or f"passes through {name(w['other'])}"
        out.append(f"  quick: {name(w['part'])} {what} (frame {w['frame']})")
    if len(wrong) > 12:
        out.append(f"  quick: ... and {len(wrong) - 12} more")
    if out:
        out.append("  quick: (an insert=(x, y, z) hint on that piece in design.py - the way it comes "
                   "in from - usually settles it)")
    return out


def _kit_mate_holds(placed, pl, i, f) -> bool:
    """A piece of a bought kit lands with the rest of it (held by them)."""
    k = placed[i].kit
    return k is not None and any(p.kit == k and j != i and pl["parts"][j]["land"] == f
                                 for j, p in enumerate(placed))


# ---------------------------------------------------------------------------- the plan
def plan(engine, model, cfg: dict, fps: int = FPS, size=SIZE, log=None) -> dict:
    """Everything the render and the sound need, JSON-able (frames from 0, at `fps`). The
    build is assemble.assemble()'s: every piece on a clear way in, nothing in the air - so a
    bought kit is one piece, a sub-assembly that cannot be built in place is built beside the
    model and joined, and what is built is lifted for a piece that goes underneath. If all
    that does not fit in [quick] seconds the loop is made as much longer as it needs."""
    from ..render.scene import model_scene
    placed = model.flatten()
    C = T.corners(engine, placed)
    seq = build_sequence(model, placed)
    front = float(model.meta.get("azimuth_offset", 0.0))
    # laid out first? (layout: "auto" - a model of a few pieces)
    bodies = A.structure(model, placed, seq)["bodies"]
    laid = None
    if cfg.get("layout", "auto") is True or (cfg.get("layout", "auto") == "auto" and len(bodies) < LAYOUT_UNDER):
        laid = lay_out(engine, placed, C, seq, front, bodies)
    script = A.assemble(engine, model, placed, seq, [laid["box"]] if laid else (), front, log)
    items, order = script["items"], script["order"]
    piece = {i: k for k, it in enumerate(items) if it.kind == "piece" for i in it.parts}
    order_of = {i: k for k, i in enumerate(order)}
    Cl = np.zeros_like(C)                              # where each part lands (its unit may move later)
    for i, p in enumerate(placed):
        X = script["landed"][i] @ np.linalg.inv(np.asarray(p.M, float))
        Cl[i] = C[i] @ X[:3, :3].T + X[:3, 3]
    axes = np.array([script["axis"][i] for i in range(len(placed))])
    if laid:
        laid["corners"] = np.array([laid["corner_of"][i] for i in order])
    slow = {k: SLOW["under" if it.mode == "under" else "join" if it.kind == "join" else "lift"]
            for k, it in enumerate(items) if it.kind == "join" or it.carry}
    groups = highlight_groups(placed, order, cfg)
    seconds = float(cfg["seconds"])
    flex = float(cfg.get("flex") or 0.0)
    if flex and model.pose is None:
        raise SystemExit("[quick] flex: the model has nothing that moves (design.py sets no model.pose)")

    def timed(picks):
        nonlocal seconds
        for _ in range(240):                           # (longer, if the build needs it)
            try:
                si = schedule(len(items), seconds, picks, fps, bool(laid), slow, flex)
                break
            except SystemExit:
                if not slow:
                    raise
                seconds += 0.5
        else:
            raise SystemExit(f"{len(items)} pieces with {len(slow)} lifts and joins don't fit in "
                             f"{seconds:g} s: make [quick] seconds longer")
        view = dict(si, launch=np.array([si["launch"][piece[i]] for i in order]),
                    land=np.array([si["land"][piece[i]] for i in order]), last=float(si["land"][-1]))
        return si, view

    def home(si) -> np.ndarray:
        """When (s) each part is on the model: its own landing, or when the unit it was built
        in beside the model is joined (the last such, for a unit of a unit)."""
        at = np.array([float(si["land"][piece[i]]) for i in range(len(placed))])
        for k, it in enumerate(items):
            if it.kind == "join":
                for i in it.parts:
                    at[i] = max(at[i], float(si["land"][k]))
        return at

    # schedule, pick the close-ups on it, schedule again with room round them, then the camera
    si, sch = timed([])
    cam = plan_camera(model, placed, Cl, order, sch, groups, cfg, axes, fps, size, laid, C, home=home(si))
    for _ in range(2):                                 # (again, if one is dropped: face_on())
        picked = [w[2] for w in cam["windows"]]
        si, sch = timed([piece[i] for i in picked])
        groups2 = [g2 for g2 in ([i for i in g if i in picked] for g in groups) if g2]   # (first wanted first)
        cam = plan_camera(model, placed, Cl, order, sch, groups2, cfg, axes, fps, size, laid, C, sure=True,
                          home=home(si))
        if len(cam["windows"]) == len(picked):
            break
    if seconds > float(cfg["seconds"]) and log:
        log(f"  quick: {seconds:g} s, not {float(cfg['seconds']):g}: the build takes that long "
            f"({len(slow)} lifts and joins)")
    fl, lands, notes = motion(engine, placed, script, si, cam, laid, fps, size)
    if flex:
        flex_moves(model, placed, fl, float(sch["cut"]), flex, fps)
    landed = np.array([lands[piece[i]] for i in order])         # (a moment late, some)
    scene = model_scene(engine, model, placed=placed)
    scene["lights"] = []
    allp = np.concatenate([C.reshape(-1, 3), Cl.reshape(-1, 3)])
    floor = allp if laid is None else np.concatenate([allp, laid["corners"].reshape(-1, 3)])
    r5 = lambda a: np.round(np.asarray(a, float), 4).tolist()   # noqa: E731
    mid = (allp.min(0) + allp.max(0)) / 2
    reach = float(np.linalg.norm((cam["pos"] - mid) * [1, 0, 1], axis=1).max()) * 0.0004   # m
    clicks = sorted({round(x, 4) for x in lands})
    return {
        "fps": fps, "frames": sch["frames"], "size": list(size), "set": cfg["set"],
        "surface": cfg["surface"], "room": cfg["room"], "light": cfg["light"], "seed": cfg["seed"],
        "exposure": float(cfg["exposure"]), "view": cfg["view"], "seconds": seconds,
        "cut": int(round(sch["cut"] * fps)), "scene": scene, "reach": round(reach, 4),
        "bounds": [r5(allp.min(0)), r5(allp.max(0))],
        "layout": laid is not None, "floor": [r5(floor.min(0)), r5(floor.max(0))],
        "order": order, "land": [int(fl[i]["land"]) for i in order],
        "land_s": [round(float(x), 4) for x in landed], "cut_s": round(float(sch["cut"]), 4),
        "clicks_s": clicks,                            # every landing: a piece, or a unit joined
        "joins": [{"at_s": round(lands[k], 4), "parts": list(it.parts)}
                  for k, it in enumerate(items) if it.kind == "join"],
        "notes": notes + list(script["warnings"]),
        "parts": fl,
        "camera": {"pos": r5(cam["pos"]), "target": r5(cam["target"]), "lens": r5(cam["lens"]),
                   "focus": r5(cam["focus"]), "fstop": r5(cam["fstop"])},
        "close_ups": [{"start": int(a * fps), "end": int(b * fps), "part": int(i),
                       "land": int(fl[i]["land"]),
                       "start_s": round(float(a), 4), "end_s": round(float(b), 4)}
                      for a, b, i in cam["windows"]],
    }


# ---------------------------------------------------------------------------- the sound
def moment(model, placed, pl: dict, on) -> float:
    """When (s) a [[quick.sound]] `on` is: a time in seconds; "first" or "last" (piece
    landing); a step's caption (its first piece landing); or a part number or tag (the one a
    close-up is on, else the first to land)."""
    land, order = pl["land_s"], pl["order"]
    if isinstance(on, (int, float)) and not isinstance(on, bool):
        return float(on)
    name = str(on).strip()
    if name in ("first", "last"):
        return float(land[0] if name == "first" else pl.get("clicks_s", land)[-1])
    steps = {(sub.name, k) for sub in model.submodels.values()
             for k, c in enumerate(sub.captions) if c.strip().lower() == name.lower()}
    hits = [k for k, i in enumerate(order) if (placed[i].owner, placed[i].local_step) in steps]
    if not hits:
        part = name[:-4] if name.endswith(".dat") else name
        hits = [k for k, i in enumerate(order)
                if placed[i].part.removesuffix(".dat") == part or name in placed[i].tags]
        close = {c["part"] for c in pl["close_ups"]}
        hits = [k for k in hits if order[k] in close] or hits
    if not hits:
        raise SystemExit(f"[[quick.sound]] on: no step, part or tag {name!r}")
    return float(land[hits[0]])


def cues(pl: dict, music: bool, seed: int = 1, ending: dict | None = None,
         sounds: list | None = None) -> dict:
    """audio.py's cue sheet: a click on every landing (the variants in turn, a little louder
    or softer), a deeper snap on the last, a soft swish into each close-up; `ending`
    {path, level, at}: the model's own sound (a laugh, a roar) `at` s after the last piece
    lands, over the hero and the cut; `sounds` [{path, level, times}]: more of its own, each
    at `times` (s; a bell as its tower goes up); with `music` the music bed (bed_2: even from
    its first beat, no ending) under it all, faded out at the cut; no synthesised music. Every
    time is the plan's in seconds (x fps), so 30 and 60 fps agree."""
    d = paths.DATA_DIR / "audio" / "quick"
    fps = pl["fps"]
    files = list(SOUNDS["click"]) + [SOUNDS["snap"], SOUNDS["swish"]]
    samples = {f: {"path": str(d / f), "sha1": hashlib.sha1((d / f).read_bytes()).hexdigest()}
               for f in files}
    rng = np.random.default_rng(seed)
    ev = []
    land = pl.get("clicks_s", pl["land_s"])            # (a kit lands as one; a unit joined clicks too)
    n = len(land)
    for k, t in enumerate(land):
        if k == n - 1:
            ev.append({"frame": t * fps, "type": "sample", "file": SOUNDS["snap"],
                       "level": SOUND_LEVEL["snap"], "align": "peak"})
            continue
        ev.append({"frame": t * fps, "type": "sample", "file": SOUNDS["click"][k % len(SOUNDS["click"])],
                   "level": SOUND_LEVEL["click"] + float(rng.uniform(-3.0, 1.0)), "align": "peak"})
    for c in pl["close_ups"]:
        ev.append({"frame": (c["start_s"] - SWING * 0.5) * fps, "type": "sample",
                   "file": SOUNDS["swish"], "level": SOUND_LEVEL["swish"]})
    if ending:
        f = Path(ending["path"])
        samples["ending"] = {"path": str(f), "sha1": hashlib.sha1(f.read_bytes()).hexdigest()}
        at = (land[-1] + float(ending.get("at", 0.25))) * fps
        ev.append({"frame": at, "type": "sample", "file": "ending", "fade_out": 0.1,
                   "level": float(ending.get("level", -3.0)), "dur": max(1.0, pl["frames"] - at)})
    for j, snd in enumerate(sounds or []):
        f = Path(snd["path"])
        samples[f"sound_{j}"] = {"path": str(f), "sha1": hashlib.sha1(f.read_bytes()).hexdigest()}
        for t in snd["times"]:                         # (faded out at the video's end)
            ev.append({"frame": float(t) * fps, "type": "sample", "file": f"sound_{j}",
                       "level": float(snd.get("level", -11.0)), "fade_out": 0.3,
                       "dur": max(1.0, pl["frames"] - float(t) * fps)})
    out = {"fps": fps, "frames": pl["frames"], "beat_frames": max(1, fps // 2), "style": "brand",
           "seed": seed, "sections": [{"name": "quick", "start": 0, "end": pl["frames"],
                                       "mood": "cold"}],
           "events": sorted(ev, key=lambda e: e["frame"]), "samples": samples}
    if music:
        out["track"] = {"path": str(d / SOUNDS["bed"]), "until": (pl["cut_s"] + 1 / 6) * fps,
                        "fade_out": 0.35, "gain": MUSIC_GAIN}
    return out


# ---------------------------------------------------------------------------- make it
def watermark(dst: Path, width: int, alpha: float = 0.42) -> Path:
    """The Bricks logo keyed off its cream ground, `width` px wide, at `alpha`."""
    from PIL import Image
    im = Image.open(paths.ROOT / "logo.png").convert("RGB")
    a = np.asarray(im).astype(np.float32)
    dist = np.linalg.norm(a - a[0, 0], axis=2)
    al = np.clip((dist - 22) / 40, 0, 1) * alpha
    rgba = np.dstack([a, al * 255]).astype(np.uint8)
    out = Image.fromarray(rgba, "RGBA")
    out = np.asarray(out.resize((width, int(round(width * im.height / im.width))), Image.LANCZOS)).copy()
    out[:, :, 3] = np.minimum(out[:, :, 3], int(round(alpha * 255)))   # no ringing over it
    Image.fromarray(out, "RGBA").save(dst)
    return dst


def make_quick(engine, proj, model, *, preview: bool = False, set_name: str | None = None,
               seconds: float | None = None, audio: bool = True, force: bool = False,
               stills: list[int] | None = None, device: str = "gpu", layers: dict | None = None,
               work: Path | None = None, remix: bool = False, cover: bool = False,
               log=None) -> Path:
    """Plan, render (render/blender_quick.py, under the GPU lock, a chunk of frames per
    Blender process, frames already made kept), add the sound and the logo, encode. `remix`:
    no planning or rendering - the frames there are (and the plan they were made from, even
    if the planner or the scripts have changed since), with the sound mixed again from
    [quick] as it is now (another ending, a bell, the music on or off). `cover`: nothing but
    the cover picture, picked again from those frames ([quick] cover)."""
    from . import _run_blender
    log = log or (lambda m: print(m, flush=True))
    t_start = time.time()
    qn = "preview" if preview else "full"
    q = QUALITY[qn]
    cfg = quick_config(proj.config, {"set": set_name, "seconds": seconds, **(layers or {})},
                       slug=proj.slug)
    fps, size = q["fps"], tuple(q["size"])
    samples = int(q["samples"] or cfg["samples"])
    out_dir = proj.out
    work = Path(work) if work else out_dir / "quick_frames" / qn
    work.mkdir(parents=True, exist_ok=True)
    if cover:
        if preview or not (work / "plan.json").exists():
            raise SystemExit(f"--cover: no full frames in {work} yet: render the video first")
        pl = json.loads((work / "plan.json").read_text())
        f = cover_frame(pl, cover_look(model, cfg))
        if not (work / f"{f:05d}.png").exists():
            raise SystemExit(f"--cover: frame {f} is missing in {work}: render the video first")
        wm = watermark(work / "logo.png", int(round(pl["size"][0] * 0.13))) if cfg["watermark"] else None
        poster(work, wm, pl, out_dir / "quick_poster.jpg", cover_look(model, cfg))
        log(f"{model.name}: cover -> {out_dir / 'quick_poster.jpg'} (frame {f})")
        return out_dir / "quick_poster.jpg"
    if remix:
        if not (work / "plan.json").exists():
            raise SystemExit(f"--remix: no frames in {work} yet: render the video first")
        pl = json.loads((work / "plan.json").read_text())
        gone = [f for f in range(pl["frames"]) if not (work / f"{f:05d}.png").exists()]
        if gone:
            raise SystemExit(f"--remix: {len(gone)} of {pl['frames']} frames are missing in {work}: "
                             "render the video first")
        log(f"{model.name}: quick video again from its {pl['frames']} frames, the sound mixed anew")
        return _finish(proj, model, cfg, pl, work, q, audio, preview, t_start, 0.0, log)
    pl = plan(engine, model, cfg, fps, size, log)
    wrong = clashes(engine, model.flatten(), pl)       # (the plan's own frames, checked)
    for line in report(model.flatten(), pl, wrong):
        log(line)
    script = Path(__file__).resolve().parent.parent / "render" / "blender_quick.py"
    stamp = hashlib.sha1(json.dumps([pl, samples, size], sort_keys=True, default=str).encode()
                         + script.read_bytes() + (script.parent / "quick_sets.py").read_bytes()
                         + (script.parent / "blender_scene.py").read_bytes()
                         + (script.parent / "blender_animate.py").read_bytes()
                         + (script.parent / "blender_cold_open.py").read_bytes()).hexdigest()
    sf = work / ".hash"
    if force or not sf.exists() or sf.read_text() != stamp:
        for f in work.glob("*.png"):
            f.unlink()
    sf.write_text(stamp)
    (work / "plan.json").write_text(json.dumps(pl))
    n = pl["frames"]
    log(f"{model.name}: quick video {n / fps:.1f} s at {fps} fps, {size[0]}x{size[1]}, set "
        f"{cfg['set']} ({cfg['surface']}, {cfg['room']}, {cfg['light']}), {len(pl['order'])} parts, close-ups on "
        f"{', '.join(model.flatten()[c['part']].part for c in pl['close_ups']) or 'none'}")
    want = sorted(stills) if stills else list(range(n))
    job = {"plan": str(work / "plan.json"), "frames": [[f, str(work / f"{f:05d}.png")] for f in want],
           "size": list(size), "samples": samples, "engine": "cycles", "device": device}
    secs = _run_blender(script, job, work / "job.json", "quick", log)
    if stills:
        log(f"stills -> {work}")
        return work
    for again in (True, True, False):                  # a patch gone black: those frames again
        runs = black_patches(work, n, pl["cut"])
        if not runs:
            break
        said = ", ".join(f"{a}-{b}" if b > a else str(a) for a, b in runs[:8])
        if not again:
            log(f"warning: a bright patch is flat black in frames {said}: look at them")
            break
        log(f"  quick: a bright patch went flat black in frames {said} (the GPU dropped a "
            f"material): rendering them again")
        for a, b in runs:
            for f in range(a, b + 1):
                (work / f"{f:05d}.png").unlink(missing_ok=True)
        secs += _run_blender(script, job, work / "job.json", "quick", log)
    return _finish(proj, model, cfg, pl, work, q, audio, preview, t_start, secs, log)


def cover_look(model, cfg: dict) -> float:
    """Where the cover is seen from (an azimuth): the model's front, [quick] cover from it."""
    return float(model.meta.get("azimuth_offset", 0.0)) + float(cfg.get("cover") or 0.0)


def _finish(proj, model, cfg: dict, pl: dict, work: Path, q: dict, audio: bool, preview: bool,
            t_start: float, secs: float, log) -> Path:
    """The frames in `work` (made from plan `pl`) -> the video: a check for blank frames, the
    sound from `cfg`, the logo if asked, the encode and the poster."""
    n, fps, size, out_dir = pl["frames"], pl["fps"], tuple(pl["size"]), proj.out
    blank = blank_frames(work, n)
    if blank:
        log(f"warning: {len(blank)} near-uniform frame(s) - the camera inside something? "
            f"{', '.join(map(str, blank[:12]))}{' ...' if len(blank) > 12 else ''}")
    wm = watermark(work / "logo.png", int(round(size[0] * 0.13))) if cfg["watermark"] else None
    wav = None
    if audio:
        from .audio import render_audio
        wav = work / "audio.wav"
        ending = None
        if cfg.get("ending"):
            f = proj.dir / str(cfg["ending"])
            if not f.is_file():
                raise SystemExit(f"[quick] ending: no file {f}")
            ending = {"path": f, "level": cfg["ending_level"], "at": cfg["ending_at"]}
        sounds, placed = [], model.flatten()
        for snd in cfg.get("sound") or []:
            f = proj.dir / str(snd["file"])
            if not f.is_file():
                raise SystemExit(f"[[quick.sound]] file: no file {f}")
            on = snd.get("on", "first")
            sounds.append({"path": f, "level": float(snd.get("level", -11.0)),
                           "times": [moment(model, placed, pl, o) + float(snd.get("at", 0.0))
                                     for o in (on if isinstance(on, list) else [on])]})
        st = render_audio(cues(pl, bool(cfg["music"]), ending=ending, sounds=sounds), wav,
                          lufs=LUFS, tp=TRUE_PEAK)
        log(f"sound: {st['seconds']:.1f} s at {st['lufs']:.1f} LUFS, true peak {st['true_peak_db']:.1f} dBTP")
    mp4 = out_dir / ("quick_preview.mp4" if preview else paths.video_name(proj.slug, *size))
    encode(work, fps, n, wm, wav, mp4, q, size)
    if wav is not None:
        from .sizzle import check_sound
        log(f"sound in the video: true peak {check_sound(mp4, wav, log=log):.1f} dBTP")
    if not preview:
        poster(work, wm, pl, out_dir / "quick_poster.jpg", cover_look(model, cfg))
    mb = mp4.stat().st_size / 1e6
    log(f"quick -> {mp4} ({mb:.1f} MB) in {(time.time() - t_start) / 60:.1f} min "
        f"(Blender {secs / 60:.1f} min)")
    if mb > MAX_MB:
        log(f"warning: {mp4.name} is {mb:.1f} MB (over {MAX_MB:.0f} MB)")
    return mp4


def blank_frames(work: Path, n: int, threshold: float = 5.0) -> list[int]:
    """Frames that are nearly one flat colour (their pixels' standard deviation, downscaled
    to 54 x 96, under `threshold` of 255): the camera inside a prop or a wall."""
    from PIL import Image
    out = []
    for f in range(n):
        path = work / f"{f:05d}.png"
        if not path.exists():
            continue
        with Image.open(path) as im:
            im.draft("RGB", (54, 96))
            a = np.asarray(im.convert("RGB").resize((54, 96), Image.BILINEAR), float)
        if float(a.std(axis=(0, 1)).mean()) < threshold:          # each channel's spread
            out.append(f)
    return out


def black_patches(work: Path, n: int, cut: int, least: int = 60) -> list[tuple[int, int]]:
    """Runs of frames [(first, last)] in which a bright patch is flat black: a material the GPU
    failed to draw. (Seen once, with the machine short of memory: a model's yellow feet went
    black for 18 frames, and were right again in the next Blender process.) A run starts where
    `least` pixels or more (of 270 x 480) go from bright to black between two frames, and
    ends where as many come back, or at the cut to the empty set."""
    from PIL import Image
    runs, prev, start = [], None, None
    for f in range(n):
        path = work / f"{f:05d}.png"
        if not path.exists():
            prev = None
            continue
        with Image.open(path) as im:
            im.draft("RGB", (270, 480))
            top = np.asarray(im.convert("RGB").resize((270, 480), Image.BILINEAR)).max(axis=2)
        bright, black = top > 120, top < 2             # (black plastic is never quite 0; this is)
        if prev is not None and abs(f - cut) > 2:
            if start is None and int((prev[0] & black).sum()) >= least:
                start = f
            elif start is not None and int((prev[1] & bright).sum()) >= least:
                runs.append((start, f - 1))
                start = None
        if start is not None and f == cut - 1:
            runs.append((start, f))
            start = None
        prev = (bright, black)
    if start is not None:
        runs.append((start, n - 1))
    return runs


def encode(work: Path, fps: int, n: int, wm: Path | None, wav: Path | None, mp4: Path, q: dict,
           size) -> None:
    """The frames (and the logo faint at the top in the middle, with a watermark), the sound:
    H.264 High profile (yuv420p, bt709, CRF 18 capped at 20 Mbit/s) + AAC 48 kHz, faststart."""
    ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
    y = int(round(size[1] * 0.045))
    cmd = [ffmpeg, "-v", "error", "-y", "-framerate", str(fps), "-i", str(work / "%05d.png")]
    if wm is not None:
        cmd += ["-i", str(wm)]
    if wav is not None:
        cmd += ["-i", str(wav)]
    tail = "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p[v]"
    graph = f"[0:v][1:v]overlay=(W-w)/2:{y}:format=auto,{tail}" if wm is not None else f"[0:v]{tail}"
    cmd += ["-filter_complex", graph, "-map", "[v]"]
    if wav is not None:
        cmd += ["-map", f"{2 if wm is not None else 1}:a", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                "-shortest"]
    cmd += ["-r", str(fps), "-frames:v", str(n), "-c:v", "libx264", "-profile:v", "high",
            "-preset", "slow", "-crf", str(q["crf"]),
            "-maxrate", q["maxrate"], "-bufsize", str(int(q["maxrate"][:-1]) * 2) + "k",
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
            "-color_range", "tv", "-movflags", "+faststart", str(mp4)]
    subprocess.run(cmd, check=True)


COVER_SHARP = 0.0075  # of the frame's width: the most the picture may move while the shutter is
#                       open, in a frame fit for the cover (8 px at 1080)


def _cover_blur(pl: dict, first: int, last: int) -> np.ndarray:
    """How far the model moves in the picture while the shutter is open (180 degrees: half a
    frame), in frame widths, for frames first..last: the most of seven points, the model's
    middle and six round it. The camera turning is little; the camera on its way out of a
    close-up is a smear."""
    cam = pl["camera"]
    pos, tgt = np.asarray(cam["pos"], float), np.asarray(cam["target"], float)
    lens = np.asarray(cam.get("lens") or np.full(len(pos), 50.0), float)
    r = 0.25 * np.linalg.norm(pos[last] - tgt[last])
    P = tgt[last] + r * np.array([[0, 0, 0], [1, 0, 0], [-1, 0, 0], [0, 0, 1], [0, 0, -1],
                                  [0, -1, 0], [0, 1, 0]], float)

    def screen(k):
        fwd = tgt[k] - pos[k]
        fwd = fwd / np.linalg.norm(fwd)
        right = np.cross(fwd, [0.0, -1.0, 0.0])
        right = right / np.linalg.norm(right)
        v = P - pos[k]
        return np.column_stack((v @ right, v @ np.cross(right, fwd))) / (v @ fwd)[:, None] * lens[k] / 36.0

    at = {k: screen(k) for k in range(max(first - 1, 0), last + 1)}
    out = []
    for f in range(first, last + 1):
        lo, hi = max(f - 1, min(at)), min(f + 1, last)
        out.append(0.5 * np.linalg.norm(at[hi] - at[lo], axis=1).max() / max(1, hi - lo))
    return np.array(out)


def cover_frame(pl: dict, look: float = 0.0) -> int:
    """The frame for the cover: of the hero the one the camera is nearest `look` in (an
    azimuth, degrees: the model's front, or [quick] cover from it) - its face forward, not
    whatever side the turn is on half way. The hero: from the last landing to the cut, the
    frames in which the model is whole (every piece where it ends up: nothing still to be
    joined), framed as it is at the end (not still in a close-up, or on the way out of
    one) and sharp (COVER_SHARP; else the sharpest there is). Of frames as near (within a
    degree), the last."""
    cam = pl["camera"]
    pos, tgt = np.asarray(cam["pos"], float), np.asarray(cam["target"], float)
    first, cut = int(pl["land"][-1]), int(pl["cut"])
    last = cut - 1
    d = pos - tgt
    dist = np.linalg.norm(d, axis=1)
    wide = dist / np.asarray(cam.get("lens") or np.ones(len(dist)), float)   # how much it takes in
    ok = (wide >= 0.9 * wide[last]) & (np.linalg.norm(tgt - tgt[last], axis=1) <= 0.1 * dist[last])
    for f in range(last - 1, first - 1, -1):           # back from the cut, to the last move
        if not all(np.allclose(pose_at(pl, i, f), pose_at(pl, i, last), atol=1e-3)
                   for i in range(len(pl.get("parts") or ()))):
            first = f + 1
            break
    ok = ok[first:cut]
    blur = _cover_blur(pl, first, last)
    sharp = ok & (blur <= COVER_SHARP)
    ok = sharp if sharp.any() else ok & (blur <= blur[ok].min() + 1e-9)
    off = np.abs((np.degrees(np.arctan2(d[:, 0], -d[:, 2])) - look + 180.0) % 360.0 - 180.0)
    off = np.where(ok, off[first:cut], np.inf)
    return first + int(np.flatnonzero(off <= off.min() + 1.0)[-1])


def poster(work: Path, wm: Path | None, pl: dict, dst: Path, look: float = 0.0) -> int:
    """The cover: the finished model, face forward (cover_frame), with the logo if there is a
    watermark. Returns the frame."""
    from PIL import Image
    f = cover_frame(pl, look)
    im = Image.open(work / f"{f:05d}.png").convert("RGBA")
    if wm is not None:
        logo = Image.open(wm)
        im.alpha_composite(logo, ((im.width - logo.width) // 2, int(round(im.height * 0.045))))
    im.convert("RGB").save(dst, quality=90)
    return f
