"""Legs: shoe, thigh and shin sub-assemblies.

Joints:
* hip: a Technic ball (53585) on a 2L axle in the top of the thigh, gripped by a wide ball
  socket brick (67696) in the hips;
* knee: a Technic rotation joint disk pair (44224 + 44225, LEGO's big ratchet joint) in the
  thigh's and shin's inner-middle column. The two disks nest into one 1-stud-thick joint and
  click through their teeth; each disk's thick 3L beam is pinned into its limb through 1 x 1
  Technic bricks (black 2L friction pins, see PIN);
* ankle: a Technic ball on a 2L axle under the shin, in a ball socket brick in the shoe.

Frames (y down; the limb hangs along +y; built right way up, studs towards the hip):
* thigh: origin at the hip ball centre; cells x, z in [-40, 40];
* shin: origin on the knee axis (thigh (-10, KNEE_Y, -10)); cells x, z in [-30, 50];
* shoe: origin under the ankle on the sole's underside; the ankle ball at (0, -46, 0)."""
from __future__ import annotations

from kit import BR, PL, Grid, Seg, box_cells, orient, rot

# knee disks: 44224's beam points up the thigh, 44225 (turned over) nests in it, its beam down
R_DISK_UP = orient((0, 0, -1), (1, 0, 0), (0, -1, 0))
R_DISK_DOWN = R_DISK_UP @ rot(x=180)

THIGH_TOP = 23           # thigh's top face below the hip ball (room to swing in the socket)
KNEE_Y = 161             # knee axis below the hip ball
KNEE_XZ = (-10, -10)     # knee axis x (disk slab centre) and z in the thigh frame
ANKLE = (10, 157, 10)    # ankle ball in the shin frame
SHOE_BALL = (0, -46, 0)  # ankle ball in the shoe frame
KNEE_TOP = -18           # top of the shin's knee cap (shin frame): 8 LDU under the thigh

DISK_COLOUR = {"44224": "Dark Bluish Gray", "44225": "Light Bluish Gray"}
# pins in colours that hide in their surroundings (no bright blue): (part, colour, length).
# A 3L pin goes through both Technic bricks and the disk's beam between them; a 2L pin goes
# through the inner Technic brick into the beam (black 3L friction pins are long out of
# production, and the newer one's ridges don't fit the model's pin holes)
PIN = {"jeans": ("2780", "Black", 2), "skin": ("32556b", "Tan", 3),
       "shirt": ("3673", "Light Bluish Gray", 2)}


def pin_M(where: str, centre, side: int):
    """Placement of a pin for a disk's beam hole at `centre` (left-hand coordinates, axis
    along x, the inner Technic brick on the -x side)."""
    from kit import local_M
    x, y, z = centre
    if PIN[where][2] == 2:
        x -= 10
    return local_M(PIN[where][0], (x, y, z), None, side)


def ball_on_axle(seg: Seg, centre, axle_y0: float, colour="Black", tag: str = ""):
    """A Technic ball (53585) on a vertical 2L axle running from y = axle_y0 to axle_y0 + 40
    (it goes through the ball's hole and up or down into the part holding it)."""
    x, y, z = centre
    seg.put("53585", colour, (x, y, z), tag=tag)
    seg.put("32062", "Black", (x, axle_y0 + 20, z), rot(z=90))


