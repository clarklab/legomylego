"""Arms: upper arm (short shirt sleeve), bare forearm and fist, left and right.

Joints:
* shoulder: the torso's Technic ball (53585) in a wide ball socket brick (67696) in the top
  of the upper arm, as in LEGO's own football figures: it swings, lifts and twists;
* elbow: a Technic rotation joint disk pair (44224 + 44225): LEGO's big ratchet joint,
  1 stud thick, each disk's beam pinned into its arm segment (tan 3L pins in the skin,
  light grey 2L pins in the sleeve);
* wrist: a Technic ball in the socket brick that is the core of the fist, on a 2L axle out
  of a round plate at the end of the forearm (a Technic bush on the axle is the bracelet).

Frames (y down; the arm hangs along +y; x points away from the body; side = +1 left arm,
-1 right arm, which is the mirror image):
* upper arm: origin at the shoulder ball; cells x in [0, 60], z in [-20, 40];
* forearm: origin on the elbow axis (upper arm (30, UA_LEN, 10)); cells x, z in [-30, 30];
* hand: origin at the wrist ball; the fist reaches along -x, the grip clip's bar at
  GRIP (along z)."""
from __future__ import annotations

import numpy as np

from kit import BR, PL, Grid, Seg, box_cells, rot, transform
from legs import DISK_COLOUR, PIN, R_DISK_DOWN, R_DISK_UP, pin_M

UA_LEN = 128                     # shoulder ball -> elbow axis
ELBOW = (30, UA_LEN, 10)         # elbow axis point in the upper arm frame
FA_LEN = 140                     # elbow axis -> wrist ball
GRIP = (-70, -16, 0)             # centre of the fist's clip (bar along z), hand frame
FLIP = transform((0, 0, 0), rot(z=180))       # forearm is built upside down


def build_upper_arm(model, name: str, side: int):
    """4 x 3 studs: the short sleeve down to above the elbow, bare skin below it. The outer
    column hangs down past the elbow (it is outside the 3-stud forearm, so it never gets in
    its way) and covers the joint's disks from the side."""
    sub = model.submodel(name, "Upper arm" + (" (left)" if side > 0 else " (right)"))
    s = Seg(sub, Grid(0, 0), side)
    cells = {(i, k): "shirt" for i in range(4) for k in range(-1, 2)}
    tech = [(0, 0), (2, 0)]
    beam = (1, 0)
    outer = {(3, k) for k in range(-1, 2)}
    ex, ey, ez = ELBOW
    ya = ey - 40 - 10                        # Technic course with the lower pin hole
    yb = ey - 80 - 10
    s.step("Upper arm, from the elbow up: the elbow's side cover, 1 x 3 bricks", view="above")
    for n, y in enumerate((ya + 2 * BR, ya + BR)):
        s.put("3622", "skin", (70, y, 10), rot(y=90))
    s.step("1 x 1 Technic bricks for the elbow's pins, and plates over them (skin, then the "
           "sleeve's hem)")
    for i, k in tech:
        x, z = s.g.cell_xz(i, k)
        s.put("6541", "skin", (x, ya, z), rot(y=90))
    s.put("3622", "skin", (70, ya, 10), rot(y=90))
    s.below = {c: n for n, c in enumerate(cells)}
    pl = {c: "skin" for c in cells if c != beam}
    s.course("plate", pl, ya - PL, prefer="x")
    s.course("plate", {c: "shirt" for c in pl}, ya - 2 * PL, prefer="z")
    s.step()
    for i, k in tech:
        x, z = s.g.cell_xz(i, k)
        s.put("6541", "shirt", (x, yb, z), rot(y=90))
    s.course("brick", {c: r for c, r in cells.items() if c not in tech and c != beam}, yb,
             prefer="x")
    s.below.update({c: -1 - n for n, c in enumerate(tech)})
    s.step()
    s.course("brick", cells, yb - BR, prefer="z")
    yt = yb - 2 * BR
    assert yt == -10, yt
    s.step("The shoulder socket: a ball socket brick facing the body")
    s.put("67696", "shirt", (40, yt, 0), rot(y=180))
    s.course("brick", {c: r for c, r in cells.items() if c[1] == 1 or c[0] == 3}, yt,
             prefer="x")
    s.step("The shoulder cap: plates reaching over the socket, rounded off outwards")
    for z in (-10, 10, 30):
        s.put("3623", "shirt", (50, yt - PL, z))                    # 1 x 3 plates along x
    yc = yt - PL
    s.put("15068", "shirt", (60, yc, 0), rot(y=-90))              # deltoid, rounded outwards
    s.put("11477", "shirt", (60, yc, 30), rot(y=-90))
    s.put("3069b", "shirt", (30, yc - PL, 0), rot(y=90))
    s.put("3070b", "shirt", (30, yc - PL, 30))
    return sub


