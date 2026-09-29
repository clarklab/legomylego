"""The three-storey walls: rough-faced (masonry profile) tan courses with red bands, tall
windows under red segmental hoods, built as segments that stand on the base. All in the
frame of the front (-Z) facade; design.py turns them to the four sides.

Each facade has seven bays (cells i, k; x = 20 i + 10):
    corner pavilion  cells 16..23 (x 320..480), projects to z -480 (row -24); an L round
                     the corner, a window per floor in the middle of each face
    wing             cells 12..15 (x 240..320), set back to z -460 (row -23), one window
    dome pavilion    cells 4..11 (x 80..240), projecting, one window; on the front and back
                     a bell dome rises from it, flush with the facade
    centre           cells -4..3 (x -80..80), set back: the entrance (double door under a
                     red arch, a pair of windows under a big arch with a balcony or a
                     porch, two windows above)
and the mirror images. Heights (y, base top at 0): plinth -24, red band -32; ground floor
windows -56..-128, hoods -152; red belt -208; first floor windows -232..-304, hoods -328;
red belt -384; second floor windows -408..-456, hoods -480; wall top -496."""
from __future__ import annotations

import numpy as np

from brickkit.ldraw.matrix import rot, transform
from kit import AV, PLATE, PLATE1, S, Batch, rect_M, segments, split_line

WALL_TOP = -496
MASONRY = {1: "3005", 2: "98283", 4: "15533"}       # rough-faced 1 x 2 and 1 x 4 bricks
_B = [-24] + list(range(-56, -201, -24)) + list(range(-232, -377, -24)) + \
    list(range(-408, -481, -24))
COURSES = sorted([(t, "brick", "wall") for t in _B] +
                 [(-32, "plate", "trim"), (-208, "plate", "trim"), (-384, "plate", "trim"),
                  (-488, "plate", "wall"), (-496, "plate", "wall")], key=lambda c: -c[0])
BELT = -208
WIN3 = [("60593", "window", True), ("60602", "glass", True)]
WIN2 = [("60592", "window", True), ("60601", "glass", True)]
HOOD = [("3659", "trim", False)]
ARCH6 = [("15254", "trim", False)]
DOOR = [("60593", "door", True), ("60602", "glass", True)]


def openings(kind: str) -> list[tuple]:
    """Openings of a bay, as (y top, y bottom, first cell offset, cells, parts); parts are
    (part, role, one per 2-cell window?) placed at the opening's top. p0 is a window's first
    cell ("win") or the first of the entrance's middle 4 cells ("centre")."""
    if kind == "win":
        return [(-128, -56, 0, 2, WIN3), (-152, -128, -1, 4, HOOD),
                (-304, -232, 0, 2, WIN3), (-328, -304, -1, 4, HOOD),
                (-456, -408, 0, 2, WIN2), (-480, -456, -1, 4, HOOD)]
    return [(-128, -56, 0, 4, DOOR), (-176, -128, -1, 6, ARCH6),
            (-304, -232, 0, 4, WIN3), (-352, -304, -1, 6, ARCH6),
            (-456, -408, -1, 2, WIN2), (-480, -456, -2, 4, HOOD),
            (-456, -408, 3, 2, WIN2), (-480, -456, 2, 4, HOOD)]


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
    first = (0, 2, 4)[phase % 3]
    return split_line(n, lengths, first)


