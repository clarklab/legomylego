"""Resolve LDCad `!LDCAD SNAP_*` metas for a part through its LDraw subfile tree."""
from __future__ import annotations

import itertools
import re
from dataclasses import replace

import numpy as np

from ..ldraw.library import FileIndex, LDrawLibrary, normalize
from ..ldraw.matrix import parse_type1
from .connector import Connector

META_RE = re.compile(r"^0\s+!LDCAD\s+(SNAP_\w+)\s*(.*)$")
PARAM_RE = re.compile(r"\[(\w+)=([^\]]*)\]")
KINDS = {"SNAP_CYL": "cyl", "SNAP_CLP": "clp", "SNAP_FGR": "fgr", "SNAP_GEN": "gen",
         "SNAP_SPH": "gen"}


def _floats(s: str) -> list[float]:
    return [float(x) for x in s.split()]


def _bool(s) -> bool:
    return str(s).strip().lower() == "true"


def _frame(P: dict) -> np.ndarray:
    M = np.eye(4)
    if "ori" in P:
        M[:3, :3] = np.array(_floats(P["ori"])).reshape(3, 3)
    if "pos" in P:
        M[:3, 3] = _floats(P["pos"])
    return M


def _secs(s: str) -> tuple:
    t = s.split()
    return tuple((t[i], float(t[i + 1]), float(t[i + 2])) for i in range(0, len(t) - 2, 3))


def grid_frames(spec: str | None) -> list[np.ndarray]:
    """Expand `[C] Xcnt [C] Zcnt Xstep Zstep` (or the 3-axis form) into offset frames."""
    if not spec:
        return [np.eye(4)]
    vals, centered, c = [], [], False
    for tok in spec.split():
        if tok.upper() == "C":
            c = True
            continue
        vals.append(float(tok))
        centered.append(c)
        c = False
    if len(vals) == 4:
        counts, flags, steps, axes = vals[:2], centered[:2], vals[2:], (0, 2)
    elif len(vals) == 6:
        counts, flags, steps, axes = vals[:3], centered[:3], vals[3:], (0, 1, 2)
    else:
        raise ValueError(f"unsupported grid spec {spec!r}")
    ranges = []
    for cnt, cf, st in zip(counts, flags, steps):
        n = int(cnt)
        off = -(n - 1) * st / 2 if cf else 0.0
        ranges.append([off + k * st for k in range(n)])
    frames = []
    for combo in itertools.product(*ranges):
        G = np.eye(4)
        for ax, v in zip(axes, combo):
            G[ax, 3] = v
        frames.append(G)
    return frames


def _make(kind: str, P: dict) -> Connector:
    k = KINDS[kind]
    gender = "F" if kind == "SNAP_CLP" else P.get("gender", "M").strip().upper()[:1]
    if kind == "SNAP_FGR":
        gender = P.get("genderofs", "M").strip().upper()[:1]
    bounding = tuple(P.get("bounding", "").split())
    if kind == "SNAP_SPH":
        bounding = ("sph", P.get("radius", "0"))
    return Connector(
        kind=k, gender=gender, M=np.eye(4), secs=_secs(P.get("secs", "")),
        caps=P.get("caps", "one").lower(), center=_bool(P.get("center")),
        slide=_bool(P.get("slide")), group=P.get("group", "").lower(),
        cid=P.get("id", "").lower(),
        radius=float(P.get("radius", 4.0 if kind == "SNAP_CLP" else 0.0)),
        length=float(P.get("length", 8.0 if kind == "SNAP_CLP" else 0.0)),
        seq=tuple(_floats(P.get("seq", ""))), bounding=bounding,
        scale_rule=P.get("scale", "none").lower(),
        mirror_rule=P.get("mirror", "cor" if kind == "SNAP_CYL" else "none").lower())


