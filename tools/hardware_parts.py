"""Write brickkit's stand-in parts for non-LEGO hardware (brickkit/data/ldraw/parts/*.dat).

These are simple LDraw-style meshes (BFC certified, counter-clockwise) that stand in for bought
items in the 3D model, the renders and the viewer, so the collision check sees how much room
they take. Their shopping details live in brickkit/data/hardware.json.

    python tools/hardware_parts.py

Clock insert (bk-clock-insert-35mm): a press-in "mini" quartz clock insert at the largest size
the Caldwell County Courthouse's clock openings take: 38 mm bezel, 35 mm body, 20 mm deep.
Its own frame: the dial faces -Z (LDraw's front), the origin is the centre of the bezel's
front face, the body runs back along +Z. Hands (bk-clock-hand-hour / -minute) turn about their
own Z axis, pointing at 12 o'clock (-Y, up) when unturned; rot(z=+a) turns them clockwise as
seen from the front.
"""
from __future__ import annotations

import math
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "brickkit" / "data" / "ldraw" / "parts"
N = 48                                   # segments round a circle

# the insert, LDU (1 LDU = 0.4 mm)
R_BEZEL = 47.5                           # 38 mm bezel
R_DIAL = 38.0                            # 30.4 mm dial visible inside the bezel lip
R_BODY = 43.75                           # 35 mm body (the "fit-up" / bore size)
R_KNOB = 6.0
Z_DIAL = 3.0                             # dial sits 1.2 mm behind the bezel's front face
Z_BEZEL = 8.0                            # bezel lip 3.2 mm thick
Z_BODY = 44.0                            # back of the movement
Z_KNOB = 50.0                            # back of the setting knob: 20 mm overall
R_POST = 1.5
Z_POST = 0.2


def fmt(v: float) -> str:
    v = 0.0 if abs(v) < 1e-9 else v
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


class Part:
    def __init__(self, title: str, name: str):
        self.lines = [f"0 {title}", f"0 Name: {name}", "0 Author: brickkit",
                      "0 !LDRAW_ORG Unofficial_Part", "0 !LICENSE Licensed under CC BY 4.0",
                      "", "0 BFC CERTIFY CCW", ""]

    def tri(self, c, a, b, d):
        """Triangle (a, b, d) whose normal (b - a) x (d - a) points out of the part."""
        self.lines.append(f"3 {c} " + " ".join(fmt(v) for p in (a, b, d) for v in p))

    def quad(self, c, a, b, d, e):
        self.lines.append(f"4 {c} " + " ".join(fmt(v) for p in (a, b, d, e) for v in p))

    def edge(self, a, b, c=24):
        self.lines.append(f"2 {c} " + " ".join(fmt(v) for p in (a, b) for v in p))

    def comment(self, text):
        self.lines += ["", f"0 // {text}"]

    def write(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(self.lines) + "\n")


def circle(r, z, n=N):
    return [(r * math.cos(2 * math.pi * k / n), r * math.sin(2 * math.pi * k / n), z)
            for k in range(n)]


def annulus(p, c, r0, r1, z, facing):
    """Flat ring r0..r1 at height z; facing -1 = toward -Z (the front), +1 = toward +Z."""
    inner, outer = circle(r0, z), circle(r1, z)
    for k in range(N):
        a, b = inner[k], inner[(k + 1) % N]
        d, e = outer[(k + 1) % N], outer[k]
        # (b - a) x (e - a) points +Z for this order (counter-clockwise seen from +Z)
        if facing > 0:
            p.quad(c, a, e, d, b)
        else:
            p.quad(c, a, b, d, e)


def disc(p, c, r, z, facing):
    ring = circle(r, z)
    ctr = (0.0, 0.0, z)
    for k in range(N):
        a, b = ring[k], ring[(k + 1) % N]
        if facing > 0:
            p.tri(c, ctr, a, b)
        else:
            p.tri(c, ctr, b, a)


def tube(p, c, r, z0, z1, outward=True):
    """Cylinder wall from z0 to z1 (z0 < z1), normals away from (or toward) the axis."""
    lo, hi = circle(r, z0), circle(r, z1)
    for k in range(N):
        a, b = lo[k], lo[(k + 1) % N]
        d, e = hi[(k + 1) % N], hi[k]
        if outward:
            p.quad(c, a, b, d, e)
        else:
            p.quad(c, a, e, d, b)


def edge_circle(p, r, z):
    ring = circle(r, z)
    for k in range(N):
        p.edge(ring[k], ring[(k + 1) % N])


