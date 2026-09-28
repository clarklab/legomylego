"""The two-storey walls: tan brick courses with red bands, tall arched windows on the ground
floor and arched windows above. Built as segments that stand on the base: a corner pavilion
(an L of two 8-stud faces, x4), a recessed wing (4 studs, x8) and a centre pavilion (4 studs,
x4), all in the frame of the front (-Z) facade; design.py turns them to the four sides.

Plan (studs from the centre): pavilions project to 14, wings are set back to 13, the centre
pavilion projects to 14 again. Heights (y, base top at 0): plinth 0..-24, red band -24..-32,
ground floor to -176 (windows -56..-176: a 1 x 2 x 3 under a 1 x 2 x 2, with arches over
them -176..-200), red belt -200..-208, first floor windows -232..-304 (arches -304..-328),
wall top -344."""
from __future__ import annotations

import numpy as np

from brickkit.ldraw.matrix import rot, transform
from kit import AV, BRICK, PLATE1, S, Batch, run_M, segments, split_line

WALL_TOP = -344
# (top y, kind, colour) from the bottom up
COURSES = [(-24, "brick", "wall"), (-32, "plate", "trim"),
           (-56, "brick", "wall"), (-80, "brick", "wall"), (-104, "brick", "wall"),
           (-128, "brick", "wall"), (-152, "brick", "wall"), (-176, "brick", "wall"),
           (-200, "brick", "wall"),                          # arch course (ground floor)
           (-208, "plate", "trim"),
           (-232, "brick", "wall"), (-256, "brick", "wall"), (-280, "brick", "wall"),
           (-304, "brick", "wall"),
           (-328, "brick", "wall"),                          # arch course (first floor)
           (-336, "plate", "wall"), (-344, "plate", "wall")]


def openings(w: int) -> list[tuple]:
    """What goes in a window opening w studs wide, as (y top, y bottom, cells beyond the
    opening each side, [(part, role, y of the part's top, per 2-stud window?)]).
    w = 2 (wings, centre): a tall ground-floor window (1 x 2 x 3 under a 1 x 2 x 2 transom)
    under a 1 x 4 arch; a 1 x 2 x 3 window above under another.
    w = 4 (pavilions): two windows side by side under a 1 x 6 x 2 arch, whose opening is the
    lunette over them; 1 x 2 x 3 below, 1 x 2 x 2 above."""
    win3 = [("60593", "window", None, True), ("60602", "glass", None, True)]
    win2 = [("60592", "window", None, True), ("60601", "glass", None, True)]
    if w == 2:
        return [(-128, -56, 0, win3), (-176, -128, 0, win2),
                (-200, -176, 1, [("3659", "trim", None, False)]),
                (-304, -232, 0, win3), (-328, -304, 1, [("3659", "trim", None, False)])]
    return [(-128, -56, 0, win3), (-176, -128, 1, [("15254", "trim", None, False)]),
            (-280, -232, 0, win2), (-328, -280, 1, [("15254", "trim", None, False)])]


class Line:
    """A straight wall one stud thick: cells (i, k) in order along `axis`; `out` is the
    outward normal (dx, dz)."""

    def __init__(self, cells, axis, out):
        self.cells = list(cells)
        self.axis = axis
        self.out = out

    def pos(self, c):
        return c[0] if self.axis == "x" else c[1]

    def centre(self, a: float, b: float, y: float):
        """World point on the wall's centre line for the run a..b (cell positions)."""
        i, k = self.cells[0]
        if self.axis == "x":
            return np.array([S * (a + b + 1) / 2, y, S * k + S / 2])
        return np.array([S * i + S / 2, y, S * (a + b + 1) / 2])

    def facing(self) -> np.ndarray:
        """Rotation that turns a part's front (-Z) to face outward."""
        return {(0, -1): rot(y=0), (0, 1): rot(y=180), (1, 0): rot(y=-90),
                (-1, 0): rot(y=90)}[self.out]


def _runs(n, lengths, phase):
    first = (0, 3, 2, 4, 6)[phase % 5]
    return split_line(n, lengths, first)


