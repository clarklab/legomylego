"""VHS Cassette - a life-size (1:1) VHS video cassette in real LEGO.

Units: LDU (stud 20, plate 8, brick 24), -Y is up, front (-Z) is the dust door.
Footprint 23 x 13 studs (x -230..230, z -130..130), 8 plates tall (y -64..0).

Sub-assemblies: bottom half (floor, walls, tape path, door hinge bases), dust door,
two reels (supply full, take-up nearly empty) and the top half (window, labels, reel pins).
Moving groups: `flap` (door, about the hinge axis) and `reel_l` / `reel_r` (reels, about
their pins). `reel_l` is the supply reel: on the left when you hold the tape label-up with
the door pointing away from you, i.e. at +X.
"""
from __future__ import annotations

from collections import defaultdict

import numpy as np

from brickkit.engine import Engine
from brickkit.ldraw.matrix import rot, transform, translate
from brickkit.snaps.match import find_connections

ENG = Engine()

S = 20                      # one stud
Y_BOTTOM, Y_FLOOR = -8, -16  # bottom plates [-8, 0], floor tiles [-16, -8]
Y_C1, Y_C2, Y_C3 = -16, -40, -48   # wall courses: plate, brick, plate
Y_TOP_PLATE, Y_TOP_TILE = -56, -64
NI, NK = 11, 6              # stud index ranges: i in [-11, 11] (x = 20 i), k in [-6, 6] (z = 20 k)

REEL_AXES = {"reel_l": (110, 10), "reel_r": (-110, 10)}   # supply (full) at +X, take-up at -X
DOOR_AXIS = (-50, -104)     # (y, z) of the door hinge axis (along X)
HINGE_W = rot(x=90) @ rot(y=180)   # 3937 / 6134 with the hinge top facing the front
SNOT = rot(x=90)            # studs facing the front (-Z): local +Z becomes world up

PLATE = {(1, 1): "3024", (1, 2): "3023", (1, 3): "3623", (1, 4): "3710", (1, 6): "3666",
         (1, 8): "3460", (1, 10): "4477", (1, 12): "60479", (2, 2): "3022", (2, 3): "3021",
         (2, 4): "3020", (2, 6): "3795", (2, 8): "3034", (2, 10): "3832", (2, 12): "2445",
         (2, 14): "91988", (2, 16): "4282", (4, 4): "3031", (4, 6): "3032", (4, 8): "3035",
         (4, 10): "3030", (4, 12): "3029", (6, 6): "3958", (6, 8): "3036", (6, 10): "3033",
         (6, 12): "3028", (6, 14): "3456", (6, 16): "3027", (8, 8): "41539", (8, 16): "92438"}
TILE = {(1, 1): "3070b", (1, 2): "3069b", (1, 3): "63864", (1, 4): "2431", (1, 6): "6636",
        (1, 8): "4162", (2, 2): "3068b", (2, 3): "26603", (2, 4): "87079", (2, 6): "69729"}
BRICK = {(1, 1): "3005", (1, 2): "3004", (1, 3): "3622", (1, 4): "3010", (1, 6): "3009",
         (1, 8): "3008"}
TRANS_PLATE = {(1, 1): "3024", (1, 2): "3023"}
TRANS_TILE = {(1, 1): "3070b", (1, 2): "3069b"}

# quarter-circle parts: arc centre in the part's frame; natural quadrant is (+x, -z)
ARC = {"30565": (-40, 40), "79393": (0, 0), "27507": (0, 0), "27925": (-10, 10)}


# ------------------------------------------------------------------------------ geometry helpers
def _dims(part: str) -> tuple[float, float]:
    lo, hi = ENG.geom.mesh(ENG.catalog.canonical(part)).bbox
    return hi[0] - lo[0], hi[2] - lo[2]


def rect_M(table: dict, i0: int, i1: int, k0: int, k1: int, y: float, pre=None):
    """(part, M) covering stud cells i0..i1 x k0..k1 (inclusive) with its top at y."""
    w, d = i1 - i0 + 1, k1 - k0 + 1
    part = table[(min(w, d), max(w, d))]
    bx, bz = _dims(part)
    R = np.eye(3) if abs(bx - S * w) < 1 and abs(bz - S * d) < 1 else rot(y=90)
    if pre is not None:
        R = R @ pre
    return part, transform((S * (i0 + i1) / 2, y, S * (k0 + k1) / 2), R)


