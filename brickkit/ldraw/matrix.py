"""4x4 transforms in LDraw units (LDU). LDraw's -Y axis points up."""
from __future__ import annotations

import math

import numpy as np


def translate(x: float = 0, y: float = 0, z: float = 0) -> np.ndarray:
    M = np.eye(4)
    M[:3, 3] = (x, y, z)
    return M


def rot(x: float = 0, y: float = 0, z: float = 0) -> np.ndarray:
    """3x3 rotation from Euler angles in degrees, applied about X, then Y, then Z."""
    ax, ay, az = (math.radians(v) for v in (x, y, z))
    cx, sx, cy, sy, cz, sz = (math.cos(ax), math.sin(ax), math.cos(ay), math.sin(ay),
                              math.cos(az), math.sin(az))
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    R = Rz @ Ry @ Rx
    R[np.abs(R) < 1e-12] = 0.0
    return R


def transform(pos=(0, 0, 0), rot3=None) -> np.ndarray:
    M = np.eye(4)
    if rot3 is not None:
        M[:3, :3] = np.asarray(rot3, dtype=float)
    M[:3, 3] = pos
    return M


def parse_color(token: str) -> int:
    try:
        return int(token)
    except ValueError:
        return int(token, 16) if token.lower().startswith("0x") else 16


def parse_type1(tokens: list[str]) -> tuple[int, np.ndarray, str]:
    """Parse a type-1 line given as tokens, including the leading '1'."""
    x, y, z, a, b, c, d, e, f, g, h, i = (float(t) for t in tokens[2:14])
    M = np.eye(4)
    M[:3, :3] = ((a, b, c), (d, e, f), (g, h, i))
    M[:3, 3] = (x, y, z)
    return parse_color(tokens[1]), M, " ".join(tokens[14:])


def _fmt(v: float) -> str:
    v = 0.0 if abs(v) < 1e-9 else float(v)
    s = f"{v:.6f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def format_type1(color: int, M: np.ndarray, name: str) -> str:
    vals = list(M[:3, 3]) + list(M[:3, :3].reshape(-1))
    return f"1 {color} " + " ".join(_fmt(v) for v in vals) + f" {name}"


def apply(M: np.ndarray, pts) -> np.ndarray:
    pts = np.asarray(pts, dtype=float)
    return pts @ M[:3, :3].T + M[:3, 3]


def is_mirror(M: np.ndarray) -> bool:
    return float(np.linalg.det(M[:3, :3])) < 0
