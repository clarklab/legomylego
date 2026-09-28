"""The Caldwell County Courthouse, Lockhart, Texas (1894, Alfred Giles), as a LEGO display
model about 45 cm tall on a 38 x 38 stud base. Its four clocks are real: quartz clock
inserts (not LEGO) sit behind the red dials, and the dome lifts off to set them.

Units: LDU (stud 20, plate 8, brick 24), -Y up, the front (with the portico and the flags)
faces -Z. The base's top is at y = 0. Modules: base.py (lawn, walks, trees, flagpoles),
walls.py (the two-storey walls), roofs.py (roof deck, cornice, mansards, attics, pavilion
towers), portico.py, tower.py (columns, belfry, lift-off dome) and clock.py (the clock stage
and the clock inserts).

Moving groups: `tower_top` (the dome, lifted straight off) and the eight hands
(`hour_s`/`minute_s`... one pair per side). pose(t): the hands turn from 10:10 to 12:10 and,
from t = 0.35, the top lifts 200 LDU (8 cm)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from brickkit.ldraw.matrix import rot, transform, translate  # noqa: E402

import base  # noqa: E402
import clock  # noqa: E402
import portico  # noqa: E402
import roofs  # noqa: E402
import tower  # noqa: E402
import walls  # noqa: E402
from kit import use_M  # noqa: E402

LIFT = 200.0
STAGE_M = translate(0, tower.YC, 0)


def _roof(model):
    s = model.submodel("roof", "Roof deck and cornice")
    roofs.deck_batch().emit(s, roofs.DECK_PHASES, {
        "deck1": "The roof deck: a tan ring over the walls, big plates inside",
        "deck2": "A second layer: red round the edge",
        "cornice": "The cornice: red inverted slopes out over the walls",
        "cornice2": "Red plates on the cornice", "cornice3": "Red tiles on its edge"},
        per_step=10, reach=200)
    return s


def pose(t: float) -> dict:
    out = clock.hand_pose(t, STAGE_M)
    u = min(max((t - 0.35) / 0.65, 0.0), 1.0)
    u = u * u * (3 - 2 * u)
    out["top"] = translate(0, -LIFT * u, 0)
    return out


def build(model):
    model.meta["mechanism_name"] = "Clock and lift-off dome"
    model.meta["mechanism_labels"] = ["10:10, dome on", "12:10, dome lifted"]
    model.meta["hero_open_elevation"] = 30
    main = model.main

    main.step("The base")
    base.base_batch().emit(main, [["bottom"], ["top"], ["walks"]], {
        "bottom": "The base: big plates", "top": "Lawn and walks",
        "walks": "Tiles on the walks"}, per_step=10, reach=200)

    col = tower.column(model)
    for n, (x, z) in enumerate(tower.COLUMNS):
        main.step("Four columns in the middle carry the tower" if n == 0 else "")
        main.use(col, (x, 0, z), insert=(0, -1, 0))

    pav = walls.corner_pavilion(model)
    wing = walls.wing(model)
    cen = walls.centre_pavilion(model)
    for a in (0, 90, 180, 270):
        R = transform((0, 0, 0), rot(y=a))
        main.step("The walls: a corner pavilion, two wings and a centre pavilion on each "
                  "side" if a == 0 else "")
        use_M(main, pav, R, insert=(0, -1, 0))
        use_M(main, wing, R, insert=(0, -1, 0))
        use_M(main, wing, R @ transform((-160, 0, 0)), insert=(0, -1, 0))
        use_M(main, cen, R, insert=(0, -1, 0))

    main.step("Lower the roof deck onto the walls")
    main.use(_roof(model), (0, 0, 0), insert=(0, -1, 0))
    roofs.upper_roofs().emit(main, roofs.UPPER_PHASES, roofs.UPPER_CAPTIONS, per_step=8)
    pt = roofs.pavilion_tower(model, roofs.oculus(model))
    for a in (0, 90, 180, 270):
        main.step("A pavilion tower on each corner" if a == 0 else "")
        use_M(main, pt, transform((0, 0, 0), rot(y=a)), insert=(0, -1, 0))

    main.step("The belfry, over the four columns")
    main.use(tower.belfry(model), (0, 0, 0), insert=(0, -1, 0))
    face = clock.clock_face(model)
    stage = clock.clock_stage(model, face)
    main.step("The clock stage")
    use_M(main, stage, STAGE_M, insert=(0, -1, 0))
    main.step("Set the dome on: it rests on the four corner studs and lifts off again")
    main.use(tower.tower_top(model), (0, tower.TOP_Y, 0), tag="tower_top", insert=(0, -1, 0))

    portico.build(model, main)

    base.shrubs().emit(main, [["shrubs"]], {"shrubs": "Shrubs along the walls"},
                       per_step=12, reach=300)
    tree = base.tree(model)
    for x, z in base.TREES:
        main.step("Live oaks on the side lawns")
        main.use(tree, (x, 0, z), insert=(0, -1, 0))
    pole = base.flagpole(model)
    for n, (x, z, colour, tag) in enumerate(base.FLAGS):
        main.step("Three flagpoles in front: slide a flag down each" if n == 0 else "")
        main.use(pole, (x, 0, z), insert=(0, -1, 0))
        main.place("4495b", colour, (x, base.FLAG_Y, z), rot(y=90), tag=tag,
                   insert=(0, -1, 0))

    model.moving_group("top", "tower_top", lifts_off=True)
    for f in clock.FACES:
        model.moving_group(f"hour_{f}", f"hour_{f}")
        model.moving_group(f"minute_{f}", f"minute_{f}")
    model.pose = pose
