"""The display stand: a low block of sea with rolling waves on top, hollow inside for the
battery box, and two clear round posts holding the Nautilus by its keel fins.

World frame (the main model): the table is y = 0, -Y up, the hull runs along X (bow -X), the
front of the stand faces -Z. Stud cells as the hull's: column i is x in [20 i, 20 i + 20], row
k is z in [20 k, 20 k + 20]."""
from __future__ import annotations

import math
from collections import defaultdict

from brickkit.ldraw.matrix import rot, transform
from naut_kit import AV, BRICK, PLATE, S, TILE, Batch, ids_of, pack, rect_part

I0, I1 = -22, 21                  # columns (x -440..440: 44 studs, 35 cm)
K0, K1 = -7, 6                    # rows (z -140..140: 14 studs, 11 cm)
FLOOR = -16                       # top of the floor (two crossed layers of plates)
WALL_TOP = FLOOR - 72             # walls: three bricks
DECK_TOP = WALL_TOP - 16          # two layers of plates over the walls: the sea's top
SEA_TOP = DECK_TOP - 8            # the calm sea's tiles
POST_BRICKS = 4                   # each post: round 2 x 2 bricks
POSTS = (-4, 7)                   # the posts' first columns (front, rear); rows -1, 0
BOX_X, BOX_Z = 0, 96              # the battery box, on its back on the table, its button and
                                  # plug toward the back wall (a finger's width between)
BOX_CELLS = {(i, k) for i in range(-4, 4) for k in range(0, 5)}   # its hole in the floor
BUTTON_COL = 2                    # the slot in the back wall in front of its button
CABLE_HOLE = {(-2, -1), (-2, 0)}  # where the leads go down into the sea, by the front post
PLATE_CELLS = {(i, k) for i in range(-22, -16) for k in (-7, -6)}  # nameplate (front left)


def post_top() -> float:
    """World y of the posts' tops (the keel fins' undersides)."""
    return DECK_TOP - 24 * POST_BRICKS


def _block(bt, table, cat, cells_, top, role, sizes, below=None, shift=0, prefer="x"):
    rects = pack(cells_, sizes, below, shift=shift, prefer=prefer)
    for i0, i1, k0, k1 in rects:
        part, R = rect_part(table, i1 - i0 + 1, k1 - k0 + 1)
        bt.add(part, role, transform((S * (i0 + i1 + 1) / 2, top, S * (k0 + k1 + 1) / 2), R),
               cat)
    return rects


def post_cells():
    return {(i, k) for a in POSTS for i in (a, a + 1) for k in (-1, 0)}


def all_cells():
    return {(i, k) for i in range(I0, I1 + 1) for k in range(K0, K1 + 1)}


def base(model):
    """The hollow sea block: a floor of plates (open under the battery box, which stands on
    the table), walls three bricks tall with a slot at the box's button, the box."""
    sub = model.submodel("sea_base", "Sea base")
    bt = Batch()
    floor = all_cells() - BOX_CELLS
    psz = [s for s in AV.sizes(PLATE, "sea_floor") if s[1] <= 12]
    f1 = _block(bt, PLATE, "floor", floor, FLOOR + 8, "sea_floor", psz, prefer="z")
    _block(bt, PLATE, "floor", floor, FLOOR, "sea_floor", psz, ids_of(f1), shift=5)
    ring = {(i, k) for i, k in all_cells() if i in (I0, I1) or k in (K0, K1)}
    button = {(BUTTON_COL, K1)}
    below = {}
    y, n = FLOOR, 0
    while y > WALL_TOP:
        top = y - 24
        cs = ring - (button if top in (FLOOR - 24, FLOOR - 48) else set())
        role = "sea_wall" if n < 2 else "sea_wall_top"         # the sea lightens upward
        rects = pack(cs, [s for s in AV.sizes(BRICK, role) if s[0] == 1], below, shift=n * 3)
        for i0, i1, k0, k1 in rects:
            part, R = rect_part(BRICK, i1 - i0 + 1, k1 - k0 + 1)
            x, z = S * (i0 + i1 + 1) / 2, S * (k0 + k1 + 1) / 2
            bt.add(part, role, transform((x, top, z), R), "walls")
        below = ids_of(rects)
        y, n = top, n + 1
    # the battery box (Power Functions, AAA) on its back on the table, in the floor's opening:
    # its button and plug face the back wall, the button behind the slot
    bt.add("64228", "battery", transform((BOX_X, -40, BOX_Z), rot(x=-90)), "box",
           "battery", (0, 1, 0))
    bt.emit(sub, phases=[["floor"], ["walls"], ["box"]],
            captions={"floor": "The sea base: a floor of plates, open for the battery box",
                      "walls": "Walls round the edge; a slot in the back one for the box's "
                               "button",
                      "box": "The battery box on its back, its button toward the slot"},
            per_step=8, reach=240)
    return sub


def deck(model):
    """The sea's top: two crossed layers of plates with the waves and tiles on them, built
    flat and set on the walls (lift it off to change the batteries)."""
    sub = model.submodel("sea_top", "Sea top")
    bt = Batch()
    dsz = [s for s in AV.sizes(PLATE, "sea_deck") if s[1] <= 12]
    cells = all_cells() - CABLE_HOLE
    r1 = _block(bt, PLATE, "deck", cells, DECK_TOP + 8, "sea_deck", dsz, prefer="x")
    _block(bt, PLATE, "deck", cells, DECK_TOP, "sea_deck", dsz, ids_of(r1), shift=7,
           prefer="z")
    sea(bt)
    bt.emit(sub, phases=[["deck"], ["waves"], ["foam"], ["ripples"], ["flat"], ["plate"]],
            captions={"deck": "The sea's top: two crossed layers of plates",
                      "waves": "Waves: a curved front, a crest of plates, a slope behind",
                      "foam": "Foam on the crests",
                      "ripples": "Ripples round the posts",
                      "flat": "The calm sea between the waves: tiles in three blues",
                      "plate": "A blank nameplate for a sticker"},
            per_step=8, reach=240)
    return sub


