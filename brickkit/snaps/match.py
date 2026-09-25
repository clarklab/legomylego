"""Find which connectors of different parts engage each other."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import numpy as np

from .connector import Connector

# (male shape, female shape) pairs that engage
COMPAT = {("R", "R"), ("R", "S"), ("A", "A"), ("A", "R"), ("S", "S")}
RADIUS_TOL = 0.6


@dataclass
class Connection:
    a: int
    b: int
    ca: Connector
    cb: Connector
    kind: str       # stud | pin | axle | bar | clip | hinge | gen
    overlap: float  # engaged length in LDU


def _axis_key(axis: np.ndarray) -> tuple[tuple, np.ndarray]:
    a = axis / np.linalg.norm(axis)
    k = int(np.argmax(np.abs(a)))
    if a[k] < 0:
        a = -a
    return tuple(np.round(a, 3) + 0.0), a


def _mapped(m: Connector, f: Connector) -> list[tuple[float, float, str, float]]:
    """f's intervals expressed in m's axis parameter."""
    d = float(np.dot(f.origin - m.origin, m.axis))
    sgn = 1.0 if float(np.dot(m.axis, f.axis)) > 0 else -1.0
    out = []
    for t0, t1, s, r in f.intervals():
        a0, a1 = d + sgn * t0, d + sgn * t1
        out.append((min(a0, a1), max(a0, a1), s, r))
    return out


def cyl_overlap(m: Connector, f: Connector) -> float:
    total = 0.0
    fin = _mapped(m, f)
    for t0, t1, sm, rm in m.intervals():
        if sm in ("_L", "L_"):
            continue
        for u0, u1, sf, rf in fin:
            if sf in ("_L", "L_"):
                continue
            ov = min(t1, u1) - max(t0, u0)
            if ov > 0 and (sm, sf) in COMPAT and abs(rm - rf) <= RADIUS_TOL:
                total += ov
    return total


def extent_overlap(a: Connector, b: Connector) -> float:
    ia, ib = a.intervals(), _mapped(a, b)
    if not ia or not ib:
        return 0.0
    return min(ia[-1][1], ib[-1][1]) - max(ia[0][0], ib[0][0])


def _classify(m: Connector, f: Connector) -> str:
    if f.kind == "clp":
        return "clip"
    shapes = {s for _, _, s, _ in m.intervals()} | {s for _, _, s, _ in f.intervals()}
    if "A" in shapes:
        return "axle"
    r = max((r for _, _, s, r in m.intervals() if s in ("R", "S")), default=0.0)
    if abs(r - 6) < 0.7 and m.total_length() <= 6.5:
        return "stud"
    if r <= 4.6:
        return "bar"
    return "pin"


def match_pair(a: Connector, b: Connector, min_overlap: float = 0.9):
    """Return (kind, overlap) if the two (collinear) connectors engage, else None."""
    if a.kind == "fgr" and b.kind == "fgr":
        if a.group != b.group or abs(a.radius - b.radius) > RADIUS_TOL:
            return None
        ov = extent_overlap(a, b)
        return ("hinge", ov) if ov >= 1.0 else None
    if "gen" in (a.kind, b.kind) or "fgr" in (a.kind, b.kind):
        return None
    if a.kind == "clp" and b.kind == "clp":
        return None
    if a.kind == "clp":
        f, m = a, b
    elif b.kind == "clp":
        f, m = b, a
    else:
        if a.gender == b.gender:
            return None
        m, f = (a, b) if a.gender == "M" else (b, a)
    if m.gender != "M":
        return None
    if (m.group or f.group) and m.group != f.group:
        return None
    ov = cyl_overlap(m, f)
    if ov < min_overlap:
        return None
    return _classify(m, f), ov


def find_connections(conns_by_part: list[list[Connector]], min_overlap: float = 0.9
                     ) -> list[Connection]:
    buckets: dict[tuple, list] = defaultdict(list)
    gens: dict[str, list] = defaultdict(list)
    for i, conns in enumerate(conns_by_part):
        for c in conns:
            if c.kind == "gen":
                gens[c.group].append((i, c))
                continue
            key, a = _axis_key(c.axis)
            foot = c.origin - np.dot(c.origin, a) * a
            buckets[(key, tuple(np.round(foot / 0.5).astype(int)))].append((i, c))
    out: list[Connection] = []
    for items in buckets.values():
        for x in range(len(items)):
            i, ci = items[x]
            for y in range(x + 1, len(items)):
                j, cj = items[y]
                if i == j:
                    continue
                res = match_pair(ci, cj, min_overlap)
                if res:
                    out.append(Connection(i, j, ci, cj, res[0], res[1]))
    for items in gens.values():
        for x in range(len(items)):
            i, ci = items[x]
            for y in range(x + 1, len(items)):
                j, cj = items[y]
                if i == j or ci.gender == cj.gender:
                    continue
                if (np.linalg.norm(ci.origin - cj.origin) <= 1.0
                        and abs(np.dot(ci.M[:3, 1], cj.M[:3, 1])) > 0.999):
                    out.append(Connection(i, j, ci, cj, "gen", 0.0))
    return out
