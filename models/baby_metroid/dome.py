"""The translucent dome: thin bonded rings with 45-degree slopes, capped by a woven plate
disc, tiles and a 6x6 dish at the apex."""
import math

from brickkit.ldraw.matrix import rot
from brickkit.shapes.rings import cell_center, pack_cells, ring_cells
from brickkit.shapes.shell import Layer, _place_run, build_shell, plan_layers, woven_disc

R = 11.0      # widest outer radius, studs
R0 = 9.2      # radius at the rim where the dome meets the skirt
H1 = 60       # height of the widest point above the rim, LDU
H = 312       # nominal dome height (profile reaches 0 here), LDU
R_CAP = 4.5   # radius where the rings stop and the woven cap takes over


def profile(h: float) -> float:
    if h <= H1:
        t = h / H1
        return R0 + (R - R0) * math.sqrt(max(0.0, 1 - (1 - t) ** 2))
    t = (h - H1) / (H - H1)
    return R * math.sqrt(max(0.0, 1 - t * t))


def ring_layers() -> list[Layer]:
    """Rings from the rim up to the height where the profile reaches R_CAP: bricks where the
    curve is steep, plates where it flattens toward the top."""
    h_cap = H1 + (H - H1) * math.sqrt(1 - (R_CAP / R) ** 2)
    return plan_layers(profile, h_cap, max_step=1.5, closed_top=False)


def dome(model, sub, y_base=0.0, base_cells=None):
    """Build the dome ring by ring directly on `sub` (around whatever is inside it)."""
    layers = ring_layers()
    stats = build_shell(sub, layers, "dome", y_base=y_base, base_cells=base_cells)
    y = stats["top_y"]
    cap_cells = ring_cells(layers[-1].r_out)
    cap = woven_disc(sub, cap_cells, "dome", surface_y=y, caption="Close the top")
    y = cap["top_y"]
    # tiles over the whole cap except the centre 2x2, which is raised two plates to carry the
    # dish; the dish rim then rests on the tiles instead of on studs
    centre = {(-1, -1), (-1, 0), (0, -1), (0, 0)}
    sub.step("Tiles")
    tiles = 0
    for i, k, n, axis in pack_cells(cap["cells"] - centre, lengths=(2, 1), mode="x"):
        _place_run(sub, {2: "3069b", 1: "3070b"}[n], "dome", i, k, n, axis, y - 8, "")
        tiles += 1
    sub.step("Dish")
    sub.place("3023b", "dome", (0, y - 8, -10))
    sub.place("3023b", "dome", (0, y - 8, 10))
    sub.place("3023b", "dome", (-10, y - 16, 0), rot(y=90))
    sub.place("3023b", "dome", (10, y - 16, 0), rot(y=90))
    sub.place("4285b", "dome", (0, y - 16 - 8, 0))
    stats["parts"] += cap["parts"] + tiles + 5
    return sub, layers, stats
