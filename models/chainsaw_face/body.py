"""Hips, apron skirt and torso.

Hips (pelvis frame: origin on the waist plane, on the turntable's axis; y down):
  a 10 x 6 stud block of jeans, 96 LDU deep. The bottom course holds the two hip sockets
  (67696, sockets facing out, balls at (+-60, 82, 0)); the back row has two Technic bricks
  (holes 58 and 82 down, along z) for the stand's support post; the front row is a column of
  bricks with studs on the side (22885) that carries the apron skirt. The waist is a locking
  4 x 4 turntable (61485 + 60474) sunk into the top, flush with a ring of tiles the torso
  slides over.

Torso (torso frame: origin on the waist plane, on the turntable's axis; y down, up is -y):
  an 8 x 6 stud white block in brick + 2 plate layers (so every 40 LDU is a common level),
  with a front column of 22885 bricks for the front panel (bib apron over the belly, shirt
  front, tie and apron straps above it), the shoulder axles and balls in the top course and
  a neck axle for the head's ball.

Panels (the skirt, the torso front) are built flat, studs up, and turned to face forward."""
from __future__ import annotations

from kit import BR, PL, S, Grid, Seg, box_cells, orient, panel_parts, rot, transform

R_PANEL = orient((1, 0, 0), (0, 0, 1), (0, -1, 0))   # flat panel -> studs facing -z

PELVIS_BALL = (60, 82, 0)
ROUND = {(-5, -3), (4, -3), (-5, 2), (4, 2)}     # torso corners: round 1 x 1 columns
POST_HOLES = (58, 82)            # pelvis y of the post's pin holes (z = 40..60 back row)
TORSO_W, TORSO_D = 5, 3          # half-size in studs (10 x 6, plus a 6-stud belly row)
SHOULDER = (114, -142, 0)        # left shoulder ball (torso frame); the axle runs along x
NECK = (0, -199, 0)              # neck ball (torso frame)
PANEL_TOP = -128                 # top of the belly row (torso frame); the bib: -108 .. -8
BIB_TOP = -108
SKIRT_TOP = 8                    # skirt panel: y = 8 .. 288 (pelvis frame)


# ------------------------------------------------------------------------------ hips
def build_pelvis(model):
    sub = model.submodel("pelvis", "Hips")
    s = Seg(sub, Grid(0, 0))
    W, D = 5, 3
    cells = box_cells(-W, W - 1, -D, D - 1, "jeans")
    front = {(i, -D - 1): "jeans" for i in range(-W, W)}          # the apron's row
    post = {(-1, 2), (0, 2)}
    notch = {(i, k) for i in (-4, -3, 2, 3) for k in (-1, 0)}     # room for the balls
    s.step("Hips, from the bottom up: the two hip sockets face outwards", view="above")
    bx, by, _ = PELVIS_BALL
    s.put("67696", "jeans", (bx - 40, by - 10, 0))
    s.put("67696", "jeans", (-(bx - 40), by - 10, 0), rot(y=180))
    s.put("3700", "base", (0, 72, 50))                        # post pin hole at 82
    p4 = {c: r for c, r in cells.items() if -2 <= c[0] <= 1 and c[1] not in (-1, 0)
          and c not in post}
    s.course("brick", {**p4, **front}, 72, prefer="x", bond=False)
    s.below = {c: 0 for c in cells}
    s.below.update({c: 0 for c in front})
    s.step("The second post hole, a course of bricks (room above the balls) and a plate "
           "layer to tie them together")
    s.put("3700", "base", (0, 48, 50))                        # post pin hole at 58
    s.course("brick", {**{c: r for c, r in cells.items() if c not in notch | post}, **front},
             48, prefer="z")
    s.below.update({c: -7 for c in post})
    s.course("plate", cells, 40, prefer="x", max_len=10)
    s.step("The front row: bricks with studs on the side hold the apron")
    for i in range(-W, W, 2):
        s.put("22885", "apron", (S * i + 20, 8, -70))
    s.course("brick", cells, 16, prefer="z")
    s.step("The waist: a locking turntable base in the middle")
    s.put("61485", "Black", (0, 8, 0))
    ring = {c: r for c, r in cells.items() if not (-2 <= c[0] <= 1 and -2 <= c[1] <= 1)}
    s.course("plate", ring, 8, prefer="x", max_len=10)
    s.step("Smooth tiles round it, so the torso can turn over them")
    s.course("tile", {**ring, **{c: "apron" for c in front}}, 0, prefer="x", bond=False)
    return sub