def build_shoe(model):
    """Black shoe, 4 x 7 studs: sole plates flush with the floorboards, a brick course, then
    a ball socket brick over the instep whose socket faces back to the ankle, and a rounded
    toe cap. The heel stays low so the shin can swing over it."""
    sub = model.submodel("shoe", "Shoe")
    s = Seg(sub, Grid(0, 0))
    s.step("The sole", view="above")
    s.course("plate", box_cells(-2, 1, -5, 1, "shoe"), -PL, bond=False, max_len=6)
    s.step()
    for x in (-20, 20):                   # 2 x 4s over the heel plate's joint, 2 x 3s in front
        s.put("3001", "shoe", (x, -PL - BR, 0), rot(y=90))
        s.put("3002", "shoe", (x, -PL - BR, -70), rot(y=90))
    s.step("The ankle socket: a ball socket brick with its socket facing the heel")
    y2 = -PL - 2 * BR
    s.put("67696", "shoe", (0, y2, -40), rot(y=-90))
    s.step("A rounded toe cap; smooth tiles round the ankle")
    s.put("15068", "shoe", (-20, -PL - BR, -80))                 # toe cap, falling forward
    s.put("15068", "shoe", (20, -PL - BR, -80))
    s.course("tile", {(i, k): "shoe" for i in range(-2, 2) for k in range(-3, 2)
                      if not (-1 <= i <= 0 and k <= 0)}, -PL - BR - PL, bond=False)
    return sub


def _tech_course(s: Seg, cells: dict, tech, skip, yt: float, prefer="z"):
    for i, k in tech:
        xc, zc = s.g.cell_xz(i, k)
        s.put("6541", "jeans", (xc, yt, zc), rot(y=90))
    rest = {c: r for c, r in cells.items() if c not in tech and c not in skip}
    s.course("brick", rest, yt, prefer=prefer)
    s.below.update({c: -1 - n for n, c in enumerate(tech)})


def build_thigh(model, name: str, side: int):
    """4 x 4 jeans column, built from the knee up to the hip ball."""
    sub = model.submodel(name, "Thigh" + (" (left)" if side > 0 else " (right)"))
    s = Seg(sub, Grid(0, 0), side)
    cells = box_cells(-2, 1, -2, 1, "jeans")
    tech = [(-2, -1), (0, -1)]
    beam = (-1, -1)
    # Technic courses: holes 40 and 80 above the knee axis (hole 10 below a brick's top)
    t_low = KNEE_Y - 40 - 10
    t_high = KNEE_Y - 80 - 10
    s.step("Thigh, from the knee up: Technic bricks for the knee joint's pins, a gap for the "
           "knee disk", view="above")
    _tech_course(s, cells, tech, {(-1, -2), beam, (-1, 0)}, t_low)
    s.step()
    pl = {c: r for c, r in cells.items() if c != beam}
    s.course("plate", pl, t_low - PL, prefer="x")
    s.course("plate", pl, t_low - 2 * PL, prefer="z")
    s.step()
    _tech_course(s, cells, tech, {beam}, t_high, prefer="x")
    y = t_high - BR
    s.step()
    s.course("brick", cells, y, prefer="z")
    y -= BR
    assert y == THIGH_TOP, y
    s.step("A brick with three axle holes on top")
    s.put("39789", "jeans", (0, y, 0))
    s.course("brick", {c: r for c, r in cells.items() if c[1] in (-2, 1)}, y, prefer="x")
    s.step("The hip ball on a 2L axle")
    ball_on_axle(s, (0, 0, 0), -10)
    return sub


