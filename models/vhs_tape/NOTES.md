# VHS Cassette: design notes

A life-size (1:1) VHS video cassette in real LEGO, built the way a modern display set is:
an inner chassis carries the reel spindles, lamp tube, brake release, guide rollers and
the tape run, and a shell goes over it. The full-length dust flap swings up like the real
one, and both reels turn behind two clear windows. 384 parts in 54 part/colour lines,
104 steps, about 313 g (a real T-120 weighs about 230 g).

## Size

| | Real VHS | Model | Difference |
|---|---|---|---|
| Width | 187 mm | 184.0 mm (23 studs) | -3.0 mm |
| Depth | 103 mm | 102.4 mm (12 studs + 16 LDU flap) | -0.6 mm |
| Height | 25 mm | 25.6 mm (8 plates) | +0.6 mm |

Footprint x -230..230, z -126..130 (the flap is the front, -Z), y -64..0 in LDU.
`check_dimensions` (an `extra_checks` entry, reported by the mechanism check) fails the
build if any outer dimension drifts more than 5 mm from the real cassette.

Reel hubs are 88 mm apart (x = +-110), 4 mm behind the middle of the depth.

## Structure (booklet order)

1. **Chassis** (`core`, 151 parts). Two floor layers, woven crosswise (rows along X, then
   columns along Z) so every plate is bonded:
   - Bottom layer: three Technic plates 2 x 4 whose middle holes are the two **drive holes**
     and the **lamp hole**, a Technic plate 1 x 5 whose axle hole is the **reel-lock
     release hole**, five **Flat Silver 1 x 1 round plates as screw heads**, and the open
     **mouth** (a 15-stud slot) under the tape.
   - Second layer: **smooth tiles wherever a reel turns**, a round tile with a hole over
     each drive hole (the spindle's upper bearing), plates elsewhere.
   - On top: the **lamp tube** (black 2 x 2 round brick) centre-front, the **white brake
     release** at the back centre, **white guide rollers** (1 x 1 round bricks) at both
     front corners with a guide post behind each, ledges the windows land on, and three
     bricks with a side stud carrying the **tape run**: black 1 x N plates stood on edge with
     black tiles facing forward, stretched between the rollers.
2. **Reels** (16 parts each, identical hardware; see Mechanisms). They drop onto the
   chassis, the full supply reel at +X, the take-up reel at -X.
3. **End walls**: a 1 x 8 brick and two plates at each end.
4. **Top shell** (174 parts), built upside down and lowered on:
   - Face layer: **grip bands** of 1 x 2 grille tiles along both long edges (slots along
     the cassette, like the moulded ribs), the black rim round the label (1 x 4 tiles
     front and back, a 1 x 6 tile on each side, next to the windows), 1 x 8 tiles at
     the ends. Two plate layers under it, woven crosswise; the third layer carries the
     flap's two pivot blocks.
   - **Face label** panel (its own sub-assembly): seven black 1 x 10 plates running
     front to back, which tie the front and back grip bands together, with white 2 x 4
     and 2 x 3 tiles on them. The label is 7 x 6 studs (56 x 48 mm), one plate below a
     black rim on all four sides, centred between the windows like the reference.
     The rim is 1 stud (8 mm) wide beside each window, against about 5 mm on the
     reference. A half-stud rim would need an 8-stud label centred in the 9-stud gap:
     the label would sit half a stud off the grid (on jumper plates), and a 4 mm strip
     would be left on each side. No stud-grid part fits that strip (LEGO makes no
     half-stud-wide tile), so the "rim" would be an open slot down to the reels.
     Tying the offset panel into the shell would also need plain 1 x 3 tiles in the
     grip bands, breaking the ribs.
   - **Spine label** on the back face: bricks with side studs under the back band, 2 x N
     plates stood on edge, then two rows of white 1 x N tiles with black ends, recessed
     1.6 mm. The **write-protect tab** is one 1 x 1 tile at the back-left of the lower row.
   - Two **windows** (their own sub-assembly, used twice), hung from the back band.
5. **Dust flap** (19 parts), built flat, then pinned on.

## Windows: the largest clear pane

The largest seamless clear piece that fits is **Glass for Frame 1 x 6 x 6 (42509,
Trans-Clear)** in a **Black Door Frame 1 x 6 x 6 (42205)**. The pane is 44.8 x 53.4 mm, the
frame 48 x 57.6 x 8 mm: laid flat, it is 6 studs along the cassette, 144 LDU across it and
exactly one frame thick, so its top is flush with the top face. The runner-up, a
Trans-Clear Panel 1 x 6 x 5 (59349), is 48 x 48 mm overall, but its thin wall is shorter
and it brings a clear base strip and a row of studs along its edges. Glass for Window
1 x 4 x 6 (57895) is only 29 mm wide. Transparent plates and tiles show a stud grid or
seams. Real cassettes vary, but this is about the size of the reference windows.

Mounting (SNOT, all real connections): a 2 x 6 plate stood on edge, studs forward, takes
the frame's back end; six half-round 1 x 1 x 2/3 plates with a side stud hang that plate
from the underside of the back band, and they land on ledges in the chassis. The frame's
front studs are capped by a 1 x 6 tile that butts against the front grip band; the front
end is held through the frame (a 6-stud cantilever from the back). The glass is placed
1 LDU off LDCad's snap point, where the two meshes overlap slightly; its hinge-style
connection still registers.

## Mechanisms

### Dust flap (`flap`)
The flap is the whole front edge: 23 studs long, 24 mm tall (y -64..-4), 6.4 mm thick,
black and smooth. It is built lying on its back: 2 x N plates stood up, studs forward,
2 x N tiles whose upper halves hang over the plates and make the flap's top row, 1 x N
tiles for the bottom row, and a 1 x 3 plate at each end reaching the top row. **Technic
bricks 1 x 1 with a pin hole** on the back of the end plates are the flap's **cheeks**, as
on the real flap.

It pivots on two **Black Technic pins with friction (2780)** along X: each pin goes
through a cheek into a **Plate 1 x 2 with Pin Hole on Top (11458)** hanging from the top
shell's third layer. The axis is at y = -54, z = -100: 10 LDU below the top and 10 LDU
behind the flap. `pose(t)` turns the flap by `rot(x = -90 t)` about it, so the bottom edge
swings forward and up until the flap lies flat as a visor. Because the top row is the
overhanging half of the tiles (nothing behind it), the flap's top edge swings clear of
the top shell: the mechanism check sweeps it with no collisions. The friction pins give
it some hold (a real flap is sprung shut).

When it is up, you see the tape run straight across the mouth between the two white
guide rollers.

### Reels (`reel_l` supply, `reel_r` take-up)
Each reel, from the bottom:

1. A **White Plate Round 8 x 8 (74611)**: the lower flange, 64 mm.
2. The pack: a **black 74611** on the full supply reel; a second **white** one on the
   nearly empty take-up reel, so the flange shows round a thin pack.
3. The hub: a **White 2 x 2 round plate with axle hole (4032a)** in a ring of four white
   **2 x 2 macaroni tiles** (32 mm); the round plate's four studs are the ring of bumps.
4. Four black **3 x 3 macaroni tiles**: tape round the hub (r 40..60 LDU, 48 mm).
5. Four **Trans-Clear 4 x 4 macaroni tiles**: the clear upper flange (r 60..80).
6. A **Red Technic Axle 2 Notched** pushed up through the round plates' holes and the
   hub's axle hole: its end is the **red dot** in the hub.

In the chassis the axle turns in round holes: the round tile with a hole (upper bearing)
and the Technic plate's middle hole (the drive hole). The reel rides on the smooth tiles
and the top shell keeps it down. Underneath, the red spindle end shows in each drive hole,
flush with the bottom: turn it with a fingertip to wind the tape, as a VCR's spindle turns
the hub from below. Both reels are declared `captive` (they are trapped by the shell).

Through the windows: the supply reel reads as white hub, black pack and clear ring over
black; the take-up reel as white hub, thin black pack and clear ring over the white flange.
`pose(t)` turns both reels the same way, as when playing: the supply reel 270 degrees and
the take-up reel 360 degrees (the small pack spins faster for the same tape speed).

## Part choices

- **74611** has no LDCad shadow file, so its underside connected to nothing. The engine
  now reads overlay snap files from `brickkit/data/shadow/` (see Engine changes); the
  overlay adds its 44 anti-studs.
- **Tape is Black**, like real tape seen through a window. It reads against the white
  flanges and hub; no Dark Brown was needed.
- **27507 is a ring (r 60..80 only)**. **68568 (Tile 4 x 4 quarter circle)** was tried and
  dropped: it is not a concentric ring and clashes with the macaroni tiles.
- **2780 pins stay Black** in every colourway: LEGO never made them in White.
- Screw heads are **Flat Silver** 1 x 1 round plates, flush with the bottom.

## Colourways

- default: black shell, white labels and reel hubs.
- `white`: white shell (a head-cleaner tape), Light Bluish Gray labels. Every part exists
  in White except the pins (kept black).

Both pass `real_elements` with no rare parts.

## Known limits (where it differs from the photos)

- **Depth** is 12.8 studs, not 13: the flap is 16 LDU thick in front of a 12-stud body.
- **Tape** is an 8 mm black tile strip (real tape is 12.7 mm); black on a dark mouth is
  subtle, so the top shell leaves a dark gap over it.
- **Mouth** underneath is a 1-stud slot, not the real deep U-shaped recess: the reels and
  the chassis floor fill that space.
- **Drive holes** are 4.8 mm Technic holes with the red spindle end flush, not the real
  25 mm openings showing the hub. An open 2 x 2 pocket was tried so a Technic axle
  connector could be pushed onto the spindle end; the round bearing tile above it then has
  nothing to hold on to.
- **Clear upper flange** is a ring: there is no flat transparent 8 x 8 disc, so inside
  r 60 you see the pack directly.
- **Lamp tube** is 4 mm right of centre: a 2 x 2 round brick has to sit on a cell corner.
- The top shell's two front corners are cut back where the flap's cheeks sit and swing.
- The flap stops 1.6 mm above the bottom edge, and its pin heads show on the ends.
- The spine label runs to the bottom edge (two tile rows).
- The bottom is a LEGO bottom (anti-studs), not a smooth moulding.
- Not modelled: door-release button, end-sensor light paths, reel brake levers (only the
  white release).

## Checks

`brickkit all vhs_tape`: every check passes with no warnings. real_elements (54
combinations, 0 rare, also for `white`), connections (996; one piece), collisions (0),
buildability (283 insertions, 8 sub-assemblies), stability (tips at 75 degrees),
mechanism (24 poses, 3 moving groups, plus the size check), electrics (none), technique
(0 notes).

## Engine changes made for this model

- **Shadow overlays** (this redesign): `ShadowLibrary(..., overlays=[...])` reads extra
  `!LDCAD SNAP_*` files after the LDCad library's own file for a part. The engine passes
  `brickkit/data/shadow/`, which holds `parts/74611.dat` (44 anti-studs). Tested in
  `tests/test_snaps.py`, documented in `docs/brickkit-guide.md` under "The checks".
- Earlier: buildability lets clips, click hinges and Technic pins snap on; the cache path
  test honours `BRICKKIT_CACHE`.

## Code

`design.py` holds the sub-assemblies (`reel`, `core`, `window`, `label_panel`,
`top_shell`, `flap`), the pose and the size check. `kit.py` has the layout helpers:
`weave` lays a layer in rows along X or columns along Z (runs chosen by `split_line`, never
a 1-stud run at an end), `Batch` orders a phase's parts into steps that each join what is
already built, and `best_layout` tries layout variants until every phase is one piece.

## Renders

`out/renders/`: `three_quarter.png` (closed), `open.png` (flap up, reels turned),
`back.png` (spine label and write-protect tab), `underside.png` (drive holes, screws,
mouth), `white.png` (the white colourway). Hero shots: `out/hero/hero.png` and
`out/hero_open/hero.png`.
