# brickkit — model authoring guide

brickkit turns a model written in Python into a real, checked LEGO build: an LDraw file,
a verification report, parts lists, renders (and, as they land, an instruction booklet, a
build video and a viewer page). The engine knows nothing about any particular model.

## Setup
```bash
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m brickkit fetch          # LDraw library, LDCad snap data, Rebrickable catalogue -> .cache/
.venv/bin/python -m pytest -q               # engine tests
```
Blender 5.x must be at `/Applications/Blender.app` (override with `BRICKKIT_BLENDER`).
The cache location can be overridden with `BRICKKIT_CACHE` (useful in git worktrees).

## Commands
| Command | What it does |
|---|---|
| `brickkit new SLUG --name "Name"` | scaffold `models/SLUG/` (model.toml + design.py) |
| `brickkit build SLUG` | run design.py, write `out/SLUG.mpd` |
| `brickkit verify SLUG` | run all checks, write `out/report.{json,html}`; exit 1 on any FAIL |
| `brickkit bom SLUG` | `out/parts.csv`, `out/bricklink_wanted.xml`, `out/pick_a_brick.csv` |
| `brickkit all SLUG` | build + verify + bom, then each colourway (variant) |
| `brickkit render SLUG [--views a,b] [--size N] [--samples N] [--pose T] [--lights] [--variant V]` | Blender stills in `out/renders/` |
| `brickkit find "words" [--color C]` | search real LEGO parts by name, ranked by how many sets used them in that colour |

Views: `front, three_quarter, three_quarter_right, side, back, top, low`.

## Units and axes
LDraw units (LDU): 1 stud = 20, 1 plate = 8, 1 brick = 24, 1 LDU = 0.4 mm. **-Y is up.**
A part placed at `y=0` has its top face at `y=0` (studs poke up to `y=-4`); a brick stacked on
it goes at `y=-24`, a plate at `y=-8`. A 2x4 brick `3001` spans x ±40, z ±20 around its origin.
"Front" is -Z. Rotations: `from brickkit.ldraw.matrix import rot` → `rot(x=, y=, z=)` degrees,
applied X then Y then Z.

## model.toml
```toml
[model]
name = "Baby Metroid"
design = "design.py"

[palette]            # role -> real colour name (Rebrickable/BrickLink naming)
dome = "Trans-Light Blue"
fang = "White"

[variants.sable]     # optional colourways: override any roles
title = "Sable"
coat = "Reddish Brown"

[checks]
enabled = ["real_elements", "connections", "collisions", "buildability", "stability",
           "mechanism", "electrics", "technique"]
[checks.stability]
min_margin = 0.25
min_tilt_deg = 10
[checks.connections]
allow_separate_tags = []   # tags of parts allowed to be loose (e.g. a separate accessory)
```

## design.py
```python
from brickkit.ldraw.matrix import rot, translate

def build(model):
    leg = model.submodel("leg", "Leg")          # sub-assembly (built once, used many times)
    leg.place("3005", "body")                   # part, palette role or colour, pos, rot
    leg.step("Add the foot")                    # new instruction step (optional caption)
    leg.place("3024", "body", (0, 24, 0), tag="foot")

    main = model.main
    main.place("3001", "body")
    main.step()
    main.use(leg, (-30, 24, 0), tag="leg_l")    # place a sub-assembly
    main.use(leg, (30, 24, 0), rot(y=180), tag="leg_r", insert=(0, 1, 0))
```
- Part names are LDraw file names without `.dat` (aliases like `4073` are followed to `6141`).
- `tag=` labels a placement or sub-assembly. Tag paths join with `/` (e.g. `leg_l/foot`) and
  are used by mechanisms, lights and cables.
- `insert=(dx, dy, dz)` tells the buildability check which way a part slides in when it isn't
  simply pushed along its studs/pins (e.g. slid in sideways under an overhang).
- Keep steps small (1–8 parts), use sub-assemblies for anything repeated or built apart.

### Mechanisms
```python
model.moving_group("flap", "flap")                     # group name -> tag
model.pose = lambda t: {"flap": hinge_matrix(t)}       # t in [0,1] -> {group: 4x4 WORLD transform}
model.gear_pair("gear_a", "gear_b", "spur")            # spur | worm | bevel ; tags of the gears
model.extra_checks.append(lambda ctx: [])              # return issue dicts {"problem": "..."}
```
A pose transform is applied on top of each part's rest position (`M' = T @ M`). Build 4x4s
with `brickkit.ldraw.matrix.transform(pos, rot3)` / `translate`, e.g. rotation about a hinge
axis through point P: `translate(*P) @ R @ translate(*-P)`. The mechanism check sweeps 24 poses,
fails on collisions or on the model falling apart, and checks gear spacing (LEGO gears are
module 1: pitch radius = 1.25 LDU per tooth).

### Electrics and lights
```python
model.light("nucleus_1", "nucleus_l/led", color="#FF3A1A", power=1.5)
model.cable("led_run", "battery/box", "nucleus_l/led", length=1250, route=[(x, y, z), ...])
model.glow("nucleus_l", strength=2.0)     # parts under this tag glow in `--lights` renders
```

## The checks
| Check | Fails when |
|---|---|
| real_elements | a part/colour pair LEGO never made (suggests substitutes); warns when rare (<3 sets or none since 2016) |
| connections | any part/sub-assembly not attached (studs, pins, axles, clips, hinges via LDCad snap data) |
| collisions | two parts overlap by more than ~0.5 LDU |
| buildability | a part can't slide into place in its step, or a step leaves loose pieces |
| stability | centre of mass outside the footprint of the lowest parts, or tips over under 10° |
| mechanism | moving parts collide / disconnect across the pose sweep; gear spacing wrong |
| electrics | cable runs longer than the cable |
| technique | warnings: clips on transparent parts, moving transparent parts, uncertified geometry |

## Workflow loop
1. `brickkit find` to pick parts that exist in your colours (prefer ≥3 sets since 2016).
2. Write/extend a sub-assembly in `design.py`.
3. `brickkit all SLUG` → fix every FAIL.
4. `brickkit render SLUG --size 700 --samples 48` → look at the PNGs, compare with references.
5. Record decisions and any deviations in `models/SLUG/NOTES.md`. Commit.

## Shape helpers
`brickkit.shapes.rings`: `ring_cells(r_out, r_in)`, `pack_cells(cells, lengths, offset, mode)`
(bonded 1xN runs), `exposed(lower, upper)` (step cells for slopes, with outward direction),
`shell_layers(profile, heights, thickness)` (shells of revolution).