# ------------------------------------------------------------------------------ panels
def flat_panel(s: Seg, cells_role: dict, tiles_role: dict, plate_prefer="x"):
    """Plates (studs up, top at -8) under tiles (top at -16), laid out so the tiles bridge
    every plate (the panel holds together on its own). Tile roles "@part:role:deg" are
    single special tiles (round ones for the blood spots)."""
    specials, plain = [], {}
    for (i, k), r in tiles_role.items():
        if r.startswith("@"):
            x, z = s.g.cell_xz(i, k)
            part, role, deg = r[1:].split(":")
            specials.append((part, role, transform((x, -2 * PL, z), rot(y=float(deg)))))
        else:
            plain[(i, k)] = r
    parts = panel_parts(s.g, cells_role, plain, specials, name=s.sub.name)
    plates = [p for p in parts if p[2][1, 3] == -PL]
    rest = [p for p in parts if p[2][1, 3] != -PL]
    for part, role, M in plates:
        s.put_M(part, role, M)
    s.step()
    for part, role, M in rest:
        s.put_M(part, role, M)


# blood: two splashes with drips on the lower apron (cells: i left to right -5..4, k -1 at the
# waist down to -14 at the hem); "splatter" cells take plain dark red tiles (a 1 x 2 is a drip)
SKIRT_W, SKIRT_H = 5, 14          # half-width and height in studs
SKIRT_SPOTS = {
    (1, -4): "98138:0", (2, -4): "25269:0", (0, -3): "25269:90", (1, -5): "splatter",
    (1, -6): "splatter", (2, -5): "98138:0",
    (-3, -9): "98138:0", (-2, -9): "25269:270", (-3, -10): "splatter", (-3, -11): "splatter",
    (-4, -8): "25269:180",
}


def build_skirt(model):
    """The lower apron: 10 x 14 studs of yellow tiles on plates, with a few drops of blood."""
    sub = model.submodel("skirt", "Apron (lower part)")
    s = Seg(sub, Grid(0, 0))
    cells = box_cells(-SKIRT_W, SKIRT_W - 1, -SKIRT_H, -1, "apron")
    tiles = dict(cells)
    for c, spec in SKIRT_SPOTS.items():
        if spec == "splatter":
            tiles[c] = "splatter"
            continue
        part, deg = spec.split(":")
        tiles[c] = f"@{part}:splatter:{deg}"
    s.step("The lower apron, built flat: plates", view="above")
    flat_panel(s, cells, tiles, plate_prefer="z")
    return sub


BIB_SPOTS = {(1, -4): "98138:0", (2, -5): "25269:270"}


def build_bib(model):
    """The bib: 6 x 5 studs of yellow tiles on plates, a splash of blood on one side."""
    sub = model.submodel("bib", "Apron bib")
    s = Seg(sub, Grid(0, 0))
    cells = box_cells(-3, 2, -5, -1, "apron")
    tiles = dict(cells)
    for c, spec in BIB_SPOTS.items():
        part, deg = spec.split(":")
        tiles[c] = f"@{part}:splatter:{deg}"
    s.step("The apron's bib, built flat: plates", view="above")
    flat_panel(s, cells, tiles, plate_prefer="x")
    return sub


# ------------------------------------------------------------------------------ torso
def snot_tile(s: Seg, part: str, role, x: float, y: float, z_face: float, R=None):
    """A tile pushed onto side studs that face -z from a face at z = z_face."""
    s.put(part, role, (x, y, z_face - PL), rot(x=90) if R is None else R)