def pack(cells: set, sizes, order: str = "row", prefer: str = "x", below: dict | None = None,
         shift: int = 0) -> list[tuple]:
    """Greedy cover of grid cells by rectangles (w along x, d along z); both orientations.
    Returns (i0, i1, k0, k1) tuples. With `below` (cell -> id of the part underneath) each
    rectangle is chosen to bridge as many different parts below as possible (then area);
    otherwise larger areas first, ties preferring the given direction. `shift` rotates the
    scan start so alternative layouts can be tried."""
    cells = set(cells)
    free = set(cells)
    cand = set()
    for a, b in sizes:
        cand.add((a, b))
        cand.add((b, a))
    cand = sorted(cand, key=lambda s: (-s[0] * s[1], -(s[0] if prefer == "x" else s[1])))
    keyf = (lambda c: (c[1], c[0])) if order == "row" else (lambda c: (c[0], c[1]))
    seq = sorted(cells, key=keyf)
    if shift:
        seq = seq[shift % len(seq):] + seq[:shift % len(seq)]
    out = []
    for c in seq:
        if c not in free:
            continue
        i, k = c
        best = None
        for w, d in cand:
            box = {(i + a, k + b) for a in range(w) for b in range(d)}
            if not box <= free:
                continue
            if below is None:
                best = (w, d, box)
                break
            ids = {below[x] for x in box if x in below}
            score = (len(ids), w * d)
            if best is None or score > best[0]:
                best = (score, (w, d, box))
        if best is None:
            continue
        w, d, box = best if below is None else best[1]
        free -= box
        out.append((i, i + w - 1, k, k + d - 1))
    return out


def cell_ids(rects: list[tuple], start: int = 0) -> dict:
    """cell -> rectangle id, for bonding the next layer."""
    out = {}
    for n, (i0, i1, k0, k1) in enumerate(rects, start):
        for i in range(i0, i1 + 1):
            for k in range(k0, k1 + 1):
                out[(i, k)] = n
    return out


