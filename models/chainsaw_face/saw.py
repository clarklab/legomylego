"""The chainsaw: a 1970s saw 12.8 cm long (a real one is about 80 cm).

Engine frame E (y down): the engine body is x in [-40, 40], y in [-72, 0], z in [0, 140];
the guide bar runs forward (-z) along its left side (+x) to z = -180.
* engine: yellow bricks in a brick + 2 plate rhythm so bricks with studs on the side (22885)
  can carry the guide bar; grey clutch cover, cooling fins, black pull-start;
* guide bar: built flat and turned on edge: black plates (the chain's edge) under grey tiles,
  black grille tiles along the top edge (the chain), a rounded nose;
* handles: a bar across the front and one across the back, each held out from the engine's
  top by two clip plates. The right fist grips the front handle, the left fist the rear
  handle, 16 cm apart as on a real saw."""
from __future__ import annotations

from kit import BR, PL, Grid, Seg, box_cells, orient, panel_parts, rot, transform

FRONT_BAR = (0, -78, -10)        # front handle bar centre (E), along x
REAR_BAR = (0, -78, 150)         # rear handle bar centre (E), along x
# flat panel -> the engine's left face: panel x along -z, studs towards +x, panel z down
R_BAR_PANEL = orient((0, 0, -1), (-1, 0, 0), (0, 1, 0))
BAR_LEN = 13                     # guide bar panel length in studs (from z = 80 to -180)


def build_bar(model):
    """Guide bar, built flat: black plates, 13 studs long and 2 wide, under tiles: a grey
    cover over the engine end, then grey bar tiles with the chain (black grilles) along the
    top edge (row 0) and a rounded nose."""
    sub = model.submodel("guide_bar", "Guide bar")
    s = Seg(sub, Grid(0, 0))
    cells = box_cells(0, BAR_LEN - 1, 0, 1, "chain")
    tiles = {c: ("saw_dark" if c[0] < 4 else "saw_bar") for c in cells}
    specials = []
    for i in range(BAR_LEN - 2, 3, -2):            # the chain: grilles from the nose back
        x, z = s.g.centre(i, i + 1, 0, 0)
        specials.append(("2412b", "chain", transform((x, -2 * PL, z))))
        del tiles[(i, 0)], tiles[(i + 1, 0)]
    for c in [c for c in tiles if c[1] == 0 and c[0] >= 4]:
        tiles[c] = "chain"
    x, z = s.g.cell_xz(BAR_LEN - 1, 1)
    specials.append(("25269", "saw_bar", transform((x, -2 * PL, z), rot(y=90))))   # the nose
    del tiles[(BAR_LEN - 1, 1)]
    parts = panel_parts(s.g, cells, tiles, specials)
    s.step("The guide bar, built flat: black plates", view="above")
    for part, role, M in parts:
        if M[1, 3] == -PL:
            s.put_M(part, role, M)
    s.step("Tiles: a grey cover over the engine end, the bar, and the chain along its top "
           "edge")
    for part, role, M in parts:
        if M[1, 3] != -PL:
            s.put_M(part, role, M)
    return sub


def build_saw(model):
    bar = build_bar(model)
    sub = model.submodel("saw", "Chainsaw")
    s = Seg(sub, Grid(-40, 0))
    cells = box_cells(0, 3, 0, 6, "saw")
    left = {(3, k) for k in range(4)}
    s.step("Chainsaw engine: bricks with studs on the side will carry the guide bar",
           view="above")
    for z in (20, 60):
        s.put("22885", "saw", (30, -40, z), rot(y=-90))
    s.course("brick", {c: r for c, r in cells.items() if c not in left}, -BR, prefer="z",
             bond=False)
    s.below = {c: 0 for c in cells}
    s.step()
    s.course("plate", {c: r for c, r in cells.items() if c not in left}, -BR - PL,
             prefer="x")
    s.course("plate", {c: r for c, r in cells.items() if c not in left}, -BR - 2 * PL,
             prefer="z")
    s.below.update({c: -5 for c in left})
    s.step()
    s.course("brick", cells, -2 * BR - 2 * PL, prefer="x")
    s.course("plate", cells, -3 * BR, prefer="z")
    yt = -3 * BR
    s.step("The handles: clip plates hold bars out in front and behind")
    for x in (-30, 30):
        s.put("61252", "handle", (x, yt - PL, 10))
        s.put("61252", "handle", (x, yt - PL, 130), rot(y=180))
    s.put("30374", "handle", (40, FRONT_BAR[1], FRONT_BAR[2]), rot(z=90), tag="front_bar")
    s.put("30374", "handle", (40, REAR_BAR[1], REAR_BAR[2]), rot(z=90), tag="rear_bar")
    top = {c: r for c, r in cells.items()
           if c not in {(0, 0), (3, 0), (0, 6), (3, 6)}}
    s.step("Smooth the top")
    s.course("tile", top, yt - PL, prefer="z", bond=False)
    s.step("The guide bar along the left-hand side")
    M = transform((40, -40, 80), R_BAR_PANEL)
    s.sub.use(bar, M[:3, 3], M[:3, :3], insert=(1, 0, 0))
    return sub
