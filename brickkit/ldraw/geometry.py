"""Flatten LDraw parts into triangle meshes, honouring BFC winding (CCW = outward)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .library import LDrawLibrary, normalize
from .matrix import is_mirror, parse_color, parse_type1


@dataclass
class Mesh:
    tris: np.ndarray         # (N,3,3) float64
    colors: np.ndarray       # (N,) int32; 16 = the part's main colour
    edges: np.ndarray        # (E,2,3) type-2 lines
    edge_colors: np.ndarray  # (E,) int32; 24 = edge colour of the main colour
    cond: np.ndarray         # (C,4,3) type-5 conditional lines
    certified: bool          # winding is trustworthy for every triangle

    @property
    def bbox(self) -> tuple[np.ndarray, np.ndarray]:
        if len(self.tris) == 0:
            return np.zeros(3), np.zeros(3)
        pts = self.tris.reshape(-1, 3)
        return pts.min(0), pts.max(0)

    def volume_centroid(self) -> tuple[float, np.ndarray]:
        if len(self.tris) == 0:
            return 0.0, np.zeros(3)
        a, b, c = self.tris[:, 0], self.tris[:, 1], self.tris[:, 2]
        v = np.einsum("ij,ij->i", a, np.cross(b, c)) / 6.0
        V = float(v.sum())
        if abs(V) < 1e-9:
            return 0.0, (a + b + c).mean(0) / 3.0
        return V, (v[:, None] * (a + b + c) / 4.0).sum(0) / V


def _empty(certified: bool = True) -> Mesh:
    return Mesh(np.zeros((0, 3, 3)), np.zeros(0, np.int32), np.zeros((0, 2, 3)),
                np.zeros(0, np.int32), np.zeros((0, 4, 3)), certified)


def _cat(arrs, shape, dtype=float):
    return np.concatenate(arrs).astype(dtype) if arrs else np.zeros(shape, dtype)


class GeometryCache:
    def __init__(self, lib: LDrawLibrary, cache_dir: Path | None = None):
        self.lib = lib
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self._mem: dict[str, Mesh] = {}
        self._sub: dict[str, Mesh] = {}
        self.missing: set[str] = set()

    def mesh(self, name: str) -> Mesh:
        key = normalize(name)
        if key in self._mem:
            return self._mem[key]
        m = self._load(key)
        if m is None:
            m = self._flatten(key, ())
            self._save(key, m)
        self._mem[key] = m
        return m

    def _cache_file(self, key: str) -> Path | None:
        return self.cache_dir / (key.replace("/", "__") + ".npz") if self.cache_dir else None

    def _load(self, key: str) -> Mesh | None:
        f = self._cache_file(key)
        src = self.lib.resolve(key)
        if f is None or not f.exists() or src is None or f.stat().st_mtime < src.stat().st_mtime:
            return None
        d = np.load(f)
        return Mesh(d["tris"], d["colors"], d["edges"], d["edge_colors"], d["cond"],
                    bool(d["certified"]))

    def _save(self, key: str, m: Mesh) -> None:
        f = self._cache_file(key)
        if f is None or key in self.missing:
            return
        f.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(f, tris=m.tris, colors=m.colors, edges=m.edges,
                            edge_colors=m.edge_colors, cond=m.cond, certified=m.certified)

    def _flatten(self, key: str, stack: tuple) -> Mesh:
        if key in self._sub:
            return self._sub[key]
        path = self.lib.resolve(key)
        if path is None:
            self.missing.add(key)
            return _empty(False)
        tris, cols, edges, ecols, conds = [], [], [], [], []
        certified = nocert = False
        ccw = True
        invert_next = False
        subs_certified = True
        with open(path, encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                t = raw.split()
                if not t:
                    continue
                kind = t[0]
                if kind == "0":
                    if len(t) >= 2 and t[1] == "BFC":
                        rest = [w.upper() for w in t[2:]]
                        if "NOCERTIFY" in rest:
                            nocert = True
                        elif "CERTIFY" in rest:
                            certified = True
                        if "CW" in rest:
                            ccw = False
                        if "CCW" in rest:
                            ccw = True
                        if "INVERTNEXT" in rest:
                            invert_next = True
                    continue
                if kind == "1" and len(t) >= 15:
                    color, M, sub = parse_type1(t)
                    subkey = normalize(sub)
                    inv = invert_next ^ is_mirror(M)
                    invert_next = False
                    if subkey in stack:
                        continue
                    sm = self._flatten(subkey, stack + (key,))
                    subs_certified = subs_certified and sm.certified
                    R, T = M[:3, :3].T, M[:3, 3]
                    if len(sm.tris):
                        pts = sm.tris @ R + T
                        tris.append(pts[:, ::-1] if inv else pts)
                        c = sm.colors.copy()
                        if color != 16:
                            c[c == 16] = color
                        cols.append(c)
                    if len(sm.edges):
                        edges.append(sm.edges @ R + T)
                        ec = sm.edge_colors.copy()
                        if color != 16:
                            ec[ec == 16] = color
                        ecols.append(ec)
                    if len(sm.cond):
                        conds.append(sm.cond @ R + T)
                elif kind == "3" and len(t) >= 11:
                    p = np.array(t[2:11], float).reshape(1, 3, 3)
                    tris.append(p if ccw else p[:, ::-1])
                    cols.append(np.array([parse_color(t[1])], np.int32))
                elif kind == "4" and len(t) >= 14:
                    q = np.array(t[2:14], float).reshape(4, 3)
                    pair = np.stack([q[[0, 1, 2]], q[[0, 2, 3]]])
                    tris.append(pair if ccw else pair[:, ::-1])
                    cols.append(np.full(2, parse_color(t[1]), np.int32))
                elif kind == "2" and len(t) >= 8:
                    edges.append(np.array(t[2:8], float).reshape(1, 2, 3))
                    ecols.append(np.array([parse_color(t[1])], np.int32))
                elif kind == "5" and len(t) >= 14:
                    conds.append(np.array(t[2:14], float).reshape(1, 4, 3))
        m = Mesh(_cat(tris, (0, 3, 3)), _cat(cols, (0,), np.int32), _cat(edges, (0, 2, 3)),
                 _cat(ecols, (0,), np.int32), _cat(conds, (0, 4, 3)),
                 certified and not nocert and subs_certified)
        self._sub[key] = m
        return m
