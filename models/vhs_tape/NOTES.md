# VHS Cassette: design notes

A life-size (1:1) VHS video cassette in real LEGO, built the way a modern display set is:
an inner chassis carries the two reel drive holes, lamp tube, brake release, guide rollers
and the tape run, and a shell goes over it. The full-length dust flap swings up like the real
one, and both reels turn behind two clear windows, from the drive holes underneath. 374 parts
in 54 part/colour lines, 129 steps, about 308 g (a real T-120 weighs about 230 g).

## Drive holes underneath

A real cassette is turned by its reels' hubs, through two holes in the bottom; so is this one.

- Under each reel the bottom layer has a **square drive hole, 4 x 4 studs (32 mm; a real one is
  about 30)**.
- In the second layer **four 2 x 4 tiles in a pinwheel** reach over each hole and leave a 2 x 2
  square in the middle. Each sits on five studs of the floor round the hole and ties the plates
  under it together.
- Each reel's **drive hub, a White 2 x 2 round plate with an axle hole, is pushed studs-down onto
  the red axle's lower end**, up against the lower flange. It turns in that 2 x 2 square, which
  is the reel's bearing (0 collisions through the 24 poses). Its four studs are the pegs a
  fingertip turns the reel by: their tips are 1.6 mm inside the bottom, the red axle end is flush
  with it in the middle. The axle's cross goes through an axle hole in each hub, top and bottom,
  so turning the pegs turns the reel.

## A dust flap built to be handled

The flap is long, thin and hung at its two ends, so it is built against folding and against
coming off its pivots:

- **one 2 x 16 plate** runs behind the tiles, so there is no seam for it to fold at;
- at each end, **plates three studs long reach the top row**: two 2 x 3 plates at one end, a
  2 x 3 and a 1 x 3 at the other (the 2 x 16 sits a stud off the middle). The tiles at the
  ends hold them by their studs;
- it hangs on **four hinges, two at each front corner**: 1 x 2 plates with a pin hole under one
  end (18677), stood on the back of those end plates with the hole at the top, on two studs side
  by side, so a hinge cannot twist off. The holes are on the pivot axis (y = -54, z = -100);
- **four Technic pins**, two at each corner, end to end on that axis, join each hinge plate to a
  **pivot block** in the top shell (Plate 1 x 2 with Pin Hole on Top, 11458). From the end
  inwards a corner reads: hinge plate, pivot block, hinge plate, pivot block. The inner pin
  cannot work loose: the top shell is against its inner end and the outer pin against its outer
  end. If the outer pin backs out, the inner one still holds that corner;
- at each front corner of the body the end wall steps down to a **1 x 1 brick** and a **1 x 1
  tile**, so the outer hinge plate has room to come down in front of it.

### How the pins go in

