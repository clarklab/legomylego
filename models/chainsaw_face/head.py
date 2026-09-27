"""Head: the skin mask and messy hair.

Head frame: origin at the neck ball's centre, y down, the face towards -z. The head sits on
the torso's Technic ball in a wide ball socket brick (67696) behind the face, its socket
facing back: the head nods, turns and tilts a little. The ball sits in the back half of the
head, where a neck joins a skull.

Cells: x in [-60, 60] (6 studs), z in [-80, 40] (6 studs). Two sections of brick + 2 plates
(common levels every 40 LDU), so bricks with studs on the side (22885) in the front row
carry the face: a panel of smooth tiles built flat and turned to face forward (paint the
mask's details on it later), four rows: chin, bared teeth in a snarl, sunken eyes either
side of the nose, the heavy brow. Hair: dark brown on the back, the sides and the crown,
curved slopes falling every which way for a messy look, overhanging the head a stud all
round, a fringe over the brow. Ears (round plates on bricks with side studs) either side.
Chin to crown: 104 LDU (4.2 cm)."""
from __future__ import annotations

from kit import BR, PL, S, Grid, Seg, bbox, box_cells, rot

FACE_ROWS = 4
EARS = {(2, -3): 1, (-3, -3): -1}   # ear cells (bricks with a side stud) and which way out

# the hair on the crown (8 x 8 studs: the head's 6 x 6 and a stud's overhang all round):
# (part, x, z, degrees about y). Curved slopes fall towards -z unturned; a 2 x 1 (11477)
# down each edge, a 2 x 2 (15068) at each corner, four more on top, turned every which way
HAIR = ([("11477", 20 * i + 10, -80, 0) for i in range(-2, 2)]            # fringe
        + [("11477", 20 * i + 10, 40, 180) for i in range(-2, 2)]         # back
        + [("11477", 60, 20 * k + 10, -90) for k in range(-3, 1)]         # left side
        + [("11477", -60, 20 * k + 10, 90) for k in range(-3, 1)]         # right side
        + [("15068", 60, -80, -90), ("15068", -60, -80, 0),              # corners
           ("15068", 60, 40, 180), ("15068", -60, 40, 90)]
        + [("15068", -20, -40, 0), ("15068", 20, -40, -90),              # on top
           ("15068", -20, 0, 90), ("15068", 20, 0, 180)])
# hair hanging under the crown's overhang, down the sides (not over the ears) and the back,
# longer at the back: (part, x, z, degrees, bricks long)
HANG = ([(p, sg * 70, z, d, n) for sg in (1, -1)
         for p, z, d, n in (("3005", -70, 0, 1), ("3004", -20, 90, 1), ("3004", 20, 90, 2))]
        + [("3004", x, 50, 0, n) for x, n in ((-60, 2), (-20, 3), (20, 2), (60, 3))])
BOTTOM = 14                     # underside of the head (chin) below the ball
TOP = -98                       # top of the hair above the ball


def face_layout():
    """Face panel cells (i: -3..2 from his right to his left, x = 20 i + 10; k: -4 (chin) ..
    -1 (brow)) -> tile spec: a role for a plain tile, '@part:role:deg' for a single special
    tile, or a name placed by build_face (teeth, nose, brow)."""
    out = {(i, k): "mask" for i in range(-3, 3) for k in range(-FACE_ROWS, 0)}
    out[(-3, -4)] = "@25269:mask:180"                    # rounded jaw
    out[(2, -4)] = "@25269:mask:270"
    out[(-1, -3)] = out[(0, -3)] = "teeth"               # bared teeth ...
    out[(-2, -3)] = "@98138:mouth:0"                     # ... in a dark, open snarl
    out[(1, -3)] = "@98138:mouth:0"
    out[(-2, -2)] = "@98138:eye:0"                       # dark eye holes
    out[(1, -2)] = "@98138:eye:0"
    out[(-1, -2)] = out[(0, -2)] = "nose"                # the nose between them
    out[(-3, -2)] = "@54200:hair:90"                     # hair over the temples
    out[(2, -2)] = "@54200:hair:270"
    for i in (-3, -2, 1, 2):                             # heavy brow
        out[(i, -1)] = "brow"
    return out