def n_pieces(parts: list[tuple]) -> int:
    """Connected pieces among (part, M) pairs."""
    conns = [[c.transformed(M) for c in ENG.shadow.connectors(ENG.catalog.canonical(p))]
             for p, M in parts]
    parent = list(range(len(parts)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for c in find_connections(conns):
        parent[find(c.a)] = find(c.b)
    return len({find(i) for i in range(len(parts))})


def runs(n: int, lengths=(8, 6, 4, 3, 2, 1), phase: int = 0) -> list[int]:
    """Split a run of n studs into available lengths; `phase` shifts the first joint."""
    out, left = [], n
    if phase and n > phase:
        out.append(phase)
        left -= phase
    while left:
        for L in lengths:
            if L <= left:
                out.append(L)
                left -= L
                break
    return out


def quarter_M(part: str, k: int, y: float, centre=(0, 0)):
    """Quarter-circle part with its arc centre on `centre` (x, z), turned k * 90 deg."""
    cx, cz = ARC[part]
    return (translate(centre[0], y, centre[1]) @ transform((0, 0, 0), rot(y=90 * k))
            @ translate(-cx, 0, -cz))


# ------------------------------------------------------------------------------ step ordering
class Batch:
    """Collect placements, then emit them as build steps in an order where every step
    connects to what is already built (1..per_step parts, one category per step)."""

    def __init__(self, sub, model):
        self.sub, self.model, self.items = sub, model, []

    def add(self, part, color, M, cat, tag=""):
        self.items.append((self.model.canonical(part), color, np.asarray(M, float), cat, tag))

    def emit(self, captions: dict, per_step: int = 6, order=None):
        sub = self.sub
        prior = [(it.part, it.M) for it in sub.items if hasattr(it, "part")]
        allp = prior + [(p, M) for p, _, M, _, _ in self.items]
        conns = [[c.transformed(M) for c in ENG.shadow.connectors(p)] for p, M in allp]
        adj = defaultdict(set)
        for c in find_connections(conns):
            adj[c.a].add(c.b)
            adj[c.b].add(c.a)
        n0 = len(prior)
        built = set(range(n0))
        todo = list(range(len(self.items)))
        rank = {cat: r for r, cat in enumerate(order or [])}

        def key(j):
            p, _, M, cat, _ = self.items[j]
            return (rank.get(cat, 99), -M[1, 3], M[2, 3], M[0, 3])

        todo.sort(key=key)
        cur_cat, cur_n = None, 0
        while todo:
            ready = [j for j in todo if (adj[n0 + j] & built) or not built]
            if not ready:
                ready = todo[:1]
            same = [j for j in ready if self.items[j][3] == cur_cat] if cur_n < per_step else []
            j = same[0] if same else ready[0]
            p, color, M, cat, tag = self.items[j]
            if cat != cur_cat or cur_n >= per_step:
                sub.step(captions.get(cat, ""))
                cur_cat, cur_n = cat, 0
            pl = sub.place(p, color, (0, 0, 0), tag=tag)
            pl.M = M
            built.add(n0 + j)
            todo.remove(j)
            cur_n += 1
        self.items = []


# ------------------------------------------------------------------------------ bottom half
def bottom_half(model):
    sub = model.submodel("bottom_half", "Bottom half")
    b = Batch(sub, model)
    # 4x4 spindle openings: cells whose centres lie within 40 LDU (x and z) of the axis
    spindle = {(i, k) for i in range(-NI, NI + 1) for k in range(-NK, NK + 1)
               for ax, az in REEL_AXES.values()
               if abs(S * i - ax) < 40 and abs(S * k - az) < 40}
    screws = [(-11, -6), (11, -6), (-11, 6), (11, 6), (0, 5)]
    holes = [(0, -4), (0, 0)]          # lamp hole, reel-lock release hole (round, open stud)

    # bottom plate layer
    cells = set()
    for i in range(-NI, NI + 1):
        for k in range(-NK, NK + 1):
            if k == -6 and abs(i) <= 9:
                continue            # under the dust door
            if k == -5 and abs(i) <= 7:
                continue            # tape mouth: open underneath (head-drum cut-out)
            cells.add((i, k))
    cells -= spindle
    cells -= set(screws) | set(holes)
    for i0, i1, k0, k1 in pack(cells, [(6, 16), (6, 14), (6, 12), (8, 16), (8, 8), (6, 10),
                                      (6, 8), (4, 12), (4, 10), (4, 8), (6, 6), (4, 6), (4, 4),
                                      (2, 16), (2, 12), (2, 10), (2, 8), (2, 6), (2, 4), (2, 3),
                                      (2, 2), (1, 8), (1, 6), (1, 4), (1, 3), (1, 2), (1, 1)],
                               order="col", prefer="z"):
        p, M = rect_M(PLATE, i0, i1, k0, k1, Y_BOTTOM)
        b.add(p, "shell", M, "floor")
    for i, k in screws:
        b.add("6141", "metal", transform((S * i, Y_BOTTOM, S * k)), "screws")
    for i, k in holes:
        b.add("85861", "shell", transform((S * i, Y_BOTTOM, S * k)), "floor")

    # wall footprint (courses C1..C3) and other things standing on the bottom plates
    side = {(s * 11, k) for s in (-1, 1) for k in range(-NK, NK + 1)}
    corner_inner = {(s * 10, k) for s in (-1, 1) for k in (-6, -5)}
    back = {(i, 6) for i in range(-10, 11)}
    beam_ends = {(s * 10, -4) for s in (-1, 1)}
    posts = {(0, 5), (0, -3)}
    walls = side | corner_inner | back | beam_ends | posts

    # floor tiles (smooth floor the reels slide on)
    floor = {(i, k) for i in range(-10, 11) for k in range(-3, 6)} - walls
    ring_zone, ring_corners = set(), []
    for ax, az in REEL_AXES.values():
        zone = {(i, k) for i in range(-NI, NI + 1) for k in range(-NK, NK + 1)
                if abs(S * i - ax) < 60 and abs(S * k - az) < 60}
        ring_zone |= zone
        for dx in (-50, 50):
            for dz in (-50, 50):
                ring_corners.append(((ax + dx) // S, (az + dz) // S))
    floor -= ring_zone
    for i0, i1, k0, k1 in pack(floor, [(2, 6), (2, 4), (2, 3), (2, 2), (1, 6), (1, 4), (1, 3),
                                      (1, 2), (1, 1)], order="row", prefer="x"):
        p, M = rect_M(TILE, i0, i1, k0, k1, Y_FLOOR)
        b.add(p, "shell", M, "floor_tiles")
    for i, k in ring_corners:
        b.add("98138", "shell", transform((S * i, Y_FLOOR, S * k)), "floor_tiles")
    for ax, az in REEL_AXES.values():   # round spindle rim: 3x3 macaroni tiles around the hole
        for q in range(4):
            b.add("79393", "shell", quarter_M("79393", q, Y_FLOOR, (ax, az)), "spindle")

    # walls: C1 plates, C2 bricks, C3 plates (joints staggered)
    def wall_runs(cells_line, table, y, cat, color="shell", phase=0, lengths=(8, 6, 4, 3, 2, 1)):
        """cells_line: ordered list of cells in one straight line (same k or same i)."""
        pos = 0
        for L in runs(len(cells_line), lengths, phase):
            seg = cells_line[pos:pos + L]
            pos += L
            i0, i1 = min(c[0] for c in seg), max(c[0] for c in seg)
            k0, k1 = min(c[1] for c in seg), max(c[1] for c in seg)
            p, M = rect_M(table, i0, i1, k0, k1, y)
            b.add(p, color, M, cat)

    label_i = range(-8, 9)             # spine label: white across the middle of the back wall
    for s in (-1, 1):
        col = [(s * 11, k) for k in range(-6, 7)]
        wall_runs(col, PLATE, Y_C1, "walls_1", phase=0)
        wall_runs(col, PLATE, Y_C3, "walls_3", phase=4)
    # back wall (between the side walls): the spine label is white in C1 and C2
    wall_runs([(i, 6) for i in range(-10, -8)], PLATE, Y_C1, "walls_1")
    wall_runs([(i, 6) for i in label_i], PLATE, Y_C1, "walls_1", color="label", phase=4)
    b.add("3024", "detail", transform((S * 10, Y_C1, S * 6)), "walls_1")   # write-protect tab
    b.add("3024", "shell", transform((S * 9, Y_C1, S * 6)), "walls_1")
    wall_runs([(i, 6) for i in range(-10, 11)], PLATE, Y_C3, "walls_3", phase=3)
    for i, k in corner_inner | beam_ends | posts:
        b.add("3024", "shell", transform((S * i, Y_C1, S * k)), "walls_1")
        b.add("3024", "shell", transform((S * i, Y_C3, S * k)), "walls_3")
    # C2 bricks
    for s in (-1, 1):
        col = [(s * 11, k) for k in range(-4, 7)]     # corners (k -6, -5) are special
        wall_runs(col, BRICK, Y_C2, "walls_2", phase=3, lengths=(6, 4, 3, 2, 1))
    wall_runs([(i, 6) for i in range(-10, -8)], BRICK, Y_C2, "walls_2")
    wall_runs([(i, 6) for i in range(9, 11)], BRICK, Y_C2, "walls_2")
    wall_runs([(i, 6) for i in label_i], BRICK, Y_C2, "walls_2", color="label", phase=3,
              lengths=(6, 4, 3, 2, 1))
    for i, k in beam_ends | posts:
        b.add("3005", "shell", transform((S * i, Y_C2, S * k)), "walls_2")
    # corner blocks: light-path hole through each front corner, door release on the right side
    for s in (-1, 1):
        for i in (10, 11):
            b.add("6541", "shell", transform((s * S * i, Y_C2, -100), rot(y=90)), "corners")
        b.add("3005", "shell", transform((s * S * 10, Y_C2, -120)), "corners")
        if s < 0:
            b.add("4070", "button", transform((-S * 11, Y_C2, -120), rot(y=90)), "corners")
        else:
            b.add("3005", "shell", transform((S * 11, Y_C2, -120)), "corners")

    # front beam: tape backing bricks with side studs, guide pins, rollers
    for x0, x1 in ((-170, -90), (-90, -10), (10, 90), (90, 170)):
        b.add("30414", "shell", transform(((x0 + x1) / 2, -32, -80)), "tape_path")
    b.add("87087", "shell", transform((0, -32, -80)), "tape_path")
    for s in (-1, 1):
        for y in (-16, -24, -32):
            b.add("6141", "metal", transform((s * 180, y, -80)), "tape_path")
        b.add("3062b", "roller", transform((s * 180, -32, -100)), "tape_path")
    for a, bb in ((-190, -30), (-30, 30), (30, 190)):     # plates on top of the beam
        n = (bb - a) // S
        b.add(PLATE[(1, n)] if n in (1, 2, 3, 4, 6, 8) else "3460", "shell",
              transform(((a + bb) / 2, Y_C2, -80)), "beam_top")
    for a, bb in ((-190, -170), (-130, -10), (-10, 10), (10, 130), (170, 190)):
        n = (bb - a) // S
        b.add(PLATE[(1, n)], "shell", transform(((a + bb) / 2, Y_C3, -80)), "beam_top")
    # the tape itself, running across the mouth between the rollers
    for x0, x1 in ((-170, -110), (-110, -30), (-30, 30), (30, 110), (110, 170)):
        n = (x1 - x0) // S
        b.add(TILE[(1, n)], "tape", transform(((x0 + x1) / 2, -22, -98), SNOT), "tape")
    # door hinge mounts and hinge bases
    for s in (-1, 1):
        b.add("99206", "shell", transform((s * 150, Y_TOP_PLATE, -80)), "hinges")
        b.add("3937", "shell", transform((s * 150, DOOR_AXIS[0], -114), HINGE_W), "hinges")

    b.emit({"floor": "Lay the floor of the bottom half", "screws": "Five screws hold the halves",
            "floor_tiles": "Tile the floor so the reels can spin",
            "spindle": "Round rims for the reel drive holes",
            "walls_1": "First course of the walls", "walls_2": "Walls - spine label goes white",
            "walls_3": "Top course of the walls", "corners": "Front corners: light-path windows",
            "tape_path": "Tape path: backing, metal guide pins and rollers",
            "beam_top": "Cap the front beam", "tape": "Thread the tape across the mouth",
            "hinges": "Hinge mounts for the dust door"},
           order=["floor", "screws", "floor_tiles", "spindle", "walls_1", "corners",
                  "tape_path", "walls_2", "beam_top", "walls_3", "tape", "hinges"])
    return sub


# ------------------------------------------------------------------------------ dust door
def door(model):
    sub = model.submodel("door", "Dust door")

    def run(table, color, x0, x1, y, z):
        n = (x1 - x0) // S
        return sub.place(table[n], color, ((x0 + x1) / 2, y, z), SNOT)

    P1 = {1: "3024", 2: "3023", 3: "3623", 4: "3710", 6: "3666", 8: "3460"}
    P2 = {2: "3022", 3: "3021", 4: "3020", 6: "3795", 8: "3034"}
    T1 = {1: "3070b", 2: "3069b", 3: "63864", 4: "2431", 6: "6636", 8: "4162"}
    T2 = {2: "3068b", 3: "26603", 4: "87079", 6: "69729"}
    sub.step("Door panel: start with a 2 x 6 plate")
    run(P2, "shell", -190, -70, -40, -122)
    sub.step("Add plates and tie them with a tile")
    for a, bb in ((-70, -30), (-30, 30)):
        run(P2, "shell", a, bb, -40, -122)
    run(T1, "shell", -130, -10, -50, -130)
    sub.step()
    for a, bb in ((30, 70), (70, 190)):
        run(P2, "shell", a, bb, -40, -122)
    run(T1, "shell", 10, 130, -50, -130)
    run(T1, "shell", -10, 10, -50, -130)
    sub.step("Smooth front face")
    for a, bb in ((-190, -130), (130, 190)):
        run(T1, "shell", a, bb, -50, -130)
    for a, bb in ((-190, -130), (-130, -10), (10, 130), (130, 190)):
        run(T2, "shell", a, bb, -20, -130)
    sub.place("3069b", "shell", (0, -20, -130), SNOT @ rot(y=90))
    sub.step("Bottom edge of the door")
    for a, bb in ((-190, -30), (-30, 30), (30, 190)):
        run(P1, "shell", a, bb, -10, -122)
    sub.step("Door top: fillers that swing up with the door")
    for z in (-114, -106):
        for a, bb in ((-190, -170), (-130, -10), (-10, 10), (10, 130), (170, 190)):
            run(P1, "shell", a, bb, -50, z)
    sub.step("Hinge tops")
    for x in (-150, 150):
        sub.place("6134", "shell", (x, DOOR_AXIS[0], -114), HINGE_W)
    return sub


# ------------------------------------------------------------------------------ reels
def reel(model, name, title, full: bool):
    """A VHS reel: white lower flange, tape pack, raised white hub with a centre bore."""
    s = model.submodel(name, title)
    s.step("Hub core (the pin passes through here)")
    s.place("11833", "hub", (0, -16, 0))
    s.step("Lower flange")
    for q in range(4):
        pl = s.place("30565", "flange", (0, 0, 0))
        pl.M = quarter_M("30565", q, -8)
    s.step("Tape pack" if full else "A little tape left - and the flange shows")
    for q in range(4):
        pl = s.place("79393", "tape", (0, 0, 0))
        pl.M = quarter_M("79393", q, -16)
    for q in range(4):
        pl = s.place("27507", "tape" if full else "flange", (0, 0, 0))
        pl.M = quarter_M("27507", q, -16)
    s.step("Hub")
    s.place("60474", "hub", (0, -24, 0))
    return s


# ------------------------------------------------------------------------------ top half
def top_half(model, reels):
    sub = model.submodel("top_half", "Top half")
    b = Batch(sub, model)
    top = {(i, k) for i in range(-NI, NI + 1) for k in range(-4, NK + 1)}
    top |= {(i, k) for i in (-11, -10, 10, 11) for k in (-6, -5)}
    hinge_holes = {(s * i, -4) for s in (-1, 1) for i in (7, 8)}     # 99206 raised studs
    pin_cells = {(i, k) for ax, az in REEL_AXES.values() for i in range(-NI, NI + 1)
                 for k in range(-NK, NK + 1) if abs(S * i - ax) < 20 and abs(S * k - az) < 20}
    win_tiles = {(i, k) for i in range(-7, 8) for k in range(-1, 3)}
    win_plates = {(i, k) for i in range(-7, 8) for k in range(-2, 4)} - pin_cells
    label = {(i, k) for i in range(-8, 9) for k in (4, 5)}
    grille = {(i, k) for i in (-11, -10, 10, 11) for k in (-6, -5)}
    arrows = {(i, k) for s in (-1, 1) for i in (s * 2, s * 3) for k in (-4, -3, -2)}

    # plate layer
    black_plates = top - hinge_holes - pin_cells - win_plates
    for i0, i1, k0, k1 in pack(black_plates, [(6, 16), (6, 12), (6, 10), (6, 8), (4, 12),
                                             (4, 10), (4, 8), (6, 6), (4, 6), (4, 4), (2, 16),
                                             (2, 12), (2, 10), (2, 8), (2, 6), (2, 4), (2, 3),
                                             (2, 2), (1, 8), (1, 6), (1, 4), (1, 3), (1, 2),
                                             (1, 1)], order="row", prefer="x"):
        p, M = rect_M(PLATE, i0, i1, k0, k1, Y_TOP_PLATE)
        b.add(p, "shell", M, "plates")
    for i0, i1, k0, k1 in pack(win_plates, [(1, 2), (1, 1)], order="row", prefer="x"):
        p, M = rect_M(TRANS_PLATE, i0, i1, k0, k1, Y_TOP_PLATE)
        b.add(p, "window", M, "window")
    for ax, az in REEL_AXES.values():
        b.add("4032a", "spring", transform((ax, Y_TOP_PLATE, az)), "window")

    # tile layer
    for i0, i1, k0, k1 in pack(win_tiles, [(1, 2), (1, 1)], order="col", prefer="z"):
        p, M = rect_M(TRANS_TILE, i0, i1, k0, k1, Y_TOP_TILE)
        b.add(p, "window", M, "window_tiles")
    for x0, x1 in ((-170, -90), (-90, -10), (10, 90), (90, 170)):
        b.add("87079", "label", transform(((x0 + x1) / 2, Y_TOP_TILE, 90)), "label")
    b.add("3069b", "label", transform((0, Y_TOP_TILE, 90), rot(y=90)), "label")
    for s in (-1, 1):
        for k in (-6, -5):
            b.add("2412b", "shell", transform((s * 210, Y_TOP_TILE, S * k)), "grip")
        b.add("22385", "detail", transform((s * 50, Y_TOP_TILE, -60)), "arrows")
    black_tiles = top - win_tiles - label - grille - arrows
    for i0, i1, k0, k1 in pack(black_tiles, [(2, 6), (2, 4), (2, 3), (2, 2), (1, 6), (1, 4),
                                            (1, 3), (1, 2), (1, 1)], order="col", prefer="z"):
        p, M = rect_M(TILE, i0, i1, k0, k1, Y_TOP_TILE)
        b.add(p, "shell", M, "tiles")
    b.emit({"plates": "Top half: plate layer (build it on the table, window side up)",
            "window": "Smoked window plates and the reel-spring holders",
            "tiles": "Smooth the top with tiles", "window_tiles": "Window glass",
            "label": "Face label recess", "grip": "Grip ridges on the front corners",
            "arrows": "Moulded insert arrows"},
           order=["plates", "window", "tiles", "window_tiles", "label", "grip", "arrows"])
    sub.step("Turn the top half over: push in the two reel pins")
    for ax, az in REEL_AXES.values():
        sub.place("4274", "spring", (ax, -48, az), rot(z=-90))
    sub.step("Slide the full supply reel onto its pin")
    sub.use(reels["reel_l"], (REEL_AXES["reel_l"][0], -16, REEL_AXES["reel_l"][1]), tag="reel_l")
    sub.step("Slide the nearly empty take-up reel onto its pin")
    sub.use(reels["reel_r"], (REEL_AXES["reel_r"][0], -16, REEL_AXES["reel_r"][1]), tag="reel_r")
    return sub


# ------------------------------------------------------------------------------ checks & poses
REAL_MM = (187.0, 103.0, 25.0)


def check_dimensions(ctx):
    pts = []
    for p in ctx.placed:
        lo, hi = ctx.geom.mesh(p.part).bbox
        corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1])
                            for z in (lo[2], hi[2])])
        pts.append(corners @ p.M[:3, :3].T + p.M[:3, 3])
    allp = np.concatenate(pts)
    size_mm = (allp.max(0) - allp.min(0)) * 0.4
    got = (size_mm[0], size_mm[2], size_mm[1])          # width, depth, height
    issues = []
    for name, g, want in zip(("width", "depth", "height"), got, REAL_MM):
        if abs(g - want) > 5.0:
            issues.append({"problem": f"{name} {g:.1f} mm is not within 5 mm of the real "
                                      f"VHS cassette's {want:.0f} mm"})
    return issues


