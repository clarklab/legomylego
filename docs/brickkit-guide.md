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
| `brickkit bom SLUG` | `out/parts.csv`, `out/bricklink_wanted.xml`, `out/pick_a_brick.csv`, `out/price_estimate.md` and `out/price.json`: live BrickLink prices dated today when API keys are in `~/.config/brickkit/bricklink.env` (see `brickkit/bom/live_price.py`), else a rough range from `brickkit/data/price_bands.json` |
| `brickkit all SLUG` | build + verify + bom, then each colourway (variant) |
| `brickkit render SLUG [--views a,b] [--size N] [--samples N] [--pose T] [--lights] [--variant V]` | Blender stills in `out/renders/` |
| `brickkit booklet SLUG [--no-render]` | instruction booklet `out/booklet.pdf` (pictures in `out/booklet/`) |
| `brickkit viewer SLUG` | export `site/models/SLUG/` (GLB + model.json + files) for the viewer site |
| `brickkit turntable SLUG [--preview]` | `out/turntable.mp4`: a 12 s photoreal (Cycles) orbit with the mechanism and lights working, muted and seamless; the site plays it where WebGL is missing (`meta["turntable"]`: `program` tap/swing/lights, `cycles`, `taps`) |
| `brickkit quick SLUG [--preview] [--set PRESET\|random] [--surface S] [--room R] [--light L] [--seed N] [--seconds S] [--stills F,F] [--layout\|--no-layout] [--remix]` | `out/SLUG-1080x1920.mp4` (+ `quick_poster.jpg`): Quick Bricks, a 14 s vertical (1080×1920, 60 fps) photoreal build video of a small model for TikTok and Instagram, made to loop (config `[quick]`; see Video) |
| `brickkit sizzle [SLUG ...] [--stills F,F] [--preview]` | `showreel/sizzle.mp4`: one quick brand reel of several models cut on the music's beats, from their showreels' footage (config `showreel/sizzle.toml`; see Video) |
| `python tools/hero.py SLUG` | hero stills: `out/hero/`, `out/hero_lit/` (lights), `out/hero_open/` (pose 1) |
| `brickkit find "words" [--color C]` | search real LEGO parts by name, ranked by how many sets used them in that colour |
| `brickkit find "words" --minifig head\|torso\|legs\|any [--color C] [--ldraw]` | search minifigure components as sold (one row per colour): sets, last year, Rebrickable number, the LDraw file that models it (`~` the same print on other arms, `plain` an unprinted assembly), BrickLink number, `E` if LEGO has an element ID; `--ldraw` only those LDraw can draw |
| `brickkit figs "words"` | whole Rebrickable minifigures by name (e.g. "sea captain"), in most sets first, with their parts |

Views: `front, three_quarter, three_quarter_right, side, back, top, low`, or `close:TAG`: a
close-up framing the parts under a tag (e.g. `close:captain_nemo`, one minifigure), written as
`close_TAG.png`; the rest of the model stays in the scene.

## Units and axes
LDraw units (LDU): 1 stud = 20, 1 plate = 8, 1 brick = 24, 1 LDU = 0.4 mm. **-Y is up.**
A part placed at `y=0` has its top face at `y=0` (studs poke up to `y=-4`); a brick stacked on
it goes at `y=-24`, a plate at `y=-8`. A 2x4 brick `3001` spans x ±40, z ±20 around its origin.
"Front" is -Z. Rotations: `from brickkit.ldraw.matrix import rot` → `rot(x=, y=, z=)` degrees,
applied X then Y then Z.

## model.toml
```toml
[model]
name = "Baby Metroid Lamp"
design = "design.py"

[palette]            # role -> real colour name (Rebrickable/BrickLink naming)
dome = "Trans-Light Blue"
fang = "White"

[variants.sable]     # optional colourways: override any roles
title = "Sable"
coat = "Reddish Brown"

[booklet]           # optional text for the instruction booklet
subtitle = "One line under the title on the cover"
intro = "A paragraph for 'Before you start' and 'About this model'"
you_will_need = ["Things besides the bricks, e.g. batteries"]
notes = ["Extra tips"]
works = [{ title = "Fangs that bite", text = "...", image = "hero_open/hero.png" }]  # under out/
page = "other_slug/#section"   # its web page, when it lives on another model's page

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

```python
model.moving_group("body", "*", exclude={"stand", "hub"})  # catch-all: every other part
model.allow_contact("tube", "battery", "presser pushes the button")  # may touch/overlap
model.captive("tube", "slides in the stand's top plate")   # held by a guide, not studs
```
A catch-all group moves everything not in another group and not under an excluded tag (a whole
body sliding on a fixed stand). `allow_contact` exempts pairs of tagged parts from the collision
and mechanism checks, for contact the part geometry can't show (a presser on a spring-loaded
button, a push rod riding on a lever). `captive` tells the buildability check that parts under
a tag are held without studs (a slider in its guide); the whole model must still join them up.
The Baby Metroid Lamp's tap mechanism (`models/baby_metroid/core.py`, `stand.py`) uses all three.

### Electrics and lights
```python
model.light("nucleus_1", "nucleus_l/led", color="#FF3A1A", power=1.5,
            offset=(0, 0, -70))            # render light 70 LDU along the part's -Z
model.cable("led_run", "nucleus_l/led", "battery", length=1000, route=[(x, y, z), ...])
model.glow("nucleus_l", strength=2.0)     # parts under this tag glow in `--lights` renders
model.extra("62501c01", "led", 2, "8870 light unit")   # on the parts lists, not placed in 3D
```
Cable ends are tag paths (a part's tags joined by `/`, matched at the end). The electrics check
adds up the straight segments lamp → route points → end and compares with `length` (LDU).
Use `model.extra` for bought items whose geometry is only partly placed (a light unit's lead
and plug); `data/part_map.json` sets `"bom": false` on the placed head so nothing counts twice,
and `"bricklink_type": "S"` for items BrickLink sells as sets.

### Minifigures
```python
from brickkit.model.minifig import grip_up
fig = model.minifig("captain_nemo", (-40, 0, -30), title="Captain Nemo",
                    head=("3626bpr0251", "Yellow"),         # Rebrickable numbers, as sold
                    torso=("973c03h01pr0049", "Black"),     # colour: the torso's
                    legs=("970c03", "Black"),               # colour: the hips'
                    hair=("92081", "Dark Bluish Gray"),     # or hat=; ordinary parts
                    accessory=dict(part="64644", color="Pearl Gold", hand="right"),
                    pose=dict(arm_r=45, head=-8))           # degrees