def build_forearm(model, name: str, side: int, bracelet: str):
    """Bare forearm, built upside down (studs towards the wrist) and turned over."""
    sub = model.submodel(name, "Forearm" + (" (left)" if side > 0 else " (right)"))
    s = Seg(sub, Grid(-30, -30), side)
    cells = {(i, k): "skin" for i in range(3) for k in range(3)}
    tech = [(0, 1), (2, 1)]
    beam = (1, 1)

    def put(part, role, pos, R=None, insert=(0, 1, 0)):
        # built upside down: every part goes on from the wrist end (+y in the forearm frame)
        M = FLIP @ transform(pos, R)
        return s.put(part, role, tuple(M[:3, 3]), M[:3, :3], insert=insert)

    def course(kind, cl, ytop, prefer="x", bond=True, sizes=None):
        from kit import pack, ids_of, rect_part
        rects = pack(cl, kind, s.below if bond else None, prefer, 8, sizes)
        for role, (i0, i1, k0, k1) in rects:
            part, turned = rect_part(kind, i1 - i0 + 1, k1 - k0 + 1)
            x, z = s.g.centre(i0, i1, k0, k1)
            put(part, role, (x, ytop, z), rot(y=90) if turned else None)
        s.below = ids_of(rects, start=len(sub.items) * 1000)

    y1 = -40 - 10                              # build frame: pin holes at -40 and -80
    y2 = -80 - 10
    s.step("Forearm, built upside down from the elbow end: 1 x 1 Technic bricks",
           view="above")
    for i, k in tech:
        x, z = s.g.cell_xz(i, k)
        put("6541", "skin", (x, y1, z), rot(y=90))
    s.below = {c: n for n, c in enumerate(cells)}
    s.step()
    pl = {c: "skin" for c in cells if c != beam}
    course("plate", pl, y1 - PL, prefer="z")
    course("plate", pl, y1 - 2 * PL, prefer="x")
    s.step()
    for i, k in tech:
        x, z = s.g.cell_xz(i, k)
        put("6541", "skin", (x, y2, z), rot(y=90))
    course("brick", {c: r for c, r in cells.items() if c not in tech and c != beam}, y2,
           prefer="z")
    s.below.update({c: -1 - n for n, c in enumerate(tech)})
    s.step("The wrist: plates, then tiles round a round plate in the middle")
    course("plate", {c: "skin" for c in cells}, y2 - PL, prefer="x")
    yw = y2 - PL
    put("4073", "skin", (0, yw - PL, 0))
    band = {c: bracelet for c in cells if c != beam}
    course("tile", band, yw - PL, prefer="z", bond=False,
           sizes={bracelet: [(1, 1), (1, 2), (1, 3)]})
    s.step("A round plate with an axle hole on the middle stud, the axle and the wrist ball")
    yr = yw - 2 * PL                           # top of the round plate with the axle hole
    put("4032a", "skin", (0, yr, 0))
    put("32062", "Black", (0, yr + 4 - 20, 0), rot(z=90))   # from its axle hole up 40
    put("53585", "skin", (0, yr + 4 - 30, 0))
    assert -(yr + 4 - 30) == FA_LEN, yr
    return sub


def build_hand(model, name: str, side: int):
    """A fist: a ball socket brick is the palm (its socket takes the wrist ball), a clip plate
    on its studs is the curled fingers round the handle, curved slopes are the knuckles."""
    sub = model.submodel(name, "Fist" + (" (left)" if side > 0 else " (right)"))
    s = Seg(sub, Grid(-60, -20), side)
    s.step("Fist: a ball socket brick is the palm and wrist", view="above")
    s.put("67696", "skin", (-40, -10, 0))
    s.step("A clip plate: the fingers curled round the handle; curved slopes for the "
           "knuckles")
    s.put("11476", "skin", (-50, -18, 0), rot(y=90))
    s.put("11477", "skin", (-30, -10, 0))
    s.step("A plate under the palm makes the fist chunkier")
    s.put("3022", "skin", (-40, 14, 0), insert=(0, 1, 0))
    return sub


def build_arm(model, name: str, side: int, upper, fore, hand, U, F, H):
    """The whole arm in the upper arm's frame: the upper disk slides up into the upper arm's
    slot and is pinned, the lower disk clicks onto it, the forearm comes up over the lower
    disk's beam and is pinned, and the fist pops onto the wrist ball. U, F, H: world matrices
    of the upper arm, forearm and hand in the static pose."""
    import numpy as np
    from kit import local_M
    n = name[-1]
    arm = model.submodel(name, "Left arm" if side > 0 else "Right arm")
    Fa = np.linalg.inv(U) @ F
    Ha = np.linalg.inv(U) @ H
    arm.step("The upper arm")
    arm.use(upper, tag=f"upper_arm_{n}")
    arm.step("The elbow: the upper disk slides up into the upper arm's slot; push two long "
             "pins through the Technic bricks and its beam")
    arm.place("44224", DISK_COLOUR["44224"], insert=(0, 1, 0),
              tag=f"upper_arm_{n}").M = local_M("44224", ELBOW, R_DISK_UP, side)
    ex, ey, ez = ELBOW
    for y, where in ((ey - 80, "shirt"), (ey - 40, "skin")):
        arm.place(*PIN[where][:2], insert=(1, 0, 0),
                  tag=f"upper_arm_{n}").M = pin_M(where, (ex, y, ez), side)
    down = tuple(Fa[:3, :3] @ np.array([0.0, 1.0, 0.0]))
    arm.step("The lower disk (turned over) clicks onto it")
    arm.place("44225", DISK_COLOUR["44225"], insert=down,
              tag=f"forearm_{n}").M = Fa @ local_M("44225", (0, 0, 0), R_DISK_DOWN, side)
    arm.step("Push the forearm up over the lower disk's beam; two long pins through")
    arm.use(fore, tuple(Fa[:3, 3]), Fa[:3, :3], tag=f"forearm_{n}", insert=down)
    for y in (40, 80):
        arm.place(*PIN["skin"][:2], insert=(1, 0, 0),
                  tag=f"forearm_{n}").M = Fa @ pin_M("skin", (0, y, 0), side)
    arm.step("Press the fist onto the wrist ball")
    arm.use(hand, tuple(Ha[:3, 3]), Ha[:3, :3], tag=f"hand_{n}")
    return arm