def build_segment(lines: list[Line], windows: list[tuple], corner=None) -> Batch:
    """windows: (line index, p0, kind). corner: the cell shared by lines 0 and 1 (it
    alternates between them course by course)."""
    b = Batch()
    brick_len = [n for n in (4, 2, 1) if AV.ok(MASONRY[n], "wall")]
    for n, (top, kind, colour) in enumerate(COURSES):
        bottom = top + (24 if kind == "brick" else 8)
        table = MASONRY if kind == "brick" else PLATE1
        lengths = brick_len if kind == "brick" else AV.lengths(PLATE1, colour)
        cat = f"c{n:02d}"
        for li, line in enumerate(lines):
            blocked = set()
            for wl, p0, wk in windows:
                if wl != li:
                    continue
                for y0, y1, off, cnt, _ in openings(wk):
                    if top >= y0 and bottom <= y1:
                        blocked |= set(range(p0 + off, p0 + off + cnt))
            cells = [c for c in line.cells if line.pos(c) not in blocked]
            if corner is not None and corner in cells and (n + li) % 2:
                cells.remove(corner)                    # the other wall has it this course
            if not cells:
                continue
            R = line.facing()
            for seg in segments([line.pos(c) for c in cells]):
                pos = seg[0]
                for L in _runs(len(seg), lengths, n + li + seg[0]):
                    b.add(table[L], colour, transform(line.centre(pos, pos + L - 1, top), R),
                          cat)
                    pos += L
    for wl, p0, wk in windows:                          # windows, glass, hoods, arches
        line = lines[wl]
        R = line.facing()
        back = tuple(R @ np.array([0.0, 0.0, 1.0]))     # glass goes in from inside
        for y0, y1, off, cnt, parts in openings(wk):
            a = p0 + off
            for part, role, per_window in parts:
                spots = ([line.centre(a + 2 * k, a + 2 * k + 1, y0) for k in range(cnt // 2)]
                         if per_window else [line.centre(a, a + cnt - 1, y0)])
                for c in spots:
                    b.add(part, role, transform(c, R), f"open{y1}",
                          insert=back if role == "glass" else None)
    return b


def _phases():
    """Each course, then whatever stands on it (windows, hoods)."""
    out = []
    for n, (top, _, _) in enumerate(COURSES):
        out.append([f"c{n:02d}", f"x{top}"])
        out.append([f"open{top}"])
    return out


CAPTIONS = {"c00": "The plinth: rough-faced bricks", "c01": "A red band",
            "open-56": "Ground floor windows: white frames with clear glass",
            "open-128": "Red hoods over the windows", "c09": "The red belt course",
            "open-232": "First floor windows", "open-304": "Hoods again",
            "open-408": "Second floor windows", "open-456": "Hoods under the cornice",
            "x-208": "The balcony: its floor sticks out from the belt course, with an "
                     "iron railing on it"}


def emit(sub, b: Batch):
    b.emit(sub, _phases(), CAPTIONS, per_step=8, reach=120)


def corner_pavilion(model):
    """Front-right corner pavilion: front face cells 16..23 on row -24, right face cells
    -24..-17 on column 23; a window per floor in the middle of each face."""
    s = model.submodel("pavilion_walls", "Corner pavilion walls")
    front = Line([(i, -24) for i in range(16, 24)], "x", (0, -1))
    right = Line([(23, k) for k in range(-24, -16)], "z", (1, 0))
    emit(s, build_segment([front, right], [(0, 19, "win"), (1, -21, "win")],
                          corner=(23, -24)))
    return s


def wing(model):
    """A wing, set back: cells 12..15 on row -23, one window per floor."""
    s = model.submodel("wing_walls", "Wing walls")
    emit(s, build_segment([Line([(i, -23) for i in range(12, 16)], "x", (0, -1))],
                          [(0, 13, "win")]))
    return s


def dome_bay(model):
    """A dome pavilion's face: cells 4..11 on row -24 (projecting), one window per floor."""
    s = model.submodel("dome_bay_walls", "Dome pavilion walls")
    emit(s, build_segment([Line([(i, -24) for i in range(4, 12)], "x", (0, -1))],
                          [(0, 7, "win")]))
    return s


def centre(model, balcony: bool):
    """The centre bay, set back to row -23: 8 cells (x -80..80). A glazed double door
    under a red 1 x 6 x 2 arch, a pair of windows under another, two windows above.
    `balcony`: the belt course under the first floor sticks out one stud across the middle
    six cells with an iron railing on it (front and back); the sides get a porch instead
    (portico.py)."""
    name, title = ("centre_front", "Centre bay (front)") if balcony else \
        ("centre_side", "Centre bay (side)")
    s = model.submodel(name, title)
    line = Line([(i, -23) for i in range(-4, 4)], "x", (0, -1))
    b = build_segment([line], [(0, -2, "centre")])
    if balcony:
        cat = f"c{[c[0] for c in COURSES].index(BELT):02d}"
        b.items = [it for it in b.items if it[3] != cat]      # the belt, re-cut:
        for r in ((-4, -4, -23, -23), (-3, 2, -24, -23), (3, 3, -23, -23)):
            p, M = rect_M(PLATE, r, BELT)
            b.add(p, "trim", M, f"x{BELT}")
        b.add("19121", "crest", transform((0, BELT - 48, cx_row(-24))), f"open{BELT}")
        for x in (-50, 50):
            b.add("3062b", "crest", transform((x, BELT - 24, cx_row(-24))), f"open{BELT}")
            b.add("3062b", "crest", transform((x, BELT - 48, cx_row(-24))), f"open{BELT}")
    emit(s, b)
    return s


def cx_row(k: int) -> float:
    return 20 * k + 10