```
LEGO, Rebrickable and BrickLink sell a minifigure's body as three **assemblies**, numbered per
print and colour combination: a head (Rebrickable `3626cprNNNN`), a torso with its arms and
hands (`973cAAhBBprNNNN`: `AA`/`BB` are Rebrickable's minifig colour codes for the arms and
hands, e.g. `01` Yellow, `05` Dark Blue; BrickLink `973pbNNNNc01`) and hips with legs
(`970cAA...`, `AA` the legs' colour; BrickLink `970c00` when hips and legs match, else
`970c` + the legs' BrickLink colour id, printed `970c00pbNNNN`). LDraw models the pieces:
torso `973` (prints `973pXXX`), arms `3818`/`3819`, hands `3820`, hips `3815b`, legs
`3816c`/`3817c` (prints), head `3626c` (prints `3626cpXXX`/`3626bpXXX`), with "shortcut"
files for many assemblies (`76382pXXX` a torso with arms and hands, `73200bpXX`/`21019bpXX`
hips and legs). **Short legs** (children, short characters) are one piece in every system:
Rebrickable `41879a` (prints `41879aprNNNN`), BrickLink `41879` (`41879pbNNN`), LDraw
`41879a` (prints `41879apXX`): give them as `legs=("41879a", "Dark Bluish Gray")`.

- **Catalogue** (`catalog/minifig.py`, `catalog/xref.py`): the only cross-reference between
  the systems that ships with the libraries is LDraw's `!KEYWORDS Rebrickable ...,
  BrickLink ...` header lines; brickkit indexes them (`.cache/ldraw_xref.pkl`) and reads a
  shortcut's sub-files for the pieces and colours of an assembly. A component is given by its
  Rebrickable number (or an LDraw file or BrickLink number the headers cite), alone (its usual
  colour) or as `(number, colour)`. `catalog.rb_part` / `bl_part` also use the headers for
  any printed part whose LDraw name Rebrickable doesn't know (`3626cp01` -> `3626cpr0001`).
  Minifigure parts sit in the figures' own Rebrickable inventories (`fig-NNNNNN`); with the
  `minifigs` and `inventory_minifigs` tables (`brickkit fetch`) every part's set count and
  last year count the sets its figures come in.
- **Geometry** (`model/minifig.py`): the figure's origin is on the plate top, midway between
  the two studs its feet go on (x = ±10: `at` sits where the centre of a 1 x 2 plate lying
  along X would). Standard LDraw/LDCad minifig geometry: feet 28 below
  the hip pins, hips 12 above them, torso 32 tall, the head on the neck stud; the body stands
  1.2 LDU behind its foot holes; arms hang on the shoulder pins tilted out 9.79 degrees and
  swing about them (`arm_r`, `arm_l`: + forward), hands sit on the wrists at 45 degrees and
  twist (`hand_r`, `hand_l`), legs swing on the hip pins (`leg_r`, `leg_l`: 90 sits), the head
  turns (`head`: + to the figure's left). On short legs (24 LDU tall, hip studs on top, foot
  holes straight under the body) the torso sits 16 LDU lower and the legs don't move
  (`leg_r`/`leg_l` raise an error). Headwear goes on the head stud. An accessory's
  3.2 mm bar (LDCad) is laid in the hand's clip: by default the middle of its thinnest stretch
  (a bottle by its neck), upright side (LDraw's -Y) on the thumb's side; `grip`, `spin`,
  `flip`, `bar` adjust it. `grip_up()` is the arm swing that stands a held bar up (leaning out
  with the shoulder's 9.8 degrees).
- **What is bought**: the torso and legs are **kits** (`Submodel.kit`, a sub-assembly of the
  LDraw pieces named `NAME_torso` / `NAME_legs`); the head is a placement with `buy=`. Kits
  are not built: the instructions skip their steps and show them like parts, pictured whole;
  their pieces are joined by `kit` connections and may touch each other; buildability pushes
  the whole kit on. Short legs, like the head, are one placement bought as itself. Headwear fits over the head (`Submodel.fits`, `Model.fits`: the two may
  overlap and the hair slides over the head). Each figure is built in its own section: legs,
  torso, head, headwear, accessory.
- **Parts lists**: a component is one line (`parts.csv` column `minifig`; BrickLink number in
  the wanted list; its LEGO element ID, when there is one, in the Pick a Brick list) instead
  of its LDraw pieces; prices use `price_bands.json` `minifig` bands. A component whose
  BrickLink number no LDraw header gives takes it from `data/minifig_bricklink.json`
  (Rebrickable number -> BrickLink number, checked on bricklink.com by hand), else it is
  left out of `bricklink_wanted.xml` (the command says so) and listed by its Rebrickable
  number. The build and bom summaries and
  `price.json` count the minifigures.
- **real_elements** checks each component as sold (that print on that colour: set count,
  last year, the usual rare warning), and notes (severity `info`) prints drawn as **stand-ins**
  and missing BrickLink numbers. A print LDraw has no model of (and no LDraw model of the same
  print on other arms, matched by Rebrickable's print number and description) is drawn with
  plain pieces in its colours; the build command lists them. Prefer prints LDraw models
  (`find --minifig ... --ldraw`).

### Real LEGO parts LDraw has no model of
Some real elements have no LDraw file at all (the Series 8 Diver's brass helmet, `10165c01`).
brickkit draws them with its **own approximate 3D model**, a BFC-certified LDraw file named
after the part's real number under `brickkit/data/ldraw/parts/` (made by
`tools/approximate_parts.py`, with any LDCad snaps in `brickkit/data/shadow/parts/` and a
mass in `data/masses.json`), listed in `brickkit/data/approximate.json` (name, `bricklink`
number if it differs, what the `shape` gets right and leaves out).
```python
fig = model.minifig("diver", at, head=..., torso=..., legs=...,
                    hat=("10165c01", "Pearl Gold"))      # placed like any part
