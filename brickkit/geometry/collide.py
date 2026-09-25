"""Mesh collisions via FCL on shrunk meshes: faces move `shrink` LDU inward and are inset
in their own plane by the same amount, so parts that only touch never register."""
from __future__ import annotations

import fcl
import numpy as np

from ..ldraw.geometry import GeometryCache


def shrink_tris(T: np.ndarray, d: float) -> np.ndarray:
    if len(T) == 0:
        return T
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    L = np.linalg.norm(n, axis=1)
    keep = L > 1e-9
    T, n, L = T[keep], n[keep] / L[keep, None], L[keep]
    a = np.linalg.norm(T[:, 1] - T[:, 2], axis=1)
    b = np.linalg.norm(T[:, 2] - T[:, 0], axis=1)
    c = np.linalg.norm(T[:, 0] - T[:, 1], axis=1)
    per = a + b + c
    r = L / np.maximum(per, 1e-12)            # inradius = 2*area/perimeter, area = L/2
    inc = (a[:, None] * T[:, 0] + b[:, None] * T[:, 1] + c[:, None] * T[:, 2]) / per[:, None]
    k = 1 - d / np.maximum(r, 1e-12)
    ok = k > 0
    T = inc[:, None, :] + (T - inc[:, None, :]) * np.clip(k, 0, 1)[:, None, None]
    return (T - d * n[:, None, :])[ok]


class CollisionEngine:
    def __init__(self, geom: GeometryCache, shrink: float = 0.25):
        self.geom = geom
        self.shrink = shrink
        self._bvh: dict[str, object] = {}
        self._corners: dict[str, np.ndarray] = {}

    def _model(self, part: str):
        if part not in self._bvh:
            mesh = self.geom.mesh(part)
            S = shrink_tris(mesh.tris, self.shrink)
            if len(S) == 0:
                self._bvh[part] = None
            else:
                V = np.ascontiguousarray(S.reshape(-1, 3))
                F = np.arange(len(V), dtype=np.int32).reshape(-1, 3)
                m = fcl.BVHModel()
                m.beginModel(len(V), len(F))
                m.addSubModel(V, F)
                m.endModel()
                self._bvh[part] = m
            lo, hi = mesh.bbox
            self._corners[part] = np.array([[x, y, z] for x in (lo[0], hi[0])
                                            for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
        return self._bvh[part]

    def world_aabb(self, part: str, M: np.ndarray) -> np.ndarray:
        self._model(part)
        pts = self._corners[part] @ M[:3, :3].T + M[:3, 3]
        return np.stack([pts.min(0), pts.max(0)])

    def aabbs(self, items) -> np.ndarray:
        if not items:
            return np.zeros((0, 2, 3))
        return np.stack([self.world_aabb(p, M) for p, M in items])

    def collide_pair(self, pa: str, Ma: np.ndarray, pb: str, Mb: np.ndarray) -> bool:
        a, b = self._model(pa), self._model(pb)
        if a is None or b is None:
            return False
        oa = fcl.CollisionObject(a, fcl.Transform(Ma[:3, :3], Ma[:3, 3]))
        ob = fcl.CollisionObject(b, fcl.Transform(Mb[:3, :3], Mb[:3, 3]))
        return fcl.collide(oa, ob, fcl.CollisionRequest(), fcl.CollisionResult()) > 0

    def _candidates(self, box: np.ndarray, boxes: np.ndarray) -> np.ndarray:
        m = 2 * self.shrink
        ok = np.all((boxes[:, 0] < box[1] - m) & (box[0] < boxes[:, 1] - m), axis=1)
        return np.nonzero(ok)[0]

    def pairs(self, items, only: set[int] | None = None) -> list[tuple[int, int]]:
        boxes = self.aabbs(items)
        out = []
        for i in range(len(items)):
            for j in self._candidates(boxes[i], boxes):
                j = int(j)
                if j <= i or (only is not None and i not in only and j not in only):
                    continue
                if self.collide_pair(items[i][0], items[i][1], items[j][0], items[j][1]):
                    out.append((i, j))
        return out

    def hits(self, part: str, M: np.ndarray, items, boxes: np.ndarray | None = None) -> bool:
        if not items:
            return False
        boxes = self.aabbs(items) if boxes is None else boxes
        for j in self._candidates(self.world_aabb(part, M), boxes):
            if self.collide_pair(part, M, items[j][0], items[j][1]):
                return True
        return False