A Technic pin goes into a hole only up to the ridge in its middle. Two parts are pinned together
by pushing the pin into one and sliding the other onto the half that sticks out, along the pin.
The flap is one rigid piece and its pins run along it, so it cannot slide onto them at both
ends. So the hinge plates go on the pins first, loose, and the flap is pressed onto the hinge
plates' studs last. At each corner, all from the end, as the last steps of the top shell (it is
upside down): a pin into the inner pivot block, which is in the shell's third layer; the inner
hinge plate slid onto it; the outer pivot block onto its stud (before this, it would block that
hinge plate's way in); a pin into it; the outer hinge plate onto that. The top shell is lowered
onto the chassis, the four hinge plates are turned to hang straight down, and the flap is
pressed onto them: eight studs. The buildability check holds the booklet to this order: with the
outer pivot block on first, it finds no way in for the inner hinge plate.

## One Pick a Brick parcel

Pick a Brick ships its Bestseller pieces together within days and the rest later, in a parcel of
their own. Every line of the kit is a Bestseller (lego.com, US shop, 2026-10-28), so it comes in
one parcel; the reels' 8 x 8 round plates are Light Bluish Gray (6353794) for that reason, as
Black 74611 is a Standard piece. The range changes: look again before ordering. (That is the
black cassette; the `white` colourway's own lines were not looked up.) Two elements are sold
under other numbers than LDraw's data gives: the flap's friction pins as 6279875 ("CONNECTOR
PEG W. FRICTION", LEGO's design 61332) and the 2 x 16 plate as 428226.
`brickkit/data/pick_a_brick.json` swaps each for the number that is sold, so
`out/pick_a_brick.csv` is the whole kit.

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

1. **Chassis** (`core`, 137 parts). Two floor layers, woven crosswise (rows along X, then
   columns along Z) so every plate is bonded:
   - Bottom layer: two square **drive holes**, 4 x 4 studs, one under each reel; a Technic
     plate 2 x 4 whose middle hole is the **lamp hole**, a Technic plate 1 x 5 whose axle
     hole is the **reel-lock release hole**, five **Flat Silver 1 x 1 round plates as screw
     heads**, and the open **mouth** (a 15-stud slot) under the tape.
   - Second layer: **smooth tiles wherever a reel turns**, plates elsewhere. Over each drive
     hole four 2 x 4 tiles in a pinwheel leave a 2 x 2 square for the reel's drive hub (the
     reel's bearing). In front of and behind them a 1 x 6 tile lies along the cassette, where
     a column would be a single 1 x 1.
   - On top: the **lamp tube** (black 2 x 2 round brick) centre-front, the **white brake
     release** at the back centre, **white guide rollers** (1 x 1 round bricks) at both
     front corners with a guide post behind each, ledges and posts the windows land on, and three
     bricks with a side stud carrying the **tape run**: black 1 x N plates stood on edge with
     black tiles facing forward, stretched between the rollers.
2. **Reels** (17 parts each, identical hardware; see Mechanisms). They drop into the
   chassis' drive holes, the full supply reel at +X, the take-up reel at -X.
3. **End walls**: a 1 x 8 brick at each end, a 1 x 1 brick in front of it and a 1 x 1 tile
   at the corner, under the flap's outer hinge plate.
4. **Top shell** (180 parts), built upside down and lowered on:
   - Face layer: **grip bands** of 1 x 2 grille tiles along both long edges (slots along
     the cassette, like the moulded ribs), the black rim round the label (1 x 4 tiles
     front and back, a 1 x 6 tile on each side, next to the windows), 1 x 8 tiles at
     the ends. Two plate layers under it, woven crosswise (behind each cut-back front
     corner a 1 x 3 plate runs along the cassette instead, over both pivot blocks); the
     third layer carries the flap's two inner pivot blocks.
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
   - Last, the flap's **pivots** at the two front corners: four pins, two outer pivot blocks
     and four hinge plates (see "How the pins go in").
5. **Dust flap** (15 parts), built flat, then pressed onto the four hinge plates.

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
front studs are capped by a 1 x 6 tile that butts against the front grip band. Nothing can
take those studs (the grip band in front of them is tiles and plates, and a reel turns under
most of the front edge), so the front rests on a post instead: under each window's outer
front corner, where the reel does not reach, a black 1 x 1 brick stands on the chassis
floor, and its stud meets the underside of the frame and of the cap tile. Without it the
frame is a cantilever from its six back studs, and a poke at its front edge tips it in. The
reel passes 9 LDU (3.6 mm) from the post at its nearest. The glass is placed
1 LDU off LDCad's snap point, where the two meshes overlap slightly; its hinge-style
connection still registers.

## Mechanisms

### Dust flap (`flap`)
The flap is the whole front edge: 23 studs long, 24 mm tall (y -64..-4), 6.4 mm thick,
black and smooth. It is built lying on its back: one 2 x 16 plate stood up, studs forward,
2 x N tiles whose upper halves hang over the plates and make the flap's top row, 1 x N tiles
for the bottom row, and at each end plates that reach the top row (two 2 x 3 at +X, a 2 x 3
and a 1 x 3 at -X). On their backs, on two studs each, are four **1 x 2 plates with a pin
hole under one end (18677)**, holes uppermost: the flap's **hinges**, at x = +-220 and
+-180.

It pivots on four **Black Technic pins with friction (2780)** along X, two at each corner,
end to end: each joins a hinge plate to the **Plate 1 x 2 with Pin Hole on Top (11458)**
inside it, a pivot block in the top shell's third layer (x = +-200 and +-160). The outer
blocks stand on the white guide rollers and the post behind each; all four hang from the
second layer by their studs, the two at each corner from one 1 x 3 plate. The axis is at
y = -54, z = -100: 10 LDU below the top and 10 LDU behind the flap. `pose(t)` turns the flap by `rot(x = -90 t)` about it, so the bottom edge
swings forward and up until the flap lies flat as a visor. Because the top row is the
overhanging half of the tiles (nothing behind it), the flap's top edge swings clear of
the top shell: the mechanism check sweeps it with no collisions. The friction pins give
it some hold (a real flap is sprung shut).

When it is up, you see the tape run straight across the mouth between the two white
guide rollers.

### Reels (`reel_l` supply, `reel_r` take-up)
Each reel, from the bottom:

1. A **Light Bluish Gray Plate Round 8 x 8 (74611)**: the lower flange, 64 mm.
2. A second one on top of it: on the full supply reel, the tape pack under the tape tiles.
   Through the clear ring both reels show grey, like the grey or white inside of a real
   cassette, round the black tape.
3. The hub: a **White 2 x 2 round plate with axle hole (4032a)** in a ring of four white
   **2 x 2 macaroni tiles** (32 mm); the round plate's four studs are the ring of bumps.
4. Four black **3 x 3 macaroni tiles**: tape round the hub (r 40..60 LDU, 48 mm).
5. Four **Trans-Clear 4 x 4 macaroni tiles**: the clear upper flange (r 60..80).
6. A **Red Technic Axle 2 Notched** pushed up through the round plates' holes and the
   hub's axle hole: its end is the **red dot** in the hub.
7. The **drive hub**: a second **White 4032a** pushed studs-down onto the axle's lower end,
   against the lower flange. Its four studs are the pegs the reel is turned by.

The reel lies loose in the chassis, as a real one does. Its drive hub turns in the 2 x 2
square the four tiles leave (the bearing), the reel rides on the smooth tiles and the top
shell keeps it down. Underneath, each drive hole shows the white hub, its four pegs and the
red spindle end in the middle: put a fingertip on the pegs and turn, as a VCR's spindle turns
the hub from below. Nothing clicks a reel to the chassis, so the connections check is told the
two may be separate (`[checks.connections] allow_separate_tags`), and both are declared
`captive` (they are trapped by the shell).

Through the windows each reel reads as a white hub, a ring of black tape and a clear ring
over grey.
`pose(t)` turns both reels the same way, as when playing: the supply reel 270 degrees and
the take-up reel 360 degrees (the small pack spins faster for the same tape speed).

## Part choices

- **74611** has no LDCad shadow file of its own: the engine reads an overlay snap file from
  `brickkit/data/shadow/` (see Engine support), which gives it its 44 anti-studs.
- **Tape is Black**, like real tape seen through a window. It reads against the grey
  flanges and the white hub.
- **27507 is a ring (r 60..80 only)**. **68568 (Tile 4 x 4 quarter circle)** would not do: it
  is not a concentric ring and clashes with the macaroni tiles.
- **2780 pins stay Black** in every colourway: LEGO never made them in White. On Pick a
  Brick the pin is element 6279875 (see "One Pick a Brick parcel").
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
- **Drive holes** are square, 32 mm, with a round hub of four pegs; a real one is a round
  30 mm opening on a hub with a ring of teeth inside. LEGO makes no plate with a round hole
  that size among the Bestsellers (the 4 x 4 round plate with a 2 x 2 hole, 11833, is not on
  Pick a Brick at all), and the pegs are studs, so there are four.
- **Clear upper flange** is a ring: there is no flat transparent 8 x 8 disc, so inside
  r 60 you see the pack directly.
- **Lamp tube** is 4 mm right of centre: a 2 x 2 round brick has to sit on a cell corner.
- The top shell's two front corners are cut back, four studs along the front, where the
  flap's hinge plates and pivot blocks sit on the pivot axis and swing: from above they read as
  a hinge's knuckles.
- The tape's tiles stop a stud short of each guide roller: the inner hinge plate hangs in front
  of that stud of the tape's plate, which shows beside the roller when the flap is up.
- The inner pivot blocks hang from the top shell by one stud each (nothing is under them but
  the tape and the reel). The flap holds them in line with the outer blocks, which also stand
  on posts.
- The flap stops 1.6 mm above the bottom edge, and its pin heads show on the ends.
- The spine label runs to the bottom edge (two tile rows).
- The bottom is a LEGO bottom (anti-studs), not a smooth moulding.
- Not modelled: door-release button, end-sensor light paths, reel brake levers (only the
  white release).

## Checks

`brickkit all vhs_tape`: every check passes with no warnings. real_elements (54
combinations, 0 rare, also for `white`), connections (973, 29 of them pin; three pieces: the
cassette and its two loose reels), collisions (0), buildability (255 insertions, 14
sub-assemblies), stability (tips at 75 degrees), mechanism (24 poses, 3 moving groups: the
flap with its four hinge plates sweeps 0 to 90 degrees with no collisions; plus the size
check), electrics (none), technique (0 notes).

## Engine support

- **Shadow overlays**: `ShadowLibrary(..., overlays=[...])` reads extra
  `!LDCAD SNAP_*` files after the LDCad library's own file for a part. The engine passes
  `brickkit/data/shadow/`, which holds `parts/74611.dat` (44 anti-studs). Tested in
  `tests/test_snaps.py`, documented in `docs/brickkit-guide.md` under "The checks".
- Buildability lets clips, click hinges and Technic pins snap on.

## Code

`design.py` holds the sub-assemblies (`reel`, `core`, `window`, `label_panel`,
`top_shell` with `pivots`, `flap`), the pose and the size check. `kit.py` has the layout helpers:
`weave` lays a layer in rows along X or columns along Z (runs chosen by `split_line`, never
a 1-stud run at an end), `Batch` orders a phase's parts into steps that each join what is
already built, and `best_layout` tries layout variants until every phase is one piece.

## Renders

`out/renders/`: `three_quarter.png` and `front.png` (closed), `open.png` (flap up, reels
turned: `out/renders_open/three_quarter.png`), `close_pivots_r.png` (the -X front corner,
closed: the outer pin's end in the end face, the cut-back corner; open:
`out/renders_open/close_pivots_r.png`; `brickkit render vhs_tape --views close:pivots_r`),
`back.png` (spine label and write-protect tab), `underside.png` (drive holes with the reels'
drive hubs, screws, mouth), `white.png` (the white colourway). Hero shots: `out/hero/hero.png` and
`out/hero_open/hero.png`.