```
- Unlike a hardware stand-in it **is** LEGO: it stays on `parts.csv` (note "approximate 3D
  model"), the BrickLink wanted list and Pick a Brick under its real number, and
  `real_elements` checks it like any part (set count, year, rare warning), adding an `info`
  item that its shape is approximate; the build command lists it.
- The library's own file wins if LDraw ever adds the part. The MPD embeds the model, so
  Studio and LDCad show it.
- `catalog.is_approximate(part)` tells them apart. A custom file that is in neither
  `hardware.json` nor `approximate.json` fails `real_elements`.

### Non-LEGO hardware
Bought items that are not LEGO elements (a quartz clock insert) go in the model as **stand-in
parts**: simple LDraw-style meshes under `brickkit/data/ldraw/parts/` (made by
`tools/hardware_parts.py`, BFC-certified), which the library finds like any other part. They
show in renders, the booklet and the viewer, and the collision check sees them, so the model
really has room for the item. `brickkit/data/hardware.json` lists each stand-in's shopping
details: name, description (the sizes that fit), rough `price` [low, high] in USD each and
`where` to buy; a `part_of` entry (a clock's hands) is counted with its item.
```python
sub.place("bk-clock-insert-35mm", "Black", pos, R, tag="clock_n", insert=(0, -1, 0))
model.press_fit("clock_n", "rests in its cradle behind the ring")   # held without studs
model.hardware("Spare button cell SR626SW", 4, "for the clocks", (1, 3), "any shop")  # not placed
model.moving_group("top", "tower_top", lifts_off=True)            # the pose lifts it away
```
- Stand-ins are not on the LEGO lists (`parts.csv`, the BrickLink and Pick a Brick files, the
  piece count) and `real_elements` skips them. They go on `out/hardware.csv`, in a "Not LEGO"
  section of `price_estimate.md`, under `hardware` in `price.json`, in the booklet's "You will
  need" box and in the viewer's `model.json`. The MPD embeds their files, so Studio and LDCad
  show them.
- `model.press_fit(tag, note, reach=2.0)`: parts under the tag are held by friction by the
  parts they touch (within `reach` LDU, found with unshrunk meshes by nudging the part along
  its own axes). The connections, buildability and mechanism checks count each touch as a
  `press` connection. Give the placement an `insert=` direction (how it goes in); the parts
  it slides along must not overlap it.
- `lifts_off=True` on a moving group: the mechanism check lets the group come away from the
  model in the pose (a lift-off lid or tower top), as long as it stays in one piece and
  collides with nothing on its way.

## The checks
| Check | Fails when |
|---|---|
| real_elements | a part/colour pair LEGO never made (suggests substitutes); warns when rare (<3 sets or none since 2016) |
| connections | any part/sub-assembly not attached (studs, pins, axles, clips, hinges, balls via LDCad snap data) |
| collisions | two parts overlap by more than ~0.5 LDU |
| buildability | a part can't slide into place in its step, or a step leaves loose pieces |
| stability | centre of mass outside the footprint of the lowest parts, or tips over under 10° |
| mechanism | moving parts collide / disconnect across the pose sweep; gear spacing wrong |
| electrics | cable runs longer than the cable |
| technique | warnings: clips on transparent parts, moving transparent parts, uncertified geometry, locking hinges set between their clicks, parts sitting on studs their snap data has no holes for (a stud another part already fills doesn't count) |

Connection points come from the LDCad shadow library. When a part has none there (for example
74611 Plate Round 8 x 8 with hole, whose underside would otherwise connect to nothing), add a
file with the same name under `brickkit/data/shadow/parts/` (or `parts/s/`) holding
`0 !LDCAD SNAP_*` lines in the part's own frame. These overlay files are read after the
library's file for that part, so they add to it; they never remove its snaps.

**Ball joints.** LDCad describes balls and their sockets as `SNAP_GEN [bounding=sph R]`
(towballs, Technic balls). A ball turns in its socket, so these connect at any orientation:
same centre (within 1 LDU), same radius (within 0.6), same group, opposite genders. They are
reported as `ball` connections, and the buildability check treats them like clips and hinges
(the socket's jaws flex as the ball pops in, so the socket never blocks the part carrying the
ball). Overlays add the Technic ball snaps LDCad lacks: 53585 (Technic Ball Joint with through
axle hole) gets the `techBallJnt` group its twin 32474 has, and 67696 (Brick 2 x 2 with wide
ball socket, the football figures' shoulder joint) gets its socket, where 92013's is. The
67696 socket's jaws leave a slot in the brick's own x-y plane: the ball's axle can swing
freely in that plane, only about 25 degrees across it.

**Window glass.** Glass that clicks into its frame is matched through LDCad snaps too:
60601 meets 60592 with a generic snap (SNAP_GEN), and the overlay
`brickkit/data/shadow/parts/60602.dat` gives 60602 (glass for 60593, Window 1 x 2 x 3 Flat
Front) the fingers its frame's glazing slot expects (the complementary sequence). Generic snaps
count as clicking in for the buildability check, like clips and hinges; give the glass
`insert=` pointing to the side it goes in from.

**Finger hinges** (`SNAP_FGR`: hinge bricks, click hinges, locking hinge plates). As in LDCad,
a finger sequence is centred on the snap's position unless the meta says `[center=false]`;
fingers and gaps alternate from `genderOfs`. Two halves on the same line engage when their
extents overlap by 1 LDU or more and their fingers interleave: no finger of one may sit on a
finger of the other by more than 1.5 LDU. So a pair works whichever way round its halves face
(44301b's single finger in 54657's pair, 44567b on 60471), at any angle about the hinge line,
and two single fingers in one place don't. The joint doesn't model click steps: locking
hinges hold only at their clicks (22.5-degree steps, by builders' accounts), so keep their
angles to those: the technique check warns when a locking hinge (LDCad group `lckHng`) is set
more than 1 degree off a click, measuring the turn of one half's frame from the other's about
the hinge line (`[checks.technique] click_step`, `click_tolerance`, `click_groups` change
that). Bar-and-clip and the friction hinges hold anywhere. Hinge pairs also have a
range the collision check enforces: 3937 + 6134 open one way only, 0 to 90 degrees; a 1 x 4
swivel (2429 + 2430) folds one way only; locking hinge plates and bar-and-clip swing about
+-90 and +-120 degrees.

**Angled frames.** Connectors are bucketed by their line (direction to 0.001, foot of the line
to 0.5 LDU). A connector sitting exactly on a bucket boundary, as feet can in frames made of
several 45- or 30-degree turns, goes in both buckets, so float noise can't split a pair.

The overlay `50747.dat` (Windscreen 6 x 6 x 3 Canopy Half Sphere with Dual 2 Fingers) gives
the canopy's two pairs of fingers the `lckHng` group LDCad's file leaves out, so it clicks onto
single-finger click hinges (44567b, 44301b, 30383) as the real part does.

The overlays `43722a/43723a/43722b/43723b.dat` (Wedge Plate 3 x 2) give those wedge plates the
stud holes LDCad's library lacks. The technique check finds gaps like that one: it warns when a
part with studs on top but nothing that connects through its underside sits on another part's
studs.

**Swivel hinges.** The 1 x 4 swivel plate is sold assembled (73983), but LDraw draws it
straight; to set it at an angle, place its halves 2429 (base) and 2430 (top) separately, turned
about the pivot. The parts list counts each 2429 as one 73983 and leaves 2430 out
(`data/part_map.json`). The swivel folds one way only.

## Workflow loop
1. `brickkit find` to pick parts that exist in your colours (prefer ≥3 sets since 2016).
2. Write/extend a sub-assembly in `design.py`.
3. `brickkit all SLUG` → fix every FAIL.
4. `brickkit render SLUG --size 700 --samples 48` → look at the PNGs, compare with references.
5. Record decisions and any deviations in `models/SLUG/NOTES.md`. Commit.

## Video
`brickkit video SLUG` makes `out/SLUG-1080x1080.mp4` (every finished video is named for its model
and its size, so no two share a name): a square 1080×1080, 30 fps showreel of the model
(H.264 + AAC, under 40 MB) and `out/video_poster.jpg`. Everything on screen comes from the
model: the parts list, `out/report.json`, the booklet, the poses, lights and colourways.
It needs Blender, ffmpeg and Playwright's Chromium (`.venv/bin/python -m playwright install
chromium`). A full render takes roughly an hour of GPU time per model; iterate with `--preview`.

| Flag | What it does |
|---|---|
| `--preview` | 540×540, low samples, 15 fps → `out/video_preview.mp4` (iterate with this) |
| `--segments build,scan` | only those segments → `out/video_build+scan.mp4` |
| `--no-render` | no Blender: compose from the plates already rendered (grey where missing) |
| `--stills 120,480` | write single composed frames to `out/video_frames/<q>/stills/`, no video |
| `--cold-open SCENE` | try a cold open (`sunset_road`, `night_desk`, `deep_sea`) for this run, tagged like `--theme` (`out/video_cold_open...`); `--segments cold_open,open` renders just it and the cut into the reel |
| `--scratch DIR` | write the run's work and outputs under `DIR` (the model's `out/` is only read): previews of a model someone else is working on |
| `--theme NAME` | try another theme for this run (model.toml's theme and its overrides left out): writes `out/video_NAME[...].mp4` and `out/video_frames/<q>@NAME/` (stills there too), never the model's own video, poster or plates; with `--no-render` it composes over the model's rendered plates read-only, keeping their tempo and backdrop so they line up |
| `--no-audio` | no music or sound effects |
| `--force` | re-render cached plates; `--engine cycles` / `--device cpu` as for stills |

**Segments** (beat-aligned; ones that don't apply are skipped):

| Segment | Beats | Shows | When |
|---|---:|---|---|
| cold_open | seconds + 1 | the model performs in a set of its own before anything else (a figure on a sunset road, a tap lamp on a desk at night, a vessel gliding under the sea), in two or three shots, then a hard cut to black for a beat and straight into the open (below) | `[video.cold_open]` |
| open | 6 | a brick drops and snaps, stud wipe, REAL LEGO PIECES. / CHECKED BY COMPUTER. | always |
| title | 8 | the name in kinetic type over a transparent Cycles hero, piece counter, one row of stats | always |
| build | 36 | the time-lapse build growing up from the table (parts by the height of their lowest point, outward from the centre, each waiting for something to stand on or connect to, dropping a short way into place); one orbiting shot per height band; HUD: pieces placed, height, progress | always |
| scan | 12 | a scan line sweeps the model: x-ray of its LDraw edges and connection points; the eight checks tick in with their numbers | always |
| mechanism | 12 | `model.pose`: build pose → 0 → 1 → back, with callouts tracked on real parts and a gauge | pose + groups |
| lights | 8 (+2) | the set goes dark, the lights switch on with a bloom flash; optionally a tap presses the mechanism as they do, and a second tap switches them off | lights / glow |
| lift | 6 | everything but `exclude_tag` rises and hovers | `[video] lift` |
| colourways | 4 per colourway | wipes between colourways that share the parts, with swatches | variants |
| booklet | 12 | the printed booklet: its real cover opens, a thumb-flip through the step pages (motion-blurred) lands on a step spread, then loose step sheets are dealt into a fan (from every colourway's booklet if there are any) | `out/booklet.pdf` |
| companions | 10 each | a smaller build featured with the model (e.g. a kids' version): its eyebrow and heading, its turntable loop on a card, chips (pieces, steps, about what it costs on Pick a Brick), then to scale: the model's cut-out with the companion dropping in beside it, each height measured | `[[companions]]` with `video = true` |
| outro | 8 | logo, `bricks.superfun.games/m/SLUG`, the small print and the model's notice | always |
| coda | seconds | the last moments: the model in the dark sea and a giant squid about its size coming out of the murk at it, fading to black as it closes in | `[video.coda]` |

**Config** in model.toml (all optional; `model.meta["video"]` from design.py wins key by key):
```toml
[video]
theme = "tape"                  # brand (default) | scan | tape | playful | grindhouse | abyss
beats = { build = 28 }          # segment lengths in beats
skip = ["scan"]                 # leave segments out
facts = ["1:1 scale"]           # extra title chips (words from the model's own docs)
default_title = "Black"         # name of the default colourway (else [model] palette_title)
build_order = "ground_up"       # or "instructions": follow the booklet's order instead
sections = [[1, "Base"], ["Layer 1 (", "Dome"]]   # named parts of the build (step or caption
                                # start); ground-up bands are named after the one most of
                                # their parts belong to, when it's at least 60% of them
