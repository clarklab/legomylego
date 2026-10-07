"""The big Nautilus's display stand: a sculpted sea under the hull, the sub held up on two clear
posts plugged into its keel fins.

World frame (the main model's): the table is y = 0, -Y up, the hull runs along X (bow -X), the
front faces -Z. Stud cells: column i is x in [20 i, 20 i + 20], row k is z in [20 k, 20 k + 20].

The base is a hollow, organic oval about 115 x 34 studs (92 x 27 cm) and 4 cm deep: a deck of
two crossed layers of plates on pillars and walls three bricks tall, black below fading to dark
blue at the top, a black plinth line under them. On the deck the sea, in a Japanese-print style:
big swells across it marching toward the bow, tiers of curved slopes rising to white-capped
crests (the posts stand in the troughs, ringed with foam), a great wave breaking under the bow,
its white lip curling over with foam claws and spray; a reef of banded rock by the stern with
kelp, coral and a crab in turquoise shallows; the giant squid's tentacles breaking the surface
at the front; a black nameplate framed in brass for a sticker.

Each post is a tube of clear 4 x 4 ring plates standing on a hollow pillar in the base. The
lights' lead runs down the middle of one tube and its pillar, out of a doorway at the pillar's
foot, across the inside of the base and round the battery box (Power Functions AAA, 64228),
which lies on its back at the rear, its button, light and plug facing a window in the back
wall; it slides out backwards to change the batteries.

`build_stand(model, posts)` builds it all into `model.main` (tag "stand") and returns a
StandInfo: where to put the hull's frame, the posts and their tops, the lead's exit and route.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from brickkit.ldraw.matrix import rot, transform
from naut_kit import AV, BRICK, PLATE, S, TILE, Batch, cells_of, ids_of, pack, rect_part

# ------------------------------------------------------------------ colours (real names)
COL = dict(
    plinth="Black", wall="Dark Blue", wall_low="Black", pillar="Black", deck="Dark Blue",
    deck_in="Black", deep="Dark Blue", sea="Blue", mid="Dark Azure", light="Medium Azure",
    glint="Trans-Light Blue", sparkle="Trans-Clear", foam="White", post="Trans-Clear",
    battery="Light Bluish Gray", nameplate="Black", brass="Pearl Gold",
    tentacle="Red", shallow="Dark Turquoise",
)

# ------------------------------------------------------------------ the base's shape
XC = -100.0                # the oval's middle (under the hull's middle)
A_HALF = 1150.0            # half-length (x): 115 studs, 92 cm
B_HALF = 340.0             # half-width (z): 34 studs, 27 cm
PLINTH_TOP = -8            # a line of black plates under the walls
WALL_TOP = -80             # three courses of bricks
DECK_TOP = -96             # two layers of plates: the sea's floor
CALM = DECK_TOP - 8        # the calm sea's tiles
GAP = 200                  # the lowest keel fin this far above the calm sea (if hull_y not given)
BELLY = 168                # the hull's keel strip's underside (naut_shape.KEEL_TOP + 16)
N_REGIONS = 8              # the sea is built in this many stretches along X

# default posts (hull frame, x, z, y_top): naut_keel.post_tops() as of writing: the forward
# post meets the keel strip's underside just ahead of the forward keel fin (naut_shape.POSTS[0]),
# the after one the after fin's underside (POSTS[1])
DEFAULT_POSTS = ((-480.0, 0.0, 168.0), (380.0, 0.0, 248.0))


def _wobble(t: float) -> float:
    return 0.018 * math.sin(3 * t + 0.6) + 0.012 * math.sin(7 * t + 2.0) + \
        0.008 * math.sin(11 * t + 0.3)


def inside(x: float, z: float) -> bool:
    """Is (x, z) inside the oval? A superellipse, fuller toward the stern, with a slight
    organic wobble."""
    u, v = (x - XC) / A_HALF, z / B_HALF
    n = 2.3 if u < 0 else 2.7
    r = (abs(u) ** n + abs(v) ** n) ** (1 / n)
    return r <= 1.0 + _wobble(math.atan2(v, u))


def all_cells() -> set:
    i0, i1 = int((XC - A_HALF) // S) - 2, int((XC + A_HALF) // S) + 2
    k0, k1 = int(-B_HALF // S) - 2, int(B_HALF // S) + 2
    cells = {(i, k) for i in range(i0, i1 + 1) for k in range(k0, k1 + 1)
             if inside(S * i + 10, S * k + 10)}
    # no spurs: every cell has at least two neighbours inside, along each axis or the other
    while True:
        spur = {(i, k) for i, k in cells
                if ((i - 1, k) not in cells and (i + 1, k) not in cells)
                or ((i, k - 1) not in cells and (i, k + 1) not in cells)}
        if not spur:
            return cells
        cells -= spur


def ring_cells(cells: set) -> set:
    """Cells with an outside cell among their eight neighbours: the walls."""
    return {(i, k) for i, k in cells
            if any((i + a, k + b) not in cells for a in (-1, 0, 1) for b in (-1, 0, 1))}


def _noise(x, z, seed=0.0):
    return (math.sin(0.0155 * x + 0.0415 * z + seed) + 0.7 * math.sin(0.0085 * x - 0.0275 * z
            + 1.3 + 2 * seed) + 0.5 * math.sin(0.0265 * x + 0.0105 * z + 2.2 - seed))


def _hash(i, k, s=0):
    """A repeatable pseudo-random number in [0, 1) for a cell."""
    v = math.sin(i * 127.1 + k * 311.7 + s * 74.7) * 43758.5453
    return v - math.floor(v)


# ------------------------------------------------------------------ result
@dataclass
class StandInfo:
    hull_y: float                       # put the hull's frame at (0, hull_y, 0) in the world
    post_tops: list                     # world (x, y, z) of each post's top (a fin's underside)
    lead_post: int                      # which post the lead runs down
    lead_exit: tuple                    # world (x, y, z): the lead leaves the post's top here
    lead_route: list                    # world points from the post's top to the box's plug
    lead_length: float                  # LDU along that route
    post_plates: list = field(default_factory=list)   # ring plates in each post
    battery: tuple = ()                 # world (x, y, z) of the box's top face's centre
    battery_tag: str = "battery"        # the battery box's tag (a press fit)


# ------------------------------------------------------------------ helpers
BIG_PLATE = {**PLATE, (2, 14): "91988", (2, 16): "4282", (6, 14): "3456", (6, 16): "3027",
             (8, 8): "41539", (8, 16): "92438", (16, 16): "91405"}


def _rect(bt, table, r, top, color, cat, tag="", insert=None):
    i0, i1, k0, k1 = r
    part, R = rect_part(table, i1 - i0 + 1, k1 - k0 + 1)
    bt.add(part, color, transform((S * (i0 + i1 + 1) / 2, top, S * (k0 + k1 + 1) / 2), R),
           cat, tag, insert)


def _sizes(table, color, max_long=12, max_short=6):
    return [s for s in AV.sizes(table, color) if s[1] <= max_long and s[0] <= max_short]


def _square(ci, ck, half):
    """Cells of a (2 half) x (2 half) square centred on the grid point (20 ci, 20 ck)."""
    return {(i, k) for i in range(ci - half, ci + half) for k in range(ck - half, ck + half)}


class Layout:
    """Where everything goes (cells), from the posts' positions."""

    def __init__(self, posts_world):
        self.cells = all_cells()
        self.ring = ring_cells(self.cells)
        self.i_min = min(i for i, _ in self.cells)
        self.i_max = max(i for i, _ in self.cells)
        self.posts = posts_world                       # [(x, z)] on grid lines (x, z % 20 == 0)
        self.post_sq, self.post_pad, self.post_splash = {}, {}, {}
        for n, (x, z) in enumerate(self.posts):
            ci, ck = int(x // S), int(z // S)
            self.post_sq[n] = _square(ci, ck, 2)       # the tube's hole in the deck
            self.post_pad[n] = _square(ci, ck, 3)      # the pillar's top under the deck
            self.post_splash[n] = _square(ci, ck, 4)   # the ring of foam round it
            if not self.post_splash[n] <= self.cells - self.ring:
                raise ValueError(f"post {n} at x={x}, z={z} is too near the base's edge")
        # the battery box: on its back on the table at the rear, between the posts, its top
        # (button, plug) facing +Z one stud in from the back wall's outer face
        bx = S * round((sum(x for x, _ in self.posts) / len(self.posts)) / S)
        back = max(k for i, k in self.cells if bx - 80 <= S * i + 10 <= bx + 100)
        self.box = (bx, -40.0, S * back)               # (x, y, z of its top face)
        bz = self.box[2]
        self.box_cells = {(i, k) for i in range(int((bx - 80) // S), int((bx + 80) // S))
                          for k in range(int((bz - 100) // S), back + 1)}
        # the window in the back wall: the box's width and a stud more at its plug's end,
        # where the lead comes round from inside
        self.opening = {(i, k) for i, k in self.ring
                        if bx - 80 <= S * i + 10 <= bx + 100 and S * k >= bz - 100}
        # the bay's side walls inside: one beside the box, one past the lead's gap
        bi0 = int((bx - 80) // S)
        self.bay = {(i, k) for i in (bi0 - 1, bi0 + 9) for k in range(back - 5, back)}
        self.lead_gap = {(bi0 + 8, k) for k in range(back - 6, back + 1)}   # kept clear
        # regions along X (build order of the sea)
        span = self.i_max - self.i_min + 1
        self.region_bounds = [self.i_min + round(r * span / N_REGIONS)
                              for r in range(N_REGIONS + 1)]

    def region(self, i):
        for n in range(N_REGIONS):
            if i < self.region_bounds[n + 1]:
                return n
        return N_REGIONS - 1

    def front_row(self, i):
        return min(k for a, k in self.cells if a == i)


# ------------------------------------------------------------------ the base
# 1 x 3 bricks round a 2 x 2 hole (offsets of their middles from the post's centre), along X,
# Z, X, Z: one way round and the other
_PINWHEEL = (((-10, -30), (30, -10), (10, 30), (-30, 10)),
             ((10, -30), (30, 10), (-10, 30), (-30, -10)))


def _pillar_cells(L: Layout) -> list:
    """2 x 2 pillars under the deck, on a grid."""
    taken = set(L.ring) | set(L.box_cells) | L.bay | L.lead_gap
    for n in L.post_pad:
        taken |= L.post_pad[n]
    near = {(i + a, k + b) for i, k in taken for a in (-1, 0, 1) for b in (-1, 0, 1)}
    out, used = [], set()
    for i in range(L.i_min + 6, L.i_max, 11):
        for k in range(-18, 20, 8):
            sq = {(i, k), (i + 1, k), (i, k + 1), (i + 1, k + 1)}
            grow = {(a + x, b + y) for a, b in sq for x in (-1, 0, 1) for y in (-1, 0, 1)}
            if sq <= L.cells and not sq & near and not grow & used:
                out.append((i, k))
                used |= sq
    return out


def base(model, L: Layout):
    """The hollow base, built upside down from its top: the deck (two crossed layers of plates
    with holes for the posts' tubes, the lower one big black plates inside a ring of dark blue
    ones along the edge, the upper one dark blue), then hanging under it the pillars, the
    hollow pillars under the posts, the walls three bricks deep and their black plinth; turned
    over onto the table, the battery box slides into its bay through the window at the
    back."""
    sub = model.submodel("stand_base", "Sea base")
    bt = Batch()
    cells = deck_cells(L)
    rim = L.ring & cells
    r1 = pack(rim, [s for s in _sizes(PLATE, COL["deck"]) if s[0] <= 2], prefer="z")
    r1 += _pack_bands(cells - rim, AV.sizes(BIG_PLATE, COL["deck_in"]), 8, 0)
    for r in r1:
        part, R = rect_part(BIG_PLATE, r[1] - r[0] + 1, r[3] - r[2] + 1)
        color = COL["deck"] if cells_of(r) & rim else COL["deck_in"]
        bt.add(part, color, transform((S * (r[0] + r[1] + 1) / 2, WALL_TOP - 8,
                                       S * (r[2] + r[3] + 1) / 2), R), "deck1")
    # the upper layer: big plates, repacked where they leave a piece of the deck on its own
    r2 = _bond_layer(r1, cells, _sizes(PLATE, COL["deck"]), band=6)
    for r in r2:
        _rect(bt, PLATE, r, DECK_TOP, COL["deck"], "deck2")
    # under it, hanging: pillars down to the table, hollow ones under the posts
    for i, k in _pillar_cells(L):
        x, z = S * i + 20, S * k + 20
        for c in range(3):
            bt.add("3003", COL["pillar"], transform((x, -24 * (c + 1), z)), "pillars",
                   insert=(0, 1, 0))
        bt.add("3022", COL["pillar"], transform((x, WALL_TOP, z)), "pillars", insert=(0, 1, 0))
    # hollow pillars under the posts: rings of 1 x 3 bricks turned in a pinwheel round the
    # lead's shaft (each course the other way round), a doorway in the lowest course toward
    # the battery box (+Z), and a pinwheel of 2 x 4 plates on top, 6 x 6 round the shaft
    for n, (px, pz) in enumerate(L.posts):
        for c in range(3):
            for j, (dx, dz) in enumerate(_PINWHEEL[c % 2]):
                part, pos = "3622", (px + dx, pz + dz)
                if c == 0 and j == 2:
                    part, pos = "3004", (px + 20, pz + 30)
                bt.add(part, COL["pillar"], transform((pos[0], -24 * (c + 1), pos[1]),
                                                      rot(y=90) if j % 2 else None), "pillars",
                       insert=(0, 1, 0))
        for j, (dx, dz) in enumerate(((-20, -40), (40, -20), (20, 40), (-40, 20))):
            bt.add("3020", COL["pillar"], transform((px + dx, WALL_TOP, pz + dz),
                                                    rot(y=90) if j % 2 else None), "pillars",
                       insert=(0, 1, 0))
    # the walls (with the battery bay's), hanging from the deck's edge, and the plinth
    walls = (L.ring - L.opening) | L.bay
    bsz = [s for s in AV.sizes(BRICK, COL["wall"]) if s[0] == 1 and s[1] <= 8]
    above = r1
    for c in range(3):
        rects = pack(walls, bsz, ids_of(above), shift=3 + 4 * c, prefer="x")
        color = COL["wall"] if c == 0 else COL["wall_low"]
        for r in rects:
            _rect(bt, BRICK, r, WALL_TOP + 24 * c, color, "walls", insert=(0, 1, 0))
        above = rects
    psz = [s for s in _sizes(PLATE, COL["plinth"]) if s[0] == 1]
    for r in pack(walls, psz, ids_of(above), prefer="x"):
        _rect(bt, PLATE, r, PLINTH_TOP, COL["plinth"], "plinth", insert=(0, 1, 0))
    bt.emit(sub, phases=[["deck1"], ["deck2"], ["pillars", "walls"], ["plinth"]],
            captions={"deck1": "The sea base, built upside down from its top: the deck's "
                               "first layer of plates",
                      "deck2": "A second layer across the first ties it together",
                      "pillars": "Pillars under it, hollow ones under the posts' holes for "
                                 "the lead",
                      "walls": "The walls round its edge, three bricks deep; a window at the "
                               "back for the battery box",
                      "plinth": "A line of black plates under the walls"},
            per_step=12, reach=240, hanging=("pillars", "walls", "plinth"))
    bx, by, bz = L.box
    sub.step("Turn the base over. The battery box, on its back, slides in from behind: its "
             "button and plug face the window in the back wall")
    sub.place("64228", COL["battery"], (bx, by, bz), rot(x=-90), tag="battery",
              insert=(0, 0, 1))
    return sub


def _components(layers):
    """Groups of rectangles (index pairs (layer, n)) joined by overlapping between layers."""
    parent = {}

    def root(a):
        parent.setdefault(a, a)
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    prev = {}
    for n, rects in enumerate(layers):
        cur = {}
        for j, r in enumerate(rects):
            root((n, j))
            for c in cells_of(r):
                cur[c] = (n, j)
                if c in prev:
                    parent[root(prev[c])] = root((n, j))
        prev = cur
    groups = {}
    for a in list(parent):
        groups.setdefault(root(a), []).append(a)
    return sorted(groups.values(), key=len)


def _pack_bands(cells, sizes, band, offset):
    """Big plates over a large irregular area: pack it in bands `band` columns wide (across
    the oval), each band apart, so plates span the band instead of strips along the
    outline."""
    bands = {}
    for i, k in cells:
        bands.setdefault((i - offset) // band, set()).add((i, k))
    out = []
    for _, cs in sorted(bands.items()):
        out += pack(cs, [s for s in sizes if s[0] <= band], prefer="z")
    return out


def _bond_layer(lower, cells, sizes, tries=200, shift=7, band=None):
    """Pack `cells` with plates over the `lower` layer so the two layers make one piece: start
    from plain big plates; while a piece stands apart, lay a plate across from it onto the
    rest (the one joining the most lower plates), and repack what that plate displaced."""
    upper = (pack(cells, sizes, shift=shift, prefer="x") if band is None else
             _pack_bands(cells, sizes, band, 3))
    lower_of = ids_of(lower)
    shapes = sorted({(a, b) for s in sizes for a, b in (s, s[::-1])}, key=lambda t: -t[0] * t[1])
    for _ in range(tries):
        comps = _components([lower, upper])
        if len(comps) == 1:
            return upper
        island = set()
        for n, j in comps[0]:
            island |= cells_of(lower[j] if n == 0 else upper[j])
        best = None
        for w, d in shapes:
            for i, k in island:
                for i0 in range(i - w + 1, i + 1):
                    for k0 in range(k - d + 1, k + 1):
                        box = {(i0 + a, k0 + b) for a in range(w) for b in range(d)}
                        if not box <= cells or box <= island:
                            continue
                        score = (len({lower_of[c] for c in box}), w * d)
                        if best is None or score > best[0]:
                            best = (score, box, (i0, i0 + w - 1, k0, k0 + d - 1))
        if best is None:
            break
        box = best[1]
        hit = [r for r in upper if cells_of(r) & box]
        rest = set()
        for r in hit:
            rest |= cells_of(r)
        rest -= box
        upper = [r for r in upper if r not in hit] + [best[2]] + (
            pack(rest, sizes, prefer="x") if rest else [])
    raise ValueError("the deck's layers would not hold together")


def deck_cells(L: Layout) -> set:
    holes = set()
    for n in L.post_sq:
        holes |= L.post_sq[n]
    return L.cells - holes


# ------------------------------------------------------------------ the sea's surface
class Plan:
    """The sea's surface: placements (world), each with a category and the region it's in."""

    def __init__(self, L: Layout):
        self.L = L
        self.free = deck_cells(L)
        self.items = []               # (part, color, M, cat, region, low)
        self.crests = {}              # (i, k) -> (height of a swell's crest, region)
        self.stack = {}               # (i, k) -> (height under a crest or a tier, region)
        self.face = {}                # (i, k) -> (height of the breaker's face, region)
        self.lip = {}                 # (region, crest height, level) -> cells of its lip
        self.lip_bricks = {}          # (region, crest height) -> cells beside its slopes
        self.wave_rows = {}           # (i, k) -> "front" | "back" | "crest"
        self.cur = None               # the region of the feature being planned
        self.spray = set()            # crest cells that throw up spray

    def add(self, part, color, pos, R=None, cat="calm", i=None, M=None, low=None):
        """Items of a feature go in its region (self.cur), so a stretch of sea is built whole;
        loose items go in the region of their column."""
        reg = self.cur if self.cur is not None else self.L.region(
            int(pos[0] // S) if i is None else i)
        self.items.append((part, color, transform(pos, R) if M is None else M, cat, reg, low))

    def take(self, cells):
        cells = set(cells)
        if not cells <= self.free:
            raise ValueError(f"cells taken twice: {sorted(cells - self.free)[:6]}")
        self.free -= cells


# ------------------------------------------------------------------ swells
# The swells' crests run across the sea (along Z) and march along it toward the bow (-X): the
# steep fronts face -X, the backs +X. A swell's profile either side of its crest: tiers of curved
# slopes from the crest outward, (columns, rise); each tier stands on a step as high as the
# tiers outside it (bricks, then plates), the crest on a stack as high as the swell.
_T16, _T24 = (2, 16), (3, 24)
PROFILES = {16: (_T16,), 24: (_T24,), 48: (_T24,) * 2, 72: (_T24,) * 3, 96: (_T24,) * 4,
            120: (_T24,) * 5, 144: (_T24,) * 6, 168: (_T24,) * 7}
HEIGHTS = (16, 24, 48, 72)
FRONT_COLS = ("Medium Azure", "Dark Azure", "Dark Azure")    # tiers from the crest outward
BACK_COLS = ("Blue", "Blue", "Blue", "Blue", "Dark Blue", "Dark Blue", "Dark Blue")
SWELL_SPACING = 430.0       # LDU between crests (posts sit in the troughs)
BOW_X = -900.0              # the breaking wave's zone: the oval's end beyond this
SLANT = 0.22                # the crests lean: x shifts this much per LDU of z


def _cols(h):
    return sum(t[0] for t in PROFILES[h])


def swell_lines(L: Layout) -> list:
    """Crest x positions (at z = 0) of the swells: half-way between the posts, then on at the
    same spacing, between the bow's breaking wave and the stern."""
    xs = sorted(x for x, _ in L.posts)
    lam = SWELL_SPACING
    if len(xs) >= 2:
        n = max(1, round((xs[-1] - xs[0]) / SWELL_SPACING))
        lam = (xs[-1] - xs[0]) / n
    out = []
    for j in range(-8, 9):
        x = xs[0] + lam * (j + 0.5)
        if BOW_X + 150 <= x <= XC + A_HALF - 140:
            out.append(x)
    return out


def plan_swells(P: Plan, keep_out: set):
    """Big rolling swells across the sea: in each row curved slopes rise in tiers from the
    trough to a crest with foam on top, and fall away behind; highest mid-sea, lower toward
    the rim and where a post cuts through."""
    L = P.L
    for m, x0 in enumerate(swell_lines(L)):
        scale = (1.0, 0.75, 1.0, 0.85, 1.0, 0.7, 0.9)[m % 7]
        rows = {}
        for k in sorted({k for _, k in L.cells}):
            z = S * k + 10
            xc = x0 + SLANT * z + 22 * math.sin(z / 85.0 + 1.7 * m) + 10 * math.sin(z / 31.0 + m)
            i = int(math.floor(xc / S))
            w = 1.0 - (abs(z) / (B_HALF * 0.95)) ** 2.2
            a = w * scale
            hmax = 72 if a > 0.62 else (48 if a > 0.38 else (24 if a > 0.18 else
                                                             (16 if a > 0.06 else 0)))
            h = hmax
            while h:
                nc = _cols(h)
                need = {(i + e, k) for e in range(-nc, nc + 1)}
                if need <= P.free - keep_out and {(i - nc - 1, k), (i + nc + 1, k)} <= L.cells:
                    break
                h = max([v for v in HEIGHTS if v < h], default=0)
            if h:
                rows[k] = (i, h)
        # no jumps of more than one size between neighbouring rows
        lv = {k: HEIGHTS.index(h) for k, (i, h) in rows.items()}
        for _ in range(3):
            for k in sorted(lv):
                nb = [lv.get(k - 1, -1), lv.get(k + 1, -1)]
                lv[k] = min(lv[k], max(0, min(nb) + 1) if min(nb) >= 0 else 0)
        for k, (i, h) in rows.items():
            _swell_cell(P, i, k, HEIGHTS[lv[k]], m)


def _swell_cell(P: Plan, i, k, h, m):
    z = S * k + 10
    tiers = PROFILES[h]
    nc = _cols(h)
    P.take({(i + e, k) for e in range(-nc, nc + 1)})
    P.cur = reg = P.L.region(i)
    P.crests[(i, k)] = (h, reg)
    P.stack[(i, k)] = (h, reg)
    P.wave_rows[(i, k)] = "crest"
    for side, cols in ((-1, FRONT_COLS), (1, BACK_COLS)):
        off = 0
        for j, (ncol, rise) in enumerate(tiers):
            step = sum(t[1] for t in tiers[j + 1:])
            cs = [i + side * e for e in range(off + 1, off + ncol + 1)]
            for c in cs:
                P.wave_rows[(c, k)] = "front" if side < 0 else "back"
                if step:
                    P.stack[(c, k)] = (step, reg)
            x = S * (min(cs) + max(cs) + 1) / 2
            part = "11477" if ncol == 2 else "50950"
            y = DECK_TOP - step - (24 if part == "50950" else 0)
            color = cols[min(j, len(cols) - 1)]
            if side < 0 and j == 0 and h >= 48 and _hash(i, k, 1) < 0.75:
                color = COL["foam"]                    # a whitecap: the crest spilling
            P.add(part, color, (x, y, z), rot(y=90) if side < 0 else rot(y=-90), cat="waves")
            off += ncol
    P.cur = None


# ------------------------------------------------------------------ the breaking wave
BREAKER_X = -1060.0         # its crest (x at z = 0): the oval's bow end


def plan_breaker(P: Plan):
    """A wave breaking at the bow end: its crest bows forward in the middle, where it stands
    up to seven bricks high and curls over toward the bow: a sheer face shading up from dark
    blue, stepping out under the lip on inverted 45-degree slopes; the lip's top rolled white
    with foam claws (white tooth plates) hanging off its front and white water (round bricks)
    falling from it, spray on the highest crests; lower toward the sides, where it runs out
    into ordinary swells. Long tiers of curved slopes behind."""
    L = P.L
    rows = sorted({k for _, k in L.cells})
    for k in rows:
        z = S * k + 10
        xc = BREAKER_X - 90 * max(0.0, 1 - (z / 220.0) ** 2) + 0.15 * z + 14 * math.sin(z / 29.0)
        c = int(math.floor(xc / S))
        az = abs(z)
        h = (168 if az < 45 else 144 if az < 85 else 120 if az < 120 else 96 if az < 150 else
             72 if az < 180 else 48 if az < 215 else 24 if az < 250 else 0)
        if not h:
            continue
        while h:
            nb = h // 24 * 3 if h >= 96 else _cols(h)
            nf = 3 if h >= 96 else _cols(h)
            need = {(c + e, k) for e in range(-nf, nb + 1)}
            # (the lip may reach out over the base's edge)
            if need <= P.free and (c + nb + 1, k) in L.cells and \
                    (h >= 96 or (c - nf - 1, k) in L.cells):
                break
            h = max([v for v in HEIGHTS + (96, 120, 144) if v < h], default=0)
        if not h:
            continue
        if h >= 96:
            _breaker_cell(P, c, k, h)
        else:
            _swell_cell(P, c, k, h, -1)


def _breaker_cell(P: Plan, c, k, h):
    z = S * k + 10
    n = h // 24
    P.take({(c + e, k) for e in range(-3, 3 * n + 1)})
    P.cur = reg = P.L.region(c)
    P.crests[(c, k)] = (h, reg)
    P.wave_rows[(c, k)] = "crest"
    # behind: n tiers of curved slopes on brick steps
    for j in range(n):
        cs = [c + e for e in range(3 * j + 1, 3 * j + 4)]
        step = h - 24 * (j + 1)
        for cc in cs:
            P.wave_rows[(cc, k)] = "back"
            if step:
                P.stack[(cc, k)] = (step, reg)
        P.add("50950", BACK_COLS[min(j, 6)], (S * (cs[0] + 1) + 10, DECK_TOP - step - 24, z),
              rot(y=-90), cat="waves")
    if h >= 144:                        # spray off the crest: a splash on an open stud
        P.spray.add((c, k))
    # the crest's stack and the face's (bricks); the face steps out under the lip on two
    # inverted 45-degree slopes, a brick beside the upper one's base; the lip's plates (white)
    P.stack[(c, k)] = (h - 24, reg)
    P.face[(c - 1, k)] = (h - 72, reg)
    P.lip_bricks.setdefault((reg, h), set()).add((c - 1, k))
    P.add("3665b", COL["mid"], (S * (c - 1) + 10, DECK_TOP - (h - 48), z), rot(y=90),
          cat="breaker")
    P.add("3665b", COL["light"], (S * (c - 2) + 10, DECK_TOP - (h - 24), z), rot(y=90),
          cat="breaker")
    for cc in range(c - 5, c + 1):
        P.lip.setdefault((reg, h, 0), set()).add((cc, k))
    for lv in (1, 2):
        for cc in (c - 1, c):
            P.lip.setdefault((reg, h, lv), set()).add((cc, k))
    # its rolled top: a white curved slope and a round plate of foam; at the front a white
    # tooth hanging off it as a claw, and a white round brick hanging under it: the lip falling
    P.add("11477", COL["foam"], (S * (c - 2), DECK_TOP - (h - 16), z), rot(y=90),
          cat="breaker")
    P.add("6141", COL["foam"] if _hash(c, k, 7) < 0.6 else COL["sparkle"],
          (S * (c - 4) + 10, DECK_TOP - (h - 8), z), cat="breaker")
    P.add("15070", COL["foam"], (S * (c - 5) + 10, DECK_TOP - (h - 8), z), rot(y=90),
          cat="breaker")
    P.add("3062b", COL["foam"], (S * (c - 5) + 10, DECK_TOP - (h - 24), z), cat="lip_hang")
    # the foot of the face in the trough under the lip, and the trough's tiles under its tip
    # (laid first: nothing could reach them from above once the lip is on)
    P.add("11477", COL["mid"], (S * (c - 2), DECK_TOP, z), rot(y=90), cat="waves")
    for cc in (c - 3, c - 2, c - 1):
        P.wave_rows[(cc, k)] = "front"
    for cc in (c - 5, c - 4):
        if (cc, k) in P.free:
            P.take({(cc, k)})
            P.add("3070b", COL["deep"], (S * cc + 10, CALM, z), cat="under_lip")
    P.cur = None


def plan_lip(P: Plan):
    """The breaker's white lip plates, its sheer face (bricks shading up from dark blue) and the
    bricks beside the slopes under its lip."""
    for (reg, h), cells in sorted(P.lip_bricks.items()):
        P.cur = reg
        for i0, i1, k0, k1 in pack(cells, [s for s in AV.sizes(BRICK, COL["light"])
                                           if s[0] == 1 and s[1] <= 4], prefer="z"):
            part, R = rect_part(BRICK, i1 - i0 + 1, k1 - k0 + 1)
            P.add(part, COL["light"], (S * (i0 + i1 + 1) / 2, DECK_TOP - (h - 24),
                                       S * (k0 + k1 + 1) / 2), R, cat="breaker", i=i0)
    for (reg, h, lv), cells in sorted(P.lip.items()):
        P.cur = reg
        y = DECK_TOP - (h - 24) - 8 * lv - 8
        # the lip's own plate runs along each row from the crest out to its tip; the two
        # above it cross the rows
        sizes = [s for s in _sizes(PLATE, COL["foam"], 8, 4) if lv or s[0] == 1]
        for i0, i1, k0, k1 in pack(cells, sizes, prefer="x" if lv == 0 else "z"):
            part, R = rect_part(PLATE, i1 - i0 + 1, k1 - k0 + 1)
            P.add(part, COL["foam"], (S * (i0 + i1 + 1) / 2, y, S * (k0 + k1 + 1) / 2), R,
                  cat="breaker", i=i0)
    for reg in sorted({r for _, r in P.face.values()}):
        P.cur = reg
        _face_bricks(P, {c: v for c, (v, r) in P.face.items() if r == reg})
    P.cur = None


def _face_bricks(P, face):
    below = None
    nb = max([v // 24 for v in face.values()], default=0)
    for b in range(nb):
        cells = {cc for cc, v in face.items() if v >= 24 * (b + 1)}
        color = FACE_COLS[min(b, len(FACE_COLS) - 1)]
        rects = pack(cells, [s for s in AV.sizes(BRICK, color) if s[0] == 1 and s[1] <= 4],
                     below, shift=b, prefer="z")
        for i0, i1, k0, k1 in rects:
            part, R = rect_part(BRICK, i1 - i0 + 1, k1 - k0 + 1)
            P.add(part, color, (S * (i0 + i1 + 1) / 2, DECK_TOP - 24 * (b + 1),
                                S * (k0 + k1 + 1) / 2), R, cat="breaker", i=i0)
        below = ids_of(rects)


# wider curved slopes that do the work of two or four side by side (part -> {width: part})
_WIDER = {"11477": {2: "15068", 4: "88930"}, "50950": {2: "24309"}}


def merge_slopes(P: Plan):
    """Curved slopes side by side along a crest (same place across, same height, colour and
    facing) become one wider slope where LEGO makes one in that colour."""
    groups, rest = {}, []
    for it in P.items:
        part, color, M, cat, reg, low = it
        if cat == "waves" and part in _WIDER:
            key = (part, color, round(M[0, 3]), round(M[1, 3]), tuple(np.round(M[:3, 0], 3)),
                   reg)
            groups.setdefault(key, []).append(it)
        else:
            rest.append(it)
    out = rest
    for (part, color, x, y, ex, reg), its in groups.items():
        its.sort(key=lambda it: it[2][2, 3])
        runs, cur = [], []
        for it in its:
            if cur and abs(it[2][2, 3] - cur[-1][2][2, 3] - S) > 0.5:
                runs.append(cur)
                cur = []
            cur.append(it)
        runs.append(cur)
        for run in runs:
            j = 0
            while j < len(run):
                for w in (4, 2):
                    wide = _WIDER[part].get(w)
                    if wide and j + w <= len(run) and AV.ok(wide, color):
                        M = run[j][2].copy()
                        M[2, 3] = (run[j][2][2, 3] + run[j + w - 1][2][2, 3]) / 2
                        out.append((wide, color, M, "waves", reg, None))
                        j += w
                        break
                else:
                    out.append(run[j])
                    j += 1
    P.items = out


# the water's colour by height in a swell (brick levels from the deck up)
LEVEL_COLS = ("Dark Blue", "Blue", "Blue", "Dark Azure", "Dark Azure", "Medium Azure",
              "Medium Azure", "Medium Azure")
FACE_COLS = ("Dark Blue", "Dark Azure", "Dark Azure", "Medium Azure", "Medium Azure",
             "Medium Azure")


def plan_stacks(P: Plan):
    """What the slopes and crests stand on: bricks for whole bricks of height, plates for the
    rest, packed level by level within each region; then foam on the crests."""
    for reg in range(N_REGIONS):
        mine = {c: h for c, (h, r) in P.stack.items() if r == reg}
        P.cur = reg
        below = None
        nb = max([h // 24 for h in mine.values()], default=0)
        for b in range(nb):
            cells = {c for c, h in mine.items() if h >= 24 * (b + 1)}
            color = LEVEL_COLS[min(b, len(LEVEL_COLS) - 1)]
            rects = pack(cells, [s for s in AV.sizes(BRICK, color) if s[1] <= 8], below,
                         shift=b * 3, prefer="z")
            for r in rects:
                i0, i1, k0, k1 = r
                part, R = rect_part(BRICK, i1 - i0 + 1, k1 - k0 + 1)
                P.add(part, color, (S * (i0 + i1 + 1) / 2, DECK_TOP - 24 * (b + 1),
                                    S * (k0 + k1 + 1) / 2), R, cat="crests", i=i0)
            below = ids_of(rects)
        top = {c: 24 * (h // 24) for c, h in mine.items()}
        lv = 0
        while True:
            cells = {c for c, h in mine.items() if h > top[c] + 8 * lv}
            if not cells:
                break
            # plates at different heights can't share a rectangle: pack each height apart
            by_y = {}
            for c in cells:
                by_y.setdefault(top[c] + 8 * lv, set()).add(c)
            for base_h, cs in by_y.items():
                color = LEVEL_COLS[min(base_h // 24, len(LEVEL_COLS) - 1)]
                rects = pack(cs, [s for s in _sizes(PLATE, color, 8, 4)], below,
                             shift=lv, prefer="z")
                for r in rects:
                    i0, i1, k0, k1 = r
                    part, R = rect_part(PLATE, i1 - i0 + 1, k1 - k0 + 1)
                    P.add(part, color, (S * (i0 + i1 + 1) / 2, DECK_TOP - base_h - 8,
                                        S * (k0 + k1 + 1) / 2), R, cat="crests", i=i0)
            lv += 1
    # foam: white round plates and tiles, a few clear ones catching the light
    sprayed = set()
    for (i, k), (h, reg) in sorted(P.crests.items()):
        P.cur = reg
        r = _hash(i, k, 2)
        top = DECK_TOP - h
        x, z = S * i + 10, S * k + 10
        if ((i, k) in P.spray or (h >= 72 and r > 0.9)) and not any(
                (i + a, k + b) in sprayed for a in (-1, 0, 1) for b in (-1, 0, 1)):
            sprayed.add((i, k))
            P.add("85861", COL["foam"], (x, top - 8, z), cat="foam")
            P.add("6126b", COL["glint"], (x, top - 14, z),
                  rot(y=360 * _hash(i, k, 8)) @ rot(x=90), cat="spray")
        elif r < 0.5:
            P.add("6141", COL["foam"], (x, top - 8, z), cat="foam")
        elif r < 0.75:
            P.add("98138", COL["foam"], (x, top - 8, z), cat="foam")
        elif r < 0.87:
            P.add("6141", COL["sparkle"], (x, top - 8, z), cat="foam")
        else:
            P.add("25269", COL["foam"], (x, top - 8, z), rot(y=90 * int(r * 40 % 4)),
                  cat="foam")
    P.cur = None


def plan_posts(P: Plan):
    """A ring of foam round each post: four white 4 x 4 macaroni tiles, quarter tiles in the
    square's corners."""
    for n, (px, pz) in enumerate(P.L.posts):
        P.cur = P.L.region(int(px // S))
        P.take(P.L.post_splash[n] - P.L.post_sq[n])
        for j in range(4):
            P.add("27507", COL["foam"], (px, CALM, pz), rot(y=90 * j), cat="rings")
        for sx in (-1, 1):
            for sz in (-1, 1):
                # the square's corner cell is clear of the ring: a square tile; the two
                # beside it get quarter tiles, rounded toward the ring
                P.add("3070b", COL["light"], (px + sx * 70, CALM, pz + sz * 70), cat="rings")
                for dx, dz in ((50, 70), (70, 50)):
                    P.add("25269", COL["light"], (px + sx * dx, CALM, pz + sz * dz),
                          rot(y=_QUARTER_ANGLE[(-sx, -sz)]), cat="rings")
    P.cur = None


_QUARTER_ANGLE = {}


def _quarter_setup():
    """Find the turn of a 1 x 1 quarter tile (25269) whose round edge faces each diagonal."""
    from naut_kit import ENG
    m = ENG.geom.mesh("25269.dat")
    v = m.tris.reshape(-1, 3)
    top = v[v[:, 1] < 0.5]
    # the square corner is the one the top face reaches; the round corner is cut away
    corners = {(sx, sz): float(np.max(sx * top[:, 0] + sz * top[:, 2]))
               for sx in (-1, 1) for sz in (-1, 1)}
    cut = min(corners, key=corners.get)           # the rounded corner's direction (local)
    for sx in (-1, 1):
        for sz in (-1, 1):
            for ang in (0, 90, 180, 270):
                R = rot(y=ang)
                d = R @ np.array([cut[0], 0, cut[1]], float)
                if round(d[0]) == sx and round(d[2]) == sz:
                    _QUARTER_ANGLE[(sx, sz)] = ang


_quarter_setup()


def plan_wakes(P: Plan):
    """Wakes trailing aft of each post: two lines of foam opening out behind it."""
    for n, (px, pz) in enumerate(P.L.posts):
        for side in (-1, 1):
            for t in range(0, 15):
                x = px + 90 + 20 * t
                z = pz + side * (70 + 7.5 * t)
                i, k = int(x // S), int(z // S)
                if (i, k) not in P.free or P.wave_rows.get((i, k)):
                    continue
                if _hash(i, k, 3) > 1.0 - t / 17.0:
                    continue
                r = _hash(i, k, 4)
                part = "98138" if r < 0.4 else ("25269" if r < 0.8 else "3070b")
                R = rot(y=_QUARTER_ANGLE[(1, side)]) if part == "25269" else None
                P.take({(i, k)})
                P.add(part, COL["foam"] if r < 0.9 else COL["sparkle"], (x - x % S + 10,
                      CALM, z - z % S + 10), R, cat="wakes")


def plan_nameplate(P: Plan, x_mid=-60):
    """A blank black nameplate (two 2 x 6 tiles) in a brass frame at the front."""
    i_mid = int(x_mid // S)
    i0, i1 = i_mid - 7, i_mid + 6                     # 14 columns
    k0 = max(P.L.front_row(i) for i in range(i0, i1 + 1)) + 1
    cells = {(i, k) for i in range(i0, i1 + 1) for k in range(k0, k0 + 4)}
    P.take(cells)
    P.cur = P.L.region(i_mid)
    for j in range(2):                                 # the field
        P.add("69729", COL["nameplate"], (S * (i0 + 1 + 6 * j) + 60, CALM, S * (k0 + 1) + 20),
              cat="nameplate")
    for kk in (k0, k0 + 3):                            # top and bottom of the frame
        for j in range(6):
            P.add("3069b", COL["brass"], (S * (i0 + 1 + 2 * j) + 20, CALM, S * kk + 10),
                  cat="nameplate")
    for ii in (i0, i1):                                # the sides
        P.add("3069b", COL["brass"], (S * ii + 10, CALM, S * (k0 + 1) + 20), rot(y=90),
              cat="nameplate")
    for ii, sx in ((i0, -1), (i1, 1)):                 # rounded corners
        for kk, sz in ((k0, -1), (k0 + 3, 1)):
            P.add("25269", COL["brass"], (S * ii + 10, CALM, S * kk + 10),
                  rot(y=_QUARTER_ANGLE[(sx, sz)]), cat="nameplate")
    P.cur = None
    return cells


def plan_calm(P: Plan):
    """The calm water between the swells: blue tiles laid along the swells, dark blue in the
    trough in front of each swell, dark azure in its lee, short glints of medium azure, a few
    white flecks of foam and clear bubbles; turquoise shallows and foam round the reef."""
    L = P.L
    # a red crab scuttling on the foam by the reef, on a white round plate
    spots = [(i, k) for i, k in sorted(P.free) if 1.0 < _reef_d(S * i + 10, S * k + 10) < 1.9
             and all((i + a, k + b) in P.free for a in range(-2, 3) for b in range(-2, 3))]
    if spots:
        i, k = min(spots, key=lambda c: (c[1], -c[0]))
        P.take({(i, k)})
        P.add("6141", COL["foam"], (S * i + 10, CALM, S * k + 10), cat="crab")
        P.add("6141", COL["foam"], (S * i + 10, CALM - 8, S * k + 10), cat="crab")
        P.add("33121", "Red", (S * i + 10, CALM - 8 - 16, S * k + 10), rot(y=200), cat="crab")
    tones = {}
    for i, k in P.free:
        x, z = S * i + 10, S * k + 10
        trough = any(P.wave_rows.get((i + d, k)) == "front" for d in (1, 2))
        lee = any(P.wave_rows.get((i - d, k)) == "back" for d in (1, 2))
        r = _hash(i, k, 5)
        rd = _reef_d(x, z)
        if rd < 1.18:                           # foam where the sea breaks on the reef
            tone = "fleck" if r < 0.55 else "shallow"
        elif rd < 1.75:                         # shallow water round the reef
            tone = "shallow" if r < 0.8 - 0.5 * (rd - 1.18) else (
                "light" if r < 0.93 else "fleck")
        elif r < 0.015:
            tone = "bubble"
        elif r < (0.06 if lee else 0.022):
            tone = "fleck"
        elif trough:
            tone = "deep"                       # dark in front of a swell's foot
        elif lee:
            tone = "mid"                        # lighter in its lee
        elif _hash(i, (k + 40) // 3, 9) < 0.07:
            tone = "light"                      # a short glint along the swells
        else:
            tone = "sea"
        tones.setdefault(tone, set()).add((i, k))
    for tone, cs in tones.items():
        if tone in ("bubble", "fleck"):
            for i, k in cs:
                r = _hash(i, k, 6)
                part = "98138" if tone == "bubble" or r < 0.6 else "25269"
                P.add(part, COL["sparkle"] if tone == "bubble" else COL["foam"],
                      (S * i + 10, CALM, S * k + 10),
                      rot(y=90 * int(r * 40 % 4)) if part == "25269" else None, cat="calm")
            continue
        color = COL[tone]
        tsz = [s for s in AV.sizes(TILE, color) if s[0] == 1]
        # pack each region apart, so no tile crosses from one region to the next
        for reg in range(N_REGIONS):
            sub = {(i, k) for i, k in cs if L.region(i) == reg}
            if not sub:
                continue
            for i0, i1, k0, k1 in pack(sub, tsz, prefer="z"):
                part, R = rect_part(TILE, i1 - i0 + 1, k1 - k0 + 1)
                P.add(part, color, (S * (i0 + i1 + 1) / 2, CALM, S * (k0 + k1 + 1) / 2), R,
                      cat="calm", i=i0)
    P.free = set()


# ------------------------------------------------------------------ the reef
REEF = (880.0, 165.0, 165.0, 105.0)     # centre x, z and radii of the reef by the stern
ROCK_COLS = ("Dark Bluish Gray", "Dark Bluish Gray", "Dark Tan", "Dark Bluish Gray",
             "Dark Bluish Gray", "Dark Tan", "Dark Bluish Gray", "Dark Bluish Gray",
             "Dark Bluish Gray", "Dark Tan", "Dark Bluish Gray", "Dark Bluish Gray")


def _reef_d(x, z):
    cx, cz, rx, rz = REEF
    return max(0.0, math.hypot((x - cx) / rx, (z - cz) / rz) + 0.16 * _noise(x, z, 3.1))


def plan_reef(P: Plan):
    """A reef by the stern: a mound of dark grey rock banded with dark tan, cheese slopes on
    its edges, rocky plates on top, kelp, coral (round bricks topped with flowers, leafy
    anemones), a red crab; foam where the sea breaks on it, shallow turquoise water round it."""
    hp = {}
    for i, k in sorted(P.free):
        x, z = S * i + 10, S * k + 10
        d = _reef_d(x, z)
        if d < 1.0:
            v = int(round((1 - d ** 1.4) * 12 + 1.2 * _noise(x, z, 5.3)))
            if v >= 1 and (i, k) not in P.L.ring:
                hp[(i, k)] = min(v, 12)
    if not hp:
        return set()
    P.take(hp)
    P.cur = P.L.region(int(REEF[0] // S))
    # the top of each cell: a cheese slope down toward its lowest neighbour if it drops two
    # plates or more, else flat (a tile, a plant, or bare studs for coral)
    tops, stack = {}, {}
    dirs = {(0, -1): 0, (-1, 0): 90, (0, 1): 180, (1, 0): 270}
    for (i, k), v in hp.items():
        drops = {d: v - hp.get((i + d[0], k + d[1]), 0) for d in dirs}
        d, drop = max(drops.items(), key=lambda t: t[1])
        if drop >= 2 and v >= 2:
            tops[(i, k)] = ("slope", dirs[d])
            stack[(i, k)] = v - 2
        else:
            tops[(i, k)] = ("flat", 0)
            stack[(i, k)] = v
    # the rock: plates in bands, packed level by level
    below = None
    lv = 0
    while True:
        cells = {c for c, v in stack.items() if v > lv}
        if not cells:
            break
        color = ROCK_COLS[lv % len(ROCK_COLS)]
        rects = pack(cells, [s for s in _sizes(PLATE, color, 6, 4)], below, shift=lv * 3,
                     prefer="x" if lv % 2 else "z")
        for i0, i1, k0, k1 in rects:
            part, R = rect_part(PLATE, i1 - i0 + 1, k1 - k0 + 1)
            P.add(part, color, (S * (i0 + i1 + 1) / 2, DECK_TOP - 8 * (lv + 1),
                                S * (k0 + k1 + 1) / 2), R, cat="reef", i=i0)
        below = ids_of(rects)
        lv += 1
    # tops
    plants = set()
    for (i, k), (kind, ang) in sorted(tops.items()):
        x, z = S * i + 10, S * k + 10
        y = DECK_TOP - 8 * stack[(i, k)]
        color = ROCK_COLS[(stack[(i, k)]) % len(ROCK_COLS)]
        if kind == "slope":
            P.add("54200", color, (x, y, z), rot(y=ang), cat="reef")
            continue
        r = _hash(i, k, 11)
        v = hp[(i, k)]
        peak = all(hp.get((i + a, k + b), 0) <= v for a, b in dirs)
        near = any(abs(i - a) <= 3 and abs(k - b) <= 3 for a, b in plants)
        if peak and v >= 5 and not near:   # kelp on an open-stud round plate
            P.add("85861", "Dark Green", (x, y - 8, z), cat="reef")
            P.add("30093", "Dark Green", (x, y - 12, z), rot(y=90 * int(r * 97 % 4)),
                  cat="plants")
            plants.add((i, k))
        elif r < 0.32:                     # a tube coral: round bricks, a flower on top
            n = 1 + int(r * 13) % 2
            col = ("Magenta", "Dark Turquoise")[int(r * 31) % 2]
            for j in range(n):
                P.add("3062b", col, (x, y - 24 * (j + 1), z), cat="plants")
            P.add("24866", ("Coral", "Dark Pink", "Bright Pink")[int(r * 57) % 3],
                  (x, y - 24 * n - 8, z), cat="plants")
        elif r < 0.44 and all(hp.get((i + a, k + b), 0) < v for a in (-1, 0, 1)
                              for b in (-1, 0, 1) if a or b) and not near:   # an anemone
            P.add("32607", ("Coral", "Magenta", "Dark Turquoise")[int(r * 71) % 3],
                  (x, y - 8, z), rot(y=90 * int(r * 89 % 4)), cat="plants")
        elif r < 0.58:
            P.add("24866", ("Coral", "Dark Pink", "Bright Pink", "Magenta")[int(r * 43) % 4],
                  (x, y - 8, z), cat="plants")
        else:
            P.add("3070b", color, (x, y - 8, z), cat="reef")
    P.cur = None
    return set(hp)


# ------------------------------------------------------------------ the tentacle
# The giant squid, breaking the surface at the front right: a long tentacle curling up out of a
# boil of foam (a tail section on the pin of a white round plate, a curled end in its tip), a
# thick one beside it, and two tips just showing.
TENT_A = (640, -220)            # the long one: boil centre (x, z on grid lines)
TENT_A_TURN, TENT_A_SPIN = 90.0, 0.0      # arching over toward the bow
TENT_B = (540, -180)            # the thick one
TENT_B_TURN = 0.0               # reaching up toward the hull (2 x 2 base: quarter turns only)
TENT_TIPS = ((710, -150, 30), (590, -270, -120))   # (x, z, turn): cell centres


def tentacle_cells(dx=0):
    cells = set()
    for x, z in (TENT_A, TENT_B):
        cells |= _square(int((x + dx) // S), int(z // S), 2)
    for x, z, _ in TENT_TIPS:
        cells.add((int((x + dx) // S), int(z // S)))
    return cells


def tentacle_shift(L: Layout) -> int:
    """How far (x) to move the squid's tentacles so they clear the posts' rings of foam."""
    near = set()
    for n in L.post_splash:
        near |= {(i + a, k + b) for i, k in L.post_splash[n] for a in range(-3, 4)
                 for b in range(-3, 4)}
    for dx in sorted(range(-600, 601, 40), key=abs):
        cells = tentacle_cells(dx)
        if cells <= L.cells - L.ring and not cells & near:
            return dx
    raise ValueError("no room for the tentacles clear of the posts")


def plan_tentacles(P: Plan, dx=0):
    P.take(tentacle_cells(dx))
    P.cur = P.L.region(int((TENT_A[0] + dx) // S))
    x, z = TENT_A[0] + dx, TENT_A[1]
    P.add("11833", COL["deep"], (x, DECK_TOP - 8, z), cat="boil")
    P.add("60474", COL["foam"], (x, DECK_TOP - 16, z), cat="boil")
    top = DECK_TOP - 16                    # (the pin reaches down into the boil)
    M2 = transform((x, DECK_TOP - 20, z), rot(y=TENT_A_TURN) @ rot(x=90))
    P.add("40378", COL["tentacle"], None, M=M2, cat="tentacle", low=top)
    M3 = _attach("40379", 0, "40378", 1, M2, TENT_A_SPIN)
    P.add("40379", COL["tentacle"], None, M=M3, cat="tentacle", low=top)
    x, z = TENT_B[0] + dx, TENT_B[1]
    P.add("60474", COL["foam"], (x, DECK_TOP - 8, z), cat="boil")
    P.add("3022", COL["foam"], (x, DECK_TOP - 16, z), cat="boil")
    P.add("3941", COL["tentacle"], (x, DECK_TOP - 40, z), cat="tentacle")
    P.add("67361", COL["tentacle"], (x, DECK_TOP - 40, z), rot(y=TENT_B_TURN), cat="tentacle")
    for x, z, turn in TENT_TIPS:
        x += dx
        P.add("85861", COL["foam"], (x, CALM, z), cat="boil")
        P.add("13564", COL["tentacle"], (x, CALM - _TIP_DY, z), rot(y=turn) @ rot(z=90),
              cat="tentacle")
    P.cur = None


_TIP_DY = 4.0


def _attach(child, ci, parent, pi, Mp, spin=0.0, back=0.0, flip=False):
    """World matrix putting `child`'s connector ci on `parent`'s connector pi (at Mp): same
    origin, same axis (opposite with `flip`: the snaps' axes don't all point the same way),
    turned `spin` degrees about it; `back` LDU pulled back along the child's own axis."""
    from naut_kit import connectors
    cp = connectors(parent, Mp)[pi]
    cc = connectors(child)[ci]
    a_p = np.asarray(cp.axis, float) * (-1 if flip else 1)
    a_c = np.asarray(cc.axis, float)
    R = _rot_between(a_c, a_p)
    Rs = _axis_angle(a_p, math.radians(spin))
    R = Rs @ R
    M = np.eye(4)
    M[:3, :3] = R
    M[:3, 3] = np.asarray(cp.origin, float) - R @ np.asarray(cc.origin, float) - back * a_p
    return M


def _rot_between(a, b):
    a, b = a / np.linalg.norm(a), b / np.linalg.norm(b)
    v = np.cross(a, b)
    c = float(np.dot(a, b))
    if np.linalg.norm(v) < 1e-9:
        if c > 0:
            return np.eye(3)
        p = np.array([1.0, 0, 0]) if abs(a[0]) < 0.9 else np.array([0, 1.0, 0])
        v = np.cross(a, p)
        return _axis_angle(v / np.linalg.norm(v), math.pi)
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx * (1 / (1 + c))


def _axis_angle(axis, ang):
    axis = np.asarray(axis, float) / np.linalg.norm(axis)
    K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + math.sin(ang) * K + (1 - math.cos(ang)) * K @ K


# ------------------------------------------------------------------ posts
def post(model, n, height, cap_side_studs=True):
    """A clear tube: ring plates (4 x 4 with a 2 x 2 round opening) stacked `height` LDU. On
    the top one, the studs either side of a keel fin two studs thick (z +-30) get clear round
    tiles; the fin plugs onto the four along it (x +-30, z +-10)."""
    sub = model.submodel(f"stand_post_{n + 1}", f"Post {n + 1}")
    k = int(height // 8)
    for j in range(k):
        if j % 8 == 0:
            sub.step("A clear post: ring plates stacked into a tube" if j == 0 else "")
        sub.place("11833", COL["post"], (0, -8 * j, 0))
    if cap_side_studs:
        sub.step("Clear round tiles on the studs beside the keel fin")
        for x in (-10, 10):
            for z in (-30, 30):
                sub.place("98138", COL["post"], (x, -8 * k, z))
    return sub


# ------------------------------------------------------------------ the whole stand
SURFACE_PHASES = [["rings", "nameplate", "under_lip", "boil"], ["reef"],
                  ["waves", "crests", "breaker"], ["lip_hang"], ["foam"], ["wakes"], ["calm"],
                  ["plants", "crab", "tentacle", "spray"]]
SURFACE_CAPTIONS = {
    "rings": "Rings of foam where the posts will meet the water",
    "nameplate": "A black nameplate in a brass frame (for a sticker)",
    "waves": "Swells: a curved slope up to the crest, another falling away behind",
    "crests": "Crests of plates",
    "reef": "A reef of rock by the stern, kelp and coral on it, a crab",
    "tentacle": "The giant squid's tentacles breaking the surface",
    "boil": "Boils of foam where the giant squid will break the surface",
    "under_lip": "The trough under the breaking wave's lip",
    "plants": "Kelp and coral on the reef",
    "crab": "A crab on the foam",
    "spray": "Spray flying off the crests",
    "breaker": "The breaking wave: its face, the curl of its lip, foam claws hanging off it",
    "lip_hang": "White water falling from the lip: round bricks pushed up under it",
    "foam": "Foam on the crests",
    "wakes": "Wakes behind the posts",
    "calm": "The calm water: tiles in four blues",
}


def surface_plan(L: Layout) -> Plan:
    P = Plan(L)
    plan_posts(P)
    keep = set()
    plate = plan_nameplate(P)
    keep |= {(i, k + d) for i, k in plate for d in range(1, 5)}
    dx = tentacle_shift(L)
    plan_tentacles(P, dx)
    keep |= {(i + a, k + b) for i, k in tentacle_cells(dx) for a in (-2, -1, 0, 1, 2)
             for b in (-2, -1, 0, 1, 2)}
    for n in L.post_splash:
        keep |= {(i + a, k + b) for i, k in L.post_splash[n] for a in (-1, 0, 1)
                 for b in (-1, 0, 1)}
    reef = plan_reef(P)
    keep |= {(i + a, k + b) for i, k in reef for a in (-2, -1, 0, 1, 2) for b in (-1, 0, 1)}
    plan_breaker(P)
    keep |= {(i, k) for i, k in L.cells if S * i + 10 < BOW_X}
    plan_swells(P, keep)
    merge_slopes(P)
    plan_stacks(P)
    plan_lip(P)
    plan_wakes(P)
    plan_calm(P)
    return P


def build_stand(model, posts=DEFAULT_POSTS, hull_y=None, parent=None, lead_post=0,
                cap_side_studs=None):
    """Build the stand into `parent` (default model.main) as a sub-assembly tagged "stand".

    `posts`: (x, z, y_top) of the hull's underside where each post holds it (a keel fin, the
    keel strip), in the HULL frame (x, z are snapped to the stud grid: a post's centre is on
    a grid line; the hull plugs onto its top ring plate's studs at x +-30, z +-10 from it,
    and at x +-10, z +-30 where it is wider than two studs). `hull_y`: where the hull's frame
    sits in the world (default: the lowest contact GAP above the calm sea, on the plate
    grid); each post is as many ring plates as reach its contact. `lead_post`: which post the
    lead runs down. `cap_side_studs`: per post (or one for all): clear round tiles on the top
    plate's studs at z +-30, beside a fin two studs thick; default: capped where the post
    meets a fin (y_top below the belly), bare under the keel strip. Returns a StandInfo."""
    pw = [(S * round(x / S), S * round(z / S)) for x, z, _ in posts]
    if cap_side_studs is None:
        cap_side_studs = [yt > BELLY for _, _, yt in posts]
    elif isinstance(cap_side_studs, bool):
        cap_side_studs = [cap_side_studs] * len(posts)
    if hull_y is None:
        hull_y = CALM - GAP - max(y for _, _, y in posts)
        hull_y = 8 * math.floor(hull_y / 8)
    tops = []
    for (x, z), (_, _, yt) in zip(pw, posts):
        y = hull_y + yt
        h = WALL_TOP - y                       # the tube stands on its pillar (y = -80)
        if h % 8 or h < 64:
            raise ValueError(f"post at x={x}: fin underside y={y} is not a whole number of "
                             f"plates above the pillar ({h} LDU)")
        tops.append((x, y, z))
    L = Layout(pw)
    parent = parent or model.main
    st = model.submodel("stand", "Display stand")
    st.use(base(model, L))
    P = surface_plan(L)
    for reg in range(N_REGIONS):
        bt = Batch()
        for part, color, M, cat, r, low in P.items:
            if r == reg:
                bt.add(part, color, M, cat, insert=(0, 1, 0) if cat == "lip_hang" else None,
                       low=low)
        st.step(f"The sea, stretch {reg + 1} of {N_REGIONS}")
        bt.emit(st, phases=SURFACE_PHASES, captions=SURFACE_CAPTIONS, per_step=10, reach=160,
                hanging=("lip_hang",))
    for n, ((x, z), (_, y, _)) in enumerate(zip(pw, tops)):
        st.step("The posts: lower each through its ring of foam onto its pillar")
        st.use(post(model, n, WALL_TOP - y, cap_side_studs[n]), (x, WALL_TOP - 8, z),
               insert=(0, -1, 0), tag=f"post_{n + 1}")
    parent.step("The display stand")
    parent.use(st, tag="stand")
    model.press_fit("battery", "the battery box lies in its bay, held by the deck over it and "
                    "the wall beside it")
    # the lead: down the post's tube and its pillar's shaft, out of the doorway at its foot
    # (+Z side), across the floor to the gap beside the battery box's plug end, along it to
    # the porch in front of the box's top, into the plug
    px, pz = pw[lead_post]
    bx, by, bz = L.box
    route = [(px, tops[lead_post][1], pz), (px, -12, pz), (px - 10, -12, pz + 30),
             (px - 10, -12, pz + 60), (bx + 90, -12, bz - 110), (bx + 90, -12, bz + 10),
             (bx + 48, by, bz + 10)]
    length = sum(float(np.linalg.norm(np.subtract(a, b))) for a, b in zip(route, route[1:]))
    return StandInfo(hull_y=hull_y, post_tops=tops, lead_post=lead_post,
                     lead_exit=tops[lead_post], lead_route=route, lead_length=length,
                     post_plates=[int((WALL_TOP - y) // 8) for _, y, _ in tops],
                     battery=(bx, by, bz))
