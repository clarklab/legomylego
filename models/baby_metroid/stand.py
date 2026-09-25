"""Hover stand: a clear column of round bricks on an axle, rising from a round base that hides
the Power Functions battery box. The column's top brick and axle plug into the black socket
under the Metroid, so the Metroid lifts off.

Heights (LDraw y, down is +): table 424; bottom plate 408..424; walls, battery box and centre
post 312..408; top plate 296..312; tiles 288..296; clear column 96..288."""
from brickkit.shapes.rings import pack_angular, ring_cells
from brickkit.shapes.shell import _place_run, pack_cells, woven_disc

BASE_R = 8.0
TABLE_Y = 424
COLUMN_BRICKS = 8
WALL_IN = 6.6
CENTRE = {(-1, -1), (-1, 0), (0, -1), (0, 0)}
SWITCH_OPENING = {(i, k) for i in range(-2, 4) for k in (2, 3)}   # switch and PF plug hatch
PLUG_OPENING = set()


def stand(model):
    s = model.submodel("stand", "Hover stand")
    disc = ring_cells(BASE_R)
    bottom = woven_disc(s, disc, "stand_base", surface_y=TABLE_Y, caption="Base plate",
                        plate={6: "3666", 4: "3710", 2: "3023b", 1: "3024"})
    y = bottom["top_y"]                                                    # 408
    s.step("Battery box (switch and plug face up)")
    s.place("64228", "battery", (0, y - 96, 60), tag="battery")
    s.step("Centre post")
    for n in range(4):
        s.place("3941", "stand_top", (0, y - 24 * (n + 1), 0))
    wall = ring_cells(BASE_R, WALL_IN)
    for n in range(4):
        s.step(f"Wall ring {n + 1}")
        for i, k, length, axis in pack_angular(wall, offset=n, support=wall):
            _place_run(s, {2: "3004", 1: "3005"}[length], "stand_base", i, k, length, axis,
                       y - 24 * (n + 1), "")
    y -= 96                                                                # 312
    openings = CENTRE | SWITCH_OPENING | PLUG_OPENING
    top = woven_disc(s, disc - openings, "stand_base", surface_y=y, caption="Top plate",
                     plate={6: "3666", 4: "3710", 2: "3023b", 1: "3024"})
    s.step("Centre plates with axle holes")
    for n in range(3):
        s.place("4032a", "stand_top", (0, y - 8 * (n + 1), 0))
    y = top["top_y"]                                                       # 296
    s.step("Tiles")
    for i, k, n, axis in pack_cells(top["cells"], lengths=(4, 2, 1), mode="x"):
        _place_run(s, {4: "2431", 2: "3069b", 1: "3070b"}[n], "stand_base", i, k, n, axis,
                   y - 8, "")
    y -= 8                                                                 # 288
    s.step("Clear column")
    for n in range(COLUMN_BRICKS):
        s.place("3941", "stand_column", (0, y - 24 * (n + 1), 0))
    s.step("Axle through the column")
    s.place("50451", "frame_dark", (0, 236, 0), rot_axle_vertical())       # axle 16: y 76..396
    return s


def rot_axle_vertical():
    from brickkit.ldraw.matrix import rot
    return rot(z=90)