lift = { exclude_tag = "stand", height = 80 }
lift_label = "Lifts off its stand"
lights_label = "Nuclei light up"
lights_tap = true               # the mechanism presses as the lights switch on (a tap lamp)
lights_off = true               # a second tap switches them off again (lights_off_label)
outro_small_print = false       # the outro without its small print (the disclaimer and the
                                # model's notice); the URL stays
drop = 24                       # LDU a part falls as it lands
[video.theme_overrides]         # any theme token, e.g. accent = "#FF3EA5"

[video.cold_open]               # opt-in: the reel opens on the model performing
scene = "sunset_road"           # a two-lane road running into a low sun
seconds = 7                     # the performance (rounded to beats; then a beat of black)
motion = "performance"          # meta["performance"] (else, or "pose": model.pose swinging 0..1)
spin_turns = 1.5                # the whole figure turns about its pivot, in three lurches
hide_tags = ["stand"]           # parts left out (added to performance_info's)
# optional: sun_elevation = 2.4, sun_size = 1.4 (deg), cycle = 2.5 (s), rev_tag = "saw",
# letterbox = 0.09; the set's look (defaults in render/blender_cold_open.py LOOK): exposure = -1.6
# (EV), sky_strength = 0.45, sky_tint = "#FFB070", sun_strength = 5, sun_color = "#FF9A4A",
# sun_disc = 90, fill_strength = 0.25, haze = 1900 (m), dust = 0.0015 (per m)
# a tap lamp instead: scene = "night_desk", motion = "tap" (no spin, nothing hidden), optional
# taps = [1.0, 3.0, 4.0] (s: on, off, on...; default beats 2, 6 and 8); the desk's look
# (DESK_LOOK): exposure = 0.9, moon_strength = 3.4, moon_color = "#9DB8FF", lamp_gain = 2.5
# (x the LEDs' own power), spill_strength = 2.2 (W), spill_color = "#FF7040"
# underwater: scene = "deep_sea" (motion "glide" and hiding the "stand" parts by default);
# optional forward = [-1, 0, 0] (else along the longest horizontal extent), glide_lengths = 1.6
# or through the model's room: motion = "flythrough" (about 15 s), its points (LDU, the model's
# frame; meta["flythrough"], this table over it):
# [video.cold_open.flythrough]
# origin = [0, -552, 0]           # added to every point (e.g. where a sub-assembly sits)
# enter = [-60, -12, -200]        # where the camera goes in through the hull (a window)...
# exit = [-60, -12, 200]          # ...and out again
# path = [[-60, -15, -125], ...]  # waypoints round the room
# look = [[-60, -30, 40], ...]    # what it looks at from each (else straight ahead)
# slow = [1.3, 1.8, ...]          # optional: time weights per waypoint (1 = its distance)
# interior = { bounds = [[-280, -152, -140], [180, 64, 140]], tags = ["salon_interior"] }

[[companions]]                  # (the site's companion section, model.toml's top level)
slug = "caldwell_mini"          # another model, with its out/turntable.mp4 (brickkit turntable)
eyebrow = "Kids' build"         # over the heading (else "Also")
heading = "The mini courthouse" # (else the companion's name)
price = { pick_a_brick = 9.87 } # its chip: "~$10 Pick a Brick"
video = true                    # feature it in the showreel (the companions segment)
# optional: video_chips = ["pieces", "steps", "price"]; [video] companions = false turns
# the segment off

[video.coda]                    # opt-in: the last image, after the outro
scene = "deep_sea"              # the cold open's sea, gone dark (the only set with a creature)
creature = "squid"              # a giant squid (the only creature so far)
seconds = 7                     # rounded to beats; no black after it
# optional: model = false (leave the model out), murk = 0.85 (0..1, how dark the sea is),
# exposure = -0.4 (EV, on the set's), size = 0.34 (the squid's mantle, in the model's lengths:
# mantle to tentacle tips about the model's length), roll = 25 (degrees it is turned from side
# on), glide_lengths = 0.25 (how far the model cruises over the shot), fade = 1.2 (s of fading
# to black at the end)