def insert():
    p = Part("Mini Quartz Clock Insert 35 mm (not LEGO, stand-in)", "bk-clock-insert-35mm.dat")
    p.comment("bezel: front face, outer rim, back face, the lip round the dial")
    annulus(p, 16, R_DIAL, R_BEZEL, 0.0, -1)
    tube(p, 16, R_BEZEL, 0.0, Z_BEZEL)
    annulus(p, 16, R_BODY, R_BEZEL, Z_BEZEL, +1)
    tube(p, 16, R_DIAL, 0.0, Z_DIAL, outward=False)
    p.comment("white dial")
    disc(p, 15, R_DIAL, Z_DIAL, -1)
    p.comment("hour marks, a hair in front of the dial (longer at 12, 3, 6 and 9)")
    for h in range(12):
        a = 2 * math.pi * h / 12
        ux, uy = math.sin(a), -math.cos(a)           # 12 o'clock is -Y
        vx, vy = -uy, ux
        big = h % 3 == 0
        r0, r1, w = (26.0 if big else 30.0), 35.5, (2.2 if big else 1.2)
        z = Z_DIAL - 0.3
        pts = [(ux * r0 - vx * w, uy * r0 - vy * w, z), (ux * r1 - vx * w, uy * r1 - vy * w, z),
               (ux * r1 + vx * w, uy * r1 + vy * w, z), (ux * r0 + vx * w, uy * r0 + vy * w, z)]
        # counter-clockwise seen from -Z
        n = ((pts[1][0] - pts[0][0]) * (pts[3][1] - pts[0][1])
             - (pts[1][1] - pts[0][1]) * (pts[3][0] - pts[0][0]))
        p.quad(0, *(pts if n < 0 else pts[::-1]))
    p.comment("centre post the hands sit on")
    tube(p, 0, R_POST, Z_POST, Z_DIAL)
    disc(p, 0, R_POST, Z_POST, -1)
    p.comment("movement body, back, setting knob")
    tube(p, 16, R_BODY, Z_BEZEL, Z_BODY)
    annulus(p, 16, R_KNOB, R_BODY, Z_BODY, +1)
    tube(p, 16, R_KNOB, Z_BODY, Z_KNOB)
    disc(p, 16, R_KNOB, Z_KNOB, +1)
    p.comment("outlines")
    for r, z in ((R_BEZEL, 0.0), (R_DIAL, 0.0), (R_DIAL, Z_DIAL), (R_BEZEL, Z_BEZEL),
                 (R_BODY, Z_BEZEL), (R_BODY, Z_BODY), (R_KNOB, Z_BODY), (R_KNOB, Z_KNOB)):
        edge_circle(p, r, z)
    return p


def hand(name, title, length, w_base, w_tip, tail, w_tail):
    """A flat hand 0.6 LDU thick with a hub ring (bore = the insert's centre post)."""
    p = Part(title, name)
    t = 0.3
    outline = [(0.0, -length), (w_tip / 2, -length + 4), (w_base / 2, 0.0), (w_tail / 2, tail),
               (-w_tail / 2, tail), (-w_base / 2, 0.0), (-w_tip / 2, -length + 4)]
    # outline runs clockwise seen from -Z (x right, -y up): front faces use it reversed
    cx = sum(q[0] for q in outline) / len(outline)
    cy = sum(q[1] for q in outline) / len(outline)
    p.comment("blade")
    n = len(outline)
    for k in range(n):
        a, b = outline[k], outline[(k + 1) % n]
        p.tri(16, (cx, cy, -t), (b[0], b[1], -t), (a[0], a[1], -t))     # front, toward -Z
        p.tri(16, (cx, cy, t), (a[0], a[1], t), (b[0], b[1], t))        # back, toward +Z
        p.quad(16, (a[0], a[1], -t), (b[0], b[1], -t), (b[0], b[1], t), (a[0], a[1], t))
        p.edge((a[0], a[1], -t), (b[0], b[1], -t))
    p.comment("hub")
    annulus(p, 16, R_POST, 3.0, -0.5, -1)
    annulus(p, 16, R_POST, 3.0, 0.5, +1)
    tube(p, 16, 3.0, -0.5, 0.5)
    tube(p, 16, R_POST, -0.5, 0.5, outward=False)
    edge_circle(p, 3.0, -0.5)
    return p


def main():
    insert().write(OUT / "bk-clock-insert-35mm.dat")
    hand("bk-clock-hand-hour.dat", "Clock Hand Hour (not LEGO, stand-in)",
         22.0, 3.4, 1.4, 5.0, 2.6).write(OUT / "bk-clock-hand-hour.dat")
    hand("bk-clock-hand-minute.dat", "Clock Hand Minute (not LEGO, stand-in)",
         33.0, 2.4, 1.0, 7.0, 2.0).write(OUT / "bk-clock-hand-minute.dat")
    print("wrote", *sorted(f.name for f in OUT.glob("bk-*.dat")))


if __name__ == "__main__":
    main()
