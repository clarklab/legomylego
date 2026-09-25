"""Hover stand and tap-lamp base.

The Metroid rests on a clear tube (stacked round 4x4 plates with a round opening) that slides
up and down through the stand's top. A fixed black axle rises through the middle of the tube
into the Metroid, where it carries the fang hub. Pressing the Metroid pushes the tube down:
  - a presser under the tube pushes the battery box's green on/off button (push on, push off),
  - two push rods pull Technic rubber belts down between pairs of fixed pins; the belts lift
    everything back up. Pre-stretched and only lengthened a little by the stroke, they pull
    almost evenly: enough to float the Metroid (about 1.2 kg) yet leave a light tap. The belt
    count sets the balance: add a belt if the Metroid sags, take one out if the tap is stiff.
At rest the tube's flange sits against the underside of the stand's top plate.

Heights (LDraw y, down is +):
  table 488; base plate 472..488; battery box and lower walls 376..472; a ring of plates on
  the walls 368..376 (so the bridge clears the box's top rim); bridge 352..368; upper walls
  328..352; top plate 312..328; tiles 304..312.
  Tube: rings 72..328 (from under the base disc down to the flange), flange 328..336, push
  rods 336..440 ending in a Technic brick (belt pin at 426), presser 328..368 over the box's
  button (top at 376). Belt pins under the bridge at 378.
Stroke: 16 LDU to the bridge; the button bottoms out after about 10.5 (core.PRESS)."""
import math

from brickkit.ldraw.matrix import rot
from brickkit.shapes.rings import pack_angular, pack_cells, ring_cells
from brickkit.shapes.shell import _place_run, woven_disc

BASE_R = 8.0
TABLE_Y = 488
WALL_IN = 6.6
BOX = (0.0, 376.0, 0.0)            # AAA battery box: button at x -40, PF plug at about x +48
TUBE_OPENING = {(i, k) for i in range(-2, 2) for k in range(-2, 2)}   # 4x4: the round tube
                                                                      # touches its four sides
HATCH = {(2, -1), (2, 0)}          # over the box's plug: the lights' leads plug in here
RODS = [(10.0, 90.0), (10.0, -90.0)]
PRESSER = (-30.0, 10.0)            # over the box's button (x -49..-31, z -9..9)
RING_BOTTOM = 328                  # bottom of the tube's lowest ring = top plate's underside
PULLEYS = (-40.0, 60.0)            # x of the two fixed belt pins each side
PULLEY_Y = 378.0
ROD_PIN_Y = 426.0
PLATES = {6: "3666", 4: "3710", 2: "3023b", 1: "3024"}


def _cell(x, z):
    return int(math.floor(x / 20)), int(math.floor(z / 20))