[[video.callouts]]              # mechanism callouts; without any, one per moving group
label = "Dust door"
tag = "flap"                    # parts under a tag; globs make one anchor each: "fang_*"
part = "3937"                   # or a part number (one anchor per part), or color = "..."
sub = "Swings 90°"              # second line; default: how far its group turns, or its name
xray = true                     # also draw the parts' outlines (for parts hidden inside)
```
**Cold open.** `design.py` gives the motion: `model.meta["performance"] = f` with `f(u)` for u
in [0, 1) returning `{group: 4x4 world matrix}` like `model.pose` (one loop of the dance), and
`model.meta["performance_info"] = {"hide_tags": [...], "ground_y": y, "pivot": [x, z],
"cycle_s": 2.5}` (where it stands, what to hide, how long a loop takes). The loop plays at
that speed once the engine catches (after about half a second), the figure spins about the
pivot, and three shots cut hard: a 300 mm wide shot straight into the sun with the figure's
head just under it, a low 70 mm and an ankle-height 38 mm shot. `sunset_road`
(`render/blender_cold_open.py`, EEVEE) treats the figure as life-size (a man about 2 m tall
with his arms up) and builds everything procedurally: a physical sky with a dusty aureole and
thin cloud bands, a warm sun lamp along the sun's line and a camera-only sun disc; a worn
two-lane chip-seal road (patches, tar-filled cracks, polished wheel paths that take the sun's
glare, a faded dashed yellow centre line, worn edge lines, crumbling edges, caliche
shoulders); dry grass and seed stalks along the verges, lit through from behind; barbed-wire
fences; a power line and a telephone line of leaning poles with sagging wires (phased so none
stands out of the figure's head); mesquites, live oaks, a dead tree, a windpump, a farmhouse
and barn, a tree line and two ridges of low hills; aerial haze with distance and a thin dust
over the road. The lens focuses on the figure per shot (the wide shot deeper, the close shots
softer behind, oval bokeh), blurs the swing a little (a 180° shutter), and Blender's
compositor exposes each shot, blooms the highlights and throws sun beams from the visible part
of the disc. The web compositor adds letterbox bars, a veil of flare, a thin anamorphic streak
through the sun and aperture ghosts along the line through the middle (all dying when
something crosses the sun), and dust in the light; the sound is a chainsaw that is pulled,
catches, idles and roars with the saw's speed (the `rev_tag` parts'), over wind, cut dead at
the black. No music plays under it. Its plates render in about 0.6 s a frame at preview size
and 1.8 s at full size. A model without one is unchanged.

A **tap lamp** (`motion = "tap"`, for a model with a press pose and LEDs, e.g. in
`scene = "night_desk"`) is pressed and let go on three taps - on, off, on, then held into the
cut - `model.pose` 0 -> 1 -> 0 with a little rebound, clicking at the bottom of its travel,
where the push-on/push-off switch toggles its LEDs: they snap on with a flash that settles
(and its glowing parts glow with them), and go off in a few frames. The camera punches in on
each click and the picture jolts; the lamp doesn't spin. `night_desk` is a bedroom at night at
the model's real size: a varnished desk against the wall under a window of moonlit blue night
(a moon, stars and trees beyond), a curtain, books, a mug, a plant, a notebook and a print on
the wall, the moon the only light until the lamp comes on; then the LEDs light the parts they
glow in and a soft glow round them lights the room warm (light-linked, so the clear shell
isn't washed out). Two shots: the room at 40 mm from above the desk, cutting in the dark
before the third tap to a low 75 mm close with the moon through the window behind, both
slowly pushing in with shallow focus on the lamp. The compositor adds a warm haze round the
lamp while it's lit, a flash as it snaps on, and in the bottom bar what the last tap did
(TAP · ON, TAP · OFF). The sound: the switch's click on every tap, a pop as the light comes on
and a softer one as it goes off, the night under it all and a faint mains hum while it's lit
(synthesised: a plastic snap, the power-up and -down and a quiet wind unless recorded, below).
Its plates take about 0.7 s a frame at preview size and 1.7 s at full (the set renders at two
thirds of the job's samples).

A **glide** (`motion = "glide"`, the default in `scene = "deep_sea"`) carries the whole model
forward through the water along its long axis (`performance_info` "forward", else the longest
horizontal extent, towards -X or -Z) for 1.6 of its own lengths, banking, pitching and bobbing
gently, its `meta["performance"]` loop (else its pose, swinging) playing; parts tagged "stand"
are hidden. Three shots: a wide approach from below as it comes out of the blue towards the
camera (28 mm), a tracking shot along the side shown to the camera (its front) a little below
it and slower, so it slides through the frame (40 mm), and a still close one just off its path,
the bow sweeping past the lens (20 mm); the camera is keyed too, so motion blur follows what it
tracks. `deep_sea` is open water scaled to the model: a volume of water that pales and greens
under a rippling bright surface and thickens to deep blue with distance and depth, shafts of
light along the sun's line through it, marine snow drifting, bubbles rising from vents in a
rocky seabed with kelp far below and streaming from the model's stern, caustics on the sand;
its LEDs (if any) lit throughout. The sound is the set's own (shared recordings in
`brickkit/data/audio/deep_sea/`, made by `tools/elevenlabs_sfx.py brickkit/data/audio/deep_sea`)
unless the model's `[video.audio]` gives its own: the deep's rumble under it, a sonar ping at
the start and after each cut, bubbles on the cuts and as the bow passes, the hull groaning
once, the propeller churning louder as the stern nears the camera. About 0.4 s a frame at
preview size and 1.6 s at full.

A **flythrough** (`motion = "flythrough"`, in `scene = "deep_sea"`) glides the model the same
way (1.3 of its lengths) and takes the camera through its room. Two shots outside: still under
its bow as it passes overhead (20 mm), and wide from below and to the side, the whole model dark
against the bright water (32 mm); then one take: along the hull to the lit window at `enter`
(24 mm), through it, round the room along `path` looking at each `look` in turn (18 mm; turns
take their time and `slow` stretches a waypoint), out through the far wall at `exit`, swinging
back to the model and away from it into the deep (30 mm). Hull parts near the camera are hidden
while it passes (never the room's own, `interior.tags`); the water stops at the room's bounds and
in the walls the camera goes through, three warm lamps light the room (light-linked to it; the
sun and the sea's fill are kept out), the windows glow out into the water and the picture warms
inside. Past the far wall the sea goes dark: the surface's light, the shafts and the caustics
die and the water thickens to near black as the model's lit windows recede, and below and beyond
it something huge rises, its arms reaching up (a squid's dark bulk, faintly rim-lit, one eye
catching the light). The sound: the deep (hushed in the room), pings at the start and on the
wide shot, the hull groaning; a pipe organ, synthesised (`audio.SFX.fx_organ`: the opening of
Bach's Toccata in D minor on a full organ in a hall), heard faintly through the hull from the
wide shot on, swelling as the camera nears the window, open in the room (its second statement
starts on the window, the pedal and the diminished seventh over it build past the organ), muffled
again outside and dying away; bubbles bursting going in and out; then the dread (`fx_dread`: a
low drone a minor second wide, a sub swelling, dark water), a far ping with no answer, the hull
groaning behind and something huge moaning in the dark. The set renders at half the job's
samples (finer water while inside the room): about 1.2 s a frame at preview size and
1.9 s at full for a model of 8,500 parts (14 minutes for the 15 s). With `organ` in
`[video.audio]` a recording (e.g. ElevenLabs music, `[[music]]` in the model's `audio/sfx.toml`)
plays instead of the synthesised organ, faint through the hull, open in the room, its
`organ_in` seconds reaching the window.

**Companions** (`video/companions.py`): each `[[companions]]` block with `video = true` gets
10 beats between the booklet and the outro (`[video] beats = { companions = N }` for all of
them). Nothing new is rendered in 3D but a transparent hero still of the companion (Cycles,
cached in `video_frames/<q>/companions/<slug>/` like the title's): its turntable
(`out/turntable.mp4`) is turned into frames as the sizzle reel does (`sizzle.turntable_frames`),
and the scale beat stands the model's own hero cut-out and the companion's on one line, each
as tall as the other's real height says (their solid pixels, not their shadows, measured; clean
copies without the shadow catcher's faint veil), with its height in cm beside each. The sound:
a whoosh as the heading rises, a pop for the card, blips for the chips, a snap as the
companion lands, ticks as the measures draw; the music grooves on under it.

A **coda** (`[video.coda]`, after the outro) is the video's last moments, in the same `deep_sea`
set (`render/blender_cold_open.py`, plan "coda"; `timeline.coda_plan`): the sea gone dark (murk),
the model cruising slowly with its lights on, seen from off its side and a little below, and
its creature coming out of the murk at it. `creature = "squid"` is a procedural giant squid
(`Squid`: a long mantle tapering to a point with a heart-shaped pair of fins at its tip, the head
and two great eyes, eight thick arms and two long tentacles ending in clubs) about the model's
size, the two of them in one frame: it comes from beyond the model, low on the right, arms
first, and closes on it - arms writhing and curling, mantle breathing, fins rippling, its
tentacles uncoiling and reaching for the model - its back and edges catching a light from above
and behind it (light-linked to it alone, coming up as it leaves the murk), its eyes catching
the light. One take at 28 mm, pushing in a little, letterboxed like the cold open; the theme's
wipe into it from the outro (the abyss porthole opens on it); the picture fades to black over
its last `fade` seconds as the squid closes in. The sound: no music (a recorded score's tail
dies away in it), the deep fading in, a lone sonar ping and a fainter one later, the dread
swelling, the creature moaning as its eye catches the light (the set's recorded `creature`),
all fading out with the picture. The cold open's flythrough ends on the same squid, barely seen
far off in the dark.

**Recorded sounds** (optional). The music and effects are synthesised unless the model has
`[video.audio]`: sound files in the model's `audio/` (committed, so the video rebuilds offline)
by role. `tools/elevenlabs_sfx.py SLUG` generates them from `audio/sfx.toml` (`[[sfx]]` name,
prompt, seconds, variants, loop) with ElevenLabs' sound-generation API, skipping files that
exist and recording each file's prompt and settings in `audio/sfx_generated.json`; `--dry-run`
lists what it would make, `--analyse` measures every file (length, loudness, true peak,
silence, how it ends, band energy, engine periodicity, speech-like modulation) and ranks the
variants. The API key is read from `ELEVENLABS_API_KEY` or `~/.config/brickkit/elevenlabs.env`
and never printed or written. MP3s decode through ffmpeg.
```toml
[video.audio]
pull_start = "pull_start_1.mp3"   # the cold open: pulled at its start...
catch = 0.73                      # ...the engine catches this far in, the idle takes over
idle = "idle_1.mp3"               # looped (crossfaded) to the cut, ducked under the screams
screams = ["scream_3.mp3", ...]   # full throttle: on the swing's peaks (the saw's speed), and
                                  # quieter on the build's section changes