def build_shin(model, name: str, side: int):
    """4 x 4 jeans column, built from the ankle up to the knee."""
    sub = model.submodel(name, "Shin" + (" (left)" if side > 0 else " (right)"))
    s = Seg(sub, Grid(10, 10), side)
    cells = box_cells(-2, 1, -2, 1, "jeans")
    tech = [(-2, -1), (0, -1)]
    beam = (-1, -1)
    bottom = ANKLE[1] - 15
    y = bottom - BR
    s.step("Shin, from the ankle up: a brick with three axle holes", view="above")
    s.put("39789", "jeans", (ANKLE[0], y, ANKLE[2]))
    s.course("brick", {c: r for c, r in cells.items() if c[1] == 1}, y, prefer="x",
             bond=False)
    s.below = {c: 0 for c in cells}
    y -= BR
    s.step()
    s.course("brick", cells, y, prefer="z")
    y -= BR
    assert y == 70, y
    s.step("Technic bricks for the knee joint's pins")
    _tech_course(s, cells, tech, {beam}, y, prefer="x")
    s.step()
    pl = {c: r for c, r in cells.items() if c != beam}
    s.course("plate", pl, y - PL, prefer="z")
    s.course("plate", pl, y - 2 * PL, prefer="x")
    y -= 2 * PL + BR
    s.step()
    _tech_course(s, cells, tech, {beam}, y, prefer="z")
    s.step("The knee cap round the disk slot: a brick, two plates and smooth tiles close the "
           "gap under the thigh, so the knee disks hide inside")
    cap = {c: r for c, r in cells.items() if c[0] != -1}
    y -= BR
    s.course("brick", cap, y, prefer="x")
    # the knee is bent 15 degrees, so the thigh's underside comes down towards the back: the
    # cap steps down from front to back (4 layers of 8 at the front, 1 at the back)
    rows = {c: r for c, r in cap.items()}
    s.course("plate", {c: r for c, r in rows.items() if c[1] <= 0}, y - PL, prefer="z")
    s.course("plate", {c: r for c, r in rows.items() if c[1] <= -1}, y - 2 * PL, prefer="x")
    s.course("tile", {c: r for c, r in rows.items() if c[1] <= -1}, y - 3 * PL, prefer="z",
             bond=False)
    s.course("tile", {c: r for c, r in rows.items() if c[1] == 0}, y - 2 * PL, prefer="x",
             bond=False)
    s.course("tile", {c: r for c, r in rows.items() if c[1] == 1}, y - PL, prefer="x",
             bond=False)
    y -= 3 * PL
    assert y == KNEE_TOP, y
    s.step("The ankle ball on a 2L axle, pushed up into the bottom brick")
    ball_on_axle(s, ANKLE, bottom - 22)
    return sub


def build_leg(model, name: str, side: int, thigh, shin, rel):
    """The knee: the lower disk slides down into the shin's slot and is pinned, the upper disk
    clicks onto it, and the thigh comes down over the upper disk's beam and is pinned too.
    Frame: the shin's. `rel`: the thigh's placement in it (the knee is posed slightly bent)."""
    from kit import local_M
    import numpy as np
    leg = model.submodel(name, "Left leg" if side > 0 else "Right leg")
    leg.step("The shin")
    leg.use(shin, tag=f"shin_{name[-1]}")
    leg.step("The knee: the lower disk (turned over) slides down into the shin's slot; push "
             "two long pins through the Technic bricks and its beam")
    n = name[-1]
    p = leg.place("44225", DISK_COLOUR["44225"], insert=(0, -1, 0), tag=f"shin_{n}")
    p.M = local_M("44225", (0, 0, 0), R_DISK_DOWN, side)
    for y in (40, 80):
        leg.place(*PIN["jeans"][:2], insert=(1, 0, 0),
                  tag=f"shin_{n}").M = pin_M("jeans", (0, y, 0), side)
    up = rel[:3, :3] @ np.array([0.0, -1.0, 0.0])
    leg.step("The upper disk clicks onto it")
    p = leg.place("44224", DISK_COLOUR["44224"], insert=tuple(up), tag=f"thigh_{n}")
    p.M = rel @ local_M("44224", (KNEE_XZ[0], KNEE_Y, KNEE_XZ[1]), R_DISK_UP, side)
    leg.step("Lower the thigh over the upper disk's beam; push two long pins through")
    leg.use(thigh, tuple(rel[:3, 3]), rel[:3, :3], tag=f"thigh_{name[-1]}", insert=tuple(up))
    for y in (KNEE_Y - 80, KNEE_Y - 40):
        leg.place(*PIN["jeans"][:2], insert=(1, 0, 0), tag=f"thigh_{n}").M = rel @ pin_M(
            "jeans", (KNEE_XZ[0], y, KNEE_XZ[1]), side)
    return leg