def build_face(model):
    sub = model.submodel("face", "Face (the mask)")
    s = Seg(sub, Grid(0, 0))
    lay = face_layout()
    s.step("The mask, built flat: a 4 x 6 plate", view="above")
    s.put("3032", "mask", (0, -PL, -40))
    s.step("Tiles, the eyes, the teeth and the nose")
    plain = {}
    for (i, k), spec in lay.items():
        x, z = s.g.cell_xz(i, k)
        if spec in ("teeth", "nose", "brow"):
            continue
        if spec.startswith("@"):
            part, role, deg = spec[1:].split(":")
            yb = -PL if bbox(part)[0][1] < -6 else -2 * PL     # slopes stand on the plate
            s.put(part, role, (x, yb, z), rot(y=float(deg)))
        else:
            plain[(i, k)] = spec
    s.course("tile", plain, -2 * PL, prefer="x", bond=False)
    s.put("2412b", "teeth", (0, -2 * PL, S * -3 + 10))                    # the teeth
    s.put("85984", "mask", (0, -PL, S * -2 + 10), rot(y=180))    # the nose, broad below
    s.step("The heavy brow over the eyes")
    for i in (-3, 1):
        s.put("85984", "mask", (S * i + 20, -PL, S * -1 + 10))    # brow ridge, falling down
    return sub


def build_head(model):
    face = build_face(model)
    sub = model.submodel("head", "Head")
    s = Seg(sub, Grid(0, 0))
    X0, X1, Z0, Z1 = -3, 2, -4, 1
    cells = box_cells(X0, X1, Z0, Z1, "mask")
    front = {(i, Z0) for i in range(X0, X1 + 1)}
    socket = {(i, k) for i in (-1, 0) for k in (-3, -2)}
    ball = {(i, k) for i in (-1, 0) for k in (-1, 0)}

    def role(c, level):
        """Hair on the back and, above the jaw, on the sides."""
        i, k = c
        if k >= Z1 - 1 or (level >= 1 and i in (X0, X1)):
            return "hair"
        return "mask"

    s.step("Head: the neck socket, a ball socket brick facing back; bricks with side studs "
           "for the face", view="above")
    s.put("67696", "mask", (0, -10, -40), rot(y=-90))
    y = BOTTOM
    for n in range(FACE_ROWS // 2):
        y_sec = y - 40
        for i in range(X0, X1 + 1, 2):
            s.put("22885", "mask", (S * i + 20, y_sec, -70))
        body = {c: role(c, n) for c in cells if c not in front}
        if n == 0:
            body = {c: r for c, r in body.items() if c not in socket | ball}
        levels = (("brick", y - BR), ("plate", y - BR - PL), ("plate", y - 40))
        for m, (kind, yt) in enumerate(levels):
            if n == 0 and m == 0:
                s.course(kind, body, yt, prefer="x", bond=False)
                s.below = {c: 0 for c in cells}
            else:
                cl = {c: role(c, n) for c in cells if c not in front}
                if n == 0 and m == 1:          # over the socket brick, clear of the ball
                    cl = {c: r for c, r in cl.items() if c not in ball}
                if n == 1 and m == 0:          # the ears: bricks with a stud on the side
                    for (i, k), sg in EARS.items():
                        del cl[(i, k)]
                        x, z = s.g.cell_xz(i, k)
                        s.put("87087", "mask", (x, yt, z), rot(y=-90 * sg))
                s.course(kind, cl, yt, prefer="z" if (n + m) % 2 else "x")
                if n == 1 and m == 0:
                    s.step("The ears: round plates on the side studs")
                    for (i, k), sg in EARS.items():
                        x, z = s.g.cell_xz(i, k)
                        s.put("6141", "mask", (x + sg * 18, yt + 10, z), rot(z=90 * sg),
                              insert=(sg, 0, 0))
            if m == 0:
                s.step()
        s.below.update({c: -30 - n for c in front})
        y = y_sec
    top_y = y
    s.step("The crown: plates of hair a stud wider than the head all round, so the hair "
           "overhangs the brow, the sides and the back")
    crown = box_cells(X0 - 1, X1 + 1, Z0 - 1, Z1 + 1, "hair")
    s.course("plate", crown, top_y - PL, prefer="x", max_len=8)
    s.step("Messy hair: curved slopes falling over the edges all round, a fringe over the "
           "brow, and more falling every which way on top")
    yh = top_y - PL
    s.course("plate", {(i, k): "hair" for i in range(-2, 2) for k in range(-3, 1)}, yh - PL,
             prefer="x")
    assert yh - PL - 16 == TOP, yh
    for part, x, z, deg in HAIR:
        s.put(part, "hair", (x, yh - PL * (abs(x) < 40 and -60 < z < 20), z), rot(y=deg))
    s.step("Hair hanging down the sides and the back: bricks under the crown's overhang",
           view="below")
    for part, x, z, deg, n in HANG:
        for m in range(n):
            s.put(part, "hair", (x, top_y + BR * m, z), rot(y=deg), insert=(0, 1, 0))
    s.step("Press the face onto the side studs")
    from brickkit.ldraw.matrix import transform
    from body import R_PANEL
    M = transform((0, top_y, -80), R_PANEL)
    sub.use(face, tuple(M[:3, 3]), M[:3, :3], insert=(0, 0, -1))
    return sub