burst = "rev_burst_2.mp3"         # on the title's stamp (theme grindhouse), with the first...
stings = ["string_stab_1.mp3", "string_stab_3.mp3"]   # ...sting; the rest, the hits and the
hits = ["metal_hit_2.mp3"]        # booms take turns on the big cuts (a boom replaces the
booms = ["boom_2.mp3"]            # synthesised hit there)
levels = { scream = -8.5 }        # optional: peak dBFS per role (reel.SAMPLE_LEVEL)
# a tap cold open (a tap lamp):
clicks = ["click_2.mp3", ...]     # the switch, on each tap in turn
snaps_on = ["snap_on_1.mp3", ...] # a pop as the light comes on (in turn)...
snaps_off = ["snap_off_1.mp3"]    # ...and a soft one as it goes off
room = "crickets_2.mp3"           # the night outside, looped under it
# a glide (deep_sea; reel.SCENE_SOUNDS fills in what isn't given, from the set's shared folder):
ambience = "..."                  # the deep, looped under it
pings = ["..."]                   # sonar pings: at the start and after each cut
bubbles = ["..."]                 # on the cuts and as the bow passes
groan = "..."                     # the hull, once
churn = "..."                     # the propeller, looped, louder as the stern nears
                                  # (a flythrough uses the same roles; its dread is
                                  # synthesised, its organ too unless:)
organ = "organ_1.mp3"             # a flythrough's organ music, recorded: shaped like the
organ_in = 4.25                   # synthesised one; this many s of it reach the window
creature = "..."                  # the coda's creature moaning (the set's own by default)
# any model, a recorded score instead of the synthesised music:
music = "score_2.mp3"             # from the cut out of the cold open to the end (the synth
music_offset = 0.5                # silenced), this many s into it on that cut; into a coda
music_tail = 3.0                  # for this many s, fading out there
```
A score is ElevenLabs music like the sizzle's: a `[[music]]` composition plan in the model's
`audio/sfx.toml` whose sections are held to the reel's segments (their lengths in `ms`, at the
theme's tempo), e.g. a hit on the open, the theme on the title, a long crescendo through the
build, its peak on the mechanism, resolving on the outro (models/nautilus/audio/sfx.toml). It
is balanced to the same music level and ducked under the big sound effects like the synth.
Everything in the cold open stops dead at its cut; the synthesised music bed stays (ducked under
the stings) and the mix is mastered to the same -16 LUFS / -1.5 dBTP. Without the table a model
sounds exactly as before.

Callout anchors are the centres of the matched parts, moved by their group's pose every
frame and projected through the video camera, so the lines follow the real parts. Callouts
that match nothing are left out (with a note in the log).

**Themes** (`brickkit/video/themes.py`) set the tempo, colours, wipes, title animation and
overlay; they all share the site's type: Inter for display (700, set tight: -0.022 em for
headings, -0.028 em for the name; figures in fixed cells so counters don't jitter), Menlo
caps, tracked out, for small labels, Inter 500 for detail lines (tokens `display`, `mono`,
`brand_mono`; another face gets scaled to the same cap height). `brand` (cream and yellow,
stud wipes), `scan` (teal HUD, scan lines, blast-door wipes), `tape` (VCR on-screen display,
tracking glitches, chroma bleed; the on-screen display itself - PLAY, SP, the timecode, the
counters, CHAPTER, TRACKING - keeps a VCR's VT323 lettering), `playful` (bouncy type,
paw-print slides), `grindhouse` (a 70s drive-in horror print at 100 BPM: warm near-black,
bone type, blood red and apron yellow; gate weave, flicker, dust, hairs, scratches and light
leaks; film-burn cuts spliced in with a frame slip, frame slips between build sections, a
projector roll between colourways; the name rubber-stamped, typewritten labels, evidence-tag
callouts; a heartbeat, drone, string swells and scraped metal, with a two-stroke chainsaw on
the title), `abyss` (the deep, at 106 BPM: teal-black and sea blue, brass and copper, aqua
light; a deep blue studio backdrop; a brass-rimmed porthole irises shut on riveted hull plating
over every big cut, turning as it closes, bubbles rushing past it; a sonar sweep - range rings,
the beam going once round, a ping ringing out - between build sections; the next colourway
seen through a porthole opening up; caustics rippling down from the surface, slow light
shafts, marine snow and a few bubbles over everything, fainter over the plates and thinning out
over the model; the name engraved letter by letter into a brushed brass plaque that swings up
into place and is riveted round its edge, dive-log section titles over a riveted brass rule,
porthole callouts, gauge-plate chips in brass rims; the score: a slow heartbeat pulse under
drones and string swells, a knock on the hull for a backbeat, sonar pings on the beat (each
with its echo off the sea floor, through the dotted delay), bubbly arps, a rush of bubbles on
every cut and a deep undertow swelling into it). Fonts are bundled OFL fonts in `brickkit/video/web/fonts/` (Menlo is the
system's; elsewhere it falls back to the default monospace). Try one without
touching the model: `brickkit video SLUG --theme grindhouse --no-render --stills 90,150,600`.

**How it's made:** `video/timeline.py` plans the 3D shots (no Blender), `video/reel.py` the
graphics and the cue sheet from the model's data, `render/blender_animate.py` renders the
plates (EEVEE, always under the machine-wide `blender_slot()` lock, 40 frames per process),
`video/web/` is the compositor (a canvas `renderFrame(f)` run in headless Chromium by
`video/compose.py`) and `video/audio.py` synthesises the music and effects (numpy, mastered to
-16 LUFS). Plates are cached per segment, numbered from the segment's start, with a hash, so
editing graphics never re-renders 3D and moving a segment in the edit keeps its renders.

### Sizzle reel

`brickkit sizzle [SLUG ...] [--config FILE] [--out DIR] [--stills 60,240] [--preview]
[--no-audio]` cuts one quick brand reel from several models' showreels: by default
`showreel/sizzle.toml` -> `showreel/sizzle.mp4` (1080×1080, 30 fps, about 43 s for five
models, ~15 MB),
`sizzle_poster.jpg` (the finale's grid) and `sizzle_contact.jpg`. It renders nothing in 3D:
the footage is each model's last `brickkit video` run, read-only (its cached plates in
`out/video_frames/full/<segment>/`, `out/turntable.mp4`, the hero cut-out), and the frames it
uses are copied into `showreel/work/footage/` first (git-ignored), so a showreel re-rendering
at the same time doesn't matter. Run `brickkit video SLUG` for a model before adding it.

Everything sits on the music's beats. With `music` set, the track's beats are found in the
track itself (`video/beats.py`: the tempo from the onsets' autocorrelation, the beats by
dynamic programming, moved onto the kick if they locked to an off-beat hat, bars from the
claps on 2 and 4; cached in `work/beats.json`); without it a fixed grid at `bpm` drives the
house synth. Sections are counted in bars: the open (the logo, the tagline slammed on beats,
then each model's cut-out on a coloured card in the bar before the drop: a beat each for four,
the bar shared out on eighths for more - five go ½, ½, 1, 1, 1 beats, the last one half
under the wipe into the drop),
each model (its name slammed on yellow bars over quick cuts of its own footage, a caption,
stat chips; a long name goes on three lines), the finale (the turntables popping into a grid
across its first bar - 2×2 for four, three across for five to nine with the last row centred,
the name tags sized to the cells - then "5 models · N pieces · every brick checked") and the
outro (logo, URL, small print and the models' notices). Wipes are the brand's: a brick wall at
the drop, then studs in yellow and brick red. Any number of models works; lay the sections on
the music's own phrases (its drop, fills and breaks) by their `bars`.
```toml
title = "Bricks"
url = "bricks.superfun.games"
music = "audio/track_long_1.mp3"   # next to the config; omit for the synthesised music
bpm = 128                     # a hint for the beat tracker (or the synth's tempo)
whoosh = "audio/whoosh_1.mp3" # on every wipe (else the synthesised whoosh)
line = "{n} models · {pieces} pieces|every brick checked"   # the finale; | breaks the line
disclaimer = "Unofficial fan models · ..."
[theme]                       # overrides on the brand theme (the site's colours)
bg = "#FFFDF5"
bg2 = "#FEDB05"
[timeline]                    # bars
open = 4
finale = 3
outro = 2
open_words = [["Real", 4], ["LEGO.", 6], ["Checked by", 8], ["computer.", 10]]  # [word, beat]