def place(c: Connector, W: np.ndarray) -> Connector | None:
    """Apply a (possibly scaled or mirrored) transform, following the snap's scale/mirror rules."""
    F = W @ c.M
    R = F[:3, :3].copy()
    sx, sy, sz = np.linalg.norm(R, axis=0)
    if min(sx, sy, sz) < 1e-9:
        return None
    if np.linalg.det(R) < 0:
        if c.mirror_rule == "none":
            return None
        R[:, 0] = -R[:, 0]
    y_scaled = abs(sy - 1) > 1e-4
    r_scaled = abs(sx - 1) > 1e-4 or abs(sz - 1) > 1e-4
    if y_scaled and c.scale_rule not in ("yonly", "yandr"):
        return None
    if r_scaled and c.scale_rule not in ("ronly", "yandr"):
        return None
    out = np.eye(4)
    out[:3, :3] = R / np.array([sx, sy, sz])
    out[:3, 3] = F[:3, 3]
    ky = sy if y_scaled else 1.0
    kr = sx if r_scaled else 1.0
    return replace(c, M=out,
                   secs=tuple((s, round(r * kr, 4), round(ln * ky, 4)) for s, r, ln in c.secs),
                   radius=c.radius * kr, length=c.length * ky,
                   seq=tuple(q * ky for q in c.seq))


def _dedupe(conns: list[Connector]) -> list[Connector]:
    seen, out = set(), []
    for c in conns:
        key = (c.kind, c.gender, tuple(np.round(c.M[:3, :], 2).ravel()), c.secs,
               round(c.radius, 2), round(c.length, 2), c.seq, c.group)
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out


class ShadowLibrary:
    def __init__(self, root, ldraw: LDrawLibrary):
        self.index = FileIndex(root)
        self.ldraw = ldraw
        self._metas: dict[str, list] = {}
        self._own: dict[str, list[Connector]] = {}
        self._all: dict[str, list[Connector]] = {}

    def metas(self, name: str) -> list[tuple[str, dict]]:
        key = normalize(name)
        if key not in self._metas:
            out = []
            p = self.index.resolve(key)
            if p:
                for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                    m = META_RE.match(line.strip())
                    if m:
                        params = {k.lower(): v.strip() for k, v in PARAM_RE.findall(m.group(2))}
                        out.append((m.group(1).upper(), params))
            self._metas[key] = out
        return self._metas[key]

    def own_connectors(self, name: str) -> list[Connector]:
        """The shadow file's own metas plus SNAP_INCL'd files (no LDraw inheritance)."""
        key = normalize(name)
        if key in self._own:
            return self._own[key]
        self._own[key] = []
        out: list[Connector] = []
        for kind, P in self.metas(key):
            if kind == "SNAP_CLEAR":
                continue
            base = _frame(P)
            if kind == "SNAP_INCL":
                if "scale" in P:
                    base = base @ np.diag(_floats(P["scale"])[:3] + [1.0])
                for G in grid_frames(P.get("grid")):
                    for c in self.own_connectors(P.get("ref", "")):
                        cc = place(c, base @ G)
                        if cc is not None:
                            out.append(replace(cc, cid=P.get("id", cc.cid).lower()))
            elif kind in KINDS:
                proto = _make(kind, P)
                out.extend(replace(proto, M=base @ G) for G in grid_frames(P.get("grid")))
        self._own[key] = out
        return out

    def connectors(self, name: str) -> list[Connector]:
        """All connectors of a part in its own frame (own + included + inherited from subfiles)."""
        key = normalize(name)
        if key in self._all:
            return self._all[key]
        self._all[key] = []
        clear_all, clear_ids = False, set()
        for kind, P in self.metas(key):
            if kind == "SNAP_CLEAR":
                if P.get("id"):
                    clear_ids.add(P["id"].lower())
                else:
                    clear_all = True
        conns = list(self.own_connectors(key))
        path = self.ldraw.resolve(key)
        if path is not None and not clear_all:
            for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
                t = raw.split()
                if len(t) >= 15 and t[0] == "1":
                    _, M, sub = parse_type1(t)
                    for c in self.connectors(sub):
                        if c.cid and c.cid in clear_ids:
                            continue
                        cc = place(c, M)
                        if cc is not None:
                            conns.append(cc)
        self._all[key] = _dedupe(conns)
        return self._all[key]