# ------------------------------------------------------------------ the sea's surface
# wave crests: (first column, last column, crest row, height in LDU: 16 or 24); the fronts
# face the viewer (-Z), the backs fall away behind
WAVES = ((-15, -13, -4, 16), (-12, -6, -4, 24), (-4, 1, -4, 16), (3, 9, -4, 24),
         (11, 14, -4, 16), (16, 21, -4, 24),
         (-22, -16, 4, 24), (-14, -9, 4, 16), (-7, -2, 4, 24), (1, 6, 4, 16), (8, 14, 4, 24),
         (16, 21, 4, 16))
RIPPLES = ((-17, -1), (-9, 0), (1, -1), (4, 0), (12, -1), (17, 0), (-13, -1))


def _noise(i, k):
    return math.sin(0.55 * i + 0.9 * k) + 0.6 * math.sin(0.23 * i - 1.3 * k + 1.0)


def sea(bt):
    """The sea's surface: long rolling waves - a curved front rising to a crest, foam on the
    crest, a curved back falling away - with ripples and tiles in three blues between."""
    taken = post_cells() | CABLE_HOLE | PLATE_CELLS
    wave_cells = set()
    for i0, i1, kc, h in WAVES:
        nfront = 3 if h == 24 else 2
        zc = S * kc + 10                                  # the crest row's middle
        for i in range(i0, i1 + 1):
            x = S * i + S / 2
            if h == 24:     # the front: a 3 x 1 curved slope, 24 tall, over three rows
                bt.add("50950", "wave", transform((x, DECK_TOP - 24, zc - 40)), "waves")
            else:           # or a 2 x 1 curved slope, 16 tall, over two rows
                bt.add("11477", "wave", transform((x, DECK_TOP, zc - 30)), "waves")
            # the back: a curved slope falling away over two rows
            bt.add("11477", "wave_back", transform((x, DECK_TOP, zc + 30), rot(y=180)),
                   "waves")
            for k in range(kc - nfront, kc + 3):
                wave_cells.add((i, k))
        crest = {(i, kc) for i in range(i0, i1 + 1)}
        y = DECK_TOP - 8
        for lvl in range(h // 8):
            rows = pack(crest, [(1, n) for n in (1, 2, 3, 4, 6, 8)], shift=lvl * 2 + i0)
            for a, b, _, _ in rows:
                part, R = rect_part(PLATE, b - a + 1, 1)
                bt.add(part, "wave_crest", transform((S * (a + b + 1) / 2, y, zc), R),
                       "waves")
            y -= 8
        top = DECK_TOP - h
        for i in range(i0, i1 + 1):
            x = S * i + S / 2
            if _noise(i, kc) > -0.4:      # foam: white round plates along most of the crest
                bt.add("6141", "foam", transform((x, top - 8, zc)), "foam")
            else:
                bt.add("98138", "wave", transform((x, top - 8, zc)), "foam")
    # small ripples in the calm water round the posts
    for i, k in RIPPLES:
        if {(i, k), (i, k + 1)} & (taken | wave_cells):
            continue
        bt.add("11477", "sea_glint", transform((S * i + S / 2, DECK_TOP, S * k + 20)),
               "ripples")
        wave_cells |= {(i, k), (i, k + 1)}
    # the calm sea: tiles in three blues, set by a ripple pattern
    flat = all_cells() - taken - wave_cells
    tones = defaultdict(set)
    for i, k in flat:
        v = _noise(i, k)
        tone = "sea_glint" if v > 1.0 else ("sea_light" if v > -0.1 else "sea_dark")
        tones[tone].add((i, k))
    for tone, cs in tones.items():
        tsz = [s for s in AV.sizes(TILE, tone) if s[0] == 1]
        _block(bt, TILE, "flat", cs, SEA_TOP, tone, tsz)
    # the nameplate: a blank black 2 x 6 tile at the front left (for a sticker)
    xs = sorted({i for i, _ in PLATE_CELLS})
    bt.add("69729", "nameplate", transform((S * (xs[0] + xs[-1] + 1) / 2, SEA_TOP,
                                            S * K0 + 20)), "plate", "nameplate")


def post(model, name):
    """A clear post: round 2 x 2 bricks stacked from the sea's top up to a keel fin."""
    sub = model.submodel(name, f"{'Front' if 'front' in name else 'Rear'} post")
    for n in range(POST_BRICKS):
        sub.step("A clear post: round 2 x 2 bricks" if n == 0 else "")
        sub.place("3941", "post", (0, DECK_TOP - 24 * (n + 1), 0))
    return sub


def stand(model):
    """The whole stand: base, sea, posts."""
    st = model.submodel("stand", "Display stand")
    st.use(base(model))
    st.step("Set the sea's top on the base")
    st.use(deck(model), insert=(0, -1, 0))
    for a, name in zip(POSTS, ("post_front", "post_rear")):
        st.step()
        st.use(post(model, name), (S * (a + 1), 0, 0), insert=(0, -1, 0))
    return st
