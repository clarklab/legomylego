"""The Caldwell County Courthouse, mini: a small, quick kids' build of the 1894 courthouse in
Lockhart, Texas (the big display model is models/caldwell_courthouse). It keeps what makes it
the courthouse: buff stone walls with a red band, the four corner pavilions under slate hip
roofs, slate mansard slopes between them, and above all the clock tower in the middle - a
clock on each of its four sides under a steep slate spire and a red finial.

Frame: LDU, -Y up, the front faces -Z. The building is 6 x 6 studs on an 8 x 8 lawn; the
tower is 2 x 2, in the middle of the roof.

Two builds (model.toml): the standard one ("set A", 60 pieces), and "budget" (52 pieces,
about 5 % cheaper on Pick a Brick) - the clocks pressed straight onto the clock stage's side
studs instead of on jumper plates, and a curved 2 x 2 slope between the pavilions instead of a
45-degree slope with a tile on its ridge. Every part of both is a Pick a Brick bestseller.
Both come with the clockmaster, a minifigure who stands on the front lawn."""
import numpy as np

from brickkit.ldraw.matrix import rot

S, PLATE, BRICK = 20, 8, 24

WALL_1 = -BRICK                  # the first floor's top
BAND = WALL_1 - PLATE            # the red band's top
WALL_2 = BAND - BRICK
ROOF = WALL_2 - PLATE            # the red cornice plates' top: the roof
TOWER = ROOF - 3 * BRICK         # the tower's three bricks' top
TOWER_BAND = TOWER - PLATE
CLOCKS = TOWER_BAND - BRICK      # the clock stage's top
CLOCK_Y = CLOCKS + 10            # the clocks' middle: the side studs, 10 below the top
CLOCK_Y_BUDGET = CLOCKS + 20     # budget: each clock's top row of anti-studs on the side studs
TOWER_TOP = CLOCKS - PLATE
SPIRE = TOWER_TOP - 2 * BRICK    # the spire's top (its stud on it)

# the four sides: (turn, outward (x, z)); a part turned by `turn` faces that side
FACES = ((0, (0, -1)), (-90, (1, 0)), (180, (0, 1)), (90, (-1, 0)))
# the corners: (turn, outward (x, z)) for a part whose corner points to (+x, -z) unturned
CORNERS = ((0, (1, -1)), (90, (-1, -1)), (180, (-1, 1)), (-90, (1, 1)))


CLOCKMASTER = (120, PLATE, -50)  # beside the lawn, on the table: the border is one stud deep,
                                 # too close to the walls for his hips
CLOCKMASTER_FIG = dict(head=("3626cpr3067", "Yellow"), torso=("973c27h01pr4203", "Black"),
                       legs=("970c07", "Dark Brown"), hat=("3878", "Black"))


def _wall(m, part, y, x, z, turn):
    m.place(part, "wall", (x, y, z), rot(y=turn))


def build(model):
    m = model.main
    budget = model.variant == "budget"

    m.step("The lawn and the front walk")
    m.place("41539", "lawn", (0, 0, 0))
    m.place("3069b", "walk", (0, -PLATE, -70))

    m.step("The first floor: stone walls")
    _wall(m, "98283", WALL_1, -40, -50, 0)
    m.place("2877", "door", (0, WALL_1, -50))          # the front doors, at the walk
    _wall(m, "98283", WALL_1, 40, -50, 0)
    _wall(m, "15533", WALL_1, 20, 50, 180)
    _wall(m, "98283", WALL_1, -40, 50, 180)
    _wall(m, "15533", WALL_1, -50, 0, 90)
    _wall(m, "15533", WALL_1, 50, 0, -90)

    m.step("A red band all the way round")
    for z in (-50, 50):
        m.place("3666", "trim", (0, BAND, z))
    for x in (-50, 50):
        m.place("3710", "trim", (x, BAND, 0), rot(y=90))

    m.step("The second floor")
    _wall(m, "15533", WALL_2, -50, -20, 90)
    _wall(m, "98283", WALL_2, -50, 40, 90)
    _wall(m, "15533", WALL_2, 50, 20, -90)
    _wall(m, "98283", WALL_2, 50, -40, -90)
    _wall(m, "15533", WALL_2, 0, -50, 0)
    _wall(m, "15533", WALL_2, 0, 50, 180)

    m.step("The red cornice: the roof")
    m.place("3032", "trim", (0, ROOF, -20))
    m.place("3795", "trim", (0, ROOF, 40))

    m.step("The corner pavilions and their slate roofs")
    for turn, (cx, cz) in CORNERS:
        m.place("3003", "wall", (40 * cx, ROOF - BRICK, 40 * cz))
        # the hip roof's stud is on the corner's inner quarter, its slopes run out to the corner
        m.place("3045", "roof", (30 * cx, ROOF - 2 * BRICK, 30 * cz), rot(y=turn))
        m.place("59900", "trim", (30 * cx, ROOF - 3 * BRICK, 30 * cz))     # a red finial

    m.step("Slate roofs between them")
    for turn, (nx, nz) in FACES:
        if budget:                                           # one curved slope
            m.place("15068", "roof", (40 * nx, ROOF, 40 * nz), rot(y=turn))
            continue
        m.place("3039", "roof", (30 * nx, ROOF - BRICK, 30 * nz), rot(y=turn))
        m.place("3069b", "roof", (30 * nx, ROOF - BRICK - PLATE, 30 * nz),
                rot(y=0 if nx == 0 else 90))                 # a tile over its ridge

    m.step("The clock tower")
    for k in range(3):
        m.place("3003", "wall", (0, ROOF - BRICK * (k + 1), 0))
    m.place("3022", "trim", (0, TOWER_BAND, 0))

    m.step("The clock stage: bricks with studs on their sides")
    for (x, z), turn in (((10, -10), 0), ((-10, -10), 90), ((-10, 10), 180), ((10, 10), -90)):
        m.place("26604", "wall", (x, CLOCKS, z), rot(y=turn))

    m.step("A clock on each side")
    for turn, (nx, nz) in FACES:
        R = rot(y=turn) @ rot(x=90)          # stood on edge, its stud facing out
        if budget:                           # pressed straight onto the two side studs
            m.place("14769p0m", "clock", (nx * 28, CLOCK_Y_BUDGET, nz * 28), R)
            continue
        m.place("15573", "trim", (nx * 28, CLOCK_Y, nz * 28), R)
        m.place("14769p0m", "clock", (nx * 36, CLOCK_Y, nz * 36), R)

    m.step("The spire and its finial")
    m.place("3022", "trim", (0, TOWER_TOP, 0))
    m.place("3688", "roof", (0, SPIRE, 0))
    m.place("59900", "trim", (0, SPIRE - BRICK, 0))

    # the clockmaster, on the lawn to the right of the front walk (the same figure as the big
    # courthouse's): glasses and grey stubble, a black vest and blue tie, a top hat
    model.minifig("clockmaster", CLOCKMASTER, None, title="The clockmaster", **CLOCKMASTER_FIG)
