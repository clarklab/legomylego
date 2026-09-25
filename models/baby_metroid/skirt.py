"""The Coral skirt between the base disc and the dome: three bonded rings (brick, brick,
plate) whose inside clears the hub arms (r >= 9 studs)."""
from brickkit.shapes.rings import pack_angular, ring_cells
from brickkit.shapes.shell import _place_run

R_IN = 9.0
LAYERS = [("brick", 10.0, 32), ("brick", 10.3, 8), ("plate", 10.3, 0)]   # (kind, r_out, origin y)


def skirt(sub, disc_cells):
    below = disc_cells
    for n, (kind, r_out, y) in enumerate(LAYERS):
        cells = ring_cells(r_out, R_IN)
        sub.step(f"Skirt ring {n + 1}")
        parts = {"brick": {2: "3004", 1: "3005"}, "plate": {2: "3023b", 1: "3024"}}[kind]
        for i, k, length, axis in pack_angular(cells, offset=n, support=below):
            _place_run(sub, parts[length], "skirt", i, k, length, axis, y, "skirt")
        below = cells
    return below