def build_segment(lines: list[Line], windows: list[tuple], corner=None) -> Batch:
    """windows: (line index, first cell position, width 2 or 4). corner: the cell shared by
    lines 0 and 1 (it alternates between them course by course)."""
    b = Batch()
    brick_len = AV.lengths(BRICK, "wall")
    for n, (top, kind, colour) in enumerate(COURSES):
        h = 24 if kind == "brick" else 8
        bottom = top + h
        table = BRICK if kind == "brick" else PLATE1
        lengths = AV.lengths(table, colour) if kind == "plate" else brick_len
        cat = f"c{n:02d}"
        for li, line in enumerate(lines):
            blocked = set()
            for wl, p0, w in windows:
                if wl != li:
                    continue
                for y0, y1, extra, _ in openings(w):
                    if top >= y0 and bottom <= y1:
                        blocked |= set(range(p0 - extra, p0 + w + extra))
            cells = [c for c in line.cells if line.pos(c) not in blocked]
            if corner is not None and corner in cells and (n + li) % 2:
                cells.remove(corner)                    # the other wall has it this course
            if not cells:
                continue
            for seg in segments([line.pos(c) for c in cells]):
                pos = seg[0]
                for L in _runs(len(seg), lengths, n + li + seg[0]):
                    M = transform(line.centre(pos, pos + L - 1, top),
                                  rot(y=90) if line.axis == "z" else None)
                    b.add(table[L], colour, M, cat)
                    pos += L
    for wl, p0, w in windows:                           # windows, glass, arches
        line = lines[wl]
        R = line.facing()
        back = tuple(R @ np.array([0.0, 0.0, 1.0]))     # glass goes in from inside
        for y0, y1, _, parts in openings(w):
            for part, role, _, per_window in parts:
                spots = ([line.centre(p0 + 2 * k, p0 + 2 * k + 1, y0) for k in range(w // 2)]
                         if per_window else [line.centre(p0, p0 + w - 1, y0)])
                for c in spots:
                    b.add(part, role, transform(c, R), f"open{y1}",
                          insert=back if role == "glass" else None)
    return b


def _phases():
    """Each course, then whatever stands on it (windows, arches)."""
    out = []
    for n, (top, _, _) in enumerate(COURSES):
        out.append([f"c{n:02d}"])
        out.append([f"open{top}"])
    return out


CAPTIONS = {"c00": "The plinth: one course of bricks", "c01": "A red band",
            "open-56": "Ground floor windows: white frames with clear glass",
            "open-128": "Arches (or transoms) over the ground floor windows",
            "c09": "The red belt course between the floors",
            "open-232": "First floor windows", "open-280": "Arches over them",
            "c15": "Two courses of plates on top"}


def emit(sub, b: Batch):
    b.emit(sub, _phases(), CAPTIONS, per_step=8, reach=120)


def corner_pavilion(model):
    """Front-right corner pavilion: front face x 120..280 at z -280..-260, right face
    x 260..280 at z -280..-120. Paired windows in the middle of each face."""
    s = model.submodel("pavilion_walls", "Corner pavilion walls")
    front = Line([(i, -14) for i in range(6, 14)], "x", (0, -1))
    right = Line([(13, k) for k in range(-14, -6)], "z", (1, 0))
    b = build_segment([front, right], [(0, 8, 4), (1, -12, 4)], corner=(13, -14))
    emit(s, b)
    return s


def wing(model):
    """A recessed wing, 4 studs (x 40..120, wall z -260..-240) with one window each floor."""
    s = model.submodel("wing_walls", "Wing walls")
    line = Line([(i, -13) for i in range(2, 6)], "x", (0, -1))
    emit(s, build_segment([line], [(0, 3, 2)]))
    return s


def centre_pavilion(model):
    """The centre pavilion's face, 4 studs (x -40..40, z -280..-260): a door or window."""
    s = model.submodel("centre_walls", "Centre pavilion walls")
    line = Line([(i, -14) for i in range(-2, 2)], "x", (0, -1))
    emit(s, build_segment([line], [(0, -1, 2)]))
    return s
