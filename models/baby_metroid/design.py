"""Baby Metroid (prototype stage: dome on a simple ring)."""
from brickkit.shapes.rings import pack_cells, ring_cells
from brickkit.ldraw.matrix import rot

import dome as dome_mod


def build(model):
    main = model.main
    L0 = dome_mod.ring_layers()[0]
    cells = ring_cells(L0.r_out, L0.r_in)
    for i, k, n, axis in pack_cells(cells, (2, 1)):
        part = {2: "3004", 1: "3005"}[n]
        x = (i + (n / 2 if axis == "x" else .5)) * 20
        z = (k + (n / 2 if axis == "z" else .5)) * 20
        main.place(part, "skirt", (x, 0, z), rot(y=90) if axis == "z" and n > 1 else None)
    sub, layers, stats = dome_mod.dome(model, main, base_cells=cells)
    print("dome layers:", [(L.kind, round(L.r_out, 1), round(L.r_in, 1)) for L in layers])
    print("dome stats:", stats)
