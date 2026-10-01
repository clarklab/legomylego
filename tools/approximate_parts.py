"""Write brickkit's approximate 3D models of REAL LEGO parts that the LDraw library has no
model of (brickkit/data/ldraw/parts/<the part's real number>.dat).

Unlike the non-LEGO hardware stand-ins (tools/hardware_parts.py), these are LEGO elements:
they keep their real Rebrickable / BrickLink number, stay on the parts lists and the BrickLink
wanted list, and the real_elements check checks them like any part. Only their shape is
brickkit's approximation (listed in brickkit/data/approximate.json, noted in the reports).
The library's own file wins if LDraw ever adds the part.

    python tools/approximate_parts.py

10165c01, Minifig Helmet Underwater Deep Diver with Trans-Clear Glass (Collectible Minifigures
Series 8 Diver, 2012; Pearl Gold): a round brass diving helmet. Its frame is the minifig head's
(origin at the top of the head, under its stud; -Y up; the face toward -Z), so it is placed
exactly like a hat. BrickLink gives it 1.85 x 1.8 x 2.1 cm and 1.96 g; this model is 1.8 cm
wide and 1.8 cm tall: a hollow sphere (outer radius 22 LDU, centred 8 LDU below the top of
the head) with a large round front window (30 degrees across its axis, Trans-Clear glass,
colour 47, in a raised Pearl Gold frame), a small round port on each side, a valve on top, an
air connector at the back, and a flared collar that clears the torso's shoulders, with eight
bolts round it. It takes the head's stud like a hat (LDCad snap in
brickkit/data/shadow/parts/10165c01.dat).
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent / "brickkit" / "data"
OUT = ROOT / "ldraw" / "parts"
SHADOW = ROOT / "shadow" / "parts"
GLASS = 47                         # LDraw Trans-Clear
MAIN = 16                          # the part's own colour (Pearl Gold)


def fmt(v: float) -> str:
    v = 0.0 if abs(v) < 1e-9 else float(v)
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


class Part:
    """LDraw part writer: every triangle is wound counter-clockwise seen from outside (BFC
    CERTIFY CCW); `tri` turns it round if its normal points against `out` (a direction)."""

    def __init__(self, title: str, name: str, keywords: str = ""):
        self.lines = [f"0 {title}", f"0 Name: {name}", "0 Author: brickkit",
                      "0 !LDRAW_ORG Unofficial_Part", "0 !LICENSE Licensed under CC BY 4.0", ""]
        if keywords:
            self.lines += [f"0 !KEYWORDS {keywords}", ""]
        self.lines += ["0 BFC CERTIFY CCW", ""]

    def comment(self, text: str) -> None:
        self.lines += ["", f"0 // {text}"]

    def tri(self, c, a, b, d, out) -> None:
        a, b, d = (np.asarray(v, float) for v in (a, b, d))
        n = np.cross(b - a, d - a)
        if np.linalg.norm(n) < 1e-9:
            return
        if float(np.dot(n, out)) < 0:
            b, d = d, b
        self.lines.append(f"3 {c} " + " ".join(fmt(v) for p in (a, b, d) for v in p))

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(self.lines) + "\n")


def unit(v) -> np.ndarray:
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def basis(d):
    """Two unit vectors perpendicular to d (and to each other)."""
    d = unit(d)
    a = np.array([0.0, 1.0, 0.0]) if abs(d[1]) < 0.9 else np.array([1.0, 0.0, 0.0])
    u = unit(np.cross(d, a))
    return u, np.cross(d, u)


def ring(centre, d, r, n):
    u, w = basis(d)
    return [np.asarray(centre) + r * (math.cos(2 * math.pi * k / n) * u
                                       + math.sin(2 * math.pi * k / n) * w) for k in range(n)]


def clip(poly, g):
    """Sutherland-Hodgman: keep the part of a polygon where g(v) >= 0."""
    out = []
    for k in range(len(poly)):
        a, b = poly[k], poly[(k + 1) % len(poly)]
        ga, gb = g(a), g(b)
        if ga >= 0:
            out.append(a)
        if (ga >= 0) != (gb >= 0):
            t = ga / (ga - gb)
            out.append(a + t * (b - a))
    return out


def sphere(p, c, C, R, keeps, outward, nlat=32, nlon=64):
    """A sphere (centre C, radius R) with the parts where any keep-function < 0 cut away;
    cut edges are put back on the sphere. `outward`: normals away from the centre."""
    C = np.asarray(C, float)

    def pt(i, j):
        th, ph = math.pi * i / nlat, 2 * math.pi * j / nlon
        return C + R * np.array([math.sin(th) * math.cos(ph), -math.cos(th),
                                 math.sin(th) * math.sin(ph)])

    for i in range(nlat):
        for j in range(nlon):
            quad = [pt(i, j), pt(i + 1, j), pt(i + 1, j + 1), pt(i, j + 1)]
            for poly in ([quad[0], quad[1], quad[2]], [quad[0], quad[2], quad[3]]):
                for g in keeps:
                    poly = clip(poly, g)
                    if len(poly) < 3:
                        break
                if len(poly) < 3:
                    continue
                poly = [C + R * unit(v - C) for v in poly]
                mid = sum(poly) / len(poly)
                out = (mid - C) if outward else (C - mid)
                for k in range(1, len(poly) - 1):
                    p.tri(c, poly[0], poly[k], poly[k + 1], out)


def band(p, c, lo, hi, out_of):
    """Quads between two rings of equal length; `out_of(point)` gives the outward direction."""
    n = len(lo)
    for k in range(n):
        a, b, d, e = lo[k], lo[(k + 1) % n], hi[(k + 1) % n], hi[k]
        mid = (a + b + d + e) / 4
        p.tri(c, a, b, d, out_of(mid))
        p.tri(c, a, d, e, out_of(mid))


def disc(p, c, centre, d, r, n, facing):
    pts = ring(centre, d, r, n)
    for k in range(n):
        p.tri(c, centre, pts[k], pts[(k + 1) % n], facing)


def cylinder(p, c, base, d, r, length, n=24, cap=True):
    """A closed post from `base` along d (its base disc left open, buried in the shell)."""
    d = unit(d)
    lo, hi = ring(base, d, r, n), ring(np.asarray(base) + length * d, d, r, n)
    band(p, c, lo, hi, lambda m: (m - base) - np.dot(m - base, d) * d)
    if cap:
        disc(p, c, np.asarray(base) + length * d, d, r, n, d)


def torus(p, c, centre, d, R, r, n=64, m=12):
    d = unit(d)
    u, w = basis(d)
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        radial = math.cos(a) * u + math.sin(a) * w
        pts.append([np.asarray(centre) + (R + r * math.cos(2 * math.pi * j / m)) * radial
                    + r * math.sin(2 * math.pi * j / m) * d for j in range(m)])
    for i in range(n):
        for j in range(m):
            a, b = pts[i][j], pts[(i + 1) % n][j]
            e, f = pts[(i + 1) % n][(j + 1) % m], pts[i][(j + 1) % m]
            mid = (a + b + e + f) / 4
            radial = unit((mid - centre) - np.dot(mid - centre, d) * d)
            core = np.asarray(centre) + R * radial
            p.tri(c, a, b, e, mid - core)
            p.tri(c, a, e, f, mid - core)


def diver_helmet():
    C = np.array([0.0, 8.0, 0.0])             # sphere centre: 8 LDU below the top of the head
    RO, RI = 22.0, 21.0
    CUT = 22.0                                 # the sphere ends here (y, down); the collar below
    holes = [(unit((0, 0.12, -1)), math.radians(30)),     # the front window
             (unit((1, 0.10, 0)), math.radians(12)),      # side ports
             (unit((-1, 0.10, 0)), math.radians(12))]
    keeps = [lambda v: CUT - v[1]]
    for d, a in holes:
        keeps.append(lambda v, d=d, a=a: math.acos(max(-1.0, min(1.0, float(
            np.dot(unit(v - C), d))))) - a)
    p = Part("Minifig Helmet Underwater Deep Diver with Trans-Clear Glass (brickkit approximation)",
             "10165c01.dat",
             "Rebrickable 10165c01, BrickLink 10165c01, approximate, Collectible Minifigures "
             "Series 8, Diver")
    p.comment("brickkit's approximation of a real LEGO part LDraw has no model of: the shape "
              "is not LEGO's; see tools/approximate_parts.py")
    p.comment("the dome: a brass shell 1 LDU thick, open at the windows and at the collar")
    sphere(p, MAIN, C, RO, keeps, outward=True)
    sphere(p, MAIN, C, RI, keeps, outward=False)
    n = 64
    for d, a in holes:
        p.comment("a window's rim through the shell, its glass and its raised frame")
        lo = ring(C + RO * math.cos(a) * d, d, RO * math.sin(a), n)
        hi = ring(C + RI * math.cos(a) * d, d, RI * math.sin(a), n)
        band(p, MAIN, lo, hi, lambda m, d=d: -((m - C) - np.dot(m - C, d) * d))
        rg = (RO + RI) / 2
        gc = C + rg * math.cos(a) * d
        disc(p, GLASS, gc, d, rg * math.sin(a), n, d)
        disc(p, GLASS, gc - 0.05 * d, d, rg * math.sin(a), n, -d)
        big = a > math.radians(20)
        torus(p, MAIN, C + (RO + 0.3) * math.cos(a) * d, d, RO * math.sin(a) + 0.4,
              1.8 if big else 1.1)
    p.comment("the collar, flaring out over the shoulders, its underside and eight bolts")
    yo, yb = CUT, 26.0
    ro, ri = math.sqrt(RO ** 2 - (CUT - C[1]) ** 2), math.sqrt(RI ** 2 - (CUT - C[1]) ** 2)
    ro2, ri2 = 21.0, 19.6
    down = np.array([0.0, 1.0, 0.0])
    o0, o1 = ring((0, yo, 0), down, ro, 96), ring((0, yb, 0), down, ro2, 96)
    i0, i1 = ring((0, yo, 0), down, ri, 96), ring((0, yb, 0), down, ri2, 96)
    band(p, MAIN, o0, o1, lambda m: np.array([m[0], 0.0, m[2]]))
    band(p, MAIN, i0, i1, lambda m: -np.array([m[0], 0.0, m[2]]))
    band(p, MAIN, i1, o1, lambda m: down)
    for k in range(8):
        a = 2 * math.pi * (k + 0.5) / 8
        radial = np.array([math.cos(a), 0.0, math.sin(a)])
        y = 24.0
        r = ro + (ro2 - ro) * (y - yo) / (yb - yo)
        cylinder(p, MAIN, np.array([0.0, y, 0.0]) + (r - 0.5) * radial, radial, 1.3, 1.6, n=12)
    p.comment("the valve on top and the air connector at the back")
    top = C + np.array([0.0, -(RO - 1.0), 0.0])
    cylinder(p, MAIN, top, (0, -1, 0), 4.5, 3.5)
    cylinder(p, MAIN, top + np.array([0.0, -3.5, 0.0]), (0, -1, 0), 2.2, 2.0)
    back = unit((0, -0.25, 1))
    cylinder(p, MAIN, C + (RO - 1.0) * back, back, 3.2, 4.0)
    p.write(OUT / "10165c01.dat")
    SHADOW.mkdir(parents=True, exist_ok=True)
    (SHADOW / "10165c01.dat").write_text(
        '0 brickkit overlay for "Minifig Helmet Underwater Deep Diver with Trans-Clear Glass" '
        "(10165c01)\n"
        "0 // brickkit's own approximate model (tools/approximate_parts.py): it sits on the\n"
        "0 // minifig head's stud like a hat (the head stud is R 6 x 4 at the head's origin).\n"
        "0 !LDCAD SNAP_CYL [gender=F] [caps=one] [secs=R 6 4]\n")


def main():
    diver_helmet()
    print("wrote", OUT / "10165c01.dat")


if __name__ == "__main__":
    main()
