"""Magikarp: a Quick Bricks fish in 43 pieces, about 6.5 cm long and 6.4 cm from fin tip to fin
tip. It follows a designer's plans (Rebrickable MOC-182443 by Redverse: 14 numbered steps on 9
pages); NOTES.md has the credit, the parts page by page and what had to be worked out.

One step here per numbered step of the plans, with one change: the plans' steps 2 and 3 are one
step. Step 2 puts a 2 x 4 plate and a bracket under the first three pieces, where nothing holds
them until step 3's two slopes go on; here that plate and bracket are built apart ("belly") and
go on in the same step as the slopes.

Frame: LDU (stud 20, plate 8, brick 24), -Y up. The mouth faces -Z (the front), the tail is at
+Z, x runs across the fish. y = 0 is the top of the core (the first bracket's studs).

The fish is built sideways off two brackets. Its core is a stack of five plates:

    y =  0 ..  8   the first bracket's plate, studs up (and, towards the head, the axle's plates)
    y =  8 .. 24   two 2 x 2 plates, studs up
    y = 24 .. 32   the 2 x 4 plate, UPSIDE DOWN: studs down, its hollow underside up
    y = 32 .. 40   the second bracket, upside down on the 2 x 4's end studs

The two brackets' walls stand one over the other at the tail end (z = 10 .. 14), four side
studs facing the tail. The undersides of the lower 2 x 2 plate and of the 2 x 4 only touch: what
joins the two halves is the pair of slopes of step 3, each pressed over an upper and a lower
side stud. Everything on the back (the tower for the dorsal fin, two curved bricks) stands on
studs that point up. Everything under the belly (the fin brackets, the belly fin, a curved
brick) hangs on the 2 x 4's studs, which point down. The head is a brick with a hole, upside
down as well: it lies on the 2 x 4's hollow side, its studs pressed down into it.

Rows of studs along the fish, by z:

    z =   0   TAIL   the brackets' plates, the tail-side curved brick, the belly slope
    z = -20   FIN    the dorsal tower, the fin brackets, both yellow fins
    z = -40   EYE    the eye axle, the studs the front curved brick sits on
    z = -60   HEAD   the brick with a hole; the mouth is on a pin in it, at z = -70"""
import numpy as np

PLATE, BRICK = 8, 24

TAIL, FIN, EYE, HEAD = 0, -20, -40, -60      # the rows of studs, by z
BELLY = 32                                   # the 2 x 4's stud face (its studs point down)
WALL = 14                                    # the brackets' walls: their tail-side face (z)
EYE_Y = 10                                   # the eye axle
MOUTH_Y = 14                                 # the hole of the upside-down Technic brick
FIN_STUD = (24, 42)                          # a fin bracket's side stud: x (+-), y


def orient(ex, ey) -> np.ndarray:
    """3x3 rotation whose columns are where the part's local X, Y and Z axes point."""
    ex, ey = np.asarray(ex, float), np.asarray(ey, float)
    return np.column_stack([ex, ey, np.cross(ex, ey)])


TURNED = np.diag([-1.0, 1.0, -1.0])          # half a turn about the vertical
OVER = np.diag([1.0, -1.0, -1.0])            # upside down (turned over about x)
OVER_Z = np.diag([-1.0, -1.0, 1.0])          # upside down (turned over about the fish's length)
ALONG = orient((0, 0, 1), (0, 1, 0))         # a part's long side along the fish
FACE_TAIL = orient((1, 0, 0), (0, 0, -1))    # studs towards the tail, its own +z down
S = 1 / np.sqrt(2)