def build_torso(model):
    """10 x 6 studs of shirt with a 6-stud belly row in front carrying the bib."""
    sub = model.submodel("torso", "Torso")
    s = Seg(sub, Grid(0, 0))
    W, D = TORSO_W, TORSO_D
    cells = box_cells(-W, W - 1, -D, D - 1, "shirt")
    belly = {(i, -D - 1): "shirt" for i in range(-3, 3)}
    notch = set()                     # the shoulder balls sit just outside the torso
    s.step("Torso: a round plate with a pin hole (the turntable's top), a plate layer, bricks "
           "with studs on the side at the front (the belly) and a course of bricks",
           view="above")
    s.put("60474", "Black", (0, 0, 0))
    s.put("3795", "apron", (0, -PL, -60))           # 2 x 6: ties the belly row to the body
    rest = {c: r for c, r in {**cells, **belly}.items() if not (-3 <= c[0] <= 2 and c[1] <= -3)}
    s.course("plate", rest, -PL, prefer="z", bond=False)
    s.below = {**s.below, **{(i, k): -99 for i in range(-3, 3) for k in (-4, -3)}}
    y = -PL
    for n in range(3):
        if n:
            s.step()
        # below the chest the apron wraps round the front corners: the belly row and the
        # front row's outer cells are apron-coloured there
        wrap = "apron" if n < 2 else "shirt"
        for i in range(-3, 3, 2):
            s.put("22885", wrap, (S * i + 20, y - 40, -70))
        for kind, pref in (("brick", "z"), ("plate", "x"), ("plate", "z")):
            y -= BR if kind == "brick" else PL
            body = {c: (wrap if c[1] == -D else r) for c, r in cells.items() if c not in ROUND}
            if n == 2 and kind == "plate" and y == PANEL_TOP:
                body = {c: r for c, r in body.items() if c not in notch}
            for (i, k) in ROUND:                    # rounded corners: 1 x 1 round columns
                x, z = s.g.cell_xz(i, k)
                s.put("3062b" if kind == "brick" else "6141", wrap if k < 0 else "shirt",
                      (x, y, z))
            s.course(kind, body, y, prefer=pref)
            if n == 0 and kind == "brick":
                s.step()
        s.below.update({c: -9 - n for c in belly})
    assert y == PANEL_TOP, y
    s.step("Shirt front over the belly bricks' top studs: the tie and the apron's straps")
    for x, part, role in ((-50, "3070b", "apron"), (-30, "3070b", "shirt"),
                          (0, "3069b", "tie"), (30, "3070b", "shirt"), (50, "3070b", "apron")):
        snot_tile(s, part, role, x, PANEL_TOP + 10, -80)
    # shoulder course: axle holders either side, notched round the shoulder balls; the
    # belly row carries the tie's knot and the straps on bricks with side studs
    s.step("The shoulders: Technic bricks for the shoulder axles; bricks with side studs "
           "at the front")
    sx, sy, sz = SHOULDER
    yt = sy - 10
    assert yt == PANEL_TOP - BR, yt
    for sg in (1, -1):
        for x in (70, 90):                              # the axle runs x = 64 .. 124
            s.put("3700", "shirt", (sg * x, yt, sz), rot(y=90))
        s.put("87087", "shirt", (sg * 50, yt, -70))
        s.put("3005", "shirt", (sg * 30, yt, -70))
    s.put("11211", "shirt", (0, yt, -70))
    tech = {(i, k) for i in (-5, -4, 3, 4) for k in (-1, 0)}
    s.course("brick", {c: r for c, r in cells.items() if c not in notch | tech}, yt,
             prefer="x")
    s.below.update({c: -20 for c in belly})
    s.step("The tie's knot and the straps")
    for x, part, role in ((-50, "3070b", "apron"), (0, "3069b", "tie"), (50, "3070b", "apron")):
        snot_tile(s, part, role, x, yt + 10, -80)
    s.step("Axles and balls for the shoulders")
    for sg in (1, -1):
        s.put("4519", "Light Bluish Gray", (sg * (sx - 20), sy, sz))     # 64 .. 124
        s.put("53585", "Black", (sg * sx, sy, sz), rot(z=90))
    s.step("The neck: a brick with axle holes; the collar round it")
    nx, ny, nz = NECK
    ytop = yt
    s.put("39789", "shirt", (nx, ytop - BR, nz))
    for sg in (1, -1):
        for x in (10, 30):
            s.put("54200", "shirt", (sg * x, ytop, -30))                # collar points
            s.put("54200", "shirt", (sg * x, ytop, 30), rot(y=180))
    s.step("Round the shoulders off; the apron's straps run over them")
    top = {(i, k): "shirt" for i in range(-W, W) for k in range(-D - 1, D)
           if not (k == -D - 1 and not -3 <= i <= 2)}
    top = {c: r for c, r in top.items() if c not in notch}
    # the shoulder corners stay clear: the arms' sockets swing down there when raised
    top = {c: r for c, r in top.items() if not (c[0] in (-W, W - 1) and -2 <= c[1] <= 1)}
    used = {(i, k) for i in range(-2, 2) for k in range(-2, 2)}          # neck and collar
    for sg in (1, -1):
        s.put("15068", "shirt", (sg * 60, ytop, 0), rot(y=-90 * sg))      # trapezius
        used |= {(i, k) for i in ((2, 3) if sg > 0 else (-4, -3)) for k in (-1, 0)}
        s.put("3069b", "apron", (sg * 50, ytop - PL, -60), rot(y=90))     # the strap
        used |= {(2 if sg > 0 else -3, k) for k in (-4, -3)}
    s.course("tile", {c: r for c, r in top.items() if c not in used}, ytop - PL, prefer="x",
             bond=False)
    s.step("The neck ball on a 2L axle")
    s.put("53585", "Black", (nx, ny, nz))
    s.put("32062", "Black", (nx, ny + 10, nz), rot(z=90))
    return sub