def stand(model):
    s = model.submodel("stand", "Hover stand and tap base")
    disc = ring_cells(BASE_R)
    wall = ring_cells(BASE_R, WALL_IN)
    bottom = woven_disc(s, disc, "stand_base", surface_y=TABLE_Y, caption="Base plate",
                        plate=PLATES, on_table=True)
    y = bottom["top_y"]                                                    # 472
    s.step("Battery box, green button and plug facing up")
    s.place("64228", "battery", BOX, tag="battery")
    for n in range(4):
        s.step(f"Lower wall ring {n + 1}")
        for i, k, length, axis in pack_angular(wall, offset=n, support=wall):
            _place_run(s, {2: "3004", 1: "3005"}[length], "stand_base", i, k, length, axis,
                       y - 24 * (n + 1), "")
    y -= 96                                                                # 376
    s.step("A ring of plates on the walls, to lift the bridge clear of the box")
    for i, k, length, axis in pack_angular(wall, offset=4, support=wall):
        _place_run(s, {2: "3023b", 1: "3024"}[length], "stand_base", i, k, length, axis,
                   y - 8, "")
    y -= 8                                                                 # 368
    holes = {_cell(x, z) for x, z in RODS} | {_cell(*PRESSER)} | HATCH
    bridge = woven_disc(s, disc - holes, "stand_base", surface_y=y,
                        caption="Bridge over the box, with holes for the push rods, the "
                                "presser and the plug")
    y = bridge["top_y"]                                                    # 352
    s.step("Belt pins under the bridge, two each side (pin into the brick first)")
    for sg in (1, -1):
        post = _belt_post(model, sg)
        for x in PULLEYS:
            s.use(post, (x, PULLEY_Y - 10, 90 * sg), None, insert=(0, 1, 0))
    s.step("Anchor for the centre axle")
    s.place("3941", "frame_dark", (0, y - 24, 0), tag="anchor")
    s.place("3941", "frame_dark", (0, y - 48, 0), tag="anchor")
    s.step("Centre axle: the Metroid's fang hub rides on its top")
    s.place("50451", "frame_dark", (0, 188, 0), rot(z=90), tag="core")  # axle 16: y 28..348
    s.step("Upper wall ring")
    for i, k, length, axis in pack_angular(wall, offset=5, support=wall):
        _place_run(s, {2: "3004", 1: "3005"}[length], "stand_base", i, k, length, axis,
                   y - 24, "")
    s.step("Lower the tube's bottom in: push rods and presser go down through the bridge. "
           "Hook two belts round each rod's pin and over the two pins beside it")
    s.use(_tube_bottom(model), (0, 0, 0), None, tag="tube", insert=(0, -1, 0))
    model.extra("85544", "belt", 4,
                "Technic rubber belts: two per push rod, looped under the rod's pin and over "
                "the two fixed pins beside it")
    y -= 24                                                                # 328
    top = woven_disc(s, disc - TUBE_OPENING - HATCH, "stand_base", surface_y=y,
                     caption="Top plate round the tube (it holds the tube's flange down)",
                     plate=PLATES)
    y = top["top_y"]                                                       # 312
    s.step("Tiles")
    for i, k, n, axis in pack_cells(top["cells"], lengths=(4, 2, 1), mode="x"):
        _place_run(s, {4: "2431", 2: "3069b", 1: "3070b"}[n], "stand_base", i, k, n, axis,
                   y - 8, "")
    s.step("Clear tube: stack the rings")
    for ring_y in range(RING_BOTTOM - 16, 64, -8):
        s.place("11833", "stand_column", (0, ring_y, 0), tag="tube")
    model.captive("tube", "the tube slides in the stand's top plate; its flange keeps it in")
    return s


def _belt_post(model, sg: int):
    """A Technic brick with a pin sticking out toward the box; the belts hook over the pin."""
    name = f"belt_post_{'back' if sg > 0 else 'front'}"
    if name in model.submodels:
        return model.submodels[name]
    b = model.submodel(name, "Belt pin")
    b.place("3700", "stand_top", (0, 0, 0))
    b.step("Pin, half sticking out")
    b.place("3673", "frame", (0, 10, -10 * sg), rot(y=90), insert=(0, 0, -sg))
    return b


def _tube_bottom(model):
    """The tube's lowest ring with the flange under it, two push rods ending in Technic bricks
    (belt pins), and the presser over the battery box's button."""
    t = model.submodel("tube_bottom", "Tube bottom")
    t.place("11833", "stand_column", (0, RING_BOTTOM - 8, 0))
    t.step("Flange under the ring")
    for sg in (1, -1):
        t.place("3020", "stand_top", (0, RING_BOTTOM, 60 * sg), rot(y=90), insert=(0, 1, 0))
    t.step("Push rods, each ending in a Technic brick for the belts, and the presser")
    for x, z in RODS:
        sg = 1 if z > 0 else -1
        y = RING_BOTTOM + 8
        t.place("6141", "frame_dark", (x, y, z), insert=(0, 1, 0))
        y += 8
        for _ in range(3):
            t.place("3062b", "frame_dark", (x, y, z), insert=(0, 1, 0))
            y += 24
        t.place("3700", "stand_top", (x + 10, y, z), insert=(0, 1, 0))     # hole at y + 10
        t.place("3673", "frame", (x + 10, ROD_PIN_Y, z - 10 * sg), rot(y=90), insert=(0, 0, -sg))
    px, pz = PRESSER
    t.place("3062b", "frame_dark", (px, RING_BOTTOM, pz), insert=(0, 1, 0))
    t.place("6141", "frame_dark", (px, RING_BOTTOM + 24, pz), insert=(0, 1, 0))
    t.place("6141", "frame_dark", (px, RING_BOTTOM + 32, pz), insert=(0, 1, 0))
    return t