def build(model):
    # (a fish is at its best from the side: the stills, the booklet's cover and the end of the
    # video look from three-quarters on, not straight into its mouth)
    model.meta["azimuth_offset"] = 55
    # ---- built apart -----------------------------------------------------------------------
    # plans' step 2: the 2 x 4 plate with the second bracket on its end studs. Built the right
    # way up here; it goes into the fish upside down
    belly = model.submodel("belly", "Belly plate")
    belly.step("A bracket on the end studs of the 2 x 4 plate, its wall down over the plate's end")
    belly.place("3020", "body", (0, 0, 0), ALONG)
    belly.place("99781", "body", (0, -PLATE, 30), TURNED)

    # plans' step 4 (its boxed steps 1 to 3): two plates with a hole underneath, a blue pin in
    # each, and the black bar through both pins. The eyes go on its ends
    axle = model.submodel("axle", "Eye axle")
    peg = orient((0, 0, -1), (0, 1, 0))                    # the hole end towards the head
    axle.step("A blue pin in the hole under a plate, from the outside")
    axle.place("18677", "body", (-10, 0, -30), peg)
    axle.place("4274", "pin", (-20, EYE_Y, EYE), TURNED)
    axle.step("The second plate beside it, with its pin")
    axle.place("18677", "body", (10, 0, -30), peg)
    axle.place("4274", "pin", (20, EYE_Y, EYE))
    axle.step("The bar through both pins: the same length sticks out at each end")
    axle.place("87994", "bar", (-30, EYE_Y, EYE), orient((0, 1, 0), (1, 0, 0)))

    # plans' step 14 (its boxed steps 1 and 2), made twice: a brick with a stud on two opposite
    # sides, a slope on each and one on top. The side slopes' thick ends are at the top
    fin = model.submodel("fin", "Fin")
    fin.step("A yellow brick with a stud on two sides")
    fin.place("47905", "fin", (0, 0, 0))
    fin.step("A slope on top, falling to the front, and one on each side stud, thick end up")
    fin.place("54200", "fin", (0, 0, 0))
    fin.place("54200", "fin", (0, 10, -10), orient((1, 0, 0), (0, 0, 1)))
    fin.place("54200", "fin", (0, 10, 10), orient((-1, 0, 0), (0, 0, -1)))

    m = model.main

    # ---- the core ----------------------------------------------------------------------------
    m.step("Two 2 x 2 plates, and a bracket on their end studs: its wall hangs down over their end")
    m.place("3022", "body", (0, 2 * PLATE, -10))
    m.place("3022", "body", (0, PLATE, -10))
    m.place("99781", "body", (0, 0, TAIL), TURNED)

    # plans' steps 2 and 3 in one: the belly plate is held by nothing until the slopes are on
    m.step("Turn the belly plate over and hold it under the stack, wall under wall. "
           "Lock them with two slopes: each goes on an upper and a lower side stud")
    m.use(belly, (0, BELLY, -30), OVER_Z, insert=(0, 1, 0))
    for x in (10, -10):
        m.place("15672", "body", (x, 20, WALL + PLATE), orient((-1, 0, 0), (0, 0, -1)))

    m.step("The eye axle on the two free studs, its pins over the hollow of the 2 x 4")
    m.use(axle, (0, 0, 0))

    m.step("On the slopes' two studs: a plate, then a plate with one stud")
    m.place("3023", "body", (0, 10, WALL + 2 * PLATE), FACE_TAIL)
    m.place("15573", "body", (0, 10, WALL + 3 * PLATE), FACE_TAIL)

    m.step("The tail on that stud, upright, and a white slope on its top and bottom studs")
    m.place("18759", "tail", (0, 10, WALL + 3 * PLATE + BRICK), FACE_TAIL, tag="tail",
            insert=(0, 0, 1))                                  # (on before its two slopes)
    m.place("54200", "tail", (0, -10, WALL + 3 * PLATE + BRICK), orient((-1, 0, 0), (0, 0, -1)),
            tag="tail")
    m.place("54200", "tail", (0, 30, WALL + 3 * PLATE + BRICK), FACE_TAIL, tag="tail")

    # ---- under the belly (the plans draw steps 5 to 8 with the fish turned over) ------------
    m.step("Turn it over. A small bracket on each stud of the next row, side studs out, "
           "and a plate across the two")
    m.place("36840", "body", (10, BELLY + PLATE, FIN), orient((0, 0, -1), (0, -1, 0)),
            insert=(0, 1, 0))                                  # (on before the plate across them)
    m.place("36840", "body", (-10, BELLY + PLATE, FIN), orient((0, 0, 1), (0, -1, 0)),
            insert=(0, 1, 0))
    m.place("3023", "body", (0, BELLY + 2 * PLATE, FIN), OVER)

    m.step("A plate with one stud on that plate, and a slope on the big bracket, falling to the tail")
    m.place("15573", "body", (0, BELLY + 3 * PLATE, FIN), OVER)
    m.place("85984", "body", (0, BELLY + PLATE, TAIL), OVER)

    # ---- the head and the back (turned back) -------------------------------------------------
    m.step("Turn it back. A plate on the axle's rear studs. The head: a brick with a hole, upside "
           "down, its studs pressed into the hollow of the 2 x 4 at the front")
    m.place("3023", "body", (0, -PLATE, FIN))
    m.place("3700", "body", (0, BRICK, HEAD), OVER)

    m.step("A red pin in the head's hole, and on the plate a plate with one stud and a 1 x 1 plate")
    m.place("89678", "body", (0, MOUTH_Y, HEAD - 10), orient((0, 0, -1), (0, 1, 0)))
    m.place("15573", "body", (0, -2 * PLATE, FIN))
    m.place("3024", "body", (0, -3 * PLATE, FIN))

    # an eye: a dish on the pin's stud, the bar's end in its middle. A side fin: a triangle tile
    # on the small bracket's side stud by its square corner, that corner pointing at the head,
    # its long edge upright behind
    m.step("An eye on the axle, and a triangle on the bracket's side stud: square corner forward")
    m.place("4740", "eye", (28, EYE_Y, EYE), orient((0, 0, 1), (-1, 0, 0)), tag="eye")
    m.place("35787", "side_fin", (FIN_STUD[0] + PLATE, FIN_STUD[1], FIN + 20 * S),
            orient((0, S, S), (-1, 0, 0)), tag="side_fin")

    m.step("The same on the other side")
    m.place("4740", "eye", (-28, EYE_Y, EYE), orient((0, 0, 1), (1, 0, 0)), tag="eye")
    m.place("35787", "side_fin", (-FIN_STUD[0] - PLATE, FIN_STUD[1], FIN + 20 * S),
            orient((0, -S, S), (1, 0, 0)), tag="side_fin")

    m.step("The mouth on the red pin. Three curved bricks: behind the tower, in front of it, "
           "and upside down under the head")
    m.place("97785", "mouth", (0, MOUTH_Y, HEAD - 10 - PLATE), orient((0, 1, 0), (0, 0, 1)),
            tag="mouth")
    m.place("30602", "body", (0, 0, 10), TURNED)
    m.place("30602", "body", (0, 0, -50))
    m.place("30602", "body", (0, BELLY, -50), OVER_Z)

    m.step("The fins: one on the tower, one under the belly")
    m.use(fin, (0, -3 * PLATE - BRICK, FIN), tag="dorsal_fin")
    m.use(fin, (0, BELLY + 3 * PLATE + BRICK, FIN), OVER_Z, tag="belly_fin")