[[model]]                     # in order; `brickkit sizzle ferret vhs_tape` keeps a subset
slug = "baby_metroid"
bars = 3
chips = ["pieces", "headline"]   # or steps, colours; in on the section's beats 4 and 6 (from 0)
# name = "..."                # shown instead of the model's name (tags, slam, teaser)
# break = true                # a filter break: the track's kick and bass drop out under this
                              # section (a 24 dB/oct high-pass at 320 Hz, 2.5 dB up, swept to
                              # 1.2 kHz over its last beat); the drop comes back on the next
[[model.shot]]                # shots follow each other, `beats` long (the last runs to the end)
source = "build"              # a plate segment of the model's video, or "turntable"
from = 0.2                    # a stretch of it (0..1), sped to fit...
to = 1.0
beats = 3
[[model.shot]]
source = "cold_open"
at = 30                       # ...or this frame of the segment lands `lead` (whole) beats in,
lead = 1                      # played at `speed` (default 1), so the moment hits the beat
beats = 3
caption = "Tap: lights on"
sfx = "../models/baby_metroid/audio/snap_on_1.mp3"   # a sound on that beat...
sfx_align = "peak"            # ...its loudest moment on it (else its start)
sfx_level = -1.0              # peak dBFS against the music (default -9); it stops at the cut
[[model.shot]]
source = "still"              # a picture from the model's out/ (one frame, pushed in)
file = "renders/tower_close.png"
push = 0.14                   # how far it creeps in over the shot (default 0.04)
beats = 3
[[model.shot]]
source = "mechanism"
at = 60
lead = 1
zoom = 1.8                    # crop in (plates are 1080: up to about 1.8 stays crisp enough)...
focus = [0.5, 0.47]           # ...about this point of the frame (0..1), kept off the edges
beats = 3
```
The sound is `video/audio.py`'s: the track as a bed (`cues["track"]`: balanced to the same
level as the synthesised music, faded out at the reel's end, which is the bar where the music
ends), the models' own sounds ducking it, clicks on the cuts, pops on the chips, snaps on the
slams, mastered to -16 LUFS / -2 dBTP (the AAC encode adds a few tenths; the file stays
under -1.5 dBTP). The encoded track is then decoded and compared with the WAV: ffmpeg's own
AAC encoder sometimes puts a click (a burst 10 dB or more over a quiet, wide passage) into
this reel's mix, so on a burst or a true peak over -1.5 dBTP the sound is encoded again, the
video copied, with AudioToolbox's AAC (`aac_at`, macOS) where ffmpeg has it, else other
settings (`check_sound`). The models' own showreels had no bursts when checked. The track, whoosh, clunk and clock bell are ElevenLabs'
(`showreel/audio/sfx.toml`: a `[[music]]` entry goes through the music API - a prompt and
seconds, or a composition plan: `styles`, `avoid`, `bpm` and `[[music.section]]` name, bars,
styles, avoid, each section held to its length - and `[[sfx]]` through sound generation, as
for a model: `python tools/elevenlabs_sfx.py showreel/audio`). Check a new track's structure
before laying sections on it (its bars' energy by band, from the detected beats): the plan's
sections are a request, not a promise (`track_long_1` came back with its drop and two 8-bar
phrases but no breakdown, hence the filter break under the ferret). To choose a shot's
`at`, look through the plates (for example the frame a lamp snaps on or a door lands; a
mechanism's timing comes from its program, so it survives the model being rebuilt) and
preview with `--stills`.

### Quick Bricks

`brickkit quick SLUG` turns a finished small model (a sub-$20 set) into a short vertical build
video for TikTok and Instagram: `out/SLUG-1080x1920.mp4`, 1080×1920 at 60 fps (the top rate Reels and
TikTok take), H.264 High profile (CRF 18, capped at 20 Mbit/s) + AAC 48 kHz, 14 s, under 50 MB,
made to loop, and `out/quick_poster.jpg` (the finished model in its hero spin). The motion blur
is a 180° shutter (1/120 s). Every timing is in seconds, so a 30 or 15 fps run lands, cuts and
clicks at the same moments. `--preview` makes `out/quick_preview.mp4` (540×960, 15 fps, 16
samples) to iterate on;
`--stills 0,150` renders just those frames (into `out/quick_frames/<q>/`); `--set`,
`--surface`, `--room`, `--light`, `--seed` and `--seconds` try another workshop or length for
one run. Plain and clean, like the "LEGO assembly
animation" reels it follows: just the render, no titles, cards, counters or graphics.

It is all photoreal (Cycles, `render/blender_quick.py`; the parts' plastic from
`blender_scene`), very shallow depth of field (a macro's: f/2.8-6.3, the set melting away), in
a little workshop at the model's real size built from three layers, any with any
(`render/quick_sets.py`):

| Layer | Options |
|---|---|
| surface (what it stands on) | `blue_mat` (blue self-healing cutting mat, fine cyan centimetre grid, on oak), `green_mat` (the classic green mat, pale grid and diagonals, on walnut), `kraft` (tan linen with a big printed ring), `oak` (a bare light-oak desktop), `baseplate` (a light grey 48×48 LEGO baseplate, studs and all) |
| room (always soft behind) | `workbench` (plank walls, pegboards of colourful tools, a desk lamp, a red toolbox), `studio` (bright white walls, low white shelves, plants, pastel books), `window` (big windows of daylight, bushes and sky outside, a sill of succulents), `night` (dark walls, strings of warm lights, a glowing desk lamp), `bookshelf` (shelves packed with colourful books) |
| light | `morning` (warm low sun from the side, a cool fill), `day` (bright soft neutral daylight from high up), `evening` (a warm lamp-like key, a dark room) |

The camera is low, so a room is what shows in the bottom 30 cm of its walls and on the desk:
big shapes and colour, cheap to render. The walls stand back past the camera's whole path (the
plan's `reach`, its farthest from the model) and every prop on the desk - lamps, a toolbox, a
mug, a plant - stands out past it too, so the camera never passes through one; before encoding,
any frame that is nearly one flat colour (the camera inside something) is listed as a warning. Presets (`set`) name a combo: `cutting_mat` (blue_mat,
workbench, morning), `linen` (kraft, window, day), `studio` (green_mat, studio, day),
`night_shift` (oak, night, evening), `reading_nook` (baseplate, bookshelf, morning); any layer
given beside it wins; `set = "random"` picks one of each by `seed` (else by the model), so a
series of videos varies by itself.

The build (`video/quick.py`, no Blender: `plan`): it opens on the empty set; the parts come in
instruction order (`build_sequence`), each flying in from just off the frame - out to the side
it faces, or the camera's left or right of it, and up - on a short cubic arc whose last stretch
runs along its insertion axis (its `insert=` hint, else its own top: down onto its studs, or
sideways for a part on side studs) so nothing passes through what is built, slowing as it
lands, tumbling a little and straightening, then a tiny bounce back off its studs. The pace
ramps up (the last parts land about 3× as often as the first, several a second), a beat before
the last piece. The camera circles the model low by the table (11-20°) in one smooth orbit
that only ever goes one way (`orbit`): it starts on the front's three-quarter view (the front
is -Z, or the model's `azimuth_offset`), goes slowly at first and faster as the build speeds
up, passes the back faster than the front, and ends on the front again. It frames what is
built so far, tight on the base at first, rising and pulling back as the build grows, and
moves in to a macro close-up (a longer lens, the part about a third of the frame wide) on up to
three landings - per `highlight` group the part facing the camera best as it lands. The orbit
is timed to be on the side each close-up's part faces when it lands (a part that goes on
sideways, like an eye or a clock, is seen face on; one that goes on from above from between
its side of the model and the front), so the close-up is a push in along the orbit, not a
swing across it; the build gives each one room. Then out, a slow drift across the front, and
a hard cut to the empty set, whose camera runs on into the first frame: the loop. The sound:
a crisp click on every landing (six ElevenLabs takes in turn, a little louder or softer), a
deeper snap on the last piece and a soft swish into each close-up - just those by default;
`music = true` adds a light, loopable lo-fi music bed under them
(`brickkit/data/audio/quick/`, made by `tools/elevenlabs_sfx.py brickkit/data/audio/quick`),
and `ending` plays a sound of the model's own after the last piece (Dracula's laugh, from
`tools/elevenlabs_sfx.py dracula`); `[[quick.sound]]` plays others at moments of the build
(the mini courthouse's bell tolls as its tower goes up). The sound is mixed apart from the
picture, so changing
it needs no new frames: the next `brickkit quick SLUG` only mixes and encodes again - or
`brickkit quick SLUG --remix`, which never renders: it takes the frames there are (and the
plan they were made from, even if the planner or the render scripts have changed since) and
mixes the sound from `[quick]` as it is now.
The mix is mastered for phones (-14 LUFS with the music) and checked for AAC clicks.

**Laid out** (`layout`; by default for a model of under 25 pieces, `--layout` / `--no-layout`
on the command line): the video opens on every part knolled on the table - a tidy grid
behind the build's place, each part lying as a loose one would (`resting`: studs up if that
is stable, else on its broadest stable side), long side along the rows. The grid is the model
taken apart (`lay_out`): its rows are the build's steps in order, the first furthest back and
the last nearest the build, so from the front it reads from the top down like a list and
empties towards the build; no row is wider than the build, so the grid stands tall in the
upright frame; in a row the same parts sit together and the row mirrors the model, each part
on the side it will be on. After 1.2 s to take it in, the parts lift one at a time, turn the
way they will sit, float over what is built and press on (`floats`; slower than the fly-ins).
The camera starts high (55°) in front, square on to the grid, and frames the build's place
and whatever still lies behind it, so it closes in and comes down as the grid empties; it only
drifts across the front until the table is all but clear, then makes its whole turn round the
finished model before the cut (a longer hero, 3.2 s). Close-ups are only on parts that land
once half the grid has gone. After the cut the parts are laid out again: the loop.

```toml
[quick]
set = "cutting_mat"                 # a preset (above) or "random"
surface = "green_mat"               # optional: any layer over the preset's
room = "bookshelf"
light = "evening"
seed = 3                            # for set = "random" (else the model's name)
seconds = 14                        # the whole loop
highlight = ["14769p0m", "3688"]    # parts (numbers or tags) for the close-ups, by preference
                                    # (else printed parts, then the last two parts)