def pose(t: float) -> dict:
    y, z = DOOR_AXIS
    door_T = translate(0, y, z) @ transform((0, 0, 0), rot(x=-90.0 * t)) @ translate(0, -y, -z)
    out = {"flap": door_T}
    # playing: both reels turn the same way; the small take-up pack spins faster (4:3)
    for g, deg in (("reel_l", 270.0), ("reel_r", 360.0)):
        ax, az = REEL_AXES[g]
        out[g] = (translate(ax, 0, az) @ transform((0, 0, 0), rot(y=deg * t))
                  @ translate(-ax, 0, -az))
    return out


def build(model):
    reels = {"reel_l": reel(model, "reel_full", "Supply reel (full)", True),
             "reel_r": reel(model, "reel_empty", "Take-up reel (nearly empty)", False)}
    bottom = bottom_half(model)
    flap = door(model)
    top = top_half(model, reels)

    main = model.main
    main.step("Bottom half")
    main.use(bottom)
    main.step("Click the dust door onto its hinges")
    main.use(flap, tag="flap", insert=(0, 0, -1))
    main.step("Lower the top half (with its reels) onto the bottom half")
    main.use(top)

    model.moving_group("flap", "flap")
    model.moving_group("reel_l", "reel_l")
    model.moving_group("reel_r", "reel_r")
    model.pose = pose
    model.extra_checks.append(check_dimensions)
