"""Can a piece be seen in a picture? The instruction pictures are orthographic, so every line
of sight is parallel: points are scattered over a part's surface and each is followed towards
the camera; the part is seen as far as its points get there past everything else that is
shown - measured against the part alone, which hides half of itself (its far side)."""
from __future__ import annotations

import math

import numpy as np

SAMPLES = 96          # points on each part
LIFT = 0.6            # LDU a point starts off its own surface, towards the camera
BEHIND = 0.25         # LDU something must be in front of a point to hide it


def axes(azimuth: float, elevation: float) -> np.ndarray:
    """The picture's right, up and towards-the-camera (rows), in LDraw's frame, for the
    instruction renderer's azimuth and elevation (degrees; 0 = from the front, -Z)."""
    a, e = math.radians(azimuth), math.radians(elevation)
    toward = np.array([math.sin(a) * math.cos(e), -math.sin(e), -math.cos(a) * math.cos(e)])
    right = np.cross([0.0, -1.0, 0.0], toward)
    right /= np.linalg.norm(right)
    return np.array([right, np.cross(toward, right), toward])


def _hidden(points: np.ndarray, tris: np.ndarray) -> np.ndarray:
    """Which points (k, 3: across, up, towards the camera) have a triangle (t, 3, 3) between
    them and the camera."""
    out = np.zeros(len(points), bool)
    for at in range(0, len(tris), 4000):               # (in slices: k x t numbers at a time)
        t = tris[at:at + 4000]
        a, v0, v1 = t[:, 0, :2], t[:, 2, :2] - t[:, 0, :2], t[:, 1, :2] - t[:, 0, :2]
        d00, d01, d11 = (v0 * v0).sum(1), (v0 * v1).sum(1), (v1 * v1).sum(1)
        den = d00 * d11 - d01 * d01
        ok = np.abs(den) > 1e-9                        # (edge on to the camera: hides nothing)
        den = np.where(ok, den, 1.0)
        v2 = points[:, None, :2] - a[None]
        d20, d21 = (v2 * v0[None]).sum(2), (v2 * v1[None]).sum(2)
        u = (d11 * d20 - d01 * d21) / den
        v = (d00 * d21 - d01 * d20) / den
        z = t[None, :, 0, 2] + u * (t[None, :, 2, 2] - t[None, :, 0, 2]) + v * (t[None, :, 1, 2] - t[None, :, 0, 2])
        hit = ok[None] & (u >= -1e-6) & (v >= -1e-6) & (u + v <= 1 + 1e-6) & (z > points[:, None, 2] + BEHIND)
        out |= hit.any(1)
    return out


class Sight:
    """What can be seen of a set of parts from one direction. parts: [(part, 4 x 4)]."""

    def __init__(self, engine, parts, azimuth: float, elevation: float, samples: int = SAMPLES):
        B = axes(azimuth, elevation)
        self.tris, self.box, self.points, self.alone = [], [], [], []
        for n, (part, M) in enumerate(parts):
            M = np.asarray(M, float)
            t = engine.geom.mesh(part).tris
            if not len(t):
                self.tris.append(np.zeros((0, 3, 3)))
                self.box.append(np.zeros((2, 2)))
                self.points.append(np.zeros((0, 3)))
                self.alone.append(0.0)
                continue
            t = (t @ M[:3, :3].T + M[:3, 3]) @ B.T      # (across, up, towards the camera)
            self.tris.append(t)
            flat = t.reshape(-1, 3)
            self.box.append(np.array([flat[:, :2].min(0), flat[:, :2].max(0)]))
            area = np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]), axis=1)
            rng = np.random.default_rng(n)
            pick = rng.choice(len(t), samples, p=area / area.sum()) if area.sum() > 0 else np.zeros(samples, int)
            r1, r2 = np.sqrt(rng.random(samples)), rng.random(samples)
            p = ((1 - r1)[:, None] * t[pick, 0] + (r1 * (1 - r2))[:, None] * t[pick, 1]
                 + (r1 * r2)[:, None] * t[pick, 2])
            p[:, 2] += LIFT
            self.points.append(p)
            self.alone.append(float((~_hidden(p, t)).mean()))

    def seen(self, n: int, shown) -> float:
        """How much of part n shows with the parts `shown` there (n among them or not): 1 as
        much as it ever can, 0 nothing."""
        if self.alone[n] <= 0:
            return 1.0
        lo, hi = self.box[n]
        near = [m for m in set(shown) | {n} if len(self.tris[m])
                and np.all(self.box[m][0] < hi + 0.5) and np.all(self.box[m][1] > lo - 0.5)]
        hidden = _hidden(self.points[n], np.concatenate([self.tris[m] for m in near]))
        return float((~hidden).mean()) / self.alone[n]