close_ups = 2                       # 0..3
layout = "auto"                     # true: the parts start laid out in a grid and float in;
                                    # false: they fly in; "auto": laid out under 25 pieces
music = false                       # true: a light music bed under the clicks
ending = "audio/laugh_1.mp3"        # the model's own sound after the last piece (a path in
                                    # its folder), with ending_level (-3 dBFS) and ending_at
                                    # (0.25 s after the last landing)

[[quick.sound]]                     # more sounds of the model's own, at moments of the build
file = "audio/bell_1.mp3"
on = ["The clock tower", "14769p0m", "last"]   # a step's caption (its first piece landing), a
                                    # part number or tag (the one in a close-up, else the
                                    # first), "first", "last", or a time in seconds
level = -11.0                       # peak dBFS in the mix (a click: -9); at = s after each
exposure = -1.0                     # EV, for a brighter or darker set
view = "filmic"                     # the film response: "filmic" (the parts' colours true) or
                                    # "agx" (softer; a bright yellow goes pale orange). Under
                                    # filmic the morning and day lights are exposed 1.0 and
                                    # 1.2 EV lower (quick_sets.LIGHTS "filmic"), or they wash
                                    # the colours out
watermark = false                   # true: the Bricks logo, small and faint, top centre
```
Frames render under the GPU lock, 40 to a Blender process (Cycles, 32 samples, denoised: about
8 s a frame at 1080×1920 on this Mac, so a 60 fps final of 840 frames takes about two hours;
a preview about ten minutes), and are kept between runs until the plan, the samples or the
scripts change. Every Cycles render uses the GPU on its own (`blender_scene.settings`): with
the CPU sharing each frame it took over twice as long for the same picture, and a see-through
part under motion blur made Metal fault and the render hang. See-through parts are tinted more
strongly here than in the stills (`blender_quick.TINT`): at real size and this close, the
stills' absorption leaves a flame all but clear. The next one: add `[quick]` to the model's model.toml
(or nothing: the defaults work) and run `brickkit quick SLUG --preview`, then `brickkit quick
SLUG`.

## Shape helpers
`brickkit.shapes.rings`: `ring_cells(r_out, r_in)`, `pack_cells(cells, lengths, offset, mode)`
(bonded 1xN runs), `exposed(lower, upper)` (step cells for slopes, with outward direction),
`shell_layers(profile, heights, thickness)` (shells of revolution).
