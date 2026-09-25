"""The tail: built along its own axis (studs pointing backwards), so every slice is a round
cross-section and curved-slope caps smooth the taper into a thick, bushy cone. It plugs onto
the four side studs of a 1 x 2 x 1 2/3 brick (22885) set into the rump.

Tail frame (a sub-assembly built standing up): local -Y (up) = world +Z (backwards),
local +Z = world down, local x = world x. Cells (i, jz): x = 20i, local z = 20jz."""
from __future__ import annotations

import math

import ferret_sculpt as sc
from brickkit.ldraw.matrix import rot, transform

ROOT_J = 50             # the tail starts at z = 20 * ROOT_J LDU, the rump's rear face
SOCKET_I, SOCKET_P = -1, 24   # 22885 over cells i, i+1 of row ROOT_J - 1, bottom plate
AXIS_H = 8 * (SOCKET_P + 5) - 20   # LDU: between the socket's two rows of side studs
R0, LENGTH = 22.5, 114.0      # mm: radius at the root, length
MM = 2.5


def radius(d_mm: float) -> float:
    """Thick at the root, tapering steadily to a rounded tip."""
    t = min(max(d_mm / LENGTH, 0.0), 1.0)
    return R0 * (1.0 - t) ** 0.55


def frame():
    return transform((0.0, -AXIS_H, 20.0 * ROOT_J), rot(x=-90))


def layers() -> dict[int, set]:
    L = {}
    b = 0
    while True:
        d = (3 * b + 1.5) * 3.2
        r = radius(d)
        cells = set()
        for i in range(-4, 4):
            for jz in range(-4, 4):
                x, dz = (i + 0.5) * 8.0, (jz + 0.5) * 8.0
                if x * x + dz * dz <= r * r:
                    cells.add((i, jz))
        if not cells:
            break
        L[b] = cells
        b += 1
    # the root slice must cover the socket's four studs
    L[0] |= {(SOCKET_I, -1), (SOCKET_I, 0), (SOCKET_I + 1, -1), (SOCKET_I + 1, 0)}
    return L


def outward(c) -> tuple[int, int]:
    x, z = c[0] + 0.5, c[1] + 0.5
    if abs(x) >= abs(z):
        return (1 if x > 0 else -1, 0)
    return (0, 1 if z > 0 else -1)


def pieces(sizes_of, role: str = "dark"):
    L = layers()
    bands = sorted(L)
    layer_list = [(b, L[b], {c: role for c in L[b]}, "x" if b % 2 else "z") for b in bands]
    packed, n = sc.pack_section(layer_list, sizes_of)
    caps = []
    for b in bands:
        top = L[b] - L.get(b + 1, set())
        dirs = {c: outward(c) for c in top}
        above = L.get(b + 1, set())
        for run, d in sc.ramps_of(top, dirs):
            wall = (run[-1][0] - d[0], run[-1][1] - d[1]) in above
            if wall:
                for m in range(0, len(run), 3):
                    caps += sc.ramp_pieces(run[m:m + 3], d, 3 * (b + 1), role, b + 1)
            else:
                caps += sc.roof_pieces(run, d, 3 * (b + 1), role, b + 1)
    return packed + caps, n


def socket_pieces(role: str = "core"):
    """The rump's socket: a 22885 facing backwards and a plate on top, in world coordinates."""
    j = ROOT_J - 1
    cells = frozenset({(SOCKET_I, j), (SOCKET_I + 1, j)})
    brick = sc.Piece("22885", role, cells, SOCKET_P, SOCKET_P + 5, cells, {SOCKET_P: cells},
                     (20.0 * (SOCKET_I + 1), -8.0 * (SOCKET_P + 5), 20.0 * j + 10),
                     rot(y=180), SOCKET_P // 3, "tail socket")
    cap = sc.plate(cells, SOCKET_P + 6, role, (SOCKET_P + 5) // 3)
    return [brick, cap], cells, range(SOCKET_P // 3, (SOCKET_P + 6) // 3)
