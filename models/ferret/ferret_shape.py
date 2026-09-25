"""The ferret's volume: a tube swept along an arched spine (the running "hunch"), plus four
limb capsules, sampled on the stud grid in brick-high layers.

Units here are millimetres (1 stud = 8 mm, 1 brick = 9.6 mm); the design converts to LDU
(1 LDU = 0.4 mm). Height `h` is measured up from the ground; `z` runs from the nose (z = 0)
towards the tail; `x` is lateral (0 = the ferret's midline)."""
from __future__ import annotations

import numpy as np

STUD = 8.0          # mm
BRICK = 9.6         # mm

# Spine nodes: (z, centre height, half-width, half-height), all in mm.
# Head low and forward, back arched high in the middle, rump dropping into a thick tail.
SPINE = [
    (0.0, 88.0, 5.0, 5.0),      # nose tip (the head itself is built apart: ferret_head)
    (16.0, 90.0, 12.0, 12.0),   # muzzle
    (38.0, 94.0, 19.0, 17.0),   # eyes
    (62.0, 97.0, 25.0, 21.0),   # cheeks, ears
    (82.0, 96.0, 24.0, 21.0),   # back of the skull
    (104.0, 88.0, 23.0, 22.0),  # neck, rising to hold the head up
    (130.0, 78.0, 27.0, 27.0),  # base of the neck
    (158.0, 74.0, 30.0, 31.0),  # shoulders, deep chest
    (200.0, 96.0, 31.0, 30.0),
    (246.0, 116.0, 31.0, 28.0), # top of the arch
    (290.0, 112.0, 31.0, 28.0),
    (332.0, 90.0, 30.0, 29.0),  # hips
    (366.0, 78.0, 27.0, 27.0),
    (394.0, 80.0, 21.0, 21.0),  # rump / tail root
    (424.0, 86.0, 18.0, 17.0),  # thick, bushy tail
    (458.0, 92.0, 15.0, 14.0),
    (488.0, 96.0, 11.0, 11.0),
    (506.0, 96.0, 7.0, 8.0),    # tail tip (on a layer boundary: always two layers deep)
]

# Limb capsules: chains of (x, h, z, radius) in mm (left side; mirrored to the right).
LIMBS = {
    "front": [(17.0, 64.0, 150.0, 15.0), (16.0, 42.0, 157.0, 12.0), (16.0, 16.0, 160.0, 9.0)],
    "hind": [(18.0, 78.0, 336.0, 19.0), (17.0, 50.0, 350.0, 13.0), (16.0, 16.0, 352.0, 9.0)],
}


def _catmull(P: np.ndarray, n: int = 24) -> np.ndarray:
    """Uniform Catmull-Rom through the rows of P, n samples per segment."""
    P = np.vstack([P[0] * 2 - P[1], P, P[-1] * 2 - P[-2]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for t in np.linspace(0, 1, n, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-2])
    return np.array(out)


_SPINE = _catmull(np.array(SPINE, float))


def _limb_samples():
    out = []
    for chain in LIMBS.values():
        C = np.array(chain, float)
        for a, b in zip(C[:-1], C[1:]):
            for t in np.linspace(0, 1, 12):
                out.append(a + (b - a) * t)
    L = np.array(out)
    R = L.copy()
    R[:, 0] *= -1
    return np.vstack([L, R])


_LIMBS = _limb_samples()


def body_dist(x, h, z) -> np.ndarray:
    """Normalised distance (<= 1 inside) to the swept body tube (union of ellipsoids)."""
    x, h, z = (np.asarray(v, float)[..., None] for v in (x, h, z))
    zs, hs, a, b = _SPINE[:, 0], _SPINE[:, 1], _SPINE[:, 2], _SPINE[:, 3]
    return ((x / a) ** 2 + ((h - hs) ** 2 + (z - zs) ** 2) / b ** 2).min(-1)


def limb_dist(x, h, z) -> np.ndarray:
    x, h, z = (np.asarray(v, float)[..., None] for v in (x, h, z))
    L = _LIMBS
    return (((x - L[:, 0]) ** 2 + (h - L[:, 1]) ** 2 + (z - L[:, 2]) ** 2) / L[:, 3] ** 2).min(-1)


def inside(x, h, z) -> np.ndarray:
    return np.minimum(body_dist(x, h, z), limb_dist(x, h, z))


def voxels(x_cells, z_cells, layers, limit=1.0):
    """Boolean grid [layer, z, x] of cells whose centre is inside the ferret."""
    X = (np.asarray(x_cells) + 0.5) * STUD
    Z = (np.asarray(z_cells) + 0.5) * STUD
    H = (np.asarray(layers) + 0.5) * BRICK
    hh, zz, xx = np.meshgrid(H, Z, X, indexing="ij")
    return inside(xx, hh, zz) <= limit
