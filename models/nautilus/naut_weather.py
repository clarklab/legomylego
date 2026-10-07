"""Weathering: the iron hull isn't one flat brown. Once the hull is built, the plates and tiles
on its outside (not the core and walls inside it) are recoloured in colour zones and then plate
by plate. The zones (SCHEMES) pick out the hull's iron frame: the side keels' edges and their
teeth, the deck's walkway and the keel. Then the plating is cut into strakes, as a riveted hull
is plated: each side panel or quarter skin is one plate (elsewhere bands round the hull about
ten studs long, staggered like brickwork), and a few plates are darker iron. Every part in a
plate takes its colour, so a colour change is always a whole plate's worth of tiles - never a
checkerboard, stripes or single dots.

A part only takes a zone's or strake's colour when it is made in that colour in every colourway
(the roles frame_iron, hull_lower, hull_dark, hull_rust and hull_iron in model.toml's palette
and its variants); otherwise it stays the hull's colour. The salon's furniture, the crew, the
stand and whatever `skip` names (the superstructure, kept clean) aren't touched.

SCHEME picks the look: "iron_frame" (the model's), or "weathered" (no frame, more and rustier
plates) and "two_tone" (the frame and a darker lower hull), the alternatives it was chosen from;
NAUT_SCHEME in the environment overrides it for a test build."""
from __future__ import annotations

import math
import os

import numpy as np

from brickkit.model.builder import Placement, Use
import naut_shape as shp
from naut_kit import AV, bbox

SEED = 1954
STRAKE_L = 200.0                  # a strake's length along the hull (ten studs)
STRAKE_A = 30                     # strakes round the hull (about two tiles wide each)
MIN_PARTS = 3                     # a strake of fewer parts stays as it is (no lone dark tiles)
MAX_PARTS = 120                   # nor a bigger one (a whole bow module darker)
# strakes: (role, share of the strakes, where it may go ((x, y, z) of a strake's middle -> bool))
PATCHES = (                       # the "weathered" scheme's
    ("hull_iron", 0.35, lambda c: c[1] < -150 and abs(c[2]) < 100),   # the deck, worn bare
    ("hull_dark", 0.14, lambda c: c[1] > -150),
    ("hull_rust", 0.04, lambda c: -150 < c[1] < 60),
)
# colour zones, before the strakes: (role, (x, y, z) of an outside part's middle -> bool)
FLANGE = lambda c: -24 < c[1] < 16 and abs(c[2]) > shp.flange_hw(c[0]) - 45   # side keels
DECK = lambda c: (-200 < c[1] < -150 and abs(c[2]) < shp.deck_hw(c[0]) + 5
                  and shp.QUARTER_DECK_FWD <= c[0] < 900)        # the deck's walkway
KEEL = lambda c: c[1] > 140 and abs(c[2]) < 70                   # the keel strip, the saw keel
LOWER = lambda c: c[1] > 16                                      # under the side keels
SCHEMES = {
    "weathered": dict(zones=(), patches=PATCHES),
    "iron_frame": dict(zones=(("frame_iron", FLANGE), ("frame_iron", DECK),
                              ("frame_iron", KEEL)),
                       patches=()),       # darker plates came out as dots, stripes or
                                          # patchy panels (the hinges' tiles and wedge plates
                                          # stay Reddish Brown): the frame alone
    "two_tone": dict(zones=(("frame_iron", FLANGE), ("frame_iron", DECK), ("frame_iron", KEEL),
                            ("hull_lower", LOWER)),
                     patches=(("hull_dark", 0.10, lambda c: c[1] < 16),
                              ("hull_rust", 0.03, lambda c: -150 < c[1] < 16))),
}
SCHEME = os.environ.get("NAUT_SCHEME", "iron_frame")
X_BIN, A_BINS = 20.0, 64          # the outside's envelope: x bins, angle bins round the axis
SKIN = 16.0                       # a part within this of the envelope is on the outside


def _samples(part: str, M: np.ndarray) -> np.ndarray:
    lo, hi = bbox(part)
    g = [np.linspace(lo[i], hi[i], 3) for i in range(3)]
    pts = np.array([[x, y, z] for x in g[0] for y in g[1] for z in g[2]])
    return pts @ M[:3, :3].T + M[:3, 3]


def _angle(pts: np.ndarray) -> np.ndarray:
    return (np.arctan2(pts[..., 1], pts[..., 2]) + math.pi) / (2 * math.pi)     # 0..1


def _polar(pts: np.ndarray):
    xb = np.floor(pts[:, 0] / X_BIN).astype(int)
    r = np.hypot(pts[:, 1], pts[:, 2])
    a = (_angle(pts) * A_BINS).astype(int) % A_BINS
    return xb, a, r


def weather(model, root, skip=lambda name: False) -> dict:
    """Recolour the outside of `root` (the hull, in its own frame). `skip(name)`: sub-assemblies
    left alone. Returns {role: parts recoloured}."""
    base = model.resolve_color("hull")
    seen, found = set(), []    # (placement, sample points, skipped, owner) of the hull's parts

    def walk(sub, M, skipped):
        if sub.name in seen:
            return
        seen.add(sub.name)
        for it in sub.items:
            if isinstance(it, Use):
                walk(it.sub, M @ it.M, skipped or skip(it.sub.name))
            elif isinstance(it, Placement):
                found.append((it, _samples(it.part, M @ it.M), skipped,
                              None if sub is root else sub.name))
    walk(root, np.eye(4), False)

    env = {}                         # the outermost radius in each (x, angle) bin
    for _, pts, *_ in found:
        for xb, a, r in zip(*_polar(pts)):
            if r > env.get((xb, a), 0.0):
                env[(xb, a)] = r
    scheme = SCHEMES[SCHEME]
    rng = np.random.default_rng(SEED)
    offset = rng.uniform(0, STRAKE_L, STRAKE_A)        # each band's joints, staggered
    strakes: dict = {}
    done = {}
    for p, pts, skipped, owner in found:
        if skipped or p.color != base:
            continue
        xb, a, r = _polar(pts)
        if not any(r[j] >= env[(xb[j], a[j])] - SKIN for j in range(len(r))):
            continue                                    # inside the hull
        c = pts.mean(0)
        zone = next((role for role, inside in scheme["zones"] if inside(c)), None)
        if zone is not None:
            if AV.ok(p.part, zone):
                p.color = model.resolve_color(zone)
                done[zone] = done.get(zone, 0) + 1
            continue
        band = int(_angle(c) * STRAKE_A) % STRAKE_A
        # a side panel or a quarter's skin (a sub-assembly) is one plate: it changes colour
        # whole, its edges the panel's (bands across a panel came out as stripes where its tiles
        # run across them); elsewhere bands are cut every STRAKE_L, staggered
        key = owner or (band, int(math.floor((c[0] + offset[band]) / STRAKE_L)))
        strakes.setdefault(key, []).append((p, c))

    keys = sorted(strakes, key=str)
    order = rng.permutation(len(keys))
    free = set(keys)
    for role, share, where in scheme["patches"]:
        col = model.resolve_color(role)
        ok = [keys[j] for j in order if keys[j] in free
              and MIN_PARTS <= len(strakes[keys[j]]) <= MAX_PARTS
              and where(np.mean([c for _, c in strakes[keys[j]]], axis=0))]
        n = 0
        for key in ok[:round(share * len(ok))]:
            free.discard(key)
            for p, _ in strakes[key]:
                if AV.ok(p.part, role):
                    p.color = col
                    n += 1
        done[role] = n
    return done
